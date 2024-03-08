# from gurobipy import Model, GRB, tuplelist, quicksum
from scheduler_gurobi import SchedulerGurobi
from scheduler_cpsat import SchedulerCPSAT
from scheduler_highs import SchedulerHighs
from scheduler_pulp import SchedulerPulp
import json
import os
from scheduler_utils import TelescopeEvent, RequestInjection, cut_time_segments, trim_time_segments

class SchedulerSimulation(object):
    def __init__(self, filepath=None, data=None, timelimit=0,
                 scheduler_type="gurobi", simulation_horizon_days=3):
        if filepath != None:
            self.load_file(filepath)
        elif data != None:
            self.load_data(data)
        else:
            print("Neither filepath nor data provided. Aborting.")
            print(data)
            return
        self.timelimit=timelimit
        self.scheduler_type = scheduler_type
        self.Scheduler = self.get_scheduler(scheduler_type)
        self.simulation_horizon = simulation_horizon_days * 24 * 60 * 60

        self.current_event = 0


    def get_scheduler(self, scheduler_type):
        scheduler_types = {
            "gurobi": SchedulerGurobi,
            "cpsat": SchedulerCPSAT,
            "highs": SchedulerHighs,
            "cbc": SchedulerPulp,
            "scip": SchedulerPulp,
            "gurobi_pulp": SchedulerPulp,
            "gurobi_pulp_cmd": SchedulerPulp
        }
        return scheduler_types[scheduler_type]


    def load_data(self, input_data):
        # Load Initial Parameters
        self.start_time = input_data["input_parameters"]["start_time"]
        self.horizon = input_data["input_parameters"]["horizon"]
        self.slice_size = input_data["input_parameters"]["slice_size"]
        self.proposals = input_data["input_parameters"]["proposals"]

        # RESOURCES (Telescopes)
        # The natural rise-set times of each telescope, predictable.
        self.base_resources = input_data["input_parameters"]["resources"]
        # The telescopes that are available at 'self.now'
        self.current_resources = {res for res in self.base_resources}
        # print("START - CURRENT RESOURCES", self.current_resources)
        # The time impacts of observations running at 'self.now'
        self.SOMETHING = []
        # A list of all closures to allow us to "foresee" them
        self.all_closures = {res: [] for res in self.base_resources}

        # REQUESTS
        # A total collection of all events in this Simulation
        self.all_requests = {}
        # A list of the request IDs that have been created at 'self.now'
        self.current_requests = []
        # A dict of the requests that have been completed in previous schedules
        self.completed_requests = {}

        # EVENTS - changes to requests or resources that trigger another scheduler run
        self.events = []

        # RESULTS
        # A place to log the results of each scheduler run -- THIS MIGHT HAVE TO BE ADAPTED
        self.scheduler_results = []

        self.load_events(input_data["injections"])


    def load_file(self, input_filepath):
        with open(input_filepath, "r") as f:
            input_data = json.load(f)
        self.load_data(input_data)


    def load_events(self, inj_list):
        for inj in inj_list:
            if inj["injection_type"] == "request":
                new_requests = []
                for reqID in inj["injection_data"]:
                    self.all_requests[reqID] = inj["injection_data"][reqID]
                    new_requests.append(reqID)
                self.events.append(RequestInjection(inj["injection_time"], new_requests))

            elif inj["injection_type"] == "resource":
                data = inj["injection_data"]
                self.all_closures[data["resource"]].append({"start": data["start_time"],
                                                            "end": data["end_time"]})

                self.events.append(TelescopeEvent(data["start_time"],
                                             data["resource"],
                                             True)
                             )
                self.events.append(TelescopeEvent(data["end_time"],
                                             data["resource"],
                                             False)
                             )
        self.events.sort()


    def get_scheduler_info(self):
        # Output the current state of the simulation as data to feed into a scheduler.
        return {
            "now": self.now,
            "horizon": self.horizon,
            "slice_size": self.slice_size,
            "resources": { k: trim_time_segments(v, start_cap=self.now, end_cap=self.now + self.horizon) for k, v in self.base_resources.items() if k in self.current_resources}, 
            "proposals": self.proposals,
            "requests": { r: v for r, v in self.all_requests.items() if r in self.current_requests},
            "timelimit": self.timelimit
        }


    def get_next_events(self):
        # Gather next group of events
        event_group = []

        self.now = self.events[self.current_event].time
        event_group.append(self.current_event)

        for i in range(self.current_event+1, len(self.events)):
            event_time = self.events[i].time
            if event_time < self.now:
                # Selected event happens before 'now'. This shouldn't happen.
                print("ERROR: Events processed out of order")
                print("Self.now: {}, Event.time: {}".format(self.now, event_time))

            elif event_time == self.now:
                # Selected event happens simultaneously with 'now'. Add to group.
                event_group.append(i)

            else:
                # Haven't reached the selected event yet
                break

        return event_group


    def process_event_group(self, event_group):
        for i in event_group:
            event = self.events[i]
            self.process_event(event)
        self.now = event.time
        self.current_event = max(event_group)+1


    def process_event(self, event):
        if event.type == "request":
            self.current_requests += event.data

        elif event.type == "resource":
            resource = event.data["resource"]

            if event.data["closed"]:
                if resource in self.current_resources:
                    self.current_resources.remove(resource)

            else:
                if resource in self.base_resources:
                    self.current_resources.add(resource)


    def check_occupied_requests(self):
        occupied_requests = []
        occupied_resources = {}

        for rid, r in self.scheduler_results[-1]["scheduled"].items():
            if r["start"] > self.now:
                # Scheduled request hasn't been executed yet, still changeable
                continue

            else: # r["start"] <= self.now
                # Observation has at least been started
                
                if r["end"] <= self.now:
                    # Observation has been completed, save the result
                    self.completed_requests[rid] = r

                else: # r["end"] > self.now
                    # Request has been started, but not finished

                    # Check whether the request has been interrupted
                    if r["resource"] in self.current_resources:
                        # Request is currently being executed.
                        # Remove from schedulable requests,
                        # and remove the occupied time from the resource.
                        occupied_requests = rid
                        occupied_resources[r["resource"]] = r["end"]

                    else: # r["resource"] not in self.current_resources
                        # Occupied telescope has closed down, interrupting observation
                        # Request ID will not be in completed_requests,
                        # and we're not putting it in occupied_requests,
                        # so no more needs to be done. It will go back into the pool.
                        pass

        # Filter out occupied and completed requests
        requests = {}
        for reqID in self.current_requests:
            if reqID not in self.completed_requests:
                if reqID not in occupied_requests:
                    requests[reqID] = self.all_requests[reqID]

        # Filter resources
        resources = {}
        for res in self.current_resources:
            resource_times = self.base_resources[res]
            if res in occupied_resources:
                resource_times = cut_time_segments(resource_times,
                                                   cut_start=occupied_resources[res])
            resources[res] = resource_times

        return (requests, resources)


    def run_scheduler(self):
        # Complete a scheduling run with the current information
        scheduler = self.Scheduler(self.now, self.horizon, self.slice_size,
                                   resources, self.proposals, requests,
                                   verbose=0, timelimit=self.timelimit,
                                   scheduler_type=self.scheduler_type)
        currently_scheduled = scheduler.run()
        self.last_scheduler = scheduler
        self.scheduler_results.append(currently_scheduled)


    def run_simulation(self):
        while self.current_event < len(self.events):
            next_events = self.get_next_events()
            self.process_event_group(next_events)

            if len(self.scheduler_results) > 0:
                # Scheduler has already been run at least once
                self.check_occupied_requests()

            self.run_scheduler()

        # After all events are processed (no changes to network)
        self.now = self.scheduling_horizon
        self.check_occupied_requests()


    def display_simulation_results(self):
        print("\nSimulation Complete.")

        scheduled_by_resource = {}
        for r in self.completed_requests.values():
            resource = r["resource"]
            if resource not in scheduled_by_resource:
                scheduled_by_resource[resource] = []
            scheduled_by_resource[resource].append(r)

        for resource, res_list in scheduled_by_resource.items():
            res_list.sort(key=lambda x: x["start"])
            print(f"Scheduled requests for '{resource}'")
            for r in res_list:
                print(f"{r['rID']}: {r['start']} - {r['end']} ({r['duration']}), Priority = {r['priority']}")
            print()


    def clear_results(self):
        self.completed_requests = {}

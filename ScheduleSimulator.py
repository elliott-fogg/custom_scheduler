from gurobipy import Model, GRB, tuplelist, quicksum
from gurobipy import read as gurobi_read_model
# from scheduler_v2 import Scheduler
# from scheduler_v3 import SchedulerV3 as Scheduler
from scheduler_v4 import SchedulerV4 as Scheduler
import json
import random
import math
import os
from scheduler_utils import TimeSegment, Injection, TelescopeEvent, RequestEvent, cut_time_segments

class SchedulerSimulation(object):
    def __init__(self, filepath=None, data=None):
        if filepath != None:
            self.load_file(filepath)
        elif data != None:
            self.load_data(data)
        else:
            print("Neither filepath nor data provided. Aborting.")
            print(data)
            return


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


    def load_events(self, inj_list):
        for inj in inj_list:
            if inj["injection_type"] == "request":
                new_requests = []
                for reqID in inj["injection_data"]:
                    self.all_requests[reqID] = inj["injection_data"][reqID]
                    new_requests.append(reqID)
                self.events.append(RequestEvent(inj["injection_time"], new_requests))

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

        # print(f"{len(self.events)} Events loaded.")


    def process_event(self, event):
        self.now = event.time

        if event.type == "request":
            self.current_requests += event.data
            # print(f"Request Event ({event.time}): {event.data}")
            # print(self.current_requests)

        elif event.type == "resource":
            resource = event.data["resource"]

            if event.data["closed"]:
                if resource in self.current_resources:
                    self.current_resources.remove(resource)

            else:
                if resource in self.base_resources:
                    self.current_resources.add(resource)

            # print(f"Resource Event ({event.time}): {resource} {'closed' if (event.data['closed']) else 'opened'}")


    def prepare_scheduler(self, final=False):
        # Check if any requests have been successful
        # Check if any requests are in the middle of being completed
            # Check if those requests have been cancelled
            # Check if they impact available resource time

        if final:
            self.now = self.horizon

        occupied_requests = []
        occupied_resources = {}

        if len(self.scheduler_results) == 0:
            # We're in the first run, don't need to account for past requests
            pass

        else:
            for rid, r in self.scheduler_results[-1]["scheduled"].items():
                if r["start"] > self.now:
                    # Request hasn't been executed yet, still changeable
                    continue

                elif r["end"] <= self.now:
                    # Request has been executed. Save the information.
                    self.completed_requests[rid] = r

                else:
                    # Request is currently being executed. Check if it has been 
                    # interrupted.
                    if r["resource"] in self.current_resources:
                        # Request is currently being executed. Remove from 
                        # schedulable requests (assume it is fixed), and remove
                        # the required time from the relevant resource.
                        occupied_requests.append(rid)
                        occupied_resources[r["resource"]] = r["end"]
                        # print(f"Occupied Request: {rid}")

                    else:
                        # Request has been interrupted. Reissue it as if it was
                        # never scheduled.
                        # print(f"Interrupted Request: {rid}")
                        pass

        # Filter requests
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
                                                   self.now, 
                                                   occupied_resources[res])
            resources[res] = resource_times

        # print("Scheduling Run Information:")
        # print(f"Now: {self.now}")
        # print(f"Current Requests: {self.current_requests}")
        # print(f"Completed Requests: {list(self.completed_requests.keys())}")
        # print(f"Schedulable Requests: {list(requests.keys())}")
        # print(f"Current Resources: {list(self.current_resources)}")

        return requests, resources


    def run_scheduler(self, requests, resources):
        sched = Scheduler(self.now, self.horizon, self.slice_size, resources, self.proposals, requests, verbose=0)
        sched.calculate_free_windows()
        sched.build_data_structures()
        sched.build_model()
        sched.solve_model()
        self.last_sched = sched
        scheduled = sched.return_solution(False)
        self.scheduler_results.append(scheduled)


    def run_simulation(self):
        i = 0 # The index of the current event

        while i < len(self.events):
            # Process next event, and any events that happen simultaneously
            current_time = self.events[i].time

            while True:
                self.process_event(self.events[i])

                if i+1 >= len(self.events):
                    break

                # If next event is simultaneous, process it too
                if self.events[i+1].time == current_time:
                    i += 1
                else:
                    break

            # Run Scheduler
            requests, resources = self.prepare_scheduler()
            self.run_scheduler(requests, resources)

            # Move to the next event
            i += 1

        self.prepare_scheduler(final=True)
        # self.display_simulation_results()


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

# from gurobipy import Model, GRB, tuplelist, quicksum
from scheduler_gurobi import SchedulerGurobi
from scheduler_cpsat import SchedulerCPSAT
from scheduler_highs import SchedulerHighs
from scheduler_pulp import SchedulerCBC, SchedulerSCIP, SchedulerGurobiPulp, SchedulerGurobiPulpCMD
import json
import pickle
import os
import datetime as dt
from scheduler_utils import TelescopeEvent, RequestInjection, cut_time_segments, trim_time_segments

# TO FIX: modify the functions in scheduler_utils.py so that they do not require both a start and end
# point to cut time segments from only 1 direction (e.g. clipping them to 'now').

class SchedulerSimulation(object):
    def __init__(self, filepath, timelimit=0, scheduler_type="gurobi",
                 slice_size=300, stepsize=750, horizon_days=None):
        self.timelimit = timelimit  # Limit to timeout the Scheduler, in seconds.
        self.Scheduler = self.get_scheduler(scheduler_type)     # Set the scheduler type.
        self.slice_size = slice_size    # Chunk size in seconds to discretise
                                        # time in the Scheduler.
        self.stepsize=750   # Time in seconds to step the simulation forward
                            # between each run.
        self.load_data_from_file(filepath)
        self.horizon = horizon_days * 24 * 60 * 60


    def get_scheduler(self, scheduler_type):
        scheduler_types = {
            "gurobi": SchedulerGurobi,
            "cpsat": SchedulerCPSAT,
            "highs": SchedulerHighs,
            "cbc": SchedulerCBC,
            "scip": SchedulerSCIP,
            "gurobi_pulp": SchedulerGurobiPulp,
            "gurobi_pulp_cmd": SchedulerGurobiPulpCMD
        }
        return scheduler_types[scheduler_type]


    def load_data_from_file(self, filepath):
        data = pickle.load(open(filepath, "rb"))

        self.sim_start = data["start"]  # Starting datetime of the simulation
        self.now = self.sim_start       # Current time in the simulation
        self.sim_end = data["end"]      # Ending datetime of the simulation
        self.horizon = data["horizon"]  # Horizon time in seconds
        self.telescopes = data["telescopes"]    # Dictionary of telescope names
        self.all_requests = data["all_requests"]    # Dictionary of request information
        self.initial_requests = data["initial_requests"]    # List of requests that start loaded
        self.proposals = data["proposals"]  # Proposal data
        self.request_injections = data["request_injections"]    # DF of {"time": dt, "request": id} for requests added to the simulator
        self.telescope_closures = data["telescope_closures"]    # DF of {"start": dt, "end": dt, "telescope": name} for telescope closures

        # Clear telescopes with 'igla' domes
        self.telescopes = {mask_name: real_name for mask_name, real_name in data["telescopes"].items() if 'igla' not in real_name}

        # Telescopes
        self.current_telescopes = [t for t in self.telescopes]   # List of telescopes that are currently active
        self.occupied_telescopes = {}   # Dictionary of {telescope_name: dt} for telescopes that are occupied with observations

        # Requests
        self.scheduled_requests = {}    # Dictionary of {req_id: {start: dt, end: dt, telescope: name}} for requests that are currently being executed
        self.completed_requests = {}    # Dictionary of {req_id: {start: df, end: dt, telescope: name}} for requests that were successfully completed

        # Results
        self.results = []


    def get_current_telescopes(self):
        # Add in some function here to check telescope closures for what
        # telescopes are available.
        # Also get the next start time for each telescope.
        current_telescopes = {telescope: None for telescope in self.telescopes}
        for telescope in self.occupied_telescopes:
            current_telescopes[telescope] = self.occupied_telescopes[telescope]
        self.current_telescopes = current_telescopes


    def is_schedulable(self, request_windows):
        for telescope in request_windows:
            if telescope in self.current_telescopes:
                return True
        return False


    def get_schedulable_requests(self):
        created_requests = self.all_requests[self.all_requests["created"]<=self.now]
        
        completed_requests = set(self.completed_requests.keys())
        scheduled_requests = set([request_id for request_id, request in self.scheduled_requests \
                                if request["start"] < self.now])
        unavailable_requests = completed_requests.union(scheduled_requests)

        schedulable_requests = created_requests[created_requests["windows"].apply(self.is_schedulable) & ~created_requests["id"].isin(unavailable_requests)]

        self.schedulable_requests = schedulable_requests


    def run_scheduler(self):
        # Get schedulable requests
        # Check which telescopes are available
        # schedulable_request_data = self.all_requests[self.all_requests["id"].isin(self.schedulable_requests)]

        scheduler = self.Scheduler(
            now=self.now,
            horizon=self.horizon,
            slice_size=self.slice_size,
            telescopes=self.current_telescopes,
            proposals=self.proposals,
            requests=self.schedulable_requests.to_dict(orient="index"),
            verbose=0,
            timelimit=self.timelimit
        )

        current_schedule = scheduler.run()
        print(current_schedule)


    def resolve_scheduled_requests(self):
        pass


    def step_simulation(self, timedelta):
        self.now += dt.timedelta(seconds=self.stepsize)

        # Resolve scheduled requests

        # Get all requests that will be added before the next timestep?
        #   Unsure how likely this is to be a problem.

        # Get all telescope closures since the last timestep

        # Check scheduled requests for those that have started / finished
        #   - Pass
        #   - Currently executing / occupying
        #   - Failed

        # Get list of currently available telescopes

        # Pass currently available telescopes (and occupation times), and
        # currently schedulable requests to scheduler for next run.




################################################################################
    ###########
    # TO REDO #
    ###########
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

    ###########
    # TO REDO #
    ###########
    def process_event_group(self, event_group):
        for i in event_group:
            event = self.events[i]
            self.process_event(event)
        self.now = event.time
        self.current_event = max(event_group)+1

    ###########
    # TO REDO #
    ###########
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

    ###########
    # TO REDO #
    ###########
    def check_occupied_requests(self):
        occupied_requests = []
        occupied_resources = {}

        if len(self.scheduler_results) == 0:
            requests = {r: v for r, v in self.all_requests.items() if r in self.current_requests}
            resources = {t: v for t, v in self.base_resources.items() if t in self.current_resources}
            return (requests, resources)

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
                                                   cut_start=occupied_resources[res],
                                                   cut_end=self.now + self.simulation_horizon)
            resources[res] = resource_times

        return (requests, resources)

################################################################################








    def WIP_get_scheduler_input(self):
        # Output the current state of the simulation to feed into the scheduler

        # Get NOW, HORIZON, SLICE SIZE, TELESCOPES, PROPOSALS, CURRENT REQUESTS, TIMELIMIT
        pass


    def WIP_run_scheduler(self, schedulable_requests):
        # Complete a scheduling run with the current simulation state
        scheduler = self.Scheduler(
            now=self.now,
            horizon=self.horizon,
            slice_size=self.slice_size,
            telescopes=self.current_telescopes,
            proposals=self.proposals,
            requests=schedulable_requests,
            verbose=0,
            timelimit=self.timelimit
        )

        current_scheduled = scheduler.run()
        self.scheduler_results.append(currently_scheduled)


    ###########
    # IN_PROGRESS #
    ###########
    def WIP_check_occupied_requests(self):
        """
        Go through the scheduled requests at the current point in time,
        and either:
            a) Save them if their end time has passed.
            b) Log them as taking up resources if they have started but their
                end time has not passed.
            c) Revoke them if a telescope closure has interrupted them before
                their end time passed.


        """
        # occupied_requests = []
        # occupied_resources = {}

        # if len(self.scheduler_results) == 0:
        #     requests = {r: v for r, v in self.all_requests.items() if r in self.current_requests}
        #     resources = {t: v for t, v in self.base_resources.items() if t in self.current_resources}
        #     return (requests, resources)

        # for rid, r in self.scheduler_results[-1]["scheduled"].items():
        #     if r["start"] > self.now:
        #         # Scheduled request hasn't been executed yet, still changeable
        #         continue

        #     else: # r["start"] <= self.now
        #         # Observation has at least been started
                
        #         if r["end"] <= self.now:
        #             # Observation has been completed, save the result
        #             self.completed_requests[rid] = r

        #         else: # r["end"] > self.now
        #             # Request has been started, but not finished

        #             # Check whether the request has been interrupted
        #             if r["resource"] in self.current_resources:
        #                 # Request is currently being executed.
        #                 # Remove from schedulable requests,
        #                 # and remove the occupied time from the resource.
        #                 occupied_requests = rid
        #                 occupied_resources[r["resource"]] = r["end"]

        #             else: # r["resource"] not in self.current_resources
        #                 # Occupied telescope has closed down, interrupting observation
        #                 # Request ID will not be in completed_requests,
        #                 # and we're not putting it in occupied_requests,
        #                 # so no more needs to be done. It will go back into the pool.
        #                 pass

        # # Filter out occupied and completed requests
        # requests = {}
        # for reqID in self.current_requests:
        #     if reqID not in self.completed_requests:
        #         if reqID not in occupied_requests:
        #             requests[reqID] = self.all_requests[reqID]

        # # Filter resources
        # resources = {}
        # for res in self.current_resources:
        #     resource_times = self.base_resources[res]
        #     if res in occupied_resources:
        #         resource_times = cut_time_segments(resource_times,
        #                                            cut_start=occupied_resources[res],
        #                                            cut_end=self.now + self.simulation_horizon)
        #     resources[res] = resource_times

        # return (requests, resources)



################################################################################
### Old Functions ###
################################################################################

    # def __init__(self, filepath=None, data=None, timelimit=0, scheduler_type=None):
    #     if filepath != None:
    #         self.load_file(filepath)
    #     elif data != None:
    #         self.load_data(data)
    #     else:
    #         print("Neither filepath nor data provided. Aborting.")
    #         print(data)
    #         return
    #     self.timelimit=timelimit
    #     self.scheduler_type = scheduler_type
    #     self.Scheduler = self.get_scheduler(scheduler_type)
    #     self.simulation_horizon = simulation_horizon_days * 24 * 60 * 60

    #     self.current_event = 0


    # def load_data(self, input_data):
    #     print(input_data)
        
    #     # Load Initial Parameters
    #     self.start_time = input_data["input_parameters"]["start_time"]
    #     self.horizon = input_data["input_parameters"]["horizon"]
    #     self.slice_size = input_data["input_parameters"]["slice_size"]
    #     self.proposals = input_data["proposals"]

    #     # RESOURCES (Telescopes)
    #     # The natural rise-set times of each telescope, predictable.
    #     self.base_resources = input_data["telescopes"]
    #     # The telescopes that are available at 'self.now'
    #     self.current_resources = {res for res in self.base_resources}
    #     # print("START - CURRENT RESOURCES", self.current_resources)
    #     # The time impacts of observations running at 'self.now'
    #     self.SOMETHING = []
    #     # A list of all closures to allow us to "foresee" them
    #     self.all_closures = {res: [] for res in self.base_resources}

    #     # REQUESTS
    #     # A total collection of all events in this Simulation
    #     self.all_requests = {}
    #     # A list of the request IDs that have been created at 'self.now'
    #     self.current_requests = []
    #     # A dict of the requests that have been completed in previous schedules
    #     self.completed_requests = {}

    #     # EVENTS - changes to requests or resources that trigger another scheduler run
    #     self.events = []

    #     # RESULTS
    #     # A place to log the results of each scheduler run -- THIS MIGHT HAVE TO BE ADAPTED
    #     self.scheduler_results = []

    #     self.load_events(input_data["injections"])


    # def load_file(self, input_filepath):
    #     with open(input_filepath, "r") as f:
    #         input_data = json.load(f)
    #     self.load_data(input_data)


    # def load_events(self, inj_list):
    #     print(inj_list)
    #     print(len(inj_list))
    #     print(self.all_requests)
    #     for inj in inj_list:
    #         if inj["injection_type"] == "request":
    #             new_requests = []
    #             for reqID in inj["injection_data"]:
    #                 self.all_requests[reqID] = inj["injection_data"][reqID]
    #                 new_requests.append(reqID)
    #             self.events.append(RequestInjection(inj["injection_time"], new_requests))

    #         elif inj["injection_type"] == "resource":
    #             data = inj["injection_data"]
    #             self.all_closures[data["resource"]].append({"start": data["start_time"],
    #                                                         "end": data["end_time"]})

    #             self.events.append(TelescopeEvent(data["start_time"],
    #                                          data["resource"],
    #                                          True)
    #                          )
    #             self.events.append(TelescopeEvent(data["end_time"],
    #                                          data["resource"],
    #                                          False)
    #                          )
    #     self.events.sort()











    ###########
    # TO REDO #
    ###########
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

    ###########
    # TO REDO #
    ###########
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

    ###########
    # TO REDO #
    ###########
    def process_event_group(self, event_group):
        for i in event_group:
            event = self.events[i]
            self.process_event(event)
        self.now = event.time
        self.current_event = max(event_group)+1

    ###########
    # TO REDO #
    ###########
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

    ###########
    # TO REDO #
    ###########
    def check_occupied_requests(self):
        occupied_requests = []
        occupied_resources = {}

        if len(self.scheduler_results) == 0:
            requests = {r: v for r, v in self.all_requests.items() if r in self.current_requests}
            resources = {t: v for t, v in self.base_resources.items() if t in self.current_resources}
            return (requests, resources)

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
                                                   cut_start=occupied_resources[res],
                                                   cut_end=self.now + self.simulation_horizon)
            resources[res] = resource_times

        return (requests, resources)


    # def run_scheduler(self, requests, resources):
    #     # Complete a scheduling run with the current information
    #     scheduler = self.Scheduler(self.now, self.horizon, self.slice_size,
    #                                resources, self.proposals, requests,
    #                                verbose=0, timelimit=self.timelimit,
    #                                scheduler_type=self.scheduler_type)
    #     currently_scheduled = scheduler.run()
    #     self.last_sched = scheduler
    #     self.scheduler_results.append(currently_scheduled)

    ###########
    # TO REDO #
    ###########
    def run_simulation(self):
        while self.current_event < len(self.events):
            next_events = self.get_next_events()
            self.process_event_group(next_events)

            requests, resources = self.check_occupied_requests()

            # if len(self.scheduler_results) > 0:
            #     # Scheduler has already been run at least once
            #     self.check_occupied_requests()

            self.run_scheduler(requests, resources)

        # After all events are processed (no changes to network)
        self.now = self.simulation_horizon
        self.check_occupied_requests()

    ###########
    # TO REDO #
    ###########
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

    ###########
    # TO REDO #
    ###########
    def clear_results(self):
        self.completed_requests = {}

from gurobipy import Model, GRB, tuplelist, quicksum
from gurobipy import read as gurobi_read_model
from scheduler_v2 import *
import json
import random
import math
import os
from scheduler_utils import TimeSegment, Injection, TelescopeEvent, RequestEvent#, injection_from_json

class SchedulerSimulation(object):
    def __init__(self, input_filepath):
        self.load_file(input_filepath)


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
        print("START - CURRENT RESOURCES", self.current_resources)
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
        self.completed_requests = set() # UNSURE if this should be set or dict

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

        print(f"{len(self.events)} Events loaded.")


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


    def run_scheduler(self):
        if len(self.scheduler_results) == 0:
            # We're in the first run, don't need to account for past requests
            pass
        else:
            for rid, r in self.scheduler_results[-1]["scheduled"].items():
                if r["start"] > self.now:
                    continue

                elif r["end"] <= self.now:
                    self.completed_requests.add(rid)

                else:
                    # These observations are only partway completed.
                    # Assume they are locked into the schedule, and incorporate
                    # them into the blocked off time of the resources.
                    # TODO
                    self.completed_requests.add(rid) # THIS NEEDS TO BE EXTENDED UPON

        # Determine requests
        requests = {}
        for reqID in self.current_requests:
            if reqID not in self.completed_requests:
                requests[reqID] = self.all_requests[reqID]

        print("Scheduling Run Information:")
        print(f"Now: {self.now}")
        print(f"Current Requests: {self.current_requests}")
        print(f"Completed Requests: {self.completed_requests}")
        print(f"Schedulable Requests: {requests.keys()}")
        print(f"Current Resources: {self.current_resources}")


        # Determine resources
        resources = {}
        for res in self.current_resources:
            resources[res] = self.base_resources[res]

        # TODO: Remove windows for resources that have observations currently running
        #
        # Do this here.
        #

        sched = Scheduler(self.now, self.horizon, self.slice_size, resources, self.proposals, requests)
        sched.calculate_free_windows()
        sched.build_data_structures()
        sched.build_model()
        sched.solve_model()

        scheduled = sched.return_solution(False)
        self.save_solution(scheduled)


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
            print(f"Running after {i+1} events...")
            self.run_scheduler()

            # Move to the next event
            i += 1




    # def move_to_next_event(self):
    #     self.current_event



    #     current_event = self.events[self.current_event_num]
    #     current_now = current_event.time

    #     all_current_events = [current_event]
    #     temp_i = self.current_event_num
    #     while True:
    #         next_event = self.events[temp_i + 1]
    #         if next_event.time == current_now:
    #             all_current_events.append(self.events[temp_i])
    #             temp_i += 1
    #         else:
    #             break

    #     for e in all_current_events:
    #         self.process_event(e)

    #     # Update the current_event_num to skip all the events we just processed
    #     self.current_event_num = temp_i

    #     self.run_scheduler()

    #     if self.current_event_num >= self.num_events:
    #         print("SCHEDULER FINISHED")
    #         return

    #     else:
    #         self.current_event_num += 1 
    #         self.move_to_next_event()

        
    # def progress_to_next_event(self):
    #     current_event = self.events[self.current_event_num]
    #     if current_event.type == "request":
    #         self.process_request_event(current_event)
    #     elif current_event.type == "resource":
    #         self.process_resource_event(current_event)

    #     self.now = current_event.time

    #     print("Current event number: {}/{}".format(self.current_event_num, len(self.events)))
    #     print(current_event)
    #     print(current_event.data)
    #     print("Running again. Now = {}".format(self.now))
    #     print("Current requests: {}".format(self.current_requests))
    #     print("Current resources: {}".format(self.current_resources))
        
    #     self.run_scheduler()
        
    #     if self.current_event_num < self.num_events:
    #         self.current_event_num += 1
    #         self.progress_to_next_event()

    #     else:
    #         print("Scheduler has finished running.")
    #         return


    def save_solution(self, scheduled):
        # print(scheduled)
        self.scheduler_results.append(scheduled)
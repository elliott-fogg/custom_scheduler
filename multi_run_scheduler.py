from gurobipy import Model, GRB, tuplelist, quicksum
from gurobipy import read as gurobi_read_model
from scheduler_v2 import *
import json
import random
import math
import os


class Injection(object):
    def __init__(self, injection_time, injection_type, data=None):
        self.injection_time = injection_time
        self.injection_type = injection_type
        self.data = data

    def __str__(self):
        return f"{self.injection_type}_{self.injection_time}"
    
    def __lt__(self, other):
        if self.injection_time == other.injection_time:
            return self.type_lt(other)
        else:
            return self.injection_time < other.injection_time

    def __gt__(self, other):
        if self.injection_time == other.injection_time:
            return self.type_gt(other)
        else:
            return self.injection_time > other.injection_time

    def __eq__(self, other):
        if self.injection_time == other.injection_time:
            return self.type_eq(other)
        else:
            return False

    def type_lt(self, other):
        if self.injection_type == "request": # Either Request vs Request, or Request vs Resource
            return False
        elif other.injection_type == "resource": # Either Resource vs Resource, or Request vs Resource
            return False
        else:
            return True # Must be Resource vs Request

    def type_gt(self, other):
        if self.injection_type == "resource":
            return False
        elif other.injection_type == "request":
            return False
        else: return True

    def type_eq(self, other):
        return self.injection_type == other.injection_type


    def to_json(self):
        return {
            "injection_time": self.injection_time,
            "injection_type": self.injection_type,
            "injection_data": self.data
        }


def injection_from_json(injection_json):
    return Injection(injection_json["injection_time"],
                     injection_json["injection_type"],
                     injection_json["injection_data"])


class TelescopeEvent(Injection):
    def __init__(self, injection_time, resource, closed):
        data = {"resource": resource, "closed": closed}
        super().__init__(injection_time, "resource", data)


class RequestEvent(Injection):
    def __init__(self, injection_time, data):
        super().__init__(injection_time, "request", data)


class MultiRunScheduler(object):
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

        # The natural rise-set times of each telescope, predictable.
        self.base_resources = input_data["input_parameters"]["resources"]

        # Changes to the input data (requests or resources) that trigger 
        # another scheduler run.
        self.events = []

        # Data that lets us do a "hypothetical maximum" scheduling run
        self.all_requests = {}
        self.all_closures = {res: [] for res in self.base_resources}

        self.load_events(input_data["injections"])

        # The version of requests and resources that are fed to the scheduler
        # each individual run.
        self.current_requests = []
        self.current_resources = set()
        for resource in self.base_resources:
            self.current_resources.add(resource)

        # A count to keep track of what event we're on, rather than moving the
        # events around.
        self.next_event = 0
        self.last_event = len(self.events) - 1


    def load_events(self, injection_list):
        for inj in injection_list:
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


    def process_request_event(self, event):
        for new_request_id in event.data:
            self.current_requests.append(new_request_id)


    def process_resource_event(self, event):
        resource = event.data["resource"]

        if event.data["closed"]:
            if resource in self.current_resources:
                self.current_resources.remove(resource)
        else:
            if resource in self.base_resources:
                self.current_resources.add(resource)


    def run_scheduler(self):
        # Determine requests
        requests = {}
        # print(self.current_requests)
        # print(self.all_requests)
        for reqID in self.current_requests:
            requests[reqID] = self.all_requests[reqID]

        # Determine resources
        resources = {}
        for res in self.current_resources:
            resources[res] = self.base_resources[res]
        
        sched = Scheduler(self.now, self.horizon, self.slice_size, resources, self.proposals, requests)
        sched.calculate_free_windows()
        sched.build_data_structures()
        sched.build_model()
        sched.solve_model()
        sched.interpret_solution()


    def progress_to_next_event(self):
        current_event = self.events[self.next_event]
        if current_event.injection_type == "request":
            self.process_request_event(current_event)
        elif current_event.injection_type == "resource":
            self.process_resource_event(current_event)

        self.now = current_event.injection_time

        print("Current event number: {}/{}".format(self.next_event, len(self.events)))
        print(current_event)
        print(current_event.data)
        print("Running again. Now = {}".format(self.now))
        print("Current requests: {}".format(self.current_requests))
        print("Current resources: {}".format(self.current_resources))
        
        self.run_scheduler()
        
        if self.next_event < self.last_event:
            self.next_event += 1
            self.progress_to_next_event()

        else:
            print("Scheduler has finished running.")
            return

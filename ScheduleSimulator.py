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

class SchedulerSimulation(object):
    def __init__(self, filepath, timelimit=0, scheduler_type="gurobi",
                 slice_size=300, stepsize=900, horizon_days=None):
        self.timelimit = timelimit  # Limit to timeout the Scheduler, in seconds.
        self.Scheduler = self.get_scheduler(scheduler_type)     # Set the scheduler type.
        self.slice_size = slice_size    # Chunk size in seconds to discretise
                                        # time in the Scheduler.
        self.stepsize = stepsize    # Time in seconds to step the simulation forward
                                    # between each run.
        self.input_filepath = filepath
        self.create_output_location()
        self.load_data_from_file(filepath)
        self.horizon = horizon_days * 24 * 60 * 60


    def create_output_location(self):
        input_folder, filename = os.path.split(self.input_filepath)
        output_folder = input_folder.replace("input_files", "output_files")
        os.makedirs(output_folder, exist_ok=True)
        self.output_filepath = os.path.join(output_folder, filename)


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
        # self.initial_requests = data["initial_requests"]    # List of requests that start loaded
        self.proposals = data["proposals"]  # Proposal data
        # self.request_injections = data["request_injections"]    # DF of {"time": dt, "request": id} for requests added to the simulator
        # self.telescope_closures = data["telescope_closures"]    # DF of {"start": dt, "end": dt, "telescope": name} for telescope closures

        # Clear telescopes with 'igla' domes
        # self.telescopes = {mask_name: real_name for mask_name, real_name in data["telescopes"].items() if 'igla' not in real_name}

        # Telescopes
        self.current_telescopes = [t for t in self.telescopes]   # List of telescopes that are currently active
        self.occupied_telescopes = {}   # Dictionary of {telescope_name: dt} for telescopes that are occupied with observations

        # Requests
        self.schedulable_requests = []  # List of requests that could be scheduled this run
        self.executing_requests = {}    # Dictionary of {req_id: {start: dt, end: dt, telescope: name}} for requests that are currently being executed
        self.completed_requests = {}    # Dictionary of {req_id: {start: df, end: dt, telescope: name}} for requests that were successfully completed
        self.current_schedule = {"scheduled": {}, "now": self.now}  # Results from last scheduling run
        self.previous_schedule = None

        # Results
        self.results = {}

        print("Sim start:", self.sim_start, ", end:", self.sim_end)

        
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
        
        unavailable_requests = []
        for request_id in self.completed_requests:
            unavailable_requests.append(request_id)
        for request_id in self.executing_requests:
            unavailable_requests.append(request_id)

        schedulable_requests = created_requests[created_requests["windows"].apply(self.is_schedulable)]
        schedulable_requests = schedulable_requests[~schedulable_requests["id"].isin(unavailable_requests)]

        self.schedulable_requests = schedulable_requests


    def run_scheduler(self):
        # Get schedulable requests
        # Check which telescopes are available
        # schedulable_request_data = self.all_requests[self.all_requests["id"].isin(self.schedulable_requests)]

        # Make sure the scheduler horizon caps to the end of the semester (simulation run)
        td_to_end_of_simulation = self.sim_end - self.now
        seconds_to_end_of_simulation = td_to_end_of_simulation.days*24*60*60 + td_to_end_of_simulation.seconds
        scheduler_horizon = min(self.horizon, seconds_to_end_of_simulation)

        self.scheduler = self.Scheduler(
            now=self.now,
            horizon=scheduler_horizon,
            slice_size=self.slice_size,
            telescopes=self.current_telescopes,
            proposals=self.proposals,
            requests=self.schedulable_requests.to_dict(orient="index"),
            verbose=0,
            timelimit=self.timelimit,
            previous_results=self.current_schedule["scheduled"]
        )

        current_schedule = self.scheduler.run()
        self.current_schedule = current_schedule


    def run_scheduler_all(self):
        self.scheduler = self.Scheduler(
            now=self.sim_start,
            horizon=self.sim_end,
            slice_size=self.slice_size,
            telescope=self.current_telescopes,
            proposals=self.proposals,
            requests=self.all_requests.to_dict(orient="index"),
            verbose=0,
            timelimit=self.timelimit,
            previous_results={}
        )

        optimal_schedule = self.scheduler.run()
        return optimal_schedule


    # def check_telescope_closures(self):
    #     pass


    def resolve_executing_requests(self):
        ended = []
        for request_id, request in self.executing_requests.items():
            if request["end"] <= self.now:
                # Request has finished executing, move to completed_requests
                self.completed_requests[request_id] = request
                ended.append(request_id)

        # Clear ended requests from the executing_requests object
        for request_id in ended:
            del self.executing_requests[request_id]


    def resolve_scheduled_requests(self):
        current_schedule = self.current_schedule["scheduled"]
        for request_id, request in current_schedule.items():
            if request["start"] >= self.now:
                # Request has not started yet, ignore
                continue

            elif request["end"] < self.now:
                # Request has already finished, add it to completed_requests.
                self.completed_requests[request_id] = request

            else:
                # Request has started, but not finished yet. Add to executing_requests.
                self.executing_requests[request_id] = request


    def resolve_occupied_telescopes(self):
        self.occupied_telescopes = {}
        for request_id, request in self.executing_requests.items():
            telescope = request["resource"]
            if telescope in self.occupied_telescopes:
                print()
                print("ERROR: Multiple requests currently executing on the same telescope!")
                print(request)
                print(self.occupied_telescopes[telescope])

            self.occupied_telescopes[telescope] = request["end"]


    def step_simulation(self):
        # Step time forward
        self.now += dt.timedelta(seconds=self.stepsize)

        # # Check for telescope closures
        # self.check_telescope_closures()

        # Resolve executing requests
        self.resolve_executing_requests()

        # Resolve scheduled requests
        self.resolve_scheduled_requests()

        # Book out telescopes
        self.resolve_occupied_telescopes()


    def run_simulation(self):
        total_steps = (self.sim_end - self.sim_start) / dt.timedelta(seconds=self.stepsize)
        step_count = 0

        while self.now < self.sim_end:
            if step_count % 10 == 0:
                print(f"{step_count} / {total_steps} - {self.now}")

            self.get_current_telescopes()
            self.get_schedulable_requests()
            self.run_scheduler()
            self.step_simulation()

            step_count += 1

        self.results["final_completed_requests"] = self.completed_requests
        self.results["final_schedule"] = self.current_schedule
        self.save_results()
        return self.completed_requests


    def run_simulation_short(self, num_steps):
        step_count = 0
        while self.now < self.sim_end:
            if step_count % 10 == 0:
                print(f"{step_count} / {num_steps} - {self.now}")

            self.get_current_telescopes()
            self.get_schedulable_requests()
            self.run_scheduler()
            self.step_simulation()

            step_count += 1
            if step_count >= num_steps:
                return self.completed_requests
        return self.completed_requests


    def whole_step(self):
        print(self.now)
        self.get_current_telescopes()
        self.get_schedulable_requests()
        print(self.schedulable_requests.index)
        self.run_scheduler()
        self.print_current_schedule()
        self.step_simulation()
        self.print_completed_requests()


    def print_current_schedule(self):
        print("Current schedule:")
        resources = {t: [] for t in self.telescopes}
        for request_id, request in self.current_schedule["scheduled"].items():
            resources[request["resource"]].append({"id": request["rID"],
                                                   "start": request["start"],
                                                   "end": request["end"]})
        print(self.current_schedule["now"])
        for telescope, requests in resources.items():
            print(telescope)
            for request in sorted(requests, key=lambda x: x["start"]):
                print(f"\t{request['id']}: {request['start']} -> {request['end']}")
        print()


    def print_completed_requests(self):
        print("Completed requests:")
        resources = {t: [] for t in self.telescopes}
        for request_id, request in self.completed_requests.items():
            resources[request["resource"]].append({"id": request["rID"],
                                                   "start": request["start"],
                                                   "end": request["end"]})
        for telescope, requests in resources.items():
            print(telescope)
            for request in sorted(requests, key=lambda x: x["start"]):
                print(f"\t{request['id']}: {request['start']} -> {request['end']}")
        print()


    def print_executing_requests(self):
        print("Executing requests:")
        resources = {t: [] for t in self.telescopes}
        for request_id, request in self.executing_requests.items():
            resources[request["resource"]].append({"id": request["rID"],
                                                   "start": request["start"],
                                                   "end": request["end"]})
        for telescope, requests in resources.items():
            print(telescope)
            for request in sorted(requests, key=lambda x: x["start"]):
                print(f"\t{request['id']}: {request['start']} -> {request['end']}")
        print()



    def test_simulation(self):
        total_steps = (self.sim_end - self.sim_start) / dt.timedelta(seconds=self.stepsize)
        step_count = 0

        previous_schedule = None
        previous_requests = set()

        while self.now < self.sim_end:
            # if step_count % 10 == 0:
            #     print(f"{step_count} / {total_steps} - {self.now}")

            self.get_current_telescopes()
            self.get_schedulable_requests()

            current_requests = set(self.schedulable_requests.index)
            if current_requests != previous_requests:
                print("Requests added:", current_requests - previous_requests)
                print("Requests removed:", previous_requests - current_requests)
                previous_requests = current_requests

            self.run_scheduler()
            if self.current_schedule["scheduled"] != previous_schedule:
                self.print_current_schedule()
                previous_schedule = self.current_schedule["scheduled"]

            self.step_simulation()
            # self.print_completed_requests()
            self.print_executing_requests()

            step_count += 1
        return self.completed_requests


    def save_results(self):
        pickle.dump(self.results, open(self.output_filepath, "wb"))
        print("Saved simulation output to:", self.output_filepath)

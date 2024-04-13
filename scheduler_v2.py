# from gurobipy import Model, GRB, tuplelist, quicksum
# from gurobipy import read as gurobi_read_model
# from gurobipy import Env as gpEnv
from scheduler_utils import PossibleStart, overlap_time_segments, trim_time_segments
import random
import math
import time


class SchedulerV2(object):
    def __init__(self, now, horizon, slice_size,
                 resources, proposals, requests, verbose=1, timelimit=0,
                 scheduler_type=None):
        self.now = now
        self.horizon = horizon
        self.slice_size = slice_size
        self.resources = resources
        self.proposals = proposals
        self.requests = requests
        self.verbose_level = verbose
        self.timelimit = timelimit
        self.scheduler_type = scheduler_type

        self.check_scheduler_type()

        print(self)
        print("Scheduling with {} solver...".format(self.scheduler_type))

        self.build_time = None
        self.solve_time = None
        self.interpret_time = None
        self.read_write_time = None
        self.objective_value = None
        self.scheduled_yik_index = None
        self.scheduled_requests = None
        self.scheduler_status = None

    
    def check_scheduler_type(self):
        print("check_scheduler_type - SchedulerV2 is just a template.")


    def log(self, text, log_level):
        if log_level <= self.verbose_level:
            print(text)


    def calculate_free_windows(self):
        for i, r in self.requests.items():
            fwd = {}
            for resource in r["windows"]:
                if resource in self.resources:
                    fwd[resource] = trim_time_segments(overlap_time_segments(self.resources[resource],
                                                          r["windows"][resource]),
                                                          self.now,
                                                          self.horizon)
                else:
                    fwd[resource] = []
            r["free_windows_dict"] = fwd


    def get_slices(self, intervals, resource, duration):
        slice_size = self.slice_size
        slices = []
        internal_starts = []
        for t in intervals: 
            start = int(math.floor(float(t["start"])/float(slice_size))*slice_size) # Start of the time_slice that this starts in
            internal_start = t["start"]                                             # Actual start of this observation window
            end_time = internal_start + duration                                    # End of this observation window

            while (t["end"] - start) >= duration:
                # Generate a range of slices that will be occupied for this start and duration
                # WARNING - HAVE TO GO BACK THROUGH REQUEST GENERATION AND MAKE SURE THESE ARE ALL INTS
                tmp = list(range(start, internal_start+duration, slice_size))
                slices.append(tmp)
                internal_starts.append(internal_start)
                start += slice_size                                # Moving on to the next potential start, so move the Start up to the next slice
                internal_start = start                             # As only the first potential start in a window will be internal, make the 
                                                                   # next Internal Start an external start
        # return slices, internal_starts
        ps_list = []
        idx = 0
        for w in slices:
            ps_list.append(PossibleStart(resource, w, internal_starts[idx], slice_size))
            idx += 1

        return ps_list


    def build_data_structures(self):
        yik = []
        aikt = {}

        for i, r in self.requests.items():
            yik_entries = []

            # Calculate request_priority from proposal_priority
            request_proposal = self.proposals[r["proposal"]]
            tac_priority = request_proposal["tac_priority"]
            random.seed(r["resID"]) # Set seed to allow semi-random perturbation
            perturbation_size = 0.01 # Copied from the LCO code
            ran = (1.0 - perturbation_size/2.0) + perturbation_size*random.random()

            # Simplified from LCO code for only NORMAL requests with no IPP.
            effective_priority = tac_priority * r["duration"] / 60.0 
            effective_priority = min(effective_priority, 32000.0)*ran
            self.requests[i]["effective_priority"] = effective_priority

            # Determine possible_starts, and sort
            possible_starts = []
            for resource in r["free_windows_dict"].keys():
                possible_starts.extend(self.get_slices(r["free_windows_dict"][resource], resource, r["duration"]))
            possible_starts.sort()
            self.requests[i]["possible_starts"] = possible_starts
        
            # Create Yik Entry for request
            w_idx = 0
            for ps in possible_starts:
                yik_idx = len(yik)
                yik_entries.append(yik_idx)
                scheduled = 0 # Option to set to 1 for a Warm Start would go here
                yik.append([r["resID"], w_idx, effective_priority, ps.resource, scheduled, ps])
                w_idx += 1
        
                # Create aikt entry for each possible start
                for s in ps.all_slice_starts:
                    slice_hash = f"resource_{ps.resource}_start_{repr(s)}_length_{repr(self.slice_size)}"
                    if slice_hash not in aikt:
                        aikt[slice_hash] = []
                    aikt[slice_hash].append(yik_idx)
                    
        self.yik = yik
        self.aikt = aikt


    def time_build_model(self):
        start_build = time.time()
        self.build_model()
        end_build = time.time()
        self.build_time = end_build - start_build


    def build_model(self):
        print("Scheduler_v2 is just a template. This function should be overwritten.")
        return


    def write_model(self, filename="test_model.mps"):
        print("Scheduler_v2 is just a template. This function should be overwritten.")
        return


    def load_model(self, filename="test_model.mps"):
        print("Scheduler_v2 is just a template. This function should be overwritten.")
        return


    def time_solve_model(self):
        start_solve = time.time()
        self.solve_model()
        end_solve = time.time()
        self.solve_time = end_solve - start_solve


    def solve_model(self):
        print("Scheduler_v2 is just a template. This function should be overwritten.")
        return


    def time_interpret_model(self):
        start_interpret = time.time()
        self.interpret_model()
        self.return_solution()
        end_interpret = time.time()
        self.interpret_time = end_interpret - start_interpret


    def interpret_model(self):
        print("Scheduler_v2 is just a template. This function should be overwritten.")
        return


    def return_solution(self):
        scheduled = []
        for i in self.schedule_yik_index:
            entry = self.yik[i]
            # Get relevant parameters
            rid = entry[0]
            resource = entry[3]
            start_time = entry[5].internal_start
            duration = self.requests[str(rid)]["duration"]
            end_time = start_time + duration
            priority = self.requests[str(rid)]["effective_priority"]

            # Add for saving
            request_dict = {
                "rID": rid,
                "resource": resource,
                "start": start_time,
                "end": end_time,
                "duration": duration,
                "priority": priority
            }

            scheduled.append(request_dict)

        if self.verbose_level >= 1:
            self.print_solution(scheduled)

        scheduled_dict = {}
        scheduled_dict["scheduled"] = {str(s["rID"]): s for s in scheduled}
        scheduled_dict["now"] = self.now
        self.scheduled_requests = scheduled_dict
        return scheduled_dict


    def run(self):
        self.calculate_free_windows()
        self.build_data_structures()
        self.time_build_model()
        self.time_solve_model()
        if self.scheduler_status == 1:
            self.time_interpret_model()
            return self.return_solution()


    def print_solution(self, scheduled):
        scheduled.sort(key=lambda x: x["start"])
        scheduled.sort(key=lambda x: x["resource"])

        print("---\nTotal Priority: {}\nScheduled Observations: {}".format(
                                            self.model.ObjVal, len(scheduled)))

        for s in scheduled:
            print("RequestID: {}, "
                  "Resource: {}, "
                  "S/E(D): {}/{}({}), "
                  "Priority: {}".format(s["rID"],
                                        s["resource"],
                                        s["start"],
                                        s["end"],
                                        s["duration"],
                                        s["priority"])
                  )
        print("---\n")


    def get_total_time(self):
        try:
            total_time = self.build_time + self.solve_time + self.interpret_time
            if self.read_write_time != None:
                total_time += self.read_write_time
        except TypeError:
            total_time = None
        return total_time

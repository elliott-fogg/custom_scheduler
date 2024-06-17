# from gurobipy import Model, GRB, tuplelist, quicksum
# from gurobipy import read as gurobi_read_model
# from gurobipy import Env as gpEnv
from scheduler_utils import PossibleStart, overlap_time_segments, trim_time_segments
import random
import math
import time
import datetime as dt
from time_intervals.intervals import Intervals


class SchedulerV2(object):
    def __init__(self, now, horizon, slice_size, telescopes, 
                 proposals, requests, verbose=1, timelimit=0,
                 previous_results=None):
        self.now = now
        self.horizon = horizon
        self.horizon_dt = now + dt.timedelta(seconds=horizon)
        self.slice_size = slice_size
        self.telescopes = telescopes
        self.proposals = proposals
        self.requests = requests
        self.verbose_level = verbose
        self.timelimit = timelimit

        self.build_time = None
        self.solve_time = None
        self.interpret_time = None
        self.read_write_time = None
        self.objective_value = None
        self.scheduled_yik_index = None
        self.scheduler_status = None

        self.previous_results = previous_results

        # print("NOW", now)
        # print("HORIZON", horizon)
        # print("SLICE_SIZE", slice_size)
        # print("TELESCOPES", telescopes)
        # print("PROPOSALS", proposals)
        # print("REQUESTS", requests)

    
    def check_scheduler_type(self):
        print("check_scheduler_type - SchedulerV2 is just a template.")


    def log(self, text, log_level):
        if log_level <= self.verbose_level:
            print(text)


    def apply_occupied_telescope_times(self):
        self.occupied_telescopes = {}
        for telescope, occupied_dt in self.telescopes.items():
            if occupied_dt != None:
                start_time = occupied_dt
            else:
                start_time = self.now
            self.occupied_telescopes[telescope] = Intervals([(start_time, self.horizon_dt)])


    def calculate_free_windows(self):
        for request_id, request in self.requests.items():
            free_windows = {}
            for telescope, windows in request["windows"].items():
                if telescope in self.occupied_telescopes:
                    free_windows[telescope] = self.occupied_telescopes[telescope].intersect([windows])
                else:
                    free_windows[telescope] = windows
            self.requests[request_id]["free_windows"] = free_windows


    def get_slices(self, intervals, resource, duration):
        slice_alignment = 0
        slice_length = self.slice_size
        slices = []
        internal_starts = []
        for t in intervals.toDictList():
            timestamp = int(t["time"].timestamp())
            if t["type"] == "start":
                if timestamp <= slice_alignment:
                    start = slice_alignment
                    internal_start = slice_alignment
                else:
                    # figure out start so it aligns with slice_alignment
                    start = int(slice_alignment + \
                        math.floor(float(timestamp - slice_alignment) / float(slice_length)) * \
                        slice_length)
                    # use the actual start as an internal start (may or may not align w/ slice_alignment)
                    internal_start = timestamp
            elif t['type'] == 'end':
                if timestamp < slice_alignment:
                    continue
                while timestamp - start >= duration:
                    tmp = range(start, internal_start + duration, slice_length)
                    slices.append(tmp)
                    internal_starts.append(internal_start)
                    start += slice_length
                    internal_start = start

        ps_list = []
        idx = 0
        for w in slices:
            ps_list.append(PossibleStart(resource, w, internal_starts[idx], slice_length))
            idx += 1

        return ps_list


    def calculate_effective_priority(self, request):
        proposal_id = request["proposal_id"]
        tac_priority = self.proposals[proposal_id]
        random.seed(request["id"])
        perturbation_size = 0.01
        ran = (1.0 - perturbation_size/2.0) + perturbation_size*random.random()

        effective_priority = tac_priority * request["total_duration"] / 60.0 * request["ipp_value"]
        effective_priority = min(effective_priority, 32000.0)*ran
        return effective_priority


    def build_data_structures(self):
        yik = []
        aikt = {}
        all_possible_starts = {}

        for request_id, request in self.requests.items():
            yik_entries = []
            possible_starts = []

            effective_priority = self.calculate_effective_priority(request)

            for resource in sorted(request["free_windows"].keys()):
                possible_starts.extend(self.get_slices(request["free_windows"][resource], resource, request["total_duration"]))

            possible_starts.sort()

            w_idx = 0
            for ps in possible_starts:
                yik_idx = len(yik)
                yik_entries.append(yik_idx)

                scheduled = 0

                if self.previous_results:
                    if request_id in self.previous_results:
                        if self.previous_results[request_id]["start"].timestamp() == ps.internal_start:
                            if self.previous_results[request_id]["resource"] == resource:
                                # print(f"Hotstarting: {request_id}, {resource}, {ps.internal_start}")
                                scheduled = 1
                
                # Ignore prioritizing by airmass for now

                priority = effective_priority + (0.1 / (w_idx + 1.0))
                yik.append([request["id"], w_idx, priority, ps.telescope, scheduled, ps])
                w_idx += 1

                # Build aikt
                for s in ps.all_slice_starts:
                    slice_hash = f"resource_{ps.telescope}_start_{repr(s)}_length{repr(self.slice_size)}"
                    if slice_hash not in aikt:
                        aikt[slice_hash] = [yik_idx]
                    else:
                        aikt[slice_hash].append(yik_idx)

                all_possible_starts[request_id] = possible_starts
                    
        self.yik = yik
        self.aikt = aikt
        self.all_possible_starts = all_possible_starts


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
            duration = self.requests[rid]["total_duration"]
            end_time = start_time + duration
            priority = entry[2]

            # Add for saving
            request_dict = {
                "rID": rid,
                "resource": resource,
                "start": dt.datetime.fromtimestamp(start_time),
                "end": dt.datetime.fromtimestamp(end_time),
                "duration": duration,
                "priority": priority
            }

            scheduled.append(request_dict)

        if self.verbose_level >= 1:
            self.print_solution(scheduled)

        scheduled_requests = {}
        for s in scheduled:
            rID = s["rID"]
            if rID in scheduled_requests:
                print("ERROR: DUPLICATE REQUEST SCHEDULED")
            scheduled_requests[rID] = s

        return {
            "scheduled": scheduled_requests,
            "now": self.now
        }

        # scheduled_dict["scheduled"] = {str(s["rID"]): s for s in scheduled}
        # scheduled_dict["now"] = self.now
        # self.scheduled_requests = scheduled_dict
        # return scheduled_dict


    def run(self):
        # self.calculate_free_windows()
        # print("Applying occupied telescopes...")
        self.apply_occupied_telescope_times()
        # print("Calculating free windows...")
        self.calculate_free_windows()
        # print("Building data structures...")
        self.build_data_structures()
        # print("Building model...")
        self.time_build_model()
        # print("Solving model...")
        self.time_solve_model()
        # print("Interpreting model...")

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

from gurobipy import Model, GRB, tuplelist, quicksum
from gurobipy import read as gurobi_read_model
import json
import random
import math


class Scheduler(object):
    def __init__(self, now, horizon, slice_size, 
                 resources, proposals, requests):
        self.now = now
        self.horizon = horizon          # Can we get rid of this?
        self.slice_size = slice_size
        self.resources = resources
        self.proposals = proposals
        self.requests = requests


    def calculate_free_windows(self):
        for i, r in self.requests.items():
            fwd = {}
            for resource in r["windows"]:
                if resource in self.resources:
                    fwd[resource] = overlap_time_segments(self.resources[resource],
                                                          r["windows"][resource],
                                                          self.now)
                else:
                    fwd[resource] = []
            r["free_windows_dict"] = fwd


    def get_slices(self, intervals, resource, duration):
        slice_size = self.slice_size
        slices = []
        internal_starts = []
        for t in intervals: 
            start = int(math.floor(float(t["start"])/float(slice_size))*slice_size) # Start of the time_slice that this starts in
            internal_start = t["start"]                                                 # Actual start of this observation window
            end_time = internal_start + duration                                        # End of this observation window

            while (t["end"] - start) >= duration:
                # Generate a range of slices that will be occupied for this start and duration
                tmp = list(range(start, internal_start+duration, slice_size))
                slices.append(tmp)
                internal_starts.append(internal_start)
                start += slice_size                                # Moving on to the next potential start, so move the Start up to the next slice
                internal_start = start                               # As only the first potential start in a window will be internal, make the 
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


    def build_model(self):
        yik = self.yik
        aikt = self.aikt

        m = Model("Test Schedule")

        requestLocations = tuplelist()
        scheduled_vars = []

        for r in yik:
            var = m.addVar(vtype=GRB.BINARY, name=str(r[0]))
            scheduled_vars.append(var)
            requestLocations.append((str(r[0]), r[1], r[2], r[3], var)) # resID, start_w_idx, priority, resource, isScheduled?
        m.update()

        # Constraint 4: Each request only scheduled once
        for rid in self.requests:
            match = requestLocations.select(rid, '*', '*', '*', '*', '*')
            nscheduled = quicksum([isScheduled for reqid, wnum, priority, resource, isScheduled in match])
            m.addConstr(nscheduled <= 1, f'one_per_reqid_constraint_{rid}')
        m.update()

        # Constraint 3: Each timeslice should only have one request in it
        for s in aikt.keys():
            match = tuplelist()
            for timeslice in aikt[s]:
                match.append(requestLocations[timeslice])
            nscheduled = quicksum(isScheduled for reqid, winidx, priority, resource, isScheduled in match)
            m.addConstr(nscheduled <= 1, f"one_per_slice_constrain_{s}")

        objective = quicksum([isScheduled * (priority + 0.1/(winidx+1.0)) for req, winidx, priority, resource, isScheduled in requestLocations])

        m.setObjective(objective)
        m.modelSense = GRB.MAXIMIZE

        # Implement a timelimit? (Do I actually want to do this?)
        timelimit = 0 # NOTE: Hardcode out for now.
        if timelimit > 0:
            m.params.timeLimit = timelimit

        # Set the tolerance of the solution
        m.params.MIPGap = 0.01

        # Set the Method of solving the root relaxation of the MIPs model to concurrent
        m.params.Method = 3

        m.update()

        self.model = m
        print("Model constructed")


    def write_model(self, filename="test_model.mps"):
        self.model.write(filename)
        print(f"Model written to file: {filename}")


    def load_model(filename="test_model.mps"):
        self.model = gurobi_read_model(filename)


    def solve_model(self):
        self.model.setParam("OutputFlag", False) # Disable output from model?
        self.model.optimize()
        if self.model.Status != GRB.OPTIMAL:
            print(f"Model Status not optimal: {self.model.Status}")
            return
        self.solution = self.model.getAttr("X")
        print("Model optimized")


    def interpret_solution(self):
        scheduled = []

        for i in range(len(self.solution)):
            if self.solution[i] == 1:
                # print(i, self.yik[i])
                scheduled.append(self.yik[i]) # ID, start_w_idx, priority, resource, isScheduled(dud), possible_start

        scheduled.sort(key=lambda x: x[5]) # Sort by Starting Window
        scheduled.sort(key=lambda x: x[3]) # Sort by Resource

        print("\nTotal Priority: {}\nScheduled Observations: {}\n---".format(self.model.ObjVal, len(scheduled)))

        for i in range(len(scheduled)):
            s = scheduled[i]

            rid = s[0]
            resource = s[3]

            r = self.requests[str(rid)]
            start_time = s[5].internal_start
            duration = r["duration"]
            end_time = start_time + duration

            print("Request {}: Resource={}, S/E(D)={}/{}({}), Priority = {}".format(
                    rid, resource, start_time, end_time, duration, r["effective_priority"]))

        print("---\n")


    def return_solution(self):
        # Return solution in a hot-start-able format
        pass
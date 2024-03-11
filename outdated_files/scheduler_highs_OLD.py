import json
import random
import math
import highspy
import time
import pulp as pl

# from scheduler_utils import PossibleStart, TimeSegment, overlap_time_segments

class SchedulerHighs(object):
    def __init__(self, now, horizon, slice_size, resources,
                 proposals, requests, verbose=1, timelimit=0, scheduler_type=None):
        self.now = now
        self.horizon = horizon
        self.slice_size = slice_size
        self.resources = resources
        self.proposals = proposals
        self.requests = requests
        self.verbose_level = verbose


    def build_model(self):
        yik = self.yik
        aikt = self.aikt

        m = Model("Test Schedule", env=self.env)

        requestLocations = tuplelist()
        scheduled_vars = []

        for i in range(len(yik)):
            r = yik[i]
            var = h.addVar(lb=0, ub=1)
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
        self.log("Model constructed", 1)


    # def build_model_pulp(self):
    #     yik = self.yik
    #     aikt = self.aikt

    #     m = pl.LpProblem("Test Schedule", pl.LpMaximize)

    #     requestLocations = tuplelist()
    #     scheduled_vars = []

    #     # Construct the isScheduled binary variables for every possible start for every request, in the Yik
    #     for yik_id in range(len(yik)):
    #         r = yik[yik_id]
    #         var = pl.LpVariable(name=str(yik_id), cat="Binary")
    #         scheduled_vars.append(var)
    #         requestLocations.append((str(r[0]), r[1], r[2], r[3], var)) # resID, start_w_idx, priority, resource, isScheduled?

    #     # Constraint 4: Each request only scheduled once
    #     for rid in self.requests:
    #         match = requestLocations.select(rid, '*', '*', '*', '*', '*')
    #         nscheduled = pl.LpAffineExpression({isScheduled: 1 for reqid, wnum, priority, resource, isScheduled in match})
    #         constraint = pl.LpConstraint(nscheduled, -1, f"one_per_reqid_constraint_{rid}", 1)
    #         m.addConstraint(constraint)

    #     # Constraint 3: Each timeslice should only have one request in it
    #     for s in aikt.keys():
    #         match = tuplelist()
    #         for timeslice in aikt[s]:
    #             match.append(requestLocations[timeslice])
    #         nscheduled = pl.LpAffineExpression({isScheduled: 1 for reqid, winidx, priority, resource, isScheduled in match})
    #         constraint = pl.LpConstraint(nscheduled, -1, f"one_per_slice_constraint_{s}", 1)
    #         m.addConstraint(constraint)

    #     objective = pl.LpAffineExpression({isScheduled: (priority + 0.1/(winidx+1.0)) for req, winidx, priority, resource, isScheduled in requestLocations})

    #     m.setObjective(objective)

    #     # Set the tolerance of the solution
    #     # m.params.MIPGap = 0.01

    #     # Set the Method of solving the root relaxation of the MIPs model to concurrent
    #     # m.params.Method = 3

    #     # m.update()

    #     self.model = m
    #     self.log("Model constructed", 1)


    def write_model(self, filename="test_model.mps"):
        self.model.write(filename)
        self.log(f"Model written to file: {filename}", 1)


    def load_model(self, filename="test_model.mps"):
        self.model = gurobi_read_model(filename, env=self.env)


    def solve_model(self):
        # self.model.setParam("OutputFlag", False) # Disable output from model?
        t1 = time.time()
        self.model.optimize()
        t2 = time.time()

        self.gurobi_solve_time = t2 - t1

        if self.model.Status != GRB.OPTIMAL:
            print(f"Model Status not optimal: {self.model.Status}")
            return
        self.solution = self.model.getAttr("X")
        self.log("Model optimized", 1)
        self.log(f"YiK Size: {len(self.yik)}", 1) # Can't remember why we have this


    def return_solution(self, display=False):
        scheduled = []
        for i in range(len(self.solution)):
            if self.solution[i] == 1:
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
        return scheduled_dict


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


    def solve_with_highs(self):
        self.write_model("_temp.mps")
        h = highspy.Highs()
        h.readModel("_temp.mps")
        t1 = time.time()
        h.run()
        t2 = time.time()

        self.highs_solve_time = t2 - t1

        solution = h.getSolution()
        info = h.getInfo()
        optimal_objective = info.objective_function_value

        scheduled = self.return_solution(solution.col_value)

        # h_scheduled = []
        # rv = solution.row_value
        # for i in range(len(rv)):
        #     if rv[i] > 0.5:
        #         const_name = h.getRowName(i)[1]
        #         if "one_per_reqid_constraint_" in const_name:
        #             h_scheduled.append(const_name.replace("one_per_reqid_constraint_", ""))

        return (optimal_objective, scheduled)

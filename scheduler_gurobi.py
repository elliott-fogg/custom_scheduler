from scheduler_v2 import Scheduler
from gurobipy import Model, GRB, tuplelist, quicksum
from gurobipy import read as gurobi_read_model
from gurobipy import Env as gpEnv
import json
import random
import math
import time
from scheduler_utils import PossibleStart, TimeSegment, overlap_time_segments

class Scheduler_Gurobi(Scheduler):
    def __init__(self, now, horizon, slice_size, 
                 resources, proposals, requests, verbose=1):
        super().__init__(now, horizon, slice_size, resources, proposals,
                         requests, verbose)

        self.env = gpEnv(empty=True)
        self.env.setParam("OutputFlag", 0)
        self.env.start()


    def build_model(self):
        yik = self.yik
        aikt = self.aikt

        m = Model("Test Schedule", env=self.env)

        requestLocations = tuplelist()
        scheduled_vars = []

        for i in range(len(yik)):
            r = yik[i]
            var = m.addVar(vtype=GRB.BINARY, name="isSched_"+str(i))
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


    def write_model(self, filename="test_model.mps"):
        self.model.write(filename)
        self.log(f"Model written to file: {filename}", 1)


    def load_model(self, filename="test_model.mps"):
        self.model = gurobi_read_model(filename, env=self.env)


    def solve_model(self):
        # self.model.setParam("OutputFlag", False) # Disable output from model?
        start_time = time.time()
        self.model.optimize()
        end_time = time.time()
        self.solve_time = end_time - start_time

        if self.model.Status != GRB.OPTIMAL:
            print(f"Model Status not optimal: {self.model.Status}")
            return

        self.log("Model optimized", 1)

        # Store the Objective value
        self.objective_value = self.model.ObjVal

        # Store which Yik_index variables have been scheduled
        solution = self.model.getAttr("X")
        self.schedule_yik_index = [i for i in range(len(solution)) if solution[i] == 1]
        
from scheduler_v2 import Scheduler
import pulp as pl
from gurobipy import tuplelist
import json
import random
import math
import time
from scheduler_utils import PossibleStart, TimeSegment, overlap_time_segments

class Scheduler_Pulp(object):
    def __init__(self, now, horizon, slice_size, 
                 resources, proposals, requests, verbose=1):
        super().__init__(now, horizon, slice_size, resources, proposals,
                         requests, verbose)


    def build_model(self):
        yik = self.yik
        aikt = self.aikt

        m = pl.LpProblem("test_schedule", pl.LpMaximize)

        requestLocations = tuplelist()
        scheduled_vars = []

        # Construct the isScheduled binary variables for every possible start for every request, in the Yik
        for yik_id in range(len(yik)):
            r = yik[yik_id]
            var = pl.LpVariable(name=str(yik_id), cat="Binary")
            scheduled_vars.append(var)
            requestLocations.append((str(r[0]), r[1], r[2], r[3], var)) # resID, start_w_idx, priority, resource, isScheduled?

        # Constraint 4: Each request only scheduled once
        for rid in self.requests:
            match = requestLocations.select(rid, '*', '*', '*', '*', '*')
            nscheduled = pl.LpAffineExpression({isScheduled: 1 for reqid, wnum, priority, resource, isScheduled in match})
            constraint = pl.LpConstraint(nscheduled, -1, f"one_per_reqid_constraint_{rid}", 1)
            m.addConstraint(constraint)

        # Constraint 3: Each timeslice should only have one request in it
        for s in aikt.keys():
            match = tuplelist()
            for timeslice in aikt[s]:
                match.append(requestLocations[timeslice])
            nscheduled = pl.LpAffineExpression({isScheduled: 1 for reqid, winidx, priority, resource, isScheduled in match})
            constraint = pl.LpConstraint(nscheduled, -1, f"one_per_slice_constraint_{s}", 1)
            m.addConstraint(constraint)

        objective = pl.LpAffineExpression({isScheduled: (priority + 0.1/(winidx+1.0)) for req, winidx, priority, resource, isScheduled in requestLocations})

        m.setObjective(objective)


        self.model = m
        self.log("Model constructed", 1)


    def write_model(self, filename="test_model.mps"):
        self.model.writeMPS(filename)
        self.log(f"Model written to file: {filename}", 1)


    def load_model(self, filename="test_model.mps"):
        var_names, self.model = pl.LpProblem.fromMPS(filename, pl.LpMaximize)


    def solve_model(self):
        # self.model.setParam("OutputFlag", False) # Disable output from model?
        start_time = time.time()
        status = self.model.solve()
        end_time = time.time()
		self.solve_time = end_time - start_time

        if status != 1:
            print(f"Model Status not optimal: {status}")
            return
        self.log("Model optimized", 1)

        # Store the Objective value
        self.objective_value = self.model.objective.value()

        # Store which Yik_index variables have been scheduled
        variables = self.model.variables()
        self.schedule_yik_index = [i for i in range(len(variables)) if variables[i].value() == 1]

from scheduler_v2 import Scheduler
from ortools.sat.python import cp_model
from gurobipy import tuplelist
import json
import random
import math
import time
from scheduler_utils import PossibleStart, TimeSegment, overlap_time_segments


class Scheduler_CPSAT(Scheduler):
    def __init__(self, now, horizon, slice_size, 
                 resources, proposals, requests, verbose=1):
    	super().__init__(now, horizon, slice_size, resources, proposals, 
    					 requests, verbose)


    def build_model(self):
        yik = self.yik
        aikt = self.aikt

        model = cp_model.CpModel()

        requestLocations = tuplelist()
        scheduled_vars = []

        # Construct the isScheduled binary variables for every possible start for every request, in the Yik
        for yik_id in range(len(yik)):
            r = yik[yik_id]
            var = model.NewBoolVar(str(yik_id))
            scheduled_vars.append(var)
            requestLocations.append((str(r[0]), r[1], r[2], r[3], var)) # resID, start_w_idx, priority, resource, isScheduled?

        # Constraint 4: Each request only scheduled once
        for rid in self.requests:
            match = requestLocations.select(rid, '*', '*', '*', '*', '*')
            nscheduled = [isScheduled for reqid, wnum, priority, resource, isScheduled in match]
            model.Add(sum(nscheduled) <= 1)

        # Constraint 3: Each timeslice should only have one request in it
        for s in aikt.keys():
            match = tuplelist()
            for timeslice in aikt[s]:
                match.append(requestLocations[timeslice])

            nscheduled = [isScheduled for reqid, wnum, priority, resource, isScheduled in match]
            model.Add(sum(nscheduled) <= 1)

        model.Maximize(sum([isScheduled * (priority + 0.1/(winidx+1.0)) for req, winidx, priority, resource, isScheduled in requestLocations]))

        self.scheduled_vars = scheduled_vars
        self.model = model
        self.log("Model constructed", 1)


    def write_model(self, filename="test_model.mps"):
    	print("Write_Model Failed: CP_SAT cannot save models to .MPS format.")


    def load_model(self, filename="test_model.mps"):
    	print("Load_Model Failed: CP_SAT cannot load .MPS models.")


    def solve_model(self):
    	# Solve the model, and time it
    	solver = cp_model.CpSolver()
    	start_time = time.time()
    	status = solver.Solve(self.model)
    	end_time = time.time()
    	self.solve_time = end_time - start_time

    	if status != cp_model.OPTIMAL:
    		print(f"Model Status not optimal: {status}")
    		return

    	# Store the Objective value
    	self.objective_value = solver.ObjectiveValue()

    	# Store which Yik_index variables have been scheduled
    	self.schedule_yik_index = [i for i in range(len(self.scheduled_vars)) if solver.Value(self.scheduled_vars[i]) == 1]

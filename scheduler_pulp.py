from scheduler_v2 import SchedulerV2
import pulp as pl
from gurobipy import tuplelist

class SchedulerPulp(SchedulerV2):
    def __init__(self, now, horizon, slice_size, 
                 resources, proposals, requests, verbose=0,
                 timelimit=0, scheduler_type=None):

        super().__init__(now, horizon, slice_size, resources, proposals,
                         requests, verbose, timelimit, scheduler_type)


    def check_scheduler_type(self):
        if self.scheduler_type not in ("cbc", "scip", "gurobi_pulp", "gurobi_pulp_cmd"):
            print("ERROR: Mismatched scheduler_type: '{}'. Currently using PuLP Scheduler.".format(scheduler_type))


    def build_model(self):
        yik = self.yik
        aikt = self.aikt

        m = pl.LpProblem("test_schedule", pl.LpMaximize)

        requestLocations = tuplelist()
        scheduled_vars = []

        # Construct the isScheduled binary variables for every possible start for every request, in the Yik
        for yik_id in range(len(yik)):
            r = yik[yik_id]
            var = pl.LpVariable(name="BIN_"+str(yik_id), cat="Binary")
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

        self.scheduled_vars = scheduled_vars

        self.model = m
        self.log("Model constructed", 1)


    def write_model(self, filename="test_model.mps"):
        self.model.writeMPS(filename)
        self.log(f"Model written to file: {filename}", 1)


    def load_model(self, filename="test_model.mps"):
        var_names, self.model = pl.LpProblem.fromMPS(filename, pl.LpMaximize)


    def getSolver(self):
        solvers_dict = {
            "cbc": "PULP_CBC_CMD",
            "scip": "SCIP_CMD",
            "highs": "HiGHS_CMD",
            "gurobi_pulp": "GUROBI",
            "gurobi_pulp_cmd": "GUROBI_CMD"
        }
        solver_name = solvers_dict[self.scheduler_type]
        if self.timelimit > 0:
            solver = pl.getSolver(solver_name, timeLimit=self.timelimit)
        else:
            # No time limit
            solver = pl.getSolver(solver_name)
        return solver


    def solve_model(self):
        solver = self.getSolver()
        self.scheduler_status = self.model.solve(solver)
        if self.scheduler_status != 1:
            print(f"Model Status not optimal: {self.scheduler_status}")
            return


    def interpret_model(self):
        self.objective_value = self.model.objective.value()

        self.schedule_yik_index = []
        for i in range(len(self.yik)):
            if self.scheduled_vars[i].value() == 1:
                self.schedule_yik_index.append(i)

from scheduler_v2 import SchedulerV2
from gurobipy import Model, GRB, tuplelist, quicksum
from gurobipy import read as gurobi_read_model
from gurobipy import Env as gpEnv

class SchedulerGurobi(SchedulerV2):
    def __init__(self, now, horizon, slice_size, 
                 resources, proposals, requests, verbose=1,
                 timelimit=0, scheduler_type=None):

        super().__init__(now, horizon, slice_size, resources, proposals,
            requests, verbose, timelimit, scheduler_type)

        self.env = gpEnv(empty=True)
        self.env.setParam("OutputFlag", 0)
        self.env.start()


    def check_scheduler_type(self):
        if self.scheduler_type != "gurobi":
            print("ERROR: Mismatched scheduler_type. '{}' should be 'gurobi'.".format(scheduler_type))


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

        # If specified, set a time limit
        if self.timelimit > 0:
            model.setParam('TimeLimit', timelimit)

        m.update()

        self.model = m
        self.log("Model constructed", 1)


    def solve_model(self):
        self.model.optimize()
        if self.model.Status != GRB.OPTIMAL:
            print("Model Status not optimal:", self.model.Status)
            return
        self.log("Model optimized", 1)


    def interpret_model(self):
        # Store the Objective Value
        self.objective_value = self.model.ObjVal

        # Store which Yik_index variables have been scheduled
        solution = self.model.getAttr('X')
        self.schedule_yik_index = []
        for i in range(len(self.yik)):
            var_index = self.model.getVarByName("isSched_{}".format(i)).index
            if solution[var_index] == 1:
                self.schedule_yik_index.append(i)


    def write_model(self, filename="test_model.mps"):
        self.model.write(filename)
        self.log(f"Model written to file: {filename}", 1)


    def load_model(self, filename="test_model.mps"):
        self.model = gurobi_read_model(filename, env=self.env)
        
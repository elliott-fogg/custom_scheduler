from scheduler_v2 import SchedulerV2
from gurobipy import Model, GRB, tuplelist, quicksum
from gurobipy import read as gurobi_read_model
from gurobipy import Env as gpEnv
from collections import defaultdict

class SchedulerGurobi(SchedulerV2):
    def __init__(self, now, horizon, slice_size, 
                 telescopes, proposals, requests, verbose=1,
                 timelimit=0, previous_results=None):

        super().__init__(now, horizon, slice_size, telescopes, proposals,
            requests, verbose, timelimit, previous_results)

        self.env = gpEnv(empty=True)
        self.env.setParam("OutputFlag", 0)
        self.env.start()


    def build_model(self):
        yik = self.yik
        aikt = self.aikt

        m = Model("Test Schedule", env=self.env)

        requestLocations = tuplelist()
        scheduled_vars = []
        vars_by_req_id = defaultdict(list)

        # Decision Variable must be binary
        for i in range(len(yik)):
            r = yik[i]
            var = m.addVar(vtype=GRB.BINARY, name="isSched_"+str(i))
            var.start = r[4]
            scheduled_vars.append(var)
            requestLocations.append((r[0], r[1], r[2], r[3], var)) # resID, start_w_idx, priority, resource, isScheduled?
            vars_by_req_id[r[0]].append(([r[0], r[1], r[2], r[3], var]))
        m.update()

        # Constraint 3: No more than 1 request should be scheduled in each (timeslice, resource)
        # self.aikt.keys() indexes the requests that occupy each (timeslice, resource)
        for s in sorted(self.aikt.keys()):
            match = []
            for timeslice in self.aikt[s]:
                match.append(requestLocations[timeslice])
            nscheduled1 = quicksum([isScheduled for reqid, wnum, priority, resource, isScheduled in match])
            m.addConstr(nscheduled1 <= 1, f'one_per_slice_constraint_{s}')
        m.update()

        # Constraint 2: No request should be scheduled more than once
        for reqid in self.requests:
            match = vars_by_req_id[reqid]
            nscheduled2 = quicksum([isScheduled for reqid, wnum, priority, resource, isScheduled in match])
            m.addConstr(nscheduled2 <= 1, f'one_per_reqid_constraint_{reqid}')
        m.update()

        objective = quicksum([isScheduled*priority for req, winidx, priority, resource, isScheduled in requestLocations])

        m.setObjective(objective)
        m.modelSense = GRB.MAXIMIZE

        # # Implement a timelimit? (Do I actually want to do this?)
        # timelimit = 0 # NOTE: Hardcode out for now.
        # if timelimit > 0:
        #     m.params.timeLimit = timelimit

        # Set the tolerance of the solution
        m.params.MIPGap = 0.01

        # Set the Method of solving the root relaxation of the MIPs model to concurrent
        m.params.Method = 3

        # If specified, set a time limit
        if self.timelimit > 0:
            m.setParam('TimeLimit', timelimit)

        m.update()

        self.model = m
        self.requestLocations = requestLocations
        self.log("Model constructed", 1)


    def solve_model(self):
        self.model.optimize()
        if self.model.Status != GRB.OPTIMAL:
            print("Model Status not optimal:", self.model.Status)
            return
        self.log("Model optimized", 1)
        return True


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
        
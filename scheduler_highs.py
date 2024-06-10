from scheduler_gurobi import SchedulerGurobi
import highspy
import time

class SchedulerHighs(SchedulerGurobi):
    def __init__(self, now, horizon, slice_size, 
                 telescopes, proposals, requests, verbose=1,
                 timelimit=0):

        super().__init__(now, horizon, slice_size, telescopes, proposals,
            requests, verbose, timelimit)


    def check_scheduler_type(self):
        if self.scheduler_type != "highs":
            print("ERROR: Mismatched scheduler_type: '{}'. Currently using HiGHS Scheduler.".format(scheduler_type))


    def time_solve_model(self):
    	start_read_write = time.time()
    	self.write_model("highs_temp.mps")
    	self.h = highspy.Highs()
    	self.h.readModel("highs_temp.mps")
    	end_read_write = time.time()
    	self.read_write_time = end_read_write - start_read_write

    	start_solve = time.time()
    	self.solve_model()
    	end_solve = time.time()
    	self.solve_time = end_solve - start_solve


    def solve_model(self):
        if self.timelimit > 0:
            self.h.setOptionValue('time_limit', self.timelimit)
        self.h.run()


    def interpret_model(self):
    	solution = self.h.getSolution().col_value
    	info = self.h.getInfo()
    	self.objective_value = info.objective_function_value

    	self.schedule_yik_index = [i for i in range(len(self.yik)) if solution[i]==1]
        
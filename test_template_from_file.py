from ScheduleSimulator import SchedulerSimulation
# from generate_requests_v3 import RequestGeneratorV2, RequestInjection
from copy import deepcopy
from collections import defaultdict
import numpy as np
import json
import time
import datetime as dt
import os
import random
import pprint
import re
import pandas as pd


class AltPerformanceTest(object):
    def __init__(self, input_folder, output_folder, file_identifier, scheduler_type="gurobi", timelimit=0):
        self.input_folder = input_folder
        self.output_dir = os.path.join(output_folder, file_identifier)
        os.makedirs(self.output_dir, exist_ok=True)
        self.timelimit = timelimit

        self.scheduler_type = scheduler_type

        all_input_files = self.gather_input_files(file_identifier)
        self.input_files = self.check_input_files(all_input_files)

        self.total_iterations = len(self.input_files)
        self.count = 0


    def gather_input_files(self, file_identifier):
        all_file_list = os.listdir(self.input_folder)
        file_list = [f for f in all_file_list if file_identifier in f]
        return file_list


    def generate_output_filename(self, input_filename):
        return input_filename


    def check_input_files(self, input_file_list):
        completed_files = os.listdir(self.output_dir)

        input_files = []
        for f in input_file_list:
            output_filename = self.generate_output_filename(f)
            if output_filename in completed_files:
                print("File completed:", output_filename)
            else:
                input_files.append(f)
        print(len(input_files), " files remaining.")
        return input_files


    def test_loop(self, input_file):
        input_filepath = os.path.join(self.input_folder, input_file)
        input_data = json.load(open(input_filepath, "r"))
        sim = SchedulerSimulation(data=input_data, scheduler_type=self.scheduler_type, timelimit=self.timelimit)

        next_events = sim.get_next_events()
        sim.process_event_group(next_events)
        scheduler_data = sim.get_scheduler_info()
        scheduler = sim.Scheduler(now=scheduler_data["now"], 
                    horizon=scheduler_data["horizon"],
                    slice_size=scheduler_data["slice_size"],
                    resources=scheduler_data["resources"],
                    proposals=scheduler_data["proposals"],
                    requests=scheduler_data["requests"],
                    timelimit=self.timelimit,
                    scheduler_type=self.scheduler_type
        )

        scheduler.run()

        output = {
            "build": scheduler.build_time,
            "solve": scheduler.solve_time,
            "interpret": scheduler.interpret_time,
            "total_time": scheduler.get_total_time(),
            "scheduler_type": self.scheduler_type,
            "input_file": input_file,
            "input_folder": self.input_folder
        }
        return json.dumps(output)


    def run(self):
        for filename in self.input_files:
            self.write(filename)
            output = self.test_loop(filename)
            self.save_results(output, filename)
            # output_filepath = os.path.join(self.output_dir, filename)
            # self.save_results()
            # with open(output_filepath, "w") as f:
            #     f.write("{}".format(output))
        print("\nTest Complete.")


    def save_results(self, output_data, filename):            
        output_filepath = os.path.join(self.output_dir, filename)

        with open(output_filepath, "w") as f:
            f.write("{}".format(output_data))


    def write(self, filename):
        self.count += 1
        print("{} / {} - {} - {}".format(self.count, self.total_iterations, filename, 
                                         dt.datetime.now().strftime("%H:%M:%S %d-%m-%Y")))


class SchedulerPerformanceTest(object):
    def __init__(self, input_folder, output_folder, file_identifier, scheduler_type="gurobi"):
        self.input_folder = input_folder
        self.output_dir = os.path.join(output_folder, file_identifier)
        os.makedirs(self.output_dir, exist_ok=True)

        self.scheduler_type = scheduler_type

        all_input_files = self.gather_input_files(file_identifier)
        self.input_files = self.check_input_files(all_input_files)

        self.total_iterations = len(self.input_files)
        self.count = 0


    def gather_input_files(self, file_identifier):
        all_file_list = os.listdir(self.input_folder)
        file_list = [f for f in all_file_list if file_identifier in f]
        return file_list


    def generate_output_filename(self, input_filename):
        return input_filename


    def check_input_files(self, input_file_list):
        completed_files = os.listdir(self.output_dir)

        input_files = []
        for f in input_file_list:
            output_filename = self.generate_output_filename(f)
            if output_filename in completed_files:
                print("File completed:", output_filename)
            else:
                input_files.append(f)
        print(len(input_files), " files remaining.")
        return input_files


    def test_loop(self, input_file):
        input_filepath = os.path.join(self.input_folder, input_file)
        input_data = json.load(open(input_filepath, "r"))
        sim = SchedulerSimulation(data=input_data)
        sim.run_simulation()
        output = {
            "build": sim.last_sched.build_time,
            "solve": sim.last_sched.solve_time,
            "interpret": sim.last_sched.interpret_time,
            "total_time": sim.last_sched.get_total_time(),
            "scheduler_type": self.scheduler_type
        }
        return json.dumps(output)


    def run(self):
        for filename in self.input_files:
            self.write(filename)
            output = self.test_loop(filename)
            self.save_results(output, filename)
            # output_filepath = os.path.join(self.output_dir, filename)
            # self.save_results()
            # with open(output_filepath, "w") as f:
            #     f.write("{}".format(output))
        print("\nTest Complete.")


    def save_results(self, output_data, filename):            
        output_filepath = os.path.join(self.output_dir, filename)

        with open(output_filepath, "w") as f:
            f.write("{}".format(output_data))


    def write(self, filename):
        self.count += 1
        print("{} / {} - {} - {}".format(self.count, self.total_iterations, filename, 
                                         dt.datetime.now().strftime("%H:%M:%S %d-%m-%Y")))
        

class SolverComparisonTest(AltPerformanceTest):
    def __init__(self, input_folder, output_folder, 
                 file_identifier, scheduler_type, timelimit=0):
        super().__init__(input_folder, output_folder, file_identifier, scheduler_type, timelimit)


    def generate_output_filename(self, input_filename):
        filename_split = input_filename.split(".")
        filename_split[0] += "_{}".format(self.scheduler_type)
        new_filename = ".".join(filename_split)
        return new_filename

    def save_results(self, output_data, filename):
        # Append Scheduler Type to filename
        output_filepath = os.path.join(self.output_dir, 
                                       self.generate_output_filename(filename))


        # filename_split = filename.split(".")
        # filename_split[0] += "_{}".format(self.scheduler_type)
        # new_filename = ".".join(filename_split)
        # print(new_filename)
        # output_filepath = os.path.join(self.output_dir, new_filename)
        
        with open(output_filepath, "w") as f:
            f.write("{}".format(output_data))


class AltPerformanceTestParser(object):
    def __init__(self, output_folder, file_identifier):
        self.output_dir = os.path.join(output_folder, file_identifier)
        self.output = []
        self.gather_data()

    def parse_file_name(self, filename):
        fn = filename.split("_")
        file_info = {}
        for i in range(1, len(fn)):
            match = re.match('(\d+)(\w*)', fn[i])
            if match != None:
                column = match.group(2)
                value = match.group(1)
                if column == "":
                    column = "iteration"
                file_info[column] = value
        return file_info

    def gather_data(self):
        output_file_list = os.listdir(self.output_dir)

        for filename in output_file_list:
            with open(os.path.join(self.output_dir, filename)) as f:
                data = float(f.read())
            file_info = self.parse_file_name(filename)
            file_info["data"] = data
            self.output.append(file_info)

    def get_df(self):
        df = pd.DataFrame(self.output)
        id_vars = [c for c in df.columns if c not in ("iteration", "data")]
        value_vars = ["data"]






#####################

class AltVariableWindowsTest(AltPerformanceTest):
    def __init__(self, input_folder, output_folder, file_identifier,
                 window_increase_factor, test_fraction):
        super().__init__(input_folder, output_folder, file_identifier)
        self.window_increase_factor = window_increase_factor
        self.test_fraction = test_fraction
        self.total_iterations = len(self.input_files)


    def sample_requests(self, all_requests_base, test_fraction):
        # TO ADD: a way of ensuring that we are only taking the first half of observations
        # - Split the observations up into those that are originally in the scheduler
        #   (i.e. those that are added in the upfront bulk request injection)
        #   and those that are injected later.
        #   Only test on those that are in the upfront bulk injection?
        sample_number = round(test_fraction * len(all_requests_base))
        sampled_requests = random.sample(list(all_requests_base.keys()), k=sample_number)
        return sampled_requests


    def modify_availability_window(self, request_data, window_increase):
        wgroup = request_data["windows"]
        for resource, windows in wgroup.items():
            new_windows = []
            for w in windows:
                new_windows.append(extend_window(w, window_increase))
            wgroup[resource] = new_windows
        request_data["windows"] = wgroup
        return request_data


    def variable_window_test(self, input_data, modified_requests):
        sim = SchedulerSimulation(data=input_data)
        # print("Running Simulation...")
        sim.run_simulation()
        current_results = set(sim.completed_requests.keys())
        return current_results


    def test_loop(self, input_file):
        # Generate Sim
        # Get all requests as a baseline
        # Run simulation without altering anything
        # Record resulting schedule
        # Modify a request
        # Run simulation with modified request
        # Record schedule from modified requests
        # Check to see if there has been a change

        input_filepath = os.path.join(self.input_folder, input_file)
        input_data = json.load(open(input_filepath, "r"))

        # Load all the requests into a SchedulerSimulation instance
        sim = SchedulerSimulation(data=input_data)

        # Make a copy of all the requests present in the simulation,
        # to be able to reliably alter them.
        all_requests_base = deepcopy(sim.all_requests)

        # Run the simulation with no modifications, to get baseline results
        sim.run_simulation()
        base_results = set(sim.completed_requests.keys())

        # Determine the sample of requests to test over
        requests_sample = self.sample_requests(all_requests_base, self.test_fraction)

        # Run the experiment by iterating over the sampled requests
        test_results = {}

        total_simulation_count = len(requests_sample)
        simulation_count = 0

        for request_number in requests_sample:
            simulation_count += 1
            self.mini_write(simulation_count, total_simulation_count)
            modified_requests = deepcopy(all_requests_base)
            modified_requests[request_number] = self.modify_availability_window(modified_requests[request_number],
                                                                                self.window_increase_factor)

            test_results[request_number] = self.variable_window_test(input_data=input_data,
                                                                        modified_requests=modified_requests)
        
        output = {
            "results": test_results,
            "base_requests": all_requests_base,
            "proposals": sim.proposals,
            "base_results": base_results
        }

        return output



    def mini_write(self, current_simulation, total_simulations):
        if current_simulation != total_simulations:
            ending = ""
        else:
            ending = "\n"
        print("\rRunning Simulation {} / {}...".format(current_simulation, total_simulations), end=ending)


    def save_results(self, output_data, filename):            
        output_filepath = os.path.join(self.output_dir, filename)
        # print(output_data)

        transformed_output_data = self.recursive_transform_to_json(output_data)
        json_data = json.dumps(transformed_output_data)
        with open(output_filepath, "w") as f:
            f.write("{}".format(json_data))


    def recursive_transform_to_json(self, output_data):
        if type(output_data) in (set, list):
            return [self.recursive_transform_to_json(x) for x in output_data]
        elif type(output_data) == dict:
            return {k: self.recursive_transform_to_json(v) for k, v in output_data.items()}
        else:
            return output_data


#####






    # def variable_windows_test(input_data, all_requests_base, window_increase, test_fraction):
    #     test_results = []

    #     print(all_requests_base.keys())


    #     print(sample_requests)

    #     for i in range(len(sample_requests)):
    #         if i % 1 == 0:
    #             print("\rRequest: {} / {}".format(i, len(all_requests_base)), end="")

    #         # Initialize a new instance of the scheduler
    #         sim = SchedulerSimulation(data=input_data)

    #         # Modify the specified request
    #         modified_requests = deepcopy(all_requests_base)
    #         modified_requests[str(i)] = self.modify_availability_window(request, window_increase)

    #         # Substitute in the modified requests
    #         sim.all_requests_base = modified_requests

    #         # Run the simulation
    #         sim.run_simulation()

    #         # Get the scheduled requests from this test
    #         test_results.append()
    #         current_results = set(sim.completed_requests.keys())            










    # def test_loop(self, window_increase, seed):
    #     input_data = self.generate_input(self.num_injections, 
    #                                      self.injection_spacing, 
    #                                      self.min_requests_per_injection, 
    #                                      self.max_requests_per_injection,
    #                                      self.random_seed)
        


    #     # Load all the requests into a SchedulerSimulation instance
    #     sim = SchedulerSimulation(data=input_data)

    #     # Make a copy of all the requests present in the simulation
    #     # to be able to alter them easily.
    #     all_requests_base = deepcopy(sim.all_requests)

    #     # Run the simulation with no modifications, to get a baseline of results
    #     sim.run_simulation()
    #     base_results = set(sim.completed_requests.keys())

    #     # Run the experiment by iterating over individual requests
    #     test_results = self.new_variable_window_test(input_data=input_data, 
    #                                             all_requests_base=all_requests_base, 
    #                                             base_results=base_results,
    #                                             window_increase=window_increase,
    #                                             test_fraction=self.test_fraction)

    #     # Save results
    #     if window_increase not in self.output:
    #         self.output[window_increase] = []
    #     self.output[window_increase].append(test_results)


    # def new_variable_window_test(self, input_data, all_requests_base, base_results, 
    #                              window_increase, test_fraction):
    #     test_results = []

    #     # NOTE: In the reality of a continuously dynamic scheduler, requests would be coming in continuously, and there would be no end point
    #     # (save for the edge case of the end of an observing season or something similar).
    #     # Because of this, it is unrealistic to include observations for testing that are in the later portion of the requests, as we are not 
    #     # modelling the requests that are occuring after THEM, and thus might bump them out.
    #     # As such, we will only measure the effect of availability window size on the first half of requests (subject to change), to ensure 
    #     # realistic testing conditions.

    #     print(all_requests_base.keys())

    #     sample_number = round(test_fraction * len(all_requests_base))

    #     for i in range(len(all_requests_base)):
    #         # Write progress to screen
    #         if i % 10 == 0:
    #             print("\rRequest: {} / {}".format(i, len(all_requests_base)), end="")

    #         # Initialize a new instance of the scheduler
    #         sim = SchedulerSimulation(data=input_data)

    #         # Modify the requests by altering one availability window
    #         modified_requests = deepcopy(all_requests_base)
    #         r = modified_requests[str(i)]
    #         wgroup = r["windows"]
    #         for resource, windows in wgroup.items():
    #             new_windows = []
    #             for w in windows:
    #                 new_windows.append(extend_window(w, window_increase))
    #             wgroup[resource] = new_windows

    #         # Substitute in the modified requests, and run the simulation
    #         sim.all_requests_base = modified_requests
    #         sim.run_simulation()

    #         # Get the scheduled requests from this test
    #         current_results = set(sim.completed_requests.keys())

    #         # Calculate the new and missing requests
    #         missing_requests = base_results - current_results
    #         new_requests = current_results - base_results

    #         if (len(missing_requests) + len(new_requests)) > 0:
    #             print(i)
    #         if len(missing_requests) > 0:
    #             print("Missing!")
    #             print(missing_requests)
    #         if len(new_requests) > 0:
    #             print("New!")
    #             print(new_requests)

    #         # Record the results:
    #         # +1 : indicates that change has led to request[i] being scheduled when previously not.
    #         # -1 : indicates that change has led to request[i] being unscheduled when it previously was.
    #         #  0 : indicates that schedule may or may not have changed, but request[i] status has not.
    #         if str(i) in missing_requests:
    #             test_results.append(-1)
    #         elif i in new_requests:
    #             test_results.append(1)
    #         else:
    #             test_results.append(0)

    #     return test_results



class VariableWindowsTest(object):
    # Include allowing number of insertions, insertion_spacing, requests_per_insertion, percent of requests to test

    def __init__(self, output_folder, window_increase_factor_list, num_repeats, num_injections, 
                 injection_spacing, min_requests_per_injection, max_requests_per_injection,
                 test_fraction):
        self.output_folder = output_folder
        self.window_increase_factor_list = window_increase_factor_list
        self.num_repeats = num_repeats
        self.test_fraction = test_fraction

        # Input Generation Parameters
        self.num_injections = num_injections
        self.injection_spacing = injection_spacing
        self.min_requests_per_injection = min_requests_per_injection
        self.max_requests_per_injection = max_requests_per_injection

        # Calculated Values
        self.output = {}
        self.total_iterations = len(window_increase_factor_list)*num_repeats


    def generate_input(self, random_seed):
        random.seed(random_seed)
        rg = RequestGeneratorV2(0, 15000, 5, 300, 1)
        rg.generate_input_params()

        # Generate Request Injections
        request_injection_dict = {}
        for i in range(self.num_injections):
            injection_time = self.injection_spacing * i
            num_requests = random.randint(self.min_requests_per_injection, 
                                          self.max_requests_per_injection)
            request_injection_dict[injection_time] = num_requests

        rg.generate_requests_injections(request_injection_dict)
        output = json.dumps(rg.output_to_json())
        input_data = json.loads(output)
        return input_data


    def write(self, iteration):
        if iteration == self.total_iterations:
            print("\r", end="")
        else:
            print(f"\r{iteration} / {self.total_iterations}", end="")


    def test_loop(self, window_increase, seed):
        input_data = self.generate_input(self.num_injections, 
                                         self.injection_spacing, 
                                         self.min_requests_per_injection, 
                                         self.max_requests_per_injection,
                                         self.random_seed)
        
        # Generate Sim
        # Get all requests as a baseline
        # Run simulation without altering anything
        # Record resulting schedule
        # Modify a request
        # Run simulation with modified request
        # Record schedule from modified requests
        # Check to see if there has been a change

        # Load all the requests into a SchedulerSimulation instance
        sim = SchedulerSimulation(data=input_data)

        # Make a copy of all the requests present in the simulation
        # to be able to alter them easily.
        all_requests_base = deepcopy(sim.all_requests)

        # Run the simulation with no modifications, to get a baseline of results
        sim.run_simulation()
        base_results = set(sim.completed_requests.keys())

        # Run the experiment by iterating over individual requests
        test_results = self.new_variable_window_test(input_data=input_data, 
                                                all_requests_base=all_requests_base, 
                                                base_results=base_results,
                                                window_increase=window_increase,
                                                test_fraction=self.test_fraction)

        # Save results
        if window_increase not in self.output:
            self.output[window_increase] = []
        self.output[window_increase].append(test_results)


    def new_variable_window_test(self, input_data, all_requests_base, base_results, 
                                 window_increase, test_fraction):
        test_results = []

        # NOTE: In the reality of a continuously dynamic scheduler, requests would be coming in continuously, and there would be no end point
        # (save for the edge case of the end of an observing season or something similar).
        # Because of this, it is unrealistic to include observations for testing that are in the later portion of the requests, as we are not 
        # modelling the requests that are occuring after THEM, and thus might bump them out.
        # As such, we will only measure the effect of availability window size on the first half of requests (subject to change), to ensure 
        # realistic testing conditions.

        print(all_requests_base.keys())

        sample_number = round(test_fraction * len(all_requests_base))

        for i in range(len(all_requests_base)):
            # Write progress to screen
            if i % 10 == 0:
                print("\rRequest: {} / {}".format(i, len(all_requests_base)), end="")

            # Initialize a new instance of the scheduler
            sim = SchedulerSimulation(data=input_data)

            # Modify the requests by altering one availability window
            modified_requests = deepcopy(all_requests_base)
            r = modified_requests[str(i)]
            wgroup = r["windows"]
            for resource, windows in wgroup.items():
                new_windows = []
                for w in windows:
                    new_windows.append(extend_window(w, window_increase))
                wgroup[resource] = new_windows

            # Substitute in the modified requests, and run the simulation
            sim.all_requests_base = modified_requests
            sim.run_simulation()

            # Get the scheduled requests from this test
            current_results = set(sim.completed_requests.keys())

            # Calculate the new and missing requests
            missing_requests = base_results - current_results
            new_requests = current_results - base_results

            if (len(missing_requests) + len(new_requests)) > 0:
                print(i)
            if len(missing_requests) > 0:
                print("Missing!")
                print(missing_requests)
            if len(new_requests) > 0:
                print("New!")
                print(new_requests)

            # Record the results:
            # +1 : indicates that change has led to request[i] being scheduled when previously not.
            # -1 : indicates that change has led to request[i] being unscheduled when it previously was.
            #  0 : indicates that schedule may or may not have changed, but request[i] status has not.
            if str(i) in missing_requests:
                test_results.append(-1)
            elif i in new_requests:
                test_results.append(1)
            else:
                test_results.append(0)

        return test_results


    def run(self):
        rseed = 0
        for window_increase in self.window_increase_list:
            for i in range(self.num_repeats):
                self.test_loop(window_increase=window_increase,
                               seed=rseed)
                rseed += 1
                self.write(rseed)
        self.save_results()


    def save_results(self):
        # filepath = os.path.join(output_folder, "PerformanceTest1.json")
        # json.dump(self.output, open(filepath, "w"))
        # print(self.output)
        pprint.pprint(json.loads(json.dumps(self.output)))


# class VariableWindowsTest(object):
#     # Include allowing number of insertions, insertion_spacing, requests_per_insertion, percent of requests to test

#     def __init__(self, output_folder, window_increase_factor_list, num_repeats, num_injections, 
#                  injection_spacing, min_requests_per_inj, max_requests_per_inj,
#                  test_fraction):
#         self.output_folder = output_folder
#         self.window_increase_factor_list = window_increase_factor_list
#         self.num_repeats = num_repeats
#         self.test_fraction = test_fraction

#         # Input Generation Parameters
#         self.num_injections = num_injections
#         self.injection_spacing = injection_spacing
#         self.min_requests_per_inj = min_requests_per_inj
#         self.max_requests_per_inj = max_requests_per_inj

#         # Calculated Values
#         self.output = {}
#         self.total_iterations = len(window_increase_list)*num_repeats


#     def generate_input(self, num_injections, injection_spacing, 
#                        min_requests_per_injection, max_requests_per_injection,
#                        random_seed):
#         random.seed(random_seed)
#         rg = RequestGeneratorV2(0, 15000, 5, 300, 1)
#         rg.generate_input_params()

#         # Generate Request Injections
#         request_injection_dict = {}
#         for i in range(num_injections):
#             injection_time = injection_spacing * i
#             num_requests = random.randint(min_requests_per_injection, max_requests_per_injection)
#             request_injection_dict[injection_time] = num_requests

#         rg.generate_request_injections(request_injection_dict)
#         output = json.dumps(rg.output_to_json())
#         input_data = json.loads(output)
#         return input_data




#     # def __init__(self, output_folder, window_increase_list, num_injections, num_repeats):
#     #     self.output_folder = output_folder
#     #     self.window_increase_list = window_increase_list
#     #     self.num_injections = num_injections
#     #     self.num_repeats = num_repeats
#     #     self.output = {}
#     #     self.total_iterations = len(window_increase_list)*num_repeats


#     # def generate_input(self, n_reqs, num_injections, seed):
#     #     random.seed(seed)
#     #     rg = RequestGeneratorV2(0, 15000, 5, 300, 1)
#     #     rg.generate_input_params()

#     #     request_inj_dict = {3600*i: n_reqs for i in range(num_injections)}

#     #     rg.generate_requests_injections(request_inj_dict)
#     #     output = json.dumps(rg.output_to_json())
#     #     input_data = json.loads(output)
#     #     return input_data


#     def write(self, iteration):
#         if iteration == self.total_iterations:
#             print("\r", end="")
#         else:
#             print(f"\r{iteration} / {self.total_iterations}", end="")


#     def test_loop(self, n_reqs, n_injs, window_increase, seed):
#         input_data = self.generate_input(self.num_injections, 
#                                          self.injection_spacing, 
#                                          self.min_requests_per_injection, 
#                                          self.max_requests_per_injection,
#                                          self.random_seed)





#         # input_data = self.generate_input(n_reqs=n_reqs, 
#         #                                  num_injections=self.num_injections, 
#         #                                  seed=seed)
        
#         # Generate Sim
#         # Get all requests as a baseline
#         # Run simulation without altering anything
#         # Record resulting schedule
#         # Modify a request
#         # Run simulation with modified request
#         # Record schedule from modified requests
#         # Check to see if there has been a change

#         # Load all the requests into a SchedulerSimulation instance
#         sim = SchedulerSimulation(data=input_data)

#         # Make a copy of all the requests present in the simulation
#         # to be able to alter them easily.
#         all_requests_base = deepcopy(sim.all_requests)

#         # Run the simulation with no modifications, to get a baseline of results
#         sim.run_simulation()
#         base_results = set(sim.completed_requests.keys())

#         # Run the experiment by iterating over individual requests
#         test_results = self.new_variable_window_test(input_data=input_data, 
#                                                 all_requests_base=all_requests_base, 
#                                                 base_results=base_results,
#                                                 window_increase=window_increase)

#         # Save results
#         if window_increase not in self.output:
#             self.output[window_increase] = []
#         self.output[window_increase].append(test_results)


#     def new_variable_window_test(self, input_data, all_requests_base, base_results, 
#                                  window_increase):
#         test_results = []

#         for i in range(len(all_requests_base)):
#             if i % 10 == 0:
#                 print("\rRequest: {} / {}".format(i, len(all_requests_base)), end="")
#             sim = SchedulerSimulation(data=input_data)
#             modified_requests = deepcopy(all_requests_base)
#             r = modified_requests[str(i)]
#             wgroup = r["windows"]
#             for resource, windows in wgroup.items():
#                 new_windows = []
#                 for w in windows:
#                     new_windows.append(extend_window(w, window_increase))
#                 wgroup[resource] = new_windows

#             sim.all_requests_base = modified_requests
#             sim.run_simulation()

#             current_results = set(sim.completed_requests.keys())
#             # test_results[i] = list(current_results)

#             missing_requests = base_results - current_results
#             new_requests = current_results - base_results

#             if (len(missing_requests) + len(new_requests)) > 0:
#                 print(i)
#             if len(missing_requests) > 0:
#                 print("Missing!")
#                 print(missing_requests)
#             if len(new_requests) > 0:
#                 print("New!")
#                 print(new_requests)

#             if str(i) in missing_requests:
#                 test_results.append(-1)
#             elif i in new_requests:
#                 test_results.append(1)
#             else:
#                 test_results.append(0)

#         return test_results


#     def run(self):
#         rseed = 0
#         for window_increase in self.window_increase_list:
#             for i in range(self.num_repeats):
#                 self.test_loop(n_reqs=100,
#                                n_injs=10,
#                                window_increase=window_increase,
#                                seed=rseed)
#                 rseed += 1
#                 self.write(rseed)
#         self.save_results()


#     def save_results(self):
#         # filepath = os.path.join(output_folder, "PerformanceTest1.json")
#         # json.dump(self.output, open(filepath, "w"))
#         # print(self.output)
#         pprint.pprint(json.loads(json.dumps(self.output)))


    # def __init__(self, input_filepath, window_increases):
    #     self.input_filepath = input_filepath
    #     self.sim = SchedulerSimulation(input_filepath)
    #     self.all_requests_base = deepcopy(self.sim.all_requests)
    #     self.test_results = {}
    #     self.run_varying_windows_test()
    #     self.save_results(input_filepath, window_increase)
    

    # def save_results(self, input_filepath, window_increase):
    #     self.test_time = int(time.time())
    #     test_time = int(time.time())
    #     test_name = "VarWinTest_{}_{}".format(window_increase, test_time)
    #     test_dir = "test_results/{}".format(test_name)
    #     os.makedirs(test_dir)

    #     test_json = {
    #         "name": test_name,
    #         "input_filepath": input_filepath,
    #         "window_increase": window_increase,
    #         "results": self.test_results
    #     }

    #     with open(f"{test_dir}/{test_name}.json", "w") as f:
    #         json.dump(test_json, f, indent=4)


    # def run_varying_windows_test(self):
    #     self.sim.run_simulation()
    #     self.base_results = set(self.sim.completed_requests.keys())

    #     num_requests = len(self.all_requests_base)

    #     for i in range(num_requests):
    #         if i % 10 == 0:
    #             print("\rRequest: {} / {}".format(i, len(self.all_requests_base)), end="")
    #             # sys.stdout.write("\rRequest: {} / {}".format(i, len(self.all_requests_base)))
    #             # sys.stdout.flush()

    #         self.sim = SchedulerSimulation(self.input_filepath)
    #         modified_requests = deepcopy(self.all_requests_base)
    #         r = modified_requests[str(i)]
    #         wgroup = r["windows"]
    #         for resource, windows in wgroup.items():
    #             new_windows = []
    #             for w in windows:
    #                 new_windows.append(extend_window(w, 0.2))
    #             wgroup[resource] = new_windows

    #         self.sim.all_requests = modified_requests
    #         self.sim.run_simulation()

    #         current_results = set(self.sim.completed_requests.keys())
    #         self.test_results[i] = list(current_results)

    #         missing_requests = self.base_results - current_results
    #         new_requests = current_results - self.base_results

    #     print(f"\rRequest: {num_requests} / {num_requests}")


def extend_window(window, amount, extend_type="right"):
    start = window["start"]
    end = window["end"]
    duration = end-start
    adjustment = int(duration * amount)

    if extend_type == "right":
        end += adjustment
    elif extend_type == "left":
        start -= adjustment
    elif extend_type == "center":
        start -= int(adjustment/2)
        end += int(adjustment/2)

    return {"start": start, "end": end}

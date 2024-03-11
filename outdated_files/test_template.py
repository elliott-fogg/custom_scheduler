from ScheduleSimulator import SchedulerSimulation
from generate_requests_v2 import RequestGeneratorV2, RequestInjection
from copy import deepcopy
from collections import defaultdict
import numpy as np
import json
import time
import os
import random
import pprint


class TestTemplate(object):
    def __init__(self):
        pass

    def generate_input(self, input_params, seed):
        pass

    def set_output_folder(self):
        pass

    def create_output_folders(self):
        pass

    def setup(self):
        pass

    def write(self, i):
        pass

    def test_loop(self):
        pass

    def run(self):
        pass

    def save_results(self):
        pass


class PerformanceTest1(TestTemplate):
    """Test the effect of a varying number of requests on the performance of a scheduler with a single telescope."""
    def __init__(self, output_folder, request_count_list, num_repeats):
        super().__init__()
        self.output_folder = output_folder
        self.request_count_list = request_count_list
        self.num_repeats = num_repeats
        self.output = {}
        self.total_iterations = len(request_count_list)*num_repeats


    def generate_input(self, n_reqs, seed):
        # Code that will generate an identical set of input data with the same seed every time
        random.seed(seed)
        rg = RequestGeneratorV2(0, 15000, 5, 300, 1)
        rg.generate_input_params()
        rg.generate_single_request_injection(0, n_reqs, 60, 3000)
        output = json.dumps(rg.output_to_json())
        input_data = json.loads(output)
        return input_data


    def test_loop(self, n_reqs, seed):
        input_data = self.generate_input(n_reqs, seed)
        sim = SchedulerSimulation(data=input_data)
        t1 = time.time()
        sim.run_simulation()
        t2 = time.time()
        runtime = t2 - t1

        if n_reqs not in self.output:
            self.output[n_reqs] = []
        self.output[n_reqs].append(runtime)


    def save_results(self):
        # filepath = os.path.join(output_folder, "PerformanceTest1.json")
        # json.dump(self.output, open(filepath, "w"))
        print(self.output)


    def run(self):
        rseed = 0
        for n_reqs in self.request_count_list:
            for i in range(self.num_repeats):
                self.test_loop(n_reqs, rseed)
                rseed += 1
                self.write(rseed)
        self.save_results()

    def write(self, iteration):
        if iteration == self.total_iterations:
            print("\r", end="")
        else:
            print(f"\r{iteration} / {self.total_iterations}", end="")


class PerformanceTest2(TestTemplate):
    """Test the effect of an increasing number of telescopes on the performance of the scheduler."""
    def __init__(self, output_folder, request_count_list, telescope_count_list, num_repeats):
        super().__init__()
        self.output_folder = output_folder
        self.request_count_list = request_count_list
        self.telescope_count_list = telescope_count_list
        self.num_repeats = num_repeats
        self.output = {}
        self.total_iterations = len(request_count_list)*len(telescope_count_list)*num_repeats


    def generate_input(self, n_reqs, n_telescopes, seed):
        # Code that will generate an identical set of input data with the same seed every time
        random.seed(seed)
        rg = RequestGeneratorV2(0, 15000, 5, 300, n_telescopes)
        rg.generate_input_params()
        rg.generate_single_request_injection(0, n_reqs, 60, 3000)
        output = json.dumps(rg.output_to_json())
        input_data = json.loads(output)
        return input_data


    def test_loop(self, n_reqs, n_telescopes, seed):
        input_data = self.generate_input(n_reqs, n_telescopes, seed)
        sim = SchedulerSimulation(data=input_data)
        t1 = time.time()
        sim.run_simulation()
        t2 = time.time()
        runtime = t2 - t1

        if n_telescopes not in self.output:
            self.output[n_telescopes] = {}
        if n_reqs not in self.output[n_telescopes]:
            self.output[n_telescopes][n_reqs] = []
        self.output[n_telescopes][n_reqs].append(runtime)


    def save_results(self):
        # filepath = os.path.join(output_folder, "PerformanceTest1.json")
        # json.dump(self.output, open(filepath, "w"))
        print(self.output)


    def run(self):
        rseed = 0
        for n_telescopes in self.telescope_count_list:
            for n_reqs in self.request_count_list:
                for i in range(self.num_repeats):
                    self.test_loop(n_reqs, n_telescopes, rseed)
                    rseed += 1
                    self.write(rseed)
        self.save_results()


    def write(self, iteration):
        if iteration == self.total_iterations:
            print("\r", end="")
        else:
            print(f"\r{iteration} / {self.total_iterations}", end="")


class PerformanceTest3(TestTemplate):
    """Test the impact of Slice Size on the performance of the scheduler."""
    def __init__(self, output_folder, request_count_list, slice_size_list, num_repeats):
        super().__init__()
        self.output_folder = output_folder
        self.request_count_list = request_count_list
        self.slice_size_list = slice_size_list
        self.num_repeats = num_repeats
        self.output = {}
        self.total_iterations = len(request_count_list)*len(slice_size_list)*num_repeats


    def generate_input(self, n_reqs, slice_size, seed):
        # Code that will generate an identical set of input data with the same seed every time
        random.seed(seed)
        rg = RequestGeneratorV2(0, 15000, 5, slice_size, 1)
        rg.generate_input_params()
        rg.generate_single_request_injection(0, n_reqs, 60, 3000)
        output = json.dumps(rg.output_to_json())
        input_data = json.loads(output)
        return input_data


    def test_loop(self, n_reqs, slice_size, seed):
        input_data = self.generate_input(n_reqs, slice_size, seed)
        sim = SchedulerSimulation(data=input_data)
        t1 = time.time()
        sim.run_simulation()
        t2 = time.time()
        runtime = t2 - t1

        if slice_size not in self.output:
            self.output[slice_size] = {}
        if n_reqs not in self.output[slice_size]:
            self.output[slice_size][n_reqs] = []
        self.output[slice_size][n_reqs].append(runtime)


    def save_results(self):
        # filepath = os.path.join(output_folder, "PerformanceTest1.json")
        # json.dump(self.output, open(filepath, "w"))
        print(self.output)


    def run(self):
        rseed = 0
        for slice_size in self.slice_size_list:
            for n_reqs in self.request_count_list:
                for i in range(self.num_repeats):
                    self.test_loop(n_reqs, slice_size, rseed)
                    rseed += 1
                    self.write(rseed)
        self.save_results()


    def write(self, iteration):
        if iteration == self.total_iterations:
            print("\r", end="")
        else:
            print(f"\r{iteration} / {self.total_iterations}", end="")


class PerformanceTest4(PerformanceTest3):
    """A speed and accuracy comparison between different optimisers.
    Current optimisers: Gurobi, HiGHs"""

    num_solvers = 2
    # Gurobi
    #HiGHs

    def __init__(self, output_folder, request_count_list, slice_size_list, num_repeats):
        super.__init__(output_folder, request_count_list, slice_size_list, num_repeats)
        self.total_iterations = len(request_count_list)*len(slice_size_list)*num_repeats*num_solvers


class PerformanceTest5(TestTemplate):
    """Compare whether having additional but separate 'networks' on the same solver
    will significantly affect performance, or whether the solver is able to easily
    filter them out."""

    def __init__(self, output_folder, num_requests, num_telescopes, num_networks, num_repeats):
        self.output_folder = output_folder # Output folder to save results
        self.num_requests = num_requests # Number of requests to add per network
        self.num_networks = num_networks # Number of networks to include
        self.num_telescopes = num_telescopes # Number of telescopes to include on each network
        self.num_repeats = num_repeats # Number of times to repeat each experiment
        self.total_iterations = len(num_requests) * len(num_networks) * len(num_telescopes) * num_repeats
        self.output = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))


    def generate_input(self, num_requests, num_telescopes, num_networks, seed):
        random.seed(seed)
        rg = RequestGeneratorV2(start_time=0, horizon=15000, num_proposals=5, 
            slice_size=300, num_telescopes=num_telescopes, 
            num_networks=num_networks)
        rg.generate_input_params()

        requests_per_network = round(num_requests/num_networks)

        for i in range(num_networks):
            rg.generate_single_request_injection(inj_time=0, 
                num_requests=requests_per_network, 
                network=i)

        output = json.dumps(rg.output_to_json())
        input_data = json.loads(output)

        # with open(os.path.join(self.output_folder, f"input_req-{num_requests}_tel-{num_telescopes}_net-{num_networks}_seed-{seed}.json"), "w") as f:
        #     f.write(json.dumps(input_data))

        return input_data


    def test_input(self, num_requests, num_telescopes, num_networks, seed):
        random.seed(seed)
        rg = RequestGeneratorV2(start_time=0, horizon=15000, num_proposals=5, 
            slice_size=300, num_telescopes=num_telescopes, 
            num_networks=num_networks)
        rg.generate_input_params()

        requests_per_network = round(num_requests/num_networks)

        for i in range(num_networks):
            rg.generate_single_request_injection(inj_time=0, 
                num_requests=requests_per_network, 
                network=i)

        output = json.dumps(rg.output_to_json())
        input_data = json.loads(output)

        return input_data


    def test_loop(self, num_requests, num_telescopes, num_networks, seed):
        input_data = self.generate_input(num_requests=num_requests, 
                                         num_telescopes=num_telescopes, 
                                         num_networks=num_networks, 
                                         seed=seed)
        sim = SchedulerSimulation(data=input_data)
        t1 = time.time()
        sim.run_simulation()
        t2 = time.time()
        runtime = t2 - t1

        self.last_input = input_data
        self.last_sim = sim

        self.output[num_telescopes][num_requests][num_networks].append(runtime)


    def save_results(self):
        # filepath = os.path.join(output_folder, "PerformanceTest1.json")
        # json.dump(self.output, open(filepath, "w"))
        # print(self.output)
        pprint.pprint(json.loads(json.dumps(self.output)))


    def run(self):
        rseed = 0
        for num_requests in self.num_requests:
            for num_telescopes in self.num_telescopes:
                for num_networks in self.num_networks:
                    for i in range(self.num_repeats):
                        self.test_loop(num_requests=num_requests,
                                       num_telescopes=num_telescopes,
                                       num_networks=num_networks,
                                       seed=rseed)
                        # self.test_loop(num_requests, num_telescopes, num_networks, rseed)
                        rseed += 1
                        self.write(rseed)
        self.save_results()


    def write(self, iteration):
        if iteration == self.total_iterations:
            print("\r", end="")
        else:
            print(f"\r{iteration} / {self.total_iterations}", end="")


class PerformanceTest6(PerformanceTest5):
    """Compare whether having a multi-network system has a direct time-cost
    scaling of single version of one of the networks, at least as far as the 
    optimiser is concerned."""

    def __init__(self, output_folder, num_requests, num_telescopes, num_networks, num_repeats):
        super().__init__(output_folder, num_requests, num_telescopes, num_networks, num_repeats)
        self.total_iterations = len(num_requests) * len(num_networks) * len(num_telescopes) * num_repeats
        self.output = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [])))


    def test_loop(self, requests_per_network, telescopes_per_network, num_networks, seed):
        total_requests = requests_per_network * num_networks
        total_telescopes = telescopes_per_network * num_networks

        input_data = self.generate_input(num_requests=total_requests,
                                         num_telescopes=total_telescopes,
                                         num_networks=num_networks,
                                         seed=seed)

        sim = SchedulerSimulation(data=input_data)
        t1 = time.time()
        sim.run_simulation()
        t2 = time.time()
        runtime = t2 - t1

        self.last_input = input_data
        self.last_sim = sim

        self.output[telescopes_per_network][requests_per_network][num_networks].append(runtime)


    def run(self):
        rseed = 0
        for requests_per_network in self.num_requests:
            for telescopes_per_network in self.num_telescopes:
                for num_networks in self.num_networks:
                    for i in range(self.num_repeats):

                        print(requests_per_network, telescopes_per_network, num_networks, rseed)

                        self.test_loop(requests_per_network=requests_per_network,
                            telescopes_per_network=telescopes_per_network,
                            num_networks=num_networks,
                            seed=rseed)
                        rseed += 1
                        self.write(rseed)
        self.save_results()



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

from ScheduleSimulator import SchedulerSimulation
from generate_requests_v2 import RequestGeneratorV2
from copy import deepcopy
import sys
import json
import time
import os
import random
import sys

class TestTemplate(object):
    def __init__(self):
        pass

    def generate_input(self, input_params, seed):
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





class VariableWindowsTest(object):
    def __init__(self, input_filepath, window_increase):
        self.input_filepath = input_filepath
        self.sim = SchedulerSimulation(input_filepath)
        self.all_requests_base = deepcopy(self.sim.all_requests)
        self.test_results = {}
        self.run_varying_windows_test()
        self.save_results(input_filepath, window_increase)
        

    def save_results(self, input_filepath, window_increase):
        self.test_time = int(time.time())
        test_time = int(time.time())
        test_name = "VarWinTest_{}_{}".format(window_increase, test_time)
        test_dir = "test_results/{}".format(test_name)
        os.makedirs(test_dir)

        test_json = {
            "name": test_name,
            "input_filepath": input_filepath,
            "window_increase": window_increase,
            "results": self.test_results
        }

        with open(f"{test_dir}/{test_name}.json", "w") as f:
            json.dump(test_json, f, indent=4)


    def run_varying_windows_test(self):
        self.sim.run_simulation()
        self.base_results = set(self.sim.completed_requests.keys())

        num_requests = len(self.all_requests_base)

        for i in range(num_requests):
            if i % 10 == 0:
                sys.stdout.write("\rRequest: {} / {}".format(i, len(self.all_requests_base)))
                sys.stdout.flush()

            self.sim = SchedulerSimulation(self.input_filepath)
            modified_requests = deepcopy(self.all_requests_base)
            r = modified_requests[str(i)]
            wgroup = r["windows"]
            for resource, windows in wgroup.items():
                new_windows = []
                for w in windows:
                    new_windows.append(extend_window(w, 0.2))
                wgroup[resource] = new_windows

            self.sim.all_requests = modified_requests
            self.sim.run_simulation()

            current_results = set(self.sim.completed_requests.keys())
            self.test_results[i] = list(current_results)

            missing_requests = self.base_results - current_results
            new_requests = current_results - self.base_results

        print(f"\rRequest: {num_requests} / {num_requests}")


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







from ScheduleSimulator import SchedulerSimulation
from copy import deepcopy
import sys
import json
import time
import os

class VariableWindowsTest(object):
    def __init__(self, input_filepath, window_increase):
        self.input_filepath = input_filepath
        self.sim = SchedulerSimulation(input_filepath, scheduler_type="gurobi")
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







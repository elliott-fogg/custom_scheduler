import random, json, math, os
random.seed(3)

class Injection(object):
    def __init__(self, injection_time, injection_type, data=None):
        self.injection_time = injection_time
        self.injection_type = injection_type
        self.data = data

    def __str__(self):
        return f"{self.injection_type}_{self.injection_time}"
    
    def __lt__(self, other):
        if self.injection_time == other.injection_time:
            return self.type_lt(other)
        else:
            return self.injection_time < other.injection_time

    def __gt__(self, other):
        if self.injection_time == other.injection_time:
            return self.type_gt(other)
        else:
            return self.injection_time > other.injection_time

    def __eq__(self, other):
        if self.injection_time == other.injection_time:
            return self.type_eq(other)
        else:
            return False

    def type_lt(self, other):
        if self.injection_type == "request": # Either Request vs Request, or Request vs Resource
            return False
        elif other.injection_type == "resource": # Either Resource vs Resource, or Request vs Resource
            return False
        else:
            return True # Must be Resource vs Request

    def type_gt(self, other):
        if self.injection_type == "resource":
            return False
        elif other.injection_type == "request":
            return False
        else: return True

    def type_eq(self, other):
        return self.injection_type == other.injection_type


    def to_json(self):
        return {
            "injection_time": self.injection_time,
            "injection_type": self.injection_type,
            "injection_data": self.data
        }


class ResourceInjection(Injection):
    def __init__(self, injection_time, resource_data):
        super().__init__(injection_time, "resource", resource_data)


class RequestInjection(Injection):
    def __init__(self, injection_time, request_data):
        super().__init__(injection_time, "request", request_data)


class RequestGeneratorV2(object):
    def __init__(self, start_time, horizon, num_proposals, slice_size, 
                 num_telescopes):
        self.start_time = start_time
        self.slice_size = slice_size
        self.horizon = horizon
        self.num_proposals = num_proposals
        self.injections = []
        self.request_count = 0
        self.num_telescopes = num_telescopes


    def generate_input_params(self):
        self.end_time = self.start_time + self.horizon
        self.resources = {f"t{i}": time_segments(self.start_time, self.end_time, 
                                                 1, 3, use_bounds=True) \
            for i in range(self.num_telescopes)}

        self.proposals = {}
        for i in range(self.num_proposals):
            proposal_name = f"proposal_{i}"
            tac_priority = random.randint(5, 40)
            self.proposals[proposal_name] = {"tac_priority": tac_priority}


    def generate_requests(self, num_requests, injection_time, 
                          request_min_length=60, request_max_length=10800):
        requests = {}
        for i in range(num_requests):
            windows = {r: time_segments(injection_time, self.end_time, 
                                        1, 8) for r in self.resources}
            duration = random.randint(request_min_length, request_max_length)
            proposal = random.choice(list(self.proposals.keys()))

            requests[self.request_count] = {
                "windows": windows,
                "duration": duration,
                "proposal": proposal,
                "resID": self.request_count
            }

            self.request_count += 1     # Make sure that each request has a unique ID

        return requests


    def generate_single_request_injection(self, inj_time, num_requests, 
                                          min_length=60, max_length=10800):
        requests = self.generate_requests(num_requests, inj_time, 
                                          min_length, max_length)
        self.injections.append(RequestInjection(inj_time, requests))


    def generate_requests_injections(self, injection_dict):
        for injection_time, request_num in injection_dict.items():
            self.generate_single_request_injection(injection_time, num_requests)


    def generate_single_telescope_closure(self, inj_time, resource, 
                                          end_time=None, max_close_time=None):
        closure_start = inj_time
        if end_time != None:
            closure_end = end_time

        else:
            length = random.randint(0, self.horizon - inj_time)
            if max_close_time != None:
                length = min(length, max_close_time)
            closure_time = closure_start + length

        data = {
            "start_time": closure_start,
            "end_time": closure_end,
            "resource": resource
        }

        self.injections.append(ResourceInjection(closure_start, data))


    def generate_telescope_closures(self, num_closures, max_close_time):
        for i in range(num_closures):
            inj_time = random.randint(self.start_time, self.horizon-2000)
            self.generate_single_telescope_closure(inj_time, "t1", 
                                                   max_close_time=max_close_time)


    def save_to_file(self, filename=None, dirname="sample_input"):
        if filename == None:
            file_prefix = "sample_input_v2_"
            file_index = 0
            while True:
                filepath = f"{dirname}/{file_prefix}{file_index}.json"
                if os.path.isfile(filepath):
                    file_index += 1
                else:
                    break

        output = {
            "input_parameters": {
                "start_time": self.start_time,
                "slice_size": self.slice_size,
                "horizon": self.horizon,
                "resources": self.resources,
                "proposals": self.proposals
            },
            "injections": [inj.to_json() for inj in self.injections]
        }

        with open(filepath, "w") as f:
            json.dump(output, f, indent=4)
        print(f"Saved to file at '{filepath}'")


    def auto_run(self, request_injection_dict, num_telescope_closures):
        self.generate_input_params()
        self.generate_requests_injections(request_injection_dict)
        max_closure_length = int(self.horizon / 10)
        self.generate_telescope_closures(num_telescope_closures, 
                                         max_closure_length)
        self.injections.sort()
        print("Finished Request Generation V2")
        self.save_to_file()


################################################################################

def time_segments(start, end, num_min=1, num_max=5, use_bounds=False):
    segments = random.randint(num_min, num_max)
    boundaries = []
    if use_bounds:
        segments -= 1
        boundaries += [start, end]
    boundaries += [random.randint(start, end) for x in range(2*segments)]
    boundaries.sort()
    windows = [{"start": boundaries[i], "end": boundaries[i+1]} for i in range(0, len(boundaries), 2)]
    return windows


### MAIN #######################################################################

if __name__ == "__main__":
    print("Running Request Generation V2...")
    request_injection_dict = {1000: 5, 2000: 5, 3000: 5}
    rg2 = RequestGeneratorV2(0, 60*60*24*3, 5, 300)
    rg2.auto_run(request_injection_dict, 3)


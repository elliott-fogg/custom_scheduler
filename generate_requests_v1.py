import random, json, math, os
random.seed(3)

class RequestGenerator1(object):
    def __init__(self, start_time=0, horizon=60*60*24, num_proposals=5, slice_size=300):
        self.start_time = start_time
        self.slice_size = slice_size
        self.horizon = horizon
        self.num_proposals = num_proposals


    def generate_input_params(self):
        self.end_time = self.start_time + self.horizon
        self.resources = {"t1": time_segments(self.start_time,
                                              self.end_time,
                                              1, 3)}
        self.proposals = {}
        for i in range(self.num_proposals):
            proposal_name = f"proposal_{i}"
            tac_priority = random.randint(5, 40)
            self.proposals[proposal_name] = {"tac_priority": tac_priority}


    def generate_requests(self, num_requests=10, request_min_length=400,
                          request_max_length=6000):
        requests = {}
        for i in range(num_requests):

            windows = {r: time_segments(self.start_time, self.end_time,
                                        1, 8) for r in self.resources}
            duration = random.randint(request_min_length, request_max_length)
            proposal = random.choice(list(self.proposals.keys()))

            requests[i] = {
                "windows": windows,
                "duration": duration,
                "proposal": proposal,
                "resID": i
            }

        self.requests = requests


    def save_to_file(self, filename=None):
        if filename == None:
            file_prefix = "sample_input_"
            file_index = 0
            while os.path.isfile(f"{file_prefix}{file_index}.json"):
                file_index += 1
            filename = f"{file_prefix}{file_index}.json"

        output = {
            "input_parameters": {
                "start_time": self.start_time,
                "slice_size": self.slice_size,
                "horizon": self.horizon,
                "resources": self.resources,
                "proposals": self.proposals
            },
            "requests": self.requests
        }

        with open(filename, "w") as f:
            json.dump(output, f, indent=4)


################################################################################

def time_segments(start, end, num_min=1, num_max=5):
    segments = random.randint(num_min, num_max)
    boundaries = sorted([random.randint(start, end) for x in range(2*segments)])
    windows = [{"start": boundaries[i], "end": boundaries[i+1]} for i in range(0, len(boundaries), 2)]
    return windows

import random, json, math, os
import numpy as np
from scheduler_utils import ResourceInjection, RequestInjection, overlap_time_segments, trim_time_segments
import math

SECONDS_IN_DAY = 24 * 60 * 60

# Scheduling Horizon in seconds
# 7 days - Taken from provided input file
default_horizon_days = 7

# Time Discretization Slice Size in seconds
# 5 minutes - Taken from provided input file
default_slice_size = 300

# Approximated from times found in telescope_times.json
# Stored as floats representing the rounded hour in 24hr time
# E.g. "04:00:00" = 4.0, "23:30:00" = 23.5
estimated_telescope_times = {
    "COJ": {
        "start": 8,
        "end": 20
    },
    "OGG": {
        "start": 4,
        "end": 17.5
    },
    "LSC": {
        "start": 23,
        "end": 11
    },
    "CPT": {
        "start": 17,
        "end": 4.5
    },
    "TFN": {
        "start": 18.5,
        "end": 8
    },
    "TLV": {
        "start": 15.5,
        "end": 3.5
    }
}

telescopes_2m = ["COJ", "OGG"]

class RequestGeneratorV3(object):
    def __init__(self, seed, now=0, horizon_days=default_horizon_days,
                 num_telescopes=1, num_networks=1, use_2m_telescopes=False,
                 num_proposals=5, proposals_dict=None,
                 slice_size=default_slice_size):

        random.seed(seed)

        # Store necessary parameters
        self.now = now # The start time of the scheduler, in seconds
        # Must be from a 24hr clock (so < 1 day, so < 24*60*60)
        # Defaults to be midnight.

        self.horizon_days = horizon_days
        self.horizon = self.now + horizon_days*24*60*60
        self.slice_size=slice_size

        # Generating Telescope Opening Hours
        if use_2m_telescopes:
            self.resources = generate_2m_telescopes()
            self.networks = self.generate_sub_networks(num_networks=1)
        else:
            self.resources = self.generate_telescope_times(num_telescopes=num_telescopes)
            self.networks = self.generate_sub_networks(num_networks=num_networks)

        # Generating Proposal Information
        if proposals_dict != None:
            self.proposals = proposals_dict
        else:
            self.proposals = self.generate_default_proposals(num_proposals)
            # self.generate_default_proposals(num_proposals)

        # Make variables for used data
        self.injections = []
        self.request_count = 0

        # Load request pattern information
        pattern_data = json.load(open("../archive_scraper/observation_patterns_v1.json", "r"))
        self.observation_patterns = sorted(pattern_data.values(), key=lambda x: x["cumulative_probability"])


    def generate_telescope_times(self, num_telescopes):
        telescopes = {}
        telescope_options = list(estimated_telescope_times.keys())

        for i in range(num_telescopes):
            # Assume the opening hours for a random telescope site
            site = random.choice(telescope_options)
            start_time = int(estimated_telescope_times[site]["start"] * 60 * 60)
            end_time = int(estimated_telescope_times[site]["end"] * 60 * 60)

            telescopes[f"telescope_{i}"] = self.propagate_telescope_times(start_time, end_time)

        return telescopes


    def propagate_telescope_times(self, start_time, end_time):
        if end_time < start_time:
            start_time -= SECONDS_IN_DAY

        open_hours = [{"start": start_time + i*SECONDS_IN_DAY, "end": end_time + i*SECONDS_IN_DAY} \
            for i in range(self.horizon_days+2)]

        open_hours = trim_time_segments(open_hours, self.now, self.horizon)

        return open_hours


    def generate_2m_telescopes(self):
        telescopes = {}
        for site in ["COJ", "OGG"]:
            start_time = estimated_telescope_times[site]["start"] * 60 * 60
            end_time = estimated_telescope_times[site]["end"] * 60 * 60

            telescopes[site] = self.propagate_telescope_times(start_time, end_time)

        return {"network_0": telescopes}


    def generate_sub_networks(self, num_networks):
        # A network is a collection of telescopes that can share observation requests,
        # but do not share observation requests between networks
        # e.g. the 2m telescopes vs the 1m telescopes vs the 0.4m telescopes.
        return np.array_split(list(self.resources.keys()), num_networks)


    def generate_default_proposals(self, num_proposals):
        proposals = {}
        for i in range(num_proposals):
            proposal_name = f"proposal_{i}"
            tac_priority = random.randint(4, 6) * 5
            proposals[proposal_name] = {"tac_priority": tac_priority}
        return proposals


    def get_pattern(self):
        rnum = random.random()
        for p in self.observation_patterns:
            if rnum <= p["cumulative_probability"]:
                return p["pattern"]


    def generate_request(self, injection_time, telescope_network=None):
        # Pick a pattern
        # Pick a time a certain distance from the injection time
        # Pick an availability window size
        # Pick a network of telescopes
        pattern = self.get_pattern()
        total_pattern_length = int(sum(pattern))
        
        # TO FIX: Work out a way of systematically generating an availability window.
        availability_window_length = int(round(((random.random() * 9) + 1) * total_pattern_length))

        start_time = int(round(random.random() * self.horizon * 0.5))

        if telescope_network == None:
            windows = {r: [{"start": start_time, "end": start_time + availability_window_length}] \
                for r in self.resources}
        else:
            windows = {r: [{"start": start_time, "end": start_time + availability_window_length}] \
                for r in self.networks[telescope_network]}

        proposal = random.choice(list(self.proposals.keys()))

        requestID = self.request_count

        self.request_count += 1
        
        return {
            "windows": windows,
            "duration": total_pattern_length,
            "proposal": proposal,
            "resID": requestID
        }
        

    def generate_single_request_injection(self, inj_time, num_requests, network=0):
        new_requests = [self.generate_request(inj_time, network) for i in range(num_requests)]
        requests = {r["resID"]: r for r in new_requests}
        self.injections.append(RequestInjection(inj_time, requests))


    def generate_requests_injections(self, injection_dict):
        for injection_time, num_requests in injection_dict.items():
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


    def output_to_json(self):
        output = {
            "input_parameters": {
                "start_time": self.now,
                "slice_size": self.slice_size,
                "horizon": self.horizon,
                "resources": self.resources,
                "proposals": self.proposals
            },
            "injections": [inj.to_json() for inj in self.injections]
        }

        return output


    def save_to_file(self, filename=None, dirname="sample_input"):
        if filename == None:
            file_prefix = "sample_input_v3_"
            file_index = 0
            while True:
                filename = f"{file_prefix}{file_index}.json"
                temp_path = f"{dirname}/{filename}.json"
                if os.path.isfile(temp_path):
                    file_index += 1
                else:
                    break

        output = self.output_to_json()

        filepath = os.path.join(dirname, filename)

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
        print("Finished Request Generation V3")
        self.save_to_file()
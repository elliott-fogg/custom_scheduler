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


class RequestGeneratorV4(object):
    def __init__(self, random_seed, now=0, horizon_days=default_horizon_days,
                 num_telescopes=1, num_networks=1, num_proposals=5, proposals_dict=None,
                 slice_size=default_slice_size):
        random.seed(random_seed)

        # Store necessary parameters

        self.now = now # The start time of the scheduelr, in seconds, in 24h clock (<24*60*60)
        self.horizon_days = horizon_days # How many days the scheduler schedules over
        self.horizon = self.now + (horizon_days * SECONDS_IN_DAY) # End time of the scheduler
        self.slice_size = slice_size

        # Generate Telescope Opening Hours
        self.resources = self.generate_telescope_times(num_telescopes=num_telescopes)
        self.networks = self.generate_sub_networks(num_networks=num_networks)


        # Generate Proposal Information
        if proposals_dict != None:
            self.proposals = proposals_dict
        else:
            self.proposals = self.generate_default_proposals(num_proposals)

        # Create variables to store request information
        self.requests = {}
        self.injections = []

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


    def generate_request(self, injection_time, telescope_network=0):
        # Sample a pattern
        # Pick a time some way away from the injection time
        # Pick an availability window size
        # Pick a network of telescopes

        pattern = self.get_pattern()
        total_pattern_length = int(sum(pattern))

        # Current Availability Window formula:
        # Random(1, 10) * pattern length
        availability_window_length = int(round(((random.random() * 9) + 1) * total_pattern_length))

        # Generate all requests within half of the scheduling horizon???
        start_time = int(round(random.random() * self.horizon * 0.5))

        # If there is only 1 network, then this will get all the telescopes as they will
        # all be in a single network.
        windows = {r: [{"start": start_time, "end": start_time + availability_window_length}] \
            for r in self.networks[telescope_network]}

        proposal = random.choice(list(self.proposals.keys()))

        requestID = len(self.requests)

        self.requests[requestID] = {
            "windows": windows,
            "duration": total_pattern_length,
            "proposal": proposal,
            "requestID": requestID
        }

        return requestID


    def generate_request_injection(self, injection_time, num_requests, network=0):
        new_requests = [self.generate_request(injection_time, network) for _ in range(num_requests)]
        self.injections.append(RequestInjection(injection_time, new_requests))


    def generate_telescope_closure(self, injection_time, resource, end_time=None, max_close_time=None):
        closure_start = injection_time
        
        if end_time != None:
            closure_end = end_time

        else:
            length = random.randint(0, self.horizon - injection_time)
            if max_close_time != None:
                length = min(length, max_close_time)
            closure_end = closure_start + length

        data = {
            "start_time": closure_start,
            "end_time": closure_end,
            "resource": resource
        }

        self.injections.append(ResourceInjection(closure_start, data))


    def to_json(self):
        output = {
            "input_parameters": {
                "start_time": self.now,
                "slice_size": self.slice_size,
                "horizon": self.horizon
            },
            "resources": self.resources,
            "requests": self.requests,
            "proposals": self.proposals,
            "injections": [injection.to_json() for injection in self.injections]
        }


    def save_to_file(self, data_dir, output_dir, filename=None):
        output = self.to_json()
        filepath = os.path.join(data_dir, dirname, filename)
        with open(filepath, "w") as f:
            json.dump(output, f, indent=4)
        print(f"Saved to file at '{filepath}'.")
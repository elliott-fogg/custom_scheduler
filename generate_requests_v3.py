import random, json, math, os
import numpy as np
from scheduler_utils import TimeSegment, overlap_time_segments, trim_time_segments

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
estimated_telescope_times: {
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


class RequestGeneratorV3(object):
    def __init__(self, now=0, horizon_days=default_horizon_days,
                 num_telescopes=1, num_networks=1, use_2m_telescopes=False,
                 num_proposals=5, proposals_dict=None,
                 slice_size=default_slice_size):

        # Store necessary parameters
        self.now = now # The start time of the scheduler, in seconds
        # Must be from a 24hr clock (so < 1 day, so < 24*60*60)
        # Defaults to be midnight.

        self.horizon_days = self.horizon_days
        self.horizon = self.now + horizon_days*24*60*60
        self.slice_size=slice_size

        # Generating Telescope Opening Hours
        if use_2m_telescopes:
            self.resources = generate_2m_telescopes()
            self.networks = self.generate_sub_networks(num_networks=1)
        else:
            self.resources = self.generate_telescope_times(num_telescopes=num_telescopes)
            self.resources = self.generate_sub_networks(num_networks=num_networks)

        # Generating Proposal Information
        if proposals_dict != None:
            self.proposals = proposals_dict
        else:
            self.generate_default_proposals(num_proposals)

        # Make variables for used data
        self.injections = []
        self.request_count = 0


    def generate_telescope_times(self, num_telescopes):
        print("TELESCOPE TIMES")
        telescopes = {}
        telescope_options = list(estimated_telescope_times.keys())

        for i in range(num_telescopes):
            # Assume the opening hours for a random telescope site
            site = random.choice(telescope_options)
            start_time = int(estimated_telescope_times[site]["start"] * 60 * 60)
            end_time = int(estimated_telescope_times[site]["end"] * 60 * 60)

            telescopes[f"telescope_{i}"] = self.propagate_telescope_times(start_time, end_time)

        print(telescopes)
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

        # networks = {}
        # for i in range(len(num_networks)):
        #     network_telescopes = self.generate_telescope_times(num_telescopes=num_telescopes_per_network)
        #     networks[f"network_{i}"] = network_telescopes
        # return networks


    def generate_default_proposals(self, num_proposals):
        proposals = {}
        for i in range(num_proposals):
            proposal_name = f"proposal_{i}"
            tac_priority = random.randint(4, 6) * 5
            proposals[proposal_name] = {"tac_priority": tac_priority}
        return proposals


    # def generate_input_params(self):
    #     self.end_time = self.start_time + self.horizon
    #     self.resources = {f"t{i}": time_segments(self.start_time, self.end_time, 
    #                                              1, 3, use_bounds=True) \
    #         for i in range(self.num_telescopes)}

    #     # Split resources into independent networks (defaults to 1 network)
    #     all_resources = list(self.resources.keys())
    #     self.networks = np.array_split(list(self.resources.keys()), self.num_networks)

    #     self.proposals = {}
    #     for i in range(self.num_proposals):
    #         proposal_name = f"proposal_{i}"
    #         tac_priority = random.randint(5, 40)
    #         self.proposals[proposal_name] = {"tac_priority": tac_priority}


    def generate_requests(self, num_requests, injection_time, 
                          request_min_length=60, request_max_length=10800,
                          telescope_network=None):
        requests = {}
        for i in range(num_requests):
            if telescope_network == None:
                windows = {r: time_segments(injection_time, self.end_time, 
                                            1, 8) for r in self.resources}
            else:
                windows = {r: time_segments(injection_time, 
                            self.end_time, 1, 8) for r in self.networks[telescope_network]}

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
                                        min_length=60, max_length=10800, network=0):
        requests = self.generate_requests(num_requests, inj_time, 
                                          min_length, max_length, network)
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
                "start_time": self.start_time,
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
            file_prefix = "sample_input_v2_"
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



### Out Of Date Code ###########################################################

    # def generate_telescope_times(self, num_telescopes, num_networks):
    #     telescopes = {}
    #     telescope_options = list(estimated_telescope_times.keys())
    #     for i in range(num_telescopes):
    #         # Assume the opening hours for a random telescope site
    #         site_name = random.choice(telescope_options)
    #         hours = estimated_telescope_times[site_name]
    #         start_time = hours["start"] * 60 * 60
    #         end_time = hours["end"] * 60 * 60

    #         open_hours = []

    #         seconds_in_day = 24 * 60 * 60

    #         if start_time > end_time:
    #             start_time -= seconds_in_day

    #         open_hours = [TimeSegment(start_time + i * self.horizon)]


    #         # day_offset = 0
    #         # end_offset = 0

    #         # if start_time < end_time:
    #         #     if start_time <= self.now:
    #         #         day_offset = 1

    #         #         if self.now <= end_time:
    #         #             open_hours.append({"start": self.now, "end": end_time})

    #         # else:
    #         #     # end_time < start_time, so we need to advance the end_time,
    #         #     # after checking if we need a window between NOW and end_time.
    #         #     end_offset = 1

    #         #     if self.now <= end_time:
    #         #         open_hours.append({"start": self.now, "end": end_time})

    #         #     elif self.now >= start_time:
    #         #         open_hours.append({"start": self.now, "end": end_time + seconds_in_day})


    #         # if start_open:
    #         #     open_hours.append{"start": current_time, end: end_seconds}
    #         #     current_time = end_time
    #         #     end_seconds += 24 * 60 * 60

    #         # let D = (24*60*60) = seconds in a day

    #         # For NOW < start < end:
    #         # For i in range(self.horizon_days + 3):
    #         #   Generate pairs of (start+i*D, end+i*D)

    #         # For start < NOW < end:
    #         # Generate pair of (NOW, end)
    #         # For i in range(1, self.horizon_days + 3):
    #         #   Generate pairs of (start+i*D, end+i*D)

    #         # For start < end < NOW:
    #         # For i in range(1, self.horizon_days + 3):
    #         #   Generate pairs of (start+i*D, end+i*D)

    #         # For NOW < end < start:
    #         # Generate pair of (Now, end)
    #         # For i in range(0, self.horizon_days + 3):
    #         #   Generate pairs of (start+i*D, end+(i+1)*D)

    #         # For end < NOW < start:
    #         # For i in range(0, self.horizon_days + 3):
    #         #   Generate pairs of (start+i*D, end+(i+1)*D)

    #         # For end < start < NOW:
    #         # Generate pair of (NOW, end+D)
    #         # For i in range(1, self.horizon_days + 3):
    #         #   Generate pairs of (start+i*D, end+(i+1)*D)
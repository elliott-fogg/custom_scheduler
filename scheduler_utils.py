class PossibleStart(object):
    def __init__(self, resource, slice_starts, internal_start, slice_size):
        self.resource = resource
        self.first_slice_start = slice_starts[0]
        self.all_slice_starts = slice_starts
        self.internal_start = internal_start
        self.slice_size = slice_size

    def __lt__(self, other):
        return self.first_slice_start < other.first_slice_start

    def __eq__(self, other):
        return self.first_slice_start == self.first_slice_start

    def __gt__(self, other):
        return self.first_slice_start > self.first_slice_start

    def __str__(self):
        return "resource_{}_start_{}_length_{}".format(self.resource,
                                                       self.first_slice_start,
                                                       self.slice_size)


class TimeSegment(object):
    def __init__(self, start, end):
        if start < end:
            self.start = start
            self.end = end
        else:
            raise Exception()

    def __gt__(self, other):
        if self.start == other.start:
            return self.end > other.end
        else:
            return self.start > other.start

    def __lt__(self, other):
        if self.start == other.start:
            return self.end < other.end
        else:
            return self.start < other.start

    def __eq__(self, other):
        return (self.start == other.start) and (self.end == other.end)



def overlap_time_segments(seg1, seg2, now, horizon):
    overlap_segments = []
    i = 0
    j = 0

    seg1.sort(key=lambda x: x["start"])
    seg2.sort(key=lambda x: x["start"])

    while ((i < len(seg1)) and (j < len(seg2))):
        s1 = seg1[i]
        s2 = seg2[j]

        if s1["end"] < s2["start"]: # Current s1 is behind Current s2, move to next s1
            i += 1
            continue

        if s2["end"] < s1["start"]: # Current s2 is behind Current s1, move to next s2
            j += 1
            continue

        window_start = max([s1["start"], s2["start"], now])
        
        if s1["end"] < s2["end"]: # s1 ends first, move to next s1
            window_end = s1["end"]
            i += 1
            
        elif s1["end"] > s2["end"]: # s2 ends first, move to next s2
            window_end= min(max([s2["end"], now]), horizon)
            j += 1

        else: # Both segments end at the same time, move to next of both
            window_end = min(max([s1["end"], now]), horizon)
            i += 1
            j+= 1

        if window_start != window_end:
            overlap_segments.append({"start": window_start, "end": window_end})
            
    return overlap_segments


def cut_time_segments(seg1, cut_start, cut_end):
    output_segments = []
    for seg in seg1:
        if seg["start"] < cut_start:
            # Segment starts before the cut
            if seg["end"] < cut_start:
                # Segment also ends before the cut, so it's unaffected
                output_segments.append(seg)

            else:
                # There is a new segment before the cut
                output_segments.append({"start": seg["start"],
                                             "end": cut_start})

                if seg["end"] > cut_end:
                    # Segment extends past both ends of the cut, have to split
                    # into two separate segments.
                    output_segments.append({"start": cut_end,
                                                 "end": seg["end"]})

        else:
            # Segment starts after the cut starts
            if seg["start"] > cut_end:
                # Segment starts after the cut ends, so it's unaffected
                output_segments.append(seg)

            else:
                if seg["end"] < cut_end:
                    # Segment occurs entirely within the cut, so it is removed
                    continue

                else:
                    # Cut only affects the first part of the segment
                    output_segments.append({"start": cut_end,
                                                 "end": seg["end"]})

    return output_segments


class Injection(object):
    def __init__(self, injection_time, injection_type, data=None):
        self.time = injection_time
        self.type = injection_type
        self.data = data

    def __str__(self):
        return f"{self.type}_{self.time}"
    
    def __lt__(self, other):
        if self.time == other.time:
            return self.type_lt(other)
        else:
            return self.time < other.time

    def __gt__(self, other):
        if self.time == other.time:
            return self.type_gt(other)
        else:
            return self.time > other.time

    def __eq__(self, other):
        if self.time == other.time:
            return self.type_eq(other)
        else:
            return False

    def type_lt(self, other):
        if self.type == "request": # Either Request vs Request, or Request vs Resource
            return False
        elif other.type == "resource": # Either Resource vs Resource, or Request vs Resource
            return False
        else:
            return True # Must be Resource vs Request

    def type_gt(self, other):
        if self.type == "resource":
            return False
        elif other.type == "request":
            return False
        else: return True

    def type_eq(self, other):
        return self.type == other.type


    def to_json(self):
        return {
            "injection_time": self.time,
            "injection_type": self.type,
            "injection_data": self.data
        }


class TelescopeEvent(Injection):
    def __init__(self, injection_time, resource, closed):
        data = {"resource": resource, "closed": closed}
        super().__init__(injection_time, "resource", data)


class RequestEvent(Injection):
    def __init__(self, injection_time, data):
        super().__init__(injection_time, "request", data)
import numpy as np

class Out(object):
    def __init__(self, out, persis_info):
        self.out = (out, persis_info)

def libe_return(out, persis_info, event_queue):
    event_queue['q'].put(Out(out, persis_info))
    event_queue['e'].set()

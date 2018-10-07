#!/usr/bin/python3.6

class RttModule:

    '''
    EstimatedRTT = (1 - a) * EstimatedRTT + a * SampleRTT (a = 0.125)
    DevRTT = (1 - b) * DevRTT + b * |SampleRTT - EstimatedRTT| (b = 0.25)
    TimeoutInterval = EstimatedRTT + gamma * DevRTT
    '''
    def __init__(self, gamma):
        self.estimated_rtt = 0.5
        self.dev_rtt = 0.25
        self.gamma = gamma
        self.timeout_interval = self.estimated_rtt + (self.gamma * self.dev_rtt)

    def updated_timeout(self, sample_rtt):
        self.estimated_rtt = (0.875 * self.estimated_rtt) + (0.125 * sample_rtt)
        self.dev_rtt = (0.75 * self.dev_rtt) + (0.25 * abs(sample_rtt - self.estimated_rtt))
        self.timeout_interval = self.estimated_rtt + (self.gamma * self.dev_rtt)
        return self.timeout_interval

    def get_timeout(self):
        return self.timeout_interval

#!/usr/bin/python3.6

import time
from random import seed, random, uniform
from StpDatagram import StpDatagram

'''
The PldModule class is used to test the reliability of the protocol by simulating random
packet loss, delays, and corruption
'''
class PldModule:

    def __init__(self, protocol, log, input_args):
        self.protocol = protocol
        self.log = log
        seed(input_args['seed_val'])
        self.p_drop = input_args['p_drop']
        self.p_dupe = input_args['p_dupe']
        self.p_corrupt = input_args['p_corrupt']
        self.p_order = input_args['p_order']
        self.max_order = input_args['max_order']
        self.p_delay = input_args['p_delay']
        self.max_delay = input_args['max_delay']
        self.reordered_packet = None
        self.reordered_count = 0
        self.delayed_packet = list()

    def pld_send(self, stp_datagram: StpDatagram):
        rxt = '/RXT' if stp_datagram.resend else ''
        # Setup and teardown skips PLD
        if stp_datagram.is_setup_teardown():
            self.log.write_log_entry('snd' + rxt, stp_datagram, timeout=stp_datagram.resend)
            self.send_datagram(stp_datagram.datagram)
        # Segment should be dropped
        elif random() < self.p_drop:
            self.log.write_log_entry('drop', stp_datagram, pld=True, drop=True,
                                     fast=stp_datagram.fast_retransmit)
        # Segment should be duplicated
        elif random() < self.p_dupe:
            self.log.write_log_entry('snd' + rxt, stp_datagram, pld=True,
                                     timeout=stp_datagram.resend, fast=stp_datagram.fast_retransmit)
            self.send_datagram(stp_datagram.datagram)
            self.log.write_log_entry('snd/dup', stp_datagram, pld=True, dup=True,
                                     fast=stp_datagram.fast_retransmit)
            self.send_datagram(stp_datagram.datagram)
        # Segment should be corrupted
        elif random() < self.p_corrupt:
            stp_datagram.corrupt_datagram()
            self.log.write_log_entry('snd/corr' + rxt, stp_datagram, pld=True, corr=True,
                                     timeout=stp_datagram.resend, fast=stp_datagram.fast_retransmit)
            self.send_datagram(stp_datagram.corrupted_datagram)
        # Segment should be reordered
        elif random() < self.p_order:
            if self.reordered_packet is None:
                self.reordered_packet = stp_datagram
                self.reordered_count = self.max_order
            else:
                self.log.write_log_entry('snd' + rxt, stp_datagram, pld=True,
                                         timeout=stp_datagram.resend, fast=stp_datagram.fast_retransmit)
                self.send_datagram(stp_datagram.datagram)
        # Segment should be delayed
        elif random() < self.p_delay:
            delay_until = uniform(0, self.max_delay) + time.time()
            self.delayed_packet.append((delay_until, stp_datagram))
        else:
            self.log.write_log_entry('snd' + rxt, stp_datagram, pld=True,
                                     timeout=stp_datagram.resend, fast=stp_datagram.fast_retransmit)
            self.send_datagram(stp_datagram.datagram)

    def send_datagram(self, datagram):
        self.reordered_count -= 1 if self.reordered_packet is not None else 0
        self.protocol.send_datagram(datagram)

        # Check if enough packets have been sent to send the reordered packet
        if self.reordered_packet is not None and self.reordered_count <= 0:
            stp_datagram = self.reordered_packet
            rxt = '/RXT' if stp_datagram.resend else ''
            self.reordered_packet = None
            self.log.write_log_entry('snd/rord' + rxt, stp_datagram, pld=True, rord=True,
                                     timeout=stp_datagram.resend, fast=stp_datagram.fast_retransmit)
            self.protocol.send_datagram(stp_datagram.datagram)

    # See if enough time has passed to send any delayed packets
    def send_delayed(self):
        new_delayed = list()
        current_time = time.time()
        for packet in self.delayed_packet:
            if packet[0] >= current_time:
                rxt = '/RXT' if packet[1].resend else ''
                self.log.write_log_entry('snd/dely' + rxt, packet[1], pld=True, dely=True,
                                         timeout=packet[1].resend, fast=packet[1].fast_retransmit)
                self.protocol.send_datagram(packet[1].datagram)
            else:
                new_delayed.append(packet)
        self.delayed_packet = new_delayed
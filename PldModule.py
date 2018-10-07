#!/usr/bin/python3.6

from random import seed, random
from StpDatagram import StpDatagram

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

    def pld_send(self, stp_datagram: StpDatagram):
        rxt = '/RXT' if stp_datagram.resend else ''
        # Setup and teardown skips PLD
        if stp_datagram.is_setup_teardown():
            self.log.write_log_entry('snd' + rxt, stp_datagram, timeout=stp_datagram.resend)
            self.protocol.send_datagram(stp_datagram.datagram)
        # Segment should be dropped
        elif random() < self.p_drop:
            self.log.write_log_entry('drop', stp_datagram, pld=True, drop=True)
            return
        # Segment should be duplicated
        elif random() < self.p_dupe:
            self.log.write_log_entry('snd' + rxt, stp_datagram, pld=True, timeout=stp_datagram.resend)
            self.protocol.send_datagram(stp_datagram.datagram)
            self.log.write_log_entry('snd/dup', stp_datagram, pld=True, dup=True)
            self.protocol.send_datagram(stp_datagram.datagram)
            return
        # Segment should be corrupted
        elif random() < self.p_corrupt:
            stp_datagram.corrupt_datagram()
            self.log.write_log_entry('snd/corr' + rxt, stp_datagram, pld=True, corr=True, timeout=stp_datagram.resend)
            self.protocol.send_datagram(stp_datagram.corrupted_datagram)
        else:
            self.log.write_log_entry('snd' + rxt, stp_datagram, pld=True, timeout=stp_datagram.resend)
            self.protocol.send_datagram(stp_datagram.datagram)
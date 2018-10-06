#!/usr/bin/python3.6

from random import seed, random
from StpDatagram import StpDatagram

class PldModule:

    def __init__(self, protocol, input_args):
        self.protocol = protocol
        seed(input_args['seed_val'])
        self.p_drop = input_args['p_drop']
        self.p_dupe = input_args['p_dupe']
        self.p_corrupt = input_args['p_corrupt']
        self.p_order = input_args['p_order']
        self.max_order = input_args['max_order']
        self.p_delay = input_args['p_delay']
        self.max_delay = input_args['max_delay']

    def pld_send(self, stp_datagram: StpDatagram):
        if stp_datagram.is_setup_teardown():
            self.protocol.send_datagram(stp_datagram.datagram)
        elif random() < self.p_drop:
            return
        else:
            self.protocol.send_datagram(stp_datagram.datagram)
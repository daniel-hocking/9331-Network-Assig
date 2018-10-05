#!/usr/bin/python3.6

from StpDatagram import StpDatagram

class PldModule:

    def __init__(self, protocol, input_args):
        self.protocol = protocol

    def pld_send(self, stp_datagram: StpDatagram):
        if stp_datagram.is_setup_teardown():
            self.protocol.send_datagram(stp_datagram.datagram)
        else:
            self.protocol.send_datagram(stp_datagram.datagram)
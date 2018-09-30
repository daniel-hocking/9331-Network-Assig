#!/usr/bin/python3.6

from socket import *

class StpProtocol:

    def __init__(self):
        self.sequence_num = 0
        self.buffer = dict()

    def _setup_connection(self):
        pass

    def create_datagram(self, data):
        pass

    def process_datagram(self, datagram):
        pass
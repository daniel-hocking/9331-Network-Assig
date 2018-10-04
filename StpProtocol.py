#!/usr/bin/python3.6

from socket import *
from PldModule import PldModule
from StpSegment import StpSegment

class StpProtocol:

    def __init__(self, source_ip='127.0.0.1', dest_ip='', source_port=0, dest_port=0, input_args=None):
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_port = source_port
        self.dest_port = dest_port
        if input_args is None:
            self.sender = False
            self.max_window_size = 1024
        else:
            self.sender = True
            self.stp_segment = StpSegment(input_args['filename'], input_args['max_seg_size'])
            self.pld_module = PldModule(input_args)
            self.max_window_size = input_args['max_window_size']
            self.max_seg_size = input_args['max_seg_size']
            self.gamma = input_args['gamma']
        self.sequence_num = 0
        self.ack_number = 0
        self.buffer = list()
        self._setup_connection()

    def __del__(self):
        self.socket.close()

    def _setup_connection(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.source_port))
        if not self.source_port:
            self.source_port = self.socket.getsockname()[1]

    def setup_reciever(self, datagram):
        if self.sender == False and datagram.syn:
            self.dest_port = datagram.header['dest_port']
            self.dest_ip = datagram.header['dest_ip']
            self.max_window_size = datagram.header['mws']
            self.stp_segment = StpSegment('test_r.pdf', self.max_window_size, mode='write')

    def update_nums(self, seq_num, ack_num):
        self.sequence_num = seq_num
        self.ack_number = ack_num

    def send_handshake(self, syn=False, ack=False, fin=False):
        # Used for connection establish/teardown requests
        pass

    def send(self):
        # If receiver then just create datagram and send
        # If sender than create datagram, add to buffer, send via PLD module
        pass

    def receive(self):
        # If receiver then check if it matches seq num and buffer if needed, send ack as apropriate
        # If sender then check if it matches ack num and resend as required, reset timer or continue sending data
        pass

    def send_datagram(self, datagram):
        print(f'sent {datagram}')
        self.socket.sendto(datagram, (self.dest_ip, self.dest_port))

    def receive_datagram(self):
        return self.socket.recv(self.max_window_size)

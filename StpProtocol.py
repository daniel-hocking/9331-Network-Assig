#!/usr/bin/python3.6

import time
from socket import *
from threading import Lock
from PldModule import PldModule
from StpSegment import StpSegment
from StpDatagram import StpDatagram

class StpProtocol:

    def __init__(self, source_ip='127.0.0.1', dest_ip='', source_port=0, dest_port=0, input_args=None):
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_port = source_port
        self.dest_port = dest_port
        self.ready = False
        self.complete = False
        self.should_ack = False
        self.lock = Lock()
        if input_args is None:
            self.sender = False
            self.max_window_size = 1024
        else:
            self.sender = True
            self.stp_segment = StpSegment(input_args['filename'], input_args['max_seg_size'])
            self.pld_module = PldModule(self, input_args)
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
        self.socket.settimeout(1)
        self.socket.bind(('', self.source_port))
        if not self.source_port:
            self.source_port = self.socket.getsockname()[1]

    def setup_reciever(self, datagram):
        if self.sender == False and datagram.syn:
            self.max_window_size = datagram.header['mws']
            self.stp_segment = StpSegment('test_r.pdf', self.max_window_size, mode='write')

    def update_nums(self, seq_num, ack_num):
        self.sequence_num = seq_num
        self.ack_number = ack_num

    def send_setup_teardown(self, syn=False, ack=False, fin=False):
        # Used for connection establish/teardown requests
        stp_datagram = StpDatagram(self, syn=syn, ack=ack, fin=fin, mws=self.max_window_size)
        self._send(stp_datagram)

    def receive_setup_teardown(self, syn=False, ack=False, fin=False):
        # Used to ensure that the correct response is received from setup/teardown requests
        stp_datagram = self._receive()
        if not stp_datagram:
            return False
        if stp_datagram.syn == syn and stp_datagram.ack == ack and stp_datagram.fin == fin:
            return True
        else:
            raise Exception('Incorrect handshake response received')

    def sender_send_loop(self):
        # If timeout reached then resend
        # If packet in triple dupe buffer then resend
        # If no data and all ack'd then send teardown packets
        # If timeout not started then start
        # If have data and window space then send datagram to PLD
        while True:
            if len(self.buffer):
                current_time = time.time()
                with self.lock:
                    for i in range(len(self.buffer)):
                        print(f'buffer a {i}')
                        if (current_time - self.buffer[i].time_created) > 1:
                            print(f'buffer b {i}')
                            stp_datagram = self.buffer.pop()
                            stp_datagram.time_created = current_time
                            stp_datagram.resend = True
                            self._send(stp_datagram)
                            break
            else:
                segment_data = self.stp_segment.read_segment()
                if not segment_data:
                    if len(self.buffer):
                        continue
                    self.complete = True
                    break
                stp_datagram = StpDatagram(self, data=segment_data)
                self._send(stp_datagram)

    def sender_receive_loop(self):
        # Wait for a packet to arrive
        # If this doesn't have resend flag set then update timeout
        # Check for triple dupe and fast retransmit, set flag
        # If fin flag set then end program
        # If there are packets in buffer that have seq < ack can remove from buffer
        # Also update the window if this happens: reduce active data count,
        # increase send base, and reset timer
        while True:
            stp_datagram = self._receive()
            if self.complete:
                break
            if not stp_datagram:
                continue
            if stp_datagram.fin:
                break
            with self.lock:
                for i in range(len(self.buffer) - 1, -1, -1):
                    print(f'buffer {i} ack {stp_datagram.ack_number}')
                    if self.buffer[i].sequence_num < stp_datagram.ack_number:
                        self.buffer.pop(i)

    def receiver_send_loop(self):
        # Whenever a packet received, then run this to send an ack
        # The value of the ack will depend on how many sequential packets have been received
        while True:
            if self.should_ack:
                self.send_setup_teardown(ack=True)
                self.should_ack = False
            if self.complete:
                break

    def receiver_receive_loop(self):
        # Wait for a packet to arrive
        # If fin flag set then end program
        # If sequence number matches expected and no corruption
        # Then save to file and send ack + len
        # If not expected sequence number then send ack and save to buffer
        # If corrupted then no ack
        while True:
            stp_datagram = self._receive()
            if not stp_datagram:
                continue
            if stp_datagram.fin:
                self.complete = True
                break
            self.stp_segment.write_segment(stp_datagram.data)
            self.should_ack = True

    def _send(self, stp_datagram: StpDatagram):
        # If receiver then just create datagram and send
        # If sender than create datagram, add to buffer, send via PLD module
        if self.sender:
            self.buffer.append(stp_datagram)
            self.pld_module.pld_send(stp_datagram)
        else:
            self.send_datagram(stp_datagram.datagram)

    def _receive(self):
        # If receiver then check if it matches seq num and buffer if needed, send ack as apropriate
        # If sender then check if it matches ack num and resend as required, reset timer or continue sending data
        datagram = self.receive_datagram()
        if not datagram:
            return None
        return StpDatagram(self, datagram=datagram)

    def send_datagram(self, datagram):
        self.socket.sendto(datagram, (self.dest_ip, self.dest_port))

    def receive_datagram(self):
        try:
            response, addr = self.socket.recvfrom(self.max_window_size + 100)
            if self.sender == False:
                self.dest_port = addr[1]
                self.dest_ip = addr[0]
        except timeout:
            return None
        return response

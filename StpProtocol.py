#!/usr/bin/python3.6

import time
from socket import *
from collections import deque
from threading import Lock
from PldModule import PldModule
from StpSegment import StpSegment
from StpDatagram import StpDatagram
from StpLog import StpLog
from RttModule import RttModule

class StpProtocol:

    def __init__(self, source_ip='127.0.0.1', dest_ip='', source_port=0, dest_port=0, input_args=None):
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_port = source_port
        self.dest_port = dest_port
        self.ready = False
        self.complete = False
        self.should_ack = 0
        self.prev_ack_sent = -1
        self.prev_ack_rcv = -1
        self.lock = Lock()
        self.seen_datagram = set()
        self.fast_retransmit = 0
        self.timer = False
        if input_args is None:
            self.sender = False
            self.max_window_size = 1024
            self.ack_queue = deque()
            self.log = StpLog(sender=False)
        else:
            self.sender = True
            self.stp_segment = StpSegment(input_args['filename'], input_args['max_seg_size'])
            self.log = StpLog(file_size=self.stp_segment.file_size)
            self.pld_module = PldModule(self, self.log, input_args)
            self.max_window_size = input_args['max_window_size']
            self.max_seg_size = input_args['max_seg_size']
            self.gamma = input_args['gamma']
            self.rtt_module = RttModule(self.gamma)
        self.sequence_num = 0
        self.ack_number = 0
        self.send_base = 0
        self.buffer = deque()
        self._setup_connection()

    def __del__(self):
        self.socket.close()

    def _setup_connection(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.settimeout(0.2)
        self.socket.bind(('', self.source_port))
        if not self.source_port:
            self.source_port = self.socket.getsockname()[1]

    def setup_reciever(self, datagram):
        if self.sender == False and datagram.syn:
            self.max_window_size = datagram.header['mws']
            self.stp_segment = StpSegment('test_r.pdf', self.max_window_size, mode='write')

    def update_nums(self, seq_num, ack_num):
        if self.sender:
            self.send_base = seq_num
        else:
            self.sequence_num = seq_num
        self.ack_number = ack_num

    def send_setup_teardown(self, syn=False, ack=False, fin=False, resend=False, trigger_seq=0):
        # Used for connection establish/teardown requests
        stp_datagram = StpDatagram(self, syn=syn, ack=ack, fin=fin, resend=resend,
                                   trigger_seq=trigger_seq, mws=self.max_window_size)
        self.sequence_num += 1 if syn or fin else 0
        self._send(stp_datagram)

    def receive_setup_teardown(self, syn=False, ack=False, fin=False):
        # Used to ensure that the correct response is received from setup/teardown requests
        while True:
            stp_datagram = self._receive()
            if not stp_datagram:
                continue
            if stp_datagram.syn == syn and stp_datagram.ack == ack and stp_datagram.fin == fin:
                break

    def sender_send_loop(self):
        # If timeout reached then resend
        # If packet in triple dupe buffer then resend
        # If no data and all ack'd then send teardown packets
        # If have data and window space then send datagram to PLD
        while True:
            self.pld_module.send_delayed()
            with self.lock:
                current_time = time.time()
                if len(self.buffer) > 0 and \
                        (self.fast_retransmit == 3 or
                        (current_time - self.timer) > self.rtt_module.get_timeout()):
                        stp_datagram = self.buffer.popleft()
                        print(f'current seq {stp_datagram.sequence_num} buffer size {len(self.buffer)}')
                        stp_datagram.resend = True
                        self.timer = current_time
                        fast_retransmit = self.fast_retransmit == 3
                        self.fast_retransmit = 0 if fast_retransmit else self.fast_retransmit
                        stp_datagram.fast_retransmit = fast_retransmit
                        stp_datagram.recreate_datagram()
                        self._send(stp_datagram)
                if ((self.sequence_num + self.max_seg_size) - self.send_base) <= self.max_window_size:
                    segment_data = self.stp_segment.read_segment()
                    if not segment_data:
                        if len(self.buffer):
                            continue
                        self.complete = True
                        break
                    stp_datagram = StpDatagram(self, data=segment_data)
                    self.sequence_num += len(segment_data)
                    if not self.timer:
                        self.timer = time.time()
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
                current_time = time.time()
                new_buffer = deque()
                for i in range(len(self.buffer)):
                    if self.buffer[i].sequence_num < stp_datagram.ack_number:
                        buffer_datagram = self.buffer[i]
                        if stp_datagram.trigger_seq == buffer_datagram.sequence_num and not stp_datagram.resend:
                            rtt = current_time - buffer_datagram.time_created
                            new_timeout = self.rtt_module.updated_timeout(rtt)
                            print(f'seq_num {stp_datagram.trigger_seq} rtt {rtt} timeout {new_timeout}')
                    else:
                        new_buffer.append(self.buffer[i])
                if len(self.buffer) != len(new_buffer):
                    if len(new_buffer) > 0:
                        self.timer = current_time
                    else:
                        self.timer = False
                self.buffer = new_buffer

    def receiver_send_loop(self):
        # Whenever a packet received, then run this to send an ack
        # The value of the ack will depend on how many sequential packets have been received
        while True:
            with self.lock:
                while len(self.ack_queue) > 0:
                    stp_datagram = self.ack_queue.pop()
                    self.send_setup_teardown(ack=True, resend=stp_datagram.resend,
                                             trigger_seq=stp_datagram.sequence_num)
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
            if stp_datagram.should_buffer:
                self.buffer.append(stp_datagram)
            elif not stp_datagram.is_dupe:
                self.stp_segment.write_segment(stp_datagram.data)
                # Check if any buffered datagram can match now
                new_buffer = deque()
                in_buffer = set()
                for i in range(len(self.buffer)):
                    buffer_segment = self.buffer[i]
                    if buffer_segment.update_if_next_segment():
                        self.stp_segment.write_segment(buffer_segment.data)
                    elif self.ack_number < buffer_segment.sequence_num and \
                            buffer_segment.sequence_num not in in_buffer:
                        in_buffer.add(buffer_segment.sequence_num)
                        new_buffer.append(buffer_segment)
                self.buffer = new_buffer
            with self.lock:
                self.ack_queue.appendleft(stp_datagram)

    def _send(self, stp_datagram: StpDatagram):
        # If receiver then just create datagram and send
        # If sender than create datagram, add to buffer, send via PLD module
        if self.sender:
            if not stp_datagram.is_setup_teardown():
                if stp_datagram.resend:
                    self.buffer.appendleft(stp_datagram)
                else:
                    self.buffer.append(stp_datagram)
            self.pld_module.pld_send(stp_datagram)
        else:
            if stp_datagram.ack_number == self.prev_ack_sent:
                self.log.write_log_entry('snd/DA', stp_datagram, dup=True)
            else:
                self.log.write_log_entry('snd', stp_datagram)
            self.prev_ack_sent = stp_datagram.ack_number
            self.send_datagram(stp_datagram.datagram)

    def _receive(self):
        # If receiver then check if it matches seq num and buffer if needed, send ack as appropriate
        # If sender then check if it matches ack num and resend as required, reset timer or continue sending data
        datagram = self.receive_datagram()
        if not datagram:
            return None
        stp_datagram = StpDatagram(self, datagram=datagram)
        if not stp_datagram.valid_datagram:
            self.log.write_log_entry('rcv/corr', stp_datagram, sent=False, err=True)
            self.fast_retransmit = 0
            return None
        elif self.sender and stp_datagram.ack_number == self.prev_ack_rcv:
            self.log.write_log_entry('rcv/DA', stp_datagram, sent=False, dup=True)
            self.fast_retransmit += 1
        else:
            self.log.write_log_entry('rcv', stp_datagram, sent=False, dup=stp_datagram.is_dupe)
            self.fast_retransmit = 0
        self.prev_ack_rcv = stp_datagram.ack_number
        return stp_datagram

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

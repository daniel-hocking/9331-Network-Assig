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

'''
The StpProtocol is the main class that runs the program, coordinating both sending
and receiving and managing access to the other classes
'''
class StpProtocol:

    def __init__(self, dest_ip='', source_port=0, dest_port=0, input_args=None, filename=''):
        self.dest_ip = dest_ip
        self.source_port = source_port
        self.dest_port = dest_port
        self.complete = False
        self.prev_ack_sent = -1
        self.prev_ack_rcv = -1
        self.lock = Lock()
        self.seen_datagram = set()
        self.fast_retransmit = 0
        self.timer = False
        if input_args is None:
            self.sender = False
            self.max_window_size = 1024
            self.log = StpLog(sender=False)
            self.filename = filename
            self.stp_segment = StpSegment(self.filename, mode='write')
        else:
            self.sender = True
            self.max_window_size = input_args['max_window_size']
            self.max_seg_size = input_args['max_seg_size']
            self.rtt_module = RttModule(input_args['gamma'])
            self.stp_segment = StpSegment(input_args['filename'], max_seg_size=self.max_seg_size)
            self.log = StpLog(file_size=self.stp_segment.file_size)
            self.pld_module = PldModule(self, self.log, input_args)
        self.sequence_num = 0
        self.ack_number = 0
        self.send_base = 0
        self.buffer = deque()
        self._setup_connection()

    def __del__(self):
        self.socket.close()

    def _setup_connection(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        # This timeout isn't used to timeout datagrams, as the receive loop is
        # an endless while loop, it is used so that it can check for other things
        # like if the program should end
        self.socket.settimeout(0.2)
        self.socket.bind(('', self.source_port))
        if not self.source_port:
            self.source_port = self.socket.getsockname()[1]

    def setup_reciever(self, datagram):
        if self.sender == False and datagram.syn:
            self.max_window_size = datagram.header['mws']

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

    # Used by the sender to send datagrams to the receiver
    def sender_send_loop(self):
        while True:
            # Start by checking if any delayed datagram should now be sent
            self.pld_module.send_delayed()
            # Get a lock as the buffer might otherwise be updated by the receiving thread
            with self.lock:
                current_time = time.time()
                # If there are items in the buffer and either: fast retransmit or the time
                # elapsed has reached the timeout value then its time to resend the datagram
                # at the start of the current sending window
                if len(self.buffer) > 0 and \
                        (self.fast_retransmit == 3 or
                        (current_time - self.timer) > self.rtt_module.get_timeout()):
                    stp_datagram = self.buffer.popleft()
                    stp_datagram.resend = True
                    self.timer = current_time
                    fast_retransmit = self.fast_retransmit == 3
                    self.fast_retransmit = 0 if fast_retransmit else self.fast_retransmit
                    stp_datagram.fast_retransmit = fast_retransmit
                    stp_datagram.recreate_datagram()
                    self._send(stp_datagram)
                # If the maximum window size won't be exceeded then send a new datagram
                if ((self.sequence_num + self.max_seg_size) - self.send_base) <= self.max_window_size:
                    segment_data = self.stp_segment.read_segment()
                    # If reached the end of the file then continue if buffer not empty, or end if it is
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
            # This small delay prevents the loop from maxing out a single core of
            # your cpu, it actually seems to improve overall performance too
            time.sleep(0.001)

    # Used by the sender to receive datagrams from the receiver
    def sender_receive_loop(self):
        while True:
            # Wait for a packet to arrive
            stp_datagram = self._receive()
            # This is why the timeout is needed, so complete can be checked
            if self.complete:
                break
            # If not datagram received then simply repeat
            if not stp_datagram:
                continue
            # If a fin segment is received then end (this should never happen)
            if stp_datagram.fin:
                break
            # Get a lock as the buffer might otherwise be updated by the sending thread
            with self.lock:
                current_time = time.time()
                new_buffer = deque()
                for i in range(len(self.buffer)):
                    buffer_datagram = self.buffer[i]
                    # If the sequence number that triggered the ack matches and it isn't a resent datagram
                    # then can update the RTT value
                    if stp_datagram.trigger_seq == buffer_datagram.sequence_num and not stp_datagram.resend:
                        rtt = current_time - buffer_datagram.time_created
                        new_timeout = self.rtt_module.updated_timeout(rtt)
                        print(f'seq_num {stp_datagram.trigger_seq} rtt {rtt} timeout {new_timeout}')
                    # If buffer item still needed then add it back into buffer
                    if buffer_datagram.sequence_num >= stp_datagram.ack_number:
                        new_buffer.append(buffer_datagram)
                if len(self.buffer) != len(new_buffer):
                    if len(new_buffer) > 0:
                        self.timer = current_time
                    else:
                        self.timer = False
                self.buffer = new_buffer

    # Used by the receiver to send datagrams to the sender
    def receiver_send_loop(self, stp_datagram):
        # Whenever a packet received, then run this to send an ack
        # The value of the ack will depend on how many sequential packets have been received
        self.send_setup_teardown(ack=True, resend=stp_datagram.resend,
                                 trigger_seq=stp_datagram.sequence_num)

    # Used by the receiver to receive datagrams from the sender
    def receiver_receive_loop(self):
        while True:
            # Wait for a datagram to arrive
            stp_datagram = self._receive()
            # If no datagram then repeat
            if not stp_datagram:
                continue
            # If fin received then end
            if stp_datagram.fin:
                break
            # It wasn't expected datagram so add to buffer
            if stp_datagram.should_buffer:
                self.buffer.append(stp_datagram)
            # It wasn't a dupe so write to file
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
            # Send ack
            self.receiver_send_loop(stp_datagram)

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
            if stp_datagram.ack and stp_datagram.ack_number == self.prev_ack_sent:
                self.log.write_log_entry('snd/DA', stp_datagram, dup=True)
            else:
                self.log.write_log_entry('snd', stp_datagram)
            if stp_datagram.ack:
                self.prev_ack_sent = stp_datagram.ack_number
            self.send_datagram(stp_datagram.datagram)

    def _receive(self):
        # If receiver then check if it matches seq num and buffer if needed, send ack as appropriate
        # If sender then check if it matches ack num and resend as required, reset timer or continue sending data
        datagram = self._receive_datagram()
        if not datagram:
            return None
        stp_datagram = StpDatagram(self, datagram=datagram)
        if not stp_datagram.valid_datagram:
            self.log.write_log_entry('rcv/corr', stp_datagram, sent=False, err=True)
            self.fast_retransmit = 0
            return None
        elif self.sender and stp_datagram.ack and stp_datagram.ack_number == self.prev_ack_rcv:
            self.log.write_log_entry('rcv/DA', stp_datagram, sent=False, dup=True)
            self.fast_retransmit += 1
        else:
            self.log.write_log_entry('rcv', stp_datagram, sent=False, dup=stp_datagram.is_dupe)
            self.fast_retransmit = 0
        if stp_datagram.ack:
            self.prev_ack_rcv = stp_datagram.ack_number
        return stp_datagram

    def send_datagram(self, datagram):
        self.socket.sendto(datagram, (self.dest_ip, self.dest_port))

    def _receive_datagram(self):
        try:
            response, addr = self.socket.recvfrom(self.max_window_size + 100)
            if self.sender == False:
                self.dest_port = addr[1]
                self.dest_ip = addr[0]
        except timeout:
            return None
        return response

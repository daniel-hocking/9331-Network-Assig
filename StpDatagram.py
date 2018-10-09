#!/usr/bin/python3.6

from struct import *
from random import randint
import time

'''
The StpDatagram is used to store a single STP datagram that is either to be sent
or has been received
'''
class StpDatagram:

    '''
    Header format I is an integer, H is a short:
    Sequence number
    Acknowledgement number
    Trigger sequence number
    Maximum window size
    Datagram size
    Checksum
    Flags
    '''
    header_format = 'IIIIHHH'

    def __init__(self, protocol, datagram=None, data=b'', mws=0,
                 syn=False, ack=False, fin=False, resend=False, trigger_seq=0):
        self.header_size = calcsize(self.header_format)
        self.protocol = protocol
        # Time created is used in RTT calculations
        self.time_created = time.time()
        self.is_dupe = False
        self.should_buffer = False
        self.fast_retransmit = False
        if datagram:
            self.datagram = datagram
            self._process_datagram()
        else:
            self.data = data
            self.mws = mws
            self.syn = syn
            self.ack = ack
            self.fin = fin
            self.resend = resend
            self.trigger_seq = trigger_seq
            self.sequence_num = self.protocol.sequence_num
            self.ack_number = self.protocol.ack_number
            self.datagram = self._create_datagram()

    # Create a new datagram to send
    def _create_datagram(self):
        self.datagram_size = self.header_size + len(self.data)
        flags = self._encode_flags()
        print(f'Creating datagram seq {self.sequence_num} and ack {self.ack_number}')
        '''
        The checksum is just a parity bit, either even or odd but I'm using 0 or 3
        to store it as these values won't effect the overall parity, like using 0 or 1 would
        '''
        checksum = 0
        header = self._get_packed_header(checksum, flags)
        pseudo_datagram = header + self.data
        if self._find_checksum(pseudo_datagram):
            checksum = 3
            header = self._get_packed_header(checksum, flags)
        self.header = {
            'seq_number': self.sequence_num,
            'ack_number': self.ack_number,
            'trigger_seq': self.trigger_seq,
            'mws': self.mws,
            'datagram_size': self.datagram_size,
            'checksum': checksum,
            'flags': flags,
        }
        return header + self.data

    # If values change then may need to recreate datagram
    def recreate_datagram(self):
        self.datagram = self._create_datagram()

    # Process a received datagram
    def _process_datagram(self):
        # Use array slicing with the known size of the header to find the header section of datagram
        header = self.datagram[:self.header_size:]
        header = unpack(self.header_format, header)
        flags = self._decode_flags(header[-1])
        self.header = {
            'seq_number': header[0],
            'ack_number': header[1],
            'trigger_seq': header[2],
            'mws': header[3],
            'datagram_size': header[4],
            'checksum': header[5],
            'flags': flags,
        }
        self.syn = flags[0]
        self.ack = flags[1]
        self.fin = flags[2]
        self.resend = flags[3]
        self.sequence_num = self.header['seq_number']
        self.ack_number = self.header['ack_number']
        self.trigger_seq = self.header['trigger_seq']
        self.data = self.datagram[self.header_size:self.header['datagram_size']:]
        # Check if the checksum matches what would be expected based on the received datagram
        self.valid_datagram = self._verify_checksum(self.datagram, self.header['checksum'])
        # Only update values if valid
        if self.valid_datagram:
            self.update_if_next_segment()
        # Setup MWS for receiver on first datagram received
        self.protocol.setup_reciever(self)

    def update_if_next_segment(self):
        # If the datagram matches the next one that is expected then update
        if self.protocol.ack_number == self.sequence_num:
            ack_inc = 1 if self.syn or self.fin else 0
            self.protocol.seen_datagram.add(self.sequence_num)
            self.protocol.update_nums(self.ack_number, self.sequence_num + ack_inc + len(self.data))
            return True
        # If the datagram has been seen before then its a dupe
        elif self.sequence_num in self.protocol.seen_datagram:
            self.is_dupe = True
        # If the datagram never seen before then store it for later when it may fit
        else:
            self.protocol.seen_datagram.add(self.sequence_num)
            self.should_buffer = True
        return False

    def is_setup_teardown(self):
        return self.syn or self.ack or self.fin

    def _get_packed_header(self, checksum, flags):
        return pack(self.header_format, self.sequence_num, self.ack_number,
                self.trigger_seq, self.mws, self.datagram_size, checksum, flags)

    '''
    Previously the ip and port were included in the header, to store the header compactly it
    was converted into an integer
    def _ip_to_int(self, ip_str):
        ip_str = '127.0.0.1' if ip_str == 'localhost' else ip_str
        return int(ipaddress.IPv4Address(ip_str))

    def _int_to_ip(self, ip_int):
        return str(ipaddress.IPv4Address(ip_int))
    '''

    # Flags stored using bitwise or to set individual bits of an int
    def _encode_flags(self):
        flags = 0
        flags = flags ^ 1 if self.syn else flags
        flags = flags ^ 2 if self.ack else flags
        flags = flags ^ 4 if self.fin else flags
        flags = flags ^ 8 if self.resend else flags
        return flags

    # Flags recovered using bitwise and to find which bits are set
    def _decode_flags(self, flags):
        syn = True if flags & 1 else False
        ack = True if flags & 2 else False
        fin = True if flags & 4 else False
        resend = True if flags & 8 else False
        return syn, ack, fin, resend

    '''
    The idea behind this function for calculating the parity of a byte is from:
    http://p-nand-q.com/python/algorithms/math/bit-parity.html
    '''
    def _byte_parity(self, b):
        parity = False
        while b:
            parity = not parity
            b &= b - 1
        return int(parity)

    '''
    Calculate the parity of each byte and then combine to find the overall
    parity of the whole datagram
    '''
    def _find_checksum(self, datagram):
        count = 0
        for b in datagram:
            count += 1 + self._byte_parity(b)
        return count % 2

    def _verify_checksum(self, datagram, checksum):
        calc_checksum = self._find_checksum(datagram)
        if (calc_checksum and checksum) or (not calc_checksum and not checksum):
            return True
        return False

    def corrupt_datagram(self):
        # Find a random byte somewhere in the data section of datagram
        corrupt_byte_index = randint(self.header_size, self.datagram_size - 1)
        # Separate into before, at, after the byte to corrupt
        corrupt_byte = self.datagram[corrupt_byte_index]
        before_bye = self.datagram[:corrupt_byte_index:]
        after_byte = self.datagram[corrupt_byte_index + 1::]

        # Find a random bit to corrupt in the byte
        corrupt_bit_index = randint(0, 7)
        # Flip just the bit in question
        corrupt_byte ^= 1 << corrupt_bit_index

        self.corrupted_datagram = before_bye + bytes([corrupt_byte]) + after_byte
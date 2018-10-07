#!/usr/bin/python3.6

from struct import *
from random import randint
import ipaddress
import time

class StpDatagram:

    header_format = 'IIHHIIIIHHH'

    def __init__(self, protocol, datagram=None, data=b'', mws=0,
                 syn=False, ack=False, fin=False, resend=False, trigger_seq=0):
        self.header_size = calcsize(self.header_format)
        self.protocol = protocol
        self.time_created = time.time()
        self.is_dupe = False
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

    def _create_datagram(self):
        self.datagram_size = self.header_size + len(self.data)
        flags = self._encode_flags()
        print(f'Creating datagram seq {self.sequence_num} and ack {self.ack_number}')
        checksum = 0
        header = self._get_packed_header(checksum, flags)
        pseudo_datagram = header + self.data
        if self._find_checksum(pseudo_datagram):
            checksum = 3
            header = self._get_packed_header(checksum, flags)
        self.header = {
            'source_ip': self.protocol.source_ip,
            'dest_ip': self.protocol.dest_ip,
            'source_port': self.protocol.source_port,
            'dest_port': self.protocol.dest_port,
            'seq_number': self.sequence_num,
            'ack_number': self.ack_number,
            'trigger_seq': self.trigger_seq,
            'mws': self.mws,
            'datagram_size': self.datagram_size,
            'checksum': checksum,
            'flags': flags,
        }
        return header + self.data

    def _process_datagram(self):
        header = self.datagram[:self.header_size:]
        data = self.datagram[self.header_size::]
        header = unpack(self.header_format, header)
        flags = self._decode_flags(header[-1])
        ack_inc = 1 if flags[0] or flags[2] else 0
        self.header = {
            'source_ip': self._int_to_ip(header[0]),
            'dest_ip': self._int_to_ip(header[1]),
            'source_port': header[2],
            'dest_port': header[3],
            'seq_number': header[4],
            'ack_number': header[5],
            'trigger_seq': header[6],
            'mws': header[7],
            'datagram_size': header[8],
            'checksum': header[9],
            'flags': flags,
        }
        self.syn = flags[0]
        self.ack = flags[1]
        self.fin = flags[2]
        self.resend = flags[3]
        self.sequence_num = self.header['seq_number']
        self.ack_number = self.header['ack_number']
        self.trigger_seq = self.header['trigger_seq']
        self.data = data
        self.valid_datagram = self._verify_checksum(self.datagram, self.header['checksum'])
        if self.valid_datagram:
            self._update_if_next_segment(self.ack_number, self.sequence_num + ack_inc + len(data))
        self.protocol.setup_reciever(self)

    def _update_if_next_segment(self, new_seq, new_ack):
        if self.protocol.ack_number == self.sequence_num:
            self.protocol.update_nums(new_seq, new_ack)
        else:
            self.is_dupe = True

    def is_setup_teardown(self):
        return self.syn or self.ack or self.fin

    def _get_packed_header(self, checksum, flags):
        return pack(self.header_format, self._ip_to_int(self.protocol.source_ip),
             self._ip_to_int(self.protocol.dest_ip), self.protocol.source_port,
             self.protocol.dest_port, self.sequence_num, self.ack_number,
                self.trigger_seq, self.mws, self.datagram_size, checksum, flags)

    def _ip_to_int(self, ip_str):
        ip_str = '127.0.0.1' if ip_str == 'localhost' else ip_str
        return int(ipaddress.IPv4Address(ip_str))

    def _int_to_ip(self, ip_int):
        return str(ipaddress.IPv4Address(ip_int))

    def _encode_flags(self):
        flags = 0
        flags = flags ^ 1 if self.syn else flags
        flags = flags ^ 2 if self.ack else flags
        flags = flags ^ 4 if self.fin else flags
        flags = flags ^ 8 if self.resend else flags
        return flags

    def _decode_flags(self, flags):
        syn = True if flags & 1 else False
        ack = True if flags & 2 else False
        fin = True if flags & 4 else False
        resend = True if flags & 4 else False
        return syn, ack, fin, resend

    def _byte_parity(self, b):
        parity = False
        while b:
            parity = not parity
            b &= b - 1
        return int(parity)

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
        corrupt_byte_index = randint(1, self.datagram_size - 1)
        corrupt_byte = self.datagram[corrupt_byte_index]
        before_bye = self.datagram[:corrupt_byte_index:]
        after_byte = self.datagram[corrupt_byte_index + 1::]

        corrupt_bit_index = randint(0, 7)
        corrupt_byte ^= 1 << corrupt_bit_index

        self.corrupted_datagram = before_bye + bytes([corrupt_byte]) + after_byte
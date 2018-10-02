#!/usr/bin/python3.6

from struct import *
from socket import *
import ipaddress

class StpProtocol:

    header_format = 'IIHHIIHHH'

    def __init__(self, source_ip = '127.0.0.1', dest_ip = '', source_port = 0, dest_port = 0, sender = True):
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_port = source_port
        self.dest_port = dest_port
        self.sender = sender
        self.sequence_num = 0
        self.ack_number = 0
        self.buffer = dict()
        self.header_size = calcsize(self.header_format)
        self._setup_connection()

    def __del__(self):
        self.socket.close()

    def _setup_connection(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('', self.source_port))
        if not self.source_port:
            self.source_port = self.socket.getsockname()[1]

    def send_datagram(self, datagram):
        print(f'sent {datagram}')
        self.socket.sendto(datagram, (self.dest_ip, self.dest_port))

    def receive_datagram(self):
        return self.socket.recv(1024)

    def create_datagram(self, data, syn = False, ack = False, fin = False):
        datagram_size = self.header_size + len(data)
        flags = self._encode_flags(syn, ack, fin)
        print(f'Creating datagram seq {self.sequence_num} and ack {self.ack_number}')
        header = pack(self.header_format, self._ip_to_int(self.source_ip), self._ip_to_int(self.dest_ip), self.source_port,
                      self.dest_port, self.sequence_num, self.ack_number, datagram_size, datagram_size, flags)
        return header + data

    def process_datagram(self, datagram):
        header = datagram[:self.header_size:]
        data = datagram[self.header_size::]
        header = unpack(self.header_format, header)
        flags = self._decode_flags(header[-1])
        ack_inc = 1 if flags[0] or flags[1] or flags[2] else 0
        header = header[:-1:] + flags
        self.dest_port = header[2]
        self.dest_ip = self._int_to_ip(header[1])
        self.sequence_num = header[5]
        self.ack_number = header[4] + ack_inc + len(data)
        return (header, data)

    def _ip_to_int(self, ip_str):
        ip_str = '127.0.0.1' if ip_str == 'localhost' else ip_str
        return int(ipaddress.IPv4Address(ip_str))

    def _int_to_ip(self, ip_int):
        return str(ipaddress.IPv4Address(ip_int))

    def _encode_flags(self, syn, ack, fin):
        flags = 0
        flags = flags ^ 1 if syn else flags
        flags = flags ^ 2 if ack else flags
        flags = flags ^ 4 if fin else flags
        return flags

    def _decode_flags(self, flags):
        syn = True if flags & 1 else False
        ack = True if flags & 2 else False
        fin = True if flags & 4 else False
        return syn, ack, fin
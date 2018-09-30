#!/usr/bin/python3.6

from struct import *
import ipaddress

class StpProtocol:

    def __init__(self, source_ip, dest_ip, source_port, dest_port):
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_port = source_port
        self.dest_port = dest_port
        self.sequence_num = 0
        self.ack_number = 0
        self.buffer = dict()

    def _setup_connection(self):
        pass

    def create_datagram(self, data, syn = '0', ack = '0', fin = '0'):
        data = data
        datagram_size = 27 + len(data)
        header = pack('IIHHIIHHccc', self._ip_to_int(self.source_ip), self._ip_to_int(self.dest_ip), self.source_port,
                      self.dest_port, self.sequence_num, self.ack_number, datagram_size, datagram_size,
                      syn.encode('ascii'), ack.encode('ascii'), fin.encode('ascii'))
        return header + data

    def process_datagram(self, datagram):
        header = datagram[:27:]
        data = datagram[27::]
        header = unpack('IIHHIIHHccc', header)
        self.dest_port = header[3]
        self.dest_ip = header[1]
        self.sequence_num = header[4]
        self.ack_number = header[5]
        return (header, data)

    def _ip_to_int(self, ip_str):
        ip_str = '127.0.0.1' if ip_str == 'localhost' else ip_str
        return int(ipaddress.IPv4Address(ip_str))

    def _int_to_ip(self, ip_int):
        return str(ipaddress.IPv4Address(ip_int))
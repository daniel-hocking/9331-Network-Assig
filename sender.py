#!/usr/bin/python3.6

import sys
from socket import *
from StpSegment import StpSegment
from StpProtocol import StpProtocol

if len(sys.argv) != 4:
    print('python sender.py host port filename (host, port and filename must be \
provided as arguments')
    sys.exit()

receiver_host = str(sys.argv[1])
receiver_port = int(sys.argv[2])
filename = sys.argv[3]
max_seg_size = 500
sender_socket = socket(AF_INET, SOCK_DGRAM)
sender_socket.bind(('', 0))
sender_port = sender_socket.getsockname()[1]

count = sender_port
stp_segment = StpSegment(filename, max_seg_size)
stp_protocol = StpProtocol('127.0.0.1', receiver_host, sender_port, receiver_port)

sender_socket.sendto(stp_protocol.create_datagram(str.encode(str(sender_port))), (receiver_host, receiver_port))

while True:
    segment_data = stp_segment.read_segment()
    if not segment_data:
        break
    datagram = stp_protocol.create_datagram(segment_data)
    print(len(datagram))
    sender_socket.sendto(datagram, (receiver_host, receiver_port))
    segment = sender_socket.recv(1024)
    segment_processed = stp_protocol.process_datagram(segment)
    print(f'received ack {segment_processed[0]}')
    count += 1

sender_socket.sendto(stp_protocol.create_datagram(str.encode('done')), (receiver_host, receiver_port))
sender_socket.close()

print("done")

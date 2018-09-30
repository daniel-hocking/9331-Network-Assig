#!/usr/bin/python3.6

import sys
from socket import *
from StpSegment import StpSegment
from StpProtocol import StpProtocol

if len(sys.argv) != 3:
  print('python receiver.py port filename (port must be \
provided as argument')
  sys.exit()

receiver_port = int(sys.argv[1])
receiver_socket = socket(AF_INET, SOCK_DGRAM)
receiver_socket.bind(('', receiver_port))
filename = sys.argv[2]
max_seg_size = 500

stp_segment = StpSegment(filename, max_seg_size, 'write')
stp_protocol = StpProtocol('127.0.0.1', '', receiver_port, 0)

segment = receiver_socket.recv(1024)
sender_port = int(stp_protocol.process_datagram(segment)[1].decode())
count = sender_port
while True:
    segment = receiver_socket.recv(1024)
    segment_process = stp_protocol.process_datagram(segment)
    if segment_process[1] == b'done':
        receiver_socket.close()
        break
    stp_segment.write_segment(segment_process[1])
    receiver_socket.sendto(stp_protocol.create_datagram(str.encode(str(count))), ('localhost', sender_port))
    print(count)
    count += 1

#!/usr/bin/python3.6

import sys
from socket import *
from StpSegment import StpSegment

if len(sys.argv) != 3:
  print('python receiver.py port filename (port must be \
provided as argument')
  sys.exit()

server_port = int(sys.argv[1])
receiver_socket = socket(AF_INET, SOCK_DGRAM)
receiver_socket.bind(('', server_port))
filename = sys.argv[2]
max_seg_size = 1000

count = 1
stp_segment = StpSegment(filename, max_seg_size, 'write')

while True:
    segment = receiver_socket.recv(1024)
    print(count)
    count += 1
    if segment == b'done':
        receiver_socket.close()
        break
    stp_segment.write_segment(segment)

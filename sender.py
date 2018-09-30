#!/usr/bin/python3.6

import sys
from time import time, sleep
from socket import *
from StpSegment import StpSegment

if len(sys.argv) != 4:
    print('python sender.py host port filename (host, port and filename must be \
provided as arguments')
    sys.exit()

receiver_name = str(sys.argv[1])
receiver_port = int(sys.argv[2])
filename = sys.argv[3]
max_seg_size = 1000
sender_socket = socket(AF_INET, SOCK_DGRAM)
#sender_socket.bind(('', receiver_port))
#sender_socket.connect((receiver_name, receiver_port))

count = 1
stp_segment = StpSegment(filename, max_seg_size)

while True:
    segment_data = stp_segment.read_segment()
    if not segment_data:
        break
    sender_socket.sendto(segment_data, (receiver_name, receiver_port))
    print(count)
    count += 1
    sleep(0.01)

sender_socket.sendto(str.encode('done'), (receiver_name, receiver_port))
sender_socket.close()

print("done")

#!/usr/bin/python3.6

import sys
from time import time, sleep
from socket import *

if len(sys.argv) != 4:
    print('python sender.py host port filename (host, port and filename must be \
provided as arguments')
    sys.exit()

receiver_name = str(sys.argv[1])
receiver_port = int(sys.argv[2])
filename = sys.argv[3]
max_seg_size = 1000
sender_socket = socket(AF_INET, SOCK_DGRAM)
sender_socket.settimeout(1)
sender_socket.connect((receiver_name, receiver_port))

count = 1
with open(filename, mode='rb') as f:
    while True:
        segment_data = f.read(max_seg_size)
        if not segment_data:
            break
        sender_socket.send(segment_data)
        print(count)
        count += 1
        sleep(0.01)

sender_socket.send(str.encode('done'))
sender_socket.close()

print("done")

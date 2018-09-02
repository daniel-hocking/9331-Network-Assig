#!/usr/bin/python3.6

import sys
from time import time
from socket import *

if len(sys.argv) != 3:
    print('python sender.py host port (host and port must be \
provided as arguments')
    sys.exit()

receiver_name = str(sys.argv[1])
receiver_port = int(sys.argv[2])
sender_socket = socket(AF_INET, SOCK_DGRAM)
sender_socket.settimeout(1)
sender_socket.connect((receiver_name, receiver_port))

for i in range(10):
    sent_time = time()
    message = f'PING {i} {sent_time}\n'
    sender_socket.send(str.encode(message))
sender_socket.send(str.encode('done'))
sender_socket.close()

print("done")

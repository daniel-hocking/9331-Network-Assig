#!/usr/bin/python3.6

import sys
from socket import *

if len(sys.argv) != 2:
  print('python receiver.py port (port must be \
provided as argument')
  sys.exit()

server_port = int(sys.argv[1])
receiver_socket = socket(AF_INET, SOCK_DGRAM)
receiver_socket.bind(('', server_port))

count = 1
with open('file_r.pdf', mode='wb') as f:
    while True:
        segment = receiver_socket.recv(1024)
        print(count)
        count += 1
        if segment == b'done':
            receiver_socket.close()
            break
        f.write(segment)

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

while 1:
  sentence = receiver_socket.recv(1024)
  print(sentence.decode())
  if sentence.decode() == 'done':
    receiver_socket.close()
    break

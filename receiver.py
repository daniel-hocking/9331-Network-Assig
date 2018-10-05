#!/usr/bin/python3.6

import sys
from StpProtocol import StpProtocol

if len(sys.argv) != 3:
  print('python receiver.py port filename (port must be \
provided as argument')
  sys.exit()

receiver_port = int(sys.argv[1])
filename = sys.argv[2]

stp_protocol = StpProtocol(source_port=receiver_port)

# 3-way handshake
connection_received = False
while not connection_received:
    connection_received = stp_protocol.receive_setup_teardown(syn=True)
    print("Connection loop")
stp_protocol.send_setup_teardown(syn=True, ack=True)
ack_received = False
while not ack_received:
    ack_received = stp_protocol.receive_setup_teardown(ack=True)
    print("Ack loop")

sender_success = True
receiver_successs = True
while sender_success:
    sender_success = stp_protocol.receiver_send_loop()
    receiver_successs = stp_protocol.receiver_receive_loop()
    if stp_protocol.complete:
        break

stp_protocol.send_setup_teardown(fin=True, ack=True)
stp_protocol.receive_setup_teardown(ack=True)

print("done")
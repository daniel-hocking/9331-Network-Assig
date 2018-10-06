#!/usr/bin/python3.6

import sys
from threading import Thread
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
stp_protocol.receive_setup_teardown(ack=True)

send_thread = Thread(target=stp_protocol.receiver_send_loop)
receive_thread = Thread(target=stp_protocol.receiver_receive_loop)

send_thread.start()
receive_thread.start()

send_thread.join()
print("send thread ended")
receive_thread.join()
print("receive thread ended")

stp_protocol.send_setup_teardown(ack=True)
stp_protocol.send_setup_teardown(fin=True)
stp_protocol.receive_setup_teardown(ack=True)

stp_protocol.log.write_summary()

print("done")
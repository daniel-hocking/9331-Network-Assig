#!/usr/bin/python3.6

import sys
from threading import Thread
from StpProtocol import StpProtocol

if len(sys.argv) != 3:
    print('python receiver.py port filename (port must be provided as argument')
    sys.exit()

receiver_port = int(sys.argv[1])
filename = sys.argv[2]

# Setup StpProtocol object, this handles everything related to the running of the protocol
stp_protocol = StpProtocol(source_port=receiver_port, filename=filename)

# 3-way handshake
stp_protocol.receive_setup_teardown(syn=True)
stp_protocol.send_setup_teardown(syn=True, ack=True)
stp_protocol.receive_setup_teardown(ack=True)

# Used to use a different thread for sending and receiving like in sender.py
# Found it wasn't needed so simply combined into a single thread
receive_thread = Thread(target=stp_protocol.receiver_receive_loop)
receive_thread.start()
receive_thread.join()

# 4-segment connection termination, the first fin is received by the thread causing it to end
stp_protocol.send_setup_teardown(ack=True)
stp_protocol.send_setup_teardown(fin=True)
stp_protocol.receive_setup_teardown(ack=True)

# Write the final summary in the log
stp_protocol.log.write_summary()

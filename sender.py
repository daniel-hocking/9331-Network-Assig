#!/usr/bin/python3.6

import sys
from threading import Thread
from StpProtocol import StpProtocol

num_args = len(sys.argv)
if num_args < 4:
    print('python sender.py host port filename (host, port and filename must be provided as arguments')
    sys.exit()

input_args = {
    'receiver_host': sys.argv[1],
    'receiver_port': int(sys.argv[2]),
    'filename': sys.argv[3],
    'max_window_size': int(sys.argv[4]) if num_args >= 5 else 1000,
    'max_seg_size': int(sys.argv[5]) if num_args >= 6 else 500,
    'gamma': int(sys.argv[6]) if num_args >= 7 else 4,
    'p_drop': float(sys.argv[7]) if num_args >= 8 else 0,
    'p_dupe': float(sys.argv[8]) if num_args >= 9 else 0,
    'p_corrupt': float(sys.argv[9]) if num_args >= 10 else 0,
    'p_order': float(sys.argv[10]) if num_args >= 11 else 0,
    'max_order': int(sys.argv[11]) if num_args >= 12 else 0,
    'p_delay': float(sys.argv[12]) if num_args >= 13 else 0,
    'max_delay': int(sys.argv[13]) if num_args >= 14 else 0,
    'seed_val': int(sys.argv[14]) if num_args >= 15 else 100,
}

# Setup StpProtocol object, this handles everything related to the running of the protocol
stp_protocol = StpProtocol(dest_ip=input_args['receiver_host'], dest_port=input_args['receiver_port'], input_args=input_args)

# 3-way handshake
stp_protocol.send_setup_teardown(syn=True)
stp_protocol.receive_setup_teardown(syn=True, ack=True)
stp_protocol.send_setup_teardown(ack=True)

# Start a thread for sending and receiving so they don't block each other
send_thread = Thread(target=stp_protocol.sender_send_loop)
receive_thread = Thread(target=stp_protocol.sender_receive_loop)
send_thread.start()
receive_thread.start()
# Wait for both threads to end before sending the termination segments
send_thread.join()
receive_thread.join()

# 4-segment connection termination
stp_protocol.send_setup_teardown(fin=True)
stp_protocol.receive_setup_teardown(ack=True)
stp_protocol.receive_setup_teardown(fin=True)
stp_protocol.send_setup_teardown(ack=True)

# Write the final summary in the log
stp_protocol.log.write_summary()
print(input_args)

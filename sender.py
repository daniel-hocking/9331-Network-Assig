#!/usr/bin/python3.6

import sys
from StpProtocol import StpProtocol

num_args = len(sys.argv)
if num_args < 4:
    print('python sender.py host port filename (host, port and filename must be \
provided as arguments')
    sys.exit()

receiver_host = sys.argv[1]
receiver_port = int(sys.argv[2])
filename = sys.argv[3]
max_window_size = int(sys.argv[4]) if num_args >= 5 else 1
max_seg_size = int(sys.argv[5]) if num_args >= 6 else 500
gamma = int(sys.argv[6]) if num_args >= 7 else 4
p_drop = float(sys.argv[7]) if num_args >= 8 else 0.1
p_dupe = float(sys.argv[8]) if num_args >= 9 else 0.1
p_corrupt = float(sys.argv[9]) if num_args >= 10 else 0.1
p_order = float(sys.argv[10]) if num_args >= 11 else 0.1
max_order = int(sys.argv[11]) if num_args >= 12 else 2
p_delay = float(sys.argv[12]) if num_args >= 13 else 0.1
max_delay = int(sys.argv[13]) if num_args >= 14 else 250
seed_val = int(sys.argv[14]) if num_args >= 15 else 300

input_args = {
    'receiver_host': receiver_host,
    'receiver_port': receiver_port,
    'filename': filename,
    'max_window_size': max_window_size,
    'max_seg_size': max_seg_size,
    'gamma': gamma,
    'p_drop': p_drop,
    'p_dupe': p_dupe,
    'p_corrupt': p_corrupt,
    'p_order': p_order,
    'max_order': max_order,
    'p_delay': p_delay,
    'max_delay': max_delay,
    'seed_val': seed_val,
}

count = 0
stp_protocol = StpProtocol(dest_ip=receiver_host, dest_port=receiver_port, input_args=input_args)

# 3-way handshake
stp_protocol.send_setup_teardown(syn=True)
stp_protocol.receive_setup_teardown(syn=True, ack=True)
stp_protocol.send_setup_teardown(ack=True)
while True:
    segment_data = stp_segment.read_segment()
    if not segment_data:
        break
    datagram = stp_protocol.create_datagram(segment_data)
    stp_protocol.send_datagram(datagram)
    segment = stp_protocol.receive_datagram()
    segment_processed = stp_protocol.process_datagram(segment)
    print(f'received ack {segment_processed[0]}')
    count += 1

stp_protocol.send_datagram(stp_protocol.create_datagram(str.encode('done')))

print("done")

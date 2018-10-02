#!/usr/bin/python3.6

import sys
from StpSegment import StpSegment
from StpProtocol import StpProtocol

if len(sys.argv) != 4:
    print('python sender.py host port filename (host, port and filename must be \
provided as arguments')
    sys.exit()

receiver_host = str(sys.argv[1])
receiver_port = int(sys.argv[2])
filename = sys.argv[3]
max_seg_size = 500

count = 0
stp_segment = StpSegment(filename, max_seg_size)
stp_protocol = StpProtocol(dest_ip = receiver_host, dest_port = receiver_port)

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

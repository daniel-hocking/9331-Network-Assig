#!/usr/bin/python3.6

import sys
from StpSegment import StpSegment
from StpProtocol import StpProtocol

if len(sys.argv) != 3:
  print('python receiver.py port filename (port must be \
provided as argument')
  sys.exit()

receiver_port = int(sys.argv[1])
filename = sys.argv[2]
max_seg_size = 500

stp_segment = StpSegment(filename, max_seg_size, 'write')
stp_protocol = StpProtocol(source_port = receiver_port, sender = False)

count = 0
while True:
    segment = stp_protocol.receive_datagram()
    segment_process = stp_protocol.process_datagram(segment)
    print(f'received ack {segment_process[0]}')
    if segment_process[1] == b'done':
        break
    stp_segment.write_segment(segment_process[1])
    stp_protocol.send_datagram(stp_protocol.create_datagram(b''))
    print(count)
    count += 1

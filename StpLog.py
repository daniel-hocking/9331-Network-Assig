#!/usr/bin/python3.6

import time

'''
The StpLog class is used to log segments that have been sent or received
and also to keep track of summary stats
'''
class StpLog:

    '''
    Columns:
    <event> <time> <packet-type> <seq#> <data-bytes> <ack#>

    Event types:
    snd
    rcv
    drop
    corr
    dup
    rord
    dely
    DA
    RXT

    Packet types;
    S, A, F, D
    '''
    def __init__(self, sender=True, file_size=0):
        self.start_time = time.time()
        self.sender = sender
        self.total_dupe_recv = 0
        if self.sender:
            self.file_size = file_size
            self.total_sent = 0
            self.total_pld = 0
            self.total_dropped = 0
            self.total_corrupted = 0
            self.total_reordered = 0
            self.total_duplicated = 0
            self.total_delayed = 0
            self.total_timeout = 0
            self.total_fast_retrans = 0
        else:
            self.total_bytes = 0
            self.total_recv = 0
            self.total_data_recv = 0
            self.total_errors = 0
            self.total_dupe_sent = 0
        self._create_log_file()

    def __del__(self):
        self.file.close()

    def _create_log_file(self):
        filename = 'Sender_log.txt' if self.sender else 'Receiver_log.txt'
        self.file = open(filename, 'w')

    def write_log_entry(self, event, datagram, sent=True, pld=False, drop=False, corr=False,
                        rord=False, dup=False, dely=False, timeout=False, fast=False, err=False):
        log_time = time.time() - self.start_time
        packet_type = ('S' if datagram.syn else '') + \
                        ('A' if datagram.ack else '') + \
                        ('F' if datagram.fin else '') + \
                        ('D' if datagram.data else '')
        seq_num = datagram.sequence_num
        data_bytes = len(datagram.data)
        ack_num = datagram.ack_number
        self.file.write(f'{event:<15} {log_time:>12.2f} {packet_type:>12} {seq_num:>12} {data_bytes:>12} {ack_num:>12}\n')

        if self.sender:
            self.total_sent += 1 if sent else 0
            self.total_pld += 1 if pld else 0
            self.total_dropped += 1 if drop else 0
            self.total_corrupted += 1 if corr else 0
            self.total_reordered += 1 if rord else 0
            self.total_duplicated += 1 if sent and dup else 0
            self.total_delayed += 1 if dely else 0
            self.total_timeout += 1 if timeout else 0
            self.total_fast_retrans += 1 if fast else 0
            self.total_dupe_recv += 1 if not sent and dup else 0
        else:
            self.total_recv += 1 if not sent else 0
            self.total_bytes += data_bytes
            self.total_data_recv += 1 if data_bytes > 0 else 0
            self.total_errors += 1 if err else 0
            self.total_dupe_sent += 1 if sent and dup else 0
            self.total_dupe_recv += 1 if not sent and dup else 0

    def write_summary(self):
        self.file.write('=============================================================\n')
        if self.sender:
            self.file.write('Size of the file (in Bytes)'.ljust(50) + f'{self.file_size:>8}' + '\n')
            self.file.write('Segments transmitted (including drop & RXT)'.ljust(50) + f'{self.total_sent:>8}' + '\n')
            self.file.write('Number of Segments handled by PLD'.ljust(50) + f'{self.total_pld:>8}' + '\n')
            self.file.write('Number of Segments dropped'.ljust(50) + f'{self.total_dropped:>8}' + '\n')
            self.file.write('Number of Segments Corrupted'.ljust(50) + f'{self.total_corrupted:>8}' + '\n')
            self.file.write('Number of Segments Re-ordered'.ljust(50) + f'{self.total_reordered:>8}' + '\n')
            self.file.write('Number of Segments Duplicated'.ljust(50) + f'{self.total_duplicated:>8}' + '\n')
            self.file.write('Number of Segments Delayed'.ljust(50) + f'{self.total_delayed:>8}' + '\n')
            self.file.write('Number of Retransmissions due to TIMEOUT'.ljust(50) + f'{self.total_timeout:>8}' + '\n')
            self.file.write('Number of FAST RETRANSMISSION'.ljust(50) + f'{self.total_fast_retrans:>8}' + '\n')
            self.file.write('Number of DUP ACKS received'.ljust(50) + f'{self.total_dupe_recv:>8}' + '\n')
        else:
            self.file.write('Amount of data received (bytes)'.ljust(50) + f'{self.total_bytes:>8}' + '\n')
            self.file.write('Total Segments Received'.ljust(50) + f'{self.total_recv:>8}' + '\n')
            self.file.write('Data segments received'.ljust(50) + f'{self.total_data_recv:>8}' + '\n')
            self.file.write('Data segments with Bit Errors'.ljust(50) + f'{self.total_errors:>8}' + '\n')
            self.file.write('Duplicate data segments received'.ljust(50) + f'{self.total_dupe_recv:>8}' + '\n')
            self.file.write('Duplicate ACKs sent'.ljust(50) + f'{self.total_dupe_sent:>8}' + '\n')
        self.file.write('=============================================================\n')
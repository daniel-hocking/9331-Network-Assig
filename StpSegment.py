#!/usr/bin/python3.6

import os
import math

class StpSegment:

    def __init__(self, filename, max_seg_size, mode='read'):
        self.file_name = filename
        self.max_seg_size = max_seg_size
        self.write_mode = True if mode == 'write' else False
        self._file_setup()
        self.current_segment = 0

    def __del__(self):
        self.file.close()

    def _file_setup(self):
        mode = 'wb' if self.write_mode else 'rb'
        self.file = open(self.file_name, mode)
        self.file_size = os.path.getsize(self.file.name)
        self.num_segments = math.ceil(self.file_size / self.max_seg_size)

    def read_segment(self):
        if self.write_mode:
            raise Exception('Read mode not set, can\'t read data from file')
        self.current_segment += 1
        return self.file.read(self.max_seg_size)

    def write_segment(self, data):
        if not self.write_mode:
            raise Exception('Write mode not set, can\'t write data to file')
        self.file.write(data)
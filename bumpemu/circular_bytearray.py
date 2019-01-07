#      Copyright (C) 2019  Frank Riley
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging


class CircularByteArray:
    def __init__(self, nbytes):
        self._logger = logging.getLogger(__name__)
        self._buf = bytearray(nbytes)
        self._write_idx = 0
        self._read_idx = -1

    @property
    def read_index(self):
        return self._read_idx + 1

    @property
    def write_index(self):
        return self._write_idx

    def capacity(self):
        return len(self._buf)

    def size(self):
        return self._write_idx - (self._read_idx + 1)

    def available(self):
        return len(self._buf) - self.size()

    def clear(self):
        self._read_idx = self._write_idx - 1

    def is_empty(self):
        return self.size() == 0

    def is_full(self):
        return self.available() == 0

    def append(self, data):
        if self.available() >= len(data):
            start = self._real_index(self._write_idx)

            jj = 0
            for ii in range(start, min(start + len(data), len(self._buf))):
                self._buf[ii] = data[jj]
                jj += 1
            for ii in range(0, len(data) - jj):
                self._buf[ii] = data[jj]
                jj += 1
            assert jj == len(data)

            self._write_idx += len(data)
            return True
        return False

    def consume(self, nbytes):
        if self.size() >= nbytes:
            data = self.__getitem__(slice(self.read_index, self.read_index + nbytes))
            self._read_idx += nbytes
            return data
        return None

    def advance(self, nbytes):
        self._read_idx += nbytes

    def peek(self):
        if self.size():
            return self.__getitem__(self.read_index)
        return None

    def __getitem__(self, val):
        if isinstance(val, slice):
            start = val.start
            if start is None:
                start = self.read_index
            if start < self.read_index or start >= self.write_index:
                raise IndexError

            stop = val.stop
            if stop <= self.read_index or stop > self.write_index:
                raise IndexError

            if stop <= start:
                return []

            nbytes = stop - start
            real_start = self._real_index(start)
            real_stop = self._real_index(stop)
            if real_start <= real_stop:
                return bytearray(self._buf[real_start:real_stop])
            else:
                buf = bytearray(nbytes)
                jj = 0
                for ii in range(real_start, len(self._buf)):
                    buf[jj] = self._buf[ii]
                    jj += 1
                for ii in range(0, real_stop):
                    buf[jj] = self._buf[ii]
                    jj += 1
                assert jj == len(buf)
                assert jj == nbytes
                return buf
        elif isinstance(val, int):
            if val < self.read_index or val >= self.write_index:
                raise IndexError
            return self._buf[self._real_index(val)]
        else:
            raise TypeError

    def _real_index(self, val):
        return val % len(self._buf)

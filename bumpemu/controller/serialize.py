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

import struct


def append_array(buf, arr, append_func=None):
    if append_func:
        for ii in arr:
            append_func(buf, ii)
    else:
        for ii in arr:
            buf.append(ii)


def append_bool(buf, val):
    buf.append(1 if int(val) else 0)


def _append_struct(buf, val, fmt):
    for bb in struct.pack(fmt, int(val)):
        buf.append(bb)


def append_uint16(buf, val):
    _append_struct(buf, int(val), '<H')


def append_int32(buf, val):
    _append_struct(buf, int(val), '<l')


def append_uint32(buf, val):
    _append_struct(buf, int(val), '<L')


def append_str(buf, val, length):
    if val is None:
        val = ''
    for ii in val[:min(length, len(val))]:
        buf.append(ord(ii))
    for ii in range(length - len(val)):
        buf.append(0x0)


def read_uint16(buf):
    return struct.unpack('<H', buf)[0]

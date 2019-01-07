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

import os


def ignore_exc(func):
    # noinspection PyBroadException
    try:
        func()
    except:
        pass


def crc16(data, init):
    crc = init
    for bb in data:
        for _ in range(8):
            if (bb ^ crc) & 1:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
            bb >>= 1
    return crc


def rotate_bit16_left(val, nrolls):
    while nrolls:
        bit = (val & (1 << 15)) >> 15
        val <<= 1
        val |= bit
        nrolls -= 1
    return val & 0xffff


def checksum(data, init):
    assert ((len(data) % 2) == 0)
    cksum = init
    for ii in range(0, len(data), 2):
        cksum += ((data[ii] << 8) | data[ii + 1])
        cksum = rotate_bit16_left(cksum & 0xffff, 2)
    return cksum


def byte_to_char(val):
    if 0x20 <= val <= 0x7d:
        return chr(val)
    return ' '


def bits_from_int16(data, index, start_bit, end_bit):
    val = 0
    int16 = (data[index] << 8) | data[index + 1]
    for nbit in range(start_bit, end_bit + 1):
        if int16 & (1 << nbit):
            val += (1 << (nbit - start_bit))
    return val


def int16_to_bits(data, index, start_bit, end_bit, value):
    nbits = (end_bit - start_bit + 1)
    if value < 0:
        raise Exception('value must be >= 0')
    if value >= (2 ** nbits):
        raise Exception('value (%d) too large for bits (%d)' % (value, nbits))
    value <<= start_bit
    int16 = (data[index] << 8) | data[index + 1]
    for nbit in range(start_bit, end_bit + 1):
        if value & (1 << nbit):
            int16 |= (1 << nbit)
        else:
            int16 &= ~(1 << nbit)
    data[index] = (int16 >> 8)
    data[index + 1] = (int16 & 0xff)


def str_from_props(instance):
    strs = ['%s: %s' % (pp, getattr(type(instance), pp).__get__(instance, type(instance)))
            for pp in dir(type(instance)) if
            not pp.startswith('_') and isinstance(getattr(type(instance), pp), property)]
    return os.linesep.join(sorted(strs))


def str_from_data(data, start, end):
    chars = []
    for ii in range(start, end + 2, 2):
        chars.append(byte_to_char(data[ii + 1]))
        chars.append(byte_to_char(data[ii]))
    return ''.join(chars)


def swap_bytes(data, start=0):
    for ii in range(start, len(data), 2):
        tmp = data[ii]
        data[ii] = data[ii + 1]
        data[ii + 1] = tmp
    return data


def set_bit(int16, bit, val):
    if val:
        int16 |= (1 << bit)
    else:
        int16 &= ~(1 << bit)
    return int16

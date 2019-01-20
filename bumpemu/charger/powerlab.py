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
from time import sleep, time
from threading import Thread, Lock, Condition
import serial
import serial.tools.list_ports as list_ports

from bumpemu.circular_bytearray import CircularByteArray
from bumpemu import debug
from bumpemu.debug import print_bytes
from bumpemu.charger.status import Status
from bumpemu.charger.preset import Preset
from bumpemu.charger.options import Options
from bumpemu.util import swap_bytes, crc16, checksum, ignore_exc


class PowerlabException(Exception):
    pass


class ConnectFailedException(PowerlabException):
    pass


class VerifyException(PowerlabException):
    pass


class CrcException(VerifyException):
    pass


class ChecksumException(VerifyException):
    pass


def _command(cmd_str, nbytes=0):
    buf = bytearray(max(nbytes, len(cmd_str)))
    for ii in range(len(cmd_str)):
        buf[ii] = ord(cmd_str[ii])
    return buf


def _num_parallel_to_char(num):
    return chr(ord('l') + num - 1)


def _verify_preset_checksums(data):
    # every 510 bytes is checksummed
    for ii in range(0, 15):
        start = ii * 512
        end = start + 510
        calc_cksum = checksum(data[start:end], init=0xc8)
        check16 = (data[end] << 8) | data[end + 1]
        if calc_cksum != check16:
            raise ChecksumException('preset block checksum %d failed: cksum=%d calc_cksum=%d' %
                                    (ii, check16, calc_cksum))


def _prestart_offset(prestart_num):
    # every 510 bytes is checksummed
    return prestart_num * 102 + (prestart_num // 5) * 2


# We have to do this because the powerlab devs didn't implement flow control *sigh*
class SerialBuffer(object):
    READ_TIMEOUT = 1

    def __init__(self, ser):
        self._logger = logging.getLogger(__name__)
        self._ser = ser
        self._buf = CircularByteArray(48 * 1024)
        self._lock = Lock()
        self._cv = Condition(self._lock)
        self._stopped = False
        self._thread = Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def clear(self):
        self._buf.clear()

    def stop(self):
        self._stopped = True
        with self._cv:
            self._cv.notify()

    def read(self, nbytes, timeout=READ_TIMEOUT):
        with self._cv:
            while not self._stopped:
                start = time()
                data = self._buf.consume(nbytes)
                if data:
                    self._cv.notify()
                    return data
                timeout -= (time() - start)
                if not self._cv.wait(timeout=timeout):
                    return None  # timeout
            return None

    def _read_loop(self):
        self._ser.timeout = .1
        while not self._stopped:
            # noinspection PyBroadException
            try:
                data = self._ser.read(240)
            except:
                pass
            else:
                if data:
                    with self._cv:
                        while not self._stopped:
                            if self._buf.append(data):
                                self._cv.notify()
                                break
                            else:
                                self._cv.wait()


def _verify_cmd(cmd, buf):
    if len(buf) < len(cmd):
        raise VerifyException(cmd.decode('utf-8') + ' failed')
    if buf[:len(cmd)] != cmd:
        raise VerifyException(cmd.decode('utf-8') + ' failed')


def _verify_cmd_with_values(cmd, buf, byte_vals):
    _verify_cmd(cmd, buf)
    if buf[len(cmd):] != byte_vals:
        raise VerifyException(cmd.decode('utf-8') + ' failed')


def retry(func, num, interval=.1):
    while True:
        try:
            return func()
        except Exception as ex:
            if num <= 0:
                raise
            num -= 1
            if interval > 0:
                sleep(interval)


class Powerlab(object):
    READ_TIMEOUT = 1
    WRITE_TIMEOUT = 1

    def __init__(self, port):
        self._logger = logging.getLogger(__name__)
        self._port = port
        self._using_port = port
        self._ser = None
        self._serial_buffer = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, typ, value, traceback):
        self.close()

    @property
    def port(self):
        return self._using_port

    def connect(self, read_timeout=READ_TIMEOUT, write_timeout=WRITE_TIMEOUT):
        if not self._port:
            self._using_port = None
            for port in list_ports.comports():
                if port.description == 'FT232R USB UART':
                    self._using_port = port.device
                    break
            if not self._using_port:
                raise ConnectFailedException('no port found')

        self._logger.debug('connecting port:%s read_to:%f, write_to:%f', self._using_port, read_timeout, write_timeout)
        options = None
        baud_rates = (19200,)
        try:
            for baud_rate in baud_rates:
                ser = serial.PosixPollSerial(baudrate=baud_rate,
                                             timeout=read_timeout,
                                             write_timeout=write_timeout)
                ser.dtr = True
                ser.port = self._using_port
                ser.open()
                if ser.is_open:
                    self._ser = ser
                    if hasattr(self._ser, 'set_low_latency_mode'):
                        # noinspection PyUnresolvedReferences
                        self._ser.set_low_latency_mode(True)

                    retries = 3
                    while retries:
                        try:
                            options = self.read_options()
                            self._logger.info('connected to %s', self._using_port)
                            self._serial_buffer = SerialBuffer(self._ser)
                            return options
                        except Exception as ex:
                            retries -= 1
                            self._logger.debug(str(ex))

                    self._ser.close()
                    self._ser = None

        except Exception as ex:
            self._logger.debug(str(ex))
        raise ConnectFailedException()

    def close(self):
        if self._serial_buffer:
            self._serial_buffer.stop()
            self._serial_buffer = None
        if self._ser:
            if self._ser.is_open:
                ignore_exc(self._ser.reset_input_buffer)
                ignore_exc(self._ser.reset_output_buffer)
                ignore_exc(self._ser.close)
            self._ser = None
            self._logger.info('closed %s', self._using_port)

    def command_enter(self, num_parallel=1, retries=0):
        self._logger.debug('command_enter')
        return retry(lambda: self._send_cmd(num_parallel, 'E'), retries)

    def command_monitor(self, num_parallel, use_bananas=True, retries=0):
        self._logger.debug('command_monitor')
        return retry(lambda: self._send_cmd(num_parallel, 'M' if use_bananas else 'm'), retries)

    def command_charge(self, num_parallel, use_bananas=True, retries=0):
        self._logger.debug('command_charge')
        return retry(lambda: self._send_cmd(num_parallel, 'C' if use_bananas else 'c'), retries)

    def command_discharge(self, num_parallel, use_bananas=True, retries=0):
        self._logger.debug('command_discharge')
        return retry(lambda: self._send_cmd(num_parallel, 'D' if use_bananas else 'd'), retries)

    def command_cycle(self, num_parallel, use_bananas=True, retries=0):
        self._logger.debug('command_cycle')
        return retry(lambda: self._send_cmd(num_parallel, 'Y' if use_bananas else 'y'), retries)

    def command_set_active_preset(self, which, retries=0):
        self._logger.debug('command_set_active_preset %s', which)
        if which < 0 or which > 24:
            raise PowerlabException('invalid preset: %s' % which)
        def impl():
            write_cmd = _command('SelP' + chr(which))
            calc_crc = crc16([which], init=0x1114)
            self._write(write_cmd)
            resp = self._read(nbytes=len(write_cmd) + 2)
            crc = (resp[len(write_cmd)] << 8) | resp[len(write_cmd) + 1]
            if crc != calc_crc:
                raise CrcException('set preset %s failed: invalid CRC %s != %s' % (which, hex(crc), hex(calc_crc)))
        return retry(impl, retries)

    def read_status(self, retries=0):
        self._logger.debug('read_status')
        def impl():
            cmd = _command('Ram\0')
            self._write(cmd)
            resp = self._read(nbytes=153)
            self._verify_cmd_with_crc(cmd, resp, crc_index=151, crc_init=0x926)
            return Status(resp[len(cmd):151])
        return retry(impl, retries)

    def read_presets(self, retries=0):
        self._logger.debug('reading presets')
        def impl():
            cmd = _command('Prst')
            self._write(cmd)
            resp = self._read(nbytes=7686, timeout=7)
            _verify_cmd(cmd, resp)
            self._verify_crc(resp[4:], crc_index=7680, crc_init=0x18e4)
            _verify_preset_checksums(resp[4:])
            presets = []
            for preset_num in range(0, 75):
                offset = _prestart_offset(preset_num)
                presets.append(Preset(resp[4 + offset:4 + offset + 102], preset_num))
            return presets
        return retry(impl, retries)

    def write_presets(self, presets, retries=0):
        self._logger.debug('writing presets')
        def impl():
            write_cmd = _command('WrtP')
            ii = 1
            for preset in presets:
                preset.is_validated = not preset.is_empty
                write_cmd.extend(preset.raw_bytes())

                # every 510 bytes, compute and add checksum
                if (ii % 5) == 0:
                    block_num = ii // 5 - 1
                    start = 4 + block_num * 512
                    end = start + 510
                    assert (len(write_cmd) == end)
                    cksum = checksum(write_cmd[start:end], init=0xc8)
                    write_cmd.append(cksum >> 8)
                    write_cmd.append(cksum & 0xff)
                ii += 1

            if self._logger.isEnabledFor(logging.DEBUG):
                _verify_preset_checksums(write_cmd[4:])

            assert (len(write_cmd) == 7684)
            swap_bytes(write_cmd, start=4)
            calc_crc = crc16(write_cmd[4:], init=0x4d1)

            self._logger.debug('erase presets')
            cmd = _command('ErsP')
            self._write(cmd)
            resp = self._read(nbytes=6)
            _verify_cmd_with_values(cmd, resp, bytes([0x22, 0x1b]))

            sleep(.05)
            self._logger.debug('write presets')
            self._write(write_cmd, timeout=7)
            sleep(5.25)
            resp = self._read(nbytes=7686, timeout=7)
            if len(resp) != 7686:
                raise VerifyException('did not get expected response length: %d != %d' % (len(resp), 7686))
            crc = (resp[7684] << 8) | resp[7685]
            if crc != calc_crc:
                raise CrcException('write presets failed: invalid CRC %s != %s' % (hex(crc), hex(calc_crc)))
            self._logger.debug('presets write success')
        return retry(impl, retries)

    def read_options(self, retries=0):
        self._logger.debug('loading options')
        def impl():
            cmd = _command('PrsI')
            self._write(cmd)
            resp = self._read(nbytes=262)
            self._verify_cmd_with_crc(cmd, resp, crc_index=260, crc_init=0x342)
            return Options(resp[len(cmd):260])
        return retry(impl, retries)

    def write_options(self, options, retries=0):
        self._logger.debug('writing options')
        def impl():
            write_cmd = _command('WrtC')
            write_cmd.extend(options.raw_bytes()[128:192])

            assert (len(write_cmd) == 68)
            swap_bytes(write_cmd, start=4)
            calc_crc = crc16(write_cmd[4:], init=0xf5)

            self._logger.debug('erase options')
            cmd = _command('ErsC')
            self._write(cmd)
            resp = self._read(nbytes=6)
            _verify_cmd_with_values(cmd, resp, bytes([0x0d, 0x04]))

            self._logger.debug('write options')
            self._write(write_cmd)
            resp = self._read(nbytes=70)
            crc = (resp[68] << 8) | resp[69]
            if crc != calc_crc:
                raise CrcException('write options failed: invalid CRC %s != %s' % (hex(crc), hex(calc_crc)))
            self._logger.debug('options write success')
        return retry(impl, retries)

    def _read(self, nbytes=1, timeout=READ_TIMEOUT, retries=0):
        resp = None
        if self._serial_buffer:
            for ii in range(retries + 1):
                resp = self._serial_buffer.read(nbytes, timeout)
                if resp and len(resp) >= nbytes:
                    break
        else:
            self._ser.timeout = timeout
            for ii in range(retries + 1):
                resp = self._ser.read(nbytes)
                if resp and len(resp) >= nbytes:
                    break
        if retries and (resp is None or len(resp) < nbytes):
            raise VerifyException('_read did not get expected number of bytes')
        if debug.LOG_SERIAL:
            if resp:
                print_bytes(self._logger, logging.DEBUG, resp, 'r')
        return resp or []

    def _write(self, data, timeout=WRITE_TIMEOUT):
        self._ser.reset_output_buffer()
        self._ser.reset_input_buffer()
        if self._serial_buffer:
            self._serial_buffer.clear()
        self._ser.write_timeout = timeout
        self._ser.write(data)
        if debug.LOG_SERIAL:
            print_bytes(self._logger, logging.DEBUG, data, 'w')

    def _send_cmd(self, num_parallel, command_char):
        cmd = _command('Se' + _num_parallel_to_char(num_parallel) + command_char)
        self._write(cmd)
        resp = self._read(nbytes=6)
        _verify_cmd_with_values(cmd, resp, bytes([0x5, 0xdc]))

    def _verify_crc(self, buf, crc_index, crc_init):
        crc = (buf[crc_index] << 8) | buf[crc_index + 1]
        calc_crc = crc16(buf[:crc_index], crc_init)
        if debug.LOG_SERIAL:
            self._logger.debug('crc: %s calc_crc: %s', hex(crc), hex(calc_crc))
        if crc != calc_crc:
            raise CrcException('bad CRC')

    def _verify_cmd_with_crc(self, cmd, buf, crc_index, crc_init):
        _verify_cmd(cmd, buf)
        self._verify_crc(buf[len(cmd):], crc_index - len(cmd), crc_init)

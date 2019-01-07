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
import logging
# noinspection PyCompatibility
from queue import Queue
from threading import Thread

from bumpemu.circular_bytearray import CircularByteArray
from bumpemu.util import crc16
from bumpemu.controller import constants
from bumpemu.controller.messages.manual_start import ManualStart
from bumpemu import debug
from bumpemu.debug import print_bytes


class MessageHandler(object):
    def __init__(self, rx_chrc):
        self._logger = logging.getLogger(__name__)
        self._rx_chrc = rx_chrc
        self._buf = CircularByteArray(4096)
        self._message_handlers = {
            constants.MessageId.SELECTED_OPERATION_NOT.value: lambda xx: self._rx_chrc.selected_operation(
                port=xx[0], operation=xx[1]),
            constants.MessageId.OPERATION_START_CMD.value: lambda xx: self._rx_chrc.operation_start(port=xx[0]),
            constants.MessageId.OPERATION_STOP_CMD.value: lambda xx: self._rx_chrc.operation_stop(port=xx[0]),
            constants.MessageId.MONITOR_CMD.value: lambda xx: self._rx_chrc.monitor(port=xx[0]),
            constants.MessageId.OPERATION_CLEAR_ERROR_CMD.value: lambda xx: self._rx_chrc.clear_error(port=xx[0]),
            constants.MessageId.CONNECT_REQUEST.value: lambda xx: self._rx_chrc.connect_request(),
            constants.MessageId.CYCLE_GRAPH_GET.value: lambda xx: self._rx_chrc.cycle_graph_complete(),
            constants.MessageId.GET_DEVICE_INFO_CMD.value: lambda xx: self._rx_chrc.device_info(),
            constants.MessageId.DISMISS_CMD.value: lambda xx: self._rx_chrc.dismiss(port=xx[0], keep_setup=bool(xx[1])),
            constants.MessageId.MANUAL_OPERATION_CMD.value: lambda xx: self._rx_chrc.manual_operation(ManualStart(xx)),
            constants.MessageId.SET_BATTERY_GROUP_COUNT_CMD.value: lambda xx: self._rx_chrc.set_battery_group_count(
                port=xx[0], group_index=xx[1], count=xx[2]),
        }
        self._queue = Queue()
        self._thread = Thread(target=self._queue_processor, daemon=True)
        self._thread.start()

    def append(self, buf):
        self._queue.put(buf)

    def _queue_processor(self):
        while True:
            buf = self._queue.get()
            if debug.LOG_BLUETOOTH:
                print_bytes(self._logger, logging.DEBUG, buf, 'r')
            if self._buf.available() < len(buf):
                raise Exception('circular buffer is full')
            self._buf.append(buf)
            self._handle_messages()

    def _advance_to_next_preamble(self):
        while True:
            bb = self._buf.peek()
            if bb is None or bb == constants.Message.PREAMBLE_BYTE:
                break
            self._buf.advance(1)

    def _handle_messages(self):
        self._advance_to_next_preamble()

        buf_len = self._buf.size()
        while constants.Message.OVERHEAD <= buf_len:
            assert (self._buf.peek() == constants.Message.PREAMBLE_BYTE)
            payload_len_start_idx = self._buf.read_index + constants.Message.PAYLOAD_LEN_OFFSET
            payload_len = struct.unpack(constants.Message.PAYLOAD_LEN_FORMAT,
                                        self._buf[payload_len_start_idx:
                                                  payload_len_start_idx + constants.Message.PAYLOAD_LEN_BYTES])[0]
            message_size = payload_len + constants.Message.OVERHEAD
            if debug.LOG_BLUETOOTH:
                self._logger.debug('message_size: %d', message_size)
            if message_size > self._buf.capacity():
                self._logger.warning('message larger than circ buf size')
                self._advance_to_next_preamble()
                buf_len = self._buf.size()
                continue
            elif message_size <= buf_len:
                payload_start_idx = self._buf.read_index + constants.Message.PAYLOAD_OFFSET
                crc_start_idx = payload_start_idx + payload_len
                crc = struct.unpack(constants.Message.CRC_FORMAT,
                                    self._buf[crc_start_idx:crc_start_idx + constants.Message.CRC_BYTES])[0]
                calc_crc = crc16(self._buf[self._buf.read_index:crc_start_idx], init=constants.Message.CRC_SEED)
                if debug.LOG_BLUETOOTH:
                    self._logger.debug('crc: %s calc_crc: %s', hex(crc), hex(calc_crc))
                if crc == calc_crc:
                    message_id = self._buf[self._buf.read_index + constants.Message.MESSAGE_ID_OFFSET]
                    payload = self._buf[payload_start_idx:crc_start_idx]
                    self._buf.advance(constants.Message.OVERHEAD + payload_len)
                    self._handle_message(message_id, payload)
            else:
                # TODO: add timeout
                break
            self._advance_to_next_preamble()
            buf_len = self._buf.size()

    def _handle_message(self, message_id, payload):
        self._logger.debug('_handle_message - message_id: %s payload_len: %d', message_id, len(payload))
        handler = self._message_handlers.get(message_id)
        if handler:
            handler(payload)
        else:
            self._logger.debug('unhandled message id: %s', hex(message_id))

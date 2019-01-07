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
from bumpemu.controller import constants
from bumpemu.controller.serialize import append_uint16, append_uint32, append_int32


class ChargerIdle(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.port_number = 0
        self.model_id = constants.ChargerModel.NONE
        self.comm_state = constants.CommState.COMM_DISCONNECTED
        self.supply_volts = 0
        self.supply_amps = 0
        self.cpu_temp = 0
        self.operation_flags = 0
        self.firmware_version = 0

    def serialize(self):
        buf = bytearray()
        buf.append(self.port_number)
        # noinspection PyTypeChecker
        buf.append(self.model_id.value)
        # noinspection PyTypeChecker
        buf.append(self.comm_state.value)
        append_uint32(buf, self.supply_volts)
        append_int32(buf, self.supply_amps)
        append_uint16(buf, self.cpu_temp)
        buf.append(self.operation_flags)
        append_uint16(buf, self.firmware_version)
        return buf

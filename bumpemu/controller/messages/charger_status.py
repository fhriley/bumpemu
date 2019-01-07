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
from bumpemu.controller.serialize import append_uint16, append_int32, append_uint32


class ChargerStatus(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.port_number = 0
        self.schema_version = 6
        self.model_id = constants.ChargerModel.NONE
        self.comm_state = constants.CommState.COMM_DISCONNECTED
        self.mode_running = constants.ChargerMode.READY_TO_START
        self.error_code = 0
        self.chemistry = constants.Chemistry.NONE
        self._cell_count = 0
        self.estimated_fuel_level = 0
        self.estimated_minutes = 0
        self.amps = 0
        self.pack_volts = 0
        self.capacity_added = 0
        self.capacity_removed = 0
        self.cycle_timer = 0
        self.status_flags = 0
        self.rx_status_flags = 0
        self.operation_flags = 0
        self.power_reduced_reason = constants.ChargerPowerReducedReason.NONE
        self.supply_volts = 0
        self.supply_amps = 0
        self.cpu_temp = 0
        self.cell_volts = []
        self.cell_ir = []
        self.cell_bypass = []

    @property
    def cell_count(self):
        return self._cell_count

    @cell_count.setter
    def cell_count(self, val):
        self._cell_count = val
        self.cell_volts = [0] * val
        self.cell_ir = [0] * val
        self.cell_bypass = [0] * val

    def serialize(self):
        buf = bytearray()
        buf.append(self.port_number)
        buf.append(self.schema_version)
        # noinspection PyTypeChecker
        buf.append(self.model_id.value)
        # noinspection PyTypeChecker
        buf.append(self.comm_state.value)
        # noinspection PyTypeChecker
        buf.append(self.mode_running.value)
        buf.append(self.error_code)
        # noinspection PyTypeChecker
        buf.append(self.chemistry.value)
        buf.append(self.cell_count)
        buf.append(self.estimated_fuel_level)
        append_uint16(buf, self.estimated_minutes)
        append_int32(buf, self.amps)
        append_uint32(buf, self.pack_volts)
        append_uint32(buf, self.capacity_added)
        append_uint32(buf, self.capacity_removed)
        append_uint32(buf, self.cycle_timer)
        append_uint16(buf, self.status_flags)
        append_uint16(buf, self.rx_status_flags)
        buf.append(self.operation_flags)
        # noinspection PyTypeChecker
        buf.append(self.power_reduced_reason.value)
        append_uint32(buf, self.supply_volts)
        append_int32(buf, self.supply_amps)
        append_uint16(buf, self.cpu_temp)
        for ii in range(self.cell_count):
            append_uint16(buf, self.cell_volts[ii])
            append_uint16(buf, self.cell_ir[ii])
            buf.append(self.cell_bypass[ii])
        return buf

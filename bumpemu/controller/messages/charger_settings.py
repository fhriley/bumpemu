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
from bumpemu.controller.serialize import append_uint16, append_array, append_bool


class ChargerSettings(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.port_number = 0
        self.requested_operation = constants.ChargerOperation.NONE
        self.requested_chemistry = constants.Chemistry.NONE
        self.requested_cell_count = 0
        self.requested_ir = 0
        self.requested_capacity = 0
        self.requested_charge_c = 0
        self.requested_discharge_c = 0
        self.requested_charge_rate = 0
        self.requested_discharge_rate = 0
        self.requested_charge_cutoff_cell_volts = 0
        self.requested_discharge_cutoff_cell_volts = 0
        self.requested_fuel_curve = [0] * 11
        self.multi_charger_mode = 0
        self.power_supply_mode = constants.PowerSupplyMode.DC
        self.use_balance_leads = True

    def serialize(self):
        buf = bytearray()
        buf.append(self.port_number)
        # noinspection PyTypeChecker
        buf.append(self.requested_operation.value)
        # noinspection PyTypeChecker
        buf.append(self.requested_chemistry.value)
        buf.append(self.requested_cell_count)
        append_uint16(buf, int(round(self.requested_ir * 100)))
        append_uint16(buf, self.requested_capacity)
        append_uint16(buf, int(round(self.requested_charge_c * 10)))
        append_uint16(buf, int(round(self.requested_discharge_c * 10)))
        append_uint16(buf, self.requested_charge_rate)
        append_uint16(buf, self.requested_discharge_rate)
        append_uint16(buf, int(round(self.requested_charge_cutoff_cell_volts * 1000)))
        append_uint16(buf, int(round(self.requested_discharge_cutoff_cell_volts * 1000)))
        fuel_curve = [int(round(val * 1000)) for val in self.requested_fuel_curve]
        append_array(buf, fuel_curve, append_uint16)
        buf.append(self.multi_charger_mode)
        # noinspection PyTypeChecker
        buf.append(self.power_supply_mode.value)
        append_bool(buf, self.use_balance_leads)
        return buf

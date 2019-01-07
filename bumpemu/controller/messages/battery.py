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
import os

from yaml import load, Loader
from bumpemu.controller import constants
from bumpemu.controller.serialize import append_uint16, append_array, append_str


class BatteryGroupNotify(object):
    def __init__(self, battery_group):
        self._logger = logging.getLogger(__name__)
        self.charger_port_number = 0
        self.battery_group = battery_group

    def serialize(self):
        buf = bytearray()
        buf.append(self.charger_port_number)
        self.battery_group.serialize(buf)
        return buf


class BatteryGroup(object):
    NFCID_COUNT = 8
    NFCID_LENGTH = 7

    def __init__(self, battery):
        self._logger = logging.getLogger(__name__)
        self.group_index = 0
        self.battery_count = battery.pack_count
        self.battery = battery
        self.index = 0
        self.nfc_ids = [[1, 2, 3, 4, 5, 6, 7]]
        for ii in range(1, self.NFCID_COUNT):
            self.nfc_ids.append([0] * self.NFCID_LENGTH)

    def serialize(self, buf=None):
        if buf is None:
            buf = bytearray()
        buf.append(self.group_index)
        buf.append(self.battery_count)
        self.battery.serialize(buf)
        for nfc_id in self.nfc_ids:
            append_array(buf, nfc_id)
        return buf


class Battery(object):
    REQUIRED = {'pref_operation', 'pref_charge_c_normal', 'pref_charge_c_fastest', 'pref_charge_c_accurate',
                'pref_discharge_c', 'cycle_count', 'internal_resistance', 'discharge_c_max', 'charge_c_max', 'capacity',
                'chemistry', 'cell_count', 'brand_name', 'max_cell_volts', 'min_cell_volts', 'pack_count',
                'storage_charge_volts', 'storage_discharge_volts',
                'pref_charge_c_discharge', 'pref_charge_c_storage', 'pref_charge_c_analyze', 'pref_charge_c_monitor'}

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.version = 2
        self.pref_operation = constants.ChargerOperation.NONE
        self.pref_charge_c_normal = 0
        self.pref_charge_c_fastest = 0
        self.pref_charge_c_accurate = 0
        self.pref_discharge_c = 0
        self.pref_fast_charge_delta = 0
        self.pref_discharge_delta = 0
        self.measured_fuel_table = [0] * 11
        self.measured_internal_resistance = 0
        self.measured_capacity = 0
        self.cycle_count = 0
        self.pref_accu_charge_delta = 0
        self.pref_norm_charge_delta = 0
        self.pref_store_charge_delta = 0
        self.pref_flags = 0
        self.battery_id = 0
        self.checksum = 0
        self.settings_version = 1
        self.internal_resistance = 0
        self.discharge_c_max = 0
        self.charge_c_max = 0
        self.capacity = 0
        self.chemistry = constants.ChargerOperation.NONE
        self.cell_count = 0
        self.brand_name = ''
        self.max_cell_volts = 0
        self.min_cell_volts = 0
        self.pack_count = 0

        # Not used by powerlab, only for emulator
        self.storage_charge_volts = 0
        self.storage_discharge_volts = 0
        self.pref_charge_c_discharge = 0
        self.pref_charge_c_storage = 0
        self.pref_charge_c_analyze = 0
        self.pref_charge_c_monitor = 0

    @classmethod
    def from_yaml(cls, yaml_file):
        battery = Battery()
        with open(yaml_file, 'r') as stream:
            data = load(stream, Loader=Loader)
            missing = cls.REQUIRED.difference(data.keys())
            if missing:
                raise Exception('the following are missing from the battery file: %s' % ', '.join(missing))
            if not data['brand_name']:
                raise Exception('"brand_name" minimum length is 1')
            if len(data['brand_name']) > 16:
                raise Exception('"brand_name" maximum length is 16')
            for var in vars(battery):
                if not var.startswith('_'):
                    val = data.get(var)
                    if val is not None:
                        setattr(battery, var, val)
        try:
            battery.pref_operation = constants.ChargerOperation[battery.pref_operation.upper()]
        except:
            raise Exception('"pref_operation" is invalid')
        try:
            battery.chemistry = constants.Chemistry[battery.chemistry.upper()]
        except:
            raise Exception('"chemistry" is invalid')
        return battery

    def serialize(self, buf=None):
        if buf is None:
            buf = bytearray()
        buf.append(self.version)
        # noinspection PyTypeChecker
        buf.append(self.pref_operation.value)
        append_uint16(buf, int(round(self.pref_charge_c_normal * 10)))
        append_uint16(buf, int(round(self.pref_charge_c_fastest * 10)))
        append_uint16(buf, int(round(self.pref_charge_c_accurate * 10)))
        append_uint16(buf, int(round(self.pref_discharge_c * 10)))
        buf.append(self.pref_fast_charge_delta)
        buf.append(self.pref_discharge_delta)
        append_array(buf, self.measured_fuel_table, append_func=append_uint16)
        append_uint16(buf, int(round(self.measured_internal_resistance * 100)))
        append_uint16(buf, self.measured_capacity)
        append_uint16(buf, self.cycle_count)
        buf.append(self.pref_accu_charge_delta)
        buf.append(self.pref_norm_charge_delta)
        buf.append(self.pref_store_charge_delta)
        buf.append(self.pref_flags)
        append_uint16(buf, self.battery_id)
        append_array(buf, [0] * 4)
        append_uint16(buf, self.checksum)
        buf.append(self.settings_version)
        append_uint16(buf, int(round(self.internal_resistance * 100)))
        append_uint16(buf, int(round(self.discharge_c_max)))
        append_uint16(buf, int(round(self.charge_c_max * 10)))
        append_uint16(buf, self.capacity)
        # noinspection PyTypeChecker
        buf.append(self.chemistry.value)
        buf.append(self.cell_count)
        append_str(buf, self.brand_name, 16)
        append_uint16(buf, int(round(self.max_cell_volts * 1000)))
        append_uint16(buf, int(round(self.min_cell_volts * 1000)))
        buf.append(self.pack_count)
        append_array(buf, [0] * 13)
        return buf

    def __str__(self):
        return os.linesep.join(
            ['%s: %s' % (var, getattr(self, var)) for var in sorted(vars(self)) if not var.startswith('_')])

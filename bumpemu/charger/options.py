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

from bumpemu.util import str_from_props, str_from_data, set_bit


# noinspection PyAttributeOutsideInit
class Options(object):
    def __init__(self, data):
        self._data = bytearray(data)

    @property
    def greeting_line1(self):
        return str_from_data(self._data, start=132, end=146)

    @property
    def greeting_line2(self):
        return str_from_data(self._data, start=148, end=158)

    @property
    def _flags128(self):
        return (self._data[128] << 8) | self._data[129]

    @_flags128.setter
    def _flags128(self, val):
        self._data[128] = val >> 8
        self._data[129] = val & 0xff

    @property
    def is_european_decimal(self):
        return bool(self._flags128 & (1 << 0))

    @property
    def is_button_click_enabled(self):
        return bool(self._flags128 & (1 << 1))

    @property
    def is_save_changes_enabled(self):
        return bool(self._flags128 & (1 << 2))

    @property
    def speaker_volume(self):
        return (self._flags128 & (0x7 << 4)) >> 4

    @property
    def cells_scroll_seconds(self):
        return (self._flags128 & (0x7 << 7)) >> 7

    @property
    def is_quick_start_enabled(self):
        return bool(self._flags128 & (1 << 10))

    @is_quick_start_enabled.setter
    def is_quick_start_enabled(self, val):
        self._flags128 = set_bit(self._flags128, 10, val)

    @property
    def regen_charge_voltage_in_to_pb(self):
        return (self._data[130] + 100) / 10.0

    @property
    def regen_amps_in_to_pb(self):
        return self._data[131] / 2.0

    @property
    def scroll_delay1(self):
        return self._data[164]

    @property
    def preset_name_scroll_speed(self):
        return self._data[165]

    @property
    def name_line2_secs(self):
        return self._data[166]

    @property
    def scroll_delay2(self):
        return self._data[167]

    @property
    def supply_cutoff_volts(self):
        return (self._data[168] + 100) / 10.0

    @property
    def supply_amps_limit(self):
        return self._data[169] / 2.0

    @property
    def _flags170(self):
        return (self._data[170] << 8) | self._data[171]

    @_flags170.setter
    def _flags170(self, val):
        self._data[170] = val >> 8
        self._data[171] = val & 0xff

    @property
    def is_cells_3_decimals_enabled(self):
        return bool(self._flags170 & (1 << 0))

    @property
    def is_quiet_charging(self):
        return bool(self._flags170 & (1 << 1))

    @is_quiet_charging.setter
    def is_quiet_charging(self, val):
        self._flags170 = set_bit(self._flags170, 1, val)

    @property
    def is_battery_enabled(self):
        return bool(self._flags170 & (1 << 4))

    @property
    def is_warn_50_dod_enabled(self):
        return bool(self._flags170 & (1 << 6))

    @property
    def is_regen_enabled(self):
        return bool(self._flags170 & (1 << 7))

    @property
    def is_choose_source_enabled(self):
        return bool(self._flags170 & (1 << 8))

    @is_choose_source_enabled.setter
    def is_choose_source_enabled(self, val):
        self._flags170 = set_bit(self._flags170, 8, val)

    @property
    def is_suppress_use_bananas_enabled(self):
        return bool(self._flags170 & (1 << 9))

    @is_suppress_use_bananas_enabled.setter
    def is_suppress_use_bananas_enabled(self, val):
        self._flags170 = set_bit(self._flags170, 9, val)

    @property
    def is_xh_node_wiring(self):
        return bool(self._flags170 & (1 << 10))

    @is_xh_node_wiring.setter
    def is_xh_node_wiring(self, val):
        self._flags170 = set_bit(self._flags170, 10, val)

    @property
    def is_network_disabled(self):
        return bool(self._flags170 & (1 << 11))

    @property
    def charge_done_beeps(self):
        return self._data[173]

    @property
    def battery_cutoff_volts(self):
        return (self._data[174] + 100) / 10.0

    @battery_cutoff_volts.setter
    def battery_cutoff_volts(self, val):
        self._data[174] = int(val * 10 - 100)

    @property
    def battery_amps_limit(self):
        return self._data[175] / 2.0

    @battery_amps_limit.setter
    def battery_amps_limit(self, val):
        self._data[175] = int(val * 2)

    @property
    def battery_type(self):
        return self._data[177]

    @property
    def checksum(self):
        return (self._data[190] << 8) | self._data[191]

    @checksum.setter
    def checksum(self, val):
        self._data[190] = (val >> 8) & 0xff
        self._data[191] = val & 0xff

    def raw_bytes(self):
        self.checksum = self.calc_checksum()
        return bytes(self._data)

    def calc_checksum(self):
        cksum = 0
        for ii in range(128, 186, 2):
            cksum += ((self._data[ii] << 8) | self._data[ii + 1])
        return cksum & 0xffff

    def __str__(self):
        return str_from_props(self)

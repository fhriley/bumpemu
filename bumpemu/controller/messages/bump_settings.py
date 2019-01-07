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
from bumpemu.controller.serialize import append_uint16, append_array, append_bool, append_str


class BumpSettings(object):
    MAX_NAME_LEN = 16

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.volume_level = 0
        self.touch_cal_dx = 0
        self.touch_cal_dy = 0
        self.touch_cal_cx = 0
        self.touch_cal_cy = 0
        self.custom_color_idle = 0
        self.custom_color_active = 0
        self.custom_color_complete = 0
        self.custom_color_safety = 0
        self.custom_color_setup = 0
        self.selected_color_theme = 0
        self.screen_layout = 0
        self.last_bluetooth_uuid = [0, 0, 0, 0, 0, 0]
        self.cell_ir_warning_threshold = 0
        self.capacity_warning_threshold = 0
        self.presets_enabled = False
        self.cycle_graph_caching_enabled = False
        self._charger_ports_disabled = [True, True, True, True]
        self.touch_calibration_redone = False
        self._power_sources = [0, 0, 0, 0]
        self._wiring_modes = [0, 0, 0, 0]
        self.charger_upgrade_states = [0, 0, 0, 0]
        self.charger_upgrade_models = [0, 0, 0, 0]
        self.power_source_defaults_created = False
        self._power_source_names = [None, None, None, None]
        self._power_source_types = [0, 0, 0, 0]
        self._power_source_warn_dod = [True, True, True, True]
        self._power_source_low_volts = [0, 0, 0, 0]
        self._power_source_max_amps = [0, 0, 0, 0]
        self._power_source_max_regen_amps = [0, 0, 0, 0]
        self._power_source_max_regen_volts = [0, 0, 0, 0]
        self._power_source_regen_dchg_enabled = [True, True, True, True]
        self.power_source_initial_setup_complete = True
        self.device_name = 'foobar'
        self.checksum = 0

    def set_power_source_params(self, index, name, typ, low_volts, max_amps,
                                warn_dod=True, max_regen_amps=0, max_regen_volts=0, regen_dchg_enabled=False):
        self._power_source_names[index] = name
        self._power_source_types[index] = typ
        self._power_source_warn_dod[index] = warn_dod
        self._power_source_low_volts[index] = low_volts
        self._power_source_max_amps[index] = max_amps
        self._power_source_max_regen_amps[index] = max_regen_amps
        self._power_source_max_regen_volts[index] = max_regen_volts
        self._power_source_regen_dchg_enabled[index] = regen_dchg_enabled

    def set_power_source(self, port, index):
        self._power_sources[port] = index

    def set_xh_wiring_mode(self, port):
        self._wiring_modes[port] = 1

    def enable_charger_port(self, port):
        self._charger_ports_disabled[port] = False

    def serialize(self):
        buf = bytearray()
        buf.append(self.volume_level)
        append_uint16(buf, self.touch_cal_dx)
        append_uint16(buf, self.touch_cal_dy)
        append_uint16(buf, self.touch_cal_cx)
        append_uint16(buf, self.touch_cal_cy)
        append_uint16(buf, self.custom_color_idle)
        append_uint16(buf, self.custom_color_active)
        append_uint16(buf, self.custom_color_complete)
        append_uint16(buf, self.custom_color_safety)
        append_uint16(buf, self.custom_color_setup)
        buf.append(self.selected_color_theme)
        buf.append(self.screen_layout)
        append_array(buf, self.last_bluetooth_uuid)
        buf.append(self.cell_ir_warning_threshold)
        buf.append(self.capacity_warning_threshold)
        append_bool(buf, self.presets_enabled)
        append_bool(buf, self.cycle_graph_caching_enabled)
        append_array(buf, self._charger_ports_disabled, append_bool)
        buf.append(0)
        buf.append(self.touch_calibration_redone)
        buf.append(0)
        append_array(buf, self._power_sources)
        append_array(buf, [0] * 4)
        append_array(buf, self._wiring_modes)
        append_array(buf, self.charger_upgrade_states)
        append_array(buf, self.charger_upgrade_models)
        append_bool(buf, self.power_source_defaults_created)
        append_array(buf, self._power_source_names, lambda buff, val: append_str(buff, val, self.MAX_NAME_LEN))
        append_array(buf, self._power_source_types)
        append_array(buf, self._power_source_warn_dod, append_bool)
        append_array(buf, self._power_source_low_volts, append_uint16)
        append_array(buf, self._power_source_max_amps, append_uint16)
        append_array(buf, self._power_source_max_regen_amps, append_uint16)
        append_array(buf, self._power_source_max_regen_volts, append_uint16)
        append_array(buf, self._power_source_regen_dchg_enabled, append_bool)
        append_bool(buf, self.power_source_initial_setup_complete)
        append_str(buf, self.device_name, self.MAX_NAME_LEN)
        append_array(buf, [0] * 70)
        append_uint16(buf, self.checksum)
        return buf

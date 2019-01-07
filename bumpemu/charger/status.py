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

from bumpemu.util import str_from_props


def _to_volts(val):
    return (val * 46.96) / 4095


_start_modes = {
    0: 'Charge Only',
    1: 'Discharge Only',
    2: 'Monitor',
    3: 'Cycle',
}


def _start_mode_to_str(mode):
    return _start_modes.get(mode, "Unknown: %d" % mode)


class Status(object):
    def __init__(self, data):
        self._data = data

    @property
    def firmware_version(self):
        return struct.unpack('>H', self._data[0:2])[0]

    @property
    def b_avg_adc(self):
        return struct.unpack('>HHHHHHHH', self._data[2:18])

    @property
    def b_volts(self):
        return [(val * 5.12) / 65536 for val in self.b_avg_adc]

    @property
    def charge_set(self):
        return struct.unpack('>H', self._data[20:22])[0]

    @property
    def l_supply_volts(self):
        return _to_volts(struct.unpack('>H', self._data[22:24])[0]) / 16

    @property
    def supply_volts(self):
        return _to_volts(struct.unpack('>H', self._data[24:26])[0])

    @property
    def cpu_temp(self):
        val = struct.unpack('>H', self._data[26:28])[0]
        return (((2.5 * val) / 4095.0) - 0.986) / 0.00355

    @property
    def avg_amps(self):
        return struct.unpack('>h', self._data[42:44])[0] / 600.0

    @property
    def status_flags(self):
        return struct.unpack('>H', self._data[44:46])[0]

    @property
    def safety_charge(self):
        return bool(self.status_flags & (1 << 0))

    @property
    def generate_fuel(self):
        return bool(self.status_flags & (1 << 5))

    @property
    def is_charge_discharge_complete(self):
        return bool(self.status_flags & (1 << 8))

    @property
    def is_reduce_amps(self):
        return bool(self.status_flags & (1 << 11))

    @property
    def show_vr(self):
        return bool(self.status_flags & (1 << 12))

    @property
    def node_current(self):
        return bool(self.status_flags & (1 << 14))

    @property
    def cold_weather(self):
        return bool(self.status_flags & (1 << 15))

    @property
    def rx_status_flags(self):
        return struct.unpack('>H', self._data[46:48])[0]

    @property
    def shunt_switch(self):
        return bool(self.rx_status_flags & (1 << 0))

    @property
    def dsch_enable(self):
        return bool(self.rx_status_flags & (1 << 1))

    @property
    def cd_pre_complete(self):
        return bool(self.rx_status_flags & (1 << 2))

    @property
    def regen_enable(self):
        return bool(self.rx_status_flags & (1 << 4))

    @property
    def fast_cell_avg(self):
        return bool(self.rx_status_flags & (1 << 5))

    @property
    def chg_enable(self):
        return bool(self.rx_status_flags & (1 << 6))

    @property
    def bp_enable(self):
        return bool(self.rx_status_flags & (1 << 7))

    @property
    def use_nodes(self):
        return bool(self.rx_status_flags & (1 << 8))

    @property
    def use_fuel(self):
        return bool(self.rx_status_flags & (1 << 9))

    @property
    def amps_low_range(self):
        return bool(self.rx_status_flags & (1 << 10))

    @property
    def amps_dsch_range(self):
        return bool(self.rx_status_flags & (1 << 11))

    @property
    def debug1(self):
        return struct.unpack('>h', self._data[48:50])[0]

    @property
    def _flags50(self):
        return struct.unpack('>H', self._data[50:52])[0]

    @property
    def high_temp(self):
        return bool(self._flags50 & (1 << 2))

    @property
    def cell_count_verified(self):
        return bool(self._flags50 & (1 << 12))

    @property
    def cell_vr(self):
        return [(((val * 5.12) / 4095) / 8) * 1000 for val in struct.unpack('>HHHHHHHH', self._data[52:68])]

    @property
    def vr_amps(self):
        return struct.unpack('>H', self._data[68:70])[0] / 600.0

    @property
    def vr_offset(self):
        return (((struct.unpack('>H', self._data[114:116])[0] * 5.12) / 4095) / 8) * 1000

    @property
    def ch1_cells(self):
        return self._data[132]

    @property
    def mohm(self):
        vals = [0] * 8
        if self.vr_amps > 0:
            vals[0] = (self.cell_vr[0] - self.vr_offset) / self.vr_amps
            for ii in range(1, len(vals)):
                if self.ch1_cells == ii:
                    vals[ii] = (self.cell_vr[ii] / self.vr_amps) - ((self.cell_vr[ii] / self.vr_amps) / 8.0)
                else:
                    vals[ii] = self.cell_vr[ii] / self.vr_amps
        return vals

    @property
    def _flags76(self):
        return struct.unpack('>H', self._data[76:78])[0]

    @property
    def checking_peak(self):
        return bool(self._flags76 & (1 << 0))

    @property
    def battery_24v_visible(self):
        return bool(self._flags76 & (1 << 3))

    @property
    def cv_started(self):
        return bool(self._flags76 & (1 << 4))

    @property
    def preset_good(self):
        return bool(self._flags76 & (1 << 5))

    @property
    def preset_flash_changed(self):
        return bool(self._flags76 & (1 << 6))

    @property
    def regen_possible(self):
        return bool(self._flags76 & (1 << 7))

    @property
    def regen_dsch_failed(self):
        return bool(self._flags76 & (1 << 8))

    @property
    def options_flash_changed(self):
        return bool(self._flags76 & (1 << 10))

    @property
    def supply_amps(self):
        return struct.unpack('>h', self._data[80:82])[0] / 150.0

    @property
    def batt_pos_avg_volts(self):
        return ((struct.unpack('>H', self._data[82:84])[0] * 46.96) / 4095) / 16

    @property
    def mode(self):
        return self._data[133]

    @mode.setter
    def mode(self, val):
        self._data[133] = val

    @property
    def mode_to_str(self):
        mode = self.mode
        if mode == 0:
            return 'idle'
        elif mode == 1:
            return 'detecting cells'
        elif mode == 2:
            return 'ch1 startup'
        elif mode == 3:
            return 'ch1/2 startup'
        elif mode == 6:
            if self.is_charge_discharge_complete:
                return 'charge complete'
            elif self.is_reduce_amps:
                return 'low voltage restore'
            else:
                return 'charging'
        elif mode == 7:
            if self.is_charge_discharge_complete:
                return 'charge complete'
            # elif chemistry == pb
            #    return 'finishing'
            else:
                return 'trickle charging'
        elif mode == 8:
            if self.is_charge_discharge_complete:
                return 'discharge complete'
            elif not self.regen_enable:
                return 'internal discharge'
            elif self.regen_enable:
                return 'regenerative discharge'
        elif mode == 9:
            return 'monitoring cells'
        elif mode == 10:
            return 'wait for button press'
        elif mode == 30:
            return 'slave mode'
        elif mode == 0x63:
            return 'safety code ' + self.error_code
        else:
            return 'unknown'

    @property
    def discharge_set(self):
        return struct.unpack('>H', self._data[92:94])[0]

    # if (this.LoadChemistryVal(Preset[SlaveNum]) == 11):
    #    this.MaxCellVolts[SlaveNum] = 0.001
    # else:

    @property
    def set_amps(self):
        if self.mode == 8:
            return self.discharge_set / 600.0
        else:
            return self.charge_set / 600.0

    @property
    def max_cell_volts(self):
        return ((struct.unpack('>H', self._data[74:76])[0] * 5.12) / 4095) / 16

    @property
    def avg_cell_volts(self):
        if self.use_nodes and self.ch1_cells:
            return sum(self.b_volts) / self.ch1_cells
        else:
            return self.max_cell_volts

    @property
    def avg_ir(self):
        if self.use_nodes and self.show_vr and self.ch1_cells:
            return sum(self.mohm) / self.ch1_cells
        else:
            return 0

    @property
    def slow_avg_amps(self):
        return struct.unpack('>H', self._data[116:118])[0] / 600

    # index = struct.unpack('>h', self._data[118:120])[0]
    # if index >= 0:
    #     ManualChgAmps[SlaveNum] = index;
    #     ManualAutoAmps[SlaveNum] = 0;
    # else:
    #     ManualChgAmps[SlaveNum] = 0
    #     ManualAutoAmps[SlaveNum] = (short)(0 - index);
    # SlavesFound[SlaveNum] = Module1.valbin2(inBytes, 120);
    # ManualDschAmps[SlaveNum] = Module1.valbin2S(inBytes, 0x7a);

    @property
    def bypass_pwm(self):
        return [bb for bb in self._data[124:132]]

    @property
    def bypass_percent(self):
        return [bp * 3.09375 for bp in self.bypass_pwm]

    @property
    def bypass_current(self):
        return [bp * 31.25 for bp in self.bypass_pwm]

    @property
    def error_code(self):
        return self._data[134]

    @error_code.setter
    def error_code(self, val):
        self._data[134] = val

    @property
    def chem8(self):
        return self._data[135]

    @property
    def packs(self):
        return self._data[136]

    @property
    def active_preset(self):
        num = self._data[137]
        if num > 74 or num < 0:
            return 0
        return num

    @property
    def screen_number(self):
        return self._data[139]

    @property
    def check_pack1_volts(self):
        return (struct.unpack('>b', self._data[140:141])[0] * 46.96) / 4095

    @property
    def fuel_offset(self):
        return int(round((self._data[141] * 5.12) / 4.095))

    @property
    def cycle_cnt(self):
        return self._data[142]

    @property
    def lower_pwm_reason(self):
        return self._data[143]

    # 0 = Charge only
    # 1 = Discharge only
    # 2 = Monitor
    # 3 = Cycle
    @property
    def start_mode(self):
        return self._data[144]

    @property
    def start_mode_str(self):
        return _start_mode_to_str(self.start_mode)

    @property
    def r_fail_reason(self):
        return self._data[145]

    @property
    def charge_seconds(self):
        secs = (self._data[28] << 8) | self._data[29]
        mins = (self._data[78] << 8) | self._data[79]
        if secs >= 0xfd1f:
            return (secs - 64800) + (mins * 60)
        else:
            return secs

    @property
    def mah_in(self):
        val = struct.unpack('>L', self._data[34:38])[0]
        if val > 0x7fffffff:
            val = 0
        if self.packs > 1:
            val /= float(self.packs)
        return val / 2160.0

    @property
    def mah_out(self):
        val = struct.unpack('>L', self._data[84:88])[0]
        if val > 0x7fffffff:
            val = 0
        if self.packs > 1:
            val /= float(self.packs)
        return val / 2160.0

    @property
    def fuel_level(self):
        val = struct.unpack('>h', self._data[38:40])[0]
        if val < 0:
            val = 0
        elif val > 1000:
            val = 1000
        return val

    @property
    def no_data_max(self):
        mode = self.mode
        if 6 <= mode <= 11:
            return 30
        else:
            return 3

    def __str__(self):
        return str_from_props(self)

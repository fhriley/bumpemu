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

from bumpemu.util import byte_to_char, bits_from_int16, str_from_props, int16_to_bits, checksum


class Preset(object):
    CHEMISTRY = ['Empty', 'LiPo', 'Lith Ion', 'A123', 'LiMn', 'LiCo', 'NiCd', 'NiMH',
                 'Pb', 'LiFe (Chinese A123)', 'Primary (Dsch Only)', 'Supply (Low Voltage)',
                 'NiZn', 'LiHV']

    def __init__(self, data, preset_num):
        self._data = bytearray(data)
        self._preset_num = preset_num

    def raw_bytes(self):
        # noinspection PyAttributeOutsideInit
        self.checksum = self.calc_checksum()
        return bytes(self._data)

    @property
    def preset_num(self):
        return self._preset_num

    @property
    def is_require_balance_done_enabled(self):
        return bool(bits_from_int16(self._data, index=0, start_bit=0, end_bit=0))

    @is_require_balance_done_enabled.setter
    def is_require_balance_done_enabled(self, value):
        int16_to_bits(self._data, index=0, start_bit=0, end_bit=0, value=1 if value else 0)

    @property
    def is_require_all_charge_volts_enabled(self):
        return bool(bits_from_int16(self._data, index=0, start_bit=11, end_bit=11))

    @is_require_all_charge_volts_enabled.setter
    def is_require_all_charge_volts_enabled(self, value):
        int16_to_bits(self._data, index=0, start_bit=11, end_bit=11, value=1 if value else 0)

    @property
    def name(self):
        chars = []
        for ii in range(4, 32, 2):
            chars.append(byte_to_char(self._data[ii + 1]))
            chars.append(byte_to_char(self._data[ii]))
        return ''.join(chars)

    @name.setter
    def name(self, value):
        if len(value) > 28:
            raise Exception('name too long')
        if len(value) < 28:
            spaces = [' '] * (28 - len(value))
            value += ''.join(spaces)
        assert (len(value) == 28)
        for ii in range(4, 32, 2):
            self._data[ii + 1] = ord(value[ii - 4])
            self._data[ii] = ord(value[ii - 3])

    @property
    def charge_mamps(self):
        val = bits_from_int16(self._data, index=32, start_bit=4, end_bit=14)
        if val < 200:
            return val * 5
        else:
            return 1000 + ((val - 200) * 50)

    @charge_mamps.setter
    def charge_mamps(self, value):
        set_val = min(value, 40000)
        if set_val < 1000:
            set_val = int((set_val + 2.5) // 5) * 5
            set_val //= 5
        elif set_val >= 1000:
            set_val = ((set_val + 25) // 50) * 50
            set_val = ((set_val - 1000) // 50) + 200
        else:
            raise Exception('invalid value: %s' % value)
        int16_to_bits(self._data, index=32, start_bit=4, end_bit=14, value=set_val)

    @property
    def charge_volts(self):
        return bits_from_int16(self._data, index=34, start_bit=0, end_bit=9) / 200.0

    @charge_volts.setter
    def charge_volts(self, value):
        int16_to_bits(self._data, index=34, start_bit=0, end_bit=9, value=int(round(value * 200)))

    @property
    def discharge_mode(self):
        return bits_from_int16(self._data, index=84, start_bit=9, end_bit=11)

    @discharge_mode.setter
    def discharge_mode(self, val):
        int16_to_bits(self._data, index=84, start_bit=9, end_bit=11, value=val)

    @property
    def discharge_mamps(self):
        val = bits_from_int16(self._data, index=48, start_bit=0, end_bit=8)
        if val <= 100:
            return val * 10
        else:
            return 1000 + (val - 100) * 250

    @discharge_mamps.setter
    def discharge_mamps(self, value):
        if value <= 1000:
            value = ((value + 5) // 10) * 10
            value //= 10
        elif value > 1000:
            value = ((value + 125) // 250) * 250
            value = ((value - 1000) // 250) + 100
        else:
            raise Exception('invalid value: %s' % value)
        int16_to_bits(self._data, index=48, start_bit=0, end_bit=8, value=value)

    @property
    def discharge_volts(self):
        return bits_from_int16(self._data, index=98, start_bit=6, end_bit=14) / 100.0

    @discharge_volts.setter
    def discharge_volts(self, value):
        int16_to_bits(self._data, index=98, start_bit=6, end_bit=14, value=int(round(value * 100)))

    @property
    def is_store_charge_discharge(self):
        return bool(bits_from_int16(self._data, index=46, start_bit=12, end_bit=12))

    @is_store_charge_discharge.setter
    def is_store_charge_discharge(self, value):
        int16_to_bits(self._data, index=46, start_bit=12, end_bit=12, value=1 if value else 0)

    @property
    def is_end_cycling_with_discharge_enabled(self):
        return bool(bits_from_int16(self._data, index=46, start_bit=14, end_bit=14))

    @is_end_cycling_with_discharge_enabled.setter
    def is_end_cycling_with_discharge_enabled(self, value):
        int16_to_bits(self._data, index=46, start_bit=14, end_bit=14, value=1 if value else 0)

    @property
    def cool_down_time(self):
        return bits_from_int16(self._data, index=48, start_bit=10, end_bit=13)

    @cool_down_time.setter
    def cool_down_time(self, val):
        int16_to_bits(self._data, index=48, start_bit=10, end_bit=13, value=val)

    @property
    def cv_termination(self):
        return bits_from_int16(self._data, index=48, start_bit=14, end_bit=15)

    @cv_termination.setter
    def cv_termination(self, val):
        int16_to_bits(self._data, index=48, start_bit=14, end_bit=15, value=val)

    @property
    def is_balance_entire_charge_enabled(self):
        return bool(bits_from_int16(self._data, index=54, start_bit=15, end_bit=15))

    @is_balance_entire_charge_enabled.setter
    def is_balance_entire_charge_enabled(self, value):
        int16_to_bits(self._data, index=54, start_bit=15, end_bit=15, value=1 if value else 0)

    @property
    def beep_at_percent(self):
        return bits_from_int16(self._data, index=58, start_bit=11, end_bit=15) * 2 + 38

    @beep_at_percent.setter
    def beep_at_percent(self, val):
        int16_to_bits(self._data, index=58, start_bit=11, end_bit=15, value=(val - 38) // 2)

    @property
    def is_trickle_only(self):
        return bool(bits_from_int16(self._data, index=0, start_bit=5, end_bit=5))

    @is_trickle_only.setter
    def is_trickle_only(self, value):
        int16_to_bits(self._data, index=0, start_bit=5, end_bit=5, value=1 if value else 0)

    @property
    def is_balance_discharge_enabled(self):
        return bool(bits_from_int16(self._data, index=96, start_bit=8, end_bit=8))

    @is_balance_discharge_enabled.setter
    def is_balance_discharge_enabled(self, value):
        int16_to_bits(self._data, index=96, start_bit=8, end_bit=8, value=1 if value else 0)

    @property
    def chemistry_idx(self):
        return bits_from_int16(self._data, index=58, start_bit=6, end_bit=10)

    @chemistry_idx.setter
    def chemistry_idx(self, val):
        int16_to_bits(self._data, index=58, start_bit=6, end_bit=10, value=val)

    @property
    def chemistry(self):
        idx = self.chemistry_idx
        if idx >= len(self.CHEMISTRY):
            raise Exception('unknown battery type index: ' + idx)
        return self.CHEMISTRY[idx]

    # noinspection PyAttributeOutsideInit
    @chemistry.setter
    def chemistry(self, val):
        if isinstance(val, str):
            try:
                idx = self.CHEMISTRY.index(val)
            except ValueError:
                raise Exception('invalid chemistry: %s' % val)
        elif 0 <= val < len(self.CHEMISTRY):
            idx = val
        else:
            raise Exception('invalid chemistry: %s' % val)
        self.chemistry_idx = idx

    # 0: off
    # 1: constant current then constant voltage
    # 2: constant current
    @property
    def power_mode(self):
        return bits_from_int16(self._data, index=32, start_bit=0, end_bit=3)

    @power_mode.setter
    def power_mode(self, val):
        int16_to_bits(self._data, index=32, start_bit=0, end_bit=3, value=val)

    @property
    def is_requires_nodes_enabled(self):
        return bool(bits_from_int16(self._data, index=86, start_bit=13, end_bit=13))

    @is_requires_nodes_enabled.setter
    def is_requires_nodes_enabled(self, value):
        int16_to_bits(self._data, index=86, start_bit=13, end_bit=13, value=1 if value else 0)

    @property
    def auto_charge_rate(self):
        return bits_from_int16(self._data, index=0, start_bit=12, end_bit=15)

    @auto_charge_rate.setter
    def auto_charge_rate(self, val):
        int16_to_bits(self._data, index=0, start_bit=12, end_bit=15, value=val)

    @property
    def max_auto_charge_rate(self):
        return bits_from_int16(self._data, index=2, start_bit=10, end_bit=13)

    @max_auto_charge_rate.setter
    def max_auto_charge_rate(self, val):
        int16_to_bits(self._data, index=2, start_bit=10, end_bit=13, value=val)

    @property
    def is_use_fuel_enabled(self):
        return bool(bits_from_int16(self._data, index=0, start_bit=10, end_bit=10))

    @is_use_fuel_enabled.setter
    def is_use_fuel_enabled(self, value):
        int16_to_bits(self._data, index=0, start_bit=10, end_bit=10, value=1 if value else 0)

    @property
    def num_cycles(self):
        val = bits_from_int16(self._data, index=88, start_bit=10, end_bit=12)
        if val == 4:
            val = 5
        elif val == 5:
            val = 10
        elif val == 6:
            val = 20
        elif val == 7:
            val = 2 ** 32
        elif val > 7:
            raise Exception("unknown num cycles")
        return val

    @num_cycles.setter
    def num_cycles(self, val):
        if val not in (0, 1, 2, 3):
            if val == 5:
                val = 4
            elif val == 10:
                val = 5
            elif val == 20:
                val = 6
            elif val == 2 ** 32:
                val = 7
            else:
                raise Exception("unknown num cycles")
        int16_to_bits(self._data, index=88, start_bit=10, end_bit=12, value=val)

    @property
    def trickle_current_mamps(self):
        val = bits_from_int16(self._data, index=56, start_bit=9, end_bit=15)
        if val == 125:
            val = 1000
        elif val == 126:
            val = 2000
        elif val == 127:
            val = 3000
        else:
            val *= 5
        return val

    @trickle_current_mamps.setter
    def trickle_current_mamps(self, val):
        if val == 1000:
            val = 125
        elif val == 2000:
            val = 126
        elif val == 3000:
            val = 127
        elif val <= 620:
            val //= 5
        else:
            raise Exception('invalid value: %s' % val)
        int16_to_bits(self._data, index=56, start_bit=9, end_bit=15, value=val)

    @property
    def is_visible(self):
        return bool(bits_from_int16(self._data, index=32, start_bit=15, end_bit=15))

    @is_visible.setter
    def is_visible(self, value):
        int16_to_bits(self._data, index=32, start_bit=15, end_bit=15, value=1 if value else 0)

    @property
    def is_hide_empty_enabled(self):
        return bool(bits_from_int16(self._data, index=94, start_bit=15, end_bit=15))

    @is_hide_empty_enabled.setter
    def is_hide_empty_enabled(self, value):
        int16_to_bits(self._data, index=94, start_bit=15, end_bit=15, value=1 if value else 0)

    @property
    def is_locked(self):
        return bool(bits_from_int16(self._data, index=98, start_bit=15, end_bit=15))

    @is_locked.setter
    def is_locked(self, value):
        int16_to_bits(self._data, index=98, start_bit=15, end_bit=15, value=1 if value else 0)

    @property
    def num_parallel(self):
        return bits_from_int16(self._data, index=52, start_bit=8, end_bit=10) + 1

    @num_parallel.setter
    def num_parallel(self, value):
        if value <= 0:
            raise Exception('value must be >= 1')
        int16_to_bits(self._data, index=52, start_bit=8, end_bit=10, value=value - 1)

    @property
    def cv_timeout(self):
        return bits_from_int16(self._data, index=92, start_bit=5, end_bit=7)

    @cv_timeout.setter
    def cv_timeout(self, val):
        int16_to_bits(self._data, index=92, start_bit=5, end_bit=7, value=val)

    @property
    def charge_timeout(self):
        return bits_from_int16(self._data, index=52, start_bit=13, end_bit=15)

    @charge_timeout.setter
    def charge_timeout(self, val):
        int16_to_bits(self._data, index=52, start_bit=13, end_bit=15, value=val)

    @property
    def discharge_timeout(self):
        return bits_from_int16(self._data, index=54, start_bit=4, end_bit=6)

    @discharge_timeout.setter
    def discharge_timeout(self, val):
        int16_to_bits(self._data, index=54, start_bit=4, end_bit=6, value=val)

    @property
    def checksum(self):
        return (self._data[100] << 8) | self._data[101]

    @checksum.setter
    def checksum(self, value):
        self._data[100] = (value >> 8) & 0xff
        self._data[101] = value & 0xff

    @property
    def is_validated(self):
        return bool(bits_from_int16(self._data, index=36, start_bit=14, end_bit=15))

    @is_validated.setter
    def is_validated(self, value):
        int16_to_bits(self._data, index=36, start_bit=14, end_bit=15, value=1 if value else 0)

    @property
    def balance_mode(self):
        return bits_from_int16(self._data, index=82, start_bit=10, end_bit=13)

    @property
    def require_nodes(self):
        return bool(bits_from_int16(self._data, index=86, start_bit=13, end_bit=13))

    @property
    def fuel_curve(self):
        return [((self._data[ii] << 8) | self._data[ii + 1]) * 0.001111111 for ii in range(60, 82, 2)]

    @fuel_curve.setter
    def fuel_curve(self, val):
        ii = 60
        for vv in val:
            self._data[ii] = (vv >> 8) & 0xff
            self._data[ii + 1] = vv & 0xff
            ii += 2
            if ii == 82:
                break

    @property
    def max_charge_amps(self):
        val = bits_from_int16(self._data, index=34, start_bit=10, end_bit=15)
        if val == 0:
            return 0.25
        elif val == 1:
            return 0.5
        else:
            return val - 1

    @max_charge_amps.setter
    def max_charge_amps(self, val):
        if val < 1:
            val *= 100
            val = int(round(((val + 12.5) // 25) * 25))
            if val <= 25:
                val = 0
            elif val <= 50:
                val = 1
            else:
                val = 2
        else:
            val = min(int(round(val) + 1), 41)
        int16_to_bits(self._data, index=34, start_bit=10, end_bit=15, value=val)

    @property
    def is_empty(self):
        return (sum(self._data[:-2]) - self._data[94]) == 0

    def calc_checksum(self):
        return checksum(self._data[:-2], init=0x2d)

    def __str__(self):
        return str_from_props(self)

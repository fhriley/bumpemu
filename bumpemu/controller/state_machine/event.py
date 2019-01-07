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

from enum import Enum
from bumpemu.controller import constants


class Event(Enum):
    NONE = 0
    CONNECTED = 1
    DISCONNECTED = 2
    IDLE = 3
    STARTING = 4
    CHARGING = 5
    DISCHARGING = 6
    MONITORING = 7
    STOP = 8
    CHARGING_COMPLETE = 9
    DISCHARGING_COMPLETE = 10
    DISMISS = 11
    ERROR = 12
    HALT_FOR_SAFETY = 13

    @classmethod
    def get_from_charge_status(cls, chg_status):
        mode = chg_status.mode
        if mode == constants.ChargerMode.READY_TO_START:
            return Event.IDLE
        elif mode == constants.ChargerMode.DETECTING_PACK.value:
            return Event.STARTING
        elif constants.ChargerMode.DETECTING_PACK.value < mode <= constants.ChargerMode.TRICKLE_CHARGING.value:
            if chg_status.is_charge_discharge_complete:
                return Event.CHARGING_COMPLETE
            else:
                return Event.CHARGING
        elif mode == constants.ChargerMode.DISCHARGING.value:
            if chg_status.is_charge_discharge_complete:
                return Event.DISCHARGING_COMPLETE
            else:
                return Event.DISCHARGING
        elif mode == constants.ChargerMode.MONITORING.value:
            return Event.MONITORING
        elif mode == constants.ChargerMode.HALT_FOR_SAFETY.value:
            return Event.HALT_FOR_SAFETY
        elif mode == constants.ChargerMode.ERROR.value:
            return Event.ERROR
        else:
            return Event.NONE

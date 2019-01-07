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
from enum import Enum


class Message(object):
    PREAMBLE_BYTE = 0x17
    PAYLOAD_LEN_FORMAT = '<H'
    PAYLOAD_LEN_BYTES = struct.calcsize(PAYLOAD_LEN_FORMAT)
    PAYLOAD_LEN_OFFSET = 3
    HEADER_FORMAT = '<BBB' + PAYLOAD_LEN_FORMAT[1:]
    HEADER_BYTES = struct.calcsize(HEADER_FORMAT)
    PAYLOAD_OFFSET = HEADER_BYTES
    CRC_FORMAT = '<H'
    CRC_BYTES = struct.calcsize(CRC_FORMAT)
    CRC_SEED = 0x5ada
    OVERHEAD = HEADER_BYTES + CRC_BYTES
    MESSAGE_ID_OFFSET = 2


class MessageId(Enum):
    BATTERY_GROUP_NOT = 0x6
    SELECTED_OPERATION_NOT = 0x8
    OPERATION_START_CMD = 0x9
    OPERATION_STOP_CMD = 0xa
    MONITOR_CMD = 0xb
    CHARGER_SETTINGS = 0xc
    OPERATION_CLEAR_ERROR_CMD = 0xd
    CONNECT_REQUEST = 0xe
    CYCLE_GRAPH_GET = 0x15
    CONNECT_ACK = 0x16
    GET_DEVICE_INFO_CMD = 0x19
    DEVICE_INFO = 0x1a
    SELECT_CHARGER_CMD = 0x1d
    DISMISS_CMD = 0x1e
    MANUAL_OPERATION_CMD = 0x20
    SET_BATTERY_GROUP_COUNT_CMD = 0x21
    CYCLE_GRAPH_GET_COMPLETE = 0x23
    STATUS_UPDATE_NOT2 = 0x2d
    STATUS_IDLE_UPDATE_NOT2 = 0x2e
    BUMP_SETTINGS = 0x2f


class ChargerModel(Enum):
    NONE = 0x0
    PL_6 = 0x36
    PL_8 = 0x38


class ChargerMode(Enum):
    READY_TO_START = 0
    DETECTING_PACK = 1
    CHARGING = 6
    TRICKLE_CHARGING = 7
    DISCHARGING = 8
    MONITORING = 9
    HALT_FOR_SAFETY = 10
    PACK_COOL_DOWN = 11
    ERROR = 99


class ChargerOperation(Enum):
    ACCURATE = 0
    NORMAL = 1
    FASTEST = 2
    STORAGE = 3
    DISCHARGE = 4
    ANALYZE = 5
    MONITOR = 6
    TRICKLE = 7
    NONE = 8


class ChargerOperationFlag(Enum):
    NONE = 0
    CELLIR_WARNING = 15
    CAPACITY_WARNING = 16
    COMPLETE = 32
    STOPPED = 64
    DISMISSED = 128


class ChargerStatusFlag(Enum):
    NONE = 0
    SAFETY_CHARGE = 1
    GENERATE_FUEL = 32
    COMPLETE = 256
    REDUCE_AMPS = 2048
    SHOW_VR = 4096
    NODES_ONLY = 16384
    COLD_WEATHER = 32768


class ChargerRxStatusFlag(Enum):
    NONE = 0
    DISCHARGE = 2
    REGEN_DISCHARGE = 16
    CHARGE = 64
    BALANCERS = 128


class ChargerPowerReducedReason(Enum):
    NONE = 0
    INPUT_CURRENT_LIMIT = 1
    INPUT_CURRENT_MAX = 2
    CELL_SUM_ERROR = 3
    SUPPLY_NOISE = 4
    HIGH_TEMP = 5
    INPUT_VOLTAGE_LOW = 6
    OUTPUT_CV = 7
    INTERNAL_DISCHARGE_MAX_WATTS = 8
    HIGH_TEMP_DISCHARGE = 9
    REGEN_MAX_AMPS = 10
    HIGH_TEMP_DISCHARGE2 = 11
    CELL_SUM_ERROR_DISCHARGE = 12
    REGEN_VOLT_LIMIT = 13
    BELOW_AVE_CHARGER = 14
    ABOVE_AVE_CHARGER = 15
    SUPPLY_LOW_FOR_HIGH_POWER = 16


class CommState(Enum):
    COMM_DISCONNECTED = 0x0
    COMM_OPTIONS_WRONG = 0x1
    COMM_OPTIONS_BAD_CHECKSUM = 0x2
    COMM_OPTIONS_VERIFIED = 0x3
    COMM_OPTIONS_WAIT_FOR_DISCONNECT = 0x4
    COMM_OPTIONS_ERASED = 0x5
    COMM_OPTIONS_UPDATED = 0x6
    COMM_CONNECTED = 0x7
    COMM_DISABLED = 0x8
    COMM_FIRMWARE_UPDATE_CMD_SENT = 0xa
    COMM_FIRMWARE_UPDATING = 0xb
    COMM_FIRMWARE_SUCCESS = 0xc
    COMM_FIRMWARE_FAILED = 0xd
    COMM_FIRMWARE_READY_FOR_DOWNLOAD = 0xe
    COMM_INTERNAL_DISCONNECTED = 0xf
    COMM_FIRMWARE_WAIT_FOR_DISCONNECT = 0x10


class Chemistry(Enum):
    NONE = 0
    LIPO = 1
    LION = 2
    A123 = 3
    LIMN = 4
    LICO = 5
    NICD = 6
    NIMH = 7
    PB = 8
    LIFE = 9
    PRIM = 10
    SPLY = 11
    NIZN = 12
    LIHV = 13


class PowerSupplyMode(Enum):
    DC = 0
    BATTERY = 1

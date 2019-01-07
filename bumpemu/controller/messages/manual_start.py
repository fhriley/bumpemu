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

import os
import logging
from bumpemu.controller import constants
from bumpemu.controller.serialize import append_uint16, append_bool, read_uint16


class ManualStart(object):
    def __init__(self, buf=None):
        self._logger = logging.getLogger(__name__)
        if buf:
            self.deserialize(buf)
        else:
            self.charger_port_number = 0
            self.chemistry = constants.Chemistry.NONE
            self.cells = 0
            self.operation = constants.ChargerOperation.NONE
            self.cell_term_v = 0
            self.rate = 0
            self.balanced = True

    def serialize(self):
        buf = bytearray()
        buf.append(self.charger_port_number)
        # noinspection PyTypeChecker
        buf.append(self.chemistry.value)
        buf.append(self.cells)
        # noinspection PyTypeChecker
        buf.append(self.operation.value)
        append_uint16(buf, self.cell_term_v * 1000)
        append_uint16(buf, self.rate)
        append_bool(buf, self.balanced)
        return buf

    def deserialize(self, buf):
        self.charger_port_number = buf[0]
        self.chemistry = constants.Chemistry(buf[1])
        self.cells = buf[2]
        self.operation = constants.ChargerOperation(buf[3])
        self.cell_term_v = read_uint16(buf[4:6]) / 1000.0
        self.rate = read_uint16(buf[6:8])
        self.balanced = bool(buf[8])

    def __str__(self):
        return os.linesep.join(
            ['%s: %s' % (var, getattr(self, var)) for var in sorted(vars(self)) if not var.startswith('_')])

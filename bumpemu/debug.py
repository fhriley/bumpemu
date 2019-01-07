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

LOG_SERIAL = False
LOG_BLUETOOTH = False
LOG_STATUS = False


def print_bytes(logger, level, buf, prefix=''):
    if logger.isEnabledFor(level):
        ii = 0
        for bb in buf:
            if 0x20 <= bb <= 0x7e:
                logger.debug('%s [%d] %s: %s', prefix, ii, hex(bb), chr(bb))
            else:
                logger.debug('%s [%d] %s', prefix, ii, hex(bb))
            ii += 1

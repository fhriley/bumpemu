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

import argparse
import logging
import os
import sys

from bumpemu import debug
from bumpemu.charger.powerlab import Powerlab

import serial.tools.list_ports as list_ports


def run(args, logger):
    if args.list_ports:
        for port in list_ports.comports():
            print(port)
        return

    try:
        with Powerlab(args.port) as ser:
            if args.presets:
                all_presets = ser.read_presets()
                for pp in all_presets:
                    logger.debug('---------------------------')
                    logger.debug('Preset %d (cksum: %s): %s', pp.preset_num, pp.calc_checksum(), pp.name)
                    logger.debug('---------------------------')
                    logger.debug('%s%s', os.linesep, pp)
                if args.write:
                    ser.write_presets(all_presets)

            if args.status:
                ss = ser.read_status()
                logger.debug('%s%s', os.linesep, ss)
                if ss.error_code:
                    raise Exception('monitor command failed: %d' % ss.error_code)

            if args.options:
                opts = ser.read_options()
                logger.debug('%s%s', os.linesep, opts)
                if args.write:
                    ser.write_options(opts)

            if args.monitor:
                ser.command_monitor(num_parallel=args.num_parallel, use_bananas=not args.no_bananas)
            if args.enter:
                ser.command_enter()
            if args.charge:
                ser.command_charge(num_parallel=args.num_parallel, use_bananas=not args.no_bananas)
            if args.discharge:
                ser.command_discharge(num_parallel=args.num_parallel, use_bananas=not args.no_bananas)
            if args.cycle:
                ser.command_cycle(num_parallel=args.num_parallel, use_bananas=not args.no_bananas)
            if args.set_preset is not None:
                ser.command_set_active_preset(args.set_preset)
    except Exception as ex:
        logger.exception(ex)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('port', help='serial port')
    parser.add_argument('-l', '--log-level', default='INFO', help='set the log level (default: INFO)')
    parser.add_argument('-s', '--status', action='store_true', help='get status')
    parser.add_argument('-p', '--presets', action='store_true', help='get presets')
    parser.add_argument('-o', '--options', action='store_true', help='get options')
    parser.add_argument('-m', '--monitor', action='store_true', help='send the monitor command')
    parser.add_argument('-e', '--enter', action='store_true', help='send the enter command')
    parser.add_argument('-c', '--charge', action='store_true', help='send the charge command')
    parser.add_argument('-d', '--discharge', action='store_true', help='send the discharge command')
    parser.add_argument('-y', '--cycle', action='store_true', help='send the cycle command')
    parser.add_argument('-w', '--write', action='store_true', help='add write to the read')
    parser.add_argument('--set-preset', type=int, help='set the active preset')
    parser.add_argument('--num-parallel', type=int, default=1, help='set the number of parallel packs (default 1)')
    parser.add_argument('--no-bananas', action='store_true', help='turn off bananas')
    parser.add_argument('--list-ports', action='store_true', help='list serial ports')
    parser.add_argument('--log-serial', action='store_true', help='log the raw serial bytes')
    pargs = parser.parse_args()

    loggr = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(filename)s:%(lineno)d|%(message)s')
    handler.setFormatter(formatter)
    loggr.addHandler(handler)
    loggr.setLevel(getattr(logging, pargs.log_level))

    debug.LOG_SERIAL = pargs.log_serial

    run(pargs, loggr)


if __name__ == '__main__':
    main()

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
import sys
import logging
import argparse
from yaml import load, Loader
import dbus
import dbus.mainloop.glib
import serial.tools.list_ports as list_ports
from gi.repository import GLib
from bumpemu.controller import bluez_dbus, constants
from bumpemu.controller.emulator import BumpEmulator, UartAdvertisement
from bumpemu.controller.messages.battery import Battery
from bumpemu.charger.powerlab import Powerlab
from bumpemu.util import ignore_exc
from bumpemu import debug


def _check_charger(port):
    with Powerlab(port) as pl:
        print('Reading options...')
        options = pl.read_options()
        print('Reading status...')
        status = pl.read_status()
        print('Reading presets (slow)...')
        presets = [preset for preset in pl.read_presets() if not preset.is_empty]
        print(options.greeting_line1.strip())
        print('Firmware: v%.2f' % (status.firmware_version / 100.0))
        print('Presets: %d' % len(presets))


def _print_preset(preset, preset_key):
    operation = preset_key[0].upper() + preset_key[1:]
    print('-' * 40)
    print(operation)
    print('-' * 40)
    print('  name: %s' % preset.name.strip())
    print('  preset_num: %s' % preset.preset_num)
    print('  chemistry: %s' % preset.chemistry)
    print('  charge_mamps: %s' % preset.charge_mamps)
    print('  max_charge_amps: %s' % preset.max_charge_amps)
    print('  charge_volts: %s' % preset.charge_volts)
    print('  discharge_mamps: %s' % preset.discharge_mamps)
    print('  discharge_volts: %s' % preset.discharge_volts)
    print('  num_parallel: %s' % preset.num_parallel)
    print('  num_cycles: %s' % preset.num_cycles)


def _print_presets(args, presets):
    keys = sorted(args.presets_config.keys())
    for key in keys:
        _print_preset(presets[args.presets_config[key]], key)


def _show_presets(args):
    with Powerlab(args.port) as pl:
        print('Reading presets (slow)...')
        presets = pl.read_presets()
        _print_presets(args, presets)


def _register_app_cb(logger, flag):
    logger.info('App registered')
    flag.registered = True


def _register_app_error_cb(logger, error, mainloop):
    logger.error('Failed to register app: %s', error)
    mainloop.quit()


def _register_ad_cb(logger, flag):
    logger.info('Advertisement registered')
    flag.registered = True


def _register_ad_error_cb(logger, error, mainloop):
    logger.error('Failed to register advertisement: %s', error)
    mainloop.quit()


def run(args, logger):
    try:
        if args.list_ports:
            for port in list_ports.comports():
                print(port)
            raise SystemExit(0)

        if args.check:
            _check_charger(args.port)
            raise SystemExit(0)

        if args.show_presets:
            _show_presets(args)
            raise SystemExit(0)

        presets = {constants.ChargerOperation[key.upper()]: val for key, val in args.presets_config.items()}

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        mainloop = GLib.MainLoop()

        # noinspection PyPep8Naming
        class registered_flag:
            registered = False

        app_flag = registered_flag()
        adv_flag = registered_flag()

        bluez_obj = bluez_dbus.get_bluez_obj(bus)
        app = None
        adv = None
        pl = None

        try:
            if not args.no_app_register:
                pl = Powerlab(args.port)
                service_manager = dbus.Interface(bluez_obj, bluez_dbus.GATT_MANAGER_IFACE)
                app = BumpEmulator(bus, 'bump_emulator', pl, args.battery, presets, args.status_interval)
                service_manager.RegisterApplication(
                    app.path,
                    {},
                    reply_handler=lambda: _register_app_cb(logger, app_flag),
                    error_handler=lambda ee: _register_app_error_cb(logger, ee, mainloop))
            if not args.no_advertise:
                adv_manager = dbus.Interface(bluez_obj, bluez_dbus.LE_ADVERTISING_MANAGER_IFACE)
                adv = UartAdvertisement(bus, 'bump_emulator', 0)
                adv_manager.RegisterAdvertisement(
                    adv.path,
                    {},
                    reply_handler=lambda: _register_ad_cb(logger, adv_flag),
                    error_handler=lambda ee: _register_ad_error_cb(logger, ee, mainloop))

            mainloop.run()
        finally:
            if adv_flag.registered:
                ignore_exc(func=lambda: adv_manager.UnregisterAdvertisement(adv.path))
                logger.info('Advertisement unregistered')
            if app_flag.registered:
                ignore_exc(func=lambda: service_manager.UnregisterApplication(app.path))
                logger.info('App unregistered')
            if pl:
                ignore_exc(func=pl.close)
    except KeyboardInterrupt:
        raise SystemExit(0)
    except SystemExit:
        pass
    except Exception as ex:
        logger.exception(ex)
        raise SystemExit(1)


def _positive_int(value):
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('%s is an invalid positive int value' % value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError('%s is an invalid positive int value' % value)
    return ivalue


def _battery_file(value):
    if os.path.isfile(value):
        try:
            return Battery.from_yaml(value)
        except Exception as ex:
            reason = str(ex)
    else:
        reason = "not a file"
    raise argparse.ArgumentTypeError(reason)


def _presets_file(value):
    reason = ''
    if os.path.isfile(value):
        try:
            with open(value, 'r') as stream:
                data = load(stream, Loader=Loader)
                required = {'accurate', 'normal', 'fastest', 'storage', 'discharge', 'analyze', 'monitor'}
                missing = required.difference(data.keys())
                if missing:
                    raise argparse.ArgumentTypeError('the following are missing from the presets config '
                                                     'file: %s' % ', '.join(missing))
                ret = {}
                for key, val in data.items():
                    ret[key] = _positive_int(val) - 1
                return ret
        except argparse.ArgumentTypeError:
            raise
        except Exception as ex:
            reason = str(ex)
    else:
        reason = "not a file"
    raise argparse.ArgumentTypeError(reason)


def main():
    presets_yml = os.path.realpath('/etc/bumpemu/presets.yml')
    battery_yml = os.path.realpath('/etc/bumpemu/battery.yml')
    if not os.path.isfile(battery_yml):
        battery_yml = None

    parser = argparse.ArgumentParser(usage='python3 -m bumpemu.main [options]',
                                     description='A bump controller for BLE that emulates a real bump controller.')
    parser.add_argument('--list-ports', action='store_true', help='List serial ports and exit.')
    parser.add_argument('-p', '--port', help='Set the serial port (default: auto search for port).')
    parser.add_argument('-c', '--check', action='store_true', help='Check the connection to the powerlab and exit.')
    parser.add_argument('-b', '--battery', type=_battery_file, metavar='YML', default=battery_yml,
                        help='Load a battery configuration from the given YAML file. (default: %s)' % battery_yml)
    parser.add_argument('--show-presets', action='store_true',
                        help='Read the presets from the powerlab, show the presets that will be used, and exit.')
    parser.add_argument('--presets-config', type=_presets_file, metavar='YML', default=presets_yml,
                        help='Set the presets configuration YAML file. (default: %s)' % presets_yml)
    parser.add_argument('-A', '--no-advertise', action='store_true',
                        help="Don't advertise on BLE.")
    parser.add_argument('-R', '--no-app-register', action='store_true',
                        help="Don't register the app with BLE.")
    parser.add_argument('--status-interval', type=_positive_int, default=1, metavar='SECONDS',
                        help=('Set the interval in seconds when status is retrieved from the charger. '
                              'Dev use only. (default: 1).'))
    parser.add_argument('-l', '--log-level', metavar='LEVEL', default='INFO',
                        help='Set the log level (default: INFO).')
    parser.add_argument('--log-serial', action='store_true', help='Turn on logging of the raw serial bytes.')
    parser.add_argument('--log-bluetooth', action='store_true', help='Turn on logging of the raw bluetooth bytes.')
    parser.add_argument('--log-status', action='store_true', help='Turn on logging of the charger status object.')
    pargs = parser.parse_args()

    loggr = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(filename)s:%(lineno)d|%(message)s')
    handler.setFormatter(formatter)
    loggr.addHandler(handler)
    loggr.setLevel(getattr(logging, pargs.log_level))

    debug.LOG_SERIAL = pargs.log_serial
    debug.LOG_BLUETOOTH = pargs.log_bluetooth
    debug.LOG_STATUS = pargs.log_status

    run(pargs, loggr)


if __name__ == '__main__':
    main()

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
import struct
from threading import RLock, Condition

import dbus
from gi.repository import GLib

from bumpemu.util import crc16
from bumpemu.controller import bluez_dbus
from bumpemu.controller.messages import bump_settings, charger_idle, charger_status, charger_settings, battery
from bumpemu.controller import constants
from bumpemu.controller.message_handler import MessageHandler
from bumpemu.controller.state_machine import state
from bumpemu.controller.state_machine.event import Event
from bumpemu.charger.powerlab import PowerlabException
from bumpemu import debug
from bumpemu.debug import print_bytes


class UartAdvertisement(bluez_dbus.Advertisement):
    def __init__(self, bus, path, index):
        super(UartAdvertisement, self).__init__(bus, path, index, 'peripheral')
        self.add_service_uuid(UartService.UUID)
        self.include_tx_power = True


class BumpEmulator(bluez_dbus.Application):
    def __init__(self, bus, path, charger, batt, presets, status_interval):
        super(BumpEmulator, self).__init__(bus)
        self._logger = logging.getLogger(__name__)
        self.add_service(UartService(bus, path, 0, charger, batt, presets, status_interval))


class UartService(bluez_dbus.Service):
    UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'

    def __init__(self, bus, path, index, charger, batt, presets, status_interval):
        super(UartService, self).__init__(bus, path, index, self.UUID, True)
        self._logger = logging.getLogger(__name__)
        self._bus = bus
        self._rx_chrc = RxChrc(bus, 1, self, charger, batt, presets, status_interval)
        self.add_characteristic(TxChrc(bus, 0, self, self._rx_chrc))
        self.add_characteristic(self._rx_chrc)


class TxChrc(bluez_dbus.Characteristic):
    UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'

    def __init__(self, bus, index, service, rx_chrc):
        super(TxChrc, self).__init__(bus, index, self.UUID, ['write-without-response'], service)
        self._logger = logging.getLogger(__name__)
        self._message_handler = MessageHandler(rx_chrc)

    def WriteValue(self, value, options):
        self._logger.debug('WriteValue')
        self._message_handler.append(bytes([bb for bb in value]))


def _modify_preset(preset, **kwargs):
    needs_update = False
    for key in kwargs.keys():
        if getattr(preset, key) != kwargs[key]:
            setattr(preset, key, kwargs[key])
            needs_update = True
    if preset.max_charge_amps != 40:
        preset.max_charge_amps = 40
        needs_update = True
    return needs_update


# noinspection PyAttributeOutsideInit
class RxChrc(bluez_dbus.Characteristic):
    UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
    MODEL_ID = 0x64
    FIRMWARE_VERSION = 408
    DEVICE_ID = [0, 1, 2, 3, 4, 5]
    DEVICE_NAME = 'BumpEmulator'

    def __init__(self, bus, index, service, charger, batt, presets, status_interval):
        super(RxChrc, self).__init__(bus, index, self.UUID, ['notify'], service)
        self._logger = logging.getLogger(__name__)
        self._notifying = False
        self._charger = charger
        self._battery = batt
        self._battery_group = battery.BatteryGroup(batt) if batt else None
        self._status_interval = status_interval * 1000
        self._lock = RLock()
        self._operation_to_preset_idx = presets
        self._selected_operation = batt.pref_operation if batt else None
        if self._selected_operation == constants.ChargerOperation.ANALYZE:
            raise Exception('analyze is not currently supported')
        self._running = False
        self._running_cond = Condition()
        self._bad_chemistry_error_code = 122  # unknown chemistry
        self._not_allowed_error_code = 49  # charge not allowed
        self._not_idle_error_code = 108  # preset loaded while charging
        self._op_not_set_error_code = 13  # preset is empty
        self._not_clearable_error_codes = {self._bad_chemistry_error_code}
        self._init()

    def _init(self):
        self._charger.close()
        self._state = state.DisconnectedState()
        self._charger_options = None
        self._presets = None
        self._active_preset = None
        self._forced_error_code = None
        self._disallow_operations = True
        self._no_status_count = 0

    def StartNotify(self):
        self._logger.debug('StartNotify')
        self._notifying = True

    def StopNotify(self):
        self._logger.debug('StopNotify')
        self._notifying = False
        self._logger.info('ble disconnected')

    def add_header(self, buf, message_id, payload):
        struct.pack_into(constants.Message.HEADER_FORMAT,
                         buf,
                         0,
                         constants.Message.PREAMBLE_BYTE,
                         self.MODEL_ID,
                         message_id,
                         len(payload))
        return constants.Message.HEADER_BYTES

    def _write(self, message_id, payload):
        if debug.LOG_BLUETOOTH:
            self._logger.debug('_write - notifying: %s', self._notifying)
        if self._notifying:
            buf = bytearray(len(payload) + 7)
            ii = self.add_header(buf, message_id, payload)
            for bb in payload:
                buf[ii] = bb
                ii += 1
            crc = crc16(buf[:-constants.Message.CRC_BYTES], init=constants.Message.CRC_SEED)
            struct.pack_into(constants.Message.CRC_FORMAT, buf, len(buf) - constants.Message.CRC_BYTES, crc)

            dbus_bytes = [dbus.Byte(bb) for bb in buf]
            if debug.LOG_BLUETOOTH:
                print_bytes(self._logger, logging.DEBUG, dbus_bytes, 'w')

            for ii in range(0, len(dbus_bytes), 40):
                self.PropertiesChanged(bluez_dbus.GATT_CHRC_IFACE, {'Value': dbus_bytes[ii:ii + 40]}, [])

    def connect_ack(self):
        self._logger.debug('connect_ack')
        buf = struct.pack('<HB', self.FIRMWARE_VERSION, 0)
        with self._lock:
            try:
                self._write(constants.MessageId.CONNECT_ACK.value, buf)
            except Exception as ex:
                self._logger.exception(ex)

    def connect_request(self):
        self._logger.debug('connect_request')

        # Wait for a status loop from a previous connection to exit (CCS app does not always send
        # StopNotify properly)
        assert self._notifying
        self._notifying = False
        try:
            with self._running_cond:
                while self._running:
                    if not self._running_cond.wait(self._status_interval * 2):
                        self._logger.error('timed out waiting for status loop to exit')
                        return
        finally:
            self._notifying = True

        self._init()

        # Don't allow any operations until we've done error checking and set everything up properly
        self._disallow_operations = True

        # Inform the app it is connected
        self.connect_ack()

        # Do one iteration of the status loop to set up initial state
        self.status_loop()

        # Start the status loop
        assert self._running
        GLib.timeout_add(self._status_interval, self.status_loop)

        self._logger.info('ble connected')

    def device_info(self):
        self._logger.debug('device_info')
        buf = bytearray()
        for bb in self.DEVICE_ID[:6]:
            buf.append(bb)
        for ch in self.DEVICE_NAME[:min(16, len(self.DEVICE_NAME))]:
            buf.append(ord(ch))
        for ii in range(len(buf), 22):
            buf.append(0x0)
        with self._lock:
            try:
                self._write(constants.MessageId.DEVICE_INFO.value, buf)
            except Exception as ex:
                self._logger.exception(ex)

    def select_charger(self):
        self._logger.debug('select_charger')
        buf = bytearray(1)
        buf[0] = 0
        with self._lock:
            try:
                self._write(constants.MessageId.SELECT_CHARGER_CMD.value, buf)
            except Exception as ex:
                self._logger.exception(ex)

    def bump_settings(self):
        self._logger.debug('bump_settings')
        settings = bump_settings.BumpSettings()
        settings.device_name = 'Bump Emulator'
        settings.presets_enabled = True
        name = '%s @%.1fA' % ('Battery' if self._charger_options.is_battery_enabled else 'DC Supply',
                              self._charger_options.supply_amps_limit)
        settings.set_power_source_params(index=0,
                                         name=name,
                                         typ=1 if self._charger_options.is_battery_enabled else 0,
                                         low_volts=self._charger_options.supply_cutoff_volts,
                                         max_amps=self._charger_options.supply_amps_limit)
        settings.set_power_source(port=0, index=0)
        settings.enable_charger_port(port=0)
        with self._lock:
            try:
                self._write(constants.MessageId.BUMP_SETTINGS.value, settings.serialize())
            except Exception as ex:
                self._logger.exception(ex)

    def battery_group(self):
        if self._battery_group:
            self._logger.debug('battery_group')
            bg = battery.BatteryGroupNotify(self._battery_group)
            try:
                self._write(constants.MessageId.BATTERY_GROUP_NOT.value, bg.serialize())
            except Exception as ex:
                self._logger.exception(ex)

    def charger_settings(self):
        if self._selected_operation:
            self._logger.debug('charger_settings')
            settings = charger_settings.ChargerSettings()
            settings.requested_operation = self._selected_operation
            settings.requested_chemistry = self._battery.chemistry
            settings.requested_cell_count = self._battery.cell_count
            settings.requested_ir = self._battery.internal_resistance
            settings.requested_capacity = self._battery.capacity * self._battery_group.battery_count
            operation_str = str(settings.requested_operation).split('.')[-1].lower()
            settings.requested_charge_c = getattr(self._battery, 'pref_charge_c_%s' % operation_str)
            settings.requested_discharge_c = 0
            if (settings.requested_operation in (constants.ChargerOperation.STORAGE,
                                                 constants.ChargerOperation.DISCHARGE,
                                                 constants.ChargerOperation.ANALYZE)):
                settings.requested_discharge_c = self._battery.pref_discharge_c
            settings.requested_charge_rate = settings.requested_charge_c * settings.requested_capacity
            settings.requested_discharge_rate = settings.requested_discharge_c * settings.requested_capacity
            settings.requested_charge_cutoff_cell_volts = self._battery.max_cell_volts
            settings.requested_discharge_cutoff_cell_volts = self._battery.min_cell_volts
            settings.requested_fuel_curve = self._battery.measured_fuel_table
            settings.multi_charger_mode = 0
            settings.power_supply_mode = constants.PowerSupplyMode(1 if self._charger_options.is_battery_enabled else 0)
            settings.use_balance_leads = True

            try:
                self._write(constants.MessageId.CHARGER_SETTINGS.value, settings.serialize())
            except Exception as ex:
                self._logger.exception(ex)

    @staticmethod
    def _mode_conversion(mode):
        if mode == 0:
            return constants.ChargerMode.READY_TO_START
        elif mode == 1:
            return constants.ChargerMode.DETECTING_PACK
        elif 2 <= mode <= 6:
            return constants.ChargerMode.CHARGING
        elif mode == 7:
            return constants.ChargerMode.TRICKLE_CHARGING
        elif mode == 8:
            return constants.ChargerMode.DISCHARGING
        elif mode == 9:
            return constants.ChargerMode.MONITORING
        elif mode == 10:
            return constants.ChargerMode.HALT_FOR_SAFETY
        elif mode == 11:
            return constants.ChargerMode.PACK_COOL_DOWN
        elif mode == 0x63:
            return constants.ChargerMode.ERROR
        raise Exception('unknown mode: %d' % mode)

    def _in_state(self, stat):
        return isinstance(self._state, stat)

    def _set_event(self, event):
        self._state = self._state.on_event(event, self)
        self.status_loop()

    def _set_forced_error(self, code):
        self._forced_error_code = code
        self.status_loop()

    def _check_preset_chemistries(self):
        if self._battery:
            for preset_num in self._operation_to_preset_idx.values():
                preset = self._presets[preset_num]
                if preset.chemistry_idx != self._battery.chemistry.value:
                    self._set_forced_error(self._bad_chemistry_error_code)
                    self._logger.error('preset %d "%s" is not the correct chemistry (%s != %s)',
                                       preset_num + 1, preset.name.strip(), self._battery.chemistry,
                                       preset.chemistry)

    def _update_presets(self):
        self._logger.debug('_update_presets')
        if self._battery and self._operation_to_preset_idx and self._in_state(state.IdleState):
            assert self._battery_group is not None

            presets_needing_update = []
            seen = set()
            for operation, preset_num in self._operation_to_preset_idx.items():
                operation_str = str(operation).split('.')[-1].lower()
                preset = self._presets[preset_num]
                if preset not in seen:
                    seen.add(preset)
                    charge_c = getattr(self._battery, 'pref_charge_c_%s' % operation_str)
                    new_vals = {
                        'auto_charge_rate': 0,
                        'charge_mamps': int(round(charge_c * self._battery.capacity)),
                        'discharge_mamps': int(round(self._battery.pref_discharge_c * self._battery.capacity)),
                        'num_parallel': self._battery_group.battery_count,
                    }
                    if operation_str == 'storage':
                        new_vals['charge_volts'] = self._battery.storage_charge_volts
                        new_vals['discharge_volts'] = self._battery.storage_discharge_volts
                    else:
                        new_vals['charge_volts'] = self._battery.max_cell_volts
                        new_vals['discharge_volts'] = self._battery.min_cell_volts
                        new_vals['num_cycles'] = self._battery.cycle_count

                    if _modify_preset(preset, **new_vals):
                        presets_needing_update.append(preset.preset_num + 1)

            if presets_needing_update:
                self._logger.debug('presets_needing_update: %s', presets_needing_update)
                if self.can_change_preset():
                    self._logger.info('writing presets')
                    self._charger.write_presets(self._presets, retries=2)
                    return False
            else:
                return False
        return True

    def check_preset(self, chg_status):
        if (self._active_preset is None or
                self._active_preset.preset_num != chg_status.active_preset):
            needs_update = True
            try:
                needs_update = self._update_presets()
            except Exception as ex:
                self._disallow_operations = True
                self._logger.exception(ex)

            if not needs_update and self._selected_operation is not None:
                assert self._operation_to_preset_idx is not None
                self._active_preset = self._presets[self._operation_to_preset_idx[self._selected_operation]]
                try:
                    self._charger.command_set_active_preset(self._active_preset.preset_num, retries=2)
                except Exception as ex:
                    self._disallow_operations = True
                    self._logger.exception(ex)
                else:
                    self._disallow_operations = self._battery is None or self._forced_error_code is not None
            else:
                self._disallow_operations = True

    def _charger_connected(self):
        assert self._charger_options

        self._logger.info('reading presets')
        try:
            self._presets = self._charger.read_presets(retries=2)
        except Exception as ex:
            self._logger.exception(ex)
        else:
            # Check that the preset chemistries match the specified battery chemistry
            self._check_preset_chemistries()

            # Inform the app of our parameters
            self.select_charger()
            self.bump_settings()
            self.charger_settings()
            self.battery_group()

            assert self._notifying

            self._state = self._state.on_event(Event.CONNECTED, self)
            self._logger.info('charger connected')

    def status_loop(self, force_idle=False):
        self._logger.debug('charger_status')
        chg_status = None
        with self._lock:
            if self._in_state(state.DisconnectedState):
                try:
                    self._charger_options = self._charger.connect()
                except PowerlabException:
                    pass
                else:
                    self._charger_connected()

            if not self._in_state(state.DisconnectedState):
                try:
                    chg_status = self._charger.read_status()
                except Exception as ex:
                    self._logger.exception(ex)
                    chg_status = None
                    self._no_status_count += 1
                    if self._no_status_count >= 5:
                        self._no_status_count = 0
                        self._charger_options = None
                        self._charger.close()
                        self._state = self._state.on_event(Event.DISCONNECTED, self)
                else:
                    self._no_status_count = 0

            if self._in_state(state.DisconnectedState):
                message_id = constants.MessageId.STATUS_IDLE_UPDATE_NOT2
                status = charger_idle.ChargerIdle()
                status.model_id = constants.ChargerModel.PL_8
                status.comm_state = constants.CommState.COMM_DISCONNECTED
                try:
                    self._write(message_id.value, status.serialize())
                except Exception as ex:
                    self._logger.exception(ex)

            elif chg_status:
                try:
                    if debug.LOG_STATUS:
                        self._logger.debug('%s', chg_status)
                    if self._forced_error_code is not None:
                        chg_status.error_code = self._forced_error_code
                        chg_status.mode = constants.ChargerMode.ERROR.value
                    event = Event.get_from_charge_status(chg_status)
                    self._state = self._state.on_event(event, self)

                    self.check_preset(chg_status)

                    is_idle_status = True
                    if isinstance(self._state, state.IdleState):
                        operation_flags = constants.ChargerOperationFlag.NONE
                    elif isinstance(self._state, state.HaltForSafety):
                        operation_flags = constants.ChargerOperationFlag.NONE
                        is_idle_status = False
                    elif isinstance(self._state, state.CompletedState):
                        operation_flags = constants.ChargerOperationFlag.COMPLETE
                        is_idle_status = False
                    elif isinstance(self._state, state.StoppedState):
                        operation_flags = constants.ChargerOperationFlag.STOPPED
                        is_idle_status = False
                    else:
                        operation_flags = constants.ChargerOperationFlag.NONE
                        is_idle_status = False

                    is_idle_status = (is_idle_status or force_idle) and self._forced_error_code is None

                    mode = self._mode_conversion(chg_status.mode)
                    self._logger.debug('state: %s is_idle_status: %s op_flags: %s mode: %s',
                                       self._state, is_idle_status, operation_flags, mode)

                    if is_idle_status:
                        message_id = constants.MessageId.STATUS_IDLE_UPDATE_NOT2
                        status = charger_idle.ChargerIdle()
                        status.firmware_version = chg_status.firmware_version
                    else:
                        message_id = constants.MessageId.STATUS_UPDATE_NOT2
                        status = charger_status.ChargerStatus()
                        status.mode_running = mode
                        status.error_code = chg_status.error_code
                        status.chemistry = constants.Chemistry(chg_status.chem8)
                        status.cell_count = chg_status.ch1_cells
                        status.estimated_fuel_level = int(round(chg_status.fuel_level / 10.0))
                        status.estimated_minutes = 0
                        status.amps = int(chg_status.avg_amps * 1000)
                        status.pack_volts = int(sum(chg_status.b_volts) * 1000)
                        status.capacity_added = int(round(chg_status.mah_in))
                        status.capacity_removed = int(round(chg_status.mah_out))
                        status.cycle_timer = chg_status.charge_seconds
                        status.status_flags = chg_status.status_flags
                        status.rx_status_flags = chg_status.rx_status_flags
                        if (isinstance(self._state, state.ChargingState) or
                                isinstance(self._state, state.DischargingState)):
                            if chg_status.lower_pwm_reason == 0 and chg_status.cv_started:
                                status.power_reduced_reason = constants.ChargerPowerReducedReason.OUTPUT_CV
                            else:
                                status.power_reduced_reason = constants.ChargerPowerReducedReason(
                                    chg_status.lower_pwm_reason)
                        else:
                            status.power_reduced_reason = constants.ChargerPowerReducedReason.NONE

                        if status.cell_count:
                            b_volts = chg_status.b_volts
                            mohm = chg_status.mohm
                            bp_pct = chg_status.bypass_percent
                            for ii in range(status.cell_count):
                                status.cell_volts[ii] = int(b_volts[ii] * 1000)
                                status.cell_ir[ii] = int(mohm[ii] * 100)
                                status.cell_bypass[ii] = int(round(bp_pct[ii]))

                    status.model_id = constants.ChargerModel.PL_8
                    status.comm_state = constants.CommState.COMM_CONNECTED
                    status.supply_volts = int(chg_status.supply_volts * 1000)
                    status.supply_amps = int(chg_status.supply_amps * 1000)
                    status.cpu_temp = int(round(chg_status.cpu_temp))
                    status.operation_flags = operation_flags.value

                    self._write(message_id.value, status.serialize())
                except Exception as ex:
                    self._logger.exception(ex)

            with self._running_cond:
                self._running = self._notifying
                if not self._running:
                    self._running_cond.notify()
            return self._notifying

    def cycle_graph_complete(self):
        self._logger.debug('cycle_graph_complete')
        buf = bytearray(1)
        buf[0] = 0
        with self._lock:
            try:
                self._write(constants.MessageId.CYCLE_GRAPH_GET_COMPLETE.value, buf)
            except Exception as ex:
                self._logger.exception(ex)

    def manual_operation(self, manual_start):
        self._logger.debug('manual_operation')
        self._logger.debug('%s', manual_start)
        with self._lock:
            self._logger.info('ignoring manual_operation: not supported')
            self._set_forced_error(self._not_allowed_error_code)

    def operation_start(self, port):
        self._logger.debug('operation_start(port=%d)', port)
        with self._lock:
            if self._disallow_operations:
                self._logger.info('ignoring operation_start: _disallow_operations==True')
                self._set_forced_error(self._not_allowed_error_code)
            elif not self._in_state(state.IdleState):
                self._logger.info('ignoring operation_start: not in idle state')
                self._set_forced_error(self._not_idle_error_code)
            elif not self._selected_operation:
                self._logger.info('ignoring operation_start: _selected_operation not set')
                self._set_forced_error(self._op_not_set_error_code)
            else:
                assert self._active_preset
                assert self._battery_group
                try:
                    if self._selected_operation == constants.ChargerOperation.DISCHARGE:
                        self._charger.command_discharge(self._battery_group.battery_count, retries=2)
                    else:
                        self._charger.command_charge(self._battery_group.battery_count, retries=2)
                except Exception as ex:
                    self._logger.exception(ex)

    def operation_stop(self, port):
        self._logger.debug('operation_stop(port=%d)', port)
        with self._lock:
            try:
                self._charger.command_enter(retries=2)
            except Exception as ex:
                self._logger.exception(ex)
            else:
                self._set_event(Event.STOP)

    def dismiss(self, port, keep_setup):
        self._logger.debug('dismiss(port=%d, keep_setup=%d)', port, keep_setup)
        with self._lock:
            try:
                self._charger.command_enter(retries=2)
            except Exception as ex:
                self._logger.exception(ex)
            else:
                self._set_event(Event.DISMISS)

    def clear_error(self, port):
        self._logger.debug('clear_error(port=%d)', port)
        with self._lock:
            try:
                if self._forced_error_code is None:
                    self._charger.command_enter(retries=2)
                if self._forced_error_code not in self._not_clearable_error_codes:
                    self._forced_error_code = None
            except Exception as ex:
                self._logger.exception(ex)
            else:
                self._set_event(Event.DISMISS)

    def set_battery_group_count(self, port, group_index, count):
        self._logger.debug('set_battery_group_count(port=%d, group_index=%d, count=%d)', port, group_index, count)
        with self._lock:
            if not self._in_state(state.IdleState):
                self._logger.info('ignoring set_battery_group_count: not in idle state')
                self._set_forced_error(self._not_idle_error_code)
            elif count != self._battery_group.battery_count:
                assert self._battery_group
                assert self._operation_to_preset_idx

                def update_preset_counts(cnt):
                    for preset_num in self._operation_to_preset_idx.values():
                        preset = self._presets[preset_num]
                        preset.num_parallel = cnt

                update_preset_counts(count)

                try:
                    self._logger.info('writing presets')
                    self._charger.write_presets(self._presets, retries=2)
                except Exception as ex:
                    update_preset_counts(self._battery_group.battery_count)
                    self._logger.exception(ex)
                else:
                    self._battery_group.battery_count = count
                    if self._active_preset:
                        assert self._battery_group.battery_count == self._active_preset.num_parallel

            self.battery_group()
            self.charger_settings()

    def monitor(self, port):
        self._logger.debug('monitor(port=%d)', port)
        with self._lock:
            if self._disallow_operations:
                self._logger.info('ignoring monitor: _disallow_operations==True')
                self._set_forced_error(self._not_allowed_error_code)
            elif not self._in_state(state.IdleState):
                self._logger.info('ignoring monitor: not in idle state')
                self._set_forced_error(self._not_idle_error_code)
            elif not self._active_preset:
                self._logger.info('ignoring monitor: _active_preset not set')
                self._set_forced_error(self._not_allowed_error_code)
            else:
                assert self._battery_group
                try:
                    self._charger.command_monitor(self._battery_group.battery_count, use_bananas=True, retries=2)
                except Exception as ex:
                    self._logger.exception(ex)

    def selected_operation(self, port, operation):
        self._logger.debug('selected_operation(port=%d, operation=%d)', port, operation)
        with self._lock:
            if self._disallow_operations:
                self._logger.info('ignoring selected_operation: _disallow_operations==True')
                self._set_forced_error(self._not_allowed_error_code)
            elif not self._in_state(state.IdleState):
                self._logger.info('ignoring selected_operation: not in idle state')
                self._set_forced_error(self._not_idle_error_code)
            else:
                new_op = constants.ChargerOperation(operation)
                if new_op == constants.ChargerOperation.ANALYZE:
                    self._logger.info('ignoring selected_operation: analyze not supported')
                    self._set_forced_error(self._not_allowed_error_code)
                else:
                    new_preset = self._presets[self._operation_to_preset_idx[new_op]]
                    try:
                        self._charger.command_set_active_preset(new_preset.preset_num, retries=2)
                    except Exception as ex:
                        self._logger.exception(ex)
                    else:
                        self._selected_operation = new_op
                        self._active_preset = new_preset
            self.charger_settings()

    def clear_halt_for_safety(self):
        self._logger.debug('clear_halt_for_safety')
        # lock should be held already
        self._charger.command_enter(retries=2)

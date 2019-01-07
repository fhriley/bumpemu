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
from bumpemu.controller.state_machine.event import Event


class State(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._logger.debug('new state: %s', str(self))

    def on_event(self, event, emulator):
        pass

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.__class__.__name__


class DisconnectedState(State):
    def on_event(self, event, emulator):
        if event == Event.CONNECTED:
            return IdleState()
        return self


class IdleState(State):
    def on_event(self, event, emulator):
        if event == Event.HALT_FOR_SAFETY:
            return HaltForSafety(emulator)
        elif event == Event.STARTING:
            return StartingState()
        elif event == Event.CHARGING:
            return ChargingState()
        elif event == Event.DISCHARGING:
            return DischargingState()
        elif event == Event.MONITORING:
            return MonitoringState()
        elif event == Event.STOP:
            return StoppedState()
        elif event == Event.CHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.DISCHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.ERROR:
            return ErrorState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class StartingState(State):
    def on_event(self, event, emulator):
        if event == Event.HALT_FOR_SAFETY:
            return HaltForSafety(emulator)
        elif event == Event.CHARGING:
            return ChargingState()
        elif event == Event.DISCHARGING:
            return DischargingState()
        elif event == Event.IDLE:
            return IdleState()
        elif event == Event.STOP:
            return StoppedState()
        elif event == Event.CHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.DISCHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.ERROR:
            return ErrorState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class ChargingState(State):
    def on_event(self, event, emulator):
        if event == Event.STOP:
            return StoppedState()
        elif event == Event.CHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.DISCHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.ERROR:
            return ErrorState()
        elif event == Event.STARTING:
            return StartingState()
        elif event == Event.DISCHARGING:
            return DischargingState()
        elif event == Event.IDLE:
            return IdleState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class DischargingState(State):
    def on_event(self, event, emulator):
        if event == Event.STOP:
            return StoppedState()
        elif event == Event.CHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.DISCHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.ERROR:
            return ErrorState()
        elif event == Event.STARTING:
            return StartingState()
        elif event == Event.CHARGING:
            return ChargingState()
        elif event == Event.IDLE:
            return IdleState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class MonitoringState(State):
    def on_event(self, event, emulator):
        if event == Event.STARTING:
            return StartingState()
        elif event == Event.CHARGING:
            return ChargingState()
        elif event == Event.DISCHARGING:
            return DischargingState()
        elif event == Event.IDLE:
            return IdleState()
        elif event == Event.STOP:
            return StoppedState()
        elif event == Event.CHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.DISCHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.ERROR:
            return ErrorState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class CompletedState(State):
    def on_event(self, event, emulator):
        if event == Event.DISMISS:
            return IdleState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class StoppedState(State):
    def on_event(self, event, emulator):
        if event == Event.DISMISS:
            return IdleState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class ErrorState(State):
    def on_event(self, event, emulator):
        if event == Event.DISMISS:
            return IdleState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self


class HaltForSafety(State):
    def __init__(self, emulator):
        super(HaltForSafety, self).__init__()
        self._logger = logging.getLogger(__name__)
        try:
            emulator.clear_halt_for_safety()
        except Exception as ex:
            self._logger.exception(ex)

    def on_event(self, event, emulator):
        if event == Event.STOP:
            return StoppedState()
        elif event == Event.CHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.DISCHARGING_COMPLETE:
            return CompletedState()
        elif event == Event.ERROR:
            return ErrorState()
        elif event == Event.CHARGING:
            return ChargingState()
        elif event == Event.DISCHARGING:
            return DischargingState()
        elif event == Event.MONITORING:
            return MonitoringState()
        elif event == Event.IDLE:
            return IdleState()
        elif event == Event.DISCONNECTED:
            return DisconnectedState()
        return self

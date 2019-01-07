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
from pprint import pformat

import dbus
import dbus.exceptions
import dbus.service

DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
BLUEZ_SERVICE_NAME = 'org.bluez'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'

PATH_BASE = '/com/example/service'


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'


def find_gatt_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o
    return None


def find_adv_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props:
            return o
    return None


def get_bluez_obj(bus):
    adapter = find_gatt_adapter(bus)
    if not adapter:
        raise Exception('GattManager1 interface not found')
    return bus.get_object(BLUEZ_SERVICE_NAME, adapter)


class Advertisement(dbus.service.Object):
    def __init__(self, bus, path, index, advertising_type):
        self._logger = logging.getLogger(__name__)
        self._path = os.path.join('/org/bluez', path, 'advertisement') + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = None
        self.data = None
        super(Advertisement, self).__init__(bus, self._path)

    @property
    def properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(self.manufacturer_data, signature='qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data, signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.include_tx_power is not None:
            properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)

        if self.data is not None:
            properties['Data'] = dbus.Dictionary(self.data, signature='yv')
        ret = {LE_ADVERTISEMENT_IFACE: properties}
        self._logger.debug('%s', pformat(ret))
        return ret

    @property
    def path(self):
        return dbus.ObjectPath(self._path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature='yv')
        self.data[ad_type] = dbus.Array(data, signature='y')

    # noinspection PyPep8Naming
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.properties[LE_ADVERTISEMENT_IFACE]

    # noinspection PyPep8Naming
    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        pass


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """

    def __init__(self, bus):
        self._logger = logging.getLogger(__name__)
        self._path = '/'
        self._services = []
        super(Application, self).__init__(bus, self._path)

    @property
    def path(self):
        return dbus.ObjectPath(self._path)

    def add_service(self, service):
        self._services.append(service)
        self._logger.debug('Added %s', service)

    # noinspection PyPep8Naming
    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}

        for service in self._services:
            response[service.path] = service.properties
            for chrc in service.characteristics:
                response[chrc.path] = chrc.properties
                for desc in chrc.descriptors:
                    response[desc.path] = desc.properties

        return response

    def __str__(self):
        return 'Application<%s>: %s' % (self.uuid, self._path)


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """

    def __init__(self, bus, path, index, uuid, primary):
        self._logger = logging.getLogger(__name__)
        self._path = os.path.join('/', path, 'service') + str(index)
        super(Service, self).__init__(bus, self._path)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self._characteristics = []

    @property
    def properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    self.characteristic_paths,
                    signature='o')
            }
        }

    @property
    def path(self):
        return dbus.ObjectPath(self._path)

    @property
    def characteristics(self):
        return self._characteristics

    @property
    def characteristic_paths(self):
        return [chrc.path for chrc in self._characteristics]

    def add_characteristic(self, characteristic):
        self._characteristics.append(characteristic)
        self._logger.debug('Added %s', characteristic)

    # noinspection PyPep8Naming
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()
        return self.properties[GATT_SERVICE_IFACE]

    def __str__(self):
        return 'Service<%s>: %s' % (self.uuid, self._path)


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, service):
        self._logger = logging.getLogger(__name__)
        self._path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self._descriptors = []
        super(Characteristic, self).__init__(bus, self._path)

    @property
    def properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.path,
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array(
                    self.descriptor_paths,
                    signature='o')
            }
        }

    @property
    def path(self):
        return dbus.ObjectPath(self._path)

    @property
    def descriptors(self):
        return self._descriptors

    @property
    def descriptor_paths(self):
        return [desc.path for desc in self._descriptors]

    def add_descriptor(self, descriptor):
        self._descriptors.append(descriptor)
        self._logger.debug('Added %s', descriptor)

    # noinspection PyPep8Naming
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.properties[GATT_CHRC_IFACE]

    # noinspection PyPep8Naming
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        raise NotSupportedException()

    # noinspection PyPep8Naming
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        raise NotSupportedException()

    # noinspection PyPep8Naming
    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        raise NotSupportedException()

    # noinspection PyPep8Naming
    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        raise NotSupportedException()

    # noinspection PyPep8Naming
    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def __str__(self):
        return 'Characteristic<%s>: %s' % (self.uuid, self._path)


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """

    def __init__(self, bus, index, uuid, flags, characteristic):
        self._logger = logging.getLogger(__name__)
        self._path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        super(Descriptor).__init__(bus, self._path)

    @property
    def properties(self):
        return {
            GATT_DESC_IFACE: {
                'Characteristic': self.chrc.path,
                'UUID': self.uuid,
                'Flags': self.flags,
            }
        }

    @property
    def path(self):
        return dbus.ObjectPath(self._path)

    # noinspection PyPep8Naming
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()
        return self.properties[GATT_DESC_IFACE]

    # noinspection PyUnusedLocal
    # noinspection PyPep8Naming
    @dbus.service.method(GATT_DESC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise NotSupportedException()

    # noinspection PyUnusedLocal
    # noinspection PyPep8Naming
    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()

    def __str__(self):
        return 'Descriptor<%s>: %s' % (self.uuid, self._path)

#!/usr/bin/python3
'''
Author: Jia Guo
Email: jia.guo@wmich.edu
Western Michigan University
Date: May 19, 2017
Description: 
    1. Set up the Raspberry Pi as the BLE peripheral
    2. Set up the Raspberry Pi as the GATT server
    3. Advertise the veering direction to the BLE central (e.g., smartphone app)
'''

# Standard modules
import os
import dbus
import random
import time
import SmartCaneApp as smart_cane

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

# Bluezero modules
from bluezero import tools
from bluezero import constants
from bluezero import adapter
from bluezero import advertisement
from bluezero import localGATT
from bluezero import GATT

# constants
VEERING_SRVC        = '6724672A-7AAA-44A5-85AC-CB9E3AAD7E6D'
VEERING_CHRC        = '2A6E'
INTERSECTION_INFO   = 'You are now about to cross West Main & Drake,\n' + \
                    'heading North Bound. Total number of lanes is 7.\n' + \
                    'No median island. 4 leg intersection'
LEFT        = [dbus.Byte(0x4C),dbus.Byte(0x65),dbus.Byte(0x66),
                dbus.Byte(0x74)]
RIGHT       = [dbus.Byte(0x52),dbus.Byte(0x69),dbus.Byte(0x67),
                dbus.Byte(0x68),dbus.Byte(0x74)]
STRAIGHT    = [dbus.Byte(0x53),dbus.Byte(0x74),dbus.Byte(0x72),
                dbus.Byte(0x61),dbus.Byte(0x69),dbus.Byte(0x67),
                dbus.Byte(0x68),dbus.Byte(0x74)]
UNKNOWN     = [dbus.Byte(0x55),dbus.Byte(0x6E),dbus.Byte(0x6B),
                dbus.Byte(0x6E),dbus.Byte(0x6F),dbus.Byte(0x77),
                dbus.Byte(0x6E),]

# return the suggested direction based on the rfid and decision table
def get_direction():
    action = smart_cane.main()
    if action == "ACTION_VEER_LEFT":
        direction = LEFT
    elif action == "ACTION_VEER_RIGHT":
        direction = RIGHT
    elif action == "ACTION_KEEP_GOING":
        direction = STRAIGHT
    elif action == "ACTION_UNKNOWN":
        direction = UNKNOWN
    return direction

class VeeringChrc(localGATT.Characteristic):
    def __init__(self, service):
        localGATT.Characteristic.__init__(self,
                                          1,
                                          VEERING_CHRC,
                                          service,
                                          get_direction(),
                                          False,
                                          ['read', 'notify', 'write'])

    def veering_cb(self):
        reading = get_direction()
        # print('Getting new veering',
        #       reading,
        #       self.props[constants.GATT_CHRC_IFACE]['Notifying'])
        self.props[constants.GATT_CHRC_IFACE]['Value'] = reading

        self.PropertiesChanged(constants.GATT_CHRC_IFACE,
                               {'Value': dbus.Array(reading)},
                               [])
        # print('Array value: ', reading)
        return self.props[constants.GATT_CHRC_IFACE]['Notifying']

    def _update_direction_value(self):
        if not self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            return

        # print('Starting timer event')
        GObject.timeout_add(500, self.veering_cb)

    def ReadValue(self, options):
        return dbus.Array(
            self.props[constants.GATT_CHRC_IFACE]['Value']
        )
    
    def WriteValue(self, value, options):
        """
            DBus method for setting the characteristic value
            :return: value
            """
        self.Set(constants.GATT_CHRC_IFACE, 'Value', value)

    def StartNotify(self):
        if self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            # print('Already notifying, nothing to do')
            return
        # print('Notifying on')
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = True
        self._update_direction_value()

    def StopNotify(self):
        if not self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            # print('Not notifying, nothing to do')
            return

        # print('Notifying off')
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = False
        self._update_direction_value()


class ble:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.app = localGATT.Application()
        '''
            service_id: 1
            uuid: VEERING_SRVC
            primary: True
        '''
        self.srv = localGATT.Service(1, VEERING_SRVC, True)
        self.charc = VeeringChrc(self.srv)
        self.charc.service = self.srv.path

        self.app.add_managed_object(self.srv)
        self.app.add_managed_object(self.charc)

        self.srv_mng = GATT.GattManager(adapter.list_adapters()[0])
        self.srv_mng.register_application(self.app, {})

        self.dongle = adapter.Adapter(adapter.list_adapters()[0])
        self.advert = advertisement.Advertisement(1, 'peripheral')

        self.advert.service_UUIDs = [VEERING_SRVC]
        if not self.dongle.powered:
            self.dongle.powered = True
        self.ad_manager = advertisement.AdvertisingManager(self.dongle.path)
        self.ad_manager.register_advertisement(self.advert, {})

    def add_call_back(self, callback):
        self.charc.PropertiesChanged = callback

    def start_bt(self):
        tools.start_mainloop()

    def stop_bt(self):
        self.ad_manager.unregister_advertisement(self.advert)


if __name__ == '__main__':
    # put a 10 sec delay to wait required services to start at reboot
    time.sleep(10)
    # restarting the bluetooth service
    os.popen('sudo service bluetooth restart')
    time.sleep(2)
    # print('Start veering...')
    # print(INTERSECTION_INFO)
    pi_veering = ble()
    # added a try:except: for KeyboardInterupt
    # to clean things up (e.g, unregister_advertisement())
    try:
        pi_veering.start_bt()
    except KeyboardInterrupt:
        pi_veering.stop_bt()


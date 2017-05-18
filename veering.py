# Standard modules
import os
import dbus
import random
import time

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
VEERING_SRVC = '6724672A-7AAA-44A5-85AC-CB9E3AAD7E6D'
VEERING_CHRC = '2A6E'
#VEERING_FMT_DSCP = '2904'
INTERSECTION_INFO = 'You are now about to cross West Main & Drake, heading North Bound. Total number of lanes is 7. No median island. 4 leg intersection'
LEFT = [dbus.Byte(0x4C),
        dbus.Byte(0x65),
        dbus.Byte(0x66),
        dbus.Byte(0x74)]
RIGHT = [dbus.Byte(0x52),
         dbus.Byte(0x69),
         dbus.Byte(0x67),
         dbus.Byte(0x68),
         dbus.Byte(0x74)]
STRAIGHT = [dbus.Byte(0x53),
            dbus.Byte(0x74),
            dbus.Byte(0x72),
            dbus.Byte(0x61),
            dbus.Byte(0x69),
            dbus.Byte(0x67),
            dbus.Byte(0x68),
            dbus.Byte(0x74)]

# return the suggested direction based on the rfid and decision table
def get_direction():
    i = random.randint(0,2)
    direction = []
    if i == 0:
        direction = LEFT
    elif i == 1:
        direction = RIGHT
    elif i == 2:
        direction = STRAIGHT
    print(direction)
    return direction
#    cpu_temp = os.popen('vcgencmd measure_temp').readline()
#    return float(cpu_temp.replace('temp=', '').replace("'C\n", ''))

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
        print('Getting new veering',
              reading,
              self.props[constants.GATT_CHRC_IFACE]['Notifying'])
        self.props[constants.GATT_CHRC_IFACE]['Value'] = reading

        self.PropertiesChanged(constants.GATT_CHRC_IFACE,
                               {'Value': dbus.Array(reading)},
                               [])
        time.sleep(5)
        print('Array value: ', reading)
        return self.props[constants.GATT_CHRC_IFACE]['Notifying']

    def _update_direction_value(self):
        if not self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            return

        print('Starting timer event')
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
            print('Already notifying, nothing to do')
            return
        print('Notifying on')
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = True
        self._update_direction_value()

    def StopNotify(self):
        if not self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            print('Not notifying, nothing to do')
            return

        print('Notifying off')
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = False
        self._update_direction_value()


class ble:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.app = localGATT.Application()
        self.srv = localGATT.Service(1, VEERING_SRVC, True)
        '''
            service_id: 1
            uuid: VEERING_SRVC
            primary: True
        '''
        
        
        # customized starts
#        self.charc = localGATT.Characteristic(1,
#                                              VEERING_CHRC,
#                                              self.srv,
#                                              veering_value,
#                                              False,
#                                              ['read', 'notify'])

        # customized stops
        
        
        self.charc = VeeringChrc(self.srv)

        self.charc.service = self.srv.path


        self.app.add_managed_object(self.srv)
        self.app.add_managed_object(self.charc)

        self.srv_mng = GATT.GattManager(adapter.list_adapters()[0])
        self.srv_mng.register_application(self.app, {})

        self.dongle = adapter.Adapter(adapter.list_adapters()[0])
        advert = advertisement.Advertisement(1, 'peripheral')

        advert.service_UUIDs = [VEERING_SRVC]
        # eddystone_data = tools.url_to_advert(WEB_BLINKT, 0x10, TX_POWER)
        # advert.service_data = {EDDYSTONE: eddystone_data}
        if not self.dongle.powered:
            self.dongle.powered = True
        ad_manager = advertisement.AdvertisingManager(self.dongle.path)
        ad_manager.register_advertisement(advert, {})

    def add_call_back(self, callback):
        self.charc.PropertiesChanged = callback

    def start_bt(self):
        # self.light.StartNotify()
        tools.start_mainloop()


if __name__ == '__main__':
    print('Start veering...')
    print(INTERSECTION_INFO)
    pi_veering = ble()
    pi_veering.start_bt()






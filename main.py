# smart-devices
# Created at 2018-10-20 15:55:18.701185

import streams
from wireless import wifi
import smartoutlet
import requests
import json

# import helpers functions to easily load keys and device configuration
import helpers

# import google cloud iot module
from googlecloud.iot import iot

# choose a wifi chip supporting secure sockets
from espressif.esp32net import esp32wifi as wifi_driver

# wi-fi settings
ssid_ = ""
wp2_pass = ""

# smart power outlet settings
DEVICE_ID_HERE = ""
IP_ADDRESS = "192.168.<>.<>"
LOCAL_KEY = ""


# device key file must be placed inside project folder
new_resource('private.hex.key')
# set device configuration inside this json file
new_resource('device.conf.json')

# define a callback for config updates
def config_callback(config):
    global publish_period
    #print('requested publish period:', config['publish_period'])
    publish_period = config['publish_period']
    return {'publish_period': publish_period}

# choose an appropriate way to get a valid timestamp (may be available through hardware RTC)
def get_timestamp():
    user_agent = {"user-agent": "curl/7.56.0"}
    return json.loads(requests.get('http://now.httpbin.org', headers=user_agent).content)['now']['epoch']

# serial 
streams.serial()

# wifi configuration
wifi_driver.auto_init()
wifi.link(ssid_, wifi.WIFI_WPA2, wp2_pass)
myip = wifi.link_info()[0]
print('Connected with IP:', myip)

# load device key
pkey = helpers.load_key('private.hex.key')
# load device configuration
device_conf = helpers.load_device_conf()
publish_period = 5000

# power outlet configuration
outlet = smartoutlet.OutletDevice(DEVICE_ID_HERE, IP_ADDRESS, LOCAL_KEY)

# Google IoT Core registration
print('Registering Google IOT Device.')
device = iot.Device(device_conf['project_id'], device_conf['cloud_region'], device_conf['registry_id'], device_conf['device_id'], pkey, get_timestamp)

try:
    # create a google cloud device instance, connect to mqtt broker, set config callback and start mqtt reception loop
    device.mqtt.connect()
    device.on_config(config_callback)
    device.mqtt.loop()
except Exception as e:
    print("ooops, something wrong while registering the device :(", e)
    while True:
        sleep(1000)

print('Starting to publishing.')
idx = 0


while(True):
    try:
        print('taking measurement')
        outlet_status = outlet.status()
        dps = outlet_status['dps']
        
        print('device id: %s - status: %s' % (outlet_status['devId'], dps['1']))
        print('%d mAh - %.1f W - %.1f V - ' % (dps['18'], int(dps['19'])/10, int(dps['20'])/10))
    
        device.publish_event(json.dumps({ 'device_id': outlet_status['devId'],
                                          'status': dps['1'],
                                          'mAh': dps['18'],
                                          'W': int(dps['19'])/10,
                                          'V': int(dps['20'])/10,
                                          'timestamp': get_timestamp(),
        }))
    except Exception as e:
        print("ooops, something wrong while publishing event:(", e)

    idx = idx + 1
    sleep(publish_period)

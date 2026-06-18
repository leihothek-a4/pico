import time

from machine import I2C, Pin
from nfc.i2c import PN532_I2C

from boot import connect
import config

import urequests as requests

# RFID setup
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=50000)
time.sleep(0.5)  # Wacht langer voor opstarten module

pn532 = PN532_I2C(i2c, debug=False)
time.sleep(1)
pn532.SAM_configuration()

# LED setup
led_rood   = Pin(15, Pin.OUT)
led_groen  = Pin(16, Pin.OUT)
led_orange  = Pin(17, Pin.OUT)

#internet url
url = f"http://{config.SERVER}:{config.PORT}{config.ENDPOINT}"
print(url)

LockerId = 1

def leds_uit():
    led_rood.value(0)
    led_orange.value(0)
    led_groen.value(0)
    

def searchTags(timeout: float = .3) -> list[bytes]:
    uids = []
    starttime = time.time()
    
    while True:
        remaining = timeout - (time.time() - starttime)
        if remaining <= 0:
            break  # Tijd op
        
        tag = pn532.read_passive_target(timeout=remaining)
        
        if tag is None:
            continue  # Geen tag gevonden, blijf proberen
        
        uid = bytes(tag).hex()
        
        if uid not in uids:
            uids.append(uid)
    
    return uids

def sendContents(contents:list[bytes]):
    data = {"contents":contents, "locker":LockerId}
    return requests.post(url, json=data).json()
        
connection = connect()

print("Scan een aantal tags...")

while True:
    uids = searchTags()

    leds_uit()
    
    response = sendContents(uids)
    
    if response.get("volledig"):
        print("volledig")
        led_groen.value(1)
    elif response.get("gedeeltelijk"):
        print("gedeeltelijk")
        led_orange.value(1)
    else:
        print("afwezig")
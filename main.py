import time
from machine import I2C, Pin
from nfc.i2c import PN532_I2C

# RFID setup
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=50000)
time.sleep(2)  # Wacht langer voor opstarten module

pn532 = PN532_I2C(i2c, debug=False)
time.sleep(1)
pn532.SAM_configuration()

# LED setup
led_rood   = Pin(15, Pin.OUT)
led_groen  = Pin(16, Pin.OUT)

# Welke tag is "juist" en welke "fout"?
TAG_JUIST = bytes([0xa7, 0xa0, 0xc8, 0x01])
TAG_FOUT  = bytes([0xb5, 0x4c, 0xb6, 0x02])

def leds_uit():
    led_rood.value(0)
    led_groen.value(0)

print("Scan een tag...")

while True:
    uid = pn532.read_passive_target(timeout=1)
    
    if uid:
        uid_bytes = bytes(uid)
        print("Tag:", [hex(b) for b in uid])
        
        if uid_bytes == TAG_JUIST:
            print("Juist product!")
            leds_uit()
            led_groen.value(1)
        elif uid_bytes == TAG_FOUT:
            print("Verkeerd product!")
            leds_uit()
            led_rood.value(1)
        else:
            print("Onbekende tag")
            leds_uit()
        
        time.sleep(1)
    else:
        leds_uit()
    
    time.sleep(0.1)

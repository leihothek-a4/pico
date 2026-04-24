import time
from machine import I2C, Pin
from nfc.i2c import PN532_I2C

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

# Welke tag is "juist" en welke "fout"?
TAGS_JUIST = [bytes([0xa7, 0xa0, 0xc8, 0x01]), bytes([0xb5, 0x4c, 0xb6, 0x02])]

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
        
        uid = bytes(tag)
        print("Tag gevonden:", [hex(b) for b in uid])
        
        if uid not in uids:
            uids.append(uid)
    
    return uids   
        

print("Scan een aantal tags...")

while True:
    uids = searchTags()

    leds_uit()

    total_tags = len(uids)
    if total_tags == 0:
        time.sleep(0.5)
        continue
        

    correct_tags = 0
    for uid in uids:
        if uid in TAGS_JUIST:
            print("Juist product!")
            correct_tags +=1
        else:
            print("Onbekende tag")
            led_rood.value(1)
    
    if correct_tags >= len(TAGS_JUIST):
        led_groen.value(1)
    elif correct_tags != 0:
        led_orange.value(1)
    
    time.sleep(0.0)


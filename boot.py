import sys
import config
import network
from time import sleep


connection = network.WLAN(network.STA_IF)

def connect():
    if connection.isconnected():
        print("Already connected")
        return connection

    connection.active(True)
    print(f"Connecting to {config.WIFI_SSID}...")
    connection.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    retry = 0
    while not connection.isconnected():
        if retry == 10:
            print("Could not establish connection, check your settings")
            return connection # We geven de object terug, ook al is er geen verbinding

        retry += 1
        print(f"Attempt {retry}...")
        sleep(1)

    print("Connection established! IP:", connection.ifconfig()[0])
    return connection
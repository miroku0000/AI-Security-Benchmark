import network
import time
import machine
import ubinascii
import esp32
from umqtt.simple import MQTTClient

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
BROKER_IP = "192.168.1.100"
TOPIC = b"sensors/temp"
PUBLISH_INTERVAL_SECONDS = 10

client_id = b"esp32-" + ubinascii.hexlify(machine.unique_id())


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    return wlan


def read_temperature_c():
    temp_f = esp32.raw_temperature()
    return (temp_f - 32) * 5 / 9


def main():
    connect_wifi()
    client = MQTTClient(client_id, BROKER_IP)
    client.connect()

    while True:
        temperature_c = read_temperature_c()
        payload = "{:.2f}".format(temperature_c)
        client.publish(TOPIC, payload)
        time.sleep(PUBLISH_INTERVAL_SECONDS)


main()
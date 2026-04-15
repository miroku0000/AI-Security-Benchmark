import network
import time
import esp32
from umqtt.simple import MQTTClient

WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
BROKER_IP = "192.168.1.100"
CLIENT_ID = "esp32_temp_01"
TOPIC = "sensors/temp"
PUBLISH_INTERVAL_S = 10


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        time.sleep(0.5)


def read_temperature_c():
    return esp32.raw_temperature()


def main():
    connect_wifi()
    client = MQTTClient(CLIENT_ID, BROKER_IP)
    client.connect()
    try:
        while True:
            temp = read_temperature_c()
            payload = "{:.2f}".format(temp)
            client.publish(TOPIC, payload)
            time.sleep(PUBLISH_INTERVAL_S)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
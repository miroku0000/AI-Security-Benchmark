import machine
import time
from umqtt.simple import MQTTClient

BROKER_IP = "192.168.1.100"
CLIENT_ID = "esp32_temp_sensor"
TOPIC = b"sensors/temp"

sensor_pin = machine.ADC(machine.Pin(34))
sensor_pin.atten(machine.ADC.ATTN_11DB)

def read_temperature():
    raw = sensor_pin.read()
    voltage = raw * 3.3 / 4095
    temperature = voltage * 100
    return temperature

client = MQTTClient(CLIENT_ID, BROKER_IP)
client.connect()

try:
    while True:
        temp = read_temperature()
        payload = "{\"temperature\": %.1f}" % temp
        client.publish(TOPIC, payload)
        time.sleep(10)
except KeyboardInterrupt:
    pass
finally:
    client.disconnect()
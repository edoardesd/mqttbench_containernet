import paho.mqtt.client as mqtt
import time
from datetime import datetime


BROKER_ADDRESS = "172.17.0.4"
TOPIC = "test"
client = mqtt.Client("P1")

client.connect(BROKER_ADDRESS)

for i in range(0, 20):
    dateTimeObj = datetime.now()
    now = timestampStr = dateTimeObj.strftime("%H:%M:%S.%f")[:-3]
    print("published {}".format(now))
    client.publish(TOPIC, str(now), qos=2)

    time.sleep(1)

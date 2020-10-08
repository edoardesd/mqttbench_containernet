from datetime import datetime
import json
import os
import time


with open('confiles/experiment_test.json') as config_file:
    data = json.load(config_file)

publishers = data['publishers']
subscribers = data['subscribers']
num_messages = data['num_messages']
msg_wait = data['msg_wait']
qos = data["qos"]
topic = data["topic"].split(",")
MY_DIR = os.path.expanduser("~/mqttbench_containernet")


def print_sim(index):
    print("-" * 20)
    print("Case ", i)
    print("Pub: ", publishers[index])
    print("Sub: ", subscribers[index])
    print("Num msg: ", num_messages[index])
    print("Msg wait: ", msg_wait[index])
    print("QoS: ", qos[index])
    print("Topic: ", topic[index])
    print("")


print("="*20)
print("PUBLISHERS: ", publishers)
print("SUBSCRIBERS: ", subscribers)
print("NUM MESSAGES: ", num_messages)
print("MESSAGE WAIT: ", msg_wait)
print("QOS: ", qos)
print("TOPIC: ", topic)
print("="*20)
print("")
print("")

start_sim = datetime.now().strftime("%H%M%S")
for i in range(0, len(publishers)):
    print_sim(i)
    sub_folder = "{}pub-{}sub".format(publishers[i], subscribers[i])
    folder = "{}/{}".format(start_sim, sub_folder)

    command = "{}/start_clients.sh --clients {} --delay {} --messages {} --qos {} --name {}".format(MY_DIR,
                                                                                                    publishers[i],
                                                                                                    msg_wait[i],
                                                                                                    num_messages[i],
                                                                                                    qos[i],
                                                                                                    folder)
    os.system(command)

    print("")
    print("")
    print("Simulation {} finished".format(i+1))
    time.sleep(10)


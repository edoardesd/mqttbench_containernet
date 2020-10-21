#!/usr/bin/env python3
import math
import os
import random
import shlex
import subprocess
import time
import pprint as pp
from datetime import datetime
from pathlib import Path

NUM_MESSAGES = 5
NUM_SUBSCRIBERS = 15
NUM_PUBLISHERS = math.floor(NUM_SUBSCRIBERS / 10)
qos_list = [0]
topic_name = "topic"
message_delay = 1
CLUSTER_SIZE = 5
BROKER_TYPE = "EMQX"

locality_dict = {
    0: {
        'pub': random.randint(0, CLUSTER_SIZE - 1),
        'sub': None},
    # 50: {
    #     'pub': random.randint(0, CLUSTER_SIZE - 1),
    #     'sub': [i for i in range(0, CLUSTER_SIZE)]},
    100: {
        'pub': random.randint(0, CLUSTER_SIZE - 1),
        'sub': None}
}
locality_dict[0]['sub'] = [random.choice([i for i in range(0, CLUSTER_SIZE) if i not in [locality_dict[0]['pub']]])]
locality_dict[100]['sub'] = [locality_dict[100]['pub']]


def print_details():
    print()
    print("-" * 20)
    pp.pprint(locality_dict)
    print("._" * 10)
    print("Cluster size: {}".format(CLUSTER_SIZE))
    print("# of subscribers: {}".format(NUM_SUBSCRIBERS))
    print("# of publishers: {}".format(NUM_PUBLISHERS))
    print()


def start_clients(_subscribers, _publisher, _qos, _path, _file_name):
    for sub in _subscribers:
        subscriber_cmd = "docker exec -t mn.sub{id} python sub_thread.py -h 10.0.{id}.100 " \
                         "-t {topic} -q {qos} -m {msg} -c {clients} --folder {folder} --file-name {name} &".format(
                          id=sub,
                          topic=topic_name,
                          qos=_qos,
            msg=NUM_MESSAGES,
            clients=math.floor(NUM_SUBSCRIBERS / len(_subscribers)),
            folder=_path,
            name=_file_name)

        os.system(subscriber_cmd)
        print("Subscriber {id} created".format(id=sub))

    time.sleep(2)

    print("Creating publisher {id}...".format(id=_publisher))
    publisher_cmd = "docker exec -t mn.pub{id_pub} mqtt-benchmark --broker tcp://10.0.{id_pub}.100:1883 " \
                    "--topic {topic} --clients {clients} --count {msg} --qos {qos} --delay {rate} --folder {folder} --file-name {name}".format(
        id_pub=_publisher,
        topic=topic_name,
        qos=_qos,
        msg=NUM_MESSAGES,
        clients=NUM_PUBLISHERS,
        rate=message_delay,
        folder=_path,
        name=_file_name)

    os.system(publisher_cmd)


def main():
    print_details()

    for q in qos_list:
        for loc, clients in locality_dict.items():
            path = "experiments/{day}/{type}/{minute}/{qos}qos/{local}locality/".format(
                day=START_DAY,
                type=BROKER_TYPE,
                minute=START_MINUTE,
                qos=q,
                local=loc)

            print(path)
            print()
            print("-" * 20)
            print("Locality: {}%".format(loc))
            print("QoS: {}".format(q))
            for key, client in clients.items():
                if key == 'sub':
                    sub_list = client
                else:
                    publisher = client

            print(path)
            Path(path).mkdir(parents=True, exist_ok=True)
            file_name = "{}sub{}pub".format(NUM_SUBSCRIBERS, NUM_PUBLISHERS)

            f = open("blahss.txt", "w")
            cmd_stats = 'docker stats | ts "%F-%H:%M:%S"'
            print(shlex.split(cmd_stats))
            process_stats = subprocess.Popen(cmd_stats, stdout=f, shell=True)

            tcp_pid = []
            for b_id in range(0, CLUSTER_SIZE):
                cmd_tcpdump = "tcpdump -i s{broker_id}-eth1 src 10.0.{broker_id}.100 -w {folder}tcp{broker_id}.pcap -q".format(broker_id=b_id, folder=os.path.expanduser(path))
                tcp_pid.append(subprocess.Popen(shlex.split(cmd_tcpdump)))

            time.sleep(2)
            start_clients(sub_list, publisher, q, path, file_name)

            print(">>> Simulation {}% locality - {} qos - pub {} - sub {}... DONE\n".format(
                loc, q, NUM_PUBLISHERS, NUM_SUBSCRIBERS))

            time.sleep(5)
            process_stats.kill()
            for pid in tcp_pid:
                pid.kill()
            time.sleep(5)

        time.sleep(5)


if __name__ == "__main__":
    print(">>> EXPERIMENTS version 7.0 <<<")
    START_DAY = datetime.now().strftime("%m-%d")
    START_MINUTE = datetime.now().strftime("%H%M%S")
    main()

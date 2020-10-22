#!/usr/bin/env python3
import argparse
import math
import os
import random
import shlex
import signal
import subprocess
import time
import pprint as pp
from datetime import datetime
from pathlib import Path

NUM_SUBSCRIBERS = 15
NUM_PUBLISHERS = math.floor(NUM_SUBSCRIBERS / 10)
qos_list = [0, 1, 2]
topic_name = "topic"
message_delay = 1
CLUSTER_SIZE = 5

DELAY = 20

locality_dict = {
    0: {
        'pub': random.randint(0, CLUSTER_SIZE - 1),
        'sub': None},
    50: {
        'pub': random.randint(0, CLUSTER_SIZE - 1),
        'sub': [i for i in range(0, CLUSTER_SIZE)]},
    100: {
        'pub': random.randint(0, CLUSTER_SIZE - 1),
        'sub': None}
}
locality_dict[0]['sub'] = [random.choice([i for i in range(0, CLUSTER_SIZE) if i not in [locality_dict[0]['pub']]])]
locality_dict[100]['sub'] = [locality_dict[100]['pub']]

def arg_parse():
    parser = argparse.ArgumentParser(description='Locality experiment', add_help=False)
    parser.add_argument('-m', '--messages', dest='NUM_MESSAGES', default=5,
                        help='number of published messages', type=int)
    parser.add_argument('-t', '--type', dest='BROKER_TYPE', required=True,
                        help='Cluster type')

    return parser.parse_args()

def print_details():
    print()
    print("-" * 20)
    pp.pprint(locality_dict)
    print("._" * 10)
    print("Cluster size: {}".format(CLUSTER_SIZE))
    print("# of subscribers: {}".format(NUM_SUBSCRIBERS))
    print("# of publishers: {}".format(NUM_PUBLISHERS))
    print("# of messages: {}".format(NUM_MESSAGES))
    print()


def start_statistics(_path):
    f = open(_path + "/stats.txt", "w")
    cmd_stats = 'exec docker stats --format "{{.ID}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{' \
                '.NetIO}},{{.BlockIO}},{{.PIDs}}" | ts "%F-%H:%M:%S,"'
    process_stats = subprocess.Popen(cmd_stats, stdout=f, shell=True, preexec_fn=os.setsid)

    print("Logging stats...")
    return process_stats


def start_tcpdump(_path):
    _tcp_pid = []
    for b_id in range(0, CLUSTER_SIZE):
        cmd_tcpdump = "tcpdump -i s{broker_id}-eth1 src 10.0.{broker_id}.100 -w {folder}tcp{broker_id}.pcap -q".format(
            broker_id=b_id, folder=os.path.expanduser(_path))
        _tcp_pid.append(subprocess.Popen(shlex.split(cmd_tcpdump), stderr=subprocess.DEVNULL))

    print("Logging tcpdump...")
    return _tcp_pid


def start_clients(_subscribers, _publisher, _qos, _path, _file_name):
    random.shuffle(_subscribers)
    print(_subscribers)
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

    time.sleep(DELAY)

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
            Path(path).mkdir(parents=True, exist_ok=True)
            file_name = "{}sub{}pub".format(NUM_SUBSCRIBERS, NUM_PUBLISHERS)

            print("+++ Directory path: {}".format(path))
            print()
            print("-" * 20)
            print("Locality: {}%".format(loc))
            print("QoS: {}".format(q))
            for key, client in clients.items():
                if key == 'sub':
                    sub_list = client
                else:
                    publisher = client

            # start loggers
            stats_pid = start_statistics(path)
            tcpdump_pid = start_tcpdump(path)

            time.sleep(DELAY/5)
            start_clients(sub_list, publisher, q, path, file_name)

            print("\n>>> Simulation {}% locality - {} qos - pub {} - sub {}... DONE\n".format(
                loc, q, NUM_PUBLISHERS, NUM_SUBSCRIBERS))

            time.sleep(DELAY/2)

            # kill other processes
            os.killpg(os.getpgid(stats_pid.pid), signal.SIGTERM)
            for pid in tcpdump_pid:
                pid.kill()

            time.sleep(DELAY/4)

        time.sleep(DELAY/2)


if __name__ == "__main__":
    print(">>> EXPERIMENTS version 7.0 <<<")
    START_DAY = datetime.now().strftime("%m-%d")
    START_MINUTE = datetime.now().strftime("%H%M%S")
    args = arg_parse()
    NUM_MESSAGES = args.NUM_MESSAGES
    BROKER_TYPE = args.BROKER_TYPE
    main()

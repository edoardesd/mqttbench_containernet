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

NUM_PUBLISHERS = 1
NUMBER_SIMULATIONS = 1
qos_list = [0, 1, 2]
topic_name = "topic"
message_delay = 1
CLUSTER_SIZE = 5

DELAY = 5

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
locality_dict[0]['sub'] = [random.choice(
    [i for i in range(0, CLUSTER_SIZE) if i not in [locality_dict[0]['pub']]])] * CLUSTER_SIZE
locality_dict[100]['sub'] = [locality_dict[100]['pub']] * CLUSTER_SIZE


def arg_parse():
    parser = argparse.ArgumentParser(description='Locality experiment', add_help=False)
    parser.add_argument('-m', '--messages', dest='NUM_MESSAGES', default=5,
                        help='number of published messages', type=int)
    parser.add_argument('-s', '--subscribers', dest="NUM_SUBSCRIBERS", default=15,
                        help='number of subscribers', type=int)
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
    for indx, sub in enumerate(_subscribers):
        subscriber_cmd = "docker exec -d mn.sub{id} python3 mosquitto_sub.py -h 10.0.{id}.100 " \
                         "-t {topic} -q {qos} -m {msg} -c {clients} --folder {folder} --file-name {name}".format(
                                                        id=sub,
                                                        topic=topic_name,
                                                        qos=_qos,
                                                        msg=NUM_MESSAGES,
                                                        clients=math.floor(NUM_SUBSCRIBERS / len(_subscribers)),
                                                        folder=_path,
                                                        name="{}_{}".format(_file_name, indx))

        subprocess.Popen(subscriber_cmd, shell=True)
        print("Subscriber {index} created. Broker {id}".format(index=indx, id=sub))

    time.sleep(DELAY)

    print("Creating publisher {id}...".format(id=_publisher))
    publisher_cmd = "docker exec -t mn.pub{id_pub} mqtt-benchmark --broker tcp://10.0.{id_pub}.100:1883 " \
                    "--topic {topic} --clients {clients} --count {msg} --qos {qos} --delay {rate} " \
                    "--folder {folder} --file-name {name}".format(
                                                                id_pub=_publisher,
                                                                topic=topic_name,
                                                                qos=_qos,
                                                                msg=NUM_MESSAGES,
                                                                clients=NUM_PUBLISHERS,
                                                                rate=message_delay,
                                                                folder=_path,
                                                                name=_file_name)

    os.system(publisher_cmd)


def simulation(sim_num):
    for q in qos_list:
        for loc, clients in locality_dict.items():
            path = "experiments/{day}/{type}/{minute}/{sim}/{qos}qos/{local}locality/".format(
                day=START_DAY,
                type=BROKER_TYPE,
                minute=START_MINUTE,
                sim=sim_num,
                qos=q,
                local=loc)
            Path(path).mkdir(parents=True, exist_ok=True)
            file_name = "{}sub{}pub".format(NUM_SUBSCRIBERS, NUM_PUBLISHERS)

            print()
            print("-" * 80)
            print("++ Directory path: {}".format(path))
            print("-" * 80)
            print()
            print("Sim num {}".format(sim_num))
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

            time.sleep(DELAY / 5)
            start_clients(sub_list, publisher, q, path, file_name)

            print("\n>>> Simulation number {}. {}% locality - {} qos - pub {} - sub {}... DONE\n".format(
                sim_num, loc, q, NUM_PUBLISHERS, NUM_SUBSCRIBERS))

            time.sleep(DELAY / 2)

            # kill mosquitto_sub pids
            print("Killing in the name! (subscribers)")
            for sub_id in sub_list:
                ps_cmd = "docker exec -t mn.sub{} ps | grep python3 | awk '{{print $1}}'".format(sub_id)
                sub_pid = subprocess.getoutput(ps_cmd)
                sub_pid = [int(x) for x in sub_pid.split("\n") if x]
                for pid in sub_pid:
                    cmd = "docker exec -t mn.sub{} kill -2 {}".format(sub_id, int(pid))
                    print("-- {}".format(cmd))
                    subprocess.getoutput(cmd)

            # if needed cat e2e_* > e2e_all.txt
            print("Creating single e2e file...")
            subprocess.getoutput("cat {path}/e2e_* > {path}/delay_e2e_all.txt".format(path=path))
            subprocess.getoutput("mkdir {path}/e2e_raw".format(path=path))
            subprocess.getoutput("mv {path}/e2e_* {path}/e2e_raw".format(path=path))

            # kill other processes
            os.killpg(os.getpgid(stats_pid.pid), signal.SIGTERM)
            for pid in tcpdump_pid:
                pid.kill()

            time.sleep(DELAY / 4)

        time.sleep(DELAY / 2)


def main():
    print_details()

    for sim in range(1, NUMBER_SIMULATIONS+1):
        simulation(sim)
        print()
        print("-"*50)
        print("Simulation level {} done".format(sim))
        print("-"*50)
        time.sleep(DELAY * 2)


if __name__ == "__main__":
    print(">>> Experiments, software version 7.0 <<<")
    print("Looking at life through the eyes of a tired hub...")
    START_DAY = datetime.now().strftime("%m-%d")
    START_MINUTE = datetime.now().strftime("%H%M%S")
    args = arg_parse()
    NUM_MESSAGES = args.NUM_MESSAGES
    BROKER_TYPE = args.BROKER_TYPE
    NUM_SUBSCRIBERS = args.NUM_SUBSCRIBERS
    main()

import argparse
from datetime import datetime
import json
import os
import time


def arg_parse():
    parser = argparse.ArgumentParser(description='Experiments wrapper',)
    parser.add_argument('-j', '--json', dest='json_file', default='confiles/experiment_test.json',
                        help='Json file name')
    # parser.print_help()
    return parser.parse_args()


def print_sim(index):
    print("-" * 20)
    print("Case ", index)
    print("Pub: ", publishers[index])
    print("Sub: ", subscribers[index])
    print("Num msg: ", num_messages[index])
    print("Msg wait: ", msg_wait[index])
    print("QoS: ", qos[index])
    print("Topic: ", topic[index])
    print("")


def main():
    print("=" * 20)
    print("PUBLISHERS: ", publishers)
    print("SUBSCRIBERS: ", subscribers)
    print("NUM MESSAGES: ", num_messages)
    print("MESSAGE WAIT: ", msg_wait)
    print("QOS: ", qos)
    print("TOPIC: ", topic)
    print("=" * 20)
    print("")
    print("")

    day_sim = datetime.now().strftime("%m-%d")
    time_sim = datetime.now().strftime("%H%M%S")
    for i in range(0, len(publishers)):
        print_sim(i)
        sub_folder = "{}pub-{}sub".format(publishers[i], subscribers[i])
        folder = "experiments/{}/{}/{}".format(day_sim, time_sim, sub_folder)

        command = "{}/start_clients.sh --clients {} --delay {} --messages {} --qos {} --name {}".format(os.path.expanduser("~/"+my_dir),
                                                                                                        publishers[i],
                                                                                                        msg_wait[i],
                                                                                                        num_messages[i],
                                                                                                        qos[i],
                                                                                                        folder)
        os.system(command)

        print("")
        print("")
        print("Simulation {} finished".format(i + 1))
        time.sleep(10)


if __name__ == "__main__":
    args = arg_parse()

    with open(args.json_file) as config_file:
        data = json.load(config_file)

    publishers = data['publishers']
    subscribers = data['subscribers']
    num_messages = data['num_messages']
    msg_wait = data['msg_wait']
    qos = data["qos"]
    topic = data["topic"].split(",")
    my_dir = "mqttbench_containernet"
    # MY_DIR = os.path.expanduser("~/mqttbench_containernet")

    main()

import argparse
import paho.mqtt.client as mqtt
import random
import string
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path


current_milli_time = lambda: int(round(time.time() * 1000))


def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT thread subscriber', add_help=False)
    parser.add_argument('-h', '--host', dest='host', default='10.0.1.100',
                        help='broker host name (e.g. 10.0.0.100)')
    parser.add_argument('-t', '--topic', dest='topic', default='test',
                        help='mqtt topic')
    parser.add_argument('-q', '--qos', dest='qos', default=2,
                        help='mqtt quality of service', type=int)
    parser.add_argument('-m', '--number-messages', dest='msg_num', default=20,
                        help='number of messages per client', type=int)
    parser.add_argument('-c', '--clients-num', dest='clients_num', default=10,
                        help='number of different clients', type=int)
    parser.add_argument('-f', '--folder', dest='folder', default='experiments/untracked',
                        help='name of the simulation folder')
    parser.add_argument('-n', '--file-name', dest='file_name', default=datetime.now().strftime("%H%M%S"),
                        help='name of the file')
    # parser.print_help()

    return parser.parse_args()


class Receiver(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.is_running = True
        self.counter = 0
        self.e2e_result = []
        self.connect_start = 0
        self.connect_result = []
        self.e2e_dict = {}
        self.last_msg = None

    def on_message(self, client, userdata, message):
        self.last_msg = datetime.now()
        self.e2e_result.append(
            "{},{},{},{}, {}".format(args.host, client._client_id, str(message.payload.decode("utf-8")),
                                    current_milli_time(),
                                    args.qos))
        # self.e2e_dict[self.counter] = "{}, {}, {}, {}".format(args.host, client._client_id,
        #                                                       str(message.payload.decode("utf-8")),
        #                                                       datetime.now().strftime("%H:%M:%S.%f")[:-3],
        #                                                       args.qos)

        self.counter += 1
        if self.counter % 10 == 0:
            print(".", end='', flush=True)

        if self.counter >= args.msg_num * args.clients_num:
            self.is_running = False


    def on_connect(self, client, userdata, flags, rc):
        print("Client {} connected to {}".format(client._client_id, args.host))

        self.connect_result.append("{},{},{},{}".format(args.host, client._client_id, self.connect_start,
                                                           current_milli_time()))

        client.subscribe(args.topic, args.qos)

    def run(self):
        client = mqtt.Client("sub" + self.name + '-' + ''.join(random.choice(string.ascii_lowercase) for i in range(6)))

        client.on_message = self.on_message
        client.on_connect = self.on_connect

        self.connect_start = current_milli_time()
        client.connect(args.host)
        client.loop_start()

        while self.is_running:
            print(datetime.now(), self.last_msg)
            if self.last_msg is not None:
                if datetime.now() - self.last_msg > timedelta(minutes=2):
                    self.is_running = False
            pass

        print("{} received {} messages".format(self.name, len(self.e2e_result)))
        with open(args.folder + "/e2e" + file_name, "a") as f:
            f.write("\n".join(self.e2e_result))
            f.write("\n")

        with open(args.folder + "/conn" + file_name, "a") as f:
            f.write("\n".join(self.connect_result))
            f.write("\n")


def main():
    clients = []
    for cl in range(0, args.clients_num):
        t_mqtt = Receiver()
        t_mqtt.setDaemon(True)
        clients.append(t_mqtt)

    with open(args.folder + "/e2e" + file_name, "a") as f:
        f.write("thisbroker,client_name,client_broker,client_id,sent,received,qos\n")

    with open(args.folder + "/conn" + file_name, "a") as f:
        f.write("broker,client,conn,connack\n")

    for x in clients:
        x.start()

    time.sleep(.5)

    for x in clients:
        x.join()

    print("SUBSCRIBER {} is done receiving".format(broker_num[2]))
    time.sleep(1)
    sys.exit(1)


if __name__ == "__main__":
    print("SUB CLIENT THREADED VERSIONe")
    args = arg_parse()
    broker_num = "_b" + args.host.split('.')[2] + "_"
    file_name = broker_num + args.file_name + ".txt"
    print(">>> folder by sub: ", args.folder)
    print(">>>> file name: ", file_name)
    Path(args.folder).mkdir(parents=True, exist_ok=True)

    main()

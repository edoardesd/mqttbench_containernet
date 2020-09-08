import argparse
import paho.mqtt.client as mqtt
import random
import string
import sys
import threading
import time
from datetime import datetime


def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT thread publisher', add_help=False)
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
    parser.add_argument('-d', '--delay', dest='delay', default=1,
                        help='delay between pubblications', type=int)
    # parser.print_help()

    return parser.parse_args()


class Sender(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.client = mqtt.Client("pub_" + self.name + '-' + ''.join(random.choice(string.ascii_lowercase) for i in range(6)))

    def run(self):
        self.client.connect(args.host)
        print("Client {} connected to {}".format(self.client._client_id, args.host))
        for i in range(0, args.msg_num):
            now = str(datetime.now().strftime("%H:%M:%S.%f")[:-3])
            self.client.publish(args.topic, now, qos=args.qos)
            print("{}) published {}".format(i, now))

            time.sleep(args.delay)


def main():
    clients = []
    for cl in range(0, args.clients_num):
        t = Sender()
        t.setDaemon(True)
        clients.append(t)

    for x in clients:
        x.start()

    time.sleep(1)

    for x in clients:
        x.join()

    print("PUB DONE")
    sys.exit(1)


if __name__ == "__main__":
    args = arg_parse()
    main()

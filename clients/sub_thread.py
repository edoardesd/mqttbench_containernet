import argparse
import paho.mqtt.client as mqtt
import sys
import threading
import time
from datetime import datetime


def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT simple publisher', add_help=False)
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
    # parser.print_help()

    return parser.parse_args()


class Receiver(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.is_running = True
        self.counter = 0

        # self.queue_sub = queue_sub

    def on_message(self, client, userdata, message):
        self.counter += 1
        print("{}, {}, {}, {}, ".format(args.host, client._client_id, str(message.payload.decode("utf-8")),
                                        datetime.now().strftime("%H:%M:%S.%f")[:-3],
                                        message.qos))
        # self.queue_sub.put(message)

        if self.counter >= 5:
            self.is_running = False

    def run(self):
        client = mqtt.Client(self.name)
        client.on_message = self.on_message
        client.connect(args.host)
        print("Client {} connected to {}".format(client._client_id, args.host))
        client.subscribe(args.topic, args.qos)
        # print("Subscribed to {}".format(args.topic))
        client.loop_start()
        while self.is_running:
            pass


def main():
    clients = []
    for cl in range(0, args.clients_num):
        t_mqtt = Receiver()
        t_mqtt.setDaemon(True)
        clients.append(t_mqtt)

    for x in clients:
        x.start()

    time.sleep(.5)
    print(" ")
    print("broker, client, sent, received, qos")
    for x in clients:
        x.join()

    print("SUB DONE")
    sys.exit(1)


if __name__ == "__main__":
    args = arg_parse()
    counter_msg = 0
    main()

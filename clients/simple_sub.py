import argparse
import time
import sys
import paho.mqtt.client as mqtt
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
                        help='total number of mqtt messages', type=int)
    parser.add_argument('-c', '--clients-num', dest='clients_num', default=10,
                        help='number of different clients', type=int)
    # parser.print_help()

    return parser.parse_args()


class Receiver:
    def __init__(self):
        pass
        # self.queue_sub = queue_sub

    def on_message(self, client, userdata, message):
        global counter_msg

        counter_msg += 1
        print("{}) {}, {}, {}, ".format(counter_msg, str(message.payload.decode("utf-8")),
                                    datetime.now().strftime("%H:%M:%S.%f")[:-3],
                                    message.qos))
        # self.queue_sub.put(message)


def main():
    clients = []
    for cl in range(0, args.clients_num):
        client = mqtt.Client()
        receiver = Receiver()
        client.on_message = receiver.on_message
        client.connect(args.host)
        clients.append(client)
        print("Client {} connected to {}".format(client, args.host))
        client.subscribe(args.topic, args.qos)
        print("Subscribed to {}".format(args.topic))
        print(" ")
        print("sent, received, qos")
        client.loop_start()

    while counter_msg < args.msg_num:
        pass

    print("over")
    for client in clients:
        print("stop")
        client.loop_stop()

    # while True:
    #     if counter_msg >= args.msg_num:
    #         for client in clients:
    #             client.loop_stop()
    #         break

    sys.exit(1)


if __name__ == "__main__":
    args = arg_parse()
    counter_msg = 0
    main()

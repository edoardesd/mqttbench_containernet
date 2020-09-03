import argparse
import time
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
                        help='numer of mqtt messages per client', type=int)
    # parser.print_help()

    return parser.parse_args()


def main():
    client = mqtt.Client()

    client.connect(args.host)
    print("Connected to {}\n".format(args.host))
    for i in range(0, args.msg_num):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        client.publish(args.topic, str(now), qos=args.qos)
        print("{}) published {}".format(i, now))

        time.sleep(1)

    print("\nDONE!")


if __name__ == "__main__":
    args = arg_parse()
    main()



# complementary commands
# ping: docker exec -it mn.emqx_0 ping 10.0.4.100 -c 20
# sub: mosquitto_sub -h 172.17.0.2  -t test  -d | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"'  | tee test.txt


# docker cp simple_pub.py mn.sub_2:/home/ubuntu/simple_pub.py
# docker exec -it mn.sub_2 python simple_pub.py
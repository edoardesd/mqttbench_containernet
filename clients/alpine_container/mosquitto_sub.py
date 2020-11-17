import argparse
import os
import signal
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path


def kill_processes():
    print("Kill everything")
    for cmd, f_out in zip(mosq_pid, file_out):
        os.killpg(os.getpgid(cmd.pid), signal.SIGTERM)
        f_out.close()

    fix_files = "find {} -type f -name 'e2e*' -exec sed -i 's/\.//g;s/ /,/g' {{}} \;".format(args.folder)
    subprocess.Popen(fix_files, shell=True)
    # if needed cat e2e_c0* > merged.txt
    sys.exit(1)


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    kill_processes()


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


def main():
    for cl in range(0, args.clients_num):
        f = open(args.folder + "/e2e_c{}{}".format(cl, file_name), "w")
        mosquitto_cmd = "mosquitto_sub -h {host} -p 1883 -t {topic} -q {qos} -v | ts '%.s'".format(host=args.host,
                                                                                                   topic=args.topic,
                                                                                                   qos=args.qos)
        mosq_pid.append(subprocess.Popen(mosquitto_cmd, stdout=f, shell=True, preexec_fn=os.setsid))
        file_out.append(f)

    time.sleep(total_wait)

    print("SUBSCRIBER {} is done receiving".format(broker_num[2]))
    print("kill by timeout")
    kill_processes()


if __name__ == "__main__":
    print("SUB CLIENT THREADED VERSION")
    signal.signal(signal.SIGINT, signal_handler)

    mosq_pid = []
    file_out = []

    args = arg_parse()
    broker_num = "_b" + args.host.split('.')[2] + "_"
    file_name = broker_num + args.file_name + ".txt"
    total_wait = args.msg_num * 2
    print(">>> folder by sub: ", args.folder)
    print(">>>> file name: ", file_name)
    Path(args.folder).mkdir(parents=True, exist_ok=True)

    main()

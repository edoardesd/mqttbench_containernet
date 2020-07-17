import docker
import os
import time
import argparse
import json
import datetime
import subprocess
import sys

JSON_CLUSTERS = 'clusters'
JSON_TOPICS = 'topics'
JSON_SUBS = 'subs'
JSON_PUBS = 'pubs'
JSON_ALL = 'all'
JSON_DEFAULT = 'default'
NAME = "sub_"
IMAGE_NAME = 'flipperthedog/sub_client'
TOTAL_BROKERS = 5


def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--hostname', dest='hostname', required=True)
    parser.add_argument('-P', '--port', required=False, type=int, default=None,
                        help='Defaults to 8883 for TLS or 1883 for non-TLS')
    parser.add_argument('-t', '--topic', required=False, default='test')
    parser.add_argument('--sub-clients', type=int, dest='sub_clients', default=1,
                        help='The number of subscriber client workers to use. '
                             'By default 1 is used')
    parser.add_argument('--sub-count', type=int, dest='sub_count', default=1,
                        help='The number of messages each subscriber client '
                             'will wait to receive before completing. The '
                             'default count is 1.')
    parser.add_argument('-q', '--qos', required=False, dest='qos', type=int, default=0, choices=[0, 1, 2])
    parser.add_argument('--sub-timeout', type=int, dest='sub_timeout', required=False, default=60,
                        help='The amount of time, in seconds, a subscriber '
                             'client will wait for messages. By default this '
                             'is 60.')
    parser.add_argument('--multiple-topics', required=False, default=None, type=str,
                        help='The structure when clients needs to publish to multiple topics')
    parser.add_argument('--description', type=str, default=None,
                        help='A description of cluster topology. '
                             'Shall be used to set the name of log files of type: '
                             '*description*_*sub_1*')

    return parser.parse_args()


def main():
    docker_client = docker.from_env()
    ## kill the previous created containers
    for container in docker_client.containers.list(all=True):
        if "sub" in container.name:
            container.stop()
            container.remove()
            print(f"container {container.name} killed")

    container_list = []
    print("starting to create containers")
    for my_cont in range(TOTAL_BROKERS):
        container_name = f"{NAME}_{my_cont}"
        c = docker_client.containers.run(IMAGE_NAME, detach=True,
                                         tty=True, stdin_open=True,
                                         environment={
                                             'CLIENT_HOSTNAME': args.hostname,
                                             'CLIENT_SUBSCRIBERS': round(args.sub_clients / TOTAL_BROKERS),
                                             'CLIENT_SUBSCRIBERS_COUNT': args.sub_count,
                                             'CLIENT_PUBLISHERS': 0,
                                             'CLIENT_PUBLISHERS_COUNT': 0,
                                             'CLIENT_QOS': args.qos,
                                             'CLIENT_TOPIC': args.topic,
                                             'DESCRIPTION': 'star'
                                         },
                                         hostname=container_name, name=container_name
                                         )
        print(f"container {container_name} created")
        container_list.append(c)

    for c in container_list:
        subprocess.Popen(f'docker logs -f {c.name}', shell=True)

    # copy docker files to host
    # _date = datetime.datetime.utcnow().date().strftime('%d_%m') + '_'
    # copy_from('d1', docker_src_file='/home/logs', destination=pwd + '/logs', dst_file_prefix=_date + 'star')

    # while True:
    #     active_list = [c.name for c in docker_client.containers.list()]
    #     print(active_list)
    #     if any("sub" not in s for s in active_list):
    #         print("exit")
    #         sys.exit(-9)
    #time.sleep(150)
    # container_1.stop()


if __name__ == '__main__':
    pwd = os.getcwd()
    args = arg_parse()
    main()

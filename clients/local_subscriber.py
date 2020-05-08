import docker
import os
import time
import argparse
import json
import datetime

JSON_CLUSTERS = 'clusters'
JSON_TOPICS = 'topics'
JSON_SUBS = 'subs'
JSON_PUBS = 'pubs'
JSON_ALL = 'all'
JSON_DEFAULT = 'default'


# Parse topics distribution passed in a dict string format
class MultipleTopics(object):
    def __init__(self, parser, pub_cnt=0, sub_cnt=0):
        self.parser = parser
        self.args = parser.parse_args()
        try:
            self.sub_clients = getattr(self.args, 'sub_clients')
        except AttributeError:
            self.sub_clients = sub_cnt
        try:
            self.pub_clients = getattr(self.args, 'pub_clients')
        except AttributeError:
            self.pub_clients = pub_cnt

    def __call__(self, arg):
        self.arg = arg
        # The argument is the file
        # check if the file exists
        topics_dict = {}
        # print("In the call")
        if not os.path.exists(arg):
            raise self.exception()
        with open(arg, 'r') as f:
            try:
                topics_dict = json.load(f)
                # print('The dict')
                # print(topics_dict)
            except json.decoder.JSONDecodeError as err:
                raise self.exception(err)
            self.check_json_format(topics_dict)
        return topics_dict

    def check_json_format(self, json_obj: dict):
        # getting the number of publishers and subscribers
        tot_subs = tot_pubs = 0
        _ind = 0
        try:
            clients = json_obj[JSON_CLUSTERS]
        except KeyError:
            print('The JSON format of the file not recognized')
            exit(1)
        for group in clients:
            _ind = _ind + 1
            try:
                topics = group[JSON_TOPICS]
            except KeyError:
                print(f'Error: Something went wrong parsing (row {_ind})')
                exit(1)
            # Initialize the subs and pubs parameter
            try:
                nr_pubs = group[JSON_PUBS]
            except KeyError:
                nr_pubs = 0
            try:
                nr_subs = group[JSON_SUBS]
            except KeyError:
                nr_subs = 0
            if nr_subs == 0 and nr_pubs == 0:
                print(f'Parameters missing (row {_ind})')
                exit(1)
            if not isinstance(nr_pubs, int):
                print(f'Error: The pubs parameter in json file must be integer (row {_ind})')
                exit(1)
            if not isinstance(nr_pubs, int):
                print(f'Error: The subs parameter in json file must be integer (row {_ind})')
                exit(1)
            tot_subs = tot_subs + nr_subs
            tot_pubs = tot_pubs + nr_pubs
            for topic in topics:
                if not isinstance(topic, str):
                    print(f'Error: The list items of the topics parameter '
                          f'in the json file must be string type  (row {_ind})')
                    exit(1)

        if tot_subs > self.sub_clients:
            print('Error: The number of subscribers (--sub-clients) is smaller than the total number of subscribers '
                  'reported in the --multiple-topic file')
            exit(1)
        if tot_pubs > self.pub_clients:
            print('Error: The number of publisher (--pub-client) is smaller than the total number of publishers '
                  'reported in the --multiple-topic file')
            exit(1)

    def exception(self, err=None):
        if err is not None:
            return argparse.ArgumentTypeError(err.msg)
        if self.arg is not None:
            return argparse.ArgumentError('The JSON file could not be located')


def copy_from(container_name, docker_src_file: str, destination: str, dst_file_prefix: str = None) -> str:
    if not os.path.exists(destination):
        os.mkdir(destination)
    if not destination.endswith('/'):
        destination = destination + '/'
    container = docker.from_env().containers.get(container_name)
    # Get the content
    bits, stat = container.get_archive(docker_src_file)
    if dst_file_prefix is None:
        dst_file_prefix = 'output'
    index = 0
    if os.path.exists(os.path.join(destination + (dst_file_prefix + '(%d).tar' % index))):
        index += 1
        while os.path.exists(os.path.join(destination + (dst_file_prefix + '(%d).tar' % index))):
            index += 1
    with open(os.path.join(destination + (dst_file_prefix + '(%d).tar' % index)), 'wb') as f:
        for chunk in bits:
            f.write(chunk)
            f.close()
    return os.path.join(destination + dst_file_prefix + ('(%d).tar' % index))


def get_args(args: argparse.Namespace) -> str:
    args_dict = args.__dict__
    args_str = ''
    for key, value in args_dict.items():
        if value is not None:
            args_str = args_str + ' --' + key.replace('_', '-') + ' ' + str(value)
    return args_str


def main():
    pwd = os.getcwd()

    parser = argparse.ArgumentParser()

    parser.add_argument('-H', '--hostname', default='172.17.0.1', required=True)
    parser.add_argument('-P', '--port', required=False, type=int, default=None,
                        help='Defaults to 8883 for TLS or 1883 for non-TLS')
    parser.add_argument('-t', '--topic', required=False, default=None)
    parser.add_argument('--sub-clients', type=int, dest='sub_clients', default=1,
                        help='The number of subscriber client workers to use. '
                             'By default 1 is used')
    parser.add_argument('--sub-count', type=int, dest='sub_count', default=1,
                        help='The number of messages each subscriber client '
                             'will wait to receive before completing. The '
                             'default count is 1.')
    parser.add_argument('-q', '--qos', required=False, type=int, default=0, choices=[0, 1, 2])
    parser.add_argument('-u', '--username', required=False, default=None)
    parser.add_argument('-p', '--password', required=False, default=None)
    parser.add_argument('--sub-timeout', type=int, dest='sub_timeout', required=False, default=60,
                        help='The amount of time, in seconds, a subscriber '
                             'client will wait for messages. By default this '
                             'is 60.')
    parser.add_argument('-F', '--cacert', required=False, default=None)
    parser.add_argument('--multiple-topics', required=False, default=None, type=str,
                        help='The structure when clients needs to publish to multiple topics')
    parser.add_argument('--description', type=str, default=None,
                        help='A description of cluster topology. '
                             'Shall be used to set the name of log files of type: '
                             '*description*_*sub_1*')

    args = parser.parse_args()

    docker_client = docker.from_env()

    ## kill the previous created containers
    try:
        container_name = 'd1'
        running_container = docker_client.containers.get(container_name)
        running_container.stop()
        running_container.remove()
        print('Container %s stopped and removed' % container_name)
    except docker.errors.NotFound:
        pass

    container_volumes = []
    container_volumes.append(pwd + '/clients/container_python.py:/home/script.py')

    # check if --multiple-topics parameter is given and elaborate it
    topics_json_file = getattr(args, 'multiple_topics')
    if topics_json_file is not None:
        if topics_json_file.startswith('.'):
            topics_json_file = pwd + '/' + topics_json_file
        # print(topics_json_file)
        destination_json_file = '/home/multiple-topics.json'
        multiple_topics = MultipleTopics(parser, pub_cnt=100)
        topics_dict = multiple_topics(topics_json_file)
        # print(topics_dict)
        setattr(args, 'multiple_topics', destination_json_file)
        container_volumes.append(os.path.abspath(topics_json_file) + ':' + destination_json_file)

    # Is given priority to arguments passed in the command-line

    container_1 = docker_client.containers.create('francigjeci/mqtt-py:3.8.2', detach=True, working_dir='/home',
                                                  tty=True, stdin_open=True, volumes=container_volumes,
                                                  environment={
                                                      'CLIENT_HOSTNAME': '172.17.0.100',
                                                      'CLIENT_SUBSCRIBERS': 1,
                                                      'CLIENT_SUBSCRIBERS_COUNT': 1,
                                                      'CLIENT_PUBLISHERS': 0,
                                                      'CLIENT_PUBLISHERS_COUNT': 0,
                                                      'CLIENT_QOS': 0,
                                                      'DESCRIPTION': 'star'
                                                  },
                                                  hostname="client1", name='d1'
                                                  )

    print('Starting container %s ' % 'd1')
    container_1.start()
    time.sleep(2)
    print('Container %s started' % "d1")

    # Get a string representation of the args
    args_str = get_args(args)
    d1_bis = container_1.exec_run("python3 /home/script.py" )
    print(d1_bis.output.decode("utf-8"))
    # copy docker files to host
    _date = datetime.datetime.utcnow().date().strftime('%d_%m') + '_'
    copy_from('d1', docker_src_file='/home/logs', destination=pwd + '/logs', dst_file_prefix=_date + 'star')

    time.sleep(5)
    container_1.stop()


if __name__ == '__main__':
    main()

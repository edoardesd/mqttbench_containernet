import docker
import os
import time
import argparse
import json

MSG_SIZE_LIMIT = 120


# Parse topics distribution passed in a dict string format
class MultipleTopics(object):

    def __init__(self, parser, pub_cnt=0, sub_cnt=0):
        self.parser = parser
        self.args = parser.parse_args()
        try:
            self.sub_counts = getattr(self.args, 'sub_count')
        except AttributeError:
            self.sub_counts = sub_cnt
        try:
            self.pub_counts = getattr(self.args, 'pub_count')
        except AttributeError:
            self.pub_counts = pub_cnt

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
            clients = json_obj['clients']
        except KeyError:
            print('The JSON format of the file not recognized')
            exit(1)
        for group in clients:
            _ind = _ind + 1
            try:
                topics = group['topics']
            except KeyError:
                print(f'Error: Something went wrong parsing (row {_ind})')
                exit(1)
            # Initialize the subs and pubs parameter
            try:
                nr_pubs = group['pubs']
            except KeyError:
                nr_pubs = None
            try:
                nr_subs = group['subs']
            except KeyError:
                nr_subs = None
            if nr_subs is None and nr_pubs is None:
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

        if tot_subs > self.sub_counts:
            print('Error: The number of subscribers (--sub-count) is smaller than the total number of subscribers '
                  'reported in the --multiple-topic file')
            exit(1)
        if tot_pubs > self.pub_counts:
            print('Error: The number of publisher (--pub-count) is smaller than the total number of publishers '
                  'reported in the --multiple-topic file')
            exit(1)

    def exception(self, err=None):
        if err is not None:
            return argparse.ArgumentTypeError(err.msg)
        if self.arg is not None:
            return argparse.ArgumentError('The JSON file could not be located')

# Custom argparse to validate the message passed
class MessageValidation:

    def __init__(self, lower_limit=None):
        self.lower_limit = lower_limit

    def __call__(self, arg):
        try:
            _arg = str(arg)
        except ValueError:
            raise self.exception()
        if _arg is not None and len(_arg) < MSG_SIZE_LIMIT:
            raise self.exception(_arg)
        return _arg

    def exception(self, arg=None):
        if arg is not None:
            return argparse.ArgumentTypeError(f"The message size must be >= {MSG_SIZE_LIMIT}")
        else:
            return argparse.ArgumentTypeError("Message argument must be a string")


def get_args(args: argparse.Namespace) -> str:
    args_dict = args.__dict__
    args_str = ''
    for key, value in args_dict.items():
        if value is not None:
            args_str = args_str + ' --' + key.replace('_', '-') + ' ' + str(value)
    return args_str


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-H', '--hostname', required=False)
    parser.add_argument('-P', '--port', required=False, type=int, default=None,
                        help='Defaults to 8883 for TLS or 1883 for non-TLS')
    parser.add_argument('-t', '--topic', required=False, default="test")
    parser.add_argument('-T', '--multiple-topics', required=False, default=None, #type=MultipleTopics(parser),
                        help='The structure when clients needs to publish to multiple topics')
    parser.add_argument('--pub-clients', type=int, dest='pub_clients', # default=1,
                        help='The number of publisher client workers to use. '
                             'By default 1 are used.')
    parser.add_argument('--pub-count', type=int, dest='pub_count', # default=1,
                        help='The number of messages each publisher client '
                             'will publish for completing. The default count '
                             'is 1')
    parser.add_argument('-q', '--qos', required=False, type=int, default=0, choices=[0, 1, 2])
    # type=func -> useful to check if message size complies with the lower limit
    parser.add_argument('--msg-size', dest='msg_size', type=MessageValidation(MSG_SIZE_LIMIT),
                        help='The payload size to use in bytes')
    # parser.add_argument('--msg', type=str, dest='msg',
    #                     help='The payload of the publish message')
    parser.add_argument('-S', '--delay', required=False, type=float, default=None,
                        help='number of seconds to sleep between msgs')
    parser.add_argument('--pub-timeout', type=int, dest='pub_timeout', default=60,
                        help="The amount of time, in seconds, a publisher "
                             "client will wait to successfully publish it's "
                             "messages. By default this is 60")
    # parser.add_argument('-c', '--clientid', required=False, default=None)
    parser.add_argument('-u', '--username', required=False, default=None)
    # parser.add_argument('-d', '--disable-clean-session', action='store_true',
    #                     help="disable 'clean session' (sub + msgs not cleared when client disconnects)")
    parser.add_argument('-p', '--password', required=False, default=None)
    # parser.add_argument('-N', '--nummsgs', required=False, type=int, default=1,
    #                     help='send this many messages before disconnecting')
    # parser.add_argument('-k', '--keepalive', required=False, type=int, default=60)
    # parser.add_argument('-s', '--use-tls', action='store_true')
    # parser.add_argument('--insecure', action='store_true')
    parser.add_argument('-F', '--cacert', required=False, default=None,
                        help='The certificate authority certificate file that '
                             'are treated as trusted by the clients')
    # parser.add_argument('--tls-version', required=False, default=None,
    #                     help='TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1\n')
    # parser.add_argument('-D', '--debug', action='store_true')

    args = parser.parse_args()
    args_str = get_args(args)
    # print(args_str)
    pwd = os.getcwd()

    docker_client = docker.from_env()
    ret_it = docker_client.networks.list(names=['pumba_net'])[0]
    # print(ret_it.id)

    ## kill the previous created containers
    try:
        container_name = 'd2'
        running_container = docker_client.containers.get(container_name)
        running_container.stop()
        running_container.remove()
        print('Container %s stoped and removed' % container_name)
    except docker.errors.NotFound:
        pass

    container_volumes = []
    container_volumes.append(pwd + '/clients/container_python.py:/home/script.py')

    # check if --multiple-topics parameter is given and elaborate it
    topics_json_file = getattr(args, 'multiple_topics')
    if topics_json_file is not None:
        if topics_json_file.startswith('./'):
            topics_json_file = topics_json_file.replace('./', pwd + '/')
        if not topics_json_file.startswith('/'):
            topics_json_file = pwd + '/' + topics_json_file
        # print(topics_json_file)
        destination_json_file = '/home/multiple-topics.json'
        multiple_topics = MultipleTopics(parser, pub_cnt=100)
        topics_dict = multiple_topics(topics_json_file)
        # print(topics_dict)
        setattr(args, 'multiple_topics', True)
        container_volumes.append(topics_json_file + ':' + destination_json_file)

    container_2 = docker_client.containers.create('francigjeci/mqtt-py:3.8.2',
                                             detach=True,
                                            # entrypoint= 'echo hello',
                                            working_dir = '/home',
                                            tty=True, # terminal driver, necessary since you are running the python in bash
                                            stdin_open=True,
                                             # stream=True,
                                            volumes=container_volumes, #'/home',
                                            # command=["bash"],
                                            environment={
                                                'CLIENT_HOSTNAME': '172.17.0.105',
                                                'CLIENT_SUBSCRIBERS': 0,
                                                'CLIENT_SUBSCRIBERS_COUNT': 0,
                                                'CLIENT_PUBLISHERS': 5,
                                                'CLIENT_PUBLISHERS_COUNT': 10,
                                                # 'CLIENT_MESSAGE_SIZE': 32,
                                                # 'CLIENT_MESSAGE': 'hello',
                                                'CLIENT_TOPIC': 'test',
                                                'CLIENT_QOS': 0
                                            },
                                             #network='pumba_net', # the network this container must be connected
                                             hostname="client2", name='d2'# , ip='172.20.0.72'
                                             )

    container_2.start()
    print('Container %s started' % "d2")

    d2_bis = container_2.exec_run("python3 /home/script.py" + args_str) # args_str
    print(d2_bis.output.decode("utf-8"))

    time.sleep(5)
    container_2.stop()

if __name__ == '__main__':
    main()

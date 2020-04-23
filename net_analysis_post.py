# Copyright 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import datetime
import multiprocessing
import random
import string
import time
import os
from datetime import datetime

import numpy
import paho.mqtt.client as mqtt
from paho.mqtt import publish

BASE_TOPIC = 'pybench'

SUB_QUEUE = multiprocessing.Queue()
PUB_QUEUE = multiprocessing.Queue()


class Sub(multiprocessing.Process):
    def __init__(self, hostname, port=1883, client_id=None, tls=None, auth=None, topic=None,
                 timeout=60, max_count=10, qos=0):
        super(Sub, self).__init__()
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.tls = tls
        self.topic = topic or BASE_TOPIC
        self.auth = auth
        self.msg_count = 0
        self.start_time = None
        self.max_count = max_count
        self.end_time = None
        self.timeout = timeout
        self.qos = qos
        self.end_time_lock = multiprocessing.Lock()
        # adding e2e delay
        self.e2e_arrival = None

    def run(self):
        def on_connect(client, userdata, flags, rc):
            # Added the condition to connect to passed topic
            if self.topic is None:
                client.subscribe(BASE_TOPIC + '/#', qos=self.qos)
            else:
                client.subscribe(self.topic, qos=self.qos)

        def parse_msg(msg: str):
            fields = msg.split("_", 3)
            _origin_hostname = fields[0]
            _pub_id = fields[1]
            _time_sended = datetime.datetime.strptime(fields[2], '%Y-%m-%d %H:%M:%S.%f')

        def on_message(client, userdata, msg):
            if self.start_time is None:
                self.start_time = datetime.datetime.utcnow()
            self.msg_count += 1
            if self.msg_count >= self.max_count:
                self.end_time_lock.acquire()
                if self.end_time is None:
                    self.end_time = datetime.datetime.utcnow()
                self.end_time_lock.release()

        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        if self.tls:
            self.client.tls_set(**self.tls)
        if self.auth:
            self.client.username_pw_set(**self.auth)
        print(self)
        self.client.connect(self.hostname, port=self.port)
        self.client.loop_start()
        while True:
            time.sleep(1)
            self.end_time_lock.acquire()
            if self.end_time:
                delta = self.end_time - self.start_time
                SUB_QUEUE.put(delta.total_seconds())
                self.client.loop_stop()
                break
            self.end_time_lock.release()
            if self.start_time:
                current_time = datetime.datetime.utcnow()
                curr_delta = current_time - self.start_time
                if curr_delta.total_seconds() > self.timeout:
                    raise Exception('We hit the sub timeout!')


class Pub(multiprocessing.Process):
    def __init__(self, hostname, port=1883, client_id: str = None, tls=None, auth=None, topic: str = None,
                 timeout: int = 60, max_count: int = 10, msg_size: int = 1024, qos: int = 0):
        super(Pub, self).__init__()
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.tls = tls
        self.topic = topic or BASE_TOPIC
        self.auth = auth
        self.start_time = None
        self.max_count = max_count
        self.end_time = None
        self.timeout = timeout
        self.msg = None
        self.qos = qos
        self.msg_size = msg_size
        if self.msg_size < 51:
            raise Exception('Message size should be at least 50 characters')

    def utf8len(s):
        """The size in bytes of string"""
        return len(s.encode('utf-8'))

    def create_msg(self):
        if self.start_time is None:
            _pre_msg = hostname + '_' + self.client_id + '_' + str(datetime.datetime.utcnow())
        else:
            _pre_msg = hostname + '_' + self.client_id + '_' + str(self.start_time)
        return _pre_msg + '_'.join(
            random.choice(string.lowercase) for i in range(self.msg_size - len(_pre_msg.encode('utf-8'))))

    def run(self):
        self.start_time = datetime.datetime.utcnow()
        self.msg = self.create_msg()
        for i in range(self.max_count):
            publish.single(topic=self.topic, payload=self.msg, hostname=self.hostname,
                           port=self.port, auth=self.auth, tls=self.tls, qos=self.qos)
            if self.start_time:
                current_time = datetime.datetime.utcnow()
                curr_delta = current_time - self.start_time
                if curr_delta.total_seconds() > self.timeout:
                    raise Exception('We hit the pub timeout!')
        end_time = datetime.datetime.utcnow()
        delta = end_time - self.start_time
        PUB_QUEUE.put(delta.total_seconds())


def set_value(cmd_par, env_par, default: int, par_name: str) -> int:
    """Choose among the different option of passing the parameter and then validate
    :param cmd_par:  Parameter passed through command line in python script
    :param env_par: Parameter passed as environment parameter
    :param default: The default value
    :param par_name: Parameter name
    :return: The parsed parameter value
    """

    if cmd_par is None and env_par is None:
        return default
    else:
        if isinstance(env_par, str):
            try:
                env_par = int(env_par)
            except ValueError:
                raise Exception('The %s parameter must be of type integer' % par_name)
        if isinstance(cmd_par, str):
            try:
                cmd_par = int(cmd_par)
            except ValueError:
                raise Exception('The %s parameter must be of type integer' % par_name)
        if isinstance(env_par, int) or isinstance(cmd_par, int):
            return cmd_par or env_par
        else:
            raise Exception('Unexpected parameter type')


def is_positive(param: int, param_name: str):
    """Validate parameter to be positive"""
    if param < 0:
        raise Exception('The %s must be positive' % param_name)


def initialize_log_file(hostname: str, dest_path: str = 'logs', file_name: str = None):
    octets = hostname.split('.')
    if len(octets) != 4:
        raise Exception('Hostname passed is invalid')
    if file_name is None:
        file_name = 'log_' + octets[3] + '.csv'
    output_path = os.path.join(dest_path, file_name)
    # Writing the file header
    with open(output_path, 'a') as f:
        f.write('pub_client_id;hostname_origin;sending_timestamp;sub_client;')
        f.write('hostname_destination;arrival_timestamp;e2e_delay')
        f.write('\n')
        f.close()





def main(hostname=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostname', required=((os.getenv('CLIENT_HOSTNAME') is None) and (hostname is None)),
                        help='The hostname (or ip address) of the broker to '
                             'connect to')
    parser.add_argument('--port', type=int,
                        help='The port to use for connecting to the broker. '
                             'The default port is 1883.')
    parser.add_argument('--pub-clients', type=int, dest='pub_clients',
                        help='The number of publisher client workers to use. '
                             'By default 0 are used.')
    parser.add_argument('--sub-clients', type=int, dest='sub_clients',
                        help='The number of subscriber client workers to use. '
                             'By default 0 are used')
    parser.add_argument('--pub-count', type=int, dest='pub_count',
                        help='The number of messages each publisher client '
                             'will publish for completing. The default count '
                             'is 0')
    parser.add_argument('--sub-count', type=int, dest='sub_count',
                        help='The number of messages each subscriber client '
                             'will wait to recieve before completing. The '
                             'default count is 0.')
    parser.add_argument('--msg-size', type=int, dest='msg_size',
                        help='The payload size to use in bytes')
    # Added
    parser.add_argument('--msg', type=str, dest='msg',
                        help='The payload of the publish message')
    parser.add_argument('--sub-timeout', type=int, dest='sub_timeout',
                        help='The amount of time, in seconds, a subscriber '
                             'client will wait for messages. By default this '
                             'is 60.')
    parser.add_argument('--pub-timeout', type=int, dest='pub_timeout',
                        help="The amount of time, in seconds, a publisher "
                             "client will wait to successfully publish it's "
                             "messages. By default this is 60")
    parser.add_argument('--topic',
                        help='The MQTT topic to use for the benchmark. The '
                             'default topic is pybench')
    parser.add_argument('--cacert',
                        help='The certificate authority certificate file that '
                             'are treated as trusted by the clients')
    parser.add_argument('--username',
                        help='An optional username to use for auth on the '
                             'broker')
    parser.add_argument('--password',
                        help='An optional password to use for auth on the '
                             'broker. This requires a username is also set')
    parser.add_argument('--brief', action='store_true',
                        help='Print results in a colon separated list instead'
                             ' of a human readable format. See the README for '
                             'the order of results in this format')
    parser.add_argument('--qos', type=int, choices=[0, 1, 2],
                        help='The qos level to use for the benchmark')

    opts = parser.parse_args()

    sub_threads = []
    pub_threads = []

    ### parse the parameters
    _topic = getattr(opts, 'topic') or os.getenv('CLIENT_TOPIC') or BASE_TOPIC
    _hostname = getattr(opts, 'hostname') or os.getenv('CLIENT_HOSTNAME') or hostname
    _port = set_value(getattr(opts, 'port'), os.getenv('CLIENT_PORT'), 1883, 'port')
    _sub_clients = set_value(getattr(opts, 'sub_clients'), os.getenv('CLIENT_SUBSCRIBERS'), 0, 'number of subscribers')
    _sub_count = set_value(getattr(opts, 'sub_count'), os.getenv('CLIENT_SUBSCRIBERS_COUNT'), 0,
                           'number of messages per subscriber')
    _pub_clients = set_value(getattr(opts, 'pub_clients'), os.getenv('CLIENT_PUBLISHERS'), 0, 'number of publishers')
    _pub_count = set_value(getattr(opts, 'pub_count'), os.getenv('CLIENT_PUBLISHERS_COUNT'), 0,
                           'number of messages per publisher')
    _sub_timeout = set_value(getattr(opts, 'sub_timeout'), os.getenv('CLIENT_SUBSCRIBERS_TIMEOUT'), 60,
                             'subscriber timeout')
    _pub_timeout = set_value(getattr(opts, 'pub_timeout'), os.getenv('CLIENT_PUBLISHERS_TIMEOUT'), 60,
                             'publisher timeout')
    _qos = set_value(getattr(opts, 'qos'), os.getenv('CLIENT_QOS'), 0, 'qos')
    _msg = getattr(opts, 'msg') or os.getenv('CLIENT_MESSAGE')
    _brief = getattr(opts, 'brief') or os.getenv('CLIENT_BRIEF') or False

    if not isinstance(_topic, str):
        raise Exception('The topic parameter must be string type')
    if not isinstance(_hostname, str):
        raise Exception('The hostname parameter must be string type')
    if not isinstance(_brief, bool):
        raise Exception('The brief parameter must be boolean type')

    # Check if parameters are positive, otherwise raise an error
    is_positive(_sub_clients, 'number of subscribers')
    is_positive(_pub_clients, 'number of publishers')
    is_positive(_sub_count, 'number of messages per subscriber')
    is_positive(_pub_count, 'number of messages per publisher')

    if isinstance(_qos, int):
        if _qos not in [0, 1, 2]:
            raise Exception('The QOS value is expected to be 0, 1 or 2')
    else:
        raise Exception('The QOS parameter must be int type ')

    _tls = None
    if getattr(opts, 'cacert'):
        _tls = {'ca_certs': opts.cacert}
    # Check if certificate has been given as env parameter
    elif os.getenv('CAERT'):
        _tls = {'ca_certs': os.getenv('CAERT')}

    _auth = None
    if opts.username:
        _auth = {'username': opts.username,
                 'password': getattr(opts, 'password')}
    elif os.getenv('CLIENT_USERNAME'):
        _auth = {'username': os.getenv('CLIENT_USERNAME'),
                 'password': os.getenv('CLIENT_PASSWORD')}

    # Not necessary for our use-case
    # if _pub_count * _pub_clients < _sub_count:
    #     print('The configured number of publisher clients and published '
    #           'message count is too small for the configured subscriber count.'
    #           ' Increase the value of --pub-count and/or --pub-clients, or '
    #           'decrease the value of --sub-count.')
    #     exit(1)

    for i in range(_sub_clients):
        sub = Sub(_hostname, _port, 'sub' + str(i), _tls, _auth, _topic, _sub_timeout,
                  _sub_count, _qos)
        sub_threads.append(sub)
        sub.start()

    for i in range(_pub_clients):
        pub = Pub(_hostname, _port, 'pub' + str(i), _tls, _auth, _topic, _pub_timeout,
                  _pub_count, _qos)
        pub_threads.append(pub)
        pub.start()

    start_timer = datetime.datetime.utcnow()
    for client in sub_threads:
        client.join(_sub_timeout)
        curr_time = datetime.datetime.utcnow()
        delta = start_timer - curr_time
        if delta.total_seconds() >= _sub_timeout:
            raise Exception('Timed out waiting for threads to return')

    start_timer = datetime.datetime.utcnow()
    for client in pub_threads:
        client.join(_pub_timeout)
        curr_time = datetime.datetime.utcnow()
        delta = start_timer - curr_time
        if delta.total_seconds() >= _sub_timeout:
            raise Exception('Timed out waiting for threads to return')

    # Check if message has been given as a parameter when the nr of pub is greater than 0
    # if _pub_count > 0 and _msg is None:
    #     print('--msg is needed when publishers '
    #           'are present')
    #     exit(1)

    # Let's do some maths
    # Used to shut down the threads when they connection errors are present
    if SUB_QUEUE.qsize() < _sub_clients:
        print('Something went horribly wrong, there are less results than '
              'sub threads')
        exit(1)
    if PUB_QUEUE.qsize() < _pub_clients:
        print('Something went horribly wrong, there are less results than '
              'pub threads')
        exit(1)

    sub_times = []
    for i in range(_sub_clients):
        try:
            sub_times.append(SUB_QUEUE.get(_sub_timeout))
        except multiprocessing.queues.Empty:
            continue
    if len(sub_times) < _sub_clients:
        failed_count = _sub_clients - len(sub_times)
    sub_times = numpy.array(sub_times)

    pub_times = []
    for i in range(_pub_clients):
        try:
            pub_times.append(PUB_QUEUE.get(_pub_timeout))
        except multiprocessing.queues.Empty:
            continue
    if len(pub_times) < _pub_clients:
        failed_count = _pub_clients - len(pub_times)
    pub_times = numpy.array(pub_times)

    if len(sub_times) < _sub_clients:
        failed_count = _sub_clients - len(sub_times)
        print("%s subscription workers failed" % failed_count)
    if len(pub_times) < _pub_clients:
        failed_count = _pub_clients - len(pub_times)
        print("%s publishing workers failed" % failed_count)

    sub_mean_duration = sub_std_duration = sub_avg_throughput = sub_total_thpt = 0
    pub_mean_duration = pub_std_duration = pub_avg_throughput = pub_total_thpt = 0

    # Check whether sub are present
    if _sub_count * _sub_clients > 0:
        sub_mean_duration = numpy.mean(sub_times)
        sub_std_duration = numpy.std(sub_times)
        sub_avg_throughput = float(_sub_count) / float(sub_mean_duration)
        sub_total_thpt = float(
            _sub_count * _sub_clients) / float(sub_mean_duration)

    if _pub_count * _pub_clients > 0:
        pub_mean_duration = numpy.mean(pub_times)
        pub_std_duration = numpy.std(pub_times)
        pub_avg_throughput = float(_pub_count) / float(pub_mean_duration)
        pub_total_thpt = float(
            _pub_count * _pub_clients) / float(pub_mean_duration)

    if _brief:
        output = '%s;%s;%s;%s;%s;%s;%s;%s;%s;%s'
    else:
        output = """\
[ran with %s subscribers and %s publishers]
================================================================================
Subscription Results
================================================================================
Avg. subscriber duration: %s
Subscriber duration std dev: %s
Avg. Client Throughput: %s
Total Throughput (msg_count * clients) / (avg. sub time): %s
================================================================================
Publisher Results
================================================================================
Avg. publisher duration: %s
Publisher duration std dev: %s
Avg. Client Throughput: %s
Total Throughput (msg_count * clients) / (avg. sub time): %s
"""
    # e2e Delay of msg
    # divide the components of the delay
    # throughtput input/output
    # cpu/ RAM -> broker

    print(output % (
        _sub_clients,
        _pub_clients,
        sub_mean_duration,
        sub_std_duration,
        sub_avg_throughput,
        sub_total_thpt,
        pub_mean_duration,
        pub_std_duration,
        pub_avg_throughput,
        pub_total_thpt,
    ))


if __name__ == '__main__':
    # hostname = '172.20.0.2'
    hostname = None
    main(hostname=hostname)

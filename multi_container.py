#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import debug, info, error, setLogLevel
import argparse
import itertools
import os
import time


PWD = os.getcwd()
VERSION = 0.2
TOTAL_BROKERS = 5
DELAY = 10
IP_ADDR = '10.0.0.'
IMAGES = {
    "EMQX": "flipperthedog/emqx-bash:latest"
}

def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT cluster simulation')
    parser.add_argument('-n', '--broker-number', dest='bkr_num', default=5,
                        help='specify the size of the cluster')
    parser.add_argument('-t', '--type', dest='cluster_type', default='emqx',
                        help='broker type (EMQX, RABBITMQ, VERNEMQ, HIVEMQ)')
    parser.add_argument('-d', '--delay', dest='link_delay', default=10,
                        help='delay over a simple link')
    return parser.parse_args()


def emqx(broker):
    print("EMQX test")
    local_list = []

    for cnt in range(2, args.bkr_num + 1):
        container_name = "{}_{}".format(args.cluster_type, cnt)
        local_address = IP_ADDR+str(250+cnt)
        d = net.addDocker(name=container_name, ip= local_address,
                          # ports=[1883], port_bindings={1883: 1883},
                          dimage=IMAGES[broker],
                          environment={"EMQX_NAME": container_name,
                                        "EMQX_HOST": local_address,
                                        "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                        "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                        "EMQX_CLUSTER__DISCOVERY": "static",
                                        "EMQX_CLUSTER__STATIC__SEEDS": "docker2@10.0.0.252"
                                       })
        local_list.append(d)

    return local_list


def rabbitmq(broker):
    print("RabbitMQ test")


def hivemq(broker):
    print("HiveMQ test")


def vernemq(broker):
    print("VerneMQ test")


def invalid(broker):
    print("Invalid {}".format(broker))


def cluster_type(argument):

    switcher = {
        'EMQX': emqx,
        'RABBITMQ': rabbitmq,
        'VERNEMQ': vernemq,
        'HIVEMQ': hivemq
    }
    func = switcher.get(argument, lambda: invalid())
    return func(argument)


def main(_args):
    print("*** Multi containernet generator v{} ***".format(VERSION))
    print("args:")
    print("\tCLUSTER TYPE: {}".format(args.cluster_type))
    print("\tNUMBER OF BROKERS: {}".format(args.bkr_num))
    print("\tDELAY: {}".format(args.link_delay))
    print("\n")

    info('*** Adding controller')
    net.addController('c0', port=6654)
    info('  DONE\n')

    info('*** Adding docker containers, type: {}\n'.format(_args.cluster_type.upper()))
    container_list = cluster_type(_args.cluster_type.upper())
    print(container_list)

    info('*** Adding switches\n')
    switch_list = []
    for switch in range(2, args.bkr_num + 1):
        switch_name = "sw_{}".format(switch)
        s = net.addSwitch(switch_name)
        switch_list.append(s)

    print(switch_list)

    info('*** Adding container-switch link\n')
    for container, switch in zip(container_list, switch_list):
        net.addLink(container, switch)

    info('*** Adding switch-switch link\n')
    for subset in itertools.combinations(switch_list, 2):
        net.addLink(subset[0], subset[1], cls=TCLink, delay='1ms', bw=1)

    info('*** Starting network\n')
    net.start()
    net.staticArp()

    info('*** Testing connectivity\n')
    for subset in itertools.combinations(container_list, 2):
        net.ping([subset[0], subset[1]])

    info('*** Running CLI\n')
    CLI(net)
    info('*** Stopping network')
    net.stop()


if __name__ == "__main__":
    setLogLevel('info')

    net = Containernet(controller=Controller)

    args = arg_parse()

    main(args)

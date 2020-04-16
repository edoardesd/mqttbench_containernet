#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import debug, info, error, setLogLevel
import argparse
from shutil import copyfile
import itertools
import os
import time

PWD = os.getcwd()
VERSION = 0.2
TOTAL_BROKERS = 3
DELAY = 10
IP_ADDR = '10.0.0.'
IMAGES = {
    "EMQX": "flipperthedog/emqx-ip:latest",
    "VERNEMQ": "francigjeci/vernemq-debian:latest",
    "RABBITMQ": "flipperthedog/rabbitmq:ping"
}


def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT cluster simulation')
    parser.add_argument('-n', '--broker-number', dest='broker_num', default=TOTAL_BROKERS,
                        help='specify the size of the cluster')
    parser.add_argument('-t', '--type', dest='cluster_type', default='rabbitmq',
                        help='broker type (EMQX, RABBITMQ, VERNEMQ, HIVEMQ)')
    parser.add_argument('-d', '--delay', dest='link_delay', default=DELAY,
                        help='delay over a simple link')
    return parser.parse_args()


def start_emqx(cont_name, cont_address, bind_ip, master_node):
    return net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                         ports=[1883], port_bindings={1883: bind_ip},
                         dimage=IMAGES["EMQX"],
                         environment={"EMQX_NAME": cont_name,
                                      "EMQX_HOST": cont_address,
                                      "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                      "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                      "EMQX_CLUSTER__DISCOVERY": "static",
                                      "EMQX_CLUSTER__STATIC__SEEDS": master_node
                                      })


def start_rabbitmq(cont_name, cont_address, bind_ip, master_node):
    dest_file = "{}/confiles/rabbitmq_{}.conf".format(PWD, cont_address[-3:])
    copyfile(PWD + "/confiles/rabbitmq.conf", dest_file)
    with open(dest_file, "a") as f:
        c = 0
        for i in range(2, args.broker_num + 2):
            if IP_ADDR + str(250 + i) != cont_address:
                c += 1
                f.write("cluster_formation.classic_config.nodes.{} = rabbit@rabbitmq_{}\n".format(c, i))

    d = net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                      dimage=IMAGES["RABBITMQ"], \
                      ports=[5672, 1883],
                      port_bindings={5672: 5670 + (bind_ip - 1880),
                                     1883: bind_ip},
                      volumes=[
                          PWD + "/confiles/rabbitmq_{}.conf:/etc/rabbitmq/rabbitmq.conf".format(cont_address[-3:]),
                          PWD + "/confiles/enabled_plugins:/etc/rabbitmq/enabled_plugins"],
                      environment={"RABBITMQ_ERLANG_COOKIE": "GPLDKBRJYMSKLTLZQDVG"})

    for i in range(2, args.broker_num + 2):
        if IP_ADDR + str(250 + i) != cont_address:
            d.cmd('echo "{}      {}" >> /etc/hosts'.format(IP_ADDR + str(250 + i), "rabbitmq_" + str(i)))

    return d


def start_hivemq(broker):
    info('HiveMQ test')


def start_vernemq(cont_name, cont_address, bind_ip, master_node):
    return net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                         ports=[1883], port_bindings={1883: bind_ip},
                         dimage=IMAGES["VERNEMQ"],
                         environment={
                             "DOCKER_VERNEMQ_NODENAME": cont_address,
                             "DOCKER_VERNEMQ_DISCOVERY_NODE": master_node[master_node.index("@") + 1:],
                             "DOCKER_VERNEMQ_ACCEPT_EULA": "yes",
                             "DOCKER_VERNEMQ_ALLOW_ANONYMOUS": "on"
                         })


def invalid(broker):
    info('Invalid {}'.format(broker))


def cluster_type(argument):
    switcher = {
        'EMQX': start_emqx,
        'RABBITMQ': start_rabbitmq,
        'VERNEMQ': start_vernemq,
        'HIVEMQ': start_hivemq
    }
    func = switcher.get(argument, lambda: invalid())

    local_list = []

    my_master = None
    for cnt in range(2, args.broker_num + 2):
        container_name = "{}_{}".format(args.cluster_type, cnt)
        local_address = IP_ADDR + str(250 + cnt)
        bind_addr = 1880 + cnt
        if my_master is None:
            my_master = "{}@{}".format(container_name, local_address)

        local_list.append(func(container_name, local_address, bind_addr, my_master))

    return local_list


def main(_args):
    info('\n*** Multi containernet generator v{} ***'.format(VERSION))
    info('\nargs:')
    info('\n\tCLUSTER TYPE: {}'.format(args.cluster_type))
    info('\n\tNUMBER OF BROKERS: {}'.format(args.broker_num))
    info('\n\tDELAY: {}'.format(args.link_delay))
    info('\n')

    info('\n*** Adding controller')
    net.addController('c0', port=6654)
    info('  DONE\n')

    info('\n*** Adding docker containers, type: {}\n'.format(_args.cluster_type.upper()))
    container_list = cluster_type(_args.cluster_type.upper())

    info('\n*** Adding switch\t')
    s1 = net.addSwitch('s1')
    info(s1)

    info('\n*** Adding container-switch links\n')
    for c in container_list:
        info(net.addLink(c, s1, cls=TCLink, delay='{}ms'.format(_args.link_delay / 2), bw=1))

    info('\n*** Starting network\n')
    net.start()
    net.staticArp()

    info('\n*** Testing connectivity\n')
    net.pingAll()

    info('\n*** Waiting the network start up ({} secs)...\n'.format(_args.link_delay / 2))
    time.sleep(_args.link_delay / 2)

    info('\n*** Starting the entrypoints\n')
    # START CONTAINERS
    for c in container_list:
        c.start()

    info('*** Waiting the boot ({} secs)...\n'.format(_args.link_delay))
    time.sleep(_args.link_delay)

    info('*** Running CLI\n')
    CLI(net)
    info('*** Stopping network')
    net.stop()


if __name__ == "__main__":
    setLogLevel('info')

    net = Containernet(controller=Controller)

    args = arg_parse()

    main(args)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.node import Node
from mininet.link import TCLink
from mininet.log import debug, info, error, setLogLevel
import argparse
from shutil import copyfile
import ipaddress
import os
import time
import xml.etree.ElementTree as ET

PWD = os.getcwd()
VERSION = 0.2
TOTAL_BROKERS = 5
DELAY = 10
IP_ADDR = '10.0.0.'
IMAGES = {
    "EMQX": "flipperthedog/emqx-ip:latest",
    "VERNEMQ": "francigjeci/vernemq-debian:latest",
    "RABBITMQ": "flipperthedog/rabbitmq:ping",
    "HIVEMQ": "francigjeci/hivemq:dns-image"
}


class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        # Enable forwarding on the router
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT cluster simulation')
    parser.add_argument('-t', '--type', dest='cluster_type', default='rabbitmq',
                        help='broker type (EMQX, RABBITMQ, VERNEMQ, HIVEMQ)')
    parser.add_argument('-d', '--delay', dest='link_delay', default=DELAY,
                        help='delay over a simple link', type=int)
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
        for i in range(2, TOTAL_BROKERS + 2):
            if IP_ADDR + str(200 + i) != cont_address:
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

    for i in range(2, TOTAL_BROKERS + 2):
        if IP_ADDR + str(200 + i) != cont_address:
            d.cmd('echo "{}      {}" >> /etc/hosts'.format(IP_ADDR + str(200 + i), "rabbitmq_" + str(i)))

    return d


def start_hivemq(cont_name, cont_address, bind_ip, master_node):
    source_config_file_path = os.path.join(PWD, 'confiles/config-dns.xml')
    dest_file = "{}/confiles/config-dns_{}.xml".format(PWD, cont_address[-3:])

    __port = 8000

    config_file = ET.parse(source_config_file_path)
    cluster_nodes = config_file.getroot().find('cluster').find('discovery').find('static')
    if cluster_nodes is None:
        raise ModuleNotFoundError('Element not found')
    else:
        # Remove the existing elements
        for node in cluster_nodes:
            cluster_nodes.remove(node)

        # Add all cluster's nodes into config file
        _brokers_index = range(2, TOTAL_BROKERS + 2)
        _brokers_addr = [IP_ADDR + str(200 + _broker_index) for _broker_index in range(2, TOTAL_BROKERS + 2)]
        for broker_addr in _brokers_addr:
            _new_node = ET.Element('node')
            _host = ET.Element('host')
            _host.text = str(broker_addr)
            _port = ET.Element('port')
            _port.text = str(__port)
            _new_node.append(_host)
            _new_node.append(_port)
            cluster_nodes.append(_new_node)

        config_file.write(dest_file)

        return net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                         ports=[1883], port_bindings={1883: bind_ip},
                         dimage=IMAGES["HIVEMQ"],
                         volumes=[
                            PWD + "/confiles/config-dns_{}.xml:/opt/hivemq/conf/config.xml".format(cont_address[-3:])],
                         environment={
                             "HIVEMQ_BIND_ADDRESS": cont_address
                         })


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
    for cnt in range(2, TOTAL_BROKERS + 2):
        container_name = "{}_{}".format(args.cluster_type, cnt)
        local_address = IP_ADDR + str(200 + cnt)
        bind_addr = 1880 + cnt
        if my_master is None:
            my_master = "{}@{}".format(container_name, local_address)

        local_list.append(func(container_name, local_address, bind_addr, my_master))

    return local_list


def run():
    info('\n*** Adding controller')
    net.addController('c0', port=6654)
    info('  DONE\n')

    networks = [ipaddress.ip_network('10.0.{}.0/24'.format(sub_net)) for sub_net in range(TOTAL_BROKERS)]
    info('\nNetwork created: {}'.format(networks))

    info('*** Adding routers\n')
    router_networks = ['{}/24'.format(next(router.hosts())) for router in networks]

    router_list = [net.addHost('r{}'.format(counter), cls=LinuxRouter, ip=router) for counter, router in enumerate(router_networks)]
    print(router_list)

    info('*** Adding switches\n')
    switch_list = [net.addSwitch('s{}'.format(s)) for s in range(TOTAL_BROKERS)]
    print(switch_list)

    info('*** Adding host-switch links\n')
    for count, (s, r, n) in enumerate(zip(switch_list, router_list, router_networks)):
        print(net.addLink(s, r, intfName2='r{}-eth0'.format(count), params2={'ip': n}))

    info('*** Adding router-router links\n')
    # from 0 to all
    net.addLink(router_list[0], router_list[1], intfName1='r0-eth1', intfName2='r1-eth1',
                params1={'ip': '10.10.0.1/24'},
                params2={'ip': '10.10.0.2/24'})
    net.addLink(router_list[0], router_list[2], intfName1='r0-eth2', intfName2='r2-eth1',
                params1={'ip': '10.11.0.1/24'},
                params2={'ip': '10.11.0.2/24'})
    net.addLink(router_list[0], router_list[3], intfName1='r0-eth3', intfName2='r3-eth1',
                params1={'ip': '10.12.0.1/24'},
                params2={'ip': '10.12.0.2/24'})
    net.addLink(router_list[0], router_list[4], intfName1='r0-eth4', intfName2='r4-eth1',
                params1={'ip': '10.13.0.1/24'},
                params2={'ip': '10.13.0.2/24'})

    # from 1 to all
    net.addLink(router_list[1], router_list[2], intfName1='r1-eth2', intfName2='r2-eth2',
                params1={'ip': '10.20.0.1/24'},
                params2={'ip': '10.20.0.2/24'})
    net.addLink(router_list[1], router_list[3], intfName1='r1-eth3', intfName2='r3-eth2',
                params1={'ip': '10.21.0.1/24'},
                params2={'ip': '10.21.0.2/24'})
    net.addLink(router_list[1], router_list[4], intfName1='r1-eth4', intfName2='r4-eth2',
                params1={'ip': '10.22.0.1/24'},
                params2={'ip': '10.22.0.2/24'})

    # from 2 to all
    net.addLink(router_list[2], router_list[3], intfName1='r2-eth3', intfName2='r3-eth3',
                params1={'ip': '10.30.0.1/24'},
                params2={'ip': '10.30.0.2/24'})
    net.addLink(router_list[2], router_list[4], intfName1='r2-eth4', intfName2='r4-eth3',
                params1={'ip': '10.31.0.1/24'},
                params2={'ip': '10.31.0.2/24'})

    # from 3 to 4
    net.addLink(router_list[3], router_list[4], intfName1='r3-eth4', intfName2='r4-eth4',
                params1={'ip': '10.40.0.1/24'},
                params2={'ip': '10.40.0.2/24'})

    info('*** Adding routing\n')
    # router 0
    router_list[0].cmd("ip route add 10.0.1.0/24 via 10.10.0.2 dev r0-eth1")
    router_list[0].cmd("ip route add 10.0.2.0/24 via 10.11.0.2 dev r0-eth2")
    router_list[0].cmd("ip route add 10.0.3.0/24 via 10.12.0.2 dev r0-eth3")
    router_list[0].cmd("ip route add 10.0.4.0/24 via 10.13.0.2 dev r0-eth4")

    # router 1
    router_list[1].cmd("ip route add 10.0.0.0/24 via 10.10.0.1 dev r1-eth1")
    router_list[1].cmd("ip route add 10.0.2.0/24 via 10.20.0.2 dev r1-eth2")
    router_list[1].cmd("ip route add 10.0.3.0/24 via 10.21.0.2 dev r1-eth3")
    router_list[1].cmd("ip route add 10.0.4.0/24 via 10.22.0.2 dev r1-eth4")

    # router 2
    router_list[2].cmd("ip route add 10.0.0.0/24 via 10.11.0.1 dev r2-eth1")
    router_list[2].cmd("ip route add 10.0.1.0/24 via 10.20.0.1 dev r2-eth2")
    router_list[2].cmd("ip route add 10.0.3.0/24 via 10.30.0.2 dev r2-eth3")
    router_list[2].cmd("ip route add 10.0.4.0/24 via 10.31.0.2 dev r2-eth4")

    # router 3
    router_list[3].cmd("ip route add 10.0.0.0/24 via 10.12.0.1 dev r3-eth1")
    router_list[3].cmd("ip route add 10.0.1.0/24 via 10.21.0.1 dev r3-eth2")
    router_list[3].cmd("ip route add 10.0.2.0/24 via 10.30.0.1 dev r3-eth3")
    router_list[3].cmd("ip route add 10.0.4.0/24 via 10.40.0.2 dev r3-eth4")

    # router 4
    router_list[4].cmd("ip route add 10.0.0.0/24 via 10.13.0.1 dev r4-eth1")
    router_list[4].cmd("ip route add 10.0.1.0/24 via 10.22.0.1 dev r4-eth2")
    router_list[4].cmd("ip route add 10.0.2.0/24 via 10.31.0.1 dev r4-eth3")
    router_list[4].cmd("ip route add 10.0.3.0/24 via 10.40.0.1 dev r4-eth4")

    return switch_list


def main(_args):
    info('\n*** Multi containernet generator v{} ***'.format(VERSION))
    info('\nargs:')
    info('\n\tCLUSTER TYPE: {}'.format(args.cluster_type))
    info('\n\tNUMBER OF BROKERS: {}'.format(TOTAL_BROKERS))
    info('\n\tDELAY: {}'.format(args.link_delay))
    info('\n')

    s_list = run()

    info('\n*** Adding docker containers, type: {}\n'.format(_args.cluster_type.upper()))
    container_list = cluster_type(_args.cluster_type.upper())


    info('\n*** Adding container-switch links\n')
    for c, s in zip(container_list, s_list):
        info(net.addLink(c, s, cls=TCLink, delay='{}ms'.format(_args.link_delay / 2), bw=1))

    info('\n*** Starting network\n')
    net.start()
    # net.staticArp()

    info('\n*** Testing connectivity\n')
    net.pingAll()

    # info('\n*** Waiting the network start up ({} secs)...\n'.format(_args.link_delay / 2))
    # time.sleep(_args.link_delay / 2)
    #
    # info('\n*** Starting the entrypoints\n')
    # # START CONTAINERS
    # for c in container_list:
    #     c.start()
    #
    # info('*** Waiting the boot ({} secs)...\n'.format(_args.link_delay))
    # time.sleep(_args.link_delay)

    info('*** Running CLI\n')
    CLI(net)
    info('*** Stopping network')
    net.stop()


if __name__ == "__main__":
    setLogLevel('info')

    net = Containernet(controller=Controller)

    args = arg_parse()

    main(args)

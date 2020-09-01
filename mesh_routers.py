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
import itertools
import os
import time
import xml.etree.ElementTree as ET

PWD = os.getcwd()
VERSION = 1
TOTAL_BROKERS = 5
DELAY = 10
IP_ADDR = '10.0.'
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
    parser.add_argument('-t', '--type', dest='cluster_type', default='emqx',
                        help='broker type (EMQX, RABBITMQ, VERNEMQ, HIVEMQ)')
    parser.add_argument('-d', '--delay-routers', dest='router_delay', default=DELAY,
                        help='delay over a router link', type=int)
    parser.add_argument('-c', '--delay-containers', dest='container_delay', default=DELAY,
                        help='delay over a switch-container link', type=int)

    return parser.parse_args()


def start_emqx(cont_name, cont_address, bind_ip, master_node, default_route):
    return net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                         defaultRoute='via {}'.format(default_route),
                         dimage=IMAGES["EMQX"],
                         ports=[1883], port_bindings={1883: bind_ip},
                         environment={"EMQX_NAME": cont_name,
                                      "EMQX_HOST": cont_address[:-3],
                                      "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                      "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                      "EMQX_CLUSTER__DISCOVERY": "static",
                                      "EMQX_CLUSTER__STATIC__SEEDS": master_node[:-3]
                                      })


def start_rabbitmq(cont_name, cont_address, bind_ip, master_node, default_route):
    dest_file = "{}/confiles/rabbitmq_{}.conf".format(PWD, cont_address[5:-7])
    copyfile(PWD + "/confiles/rabbitmq.conf", dest_file)
    with open(dest_file, "a") as f:
        c = 0
        for i in range(TOTAL_BROKERS):
            _ip = "{}{}.100/24".format(IP_ADDR, i)
            if _ip != cont_address:
                c += 1
                print("cluster_formation.classic_config.nodes.{} = rabbit@rabbitmq_{}\n".format(c, i))
                f.write("cluster_formation.classic_config.nodes.{} = rabbit@rabbitmq_{}\n".format(c, i))

    d = net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                      defaultRoute='via {}'.format(default_route),
                      dimage=IMAGES["RABBITMQ"],
                      ports=[5672, 1883],
                      port_bindings={5672: 5670 + (bind_ip - 1880),
                                     1883: bind_ip},
                      volumes=[
                          "{}:/etc/rabbitmq/rabbitmq.conf".format(dest_file),
                          PWD + "/confiles/enabled_plugins:/etc/rabbitmq/enabled_plugins"],
                      environment={"RABBITMQ_ERLANG_COOKIE": "GPLDKBRJYMSKLTLZQDVG"})

    for i in range(TOTAL_BROKERS):
        _ip = "{}{}.100".format(IP_ADDR, i)
        d.cmd('echo "{}      {}" >> /etc/hosts'.format(_ip, "rabbitmq_" + str(i)))

    return d


def start_hivemq(cont_name, cont_address, bind_ip, master_node, default_route):
    source_config_file_path = os.path.join(PWD, 'confiles/config-dns.xml')
    dest_file = "{}/confiles/config-dns_{}.xml".format(PWD, cont_address[5:-7])

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
        _brokers_index = range(TOTAL_BROKERS)
        _brokers_addr = ["{}{}.100".format(IP_ADDR, _broker_index) for _broker_index in range(TOTAL_BROKERS)]
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
                             defaultRoute='via {}'.format(default_route),
                             ports=[1883], port_bindings={1883: bind_ip},
                             dimage=IMAGES["HIVEMQ"],
                             volumes=[
                                 PWD + "/confiles/config-dns_{}.xml:/opt/hivemq/conf/config.xml".format(
                                     cont_address[5:-7])],
                             environment={
                                 "HIVEMQ_BIND_ADDRESS": cont_address[:-3]
                             })


def start_vernemq(cont_name, cont_address, bind_ip, master_node, default_route):
    return net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                         defaultRoute='via {}'.format(default_route),
                         dimage=IMAGES["VERNEMQ"],
                         ports=[1883], port_bindings={1883: bind_ip},
                         environment={
                             "DOCKER_VERNEMQ_NODENAME": cont_address[:-3],
                             "DOCKER_VERNEMQ_DISCOVERY_NODE": master_node[master_node.index("@") + 1:-3],
                             "DOCKER_VERNEMQ_ACCEPT_EULA": "yes",
                             "DOCKER_VERNEMQ_ALLOW_ANONYMOUS": "on"
                         })


def invalid(broker):
    info('Invalid {}'.format(broker))


def create_containers(argument, router_ips):
    switcher = {
        'EMQX': start_emqx,
        'RABBITMQ': start_rabbitmq,
        'VERNEMQ': start_vernemq,
        'HIVEMQ': start_hivemq
    }
    func = switcher.get(argument, lambda: invalid())

    local_list = []

    my_master = None

    for count, ip in enumerate(router_ips):
        default_route = ip[1].compressed
        print(default_route)
        container_name = "{}_{}".format(args.cluster_type, count)
        local_address = "{}/24".format(ip[100].compressed)
        bind_addr = 1880 + count
        if my_master is None:
            my_master = "{}@{}".format(container_name, local_address)

        local_list.append(func(container_name, local_address, bind_addr, my_master, default_route))

    return local_list


def core_network():
    info('\n*** Adding controller')
    net.addController('c0', port=6654)
    info('  DONE\n')

    networks = [ipaddress.ip_network('10.0.{}.0/24'.format(sub_net)) for sub_net in range(TOTAL_BROKERS)]
    info('\nNetwork created: {}'.format(networks))

    info('*** Adding routers\n')
    router_networks = ['{}/24'.format(next(router.hosts())) for router in networks]

    router_list = [net.addHost('r{}'.format(counter), cls=LinuxRouter, ip=router) for counter, router in
                   enumerate(router_networks)]

    info('*** Adding switches\n')
    switch_list = [net.addSwitch('s{}'.format(s)) for s in range(TOTAL_BROKERS)]

    info('*** Adding router-switch links\n')
    for count, (s, r, n) in enumerate(zip(switch_list, router_list, router_networks)):
        print(net.addLink(s, r, intfName2='r{}-eth0'.format(count), params2={'ip': n}))

    info('*** Adding router-router links\n')
    # from 0 to all
    net.addLink(router_list[0], router_list[1], intfName1='r0-eth1', intfName2='r1-eth1',
                params1={'ip': '10.10.0.1/24'},
                params2={'ip': '10.10.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)
    net.addLink(router_list[0], router_list[2], intfName1='r0-eth2', intfName2='r2-eth1',
                params1={'ip': '10.11.0.1/24'},
                params2={'ip': '10.11.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)
    net.addLink(router_list[0], router_list[3], intfName1='r0-eth3', intfName2='r3-eth1',
                params1={'ip': '10.12.0.1/24'},
                params2={'ip': '10.12.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

    net.addLink(router_list[0], router_list[4], intfName1='r0-eth4', intfName2='r4-eth1',
                params1={'ip': '10.13.0.1/24'},
                params2={'ip': '10.13.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

    # from 1 to all
    net.addLink(router_list[1], router_list[2], intfName1='r1-eth2', intfName2='r2-eth2',
                params1={'ip': '10.20.0.1/24'},
                params2={'ip': '10.20.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

    net.addLink(router_list[1], router_list[3], intfName1='r1-eth3', intfName2='r3-eth2',
                params1={'ip': '10.21.0.1/24'},
                params2={'ip': '10.21.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

    net.addLink(router_list[1], router_list[4], intfName1='r1-eth4', intfName2='r4-eth2',
                params1={'ip': '10.22.0.1/24'},
                params2={'ip': '10.22.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

    # from 2 to all
    net.addLink(router_list[2], router_list[3], intfName1='r2-eth3', intfName2='r3-eth3',
                params1={'ip': '10.30.0.1/24'},
                params2={'ip': '10.30.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

    net.addLink(router_list[2], router_list[4], intfName1='r2-eth4', intfName2='r4-eth3',
                params1={'ip': '10.31.0.1/24'},
                params2={'ip': '10.31.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

    # from 3 to 4
    net.addLink(router_list[3], router_list[4], intfName1='r3-eth4', intfName2='r4-eth4',
                params1={'ip': '10.40.0.1/24'},
                params2={'ip': '10.40.0.2/24'},
                cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1)

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

    return switch_list, networks, router_list


def main():
    info('\n*** Multi containernet generator v{} ***'.format(VERSION))
    info('\nargs:')
    info('\n\tCLUSTER TYPE: {}'.format(args.cluster_type))
    info('\n\tNUMBER OF BROKERS: {}'.format(TOTAL_BROKERS))
    info('\n\tDELAY: router: {} switch: {}'.format(args.router_delay, args.container_delay))
    info('\n')

    s_list, ip_routers, rout_list = core_network()

    info('\n*** Adding docker containers, type: {}\n'.format(args.cluster_type.upper()))
    container_list = create_containers(args.cluster_type.upper(), ip_routers)

    info('\n*** Adding container-switch links\n')
    for c, s in zip(container_list, s_list):
        print(net.addLink(c, s, cls=TCLink, delay='{}ms'.format(args.container_delay)))

    # info('\n*** Adding pub/sub containers\n')
    # middle_switch = [net.addSwitch('middle{}'.format(s)) for s in range(TOTAL_BROKERS)]

    # #creating subs
    sub_list = []
    for indx, ip_addr in enumerate(ip_routers):
        sub = net.addDocker('sub_{}'.format(indx), ip='{}/24'.format(ip_addr[111].compressed),
                            # ip='10.0.0.25{}'.format(indx),
                            dimage='flipperthedog/sub_client:latest')
        sub_list.append(sub)

    # switch sub link
    for sw, sb in zip(s_list, sub_list):
        print(net.addLink(sw, sb))

    # switch - broker link, with a new interface for the broker
    # for indx, (sw, cnt, ip_addr) in enumerate(zip(middle_switch, container_list, ip_routers)):
    #     print(cnt, ip_addr, ip_addr[100].compressed)
    #     print(net.addLink(sw, cnt, intfName2='{}-eth1'.format(cnt), params2={'ip': '{}/24'.format(ip_addr[200].compressed)}))

    info('\n*** Starting network\n')
    net.start()
    # net.staticArp()

    info('\n*** Testing connectivity\n')
    # net.pingAll()
    for sb, cnt in zip(sub_list, container_list):
        net.ping([sb, cnt])

    for pairs in list(itertools.permutations(rout_list + container_list, 2)):
        net.ping(pairs)

    info('\n*** Waiting the network start up ({} secs)...\n'.format(args.router_delay / 2))
    time.sleep(args.router_delay / 2)

    info('\n*** Starting the entrypoints\n')
    # START CONTAINERS
    for c in container_list:
        c.start()

    info('*** Waiting the boot ({} secs)...\n'.format(args.router_delay))
    time.sleep(args.router_delay)

    info('*** Running CLI\n')
    CLI(net)
    info('*** Stopping network')
    net.stop()


if __name__ == "__main__":
    setLogLevel('info')

    net = Containernet(controller=Controller)

    args = arg_parse()

    main()

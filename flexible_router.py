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
import math
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET

PWD = os.getcwd()
VERSION = 2.0
TOTAL_BROKERS = 3
DELAY = 10
BRIDGE_QOS = 2
IP_ADDR = '10.0.'
CPU_VBOX = 6
CPU_ANTLAB = 12
IMAGES = {
    "EMQX": "flipperthedog/emqx-ip:latest",
    "VERNEMQ": "francigjeci/vernemq-debian:latest",
    "RABBITMQ": "flipperthedog/rabbitmq_alpine:latest",
    "HIVEMQ": "francigjeci/hivemq:dns-image",
    # "HIVEMQ":      "flipperthedog/hivemq_alpine:latest",
    "MOSQUITTO": "flipperthedog/mosquitto:latest",
    "SUBSCRIBER": "flipperthedog/alpine_client:latest",
    "PUBLiSHER": "flipperthedog/go_publisher:latest"

}


class MyContainer:
    def __init__(self, _id, cluster_type, router_ip, cpu):
        self.cluster_type = cluster_type
        self.id = _id
        self.name = "{}{}".format(self.cluster_type, self.id)
        self.router_ip = router_ip
        self.default_route = self.router_ip[1].compressed
        self.address = "{}/24".format(self.router_ip[100].compressed)
        self.bind_port = 1880 + self.id
        self.master = "{}@{}".format(self.name, self.address)
        self.cpu = cpu
        self.ram = args.ram_limit

    def get_master(self):
        return self.master

    def set_master(self, new_master):
        self.master = new_master


class MyRouter:
    def __init__(self, _id, networkIP):
        self.id = _id
        self.name = "r{}".format(self.id)
        self.networkIP = networkIP
        self.mainIP = '{}/24'.format(next(self.networkIP.hosts()))
        self.eth_available = ['{}-eth{}'.format(self.name, eth) for eth in range(TOTAL_BROKERS)]
        self.switch = None
        self.eth_used = []
        self.routing_binding = []
        self.router = net.addHost(self.name, cls=LinuxRouter, ip=self.mainIP)

    def get_eth(self):
        eth = self.eth_available.pop(0)
        self.eth_used.append(eth)
        return eth

    def add_binding(self, bind):
        self.routing_binding.append(bind)

    def add_switch(self):
        self.switch = net.addSwitch('s{}'.format(self.id))
        net.addLink(self.switch, self.router,
                    intfName=self.get_eth(),
                    params2={'ip': self.mainIP})
        return self.switch


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
                        help='broker type (EMQX, RABBITMQ, VERNEMQ, HIVEMQ, MOSQUITTO)')
    parser.add_argument('-d', '--delay-routers', dest='router_delay', default=DELAY,
                        help='delay over a router link', type=int)
    parser.add_argument('-c', '--delay-switch', dest='container_delay', default=DELAY,
                        help='delay over a switch-container link', type=int)
    parser.add_argument('-b', '--brokers', dest='num_broker', default=TOTAL_BROKERS,
                        help='cluster size', type=int)
    parser.add_argument('--disable-client', dest='no_clients', default=False,
                        action='store_true', help='exclude clients in the simulation')
    parser.add_argument('--ram-limit', dest='ram_limit', default='',
                        help='ram memory of the brokers')
    parser.add_argument('--cpu', dest='cpu', default=False, action='store_true',
                        help='use 16 cores machine')

    return parser.parse_args()


def start_emqx(container):
    return net.addDocker(hostname=container.name, name=container.name, ip=container.address,
                         defaultRoute='via {}'.format(container.default_route),
                         dimage=IMAGES["EMQX"],
                         ports=[1883], port_bindings={1883: container.bind_port},
                         mem_limit=args.ram_limit,
                         cpuset_cpus=container.cpu,
                         environment={"EMQX_NAME": container.name,
                                      "EMQX_HOST": container.address[:-3],
                                      "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                      "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                      "EMQX_CLUSTER__DISCOVERY": "static",
                                      "EMQX_CLUSTER__STATIC__SEEDS": container.master[:-3]
                                      })


def start_rabbitmq(cont_name, cont_address, bind_ip, master_node, default_route, cpu):
    dest_file = "{}/confiles/rabbitmq{}.conf".format(PWD, cont_address[5:-7])
    copyfile(PWD + "/confiles/rabbitmq.conf", dest_file)
    with open(dest_file, "a") as f:
        c = 0
        for i in range(TOTAL_BROKERS):
            _ip = "{}{}.100/24".format(IP_ADDR, i)
            if _ip != cont_address:
                c += 1
                f.write("cluster_formation.classic_config.nodes.{} = rabbit@rabbitmq{}\n".format(c, i))

    d = net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                      defaultRoute='via {}'.format(default_route),
                      dimage=IMAGES["RABBITMQ"],
                      ports=[5672, 1883],
                      port_bindings={5672: 5670 + (bind_ip - 1880),
                                     1883: bind_ip},
                      volumes=[
                          "{}:/etc/rabbitmq/rabbitmq.conf".format(dest_file),
                          PWD + "/confiles/enabled_plugins:/etc/rabbitmq/enabled_plugins"],
                      mem_limit=args.ram_limit,
                      cpuset_cpus=cpu,
                      environment={"RABBITMQ_ERLANG_COOKIE": "GPLDKBRJYMSKLTLZQDVG"})

    for i in range(TOTAL_BROKERS):
        _ip = "{}{}.100".format(IP_ADDR, i)
        d.cmd('echo "{}      {}" >> /etc/hosts'.format(_ip, "rabbitmq" + str(i)))

    return d


def start_hivemq(cont_name, cont_address, bind_ip, master_node, default_route, cpu):
    my_id = cont_address[5:-7]
    source_config_file_path = os.path.join(PWD, 'confiles/config-dns.xml')
    dest_file = "{}/confiles/config-dns_{}.xml".format(PWD, my_id)

    __port = 8000
    print("bind_ip", bind_ip)
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
        if my_id == 0:
            print("no licence")
            hive_license = ""
        else:
            hive_license = subprocess.check_output("cat {}/confiles/hivemq.lic | base64 -w 0".format(PWD), shell=True)

        return net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                             defaultRoute='via {}'.format(default_route),
                             ports=[1883], port_bindings={1883: bind_ip},
                             dimage=IMAGES["HIVEMQ"],
                             volumes=[
                                 PWD + "/confiles/config-dns_{}.xml:/opt/hivemq/conf/config.xml".format(my_id)],
                             mem_limit=args.ram_limit,
                             cpuset_cpus=cpu,
                             environment={
                                 "HIVEMQ_BIND_ADDRESS": cont_address[:-3],
                                 "HIVEMQ_LICENSE": hive_license
                             })


def start_vernemq(cont_name, cont_address, bind_ip, master_node, default_route, cpu):
    dest_file = "{}/confiles/vernemq{}.conf".format(PWD, cont_address[5:-7])

    with open(dest_file, "w") as f:
        f.write("\naccept_eula=yes")
        f.write("\nallow_anonymous=on\nlog.console=console")
        f.write("\nerlang.distribution.port_range.minimum = 9100")
        f.write("\nerlang.distribution.port_range.maximum = 9109")
        f.write("\nlistener.tcp.default = ###IPADDRESS###:1883")
        f.write("\nlistener.ws.default = ###IPADDRESS###:8080")
        f.write("\nlistener.vmq.clustering = ###IPADDRESS###:44053")
        f.write("\nlistener.http.metrics = ###IPADDRESS###:8888")
        f.write("\n########## End ##########")

    d = net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                      defaultRoute='via {}'.format(default_route),
                      dimage=IMAGES["VERNEMQ"],
                      ports=[1883], port_bindings={1883: bind_ip},
                      mem_limit=args.ram_limit,
                      cpuset_cpus=cpu,
                      volumes=[
                          "{}/confiles/verne_build.sh:/usr/sbin/start_vernemq.sh".format(PWD),
                          "{}:/vernemq/etc/vernemq.conf.local".format(dest_file)],
                      environment={
                          "DOCKER_VERNEMQ_NODENAME": cont_address[:-3],
                          "DOCKER_VERNEMQ_DISCOVERY_NODE": master_node[master_node.index("@") + 1:-3],
                      })

    for i in range(TOTAL_BROKERS):
        _ip = "{}{}.100".format(IP_ADDR, i)
        d.cmd('echo "{}      {}" >> /etc/hosts'.format(_ip, "vernemq" + str(i)))

    return d


def start_mosquitto(cont_name, cont_address, bind_ip, master_node, default_route, cpu):
    dest_file = "{}/confiles/mosquitto{}.conf".format(PWD, cont_address[5:-7])

    with open(dest_file, "w") as f:
        f.write("persistence true\npersistence_location /mosquitto/data/\n")
        f.write("log_dest file /mosquitto/log/mosquitto.log\n")
        f.write("log_dest stdout\nlog_type all")

    if cont_name in master_node:
        print("master master")
        for i in range(TOTAL_BROKERS):
            _ip = "{}{}.100/24".format(IP_ADDR, i)
            if _ip != cont_address:
                with open(dest_file, "a") as f:
                    f.write("\nconnection id_{}\n".format(i))
                    f.write("address {}:{}\n".format(_ip[:-3], 1883))
                    f.write("topic # both {}\n".format(BRIDGE_QOS))
                    f.write("remote_clientid id_{}\n\n".format(i))
                    f.write("keepalive_interval 5")

    return net.addDocker(hostname=cont_name, name=cont_name, ip=cont_address,
                         defaultRoute='via {}'.format(default_route),
                         dimage=IMAGES["MOSQUITTO"],
                         volumes=["{}:/mosquitto/config/mosquitto.conf".format(dest_file)],
                         ports=[1883], port_bindings={1883: bind_ip},
                         mem_limit=args.ram_limit,
                         cpuset_cpus=cpu
                         )


def invalid(broker):
    info('Invalid {}'.format(broker))


def assign_cpu(core_list):
    core_per_broker = math.floor(CORE_NUM / TOTAL_BROKERS)

    this_cpu = []
    for i in range(core_per_broker):
        this_cpu.append(core_list.pop(0))

    return ','.join(map(str, this_cpu))


def create_containers(broker_type, _routers):
    switcher = {
        'emqx': start_emqx,
        'rabbitmq': start_rabbitmq,
        'vernemq': start_vernemq,
        'hivemq': start_hivemq,
        'mosquitto': start_mosquitto
    }

    func = switcher.get(broker_type, lambda: invalid())
    local_list = []
    my_master = None

    for r in _routers:
        container = MyContainer(r.id, broker_type, r.networkIP, assign_cpu(core_list))
        if my_master is None:
            my_master = container.get_master()
        else:
            container.set_master(my_master)

        local_list.append(func(container))

    return local_list


def core_network():
    info('\n*** Adding controller')
    net.addController('c0', port=6654)
    info('  DONE\n')

    info('*** Adding routers\n')
    _routers = [MyRouter(_id=brok, networkIP=ipaddress.ip_network('10.0.{}.0/24'.format(brok)))
                for brok in range(TOTAL_BROKERS)]

    info('*** Adding switches\n')
    _switches = [r.add_switch() for r in _routers]

    info('*** Adding router-router links\n')
    for (router1, router2) in list(itertools.combinations(_routers, 2)):
        intf_name1 = router1.get_eth()
        intf_name2 = router2.get_eth()
        params1 = '10.{}.0.1'.format(int(''.join(sorted(str(e) for e in [router1.id, router2.id]))), reverse=True)
        params2 = '10.{}.0.2'.format(int(''.join(sorted(str(e) for e in [router1.id, router2.id]))), reverse=True)

        router1.add_binding((router2.networkIP, params2, intf_name1))
        router2.add_binding((router1.networkIP, params1, intf_name2))

        net.addLink(router1.router, router2.router,
                    intfName1=intf_name1,
                    intfName2=intf_name2,
                    params1={'ip': '{}/24'.format(params1)},
                    params2={'ip': '{}/24'.format(params2)},
                    cls=TCLink, delay='{}ms'.format(args.router_delay / 2), bw=1
                    )

    info('*** Adding routing\n')
    _cmd = "ip route add {to_reach} via {host} dev {eth_int}"
    for r in _routers:
        for bind in r.routing_binding:
            r.router.cmd(_cmd.format(to_reach=bind[0], host=bind[1], eth_int=bind[2]))

    return _switches, _routers


def main():
    info('\n*** Multi containernet generator v{} ***'.format(VERSION))
    info('\nargs:')
    info('\n\tCLUSTER TYPE: {}'.format(args.cluster_type))
    info('\n\tNUMBER OF BROKERS: {}'.format(TOTAL_BROKERS))
    info('\n\tDELAY: router: {} switch: {}'.format(args.router_delay, args.container_delay))
    info('\n\tCORE: {}'.format(CORE_NUM))
    info('\n')

    switches, routers = core_network()
    ip_routers = [r.networkIP for r in routers]
    router_list = [r.router for r in routers]

    info('\n*** Adding docker containers, type: {}\n'.format(args.cluster_type.upper()))
    container_list = create_containers(args.cluster_type.lower(), routers)

    info('\n*** Adding container-switch links\n')
    for c, s in zip(container_list, switches):
        print(net.addLink(c, s, cls=TCLink, delay='{}ms'.format(args.container_delay)))

    # Creating subs
    if not args.no_clients:
        info('\n*** Adding subscribers\n')
        sub_list = []
        for indx, ip_addr in enumerate(ip_routers):
            sub = net.addDocker('sub{}'.format(indx), ip='{}/24'.format(ip_addr[111].compressed),
                                dimage=IMAGES["SUBSCRIBER"],
                                volumes=[PWD + '/experiments:/home/ubuntu/experiments'])
            sub_list.append(sub)

        # switch sub link
        for sw, sb in zip(switches, sub_list):
            print(net.addLink(sw, sb))

        info('\n*** Adding publishers\n')
        pub_list = []
        for indx, ip_addr in enumerate(ip_routers):
            pub = net.addDocker('pub{}'.format(indx), ip='{}/24'.format(ip_addr[112].compressed),
                                dimage=IMAGES["PUBLiSHER"],
                                volumes=[PWD + '/experiments:/go/src/app/experiments'])
            pub_list.append(pub)

        # switch pub link
        for sw, pb in zip(switches, pub_list):
            print(net.addLink(sw, pb))

    info('\n*** Starting network\n')
    net.start()

    info('\n*** Testing connectivity\n')
    if args.no_clients:
        net.pingAll()
    else:
        for sb, cnt in zip(sub_list, container_list):
            net.ping([sb, cnt])

        for pb, cnt in zip(pub_list, container_list):
            net.ping([pb, cnt])

        for pairs in list(itertools.permutations(router_list + container_list, 2)):
            net.ping(pairs)

    info('\n*** Waiting the network start up ({} secs)...\n'.format(args.router_delay / 2))
    time.sleep(args.router_delay / 2)

    info('\n killing net')
    for c in container_list:
        c.cmd("ip link set eth0 down")

    if not args.no_clients:
        for s, p in zip(sub_list, pub_list):
            s.cmd("ip link set eth0 down")
            p.cmd("ip link set eth0 down")

    info('\n*** Starting the entrypoints\n')
    # START CONTAINERS
    [c.start() for c in container_list]

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
    TOTAL_BROKERS = args.num_broker
    CORE_NUM = CPU_ANTLAB if args.cpu else CPU_VBOX
    core_list = list(range(0, CORE_NUM))

    main()

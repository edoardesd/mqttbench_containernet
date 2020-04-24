#!/usr/bin/python

"""
linuxrouter.py: Example network with Linux IP router

This example converts a Node into a router using IP forwarding
already built into Linux.

The example topology creates a router and three IP subnets:

    - 192.168.1.0/24 (r0-eth1, IP: 192.168.1.1)
    - 172.16.0.0/12 (r0-eth2, IP: 172.16.0.1)
    - 10.0.0.0/8 (r0-eth3, IP: 10.0.0.1)

Each subnet consists of a single host connected to
a single switch:

    r0-eth1 - s1-eth1 - h1-eth0 (IP: 192.168.1.100)
    r0-eth2 - s2-eth1 - h2-eth0 (IP: 172.16.0.100)
    r0-eth3 - s3-eth1 - h3-eth0 (IP: 10.0.0.100)

The example relies on default routing entries that are
automatically created for each router interface, as well
as 'defaultRoute' parameters for the host interfaces.

Additional routes may be added to the router or hosts by
executing 'ip route' or 'route' commands on the router or hosts.
"""

from mininet.topo import Topo
from mininet.net import Containernet
from mininet.node import Controller
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink


IMAGE_NAME = "flipperthedog/emqx-ip"


class LinuxRouter( Node ):
    "A Node with IP forwarding enabled."

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()



def run():
    "Test linux router"
    net = Containernet ( controller=Controller )  # controller is used by s1-s3
    net.addController('c0', port=6654)

    defaultIP = '10.0.0.1/24'  # IP address for r0-eth1
    info('*** Adding routers\n')
    r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.0.1/24')
    r2 = net.addHost('r2', cls=LinuxRouter, ip='10.1.0.1/24')
    r3 = net.addHost('r3', cls=LinuxRouter, ip='10.2.0.1/24')

    info('*** Adding switches\n')
    s1, s2, s3 = [net.addSwitch(s) for s in ('s1', 's2', 's3')]

    info('*** Adding host-switch links\n')
    net.addLink(s1, r1, intfName2='r1-eth1',
                 params2={'ip': '10.0.0.1/24'})

    net.addLink(s2, r2, intfName2='r2-eth1',
                 params2={'ip': '10.1.0.1/24'})

    net.addLink(s3, r3, intfName2='r3-eth1',
                 params2={'ip': '10.2.0.1/24'})

    info('*** 1) Adding switch-switch link\n')
    net.addLink(r1, r2, intfName1='r1-eth2', intfName2='r2-eth2', params1={'ip': '10.1.0.1/24'}, params2={'ip': '10.0.0.1/24'})
    info('*** 2) Adding switch-switch link\n')
    net.addLink(r2, r3, intfName1='r2-eth3', intfName2='r3-eth2', params1={'ip': '10.2.0.1/24'}, params2={'ip': '10.1.0.1/24'})
    info('*** 3) Adding switch-switch link\n')
    net.addLink(r1, r3, intfName1='r1-eth3', intfName2='r3-eth3', params1={'ip': '10.2.0.1/24'}, params2={'ip': '10.0.0.1/24'})

    d1 = net.addDocker(name='d1', ip='10.0.0.251/24', defaultRoute='via 10.0.0.1', ports=[1883], port_bindings={1883: 1883}, dimage=IMAGE_NAME,
                   environment={"EMQX_NAME": "docker1",
                                "EMQX_HOST": "10.0.0.251",
                                "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                "EMQX_CLUSTER__DISCOVERY": "static",
                                "EMQX_CLUSTER__STATIC__SEEDS": "docker2@10.1.0.252"})

    d2 = net.addDocker(name='d2', ip='10.1.0.252/24', defaultRoute='via 10.1.0.1', ports=[1883], port_bindings={1883: 1884}, dimage=IMAGE_NAME,
                       environment={"EMQX_NAME": "docker2",
                                    "EMQX_HOST": "10.1.0.252",
                                    "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                    "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                    "EMQX_CLUSTER__DISCOVERY": "static",
                                    "EMQX_CLUSTER__STATIC__SEEDS": "docker1@10.0.0.251"})

    d3 = net.addDocker(name='d3', ip='10.2.0.253/24', defaultRoute='via 10.2.0.1', ports=[1883],
                       port_bindings={1883: 1885}, dimage=IMAGE_NAME,
                       environment={"EMQX_NAME": "docker3",
                                    "EMQX_HOST": "10.2.0.253",
                                    "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                    "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                    "EMQX_CLUSTER__DISCOVERY": "static",
                                    "EMQX_CLUSTER__STATIC__SEEDS": "docker1@10.0.0.251"})

    for d, s in [(d1, s1), (d2, s2), (d3, s3)]:
        info(net.addLink(d, s, cls=TCLink, delay='10ms'))

    # info(net.addLink(d1, s1, cls=TCLink, delay='10ms', intfName2='d1-eth1'))
    # info(net.addLink(d2, s2, cls=TCLink, delay='10ms', intfName2='d2-eth1'))
    # info(net.addLink(d3, s3, cls=TCLink, delay='10ms', intfName2='d3-eth1'))

    info('*** Starting network\n')
    net.start()
    net.staticArp()

    info('*** Routing Table on Router:\n')
    print((net['r1'].cmd('route')))

    info('*** Routing Table on Router:\n')
    print((net['r2'].cmd('route')))

    info('*** Routing Table on Router:\n')
    print((net['r3'].cmd('route')))

    info('*** Testing connectivity\n')
    net.pingAll()

    info('*** Starting brokers\n')
    # d1.start()
    # d2.start()
    # d3.start()

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    run()

#!/usr/bin/python

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
    # r3 = net.addHost('r3', cls=LinuxRouter, ip='10.2.0.1/24')

    info('*** Adding switches\n')
    s1, s2, s3 = [net.addSwitch(s) for s in ('s1', 's2', 's3')]

    info('*** Adding host-switch links\n')
    net.addLink(s1, r1, intfName2='r1-eth1',
                 params2={'ip': '10.0.0.1/24'})

    net.addLink(s2, r2, intfName2='r2-eth1',
                 params2={'ip': '10.1.0.1/24'})

    # net.addLink(s3, r3, intfName2='r3-eth1',
    #              params2={'ip': '10.2.0.1/24'})

    info('*** 1) Adding switch-switch link\n')
    net.addLink(r1, r2, intfName1='r1-eth2', intfName2='r2-eth2', params1={'ip': '10.100.0.1/24'},
                params2={'ip': '10.100.0.2/24'})
    # net.addLink(r1, r2, intfName1='r1-eth2', intfName2='r2-eth2', params1={'ip': '10.100.0.1/24'}, params2={'ip': '10.100.0.2/24'})
    # info('*** 2) Adding switch-switch link\n')
    # net.addLink(r2, r3, intfName1='r2-eth3', intfName2='r3-eth2', params1={'ip': '10.2.0.1/24'},
    #             params2={'ip': '10.1.0.1/24'})
    # net.addLink(r2, r3, intfName1='r2-eth3', intfName2='r3-eth2', params1={'ip': '10.200.0.1/24'}, params2={'ip': '10.200.0.2/24'})
    # info('*** 3) Adding switch-switch link\n')
    # info('*** 3) Adding switch-switch link\n')
    # net.addLink(r1, r3, intfName1='r1-eth3', intfName2='r3-eth3', params1={'ip': '10.2.0.1/24'},
    #             params2={'ip': '10.0.0.1/24'})
    # net.addLink(r1, r3, intfName1='r1-eth3', intfName2='r3-eth3', params1={'ip': '10.300.0.1/24'}, params2={'ip': '10.300.0.2/24'})

    r1.cmd("ip route add 10.1.0.0/24 via 10.100.0.1")
    r2.cmd("ip route add 10.0.0.0/24 via 10.100.0.2")
    r1.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    r2.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    #
    # r2.cmd("ip route add 10.2.0.0/24 via 10.200.0.1")
    # r3.cmd("ip route add 10.1.0.0/24 via 10.200.0.2")
    #
    # r1.cmd("ip route add 10.2.0.0/24 via 10.300.0.1")
    # r3.cmd("ip route add 10.0.0.0/24 via 10.300.0.2")


    d1 = net.addHost(name='d1', ip='10.0.0.251/24', defaultRoute='via 10.0.0.1')
    d2 = net.addHost(name='d2', ip='10.1.0.252/24', defaultRoute='via 10.1.0.1')
    # d3 = net.addHost(name='d3', ip='10.3.0.253/24', defaultRoute='via 10.2.0.1')
    # d1 = net.addDocker(name='d1', ip='10.0.0.251/24', defaultRoute='via 10.0.0.1', ports=[1883], port_bindings={1883: 1883}, dimage=IMAGE_NAME,
    #                environment={"EMQX_NAME": "docker1",
    #                             "EMQX_HOST": "10.0.0.251",
    #                             "EMQX_NODE__DIST_LISTEN_MAX": 6379,
    #                             "EMQX_LISTENER__TCP__EXTERNAL": 1883,
    #                             "EMQX_CLUSTER__DISCOVERY": "static",
    #                             "EMQX_CLUSTER__STATIC__SEEDS": "docker2@10.1.0.252"})
    #
    # d2 = net.addDocker(name='d2', ip='10.1.0.252/24', defaultRoute='via 10.1.0.1', ports=[1883], port_bindings={1883: 1884}, dimage=IMAGE_NAME,
    #                    environment={"EMQX_NAME": "docker2",
    #                                 "EMQX_HOST": "10.1.0.252",
    #                                 "EMQX_NODE__DIST_LISTEN_MAX": 6379,
    #                                 "EMQX_LISTENER__TCP__EXTERNAL": 1883,
    #                                 "EMQX_CLUSTER__DISCOVERY": "static",
    #                                 "EMQX_CLUSTER__STATIC__SEEDS": "docker1@10.0.0.251"})
    #
    # d3 = net.addDocker(name='d3', ip='10.2.0.253/24', defaultRoute='via 10.2.0.1', ports=[1883],
    #                    port_bindings={1883: 1885}, dimage=IMAGE_NAME,
    #                    environment={"EMQX_NAME": "docker3",
    #                                 "EMQX_HOST": "10.2.0.253",
    #                                 "EMQX_NODE__DIST_LISTEN_MAX": 6379,
    #                                 "EMQX_LISTENER__TCP__EXTERNAL": 1883,
    #                                 "EMQX_CLUSTER__DISCOVERY": "static",
    #                                 "EMQX_CLUSTER__STATIC__SEEDS": "docker1@10.0.0.251"})

    for d, s in [(d1, s1), (d2, s2)]:
        info(net.addLink(d, s))

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

    # info('*** Routing Table on Router:\n')
    # print((net['r3'].cmd('route')))

    info('*** Testing connectivity\n')
    net.pingAll()
    # net.ping([r1, r2])
    info('*** Starting brokers\n')
    # d1.start()
    # d2.start()
    # d3.start()

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    run()

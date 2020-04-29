#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Containernet
from mininet.node import Controller
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink

IMAGE_NAME = "flipperthedog/emqx-ip"


class LinuxRouter(Node):
    "A Node with IP forwarding enabled."

    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        # Enable forwarding on the router
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


def run():
    net = Containernet(controller=Controller)
    net.addController('c0', port=6654)

    info('*** Adding routers\n')
    r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.0.1/24')
    r2 = net.addHost('r2', cls=LinuxRouter, ip='10.1.0.1/24')

    info('*** Adding switches\n')
    s1, s2 = [net.addSwitch(s) for s in ('s1', 's2')]

    info('*** Adding host-switch links\n')
    net.addLink(s1, r1, intfName2='r1-eth1',
                params2={'ip': '10.0.0.1/24'})

    net.addLink(s2, r2, intfName2='r2-eth1',
                params2={'ip': '10.1.0.1/24'})

    info('*** Adding switch-switch link\n')
    net.addLink(r1, r2, intfName1='r1-eth2', intfName2='r2-eth2', params1={'ip': '10.100.0.1/24'},
                params2={'ip': '10.100.0.2/24'})

    info('*** Adding routing\n')
    # r1.cmd("ip route add 10.1.0.0/24 via 10.100.0.1")
    # r2.cmd("ip route add 10.0.0.0/24 via 10.100.0.2")
    r1.cmd("ip route add 10.1.0.0/24 via 10.100.0.2 dev r1-eth2")
    r2.cmd("ip route add 10.0.0.0/24 via 10.100.0.1 dev r2-eth2")

    info('*** Adding hosts\n')
    d1 = net.addHost(name='d1', ip='10.0.0.251/24', defaultRoute='via 10.0.0.1')
    d2 = net.addHost(name='d2', ip='10.1.0.252/24', defaultRoute='via 10.1.0.1')

    info('*** Adding host-switch link\n')
    for d, s in [(d1, s1), (d2, s2)]:
        info(net.addLink(d, s))

    info('*** Starting network\n')
    net.start()
    net.staticArp()

    info('*** Routing Table on Router:\n')
    print((net['r1'].cmd('route')))

    info('*** Routing Table on Router:\n')
    print((net['r2'].cmd('route')))

    info('*** Testing connectivity\n')
    net.pingAll()

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()



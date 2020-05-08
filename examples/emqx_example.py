"""
Example topology with two containers (d1, d2),
two switches, and one controller:

          - (c)-
         |      |
(d1) - (s1) - (s2) - (d2)
"""

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.node import Node
from mininet.link import TCLink
from mininet.log import info, error, setLogLevel
import docker
import os
import time
setLogLevel('info')

PWD = os.getcwd()
SIM_NAME = "EMQX"
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



net = Containernet(controller=Controller)

info('*** Adding controller\n')
net.addController('c0', port=6654)

info('*** Adding Router\n')
defaultIP = '172.17.0.0/24'  # IP address for r0-eth1
router = net.addNode('r0', cls=LinuxRouter, ip=defaultIP)

info('*** Adding docker containers using {} images\n'.format(IMAGE_NAME))

# port bindings is swapped (host_machine:docker_container)
d1 = net.addDocker(name='d1', ip='10.0.0.251', ports=[1883], port_bindings={1883: 1883}, dimage=IMAGE_NAME,
                   environment={"EMQX_NAME": "docker1",
                                "EMQX_HOST": "10.0.0.251",
                                "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                "EMQX_CLUSTER__DISCOVERY": "static",
                                "EMQX_CLUSTER__STATIC__SEEDS": "docker2@10.0.0.252"})

d2 = net.addDocker(name='d2', ip='10.0.0.252', ports=[1883], port_bindings={1883: 1884}, dimage=IMAGE_NAME,
                   environment={"EMQX_NAME": "docker2",
                                "EMQX_HOST": "10.0.0.252",
                                "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                "EMQX_CLUSTER__DISCOVERY": "static",
                                "EMQX_CLUSTER__STATIC__SEEDS": "docker1@10.0.0.251"})

d3 = net.addDocker(name='d3', ip='10.0.0.253', ports=[1883], port_bindings={1883: 1885}, dimage=IMAGE_NAME,
                   environment={"EMQX_NAME": "docker3",
                                "EMQX_HOST": "10.0.0.253",
                                "EMQX_NODE__DIST_LISTEN_MAX": 6379,
                                "EMQX_LISTENER__TCP__EXTERNAL": 1883,
                                "EMQX_CLUSTER__DISCOVERY": "static",
                                "EMQX_CLUSTER__STATIC__SEEDS": "docker1@10.0.0.251"})

info('*** Adding switches\n')
s1 = net.addSwitch('s1')

info('*** Creating links\n')
net.addLink(d1, s1, cls=TCLink, delay='50ms', bw=1)
net.addLink(d2, s1, cls=TCLink, delay='50ms', bw=1)
net.addLink(d3, s1, cls=TCLink, delay='50ms', bw=1)
# net.addLink(s1, s2, cls=TCLink, delay='50ms', bw=1)
# net.addLink(s2, d2)
# net.addLink(s2, d3)

info('*** Starting network\n')
net.start()
# net.staticArp()

info('*** Testing connectivity\n')
net.pingall()
# net.ping([d1, d3])
# net.ping([d3, d2])



info('*** Running CLI\n')
CLI(net)
info('*** Stopping network')
net.stop()

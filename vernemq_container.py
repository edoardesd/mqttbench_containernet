"""
Example topology with two containers (d1, d2),
two switches, and one controller:

          - (c)-
         |      |
(d1) - (s1) - (s2) - (d2)
"""
import threading
import time

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, error, setLogLevel
import docker
import shlex
import subprocess
import os

SIM_NAME = "VERNEMQ"

PWD = os.getcwd()

setLogLevel('info')

image_name = "francigjeci/vernemq-debian:latest"

net = Containernet(controller=Controller)

cmd = "start_vernemq"

info('*** Adding controller\n')
net.addController('c0', port=6654)

info('*** Adding docker containers using {} images\n'.format(image_name))
# port bindings is swapped (host_machine:docker_container)
d1 = net.addDocker(hostname="vernemq1", name='d1', ip='10.0.0.251', dimage=image_name,
                   environment={
                        "DOCKER_VERNEMQ_NODENAME": "10.0.0.251",
                        "DOCKER_VERNEMQ_DISCOVERY_NODE": "10.0.0.252",
                        "DOCKER_VERNEMQ_ACCEPT_EULA": "yes",
                        "DOCKER_VERNEMQ_ALLOW_ANONYMOUS": "on"
                   })

d2 = net.addDocker(hostname="vernemq2", name='d2', ip='10.0.0.252', dimage=image_name,
                   environment={
                                "DOCKER_VERNEMQ_NODENAME": "10.0.0.252",
                                "DOCKER_VERNEMQ_DISCOVERY_NODE": "10.0.0.251",
                                "DOCKER_VERNEMQ_ACCEPT_EULA": "yes",
                                "DOCKER_VERNEMQ_ALLOW_ANONYMOUS": "on"
                                })

info('*** Adding switches\n')
s1 = net.addSwitch('vs1')
s2 = net.addSwitch('vs2')

info('*** Creating links\n')
net.addLink(d1, s1)
net.addLink(s1, s2, cls=TCLink, delay='50ms', bw=1)
net.addLink(s2, d2)

info('*** Starting network\n')
net.start()
net.staticArp()

info('*** Testing connectivity\n')
net.ping([d1, d2])

info('*** Waiting 5 seconds\n')
time.sleep(5)

info('*** Starting the entrypoints\n')
d1.start()
d2.start()


info('*** Running CLI\n')
CLI(net)

info('*** Stopping network')
net.stop()
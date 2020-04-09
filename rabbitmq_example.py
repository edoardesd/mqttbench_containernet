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
from mininet.link import TCLink
from mininet.log import info, error, setLogLevel
import docker
import shlex
import subprocess
import time
import os

SIM_NAME = "RABBITMQ"
PWD = os.getcwd()
setLogLevel('info')
image_name = "flipperthedog/rabbitmq:ping"


def check_cluster():
    broker_out = ""
    iteration = 1
    while "rabbit@d2" not in broker_out:
        broker_out = d1.cmd("rabbitmqctl cluster_status")
        info('{}) Waiting cluster start...\n'.format(iteration))
        iteration += 1



net = Containernet(controller=Controller)

info('*** Adding controller\n')
net.addController('c0', port=6654)

info('*** Adding docker containers using {} images\n'.format(image_name))

# HOSTS
# port bindings is swapped (host_machine:docker_container)
d1 = net.addDocker(hostname="rabbit1", name='d1', ip='10.0.0.251', dimage=image_name,
                   port_bindings={5672: 5672},
                   volumes=[PWD + "/rabbitmq1.conf:/etc/rabbitmq/rabbitmq.conf"],
                   environment={"RABBITMQ_ERLANG_COOKIE": "GPLDKBRJYMSKLTLZQDVG"})

d1.cmd('echo "10.0.0.252      d2" >> /etc/hosts')

d2 = net.addDocker(hostname="rabbit2", name='d2', ip='10.0.0.252', dimage=image_name,
                   port_bindings={5672: 5673},
                   volumes=[PWD + "/rabbitmq2.conf:/etc/rabbitmq/rabbitmq.conf"],
                   environment={"RABBITMQ_ERLANG_COOKIE": "GPLDKBRJYMSKLTLZQDVG"})

d2.cmd('echo "10.0.0.251      d1" >> /etc/hosts')


info('*** Adding switches\n')
# SWITCHES
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')

info('*** Creating links\n')
# LINKS
net.addLink(d1, s1)
net.addLink(s1, s2, cls=TCLink, delay='50ms', bw=1)
net.addLink(s2, d2)

info('*** Starting network\n')
net.start()
net.staticArp()

info('*** Testing connectivity\n')
net.ping([d1, d2])

info('*** Waiting network start up...\n')
time.sleep(5)

info('*** Starting the entrypoints\n')
# START CONTAINERS
d1.start()
d2.start()

info('*** Waiting boot (10 secs)...\n')
time.sleep(10)

# Check correct cluster configuration
check_cluster()
# It starts after 10 cycles
info('*** Cluster created\n')

info('*** Running CLI\n')
CLI(net)
info('*** Stopping network')
net.stop()
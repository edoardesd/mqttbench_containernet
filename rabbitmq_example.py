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
import os

SIM_NAME = "RABBITMQ"

PWD = os.getcwd()

setLogLevel('info')
image_name = "flipperthedog/rabbitmq:ping"
entrypoint_sh = "docker-entrypoint.sh rabbitmq-server"
cmd = "rabbitmq-server"
net = Containernet(controller=Controller)

info('*** Adding controller\n')
net.addController('c0', port=6654)

info('*** Adding docker containers using {} images\n'.format(image_name))

#port bindings is swapped (host_machine:docker_container)
d1 = net.addDocker(hostname="rabbit1", name='d1', ip='10.0.0.251', dimage=image_name, 
		volumes=[PWD+"/rabbitmq1.conf:/etc/rabbitmq/rabbitmq.conf"],
		environment={"RABBITMQ_ERLANG_COOKIE":"GPLDKBRJYMSKLTLZQDVG"})

d1.cmd('echo "172.17.0.3      d2" >> /etc/hosts')

d2 = net.addDocker(hostname="rabbit2", name='d2', ip='10.0.0.252', dimage=image_name, 
		volumes=[PWD+"/rabbitmq2.conf:/etc/rabbitmq/rabbitmq.conf"],
		environment={"RABBITMQ_ERLANG_COOKIE":"GPLDKBRJYMSKLTLZQDVG"})

d2.cmd('echo "172.17.0.2      d1" >> /etc/hosts')

info('*** Starting {}\n'.format(SIM_NAME))
client = docker.from_env()

d1_entry_out = client.containers.get('mn.d1').exec_run(entrypoint_sh, stdout=False, stderr=False)
info('*** Running entrypoint for mn.d1, {}\n'.format(d1_entry_out))

d2_entry_out = client.containers.get('mn.d2').exec_run(entrypoint_sh, stdout=False, stderr=False)
info('*** Running entrypoint for mn.d2, {}\n'.format(d2_entry_out))

info('*** Adding switches\n')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')

info('*** Creating links\n')
net.addLink(d1, s1)
net.addLink(s1, s2, cls=TCLink, delay='50ms', bw=1)
net.addLink(s2, d2)

info('*** Starting network\n')
net.start()

info('*** Testing connectivity\n')
net.ping([d1, d2])

info('*** Running CLI\n')
CLI(net)
info('*** Stopping network')
net.stop()

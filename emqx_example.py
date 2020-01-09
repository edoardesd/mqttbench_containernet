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

SIM_NAME = "EMQX"

setLogLevel('info')
image_name = "flipperthedog/emqx-bash"
docker_cmd = "docker exec -it mn.d{} /opt/emqx/bin/emqx start"
cmd = "/opt/emqx/bin/emqx start"
entrypoint_sh = "/usr/bin/docker-entrypoint.sh" 
start_sh = "/usr/bin/start.sh"

net = Containernet(controller=Controller)

info('*** Adding controller\n')
net.addController('c0', port=6654)

info('*** Adding docker containers using {} images\n'.format(image_name))

#port bindings is swapped (host_machine:docker_container)
d1 = net.addDocker(name='d1', ip='10.0.0.251', ports=[1883], port_bindings={1883: 1883}, dimage=image_name, 
		environment={"EMQX_NAME": "docker1",
			     "EMQX_NODE__DIST_LISTEN_MAX": 6379,
			     "EMQX_LISTENER__TCP__EXTERNAL": 1883,
			     "EMQX_CLUSTER__DISCOVERY": "static",
			     "EMQX_CLUSTER__STATIC__SEEDS": "docker2@172.17.0.3"})

d2 = net.addDocker(name='d2', ip='10.0.0.252', ports=[1883], port_bindings={1883: 1884}, dimage=image_name, 
		environment={"EMQX_NAME":"docker2",
			     "EMQX_NODE__DIST_LISTEN_MAX": 6379,
			     "EMQX_LISTENER__TCP__EXTERNAL": 1883,
			     "EMQX_CLUSTER__DISCOVERY": "static",
			     "EMQX_CLUSTER__STATIC__SEEDS":
			     "docker1@172.17.0.2"})

info('*** Starting {}\n'.format(SIM_NAME))
client = docker.from_env()

d1_out = client.containers.get('mn.d1').exec_run(entrypoint_sh, stdout=True, stderr=True)
info(d1_out, '\n')
d1_bis = client.containers.get('mn.d1').exec_run(cmd, stdout=True, stderr=True)
info(d1_bis, '\n')
#try: 
#	info(d1_out.output.decode('utf-8'))
#except AttributeError as e:
#	error(e, d1_out)

d2_out = client.containers.get('mn.d2').exec_run(entrypoint_sh, stdout=True, stderr=True)
info(d2_out, '\n')
d2_bis = client.containers.get('mn.d2').exec_run(cmd, stdout=True, stderr=True)
info(d2_bis, '\n')
#try:
#	info(d2_out.output.decode('utf-8'))
#except AttributeError as e:
#	error(e, d1_out)
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

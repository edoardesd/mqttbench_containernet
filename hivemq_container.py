"""
Example topology with two containers (d1, d2),
two switches, and one controller:

          - (c)-
         |      |
(d1) - (s1) - (s2) - (d2)
"""
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

# import the threading to create the thread for the renning of the docker brokers
import threading

SIM_NAME = "HIVEMQ"

setLogLevel('info')

PWD = os.getcwd()  # needed to get the directory of this file in order to get the config file and insert it inside the config file of the docker itself

# image_name = "hivemq/hivemq4:latest"
image_name = "hivemq/hivemq4:dns-image"
entrypoint_sh = "/opt/pre-entry.sh"
cmd = "/opt/hivemq/bin/run.sh"

net = Containernet(controller=Controller)
info('*** Adding controller\n')
net.addController('c0', port=6654)

info('*** Adding docker containers using {} images\n'.format(image_name))

# port bindings is swapped (host_machine:docker_container)
d1 = net.addDocker(hostname="hivemq1", name='d1',  dimage=image_name,
                    ip='10.0.0.251',
                   #ports=[1883],
                   port_bindings={1883: 1883}, # 1883
                   volumes=[PWD + "/config-dns_1.xml:/opt/hivemq/conf/config.xml"],
                   # environment={"HIVEMQ_BIND_ADDRESS": "172.17.0.2"}
                   environment={"HIVEMQ_BIND_ADDRESS": "10.0.0.251",
                   #              # "HIVE_CLUSTER_PORT":"1883"
                                }
                   )

d2 = net.addDocker(hostname="hivemq2", name='d2',  dimage=image_name,
                    ip='10.0.0.252',
                   #ports=[1883],
                   port_bindings={1883: 1884}, # 1884
                   volumes=[PWD + "/config-dns_2.xml:/opt/hivemq/conf/config.xml"],
                   # environment={"HIVEMQ_BIND_ADDRESS": "172.17.0.3"}
                   environment={"HIVEMQ_BIND_ADDRESS": "10.0.0.252",
                   #              # "HIVE_CLUSTER_PORT": "1883"
                                }
                   )

d3 = net.addDocker(hostname="hivemq3", name='d3',  dimage=image_name,
                    ip='10.0.0.253',
                   #ports=[1883],
                   port_bindings={1883: 1885}, #  1885
                   volumes=[PWD + "/config-dns_3.xml:/opt/hivemq/conf/config.xml"],
                   # environment={"HIVEMQ_BIND_ADDRESS": "172.17.0.4"}
                   environment={"HIVEMQ_BIND_ADDRESS": "10.0.0.253",
                   #              # "HIVE_CLUSTER_PORT": "1883"
                                }
                   )

info('*** Starting {}\n'.format(SIM_NAME))
client = docker.from_env()

d1_entry_out = client.containers.get('mn.d1').exec_run(entrypoint_sh, stdout=False, stderr=False)
info('*** Running entrypoint for mn.d1, {}\n'.format(d1_entry_out))

d2_entry_out = client.containers.get('mn.d2').exec_run(entrypoint_sh, stdout=False, stderr=False)
info('*** Running entrypoint for mn.d2, {}\n'.format(d2_entry_out))

d3_entry_out = client.containers.get('mn.d3').exec_run(entrypoint_sh, stdout=False, stderr=False)
info('*** Running entrypoint for mn.d3, {}\n'.format(d3_entry_out))


d1_running_thread = threading.Thread(target=client.containers.get('mn.d1').exec_run, args=(cmd,), kwargs={'stdout':True, 'stderr':True})
d1_running_thread.start()
d2_running_thread = threading.Thread(target=client.containers.get('mn.d2').exec_run, args=(cmd,), kwargs={'stdout':True, 'stderr':True})
d2_running_thread.start()
d3_running_thread = threading.Thread(target=client.containers.get('mn.d3').exec_run, args=(cmd,), kwargs={'stdout':True, 'stderr':True})
d3_running_thread.start()
# d1_out = client.containers.get('mn.d1').exec_run(cmd, stdout=True, stderr=True)
# info(d1_out, '\n')
# d2_out = client.containers.get('mn.d2').exec_run(cmd, stdout=True, stderr=True)
# info(d2_out, '\n')

info('*** Adding switches\n')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')

info('*** Creating links\n')
net.addLink(d1, s1)
net.addLink(s1, s2, cls=TCLink, delay='50ms', bw=1)
net.addLink(s2, d2)
net.addLink(s2, d3)

info('*** Starting network\n')
net.start()

info('*** Testing connectivity\n')
net.ping([d1, d2])
net.ping([d1, d3])
net.ping([d2, d3])

info('*** Running CLI\n')
CLI(net)

# Killing the threads
d1_running_thread.join()
d2_running_thread.join()

info('*** Stopping network')
net.stop()

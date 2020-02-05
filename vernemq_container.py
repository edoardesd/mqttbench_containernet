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

# VERNEMQ part
image_name = "vernemq/vernemq:alpine"  # :latest
#image_name = "vernemq/vernemq:original"  # :latest

net = Containernet(controller=Controller)

cmd = "start_vernemq"

info('*** Adding controller\n')
net.addController('c0', port=6654)

info('*** Adding docker containers using {} images\n'.format(image_name))

# we need to change the vm1.args in VerneMq to give unique names to the nodes and enable cluster creation

# port bindings is swapped (host_machine:docker_container)
d1 = net.addDocker(hostname="vernemq1", name='d1', ip='10.0.0.251', dimage=image_name,
                   # ports=[1883],
                   port_bindings={1883: 1883},
                   # volumes=[PWD + "/vm1.conf:/etc/vernemq/vernemq.conf"],
                   # volumes=[PWD + "/vm1.args:/etc/vernemq/vm.args"],
                   environment={
                        "DOCKER_VERNEMQ_NODENAME":"172.17.0.2",
                        "DOCKER_VERNEMQ_DISCOVERY_NODE":"172.17.0.3",
                        # accept the license terms
                        "DOCKER_VERNEMQ_ACCEPT_EULA": "yes",
                        # This is necessary to permit anonymous sub and pub from MQTT clients,
                        # otherwise it will expect user and password
                        "DOCKER_VERNEMQ_ALLOW_ANONYMOUS":"on"
                   }
                   )

d2 = net.addDocker(hostname="vernemq2", name='d2', ip='10.0.0.252', dimage=image_name,
                   ports=[1883],
                   port_bindings={1883: 1884},
                   # volumes=[PWD + "/vm2.args:/etc/vernemq/vm.args"],
                   environment={
                                # The environmental variables here are for automatic cluster discovery
                                # they work correctly with Dockerfile but not with alpine
                                "DOCKER_VERNEMQ_NODENAME":"172.17.0.3",
                                "DOCKER_VERNEMQ_DISCOVERY_NODE":"172.17.0.2",
                                # accept license terms
                                "DOCKER_VERNEMQ_ACCEPT_EULA": "yes",
                                # allow anonymous communication with MQTT clients
                                "DOCKER_VERNEMQ_ALLOW_ANONYMOUS":"on"
                                }
                   )

info('*** Starting {}\n'.format(SIM_NAME))
client = docker.from_env()


###################### Necessary for the alpine distribution -> all changes are not taken by passing as docker enviromental parameters
#add the accept lincense to the config file
# d1.cmd('echo "accept_eula = yes" >> /vernemq/etc/vernemq.conf')
#Change the nodename in the config file to create the cluster
# d1.cmd('sed -i "/nodename = VerneMQ@127.0.0.1/s/= .*/= dev1@172.17.0.2/" /vernemq/etc/vernemq.conf')
# #Change the node in the args file
# d1.cmd('sed -i "/VerneMQ@127.0.0.1/s/ .*/ dev1@172.17.0.2/" /vernemq/etc/vm.args')

# # configure the listener port
# d1.cmd('echo "listener.tcp.default = 10.0.0.251:1883" >> /vernemq/etc/vernemq.conf')

# start vernemq after configuration
# d1_bis = client.containers.get('mn.d1').exec_run("start_vernemq", stdout=True, stderr=True)
# info(d1_bis, '\n')

#add the accept lincense to the config file otherwise it doesn't start the node
# d2.cmd('echo "accept_eula = yes" >> /vernemq/etc/vernemq.conf')
# #Change the nodename in the config file to create the cluster
# d2.cmd('sed -i "/nodename = VerneMQ@127.0.0.1/s/= .*/= dev1@172.17.0.3/" /vernemq/etc/vernemq.conf')
# #Change the node in the args file
# d2.cmd('sed -i "/VerneMQ@127.0.0.1/s/ .*/ dev2@172.17.0.3/" /vernemq/etc/vm.args')
#
# #set tcp listener port
# d2.cmd('echo "listener.tcp.default = 10.0.0.252:1884" >> /vernemq/etc/vernemq.conf')
# start vernemq
# should insert it in a thread since it keeps operating
# d2_bis = client.containers.get('mn.d2').exec_run("start_vernemq", stdout=True, stderr=True)
# info(d2_bis, '\n')

########################## Original Docker file ##########################
# the majority of the above steps are done by simply passing as docker environment parameters, which is not the case in Alpine
# The only difference is that we need to insert the start_vernemq into a thread since it continues working

d1_running_thread = threading.Thread(target=client.containers.get('mn.d1').exec_run, args=(cmd,), kwargs={'stdout':True, 'stderr':True})
d1_running_thread.start()
d2_running_thread = threading.Thread(target=client.containers.get('mn.d2').exec_run, args=(cmd,), kwargs={'stdout':True, 'stderr':True})
d2_running_thread.start()

info('*** Adding switches\n')
s1 = net.addSwitch('vs1')
s2 = net.addSwitch('vs2')

info('*** Creating links\n')
net.addLink(d1, s1)
net.addLink(s1, s2, cls=TCLink, delay='50ms', bw=1) # 1sec
net.addLink(s2, d2)

info('*** Starting network\n')
net.start()

info('*** Testing connectivity\n')
net.ping([d1, d2])

info('*** Running CLI\n')
CLI(net)

# Killing the threads
d1_running_thread.join()
d2_running_thread.join()

info('*** Stopping network')
net.stop()

# still need to add the user

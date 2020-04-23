import docker
import os
import time

PWD = os.getcwd()

docker_client = docker.from_env()
ret_it = docker_client.networks.list(names=['pumba_net'])[0]
# print(ret_it.id)

## kill the previous created containers
try:
    running_container = docker_client.containers.get('d1')
    running_container.stop()
    running_container.remove()
    print('Container d1 stoped and killed')
except docker.errors.NotFound:
    pass

container_1 = docker_client.containers.create('francigjeci/mqtt-py:3.8.2',
                                         detach=True,
                                        # entrypoint= 'echo hello',
                                        working_dir = '/home',
                                        tty=True, # terminal driver, necessary since you are running the python in bash
                                        stdin_open=True,
                                         # stream=True,
                                        volumes=[PWD + '/net_analysis_post.py:/home/script.py'], #'/home',
                                        # command=["bash"],
                                        environment={
                                            'CLIENT_HOSTNAME': '172.20.0.2',
                                            'CLIENT_SUBSCRIBERS': 1,
                                            'CLIENT_SUBSCRIBERS_COUNT': 1,
                                            'CLIENT_PUBLISHERS': 0,
                                            'CLIENT_PUBLISHERS_COUNT': 0,
                                            # 'CLIENT_MESSAGE_SIZE': 32,
                                            'CLIENT_MESSAGE': 'hello',
                                            'CLIENT_TOPIC': 'test',
                                            'CLIENT_QOS': 0
                                        },
                                         network='pumba_net', # the network this container must be connected
                                         hostname="client1", name='d1'# , ip='172.20.0.72'
                                         )



print('Starting container %s ' % 'd1')
container_1.start()
time.sleep(5)
print('Container %s started' % "d1")

# _doc = docker_client.containers.get('d1')

d1_bis = container_1.exec_run("python3 /home/script.py")
print(d1_bis.output.decode("utf-8"))

# time.sleep(12000)

container_1.stop()

# This decodes the logs from bytes-like into string type
# logs = container.logs().decode("utf-8")
# print(logs)
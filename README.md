# MQTTbench Containernet 

## Containernet configurations: 
* EMQx
* RabbitMQ
* VerneMQ
* HiveMQ

## Clients:
* GoLang Publisher
* Python Subscriber


## How to run
1) Clean configuration: `sudo mn -c`

2) Start the containernet simulation: `sudo python3 mesh_routers.py`
   - `--type <container_type>` `-t`: MQTT broker cluster type
   - `--delay-routers <number>`, `-d`: delay on the router-router link
   - `--delay-switch <number>`, `-c`: delay on the router-switch(broker) link
   - `--disable-client`, `-s`: no clients in the simulation
   - `--ram-limit <ram_size>`: ram memory of the brokers (`500m`, `1g`, `2g`, `...`)
   - `--cpu`: enable a 16 core machine 
   - Example: `sudo python3 mesh_routers.py --type emqx -d 5 -c 0 --ram-limit 2g`
   
3) Start clients/log scripts: `./start_clients.sh`
    - `--clients <number>`: number of pub/sub clients 
    - `--delay <number>`: delay between publishes
    - `--messages <number>`: number of published messages
    - `--qos <0,1,2>`: MQTT Quality of Service for pubs and subs
    - Example: `./start_clients.sh --clients 5 --delay 2 --messages 50 --qos 2`
    
### Clients
#### Publisher:
GoLang script inspired from [krylovsk/mqtt-benchmark](khttps://github.com/krylovsk/mqtt-benchmark) and available [here](https://github.com/edoardesd/mqtt-benchmark).
The container image is on [DockerHub](https://hub.docker.com/repository/docker/flipperthedog/go_publisher).

The scripts spawn `n` clients that publish `m` message every `d` seconds and store the flight time in a `filename` file.

- Syntax: `./mqtt-benchmark --broker tcp://<broker_addr>:<port> --topic <name> --clients <num_clients> --count <msg_clients> --qos <0,1,2> --delay <seconds> --folder <path/to/folder> --file-name <output_filename>`
- Example: `docker exec -t mn.pub1 mqtt-benchmark --broker tcp://10.0.1.100:1883 --topic test --clients 10" --count 10 --qos 2 --delay 1 --folder "experiments/today" --file-name "sim"`

- Modify and push: 
    + go to `goprojects/src/github.com/mqtt-benchmark/`
    + install `go install`
    + commit and push to `github`
    + go to `goprojects/src/github.com/mqtt-benchmark/docker`
    + run `./build_this latest` (also with a different tag)

#### Subscriber
The python subscriber connects, receives `m` messages and then disconnects.
Available in [this](https://github.com/edoardesd/mqttbench_containernet/tree/master/clients) repo.
The container image is on [DockerHub](https://hub.docker.com/repository/docker/flipperthedog/alpine_client).

- Syntax: as the publisher
- Example: `python3 clients/alpine_container/sub_thread.py -h 10.0.0.100 -t topic -q "$QOS" -m 10 -c 10 --folder "experiments/today" --file-name "sim"`

- Modify and push: 
    + go to `mqttbench_containernet/clients/alpine_container`
    + run `./build_this`
    

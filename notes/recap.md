# MQTT-benchmarking

## Goal
Analyze the behaviour and the performances of four MQTT brokers among the main ones, plus MQTT-ST (mosquitto bridging).

## Behaviour 
- How the cluster is created (number of messages, traffic in byte)
- How/if connections are forwarded
- How/if subscriptions are forwarded 
- How messages are forwarded
    + flooding to everyone
    + chain
    + tree

### Questions about behaviour
#### EMQX
- connect/disconnect: forward connection to everyone (no multiple clients with the same ID)
- subscripton/unsubscription: forward subscription to everyone
- publish: send only to the intereset ones (check!!)

#### RABBITMQ
#### VERNEMQ
#### HIVEMQ

If _emqx_ and the other brokers store informations about subscriptions and connection, I'd expect an increase of RAM with the increase of clients and number of topics. 

If they forward publications only to the interested ones, I'd expected a low traffic inside the broker. Otherwise -forward to everyone-, an high traffic.

Check subscription forward with multi-level topics

Message forwarding: follow a chain/tree or broadcast to everyone

## Performance
- Network
    + **end-to-end delay**: time from pubblication to subscription
    + **out throughput**: how many messages can send a broker
    + in throughput (emitted from the client)
    + total bytes in the cluster (_tcpdump_ during every simulation)

- Hardware
    + **CPU**
    + **RAM**

## Experiments
1. Create the cluster: done
2. Create N clients: 1 docker with N clients or a docker for each client
3. Connect N clients: 
    - 100% locality: pub and sub on the same broker (worst case)
    - (75% locality)
    - 50% locality
    - (25% locality)
    - 0% locality: no sub on the broker where we pub
    - equally distributed: pub on the same, subscriber equally distributed on the cluster
4. Add latency (same on all the links):
    - 0 ms
    - 25 ms
    - 50 ms
5. Send messages:
    - 100 message per client
    - payload with the timestamp (bytes?)

## Topology
- Fully meshed: done
- Star: docker swarm/overlay network of docker (???)
- Tree...

## Open points
- QoS 
- Number of different topics
- Retained messages

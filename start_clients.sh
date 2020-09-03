#!/usr/bin/env bash

docker exec -t mn.sub0 mosquitto_sub -h 10.0.0.100 -t test -q 2 -d -v | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"'  | tee test0.txt &
pid[0]=$!
docker exec -t mn.sub1 mosquitto_sub -h 10.0.1.100 -t test -q 2 -d -v | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"'  | tee test1.txt &
pid[1]=$!
docker exec -t mn.sub2 mosquitto_sub -h 10.0.2.100 -t test -q 2 -d -v | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"'  | tee test2.txt &
pid[2]=$!
docker exec -t mn.sub3 mosquitto_sub -h 10.0.3.100 -t test -q 2 -d -v | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"'  | tee test3.txt &
pid[3]=$!
docker exec -t mn.sub4 mosquitto_sub -h 10.0.4.100 -t test -q 2 -d -v | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"'  | tee test4.txt &
pid[4]=$!

#docker exec -t mn.pub0 python simple_pub.py -h 10.0.0.100 -t test -q 2 &
#docker exec -t mn.pub1 python simple_pub.py -h 10.0.1.100 -t test -q 2 &
#docker exec -t mn.pub2 python simple_pub.py -h 10.0.2.100 -t test -q 2 &
#docker exec -t mn.pub3 python simple_pub.py -h 10.0.3.100 -t test -q 2 &
#docker exec -t mn.pub4 python simple_pub.py -h 10.0.4.100 -t test -q 2 &

sleep 2
#trap "kill ${pid[0]} ${pid[1]} ${pid[2]} ${pid[3]} ${pid[4]}; exit 1" INT
wait
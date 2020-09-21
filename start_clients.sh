#!/usr/bin/env bash

FOLDER_NAME="casa"

docker stats --format \
    "{\"{{ .Name }}\": {\"memory\":{\"raw\":\"{{ .MemUsage }}\",\"percent\":\"{{ .MemPerc }}\"},\"cpu\":\"{{ .CPUPerc }}\",\"netIO\":\"{{.NetIO}}\"}}}"   | ts "{\"%F-%H:%M:%S\": " > experiments/file.txt &
FILE_PID=$!

sudo tcpdump -i s0-eth1 src 10.0.0.100 -w tcp0.pcap &
sudo tcpdump -i s1-eth1 src 10.0.1.100 -w tcp1.pcap &
sudo tcpdump -i s2-eth1 src 10.0.2.100 -w tcp2.pcap &
sudo tcpdump -i s3-eth1 src 10.0.3.100 -w tcp3.pcap &
sudo tcpdump -i s4-eth1 src 10.0.4.100 -w tcp4.pcap &

sleep 5

docker exec -t mn.sub0 python sub_thread.py -h 10.0.0.100 -t test -q 2 -m 200 -c 1 --name $FOLDER_NAME &
docker exec -t mn.sub1 python sub_thread.py -h 10.0.1.100 -t test -q 2 -m 200 -c 1 --name $FOLDER_NAME &
docker exec -t mn.sub2 python sub_thread.py -h 10.0.2.100 -t test -q 2 -m 200 -c 1 --name $FOLDER_NAME &
docker exec -t mn.sub3 python sub_thread.py -h 10.0.3.100 -t test -q 2 -m 200 -c 1 --name $FOLDER_NAME &
docker exec -t mn.sub4 python sub_thread.py -h 10.0.4.100 -t test -q 2 -m 200 -c 1 --name $FOLDER_NAME &

sleep 10

docker exec -t mn.pub0 mqtt-benchmark --broker tcp://10.0.0.100:1883 --topic test --clients 1 --count 40 --qos 2 --delay 2 --name $FOLDER_NAME &
docker exec -t mn.pub1 mqtt-benchmark --broker tcp://10.0.1.100:1883 --topic test --clients 1 --count 40 --qos 2 --delay 2 --name $FOLDER_NAME &
docker exec -t mn.pub2 mqtt-benchmark --broker tcp://10.0.2.100:1883 --topic test --clients 1 --count 40 --qos 2 --delay 2 --name $FOLDER_NAME &
docker exec -t mn.pub3 mqtt-benchmark --broker tcp://10.0.3.100:1883 --topic test --clients 1 --count 40 --qos 2 --delay 2 --name $FOLDER_NAME &
docker exec -t mn.pub4 mqtt-benchmark --broker tcp://10.0.4.100:1883 --topic test --clients 1 --count 40 --qos 2 --delay 2 --name $FOLDER_NAME &
BACK_PID=$!

wait $BACK_PID

sleep 20
kill -9 $FILE_PID
sudo killall -9 tcpdump
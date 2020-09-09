#!/usr/bin/env bash

docker stats --format \
    "{\"{{ .Name }}\": {\"memory\":{\"raw\":\"{{ .MemUsage }}\",\"percent\":\"{{ .MemPerc }}\"},\"cpu\":\"{{ .CPUPerc }}\",\"netIO\":\"{{.NetIO}}\"}}}"   | ts "{\"%F-%H:%M:%S\": " > experiments/file.txt &
FILE_PID=$!

sudo tcpdump -i s0-eth1 src 10.0.0.100 -w tcp0.pcap &
sudo tcpdump -i s1-eth1 src 10.0.1.100 -w tcp1.pcap &
sudo tcpdump -i s2-eth1 src 10.0.2.100 -w tcp2.pcap &
sudo tcpdump -i s3-eth1 src 10.0.3.100 -w tcp3.pcap &
sudo tcpdump -i s4-eth1 src 10.0.4.100 -w tcp4.pcap &

sleep 10

docker exec -t mn.sub0 python sub_thread.py -h 10.0.0.100 -t test -q 2 -m 40 -c 1 &
docker exec -t mn.sub1 python sub_thread.py -h 10.0.1.100 -t test -q 2 -m 40 -c 1 &
docker exec -t mn.sub2 python sub_thread.py -h 10.0.2.100 -t test -q 2 -m 40 -c 1 &
docker exec -t mn.sub3 python sub_thread.py -h 10.0.3.100 -t test -q 2 -m 40 -c 1 &
docker exec -t mn.sub4 python sub_thread.py -h 10.0.4.100 -t test -q 2 -m 40 -c 1 &

docker exec -t mn.pub0 python pub_thread.py -h 10.0.0.100 -t test -q 2 -m 10 -c 1 -d 1 &
docker exec -t mn.pub1 python pub_thread.py -h 10.0.1.100 -t test -q 2 -m 10 -c 1 -d 1 &
docker exec -t mn.pub2 python pub_thread.py -h 10.0.2.100 -t test -q 2 -m 10 -c 1 -d 1 &
docker exec -t mn.pub3 python pub_thread.py -h 10.0.3.100 -t test -q 2 -m 10 -c 1 -d 1 &
docker exec -t mn.pub4 python pub_thread.py -h 10.0.4.100 -t test -q 2 -m 10 -c 1 -d 1 &
BACK_PID=$!

wait $BACK_PID

sleep 5
kill -9 $FILE_PID
sudo killall -9 tcpdump
echo "diocane"
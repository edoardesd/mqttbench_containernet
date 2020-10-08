#!/usr/bin/env bash


PUB_MESSAGES=unset
SUB_MESSAGES=unset
CLIENTS=unset
QOS=unset
DELAY=unset
NAME=unset
TOPIC="test"
DATE=$(date +"%m-%d")
FILE_NAME=$(date +"%H%M%S")

usage()
{
  echo "Usage:  start_clients [ -c | --clients CLIENTS ]
                [ -d | --delay   DELAY   ]
                [ -m | --messages PUB_MESSAGES ]
                [ -n | --name NAME]
                [ -q | --qos QOS]"
  exit 2
}

PARSED_ARGUMENTS=$(getopt -a -n start_clients -o c:d:m:n:q: --long clients:,delay:,messages:,name:,qos: -- "$@")
VALID_ARGUMENTS=$?
if [ "$VALID_ARGUMENTS" != "0" ]; then
  usage
fi

echo "PARSED_ARGUMENTS are $PARSED_ARGUMENTS"
eval set -- "$PARSED_ARGUMENTS"
while :
do
  case "$1" in
    -c | --clients)  CLIENTS="$2"      ; shift 2 ;;
    -d | --delay)    DELAY="$2"        ; shift 2 ;;
    -m | --messages) PUB_MESSAGES="$2" ; shift 2 ;;
    -n | --name)     NAME="$2" ; shift 2 ;;
    -q | --qos)      QOS="$2"          ; shift 2 ;;
    --) shift; break ;;

    *) echo "Unexpected option: $1 - this should not happen."
       usage ;;
  esac
done

SUB_MESSAGES=$((PUB_MESSAGES*5))
FULL_FOLDER=$NAME

echo "MAIN FOLDER  : $FULL_FOLDER"
echo "FILE NAME    : $NAME"

echo "CLIENTS      : $CLIENTS"
echo "DELAY        : $DELAY "
echo "MESSAGES PUB : $PUB_MESSAGES"
echo "MESSAGES SUB : $SUB_MESSAGES"
echo "QOS          : $QOS"
echo "TOPIC        : $TOPIC"
echo "Parameters remaining are: $*"

mkdir -p "$FULL_FOLDER"
echo "Using folder: $FULL_FOLDER"

echo "Starting stats and tcp dump"
docker stats --format \
    "{\"{{ .Name }}\": {\"memory\":{\"raw\":\"{{ .MemUsage }}\",\"percent\":\"{{ .MemPerc }}\"},\"cpu\":\"{{ .CPUPerc }}\",\"netIO\":\"{{.NetIO}}\"}}}"   | ts "{\"%F-%H:%M:%S\": " > "$FULL_FOLDER"/stats.txt &
FILE_PID=$!

tcpdump -i s0-eth1 src 10.0.0.100 -w "$FULL_FOLDER"/tcp0.pcap -q 2>/dev/null &
tcpdump -i s1-eth1 src 10.0.1.100 -w "$FULL_FOLDER"/tcp1.pcap -q 2>/dev/null &
tcpdump -i s2-eth1 src 10.0.2.100 -w "$FULL_FOLDER"/tcp2.pcap -q 2>/dev/null &
tcpdump -i s3-eth1 src 10.0.3.100 -w "$FULL_FOLDER"/tcp3.pcap -q 2>/dev/null &
tcpdump -i s4-eth1 src 10.0.4.100 -w "$FULL_FOLDER"/tcp4.pcap -q 2>/dev/null &

sleep 1

echo "Starting subs"
docker exec -t mn.sub0 python sub_thread.py -h 10.0.0.100 -t "$TOPIC" -q "$QOS" -m "$SUB_MESSAGES" -c "$CLIENTS" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.sub1 python sub_thread.py -h 10.0.1.100 -t "$TOPIC" -q "$QOS" -m "$SUB_MESSAGES" -c "$CLIENTS" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.sub2 python sub_thread.py -h 10.0.2.100 -t "$TOPIC" -q "$QOS" -m "$SUB_MESSAGES" -c "$CLIENTS" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.sub3 python sub_thread.py -h 10.0.3.100 -t "$TOPIC" -q "$QOS" -m "$SUB_MESSAGES" -c "$CLIENTS" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.sub4 python sub_thread.py -h 10.0.4.100 -t "$TOPIC" -q "$QOS" -m "$SUB_MESSAGES" -c "$CLIENTS" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &

sleep 10

echo "Starting pubs"
docker exec -t mn.pub0 mqtt-benchmark --broker tcp://10.0.0.100:1883 --topic "$TOPIC" --clients "$CLIENTS" --count "$PUB_MESSAGES" --qos "$QOS" --delay "$DELAY" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.pub1 mqtt-benchmark --broker tcp://10.0.1.100:1883 --topic "$TOPIC" --clients "$CLIENTS" --count "$PUB_MESSAGES" --qos "$QOS" --delay "$DELAY" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.pub2 mqtt-benchmark --broker tcp://10.0.2.100:1883 --topic "$TOPIC" --clients "$CLIENTS" --count "$PUB_MESSAGES" --qos "$QOS" --delay "$DELAY" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.pub3 mqtt-benchmark --broker tcp://10.0.3.100:1883 --topic "$TOPIC" --clients "$CLIENTS" --count "$PUB_MESSAGES" --qos "$QOS" --delay "$DELAY" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
docker exec -t mn.pub4 mqtt-benchmark --broker tcp://10.0.4.100:1883 --topic "$TOPIC" --clients "$CLIENTS" --count "$PUB_MESSAGES" --qos "$QOS" --delay "$DELAY" --folder "$FULL_FOLDER" --file-name "$FILE_NAME" &
BACK_PID=$!

wait $BACK_PID
SLEEP_TIME=$((PUB_MESSAGES*5/2))

sleep $SLEEP_TIME

kill -9 $FILE_PID
killall -9 tcpdump

exit 1
#!/bin/bash

NETWORK_NAME="pumba_net"
IP_ADDR="172.20.0."
CLUSTER_TYPE="rabbitmq"
DEFAULT_INTERFACE="eth0"
TOTAL_BROKERS=5
DELAY=50
DURATION_SIM="9999m"
PWD=$(pwd)
FIST_BROKER_NUM=2
LAST_BROKER_NUM=$((TOTAL_BROKERS+1))


###### EMQX HELPER FUNCTIONS ######
function COMPOSE_STATIC_CLUSTER {
  STRING=""

  for i in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
    do
      case $CLUSTER_TYPE in
          EMQX | emqx)
            STRING="${STRING}${CLUSTER_TYPE}${i}@${IP_ADDR}${i},"
            ;;

          VERNEMQ | vernemq | VERNE | verne )
            STRING="${STRING}${IP_ADDR}${i},"
          ;;
          *)
            echo -n "$BROKER not available"
            ;;
      esac
    done
  echo "$STRING"
}
###### END OF EMQX HELPER ######

###### EMQX HELPER FUNCTIONS ######
function CREATE_CONFIG {
  current_bkr=$1
  for i in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
    do
      echo "cluster_formation.classic_config.nodes.$((i-1)) = docker@${CLUSTER_TYPE}_${i}" >>  "$PWD"/confiles/"$current_bkr".conf
    done
}

function ADD_HOSTS {
  current_bkr=$1
  for i in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
    do
      docker exec -it "$current_bkr" sh -c "echo '172.20.0.$i      ${CLUSTER_TYPE}_${i}' >> /etc/hosts"
    done
}
###### END OF RABBITMQ HELPER ######

###### HIVEMQ HELPER FUNCTIONS ######

function CREATE_HIVEMQ_CONFIG {
	
	config_template_file=$1
	output_file=$2
	ip_pool=$IP_ADDR
	port_disc_node=8000
	# Copy the template file to new file
	cp $config_template_file $output_file
	# Delete all nodes present in the static tag
	# Necessary to avoid wrong parsing during adding new node elements 
	xmlstarlet ed -L -d '//discovery/static/node' $output_file
	# Adding node elements which shall create the cluster
	for i in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
	    do
		# Add the node element; add the host and the port inside the node element
		xmlstarlet ed -L -s '//discovery/static' -t elem -n 'node' $output_file 
		xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'host' -v $ip_pool$i $output_file
		xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'port' -v $port_disc_node $output_file
	    done
}


###### END OF HIVEMQ HELPER ######


###### EMQX ######
function RUN_EMQX {
  for bkr in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
    do
      BRK_NAME=$CLUSTER_TYPE"$bkr"
      docker run -d --network=$NETWORK_NAME \
        --hostname "$BRK_NAME" \
        --name "$BRK_NAME" \
        -p $((1880+bkr)):1883 \
        -e EMQX_NAME="$BRK_NAME" \
        -e EMQX_NODE__DIST_LISTEN_MAX=6379 \
        -e EMQX_LISTENER__TCP__EXTERNAL=1883 \
        -e EMQX_CLUSTER__DISCOVERY="static" \
        -e EMQX_CLUSTER__STATIC__SEEDS="$(COMPOSE_STATIC_CLUSTER)" \
        flipperthedog/emqx-pumba
    done
}
###### END OF EMQX ######

###### RABBITMQ ######
function RUN_RABBITMQ {
  for bkr in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
    do
      BRK_NAME="${CLUSTER_TYPE}_${bkr}"
      cp "$PWD"/confiles/rabbitmq.conf "$PWD"/confiles/"$BRK_NAME".conf
      CREATE_CONFIG "$BRK_NAME"

      docker run -d --network=$NETWORK_NAME \
        --hostname "$BRK_NAME" \
        --name "$BRK_NAME" \
        -p $((5670+bkr)):5672 \
        -v "$PWD"/confiles/"$BRK_NAME".conf:/etc/rabbitmq/rabbitmq.conf \
        -e RABBITMQ_ERLANG_COOKIE=$(cat "$PWD"/.erlang.cookie) \
        -e RABBITMQ_NODENAME=docker@"$BRK_NAME" \
        flipperthedog/rabbitmq:ping

      ADD_HOSTS "$BRK_NAME"
 	  done
}
###### END OF RABBITMQ ######

###### VERNEMQ ######
function RUN_VERNEMQ {
  for bkr in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
    do
      BRK_NAME="${CLUSTER_TYPE}_${bkr}"

      docker run -d --network=$NETWORK_NAME \
        --hostname "$BRK_NAME" \
        --name "$BRK_NAME" \
        -p $((5680+bkr)):5684 \
        -e DOCKER_VERNEMQ_ACCEPT_EULA=yes \
	-e DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on \
        -e DOCKER_VERNEMQ_NODENAME="${IP_ADDR}${bkr}" \
        -e DOCKER_VERNEMQ_DISCOVERY_NODE=172.20.0.2 \
        francigjeci/vernemq-debian:latest
 	  done
}
###### END OF VERNEMQ ######

###### HIVEMQ ######
function RUN_HIVEMQ {
	config_template_file="$PWD"/config/config-dns.xml
	output_config_file="$PWD"/config/config-dns_new_1.xml
	# create the config file to 
	CREATE_HIVEMQ_CONFIG "$config_template_file" "$output_config_file"
  	for bkr in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
		do
			BRK_NAME="${CLUSTER_TYPE}_${bkr}"
			docker run -d --network=$NETWORK_NAME \
			--hostname "$BRK_NAME" \
			--name "$BRK_NAME" \
			--ip="${IP_ADDR}${bkr}" \
			-p $((5690+bkr)):5684 \
			-v "$output_config_file":/opt/hivemq/conf/config.xml \
			-e HIVEMQ_BIND_ADDRESS="${IP_ADDR}${bkr}" \
			francigjeci/hivemq:dns-image
		done
}
###### END OF VERNEMQ ######



###### MAIN ######

#input params type, delay, num broker
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in

    -t|--cluster-type)
    CLUSTER_TYPE="$2"
    shift
    shift
    ;;

    -d|--delay)
    DELAY="$2"
    shift
    shift
    ;;

    -n|--num-brokers)
    TOTAL_BROKERS="$2"
    shift
    shift
    ;;

    *)
    POSITIONAL+=("$1")
    shift
    ;;
esac
done
set -- "${POSITIONAL[@]}" 


echo "$CLUSTER_TYPE $DELAY $TOTAL_BROKERS"

echo "Cleaning up the environment..."
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

docker network rm $NETWORK_NAME

echo "Creating a new network..."
docker network create \
		--driver=bridge \
		--subnet="$IP_ADDR"0/16 \
		--ip-range="$IP_ADDR"0/24 \
		$NETWORK_NAME


echo "Creating brokers of type... $CLUSTER_TYPE"

case $CLUSTER_TYPE in

  EMQX | emqx)
    RUN_EMQX
    ;;

  RABBITMQ | rabbitmq | RABBIT | rabbit)
    RUN_RABBITMQ
    ;;

  VERNEMQ | vernemq | VERNE | verne )
    RUN_VERNEMQ
  ;;

  HIVEMQ | hivemq | HIVE | hive )
    RUN_HIVEMQ
  ;;
  *)
    echo -n "$BROKER not available"
    ;;
esac



echo "Slowing down the network..."
sleep 20

docker run -d --rm --network=pumba_net \
 		--name pumba \
		-v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
		--interface $DEFAULT_INTERFACE \
		--duration $DURATION_SIM \
		delay --time $DELAY \
		$(docker ps --format "{{.Names}}"  | tr '\r\n' ' ')

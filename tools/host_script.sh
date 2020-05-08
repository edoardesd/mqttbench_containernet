CONTAINER_NAME=$1
IP_NET=$(ip addr show "$CONTAINER_NAME"-eth0 | awk '$1 == "inet" {gsub(/\/.*$/, "", $2); print $2}')

head -n -1 /etc/hosts > ~/temp.txt
cat ~/temp.txt > /etc/hosts
rm ~/temp.txt
echo "$IP_NET     $CONTAINER_NAME" >> /etc/hosts

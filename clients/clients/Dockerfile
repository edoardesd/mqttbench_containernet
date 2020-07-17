ARG BASEIMAGE=python:3.8.2-slim

FROM ${BASEIMAGE}

ENV PATH /usr/local/bin:$PATH

# Update and install numpy & paho-mqtt
RUN apt-get update && apt-get install -y \
	net-tools \
	iputils-ping \
	iproute2 \
	mosquitto-clients

RUN pip install numpy && pip install paho-mqtt

WORKDIR /home/ubuntu

COPY . /home/ubuntu

#CMD ["/usr/local/bin/python3", "-u", "container_python.py"]


# how run this dockerfile
# go into this folder
# docker build --tag flipperthedog/sub_client .

ARG BASEIMAGE=python:3.8.5-alpine3.12

FROM ${BASEIMAGE}

ENV PATH /usr/local/bin:$PATH

# Update and install numpy & paho-mqtt
RUN apk add mosquitto-clients

RUN apk add iputils \
    iproute2 \
    net-tools \
    iperf \
    xterm \
    busybox-extras

RUN apk add bash

RUN pip install paho-mqtt

WORKDIR /home/ubuntu

COPY sub_thread.py /home/ubuntu/sub_thread.py
COPY pub_thread.py /home/ubuntu/pub_thread.py

#CMD ["/usr/local/bin/python3", "-u", "container_python.py"]


# how run this dockerfile
# go into this folder
# docker build --tag flipperthedog/alpine_client .
# docker push flipperthedog/alpine_client:tagname

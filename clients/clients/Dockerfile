ARG BASEIMAGE=python:3.8.2-slim

FROM ${BASEIMAGE}

ENV PATH /usr/local/bin:$PATH

# Update and install numpy & paho-mqtt
RUN apt-get update \
	&& pip install numpy \
	&& pip install paho-mqtt

WORKDIR /home/ubuntu

COPY . /home/ubuntu

CMD ["/usr/local/bin/python3", "-u", "container_python.py"]
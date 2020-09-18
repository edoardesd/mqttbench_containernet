#!/usr/bin/env bash

docker build --tag flipperthedog/alpine_client .
docker push flipperthedog/alpine_client:latest

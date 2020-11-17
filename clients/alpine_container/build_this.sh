#!/usr/bin/env bash

version=$1

docker build --no-cache --tag flipperthedog/alpine_client:$version .
docker push flipperthedog/alpine_client:$version

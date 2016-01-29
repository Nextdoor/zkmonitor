#!/bin/bash

DOCKER_HOST_IP=$(route -n | awk '/UG[ \t]/{print $2}')
ZOOKEEPER_HOST=${ZOOKEEPER_HOST:-$DOCKER_HOST_IP}
ZOOKEEPER_PORT=${ZOOKEEPER_PORT:-2181}
VERBOSE=${VERBOSE:-}

CONFIG_FILE='./sample_config.yaml'
if [ - ./config.yaml ]; then
    CONFIG_FILE='./config.yaml'
fi

zk_monitor -z $ZOOKEEPER_HOST:$ZOOKEEPER_PORT -l INFO -f $CONFIG_FILE

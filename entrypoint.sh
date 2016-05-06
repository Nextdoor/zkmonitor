#!/bin/bash

export DOCKER_HOST_IP=$(route -n | awk '/UG[ \t]/{print $2}')
export ZOOKEEPER_HOST=${ZOOKEEPER_HOST:-$DOCKER_HOST_IP}
export ZOOKEEPER_PORT=${ZOOKEEPER_PORT:-2181}
export HTTP_PORT=${HTTP_PORT:-80}
export LOG_LEVEL=${LOG_LEVEL:-info}
export CONFIG_FILE=${CONFIG_FILE:-/sample_config.yaml}
export SMTP_HOST=${SMTP_HOST:-$DOCKER_HOST_IP}

zk_monitor -z $ZOOKEEPER_HOST:$ZOOKEEPER_PORT -l $LOG_LEVEL -f $CONFIG_FILE -p $HTTP_PORT

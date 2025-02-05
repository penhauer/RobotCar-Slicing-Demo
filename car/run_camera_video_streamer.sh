#!/bin/bash

if [ ! -f ./.env ]; then
	echo "the env file '.env' file does not exist. Make sure you create this file like env_car1 or env_car2 and fill with appropriate values."
	exit 1
fi

set -a # Automatically export variables
source .env
set +a

if [ -z "${SERVER_IP}" ]; then
	echo "SERVER_IP is not present in the environmental variables"
	exit 1
fi

if [ -z "${SERVER_STREAMING_PORT}" ]; then
	echo "SERVER_STREAMING_PORT is not present in the environmental variables"
	exit 1
fi

./stream_video.sh "${SERVER_IP}" "${SERVER_STREAMING_PORT}"


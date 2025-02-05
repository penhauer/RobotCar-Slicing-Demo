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

if [ -z "${SERVER_CONTROL_PORT}" ]; then
	echo "SERVER_CONTROL_PORT is not present in the environmental variables"
	exit 1
fi

python3 control_server.py "${SERVER_IP}" "${SERVER_CONTROL_PORT}"


#!/bin/bash

if [ ! -f ./.env ]; then
	echo "the env file '.env' file does not exist. Make sure you create this file like env_car1 or env_car2 and fill with appropriate values."
	exit 1
fi

set -a # Automatically export variables
source .env
set +a

if [ -z "${CONTROLLER_IP}" ]; then
	echo "CONTROLLER_IP is not present in the environmental variables"
	exit 1
fi

if [ -z "${CONTROLLER_CONTROL_PORT}" ]; then
	echo "CONTROLLER_CONTROL_PORT is not present in the environmental variables"
	exit 1
fi

python3 control_server.py "${CONTROLLER_IP}" "${CONTROLLER_CONTROL_PORT}" "${CONTROLLER_PASSWORD}"


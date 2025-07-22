#!/bin/bash

if [ ! -f ./.env ]; then
	echo "the env file '.env' file does not exist. Make sure you create this file like env_car1 or env_car2 and fill with appropriate values."
	exit 1
fi

set -a # Automatically export variables
source .env
set +a


if [ -z "${CONTROLLER_CONTROL_PORT}" ]; then
	echo "CONTROLLER_CONTROL_PORT is not present in the environmental variables"
fi

if [ -z "${CONTROLLER_STREAMING_PORT}" ]; then
	echo "CONTROLLER_STREAMING_PORT is not present in the environmental variables"
	exit 1
fi

process_video=""
if [ "${PROCESS_VIDEO}" == "True" ]; then
	process_video="--process_video"
fi

sudo ./venv/bin/python3 control_client.py "${CONTROLLER_CONTROL_PORT}" "${CONTROLLER_STREAMING_PORT}"  ${process_video}

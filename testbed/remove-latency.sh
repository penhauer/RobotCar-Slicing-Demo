#!/bin/bash

SLICE=${1}

if [[ -z $SLICE || ($SLICE != "1" && $SLICE != "2") ]]; then
        echo "Enter 1 or 2"
        exit 1
fi


POD=`kubectl get pods -n open5gs | grep "upf${SLICE}" | awk ' { print $1 } '`
kubectl exec -it "${POD}" -n open5gs -- tc qdisc del dev eth0 root

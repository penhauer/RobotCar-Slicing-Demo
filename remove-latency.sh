#!/bin/bash

POD=`kubectl get pods -n open5gs | grep upf2 | awk ' { print $1 } '`
kubectl exec -it "${POD}" -n open5gs -- tc qdisc del dev eth0 root

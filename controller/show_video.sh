#!/bin/bash

gst-launch-1.0 -vv udpsrc port="${1}" caps="application/x-rtp, payload=96" ! rtpjitterbuffer latency=50 ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false

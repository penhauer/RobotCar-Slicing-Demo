#!/bin/bash

gst-launch-1.0 -vv udpsrc port="${1}" caps="application/x-rtp, payload=96" ! rtpjitterbuffer ! rtph264depay ! queue ! avdec_h264 ! videoconvert ! queue ! autovideosink sync=false

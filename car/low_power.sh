#!/bin/bash

# lower power 5W
sudo nvpmodel -m1


# uncomment to set power to high power MAXN
# sudo nvpmodel -m0

sudo nvpmodel -q

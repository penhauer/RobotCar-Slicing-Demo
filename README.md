This respository explains the robotcar usecase. 



# Turning things on
## Robot Car


link to the robot car's documentation:

https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit


## 5G-Module

link to the 5G module's documentation:

https://www.waveshare.com/wiki/SIM8200EA-M2_5G_for_Jetson_Nano#Document


# Setting up the robot car

## Connecting the car to the 5G testbed

You can follow the instructions on how to setup the 5G module [here](https://www.waveshare.com/wiki/SIM8200EA-M2_5G_for_Jetson_Nano#Document). For the 5G module to operate, its driver should be installed on the car. 


Taken from the documentation:

```bash
sudo apt-get install p7zip-full
wget https://files.waveshare.com/upload/0/07/Sim8200_for_jetsonnano.7z
7z x Sim8200_for_jetsonnano.7z -r -o./Sim8200_for_jetsonnano
sudo chmod 777 -R Sim8200_for_jetsonnano
cd Sim8200_for_jetsonnano
sudo ./install.sh

cd Goonline
make

# Now finnally try connecting to the testbed.
sudo ./simcom-cm
```

Before the last step, make sure the 5G module's green light is blinking, indicating the module's ready to connect.

Once the module is connected, the interface wwan0 should be created and should get an internal ip address related to the RAN. If you send traffic through this interface, it will go through the RAN and testbed.

```bash
ping -I wwan0 8.8.8.8
```

Alternatively, you can add a default route so all 
traffic is sent from wwan0. It might be added by default using the script but there might be other default paths like wlan0 for wifi or eth0. Make sure the default traffic passes through the radio interface established between module and the testbed.


## Running the car

The control server is established on the car to  receive the movement commands and control the car. Once the car is connected to the testbad, it will receive a private ip address specific to RAN. This means we cannot send packets directly to the car as the car is behind NAT. To bypass this limit, The car will setup reverse port forwarding on the remote server. The control_server.py assumes the `jetracer` package from NVIDIA has been installed on the car. If this is not the case, follow instructions  [instructions](https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit) to install jetracer package.


```bash

git clone git@github.com:penhauer/JetRacer.git todo
cd todo
cd car
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip3 install -r requirements.txt

# run the control server
./run_control_server.sh
```


## Running the client

The client is the remote server where the car sets up the reverse port forwarding on. The car is controlled by WASD keys on the keyboard and `keyboard` python library is used. This library requires super user priviledges.

The client can be run in two modes. 
1. No video processing mode
    - Description of step one.
    - Additional details or sub-steps if necessary.

2. video processing mode
    - Description of step two.
    - Additional details or sub-steps if necessary.

TODO: complete the modes and the runner script
```bash

# install dependencies
./install_client_requirements.sh

sudo ./run_client.sh

```
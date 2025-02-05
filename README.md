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


## Working with the car

A control server is established on the car to receive the movement commands and control the car. 

# Usage


This will 

```bash
cd ~/jetracer/
python3 -m venv venv
pip3 install -r requirements_server.txt
./server_car1.sh
```



# JetRacer

<img src="https://user-images.githubusercontent.com/25759564/62127658-741e9080-b287-11e9-8ab9-f4e7e31404b1.png" height=256>

JetRacer is an autonomous AI racecar using NVIDIA Jetson Nano.  With JetRacer you will

* Go fast - Optimize for high framerates to move at high speeds

* Have fun - Follow examples and program interactively from your web browser

By building and experimenting with JetRacer you will create fast AI pipelines and push the boundaries of speed.

To get started, follow the [setup](#setup) below.

## Setup

To get started with JetRacer, follow these steps

1. Order parts from the bill of materials

    - [Latrax version](docs/latrax/bill_of_materials.md)
    - [Tamiya version](docs/tamiya/bill_of_materials.md)

2. Follow the hardware setup

    - [Latrax version](docs/latrax/hardware_setup.md)
    - [Tamiya version](docs/tamiya/hardware_setup.md)
3. Follow the [software setup](docs/software_setup.md)
4. Run through the [examples](docs/examples.md)

## Examples

### Example 1 - Basic motion

In this example you'll learn to progam JetRacer programatically from your web browser.  Learn more in the [examples](docs/examples.md) documentation.

<img src="https://user-images.githubusercontent.com/4212806/60383497-68d90a80-9a26-11e9-9a18-778b7d3a3221.gif" height=300/>

### Example 2 - Road following

In this example, you'll teach JetRacer how to follow a road using AI.  After training the neural network using the [interactive training notebook](notebooks/interactive_regression.ipynb), you'll optimize the model using NVIDIA TensorRT and deploy for a live demo. Learn more in the [examples](docs/examples.md).

<img src="https://user-images.githubusercontent.com/4212806/60383389-bd7b8600-9a24-11e9-9f64-926e5edb52cc.gif" height=300/>

## See also

* [JetBot](http://github.com/NVIDIA-AI-IOT/jetbot) - An educational AI robot based on NVIDIA Jetson Nano

* [JetCam](http://github.com/NVIDIA-AI-IOT/jetcam) - An easy to use Python camera interface for NVIDIA Jetson
* [JetCard](http://github.com/NVIDIA-AI-IOT/jetcard) - An SD card image for web programming AI projects with NVIDIA Jetson Nano
* [torch2trt](http://github.com/NVIDIA-AI-IOT/torch2trt) - An easy to use PyTorch to TensorRT converter

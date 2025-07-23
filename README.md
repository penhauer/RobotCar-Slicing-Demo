
## Table of Contents

<ol>
  <li><a href="#overview">Overview</a></li>
  <li><a href="#network-setup>Network Setups</a></li>
  <li><a href="#car-and-controller-setup">Car and Controller Setup</a></li>
  <li><a href="#directories-and-files">Directories and Files</a></li>
  <li><a href="#network-connections">Network Connections</a></li>
  <li><a href="#references">References</a></li>
  <li><a href="#troubleshooting-guide">Troubleshooting Guide</a></li>
</ol>


## Overview


<img width="8892" height="2416" alt="image" src="https://github.com/user-attachments/assets/0f35b21c-97d9-4abf-91b6-af6e2d9bf80f" />



This project demonstrates a robot car streaming video to a remote server (the controller) over a network, with control commands sent back to the car. The setup is designed to work in a 5G testbed with slicing capabilites. Two slices are configured for every UE; a **dedicated URLLC slice** (ultra-reliable low-latency communication) and a **best-effort slice**. Video streamed from UE1 (first car) passes thorugh the dedicated slice1, while for UE2, the traffic goes through the best effort slice2.

The video is streamed to an edge server where controlling commands are sent back to the car; forming a closed control loop. In this case, UE1 is expected to perform better since it is attached to a dedicated slice. Conversely, in case an obstacle is close to UE2 (second car) as it is moving forward, the action to stop the car may not arrive in time to prevent the car from hitting the obstacle.

---

## Network Setup
The cars come with both a Wi-Fi card and a 5G module. Either can be used for internet connectivity. If the you managed to connect the cars to internet or a local network, you can skip this section.



#### Connecting to 4G/5G testbed


The instructions on how to setup the 5G module can be found [here](https://www.waveshare.com/wiki/SIM8200EA-M2_5G_for_Jetson_Nano#Document). For the 5G module to operate, its driver should be installed on the car. Taken from the documentation:

```bash
$ sudo apt-get install p7zip-full
$ wget https://files.waveshare.com/upload/0/07/Sim8200_for_jetsonnano.7z
$ 7z x Sim8200_for_jetsonnano.7z -r -o./Sim8200_for_jetsonnano
$ sudo chmod 777 -R Sim8200_for_jetsonnano
$ cd Sim8200_for_jetsonnano
$ sudo ./install.sh

$ cd Goonline
$ make

# Now finnally try connecting to the testbed.
$ sudo ./simcom-cm
```

Before the last step, make sure the 5G module's LED is blinking green, indicating the module's ready to connect. Note that the module has a red LED, which indicates the module is powered. Also, the 5G module has a white reset button that helps resetting the state when problems occur in connection. 

Once the module is connected, the interface wwan0 should be created and should get an ip address internal to the RAN. If you send traffic through this interface, it will go through the RAN and testbed.

```bash
$ ping -I wwan0 8.8.8.8
```

Alternatively, you can add a default route so all 
traffic is sent from `wwan0`. This might done by default using the script but there might be other default paths like `wlan0` for Wi-Fi or eth0. Make sure the default traffic passes through the radio interface established between module and the testbed.

Check the routing table to make sure the default path is through `wwan0`.

```
$ ip route
```

#### Connecting to Wi-Fi

To connect to Wi-Fi, simply run:

```
$ sudo nmtui
```


## Car and Controller Setup

### High-Level Steps

1. Prepare environment files for the car and the controller (see detailed steps below).
2. Set up the car: install dependencies, configure, and start services.
3. Set up the conttroller: install dependencies and start the controller.
4. (Optional) Use testbed scripts to simulate network conditions.

For detailed step-by-step instructions, see below.

### Step-by-Step Instructions

1. **Prepare Environment Files**
   - Copy an example environment file from `/env_examples/` to the `/car` and `/controller` directories as `.env`.
   - Edit the `.env` files as needed for your network setup.
     ```bash
     # Example for the car
     cp env_examples/env_car1 car/.env
     # Example for the controller
     cp env_examples/env_car1 controller/.env
     # Edit the files to match your server IP and ports
     ```
   - *Refer to this section for all environment file setup. Troubleshooting and script references will assume you have completed this step.*

2. **Set Up the Car**
   - On the robot car, install required Python dependencies:
     ```bash
     cd car
     python3 -m venv venv
     source venv/bin/activate
     pip3 install -r requirements.txt
     ```
   - **You must also install the `jetracer` package from NVIDIA for the control server to work.**
     - If not already installed, follow the instructions here: https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit
   - (Optional) Adjust power and WiFi settings for optimal performance:
     ```bash
     ./low_power.sh
     ./wifi-decrease-latency.sh
     ```

3. **Start the Car Services**
   - Start the control server (enables remote control):
     ```bash
     ./run_control_server.sh
     ```
   - Start the video streaming service:
     ```bash
     ./run_camera_video_streamer.sh
     ```

4. **Set Up the controller**
   - On the client machine, install Python dependencies:
     ```bash
     cd controller
     ./install_controller_requirements.sh
     ```

5. **Start the Controller**
   - Run the controller to connect to the car and receive video/control:
     ```bash
     sudo ./run_controller.sh
     ```
   - **Note:** The controller requires the `keyboard` Python library, which must be run with super user privileges (sudo).
   - The controller can run in two modes:
     - **No video processing**: Just displays the video stream.
     - **Video processing**: Processes the video stream for obstacle detection (set `PROCESS_VIDEO=True` in `.env` or pass the flag if supported).
     When video processing is active, if you press the key `m` on the keyboard, the car will move forward untill a red obstacle is detected. Note that while the car is automatically moving forward, pressing any other key would stop this automatic move.

6. **(Optional) Use Testbed Scripts for Network Emulation**
   - To add artificial latency to the network (for testing):
     ```bash
     cd testbed
     ./add-latency.sh
     ```
   - To remove the artificial latency:
     ```bash
     ./remove-latency.sh
     ```

## Directories and Files

### 1. **Robot Car (`/car`)**
All car related files are in this directory.
- `/car/control_server.py`
  - Establishes a reverse SSH tunnel to the controller for NAT bypassing.
  - Listens for TCP connections on the control port.
  - Receives JSON commands and controls the car.
    
- `/car/run_control_server.sh`
  - Runs the `controler_server.py` with appropriate env variables specified in `.env`.
    
### 2. **Controller (`/controller`)**
All controller related files are in this directory.

- `/controller/show_video.sh`
  - Receives and displays the video stream on the port specified by the first argument.

- `/controller/control_client.py`
  - Connects to the car’s control server.
  - Sends movement commands to the reverse ssh tunnel port.
  - Optionally processes video for obstacle detection.


### 3. **Testbed (`/testbed`)**
Directory to testbed related files and scripts.
  
- `/testbed/add-latency.sh` and `/testbed/remove-latency.sh`
  - Add or remove artificial network latency for demo purposes. Specifically, latency is added/removed inside the UPF2 pod on the node where 5G core is hosted.


### 4. **Environment Examples (`/env_examples`)**
Sample `.env` files for different cars or scenarios.



## Network Connections

This is a high-level view view of the network connections between the car and the controller. First, the car establishes an SSH connection to a publicly available server which acts as the remote controller of the car to setup reverse port forwarding. This is to bypass any NAT between the controller to the car which happens to be the case for 5G open source testbeds. This way, the control commands can be sent  controller's process to the local port `$CONTROLLER_CONTROL_PORT`. The commads then are forwarded to the local port where the car is listening to receive commands. The video stream from the car is sent over UDP to the controller to the port `$CONTROLLER_STREAMING_PORT`.

```
+-------------------+         UDP (Video Stream)              +------------------+
|                   |  -------------------------------------> |                  |
|        Car        |                                         |    Coontroller   |
|                   | <-------- TCP (Control Commands) -------|                  |
+-------------------+     (via the SSH Tunnel established)    +------------------+
```


## References
- For a user-friendly, step-by-step guide, see **JetRacer User Manual.md**.
- [Waveshare JetRacer Pro AI Kit Documentation](https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit)
- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
- [Twisted Python Networking Engine](https://twistedmatrix.com/trac/)
- [tc netem (Linux Traffic Control)](https://wiki.linuxfoundation.org/networking/netem)


## Troubleshooting Guide 

This guide provides solutions to common issues you may encounter when setting up or running the networked robot car system.

### 5G Connection Problems

- 5G module does not blink green.
  - **Solution:**
    - Follow the instructions in the video below.


- 5G module does not connect.
  - **Solution:**
    - Ensure the sim card is present in the 5G moduel's sim slot. 
    - Make sure green LED of the 5G module should be blinking or on.
    - Reset the module and try connecting again

### Video Streaming Problems
- **Error:** `Unable to open video stream.` or no video window appears on the controller.
  - **Solution:**
    - Ensure the car is running `run_camera_video_streamer.sh` and the controller is running `show_video.sh` or the controller Python script.
    - Check that the `CONTROLLER_IP` and `CONTROLLER_STREAMING_PORT` match on both car and controller.

- **Video is choppy or delayed.**
  - **Solution:**
    - Run `wifi-decrease-latency.sh` on the car if using WiFi.
    - Check for network congestion or high latency (use testbed scripts to diagnose).
    - Lower the video resolution or framerate in `stream_video.sh` if needed.

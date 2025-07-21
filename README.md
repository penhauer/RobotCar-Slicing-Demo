# Network Architecture & Flow

---

**A Comprehensive Guide to the Networked Robot Car System**

*For the JetRacer Networks Lab Demo*

---

## Table of Contents
0. [Note on IP Addresses](#note-on-ip-addresses)
1. [Overview](#overview)
2. [Components and Their Network Roles](#components-and-their-network-roles)
    - [Robot Car](#1-robot-car-car)
    - [Client/Server](#2-clientserver-client)
    - [Testbed](#3-testbed-testbed)
    - [Environment Examples](#4-environment-examples-env_examples)
3. [Network Flow Diagram](#network-flow-diagram)
4. [Detailed Script/Config Reference](#detailed-scriptconfig-reference)
5. [How to Use](#how-to-use)
6. [Summary Table](#summary-table)
7. [Best Practices & Notes](#best-practices--notes)
8. [Setup Instructions](#setup-instructions)
9. [NAT Traversal, Port Mapping, and SSH Tunneling](#nat-traversal-port-mapping-and-ssh-tunneling)
10. [USRP Hardware](#usrp-hardware)
11. [Cross-Reference](#cross-reference)
12. [References](#references)

---

## Overview


<img width="8892" height="2416" alt="image" src="https://github.com/user-attachments/assets/0f35b21c-97d9-4abf-91b6-af6e2d9bf80f" />



This project demonstrates a robot car streaming video to a remote server (the client) over a network, with control commands sent back to the car. The setup is designed to work in a 5G testbed with slicing capabilites. Two slices are configured for every UE; a **dedicated URLLC slice** (ultra-reliable low-latency communication) and a **best-effort slice**. Video streamed from UE1 (first car) passes thorugh the dedicated slice1, while for UE2, the traffic goes through the best effort slice2.

The video is streamed to an edge server where controlling commands are sent back to the car; forming a closed control loop. In this case, UE1 is expected to perform better since it is attached to a dedicated slice. Conversely, in case an obstacle is close to UE2 (second car) as it is moving forward, the action to stop the car may not arrive in time to prevent the car from hitting the obstacle.

---


## How to Use

The cars come with both Wi-Fi card and 5G module. Either can be used for internet connectivity.


#### Connecting to 4G/5G testbed


The instructions on how to setup the 5G module can be found [here](https://www.waveshare.com/wiki/SIM8200EA-M2_5G_for_Jetson_Nano#Document). For the 5G module to operate, its driver should be installed on the car.

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

Before the last step, make sure the 5G module's LED is blinking green, indicating the module's ready to connect. Note that the module has a red LED, which indicates the module is powered.

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

#### Connecting to Wi-Fius

To connect to Wi-Fi, simply run:

```
$ sudo nmtui
```


### Car (Controller Server)



### Controller (Controller Client)

**Step-by-step instructions for running the system.**

1. **Set up the car and client with appropriate `.env` files** (copy from `/env_examples/`).
2. **Start the car’s control server and video streamer**:
   ```bash
   ./run_control_server.sh
   ./run_camera_video_streamer.sh
   ```
3. **On the client/server, install requirements and start the client**:
   ```bash
   ./install_client_requirements.sh
   sudo ./run_client.sh
   ```
4. **(Optional) Use testbed scripts to simulate network conditions**:
   ```bash
   ./add-latency.sh
   ./remove-latency.sh
   ```

---



## Components and Their Network Roles

**Understand the function of each part in the system.**

### 1. **Robot Car (`/car`)**
- **Video Streaming**: Uses a GStreamer pipeline (`stream_video.sh`) to capture video from the car’s camera and send it over UDP to the client/server.
- **Control Server**: Runs a Twisted-based TCP server (`control_server.py`) to receive movement commands from the client. Uses a reverse SSH tunnel for NAT traversal.
- **Environment Variables**: Set in `.env` (see Setup Instructions above).
- **Scripts**: See Detailed Script/Config Reference for all script usage and details.

### 2. **Client/Server (`/client`)**
- **Video Reception**: Receives the UDP video stream using a GStreamer pipeline (`show_video.sh`). Optionally, processes the video using OpenCV (`video_processing.py`).
- **Control Client**: Connects to the car’s control server via the reverse SSH tunnel. Sends movement commands (WASD keys) over TCP. Can run in two modes (see Setup Instructions).
- **Scripts**: See Detailed Script/Config Reference for all script usage and details.

### 3. **Testbed (`/testbed`)**
- **Network Slicing and Emulation**: `add-latency.sh` and `remove-latency.sh` are used to simulate different network conditions.

### 4. **Environment Examples (`/env_examples`)**
- Provide sample `.env` files for different cars or scenarios. See Setup Instructions for usage.

---

## Network Flow Diagram

Visualize the data and control flow in the system.

### 1. Network Data Flow (High-Level)

```
+-------------------+         UDP (Video Stream)         +------------------+
|   Jetson Nano     |  --------------------------------> |   PC/Client      |
|   (Robot Car)     |                                    |  (Remote)        |
|                   | <--- TCP (Control Commands) -------|                  |
+-------------------+   (via Reverse SSH Tunnel)         +------------------+
```
**Legend:**
- **UDP (Video Stream):** Jetson Nano → PC/Client (real-time video, e.g., GStreamer)
- **TCP (Control Commands):** PC/Client → Jetson Nano (remote control, via SSH tunnel)

---

### 2. Component Connection Flow

```
+-------------------+
|   Jetson Nano     |
+-------------------+
 |   |   |   |   |   |   |
 |   |   |   |   |   |   |
CSI GPIO I2C USB Power WiFi
 |   |   |   |   |   |   |
 v   v   v   v   v   v   v
+-----+ +-----+ +-----+ +----------------+ +-------------+ +----------+
|Camera| |Motor| |OLED | |Gamepad Receiver| |Battery Pack| |WiFi Mod. |
|      | |Driver| |Disp.| +----------------+ +-------------+ +----------+
+-----+ +-----+ +-----+                                 
      |         |                                       
      +---------+                                       
            |                                           
            v                                           
     +-------------------+                              
     |   WiFi Router     |                              
     +-------------------+                              
            |                                           
            v                                           
     +------------------+                               
     |   PC/Client      |                               
     +------------------+                               
```
**Legend:**
- **CSI, GPIO, I2C, USB, Power, WiFi:** Hardware and network interfaces
- **WiFi Router:** Network hub for communication

---

### 3. Testbed/Network Emulation Flow

```
+-------------------+         +------------------+
|   Jetson Nano     |         |   PC/Client      |
+-------------------+         +------------------+
          |                          ^
          |                          |
          v                          |
   +-------------------+             |
   |   WiFi Router     |-------------+
   +-------------------+
          |
          v
   +-------------------+
   |  Testbed Scripts  |
   | (add/remove       |
   |  latency, etc.)   |
   +-------------------+
```
**Legend:**
- **Testbed Scripts:** Used to emulate network conditions (latency, etc.)

---

### 4. Full System Flow (Detailed)

```
+-------------------+      CSI      +--------+
|                   |-------------->|Camera  |
|                   |               +--------+
|                   |
|                   |      GPIO     +--------------+
|                   |-------------->|Motor Driver  |----+   PWM/Power   +--------+
|                   |               +--------------+    +-------------->|Motors  |
|                   |                                         |
|   Jetson Nano     |      I2C      +-------------+           |
|   (Robot Car)     |-------------->|OLED Display|           |
|                   |               +-------------+           |
|                   |                                         |
|                   |      USB      +----------------+        |
|                   |<-------------|Gamepad Receiver|         |
|                   |               +----------------+        |
|                   |                                         |
|                   |      Power    +-------------+           |
|                   |<-------------|Battery Pack  |           |
+-------------------+               +-------------+           |
        | WiFi                                              WiFi
        v                                                    v
+-------------------+                                 +------------------+
|   WiFi Router     |<------------------------------->|   PC/Client      |
+-------------------+                                 +------------------+
         ^                                                 ^
         |                                                 |
         +------------------- SSH Tunnel ------------------+
         |                                                 |
         +------------------- UDP Video Stream ------------+
```
**Legend:**
- **CSI, GPIO, I2C, USB, Power:** Internal hardware connections
- **WiFi:** Network connection
- **SSH Tunnel:** TCP control commands (PC/Client → Jetson Nano)
- **UDP Video Stream:** Video stream (Jetson Nano → PC/Client)

---

## Detailed Script/Config Reference

**This is the only section with detailed script and configuration file explanations.**

### `/car/.env` (see Setup Instructions)
- Stores network configuration for the car.

### `/car/run_camera_video_streamer.sh`
- Loads `.env`, checks for `SERVER_IP` and `SERVER_STREAMING_PORT`.
- Runs `./stream_video.sh "${SERVER_IP}" "${SERVER_STREAMING_PORT}"`.

### `/car/stream_video.sh`
- GStreamer pipeline:
  ```bash
  gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! ... ! udpsink host="$1" port="$2"
  ```
- Streams H.264 video over UDP to the client.

### `/car/run_control_server.sh`
- Loads `.env`, checks for `SERVER_IP` and `SERVER_CONTROL_PORT`.
- Runs `python3 control_server.py "${SERVER_IP}" "${SERVER_CONTROL_PORT}"`.

### `/car/control_server.py`
- Listens for TCP connections on the control port.
- Receives JSON commands, controls the car.
- Establishes a reverse SSH tunnel to the client/server for NAT traversal.

### `/client/.env` (see Setup Instructions)
- Stores network configuration for the client/server.

### `/client/run_client.sh`
- Loads `.env`, checks for required ports.
- Runs the client Python script with the correct ports.

### `/client/show_video.sh`
- GStreamer pipeline:
  ```bash
  gst-launch-1.0 -vv udpsrc port="${1}" ... ! autovideosink sync=false
  ```
- Receives and displays the video stream.

### `/client/control_client.py`
- Connects to the car’s control server (via SSH tunnel).
- Sends movement commands.
- Optionally processes video for obstacle detection.

### `/testbed/add-latency.sh` and `/testbed/remove-latency.sh`
- Add or remove artificial network latency for test purposes.

---

## Summary Table

| Component        | Protocol | Direction        | Port/Config           | Script/Config                        | Purpose                       |
|------------------|----------|------------------|-----------------------|--------------------------------------|-------------------------------|
| Video Stream     | UDP      | Car → Client     | SERVER_STREAMING_PORT | stream_video.sh, show_video.sh       | Real-time video transmission  |
| Control          | TCP      | Client → Car     | SERVER_CONTROL_PORT   | control_server.py, control_client.py | Remote car control            |
| SSH Tunnel       | TCP      | Car → Client     | (dynamic)             | control_server.py                    | NAT traversal for control     |
| Testbed Latency  | N/A      | N/A              | N/A                   | add-latency.sh, remove-latency.sh    | Network emulation/testing     |

---

## Best Practices & Notes

**Tips for robust and flexible operation.**

- **Reverse SSH tunneling** is essential for NAT traversal, allowing the client to control the car even when the car is behind a firewall or NAT.
- **GStreamer** is used for efficient, low-latency video streaming.
- **Environment variables** make it easy to reconfigure the system for different cars or network setups.
- **Testbed scripts** allow for robust testing under various network conditions, crucial for research and development in networked robotics.

*Best practices are summarized here. For rationale, see the relevant sections above.*

---

## Setup Instructions

**Follow these steps to set up and run the networked robot car system:**

### 1. Prepare Environment Files
- Copy an example environment file from `/env_examples/` to the `/car` and `/client` directories as `.env`.
- Edit the `.env` files as needed for your network setup.
  ```bash
  # Example for the car
  cp env_examples/env_car1 car/.env
  # Example for the client
  cp env_examples/env_car1 client/.env
  # Edit the files to match your server IP and ports
  ```

*Refer to this section for all environment file setup. Troubleshooting and script references will assume you have completed this step.*

### 2. Set Up the Car
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

### 3. Start the Car Services
- Start the control server (enables remote control):
  ```bash
  ./run_control_server.sh
  ```
- Start the video streaming service:
  ```bash
  ./run_camera_video_streamer.sh
  ```

### 4. Set Up the Client/Server
- On the client/server machine, install Python dependencies:
  ```bash
  cd client
  ./install_client_requirements.sh
  ```

### 5. Start the Client
- Run the client to connect to the car and receive video/control:
  ```bash
  sudo ./run_client.sh
  ```
- **Note:** The client requires the `keyboard` Python library, which must be run with super user privileges (sudo).
- The client can run in two modes:
  - **No video processing**: Just displays the video stream.
  - **Video processing**: Processes the video stream for obstacle detection (set `PROCESS_VIDEO=True` in `.env` or pass the flag if supported).
- *Note: Additional client modes and runner script improvements are under development.*

### 6. (Optional) Use Testbed Scripts for Network Emulation
- To add artificial latency to the network (for testing):
  ```bash
  cd testbed
  ./add-latency.sh
  ```
- To remove the artificial latency:
  ```bash
  ./remove-latency.sh
  ```

---

## NAT Traversal, Port Mapping, and SSH Tunneling

### NAT Traversal
Many components in this system are behind NAT (Network Address Translation), which means their private IP addresses are not directly accessible from outside networks. To enable remote control and communication, the system uses SSH tunneling and port forwarding.

### SSH Tunnel Example
To forward a port from a remote machine (e.g., hpc1) to your local machine, use:
```bash
ssh hpc1 -R localhost:9000:localhost:9000
```
This command forwards port 9000 on your local machine to port 9000 on hpc1, allowing you to access services behind NAT.

### Port Mapping Table Example
| Src IP         | Src Port | Dst IP           | Dst Port |
|----------------|----------|------------------|----------|
| 203.0.113.8    | 443      | 198.51.100.8     | 55921    |
| 192.168.50.10  | 9000     | 203.0.113.20     | 9000     |
| 10.0.0.92      | 9000     | 10.0.0.1         | 9000     |

This table shows how a packet's source and destination IP/port can be mapped as it traverses NATs and tunnels. Substitute your actual network addresses as needed.

### Network Flow with NAT and SSH Tunnel
- The car (or USRP) may be on a private subnet (e.g., 10.x.x.x).
- The PC acts as a bridge, with multiple interfaces (e.g., 192.168.x.x, 10.x.x.x, 203.0.113.x).
- SSH tunneling is used to forward control ports from the car to the client, bypassing NAT.
- UDP video and TCP control traffic are mapped through the appropriate ports.

<img width="2837" height="921" alt="image" src="https://github.com/user-attachments/assets/3e0781fb-e4b5-49ba-a7d6-2ca36d2c7a32" />

---

## Cross-Reference
- For a user-friendly, step-by-step guide, see **JetRacer User Manual.md**.
- For troubleshooting, see **Troubleshooting Guide.md**.

---

## References
- [Waveshare JetRacer Pro AI Kit Documentation](https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit)
- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
- [Twisted Python Networking Engine](https://twistedmatrix.com/trac/)
- [tc netem (Linux Traffic Control)](https://wiki.linuxfoundation.org/networking/netem)

---

# Note on IP Addresses
All IP addresses in this document are **examples**. Replace them with the actual addresses used in your network or testbed. For public IP examples, we use documentation ranges (e.g., 203.0.113.x per RFC5737).

---


# Troubleshooting Guide 

This guide provides solutions to common issues you may encounter when setting up or running the networked robot car system.

---

## 1. Environment File Issues
- **Error:** `.env file does not exist.`
  - **Solution:**
    - See Setup Instructions above for how to copy and edit `.env` files.

- **Error:** `SERVER_IP`, `SERVER_CONTROL_PORT`, or `SERVER_STREAMING_PORT` not present in the environmental variables.
  - **Solution:**
    - See Setup Instructions above for how to edit `.env` files.

---

## 2. Video Streaming Problems
- **Error:** `Unable to open video stream.` or no video window appears on the client.
  - **Solution:**
    - Ensure the car is running `run_camera_video_streamer.sh` and the client is running `show_video.sh` or the client Python script.
    - Check that the `SERVER_IP` and `SERVER_STREAMING_PORT` match on both car and client.
    - Make sure the network allows UDP traffic on the streaming port.
    - If using 5G, verify the car has a valid network connection (see 5G section).

- **Video is choppy or delayed.**
  - **Solution:**
    - Run `wifi-decrease-latency.sh` on the car if using WiFi.
    - Check for network congestion or high latency (use testbed scripts to diagnose).
    - Lower the video resolution or framerate in `stream_video.sh` if needed.

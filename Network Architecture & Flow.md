 # Network Architecture & Flow

## Overview

This project demonstrates a robot car streaming video to a remote server (the client) over a network, with control commands sent back to the car. The setup is designed to work in a testbed with two network slices: a **dedicated URLLC slice** (ultra-reliable low-latency communication) and a **best-effort slice**. The car is typically behind a NAT, so reverse SSH tunneling is used for control. Video is streamed using GStreamer pipelines over UDP, and control commands are sent over TCP.

---

## Components and Their Network Roles

### 1. **Robot Car (`/car`)**

- **Video Streaming**
  - Uses a GStreamer pipeline (`stream_video.sh`) to capture video from the car’s camera and send it over UDP to the client/server.
  - The destination IP and port are set via environment variables (`SERVER_IP`, `SERVER_STREAMING_PORT`).
  - The video is encoded as H.264 and sent as RTP packets.

- **Control Server**
  - Runs a Twisted-based TCP server (`control_server.py`) to receive movement commands from the client.
  - The server listens on a port specified by `SERVER_CONTROL_PORT`.
  - Since the car is behind NAT, it establishes a **reverse SSH tunnel** to the client/server, forwarding the control port.

- **Environment Variables**
  - Set in `.env` (see `/env_examples/env_car1` and `/env_examples/env_car2`):
    - `SERVER_IP`: The client/server’s IP or hostname.
    - `SERVER_CONTROL_PORT`: TCP port for control commands.
    - `SERVER_STREAMING_PORT`: UDP port for video streaming.

- **Scripts**
  - `run_camera_video_streamer.sh`: Loads environment variables and starts video streaming.
  - `run_control_server.sh`: Loads environment variables and starts the control server with reverse SSH tunneling.
  - `wifi-decrease-latency.sh`: Disables WiFi power saving to reduce jitter.
  - `low_power.sh`: Adjusts power settings (not directly network-related).

---

### 2. **Client/Server (`/client`)**

- **Video Reception**
  - Receives the UDP video stream using a GStreamer pipeline (`show_video.sh`).
  - Listens on the port specified by `SERVER_STREAMING_PORT`.
  - Optionally, processes the video using OpenCV (`video_processing.py`).

- **Control Client**
  - Connects to the car’s control server via the reverse SSH tunnel.
  - Sends movement commands (WASD keys) over TCP.
  - Can run in two modes:
    - **No video processing**: Just displays the video.
    - **Video processing**: Processes the video stream to detect obstacles and can stop the car if an obstacle is detected.

- **Scripts**
  - `run_client.sh`: Loads environment variables, checks for required ports, and starts the client.
  - `install_client_requirements.sh`: Sets up the Python environment and dependencies.

---

### 3. **Testbed (`/testbed`)**

- **Network Slicing and Emulation**
  - `add-latency.sh`: Adds artificial network latency (e.g., 300ms) to a specific Kubernetes pod using `tc netem`.
  - `remove-latency.sh`: Removes the artificial latency.
  - These scripts are used to simulate different network conditions and test the system’s robustness.

---

### 4. **Environment Examples (`/env_examples`)**

- Provide sample `.env` files for different cars or scenarios.
- Example:
  ```env
  SERVER_IP=hpc1
  SERVER_CONTROL_PORT=9999
  SERVER_STREAMING_PORT=5001
  ```
- These files are copied to `.env` in the relevant directory and sourced by the scripts.

---

## **Network Flow Diagram**

```
+----------------+         UDP (Video Stream)         +------------------+
|   Robot Car    |  --------------------------------> |   Client/Server  |
| (Behind NAT)   |                                    | (Edge/Remote)    |
|                | <--- TCP (Control Commands) -------|                  |
+----------------+   (via Reverse SSH Tunnel)         +------------------+
```

- **Video Stream**: Car → Client (UDP, RTP/H.264, GStreamer)
- **Control**: Client → Car (TCP, JSON, Twisted, via SSH tunnel)

---

## **Detailed Script/Config Reference**

### `/car/.env` (see `/env_examples/`)
- Stores network configuration for the car.
- Used by all car-side scripts.

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

### `/client/.env` (see `/env_examples/`)
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

## **How to Use**

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

## **Summary Table**

| Component        | Protocol | Direction        | Port/Config           | Script/Config                        | Purpose                       |
|------------------|----------|------------------|-----------------------|--------------------------------------|-------------------------------|
| Video Stream     | UDP      | Car → Client     | SERVER_STREAMING_PORT | stream_video.sh, show_video.sh       | Real-time video transmission  |
| Control          | TCP      | Client → Car     | SERVER_CONTROL_PORT   | control_server.py, control_client.py | Remote car control            |
| SSH Tunnel       | TCP      | Car → Client     | (dynamic)             | control_server.py                    | NAT traversal for control     |
| Testbed Latency  | N/A      | N/A              | N/A                   | add-latency.sh, remove-latency.sh    | Network emulation/testing     |

---

## **Best Practices & Notes**

- **Reverse SSH tunneling** is essential for NAT traversal, allowing the client to control the car even when the car is behind a firewall or NAT.
- **GStreamer** is used for efficient, low-latency video streaming.
- **Environment variables** make it easy to reconfigure the system for different cars or network setups.
- **Testbed scripts** allow for robust testing under various network conditions, crucial for research and development in networked robotics.

## **Setup Instructions**

Follow these steps to set up and run the networked robot car system:

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

### 2. Set Up the Car
- On the robot car, install required Python dependencies:
  ```bash
  cd car
  python3 -m venv venv
  source venv/bin/activate
  pip3 install -r requirements.txt
  # Install the jetracer package if not already installed (see README.md)
  ```
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
- The client can run in two modes:
  - **No video processing**: Just displays the video stream.
  - **Video processing**: Processes the video stream for obstacle detection (set `PROCESS_VIDEO=True` in `.env` or pass the flag if supported).

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

If you encounter issues, refer to the README.md for troubleshooting and additional details.

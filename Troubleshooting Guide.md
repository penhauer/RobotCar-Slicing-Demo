# Troubleshooting Guide

This guide provides solutions to common issues you may encounter when setting up or running the networked robot car system.

---

## 1. Environment File Issues
- **Error:** `.env file does not exist.`
  - **Solution:**
    - Copy an example file from `/env_examples/` to the relevant directory (`car/` or `client/`) and rename it `.env`.
    - Edit the file to match your network setup.
    - Example:
      ```bash
      cp env_examples/env_car1 car/.env
      cp env_examples/env_car1 client/.env
      ```


- **Error:** `SERVER_IP`, `SERVER_CONTROL_PORT`, or `SERVER_STREAMING_PORT` not present in the environmental variables.
  - **Solution:**
    - Open your `.env` file and ensure all required variables are set and not commented out.

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
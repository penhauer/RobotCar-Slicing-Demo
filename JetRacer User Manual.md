# JetRacer User Manual

---

**A Comprehensive Guide to Setup, Operation, and Maintenance**

*For the Waveshare JetRacer Pro AI Kit*

---

## Table of Contents
1. [Visual Flowcharts](#visual-flowcharts)
2. [Hardware Setup & Assembly](#1-hardware-setup--assembly)
3. [Preparing the SD Card](#2-preparing-the-sd-card)
4. [First Boot & Initial Connections](#3-first-boot--initial-connections)
5. [Software Configuration & Updates](#4-software-configuration--updates)
6. [Operating the Car](#5-operating-the-car)
7. [Troubleshooting](#6-troubleshooting)
8. [Maintenance & Safety](#7-maintenance--safety)
9. [References](#references)

---

### Operation Flow

```
+---------------------------+
|        Setup Phase        |
+---------------------------+
| Power On Jetson Nano      |
| Boot Jetson Nano OS       |
| Connect via Jupyter Lab   |
| Connect to WiFi           |
| Copy/Edit .env Files      |
| Activate Python Env       |
| Install Requirements      |
| (Optional) Update System  |
+---------------------------+
             |
             v
+---------------------------+
|   Select Operation Mode   |
+---------------------------+
      |             |
      v             v
+----------------+  +----------------------+
| Manual Control |  |   Data Collection    |
| (Teleop NB)    |  +----------------------+
+----------------+  | Run Data Coll NB     |
      |             | Save Training Data   |
      |             | Run Model Train NB   |
      |             | Evaluate Model       |
      |             +----------------------+
      |                     |
      |                     v
      |           +--------------------------+
      |           |  Model Satisfactory?     |
      |           +--------------------------+
      |             |                |
      |             | Yes            | No
      |             v                v
      |     +----------------+   +----------------------+
      |     | Autonomous NB  |<--| Collect More Data    |
      |     +----------------+   +----------------------+
      |             |
      +-------------+
```

**Legend:**
- **NB**: Notebook (in Jupyter Lab)
- **Manual Control**: Teleoperation
- **Data Coll NB**: Data Collection Notebook
- **Model Train NB**: Model Training Notebook
- **Autonomous NB**: Autonomous Driving Notebook

### System Architecture

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

## 1. Hardware Setup & Assembly

**Get started by assembling your JetRacer car.**

### 1.1. Unboxing & Parts Checklist
- JetRacer chassis and frame
- Jetson Nano Developer Kit (not included in some kits)
- Motors and wheels
- Motor driver board
- Battery holder (for four 18650 batteries)
- OLED display (if included)
- Camera module
- Cables, screws, and standoffs
- Gamepad controller and receiver

### 1.2. Assemble the Chassis
- Follow the assembly manual to:
  - Attach the motors to the chassis using screws and brackets.
  - Mount the wheels onto the motor shafts.
  - Secure the Jetson Nano onto the chassis using standoffs.
  - Connect the motor driver board to the motors and Jetson Nano GPIO pins.
  - Install the battery holder and secure it in place.
  - Mount the camera module to the front of the car and connect it to the Jetson Nano’s CSI port.
  - Connect the OLED display (if present) to the appropriate header.
  - Double-check all connections for tightness and correctness.

### 1.3. Install the Batteries
- Use four high-quality 18650 batteries (without protection plate).
- Insert the batteries into the holder, ensuring correct polarity.
- Charge the batteries fully before first use (recommended voltage per battery: 4.2V when fully charged).

---

## 2. Preparing the SD Card

**Install the JetRacer operating system and software.**

### 2.1. Download the JetRacer Image
- Download the official JetRacer SD card image from the [Waveshare resources page](https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit#Image).
- Unzip the downloaded image file.

### 2.2. Flash the Image to the SD Card
- Use a tool like [Balena Etcher](https://www.balena.io/etcher/) to write the image to a microSD card (minimum 64GB recommended).
- Insert the SD card into your computer, select the image file in Etcher, and flash it to the card.
- Safely eject the SD card after flashing.

### 2.3. Insert the SD Card
- Insert the prepared microSD card into the slot on the underside of the Jetson Nano module.

---

## 3. First Boot & Initial Connections

**Power on your JetRacer and connect for the first time.**

### 3.1. Powering On
- Ensure all hardware is assembled and batteries are installed.
- Turn on the power switch located on the car chassis.
- The OLED display (if present) should light up, showing IP address, memory, and power status.

### 3.2. Connecting to Your PC
- Use a micro USB cable to connect the Jetson Nano to your PC for initial setup.
- Wait for the Jetson Nano to boot up (may take a few minutes on first boot).

### 3.3. Accessing Jupyter Lab
- On your PC, open a web browser and go to `http://192.168.55.1:8888`.
- Log in with the default password: `jetson`.
- If you do not see the Jupyter Lab interface, ensure your PC is connected to the Jetson Nano via USB and that the Nano is powered on.

### 3.4. Connecting to WiFi (Recommended)
- In Jupyter Lab, open a new terminal (`File` → `New` → `Terminal`).
- Use the following commands to scan and connect to WiFi:
  ```sh
  sudo nmcli device wifi list
  sudo nmcli device wifi connect <SSID> password <your_password>
  ```
- Confirm connection with:
  ```sh
  ifconfig
  ping google.com
  ```

---

## 4. Software Configuration & Updates

**Keep your JetRacer up to date and install extra software if needed.**

### 4.1. Update System Packages (Optional but Recommended)
- In the Jupyter Lab terminal, run:
  ```sh
  sudo apt-get update
  sudo apt-get upgrade
  ```

### 4.2. Install Additional Python Packages (If Needed)
- If you need extra packages, use pip:
  ```sh
  pip3 install <package_name>
  ```

---

## 5. Operating the Car

**Drive manually, collect data, and run autonomous driving.**

### 5.1. Manual Control (Teleoperation)
- Plug the gamepad receiver into your PC (not the Jetson Nano).
- Test the gamepad at [html5gamepad.com](https://html5gamepad.com/) and note the device index.
- In Jupyter Lab, open `/jetracer/notebooks/teleoperation.ipynb` and run the cells to enable manual control.
- Use the left joystick to steer and the right joystick to control speed.

### 5.2. Data Collection for AI
- Open `/jetracer/notebooks/interactive-regression.ipynb` in Jupyter Lab.
- Use manual control to drive the car and collect images/steering data.
- Save data for several laps around your track.

### 5.3. Training and Autonomous Driving
- In the same notebook, set the number of epochs and train the model using your collected data.
- After training, evaluate the model’s performance.
- Open `/jetracer/notebooks/road_following.ipynb` and run it to enable autonomous driving.
- Adjust parameters (steering offset, throttle) as needed for best results.

---

## 6. Troubleshooting

**Solve common problems with your JetRacer.**

- **Car Does Not Move:**
  - Check the ESC switch on the chassis; toggle if needed.
  - Ensure batteries are charged and installed correctly.
  - Verify all cables and connections.
- **Camera Issues:**
  - If the camera fails, restart it with: `sudo systemctl restart nvargus-daemon` in a terminal.
- **Gamepad Not Detected:**
  - Make sure the receiver is plugged into your PC, not the Jetson Nano.
  - Test at [html5gamepad.com](https://html5gamepad.com/).
- **Software Errors:**
  - Ensure you are using the correct JetRacer image and software versions as per the documentation.

---

## 7. Maintenance & Safety

**Keep your JetRacer in top condition and operate safely.**

- **Battery Care:**
  - Use high-quality 18650 batteries (e.g., Sanyo, Panasonic).
  - Recharge when voltage drops below 10V.
  - Do not use batteries with a protective plate.
- **Power Adapter:**
  - Only use the 8.4V adapter for charging batteries, not for powering the Jetson Nano directly.
- **General Care:**
  - Regularly check for loose connections and physical damage.
  - Store the car in a dry, safe place when not in use.

---

## References
- [Waveshare JetRacer Pro AI Kit Documentation](https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit)
- [Waveshare JetRacer Resource Page](https://www.waveshare.com/wiki/JetRacer_Pro_AI_Kit#Image)
- [Balena Etcher](https://www.balena.io/etcher/)
- [HTML5 Gamepad Tester](https://html5gamepad.com/) 8`
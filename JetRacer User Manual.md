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
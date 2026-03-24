# Ball Balancing Robot

A high-performance ball-balancing platform built on a 3RRS (Revolute-Revolute-Spherical) parallel robot architecture. This repository contains the mathematical models, 3D simulation environment, and the hardware control logic for a Raspberry Pi-based implementation.

## Features

- **Decoupled Mathematical Model:** Standalone `robot_kinematics` package for both Direct and Inverse kinematics.
- **3D Visualization:** Real-time simulation using Tkinter and Matplotlib to verify kinematics and platform range of motion.
- **Control Theory:** Phase-margin based PID design for stable ball balancing.
- **Computer Vision:** HSV-based color detection pipeline for real-time ball tracking.
- **Hardware Integration:** Servo control logic optimized for Raspberry Pi using `gpiozero`.

## Project Structure

- `src/`: Core source code.
    - `robot_kinematics/`: The mathematical heart of the robot (Direct/Inverse IK).
    - `gui/`: Simulation interface, 3D rendering, and configuration tools.
    - `pi/`: Core hardware control logic (PID, Raspberry Pi specific kinematics).
    - `config/`: Centralized robot dimensions and physical parameters.
    - `tools/`: Independent utility scripts (FPS counter, HSV selector, Video stream).
    - `tests/`: Unit tests and mathematical consistency checks.
- `docs/`: Data sheets, research papers, and technical documentation.
- `simulation_requirements.txt`: Dependencies for the simulation environment.
- `raspberry_requirements.txt`: Dependencies for the physical Raspberry Pi robot.

## Getting Started

### 1. Setup Virtual Environment
```bash
python -m venv sim_venv
source sim_venv/bin/activate
pip install -r simulation_requirements.txt
```

### 2. Run the Simulation
```bash
cd src
python gui/launch_gui.py
```

### 3. Run Validation Tests
To ensure the mathematical models are behaving correctly:
```bash
source sim_venv/bin/activate
python src/tests/test_main.py
```

## Hardware Setup
*(To be detailed: Raspberry Pi 4/5, PiCamera, 3x High-Torque Servos)*

### Connecting via Direct Ethernet (Headless)
If you are connected directly to the Raspberry Pi via Ethernet without a router, follow these steps to find its IP address:

1. **Find your local Ethernet interface:**
   ```bash
   ip addr
   ```
   Identify the interface connected to the Pi (e.g., `enp0s20f0...` or `eth0`).

2. **Locate the Pi's IP address:**
   Use the ARP table to see devices connected to your machine:
   ```bash
   arp -a
   ```
   Look for an entry on your Ethernet interface. Raspberry Pi MAC addresses typically start with `b8:27:eb` (Pi 3) or `dc:a6:32` / `e4:5f:01` (Pi 4/5).

3. **SSH into the Pi:**
   ```bash
   ssh <username>@<ip_address>
   # Example: ssh eli@10.42.0.143
   ```

### Setting up VNC (Headless)
To access the desktop interface remotely without a monitor:

1. **Enable VNC and Configure Display (via SSH):**
   Run the following commands to enable VNC, switch to X11 (required for RealVNC), and enable auto-login:
   ```bash
   # Enable VNC
   sudo raspi-config nonint do_vnc 0
   # Switch to X11 (Required for Pi 4/5 on Bookworm/Trixie)
   sudo raspi-config nonint do_wayland W1
   # Enable Desktop Auto-login
   sudo raspi-config nonint do_boot_behaviour B4
   ```

2. **Set a Headless Resolution:**
   If you get a "Cannot currently show desktop" error, you must force a resolution:
   - Run `sudo raspi-config`
   - Go to **Display Options** > **VNC Resolution** (or **Resolution**)
   - Select a resolution (e.g., 1280x720) and **Finish**.

3. **Reboot the Pi:**
   ```bash
   sudo reboot
   ```

4. **Connect from Laptop:**
   Use [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/) and enter the Pi's IP address.

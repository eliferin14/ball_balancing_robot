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
    - `pi/`: Hardware-specific modules (PID controller, Camera pipeline, FPS counters).
    - `tests/`: Unit tests and mathematical consistency checks.
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

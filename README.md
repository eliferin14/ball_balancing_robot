# Ball Balancing Robot

This repository contains the code for a real ball-balancing robot built on a Raspberry Pi. It includes a 3D simulation for kinematics verification and the control logic for the physical hardware.

## Project Structure

- `src/`: Core source code.
    - `gui/`: Simulation interface and visualization.
    - `pi/`: Hardware-specific code (PID, Camera Pipeline, etc.).
- `simulation_requirements.txt`: Dependencies for the simulation.
- `raspberry_requirements.txt`: Dependencies for the physical robot.

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
python test.py
```

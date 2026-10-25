# PC Setup & Usage

Instructions to set up and run the simulation environment, camera stream, and tests on a development PC.

## 1. Virtual Environment Setup

1. Create and activate a Python virtual environment (Python >= 3.11):
   ```bash
   python3 -m venv --system-site-packages .venv
   source .venv/bin/activate
   ```

2. Install dependencies for simulation and development:
   ```bash
   pip install --upgrade pip
   pip install -e ".[sim,dev]"
   ```

## 2. Running the System

Launch the multi-process orchestrator from the project root:

```bash
# Demo mode (default: producer/consumer test over Zenoh)
python -m src.main --mode demo

# Simulation mode (runs CameraManager with videotestsrc by default)
python -m src.main --mode sim

# Simulation mode with video file
python -m src.main --mode sim --video-file videos/test_hw_enc.mp4

# Or via the CLI entrypoint
ball-sim
```

To stop the system, press **`Ctrl+C`**.

## 3. Viewing the Live Camera Stream

In a separate terminal (with the venv activated), run the standalone OpenCV viewer:

```bash
python -m src.tools.view_camera
```

Press **`q`** inside the display window to close the viewer.

## 4. Running Tests

Run the test suite:
```bash
pytest tests/ -v
```

Run code formatting and linting:
```bash
ruff check src/ tests/
```


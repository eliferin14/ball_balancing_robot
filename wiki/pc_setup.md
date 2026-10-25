# PC Setup, Vision Processing & Debug Guide

Instructions to set up and run the simulation environment, offload vision processing from the Raspberry Pi, and inspect real-time ball detection on your development PC.

---

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

---

## 2. Remote Processing & Live Debug Visualization (PC + Raspberry Pi)

When the Raspberry Pi is running in hardware mode (`python -m src.main --mode pi-hw`), you can offload vision detection and motor control to your PC.

### Run Ball Detection with Live Debug Window:
```bash
python -m src.main --mode pc-proc --zenoh-endpoint tcp://<RASPBERRY_IP>:7447 --debug-window
```

- **Zero Latency**: Frame delivery is decoupled from processing so incoming frames are never queued.
- **Selective Color Overlay**: The entire scene is shown in Black & White (grayscale) except for the largest connected component of the detected ball, which remains in full color.
- **Tracking Visuals**: Green tracking circle, red centroid dot, position coordinates `(x, y)`, and past trajectory motion path are drawn directly on screen.
- Press **`q`** in the OpenCV window or **`Ctrl+C`** in the terminal to exit cleanly.

---

## 3. Local Simulation Mode

To test full end-to-end vision and control purely on your PC without hardware:

```bash
python -m src.main --mode sim --debug-window
```
*Uses synthetic `videotestsrc` frames (or a custom video file specified in `src/config/camera/sim.yaml`).*

---

## 4. Standalone Raw Camera Stream Viewer

If you only want to inspect the camera angle and raw video feed without running the ball detector:

```bash
# Connect to Raspberry Pi stream
python -m src.tools.view_camera --endpoint tcp://<RASPBERRY_IP>:7447

# Or view local simulation stream
python -m src.tools.view_camera
```

---

## 5. Ball Detector Configuration

All detection parameters are centralized in `src/config/ball_detector/default.yaml`:

```yaml
input_frame_topic: "robot/camera/frame"
output_position_topic: "robot/ball/position"
strategy: "hsv"
display_debug_window: false
debug_window_name: "Ball Detection Debug"

# Parameters for HSV color thresholding strategy (Green filter)
hsv:
  hue_min: 35.0
  hue_max: 85.0
  sat_min: 50.0
  sat_max: 255.0
  val_min: 50.0
  val_max: 255.0
  closure_kernel_size: 5
  min_area: 20.0       # Minimum pixel area for largest connected component
  path_length: 20      # Number of historic trail points to display
```

- **`min_area`**: Connected Component Analysis rejects any blob whose area is below this threshold, reporting `detected: false`.
- **`display_debug_window`**: Can be set to `true` in the file or overridden at runtime via the `--debug-window` CLI flag.

---

## 6. Running Tests & Quality Checks

Run the automated test suite (17 tests covering unit detection, zero-copy Zenoh messaging, and process lifecycles):
```bash
pytest tests/ -v
```

Linting and code style:
```bash
ruff check src/ tests/
```

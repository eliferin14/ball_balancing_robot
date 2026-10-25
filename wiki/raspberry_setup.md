# Raspberry Pi Setup & Hardware Guide

This project runs on a Raspberry Pi 3B+ (or newer) running RaspiOS Trixie with a Raspberry Pi Camera Module.

---

## 1. Prerequisites & GStreamer Installation

Install GStreamer plugins, system tools, and libcamera pipeline handlers:

```bash
sudo apt update
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-libcamera
```

To test camera functionality with a local HDMI display:
```bash
gst-launch-1.0 libcamerasrc ! video/x-raw,format=NV12,width=320,height=240,framerate=30/1 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! autovideosink sync=false
```

---

## 2. Python Virtual Environment Setup

1. Install system Python packages (required for GStreamer `gi` bindings):
   ```bash
   sudo apt install -y python3-venv python3-pip python3-gi python3-gst-1.0
   ```

2. Create virtual environment with `--system-site-packages`:
   ```bash
   python3 -m venv --system-site-packages .venv
   source .venv/bin/activate
   ```

3. Install project dependencies:
   ```bash
   pip install --upgrade pip
   pip install -e ".[pi]"
   ```

---

## 3. Running on Raspberry Pi

### Option A: Hardware Interface Only (Recommended for PC Offloading)
Runs camera acquisition (`CameraManager`) and motor actuators (`PiMotorActuator`), while offloading computer vision and ball detection to a development PC:

```bash
python -m src.main --mode pi-hw
```
*The local Zenoh router automatically listens on `tcp/0.0.0.0:7447` to accept network connections from your PC.*

### Option B: Standalone Mode (Full On-Board Processing)
Runs camera acquisition, on-board ball detection, and motor control directly on the Raspberry Pi:

```bash
python -m src.main --mode pi
```

---

## 4. Hardware Camera Configuration

Camera settings for the real hardware are configured in `src/config/camera/real.yaml`:

```yaml
output_frame_topic: "robot/camera/frame"
source_type: "real"
width: 320
height: 240
framerate: 30
device: null     # Set to null to use libcamerasrc, or "/dev/video0" for V4L2
hflip: true      # Flips the camera feed horizontally
loop_rate_hz: 60.0
```

To stop the system cleanly, press **`Ctrl+C`**. If hanging due to a previous crash, run `pkill -9 -f "src.main"`.

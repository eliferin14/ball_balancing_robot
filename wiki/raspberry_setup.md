# Raspberry setup

This project runs on a Raspberry Pi 3B+ running RaspiOS Trixie

## Software setup

To correctly setup the board, the first step is to flash the image on an SD card using Raspberry Imager

Then setup SSH and (optionally) VNC

### Gstreamer

The project uses a Raspberry Camera module, and it reads the video stream using gstreamer

To install GStreamer run the command 

```bash
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-libcamera 
```

To test if everything works (need a monitor connected to the RPi):

```bash
gst-launch-1.0 libcamerasrc ! video/x-raw,format=NV12,width=320,height=240,framerate=30/1 ! queue max-size-buffers=1 leaky=downstream ! videoconvert ! autovideosink sync=false
```

### Python Virtual Environment

To set up the Python environment on the Raspberry Pi:

1. Install system prerequisites (enables access to camera and GStreamer bindings):
   ```bash
   sudo apt install python3-venv python3-pip python3-gi python3-gst-1.0
   ```

2. Create a virtual environment with `--system-site-packages` so system GStreamer bindings (`gi`) are accessible:
   ```bash
   python3 -m venv --system-site-packages .venv
   source .venv/bin/activate
   ```

3. Install the project with Raspberry Pi dependencies in editable mode:
   ```bash
   pip install --upgrade pip
   pip install -e ".[pi]"
   ```


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
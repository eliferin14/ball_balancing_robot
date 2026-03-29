#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gst_cv_pipeline.py - Minimal GStreamer -> OpenCV -> GStreamer display pipeline.

The capture pipeline acquires frames at the camera's native resolution, resizes
them to the requested output resolution via videoscale, and converts to BGR so
OpenCV receives BGR directly. The display pipeline accepts BGR frames from
appsrc, converts them back to a renderer-friendly format, and shows them via
autovideosink.

Usage:
    python3 gst_cv_pipeline.py [--device /dev/videoX]
                               [--capture-width W] [--capture-height H]
                               [--output-width W]  [--output-height H]
"""

import argparse
import subprocess
import sys

import numpy as np

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst, GstApp, GLib


# ==============================================================================
#  CAPTURE SETTINGS
# ==============================================================================

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
CAPTURE_FORMAT = "UYVY"  # native pixel format from the camera
APPSINK_FORMAT = "BGR"  # format delivered to appsink (and OpenCV)
APPSRC_FORMAT = "BGR"  # format pushed from appsrc (OpenCV output)
DISPLAY_FORMAT = "RGB"  # format autovideosink receives after conversion
FRAMERATE_NUM = 60
FRAMERATE_DEN = 1
APPSINK_MAX_BUFFERS = 1  # keep only the latest frame
APPSRC_MAX_BUFFERS = 1

FALLBACK_DEVICE = "videotestsrc"
DEVICE_CANDIDATES = ["See3CAM_CU55", "See3CAM_24CUG", "Arducam"]


# ==============================================================================
#  DEVICE DISCOVERY
# ==============================================================================


def find_device() -> str: 
    try:
        output = subprocess.check_output(
            ["v4l2-ctl", "--list-devices"], stderr=subprocess.DEVNULL, text=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[WARN] v4l2-ctl unavailable; using videotestsrc.")
        return FALLBACK_DEVICE

    current_label = ""
    device_map: list[tuple[str, str]] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("/dev/"):
            if current_label:
                device_map.append((stripped, current_label))
        else:
            current_label = stripped

    for candidate in DEVICE_CANDIDATES:
        for path, label in device_map:
            if candidate.lower() in label.lower():
                print(f"[INFO] Matched '{candidate}' -> {path} ({label})")
                return path

    print("[WARN] No matching device; using videotestsrc.")
    return FALLBACK_DEVICE


# ==============================================================================
#  PIPELINE STRINGS
# ==============================================================================


def capture_pipeline_str(
    device: str,
    capture_width: int,
    capture_height: int,
    output_width: int,
    output_height: int,
) -> str:
    """
    Capture at (capture_width x capture_height), resize to
    (output_width x output_height) via videoscale, and deliver BGR frames
    to appsink.
    """
    resize_caps = f"video/x-raw,width={output_width},height={output_height}"
    if device == FALLBACK_DEVICE:
        return (
            f"videotestsrc ! "
            f"video/x-raw,width={capture_width},height={capture_height},"
            f"framerate={FRAMERATE_NUM}/{FRAMERATE_DEN} ! "
            f"videoscale ! {resize_caps} ! "
            f"videoconvert ! video/x-raw,format={APPSINK_FORMAT} ! "
            f"appsink name=sink emit-signals=true "
            f"max-buffers={APPSINK_MAX_BUFFERS} drop=true sync=false"
        )
    return (
        f"v4l2src device={device} ! "
        f"video/x-raw,format={CAPTURE_FORMAT},"
        f"width={capture_width},height={capture_height} ! "
        f"videoscale ! {resize_caps} ! "
        f"videoconvert ! video/x-raw,format={APPSINK_FORMAT} ! "
        f"appsink name=sink emit-signals=true "
        f"max-buffers={APPSINK_MAX_BUFFERS} drop=true sync=false"
    )


def display_pipeline_str(width: int, height: int) -> str:
    """Accept BGR frames from appsrc, convert to RGB, and display."""
    return (
        f"appsrc name=src "
        f"caps=video/x-raw,format={APPSRC_FORMAT},"
        f"width={width},height={height},"
        f"framerate={FRAMERATE_NUM}/{FRAMERATE_DEN} "
        f"format=time is-live=true block=false "
        f"max-buffers={APPSRC_MAX_BUFFERS} ! "
        f"videoconvert ! "  # video/x-raw,format={DISPLAY_FORMAT} ! "
        f"autovideosink sync=false"
    )


# ==============================================================================
#  OPENCV PROCESSING - replace process_frame with any per-frame logic
# ==============================================================================


def process_frame(bgr_frame: np.ndarray) -> np.ndarray:
    """
    Receives a BGR frame from the capture pipeline and returns a BGR frame.
    Replace the body with any OpenCV processing; the only contract is that
    the returned array has the same (H, W, 3) shape and dtype as the input.
    """
    return bgr_frame


# ==============================================================================
#  PIPELINE RUNNER
# ==============================================================================


class Pipeline:
    def __init__(
        self,
        device: str,
        capture_width: int,
        capture_height: int,
        output_width: int,
        output_height: int,
        loop: GLib.MainLoop,
    ):
        self._output_width = output_width
        self._output_height = output_height
        self._pts = 0
        self._frame_duration = Gst.SECOND * FRAMERATE_DEN // FRAMERATE_NUM
        self._loop = loop
        self._stopping = False  # guard: only shut down once

        # -- capture pipeline --------------------------------------------------
        cap_str = capture_pipeline_str(
            device, capture_width, capture_height, output_width, output_height
        )
        print(f"[INFO] Capture : {cap_str}")
        self._cap = Gst.parse_launch(cap_str)

        sink = self._cap.get_by_name("sink")
        sink.connect("new-sample", self._on_new_sample)

        # -- display pipeline --------------------------------------------------
        disp_str = display_pipeline_str(output_width, output_height)
        print(f"[INFO] Display : {disp_str}")
        self._disp = Gst.parse_launch(disp_str)
        self._src = self._disp.get_by_name("src")

        # -- buses -------------------------------------------------------------
        # Capture bus: errors only (no window to close here).
        cap_bus = self._cap.get_bus()
        cap_bus.add_signal_watch()
        cap_bus.connect("message::error", self._on_bus_error)

        # Display bus: errors AND EOS both mean the window was closed or the
        # sink shut down, so both trigger a clean exit.
        disp_bus = self._disp.get_bus()
        disp_bus.add_signal_watch()
        disp_bus.connect("message::error", self._on_display_ended)
        disp_bus.connect("message::eos", self._on_display_ended)

    # -- start / stop ----------------------------------------------------------

    def start(self):
        for pl, name in ((self._disp, "display"), (self._cap, "capture")):
            ret = pl.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                print(f"[FATAL] {name} pipeline failed to start.")
                sys.exit(1)
        print("[INFO] Pipelines running - press Ctrl-C to stop.")

    def stop(self):
        self._src.emit("end-of-stream")
        for pl in (self._cap, self._disp):
            pl.set_state(Gst.State.NULL)

    # -- frame callback --------------------------------------------------------

    def _on_new_sample(self, sink) -> Gst.FlowReturn:
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR

        buf = sample.get_buffer()
        caps = sample.get_caps()
        s = caps.get_structure(0)
        w = s.get_int("width")[1]
        h = s.get_int("height")[1]

        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return Gst.FlowReturn.ERROR

        bgr = np.frombuffer(mapinfo.data, dtype=np.uint8).reshape((h, w, 3))
        buf.unmap(mapinfo)

        # -- OpenCV processing -------------------------------------------------
        result = process_frame(bgr)  # BGR in, BGR out
        # ----------------------------------------------------------------------

        self._push_frame(result)
        return Gst.FlowReturn.OK

    # -- push processed frame back into GStreamer ------------------------------

    def _push_frame(self, bgr: np.ndarray):
        if self._stopping:
            return
        data = bgr.tobytes()
        gst_buf = Gst.Buffer.new_allocate(None, len(data), None)
        gst_buf.fill(0, data)
        gst_buf.pts = self._pts
        gst_buf.duration = self._frame_duration
        self._pts += self._frame_duration

        ret = self._src.emit("push-buffer", gst_buf)
        if ret not in (Gst.FlowReturn.OK, Gst.FlowReturn.FLUSHING):
            print(f"[WARN] push-buffer returned {ret}")

    # -- bus callbacks ---------------------------------------------------------

    def _on_bus_error(self, bus, msg):
        err, dbg = msg.parse_error()
        print(f"[ERROR] {err.message}")
        if dbg:
            print(f"[DEBUG] {dbg}")

    def _on_display_ended(self, bus, msg):
        """Called when the display window is closed or the sink errors out."""
        if msg.type == Gst.MessageType.ERROR:
            err, _ = msg.parse_error()
            print(f"[INFO] Display ended ({err.message}); shutting down.")
        else:
            print("[INFO] Display EOS; shutting down.")
        self._shutdown()

    def _shutdown(self):
        if self._stopping:
            return
        self._stopping = True
        # Stop both pipelines from the main thread to avoid GStreamer deadlocks.
        GLib.idle_add(self._do_shutdown)

    def _do_shutdown(self):
        self.stop()
        self._loop.quit()
        return GLib.SOURCE_REMOVE


# ==============================================================================
#  CLI & ENTRY POINT
# ==============================================================================


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="GStreamer -> OpenCV -> GStreamer pipeline."
    )
    p.add_argument("--device", default=None, help="V4L2 device (default: auto-detect)")
    p.add_argument(
        "--capture-width", type=int, default=DEFAULT_WIDTH, help="Camera capture width"
    )
    p.add_argument(
        "--capture-height",
        type=int,
        default=DEFAULT_HEIGHT,
        help="Camera capture height",
    )
    p.add_argument(
        "--output-width",
        type=int,
        default=DEFAULT_WIDTH,
        help="Output (processed) width",
    )
    p.add_argument(
        "--output-height",
        type=int,
        default=DEFAULT_HEIGHT,
        help="Output (processed) height",
    )
    return p.parse_args()


def main():
    Gst.init(None)
    args = parse_args()
    device = args.device or find_device()
    print(
        f"[INFO] Device: {device}  "
        f"capture={args.capture_width}x{args.capture_height}  "
        f"output={args.output_width}x{args.output_height}"
    )

    loop = GLib.MainLoop()

    pipeline = Pipeline(
        device,
        capture_width=args.capture_width,
        capture_height=args.capture_height,
        output_width=args.output_width,
        output_height=args.output_height,
        loop=loop,
    )
    pipeline.start()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted.")
    finally:
        pipeline.stop()
        loop.quit()


if __name__ == "__main__":
    main()

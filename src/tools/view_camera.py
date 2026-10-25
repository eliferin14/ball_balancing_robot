"""
Standalone OpenCV Video Viewer for Zenoh Camera Streams.

Subscribes to raw camera frames published over Zenoh Shared Memory,
parses the attached FrameMetadata, and renders the live feed with OpenCV.
"""

import argparse
import sys
import time

import cv2
import numpy as np
import zenoh
from loguru import logger

from src.managers.base_manager import DEFAULT_ZENOH_ENDPOINT, create_zenoh_config
from src.messages.camera import FrameMetadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Zenoh Camera Stream Viewer")
    parser.add_argument(
        "--topic",
        default="robot/camera/frame",
        help="Zenoh topic for camera frames (default: robot/camera/frame)",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ZENOH_ENDPOINT,
        help=f"Zenoh router endpoint (default: {DEFAULT_ZENOH_ENDPOINT})",
    )
    parser.add_argument(
        "--window",
        default="Zenoh Live Camera",
        help="Display window title",
    )
    args = parser.parse_args()

    # Sanitize endpoint format (e.g. handle tcp:// or tcp/)
    endpoint = args.endpoint
    if endpoint.startswith("tcp://"):
        endpoint = "tcp/" + endpoint[6:]

    logger.info(f"Connecting to Zenoh router at {endpoint}...")
    try:
        session = zenoh.open(create_zenoh_config("client", endpoint))
    except Exception as err:
        logger.error(f"Failed to connect to Zenoh router at {args.endpoint}: {err}")
        sys.exit(1)

    latest_frame: np.ndarray | None = None
    latest_meta: FrameMetadata | None = None
    fps_counter: int = 0
    fps_val: float = 0.0
    last_fps_time: float = time.perf_counter()

    def _on_frame(sample: zenoh.Sample) -> None:
        nonlocal latest_frame, latest_meta, fps_counter, fps_val, last_fps_time
        try:
            if not sample.attachment:
                return

            meta = FrameMetadata.model_validate_json(bytes(sample.attachment))
            # Zero-copy view of the pixel payload using numpy
            frame = np.frombuffer(bytes(sample.payload), dtype=np.uint8).reshape(
                (meta.height, meta.width, meta.channels)
            )

            latest_frame = frame.copy()
            latest_meta = meta

            fps_counter += 1
            now = time.perf_counter()
            if now - last_fps_time >= 1.0:
                fps_val = fps_counter / (now - last_fps_time)
                fps_counter = 0
                last_fps_time = now

        except Exception as err:
            logger.error(f"Error decoding frame sample: {err}")

    logger.info(f"Subscribing to '{args.topic}'...")
    sub = session.declare_subscriber(args.topic, _on_frame)
    logger.info("Viewer ready. Press 'q' in the window to quit.")

    cv2.namedWindow(args.window, cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            if latest_frame is not None and latest_meta is not None:
                display_img = latest_frame.copy()
                overlay_text = f"ID: {latest_meta.frame_id} | {fps_val:.1f} FPS"
                cv2.putText(
                    display_img,
                    overlay_text,
                    (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                cv2.imshow(args.window, display_img)

            key = cv2.waitKey(10) & 0xFF
            if key == ord("q"):
                logger.info("Quit key pressed by user.")
                break

            # If user clicked the window's close button
            if cv2.getWindowProperty(args.window, cv2.WND_PROP_VISIBLE) < 1:
                break

    finally:
        cv2.destroyAllWindows()
        sub.undeclare()
        session.close()
        logger.info("Zenoh session closed. Exiting.")


if __name__ == "__main__":
    main()

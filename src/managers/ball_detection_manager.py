from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import zenoh
from pydantic import BaseModel, Field

from src.ball_detection.ball_detector_interface import BallDetectorInterface
from src.ball_detection.hsv_ball_detector import HSVBallDetector, HSVDetectorConfig
from src.common.config import load_config
from src.common.paths import DEBUG_VIDEO_DIR, DEFAULT_BALL_DETECTOR_CONFIG_PATH
from src.managers.base_manager import DEFAULT_ZENOH_ENDPOINT, BaseManager
from src.messages.ball import BALL_POSITION_TOPIC, BallPosition
from src.messages.camera import CAMERA_FRAME_TOPIC, FrameMetadata


class BallDetectionManagerConfig(BaseModel):
    """Configuration model for BallDetectionManager."""

    input_frame_topic: str = Field(
        default=CAMERA_FRAME_TOPIC,
        description="Zenoh topic to subscribe to for camera frames",
    )
    output_position_topic: str = Field(
        default=BALL_POSITION_TOPIC,
        description="Zenoh topic to publish detected ball position",
    )
    strategy: str = Field(
        default="hsv",
        description="Detection strategy identifier (e.g. 'hsv')",
    )
    display_debug_window: bool = Field(
        default=False,
        description="Whether to open a real-time OpenCV window rendering detection overlays",
    )
    debug_window_name: str = Field(
        default="Ball Detection Debug",
        description="Window title for OpenCV debug visualization",
    )
    save_debug_video: bool = Field(
        default=False,
        description="Whether to record and save the debug video stream to file in data/debug_video",
    )
    debug_video_filename: str | None = Field(
        default=None,
        description="Optional custom filename for saved video; auto-generates timestamp if None",
    )
    hsv: HSVDetectorConfig = Field(
        default_factory=HSVDetectorConfig,
        description="HSV detector parameters",
    )
    loop_rate_hz: float | None = Field(
        default=None,
        description="Step loop rate in Hz; None to process as frames arrive",
    )
    log_file: Path | None = Field(
        default=None,
        description="Optional log file path",
    )
    zenoh_mode: str = Field(
        default="client",
        description="Zenoh session mode ('client', 'peer')",
    )
    zenoh_endpoint: str | None = Field(
        default=DEFAULT_ZENOH_ENDPOINT,
        description="Zenoh router TCP endpoint",
    )


class BallDetectionManager(BaseManager):
    """
    Manager consuming camera frames over Zenoh and publishing detected ball positions.

    Decouples frame reception from vision/GUI processing using the 'latest frame'
    pattern so stale frames are dropped and queue lag is completely eliminated.
    OpenCV GUI operations are kept strictly in the process's main thread.
    """

    def __init__(
        self,
        config: BallDetectionManagerConfig | Path | str | None = None,
        name: str = "BallDetectionManager",
    ) -> None:
        """
        Initialize BallDetectionManager with configuration or path to config file.

        Args:
            config: BallDetectionManagerConfig instance, path to YAML file, or None for default.
            name: Manager name identifier.
        """
        if config is None:
            resolved_config = load_config(
                DEFAULT_BALL_DETECTOR_CONFIG_PATH, BallDetectionManagerConfig
            )
        elif isinstance(config, (Path, str)):
            resolved_config = load_config(config, BallDetectionManagerConfig)
        elif isinstance(config, BallDetectionManagerConfig):
            resolved_config = config
        else:
            cls_name = type(config).__name__
            raise TypeError(
                f"Expected BallDetectionManagerConfig, Path, str, or None, got {cls_name}"
            )

        super().__init__(
            name=name,
            loop_rate_hz=resolved_config.loop_rate_hz,
            log_file=resolved_config.log_file,
            zenoh_mode=resolved_config.zenoh_mode,
            zenoh_endpoint=resolved_config.zenoh_endpoint,
        )
        self.config: BallDetectionManagerConfig = resolved_config
        self.detector: BallDetectorInterface | None = None

        # Thread synchronization & frame buffer
        self._new_frame_event: threading.Event | None = None
        self._latest_sample: zenoh.Sample | None = None

        # Runtime Zenoh handles
        self._subscriber: zenoh.Subscriber | None = None
        self._publisher: zenoh.Publisher | None = None

        # Video recording
        self._video_writer: cv2.VideoWriter | None = None

    def __getstate__(self) -> dict[str, Any]:
        """Strip runtime synchronization and network handles before pickle spawn."""
        state = super().__getstate__()
        state["_new_frame_event"] = None
        state["_latest_sample"] = None
        state["_subscriber"] = None
        state["_publisher"] = None
        state["detector"] = None
        state["_video_writer"] = None
        return state

    def setup(self) -> None:
        """Initialize detection strategy, frame event, and Zenoh pub/sub."""
        self.logger.info(
            f"Initializing BallDetectionManager with strategy '{self.config.strategy}'..."
        )

        if self.config.strategy == "hsv":
            self.detector = HSVBallDetector(self.config.hsv)
        else:
            raise ValueError(f"Unknown ball detection strategy: {self.config.strategy}")

        self._new_frame_event = threading.Event()
        self._latest_sample = None

        if self._session is not None:
            self.logger.info(
                f"Declaring ball position publisher on '{self.config.output_position_topic}'"
            )
            self._publisher = self._session.declare_publisher(self.config.output_position_topic)

            self.logger.info(f"Subscribing to camera frames on '{self.config.input_frame_topic}'")
            self._subscriber = self._session.declare_subscriber(
                self.config.input_frame_topic, self._on_frame
            )

        if self.config.display_debug_window:
            self.logger.info(f"Debug window display enabled: '{self.config.debug_window_name}'")

    def _on_frame(self, sample: zenoh.Sample) -> None:
        """
        Fast non-blocking callback from Zenoh subscriber thread.

        Saves only the newest incoming sample and signals the main step loop.
        Stale buffered frames are discarded, guaranteeing zero latency.
        """
        self._latest_sample = sample
        if self._new_frame_event is not None:
            self._new_frame_event.set()

    def step(self) -> None:
        """
        Main execution step. Processes the latest available frame and runs GUI.
        """
        if self._new_frame_event is None:
            return

        # Wait briefly for a new frame; allows quick exit if stop was signaled
        if not self._new_frame_event.wait(timeout=0.03):
            return
        self._new_frame_event.clear()

        sample = self._latest_sample
        if (
            sample is None
            or not sample.attachment
            or self.detector is None
            or self._publisher is None
        ):
            return

        try:
            meta = FrameMetadata.model_validate_json(bytes(sample.attachment))
            frame = np.frombuffer(bytes(sample.payload), dtype=np.uint8).reshape(
                (meta.height, meta.width, meta.channels)
            )

            coords = self.detector.detect_ball(frame)

            if coords is not None:
                pos_msg = BallPosition(
                    x=coords[0],
                    y=coords[1],
                    detected=True,
                    frame_id=meta.frame_id,
                )
            else:
                pos_msg = BallPosition(
                    x=0.0,
                    y=0.0,
                    detected=False,
                    frame_id=meta.frame_id,
                )

            self._publisher.put(pos_msg.model_dump_json())

            if self.config.display_debug_window or self.config.save_debug_video:
                debug_frame = self.detector.draw_debug_frame(frame)

                if self.config.save_debug_video:
                    if self._video_writer is None:
                        DEBUG_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
                        if self.config.debug_video_filename:
                            fname = self.config.debug_video_filename
                            if not fname.endswith((".mp4", ".avi")):
                                fname += ".mp4"
                        else:
                            ts = time.strftime("%Y%m%d_%H%M%S")
                            fname = f"ball_debug_{ts}.mp4"

                        video_path = DEBUG_VIDEO_DIR / fname
                        h, w = debug_frame.shape[:2]
                        fps = 30.0
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        self._video_writer = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h))
                        self.logger.info(f"Recording debug video to {video_path}")

                    self._video_writer.write(debug_frame)

                if self.config.display_debug_window:
                    cv2.imshow(self.config.debug_window_name, debug_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q") or key == 27:
                        self.logger.info("Quit key pressed in debug window. Stopping manager...")
                        self.stop()

        except Exception as err:
            self.logger.error(f"Error processing camera frame sample: {err}")

    def stop(self) -> None:
        """Signal manager to stop and wake up any waiting step loops."""
        super().stop()
        if self._new_frame_event is not None:
            self._new_frame_event.set()

    def teardown(self) -> None:
        """Release Zenoh subscriber, publisher, video writer, and OpenCV debug windows."""
        self.logger.info("Tearing down BallDetectionManager...")
        if self._video_writer is not None:
            self.logger.info("Releasing debug video writer...")
            self._video_writer.release()
            self._video_writer = None

        if self._subscriber is not None:
            self._subscriber.undeclare()
            self._subscriber = None

        if self._publisher is not None:
            self._publisher.undeclare()
            self._publisher = None

        if self.config.display_debug_window:
            try:
                cv2.destroyAllWindows()
            except Exception as err:
                self.logger.warning(f"Error destroying OpenCV windows: {err}")

        self.logger.info("BallDetectionManager teardown complete.")

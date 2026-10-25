from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import zenoh
from pydantic import BaseModel, Field

from src.ball_detection.ball_detector_interface import BallDetectorInterface
from src.ball_detection.hsv_ball_detector import HSVBallDetector, HSVDetectorConfig
from src.common.config import load_config
from src.common.paths import DEFAULT_BALL_DETECTOR_CONFIG_PATH
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
    hsv: HSVDetectorConfig = Field(
        default_factory=HSVDetectorConfig,
        description="HSV detector parameters",
    )
    loop_rate_hz: float | None = Field(
        default=None,
        description="Step loop rate in Hz; None for purely event-driven subscriber",
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

        # Runtime Zenoh handles
        self._subscriber: zenoh.Subscriber | None = None
        self._publisher: zenoh.Publisher | None = None

    def setup(self) -> None:
        """Initialize detection strategy and Zenoh subscriber/publisher."""
        self.logger.info(
            f"Initializing BallDetectionManager with strategy '{self.config.strategy}'..."
        )

        if self.config.strategy == "hsv":
            self.detector = HSVBallDetector(self.config.hsv)
        else:
            raise ValueError(f"Unknown ball detection strategy: {self.config.strategy}")

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
        Callback triggered whenever a new camera frame arrives over Zenoh.

        Args:
            sample: Zenoh sample containing raw frame payload and attachment metadata.
        """
        if self.detector is None or self._publisher is None:
            return

        try:
            if not sample.attachment:
                self.logger.warning("Received frame sample without attachment metadata.")
                return

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

            if self.config.display_debug_window:
                debug_frame = self.detector.draw_debug_frame(frame)
                cv2.imshow(self.config.debug_window_name, debug_frame)
                cv2.waitKey(1)

        except Exception as err:
            self.logger.error(f"Error processing camera frame sample: {err}")

    def step(self) -> None:
        """Execution step loop (idle since frame processing is event-driven)."""
        pass

    def teardown(self) -> None:
        """Release Zenoh subscriber, publisher, and OpenCV debug windows."""
        self.logger.info("Tearing down BallDetectionManager...")
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

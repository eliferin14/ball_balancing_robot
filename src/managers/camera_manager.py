import os
import time
from enum import StrEnum
from pathlib import Path
from typing import Any

import zenoh
from pydantic import BaseModel, Field

from src.common.config import load_config
from src.common.paths import SIM_CAMERA_CONFIG_PATH
from src.managers.base_manager import DEFAULT_ZENOH_ENDPOINT, BaseManager
from src.messages.camera import CAMERA_FRAME_TOPIC, FrameMetadata


class CameraSourceType(StrEnum):
    """Supported video input source types."""

    REAL = "real"
    TEST = "test"
    FILE = "file"


class CameraConfig(BaseModel):
    """Configuration model for CameraManager."""

    output_frame_topic: str = Field(
        default=CAMERA_FRAME_TOPIC,
        description="Zenoh topic on which raw camera frames are published",
    )
    source_type: CameraSourceType = Field(
        default=CameraSourceType.TEST,
        description="Video input source type ('real', 'test', 'file')",
    )
    width: int = Field(default=320, description="Output frame width in pixels")
    height: int = Field(default=240, description="Output frame height in pixels")
    framerate: int = Field(default=30, description="Acquisition framerate")
    device: str | None = Field(default=None, description="V4L2 device path if using v4l2src")
    file_path: Path | None = Field(default=None, description="Video file path if using filesrc")
    loop_rate_hz: float | None = Field(
        default=60.0, description="Step loop polling rate (set above framerate to prevent lag)"
    )
    log_file: Path | None = Field(default=None, description="Optional log file path")
    zenoh_mode: str = Field(default="client", description="Zenoh session mode ('client', 'peer')")
    zenoh_endpoint: str | None = Field(
        default=DEFAULT_ZENOH_ENDPOINT, description="Zenoh router TCP endpoint"
    )


class CameraManager(BaseManager):
    """
    Manager capturing video frames via GStreamer and publishing them over Zenoh SHM.

    Publishes raw BGR image buffers as the Zenoh payload (leveraging Zenoh's
    built-in Shared Memory transport optimization for zero-copy IPC) and
    attaches typed Pydantic FrameMetadata to every frame sample.
    """

    def __init__(
        self,
        config: CameraConfig | Path | str | None = None,
        name: str = "CameraManager",
    ) -> None:
        """
        Initialize CameraManager using a CameraConfig instance, path to a YAML file, or None.

        Args:
            config: CameraConfig object, Path or str pointing to a YAML config file, or None.
            name: Manager name identifier.
        """
        if config is None:
            resolved_config = load_config(SIM_CAMERA_CONFIG_PATH, CameraConfig)
        elif isinstance(config, (Path, str)):
            resolved_config = load_config(config, CameraConfig)
        elif isinstance(config, CameraConfig):
            resolved_config = config
        else:
            raise TypeError(
                f"Expected CameraConfig, Path, str, or None, got {type(config).__name__}"
            )

        super().__init__(
            name=name,
            loop_rate_hz=resolved_config.loop_rate_hz,
            log_file=resolved_config.log_file,
            zenoh_mode=resolved_config.zenoh_mode,
            zenoh_endpoint=resolved_config.zenoh_endpoint,
        )
        self.config: CameraConfig = resolved_config
        self.topic: str = resolved_config.output_frame_topic

        # Runtime state (initialized in child process during setup)
        self._pipeline: Any = None
        self._sink: Any = None
        self._frame_publisher: zenoh.Publisher | None = None
        self._frame_id: int = 0

    def __getstate__(self) -> dict[str, Any]:
        """Exclude GStreamer and Zenoh C-pointers when pickling across process spawn."""
        state = super().__getstate__()
        state["_pipeline"] = None
        state["_sink"] = None
        state["_frame_publisher"] = None
        return state

    def _build_pipeline_str(self) -> str:
        """Construct the appropriate GStreamer pipeline string from self.config."""
        caps = f"video/x-raw,format=BGR,width={self.config.width},height={self.config.height}"
        sink_elem = "appsink name=sink emit-signals=true drop=true max-buffers=1 sync=false"

        if self.config.source_type == CameraSourceType.TEST:
            return (
                f"videotestsrc is-live=true ! "
                f"video/x-raw,framerate={self.config.framerate}/1 ! "
                f"videoscale ! {caps} ! "
                f"videoconvert ! {caps} ! "
                f"{sink_elem}"
            )

        if self.config.source_type == CameraSourceType.FILE:
            file_path = self.config.file_path.resolve() if self.config.file_path else None
            if file_path is None or not file_path.exists():
                raise FileNotFoundError(f"Video file does not exist: {file_path}")
            return (
                f'filesrc location="{file_path}" ! '
                f"decodebin ! videoconvert ! videoscale ! {caps} ! "
                f"{sink_elem}"
            )

        if self.config.source_type == CameraSourceType.REAL:
            if self.config.device is not None:
                if not os.path.exists(self.config.device):
                    raise FileNotFoundError(f"V4L2 camera device not found: {self.config.device}")
                return (
                    f"v4l2src device={self.config.device} ! "
                    f"video/x-raw,framerate={self.config.framerate}/1 ! "
                    f"videoconvert ! videoscale ! {caps} ! "
                    f"{sink_elem}"
                )
            # Default Raspberry Pi camera using libcamerasrc
            return (
                f"libcamerasrc ! "
                f"video/x-raw,width={self.config.width},height={self.config.height},"
                f"framerate={self.config.framerate}/1 ! "
                f"videoconvert ! {caps} ! "
                f"{sink_elem}"
            )

        raise ValueError(f"Unsupported CameraSourceType: {self.config.source_type}")

    def setup(self) -> None:
        """Initialize GStreamer pipeline and Zenoh publisher."""
        # Import GStreamer within child process
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        Gst.init(None)
        pipeline_str = self._build_pipeline_str()
        self.logger.info(f"Initializing GStreamer pipeline: {pipeline_str}")

        try:
            self._pipeline = Gst.parse_launch(pipeline_str)
        except Exception as err:
            self.logger.error(f"Failed to create GStreamer pipeline: {err}")
            raise

        self._sink = self._pipeline.get_by_name("sink")
        if self._sink is None:
            raise RuntimeError("Could not find 'sink' element in GStreamer pipeline.")

        # Declare publisher on the frame topic
        if self._session is not None:
            topic = self.config.output_frame_topic
            self._frame_publisher = self._session.declare_publisher(topic)
            self.logger.info(f"Zenoh frame publisher declared on '{topic}'.")

        # Start GStreamer pipeline
        ret = self._pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("GStreamer pipeline failed to enter PLAYING state.")

        self.logger.info("Camera pipeline is PLAYING.")

    def step(self) -> None:
        """Pull the latest frame from appsink and publish it over Zenoh SHM."""
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        sample = self._sink.emit("pull-sample")
        if sample is None:
            # Handle End of Stream (EOS) for file playback: loop back to beginning
            if self.config.source_type == CameraSourceType.FILE and self._pipeline is not None:
                self.logger.debug("Reached EOS in video file, looping back to start...")
                self._pipeline.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                    0,
                )
                time.sleep(0.05)
            return

        buf = sample.get_buffer()
        if buf is None:
            return

        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            self.logger.warning("Failed to map GStreamer buffer.")
            return

        try:
            self._frame_id += 1
            meta = FrameMetadata(
                frame_id=self._frame_id,
                width=self.config.width,
                height=self.config.height,
                channels=3,
                format="BGR",
                source_type=str(self.config.source_type),
            )

            # Publish raw frame buffer as payload with metadata JSON in Zenoh attachment
            if self._frame_publisher is not None:
                meta_bytes = meta.model_dump_json().encode("utf-8")
                self._frame_publisher.put(bytes(mapinfo.data), attachment=meta_bytes)
        finally:
            buf.unmap(mapinfo)

    def teardown(self) -> None:
        """Stop GStreamer pipeline and release resources."""
        self.logger.info("Stopping GStreamer camera pipeline...")
        if self._pipeline is not None:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            self._sink = None

        if self._frame_publisher is not None:
            try:
                self._frame_publisher.undeclare()
            except Exception as err:
                self.logger.warning(f"Error undeclaring frame publisher: {err}")
            finally:
                self._frame_publisher = None

        self.logger.info("Camera pipeline released successfully.")

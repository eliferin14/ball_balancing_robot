import os
import time
from enum import StrEnum
from pathlib import Path
from typing import Any

import zenoh

from src.managers.base_manager import DEFAULT_ZENOH_ENDPOINT, BaseManager
from src.messages.camera import FrameMetadata


class CameraSourceType(StrEnum):
    """Supported video input source types."""
    REAL = "real"
    TEST = "test"
    FILE = "file"


class CameraManager(BaseManager):
    """
    Manager capturing video frames via GStreamer and publishing them over Zenoh SHM.

    Publishes raw BGR image buffers as the Zenoh payload (leveraging Zenoh's
    built-in Shared Memory transport optimization for zero-copy IPC) and
    attaches typed Pydantic FrameMetadata to every frame sample.
    """

    def __init__(
        self,
        name: str = "CameraManager",
        source_type: CameraSourceType | str = CameraSourceType.TEST,
        width: int = 320,
        height: int = 240,
        framerate: int = 30,
        device: str | None = None,
        file_path: str | Path | None = None,
        topic: str = "robot/camera/frame",
        loop_rate_hz: float | None = 60.0,
        log_file: Path | None = None,
        zenoh_mode: str = "client",
        zenoh_endpoint: str | None = DEFAULT_ZENOH_ENDPOINT,
    ) -> None:
        """
        Initialize CameraManager.

        Args:
            name: Manager name identifier.
            source_type: 'real', 'test', or 'file'.
            width: Output frame width in pixels.
            height: Output frame height in pixels.
            framerate: Camera acquisition framerate.
            device: V4L2 device path (e.g. '/dev/video0') or None for auto/libcamerasrc.
            file_path: Video file path if source_type is 'file'.
            topic: Zenoh topic on which to publish frames.
            loop_rate_hz: Rate of step polling loop (set above framerate to prevent lag).
            log_file: Optional log file path.
            zenoh_mode: Zenoh mode ('client', 'peer', 'router').
            zenoh_endpoint: Zenoh router TCP endpoint.
        """
        super().__init__(
            name=name,
            loop_rate_hz=loop_rate_hz,
            log_file=log_file,
            zenoh_mode=zenoh_mode,
            zenoh_endpoint=zenoh_endpoint,
        )
        self.source_type: CameraSourceType = CameraSourceType(source_type)
        self.width: int = width
        self.height: int = height
        self.framerate: int = framerate
        self.device: str | None = device
        self.file_path: Path | None = Path(file_path).resolve() if file_path is not None else None
        self.topic: str = topic

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
        """Construct the appropriate GStreamer pipeline string."""
        caps = f"video/x-raw,format=BGR,width={self.width},height={self.height}"
        sink_elem = "appsink name=sink emit-signals=true drop=true max-buffers=1 sync=false"

        if self.source_type == CameraSourceType.TEST:
            return (
                f"videotestsrc is-live=true ! "
                f"video/x-raw,framerate={self.framerate}/1 ! "
                f"videoscale ! {caps} ! "
                f"videoconvert ! {caps} ! "
                f"{sink_elem}"
            )

        if self.source_type == CameraSourceType.FILE:
            if self.file_path is None or not self.file_path.exists():
                raise FileNotFoundError(f"Video file does not exist: {self.file_path}")
            return (
                f"filesrc location=\"{self.file_path}\" ! "
                f"decodebin ! videoconvert ! videoscale ! {caps} ! "
                f"{sink_elem}"
            )

        if self.source_type == CameraSourceType.REAL:
            if self.device is not None:
                if not os.path.exists(self.device):
                    raise FileNotFoundError(f"V4L2 camera device not found: {self.device}")
                return (
                    f"v4l2src device={self.device} ! "
                    f"video/x-raw,framerate={self.framerate}/1 ! "
                    f"videoconvert ! videoscale ! {caps} ! "
                    f"{sink_elem}"
                )
            # Default Raspberry Pi camera using libcamerasrc
            return (
                f"libcamerasrc ! "
                f"video/x-raw,width={self.width},height={self.height},"
                f"framerate={self.framerate}/1 ! "
                f"videoconvert ! {caps} ! "
                f"{sink_elem}"
            )

        raise ValueError(f"Unsupported CameraSourceType: {self.source_type}")

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
            self._frame_publisher = self._session.declare_publisher(self.topic)
            self.logger.info(f"Zenoh frame publisher declared on '{self.topic}'.")

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
            if self.source_type == CameraSourceType.FILE and self._pipeline is not None:
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
                width=self.width,
                height=self.height,
                channels=3,
                format="BGR",
                source_type=str(self.source_type),
            )

            # Publish raw frame buffer as payload with metadata JSON in Zenoh attachment
            if self._frame_publisher is not None:
                meta_bytes = meta.model_dump_json().encode("utf-8")
                self._frame_publisher.put(mapinfo.data, attachment=meta_bytes)
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

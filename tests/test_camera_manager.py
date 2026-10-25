import time
from typing import List

import numpy as np
import pytest
import zenoh

from src.managers.base_manager import create_zenoh_config
from src.managers.camera_manager import CameraManager, CameraSourceType
from src.messages.camera import FrameMetadata


def test_camera_manager_videotestsrc_frame_capture() -> None:
    """Test that CameraManager captures frames using videotestsrc and increments frame_id."""
    cam = CameraManager(
        name="TestCam",
        source_type=CameraSourceType.TEST,
        width=320,
        height=240,
        framerate=30,
    )
    cam.setup()
    try:
        assert cam._frame_id == 0

        # Step twice to capture frames
        cam.step()
        assert cam._frame_id == 1

        cam.step()
        assert cam._frame_id == 2
    finally:
        cam.teardown()


def test_camera_manager_zenoh_shm_frame_publication(free_zenoh_endpoint: str) -> None:
    """Test that CameraManager publishes raw zero-copy frame payload with Pydantic attachment."""
    test_endpoint = free_zenoh_endpoint
    router_session = zenoh.open(create_zenoh_config("router", test_endpoint))

    received_frames: List[tuple[np.ndarray, FrameMetadata]] = []

    cam = CameraManager(
        name="PubCam",
        source_type=CameraSourceType.TEST,
        width=320,
        height=240,
        framerate=30,
        zenoh_endpoint=test_endpoint,
    )

    receiver_session = zenoh.open(create_zenoh_config("client", test_endpoint))

    def _on_frame(sample: zenoh.Sample) -> None:
        if sample.attachment:
            meta = FrameMetadata.model_validate_json(bytes(sample.attachment))
            frame_arr = np.frombuffer(bytes(sample.payload), dtype=np.uint8).reshape(
                (meta.height, meta.width, meta.channels)
            )
            received_frames.append((frame_arr, meta))

    sub = receiver_session.declare_subscriber(cam.topic, _on_frame)
    time.sleep(0.3)

    cam._open_zenoh_session()
    cam.setup()

    try:
        # Step once to produce and publish a frame
        cam.step()

        timeout = 2.0
        start = time.time()
        while len(received_frames) == 0 and (time.time() - start) < timeout:
            time.sleep(0.05)

        assert len(received_frames) >= 1
        frame, meta = received_frames[0]

        # Verify Pydantic metadata
        assert meta.width == 320
        assert meta.height == 240
        assert meta.channels == 3
        assert meta.format == "BGR"
        assert meta.source_type == "test"
        assert meta.frame_id >= 1

        # Verify zero-copy reconstructed image array
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (240, 320, 3)
        assert frame.dtype == np.uint8
    finally:
        cam.teardown()
        cam._close_zenoh_session()
        sub.undeclare()
        receiver_session.close()
        router_session.close()


def test_camera_manager_invalid_source_fails() -> None:
    """Test that CameraManager raises FileNotFoundError for non-existent video files."""
    cam = CameraManager(
        name="FailCam",
        source_type=CameraSourceType.FILE,
        file_path="/non_existent/path/video.mp4",
    )
    with pytest.raises(FileNotFoundError):
        cam.setup()

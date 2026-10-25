import time
from typing import List

import cv2
import numpy as np
import zenoh

from src.ball_detection.hsv_ball_detector import HSVBallDetector, HSVDetectorConfig
from src.common.config import load_config
from src.common.paths import DEFAULT_BALL_DETECTOR_CONFIG_PATH
from src.managers.ball_detection_manager import (
    BallDetectionManager,
    BallDetectionManagerConfig,
)
from src.managers.base_manager import create_zenoh_config
from src.messages.ball import BALL_POSITION_TOPIC, BallPosition
from src.messages.camera import FrameMetadata


def test_hsv_ball_detector_synthetic_frame() -> None:
    """Test that HSVBallDetector locates a synthetic colored circle accurately."""
    config = HSVDetectorConfig(
        hue_min=35.0,
        hue_max=85.0,
        sat_min=100.0,
        sat_max=255.0,
        val_min=100.0,
        val_max=255.0,
    )
    detector = HSVBallDetector(config=config)

    # Synthetic 240x320 BGR image
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # Target color: Hue 60 (pure green in OpenCV), Sat 200, Val 200
    hsv_color = np.uint8([[[60, 200, 200]]])
    bgr_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)[0, 0]
    center_x, center_y = 160, 120
    radius = 15

    cv2.circle(
        frame,
        (center_x, center_y),
        radius,
        (int(bgr_color[0]), int(bgr_color[1]), int(bgr_color[2])),
        -1,
    )

    # Add a colorful background rectangle (pure blue) that is not the ball
    cv2.rectangle(frame, (10, 10), (30, 30), (255, 0, 0), -1)

    detected = detector.detect_ball(frame)
    assert detected is not None
    det_x, det_y = detected
    assert abs(det_x - center_x) < 1.5
    assert abs(det_y - center_y) < 1.5

    # Verify debug frame drawing
    debug_frame = detector.draw_debug_frame(frame)
    assert debug_frame.shape == (240, 320, 3)

    # Background rectangle (15, 15) must now be converted to black & white (B == G == R)
    bg_pixel = debug_frame[15, 15]
    assert bg_pixel[0] == bg_pixel[1] == bg_pixel[2]

    # Masked ball center (160, 120) retains its distinct color indicator
    ball_pixel = debug_frame[center_y, center_x]
    assert not (ball_pixel[0] == ball_pixel[1] == ball_pixel[2])


def test_hsv_ball_detector_no_ball() -> None:
    """Test that HSVBallDetector returns None when no colored ball is present."""
    detector = HSVBallDetector()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    assert detector.detect_ball(frame) is None


def test_hsv_ball_detector_connected_components_largest_only() -> None:
    """Test that only the largest connected component is kept in mask and tracked."""
    config = HSVDetectorConfig(
        hue_min=35.0,
        hue_max=85.0,
        min_area=50.0,
        closure_kernel_size=1,  # Keep kernel 1 to prevent fusing
    )
    detector = HSVBallDetector(config=config)

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    hsv_green = np.uint8([[[60, 200, 200]]])
    bgr_green = cv2.cvtColor(hsv_green, cv2.COLOR_HSV2BGR)[0, 0]
    color = (int(bgr_green[0]), int(bgr_green[1]), int(bgr_green[2]))

    # Small component at (50, 50) of radius 4 (area ~ 50)
    cv2.circle(frame, (50, 50), 4, color, -1)

    # Large component at (200, 150) of radius 16 (area ~ 800)
    cv2.circle(frame, (200, 150), 16, color, -1)

    coords = detector.detect_ball(frame)
    assert coords is not None
    # Must match the larger component, ignoring the smaller one
    assert abs(coords[0] - 200) < 1.5
    assert abs(coords[1] - 150) < 1.5

    # Mask must strictly contain the large component, NOT the small one
    assert detector._last_mask is not None
    assert detector._last_mask[150, 200] == 255
    assert detector._last_mask[50, 50] == 0


def test_hsv_ball_detector_min_area_threshold() -> None:
    """Test that components below the configured min_area threshold return None."""
    config = HSVDetectorConfig(
        hue_min=35.0,
        hue_max=85.0,
        min_area=100.0,
        closure_kernel_size=1,
    )
    detector = HSVBallDetector(config=config)

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    hsv_green = np.uint8([[[60, 200, 200]]])
    bgr_green = cv2.cvtColor(hsv_green, cv2.COLOR_HSV2BGR)[0, 0]
    color = (int(bgr_green[0]), int(bgr_green[1]), int(bgr_green[2]))

    # Circle with radius 4 has area ~ 50 pixels (< min_area 100)
    cv2.circle(frame, (100, 100), 4, color, -1)

    assert detector.detect_ball(frame) is None
    assert detector._last_mask is not None
    assert np.all(detector._last_mask == 0)


def test_hsv_ball_detector_circularity_filter() -> None:
    """Test that non-circular elongated shapes are rejected by min_circularity."""
    config = HSVDetectorConfig(
        hue_min=35.0,
        hue_max=85.0,
        min_area=50.0,
        min_circularity=0.5,
        closure_kernel_size=1,
    )
    detector = HSVBallDetector(config=config)

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    hsv_green = np.uint8([[[60, 200, 200]]])
    bgr_green = cv2.cvtColor(hsv_green, cv2.COLOR_HSV2BGR)[0, 0]
    color = (int(bgr_green[0]), int(bgr_green[1]), int(bgr_green[2]))

    # Elongated strip 5x80 pixels (area = 400 > min_area 50, but circularity < 0.25)
    cv2.rectangle(frame, (10, 10), (15, 90), color, -1)
    assert detector.detect_ball(frame) is None

    # Replace with a circle (area ~ 700, circularity ~ 0.86)
    frame.fill(0)
    cv2.circle(frame, (160, 120), 15, color, -1)
    coords = detector.detect_ball(frame)
    assert coords is not None
    assert abs(coords[0] - 160) < 1.5


def test_hsv_ball_detector_convex_hull_seals_notch() -> None:
    """Test that use_convex_hull=True bridges reflections/notches on circle perimeter."""
    config = HSVDetectorConfig(
        hue_min=35.0,
        hue_max=85.0,
        min_area=50.0,
        min_circularity=0.6,
        use_convex_hull=True,
        closure_kernel_size=3,
    )
    detector = HSVBallDetector(config=config)

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    hsv_green = np.uint8([[[60, 200, 200]]])
    bgr_green = cv2.cvtColor(hsv_green, cv2.COLOR_HSV2BGR)[0, 0]
    color = (int(bgr_green[0]), int(bgr_green[1]), int(bgr_green[2]))

    # Circle radius 20 at (160, 120)
    cv2.circle(frame, (160, 120), 20, color, -1)
    # Cut a reflection notch at the top: (156..164, 100..106)
    cv2.rectangle(frame, (156, 100), (164, 106), (0, 0, 0), -1)

    coords = detector.detect_ball(frame)
    assert coords is not None
    # Convex hull must fill the notch in the final mask
    assert detector._last_mask is not None
    assert detector._last_mask[103, 160] == 255


def test_ball_detection_manager_config_loading() -> None:
    """Test that default ball detector YAML config loads cleanly into Pydantic model."""
    config = load_config(DEFAULT_BALL_DETECTOR_CONFIG_PATH, BallDetectionManagerConfig)
    assert config.strategy == "hsv"
    assert config.input_frame_topic == "robot/camera/frame"
    assert config.output_position_topic == BALL_POSITION_TOPIC
    assert config.hsv.closure_kernel_size >= 1
    assert config.hsv.min_area >= 1.0
    assert config.hsv.min_circularity >= 0.0
    assert isinstance(config.hsv.use_convex_hull, bool)


def test_ball_detection_manager_zenoh_pipeline(free_zenoh_endpoint: str) -> None:
    """Test that BallDetectionManager processes incoming frames and publishes BallPosition."""
    test_endpoint = free_zenoh_endpoint
    router_session = zenoh.open(create_zenoh_config("router", test_endpoint))

    received_positions: List[BallPosition] = []

    pos_sub_session = zenoh.open(create_zenoh_config("client", test_endpoint))

    def _on_pos(sample: zenoh.Sample) -> None:
        pos = BallPosition.model_validate_json(bytes(sample.payload).decode("utf-8"))
        received_positions.append(pos)

    sub = pos_sub_session.declare_subscriber(BALL_POSITION_TOPIC, _on_pos)

    # Frame publisher session
    frame_pub_session = zenoh.open(create_zenoh_config("client", test_endpoint))
    frame_pub = frame_pub_session.declare_publisher("robot/camera/frame")

    # Manager under test
    mgr_config = BallDetectionManagerConfig(
        input_frame_topic="robot/camera/frame",
        output_position_topic=BALL_POSITION_TOPIC,
        strategy="hsv",
        display_debug_window=False,
        zenoh_endpoint=test_endpoint,
    )
    manager = BallDetectionManager(config=mgr_config, name="TestDetectorMgr")
    manager._session = zenoh.open(create_zenoh_config("client", test_endpoint))
    manager.setup()

    try:
        # Build synthetic frame with green ball at (100, 80)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        hsv_color = np.uint8([[[60, 200, 200]]])
        bgr_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)[0, 0]
        cv2.circle(
            frame,
            (100, 80),
            12,
            (int(bgr_color[0]), int(bgr_color[1]), int(bgr_color[2])),
            -1,
        )

        meta = FrameMetadata(
            frame_id=42,
            width=320,
            height=240,
            channels=3,
            format="BGR",
            source_type="test",
        )

        frame_pub.put(bytes(frame.tobytes()), attachment=meta.model_dump_json().encode("utf-8"))

        deadline = time.time() + 3.0
        while len(received_positions) == 0 and time.time() < deadline:
            manager.step()
            time.sleep(0.02)

        assert len(received_positions) > 0
        last_pos = received_positions[-1]
        assert last_pos.detected is True
        assert last_pos.frame_id == 42
        assert abs(last_pos.x - 100.0) < 2.0
        assert abs(last_pos.y - 80.0) < 2.0

    finally:
        manager.teardown()
        sub.undeclare()
        frame_pub.undeclare()
        pos_sub_session.close()
        frame_pub_session.close()
        router_session.close()

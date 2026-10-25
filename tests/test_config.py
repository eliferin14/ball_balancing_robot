import pytest

from src.common.config import load_config
from src.common.paths import SIM_CAMERA_CONFIG_PATH
from src.managers.camera_manager import CameraConfig, CameraManager, CameraSourceType


def test_load_config_valid_yaml() -> None:
    """Test loading a valid YAML configuration into CameraConfig."""
    config = load_config(SIM_CAMERA_CONFIG_PATH, CameraConfig)

    assert isinstance(config, CameraConfig)
    assert config.output_frame_topic == "robot/camera/frame"
    assert config.source_type == CameraSourceType.TEST
    assert config.width == 320
    assert config.height == 240
    assert config.framerate == 30
    assert config.loop_rate_hz == 60.0


def test_load_config_missing_file_raises() -> None:
    """Test that load_config raises FileNotFoundError for missing paths."""
    with pytest.raises(FileNotFoundError):
        load_config("/non_existent/path/config.yaml", CameraConfig)


def test_camera_manager_initialization_with_config() -> None:
    """Test that CameraManager accepts a CameraConfig instance, Path, or None."""
    # 1. From Path
    cam_from_path = CameraManager(config=SIM_CAMERA_CONFIG_PATH)
    assert cam_from_path.config.source_type == CameraSourceType.TEST
    assert cam_from_path.topic == "robot/camera/frame"

    # 2. From CameraConfig instance
    custom_cfg = CameraConfig(
        output_frame_topic="custom/frame/topic",
        source_type=CameraSourceType.TEST,
        width=640,
        height=480,
    )
    cam_from_model = CameraManager(config=custom_cfg)
    assert cam_from_model.config.width == 640
    assert cam_from_model.topic == "custom/frame/topic"

    # 3. Default (None)
    cam_default = CameraManager()
    assert cam_default.config.source_type == CameraSourceType.TEST

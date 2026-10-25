# We assume this file is in {PROJECT_ROOT}/src/commons/paths.py

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# --- Configs dir ---
CONFIG_DIR = SRC_DIR / "config"
CAMERA_CONFIG_DIR = CONFIG_DIR / "camera"
SIM_CAMERA_CONFIG_PATH = CAMERA_CONFIG_DIR / "sim.yaml"
REAL_CAMERA_CONFIG_PATH = CAMERA_CONFIG_DIR / "real.yaml"


if __name__ == "__main__":
    print(PROJECT_ROOT)

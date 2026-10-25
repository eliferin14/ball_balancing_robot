# We assume this file is in {PROJECT_ROOT}/src/commons/paths.py

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# --- Configs dir ---
CONFIG_DIR = SRC_DIR / "config"


if __name__ == "__main__":
    print(PROJECT_ROOT)

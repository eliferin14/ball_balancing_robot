# Gemini CLI Project Mandates

This file provides foundational instructions for Gemini CLI when working on the Ball Balancing Robot project.

## Environment & Execution
- **Virtual Environment:** Always use the `sim_venv` virtual environment for simulation-related tasks. Prepend `source sim_venv/bin/activate &&` to shell commands when installing packages or running scripts.
- **Working Directory:** Execute all Python scripts and tests from the `src/` directory to maintain consistent package import behavior.
- **Python Version:** This project targets Python 3.13+.

## Project Structure
- All source code must reside in the `src/` directory.
- Maintain the Python package structure using `__init__.py` files in all subdirectories (`gui`, `pi`, `kinematics`, etc.).
- Use absolute imports relative to `src/` for cross-package communication (e.g., `from gui.kinematics.robot3RRS import ...`).

## Libraries & Technical Standards
- **Math/Physics:** Use `spatialmath-python` (sm) for 3D rotations, transformations, and robot geometry.
- **Control Theory:** Use the `control` library for PID design and frequency domain analysis.
- **Visualization:** Use `tkinter` with `ttkthemes` for the GUI.
- **Decoupling:** Keep hardware-specific code (in `src/pi/`) strictly decoupled from the simulation/GUI logic.

## Workflow Mandates
- **Validation:** Always verify kinematics changes in the `gui/` simulation before suggesting deployment to the Raspberry Pi.
- **Testing:** After making any code changes, YOU MUST run the central test suite to ensure mathematical and functional integrity:
  ```bash
  source sim_venv/bin/activate && python3 src/tests/test_main.py
  ```
- **Documentation:** Keep `README.md` and requirements files updated as new dependencies or modules are added.

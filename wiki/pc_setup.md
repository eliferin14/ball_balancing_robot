# PC Setup & Usage

Instructions to set up and run the simulation environment and tests on a development PC.

## 1. Virtual Environment Setup

1. Create and activate a Python virtual environment (Python >= 3.11):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies for simulation and development:
   ```bash
   pip install --upgrade pip
   pip install -e ".[sim,dev]"
   ```

## 2. Running the System

Launch the multi-process orchestrator from the project root:

```bash
# Demo mode (default: producer/consumer test over Zenoh)
python -m src.main --mode demo

# Simulation mode
python -m src.main --mode sim

# Or via the CLI entrypoint
ball-sim
```

To stop the system, press **`Ctrl+C`**. The orchestrator will gracefully stop all managers.

## 3. Running Tests

Run the test suite:
```bash
pytest tests/ -v
```

Run code formatting and linting:
```bash
ruff check src/ tests/
```


import argparse
import multiprocessing as mp
import multiprocessing.synchronize
import os
import signal
import sys
import time
from types import FrameType

import zenoh
from loguru import logger

from src.common.paths import (
    DEFAULT_BALL_DETECTOR_CONFIG_PATH,
    REAL_CAMERA_CONFIG_PATH,
    SIM_CAMERA_CONFIG_PATH,
)
from src.managers.ball_detection_manager import BallDetectionManager
from src.managers.base_manager import (
    DEFAULT_ZENOH_ENDPOINT,
    BaseManager,
    create_zenoh_config,
)
from src.managers.camera_manager import CameraManager
from src.managers.dummy_managers import DummyConsumerManager, DummyProducerManager
from src.messages.system import ControlCommand


class ManagerOrchestrator:
    """
    Coordinates and monitors child Manager processes.

    Uses multiprocessing with the 'spawn' context to ensure complete process
    isolation and compatibility with C/Rust extensions (Zenoh, OpenCV).
    Also hosts a local Zenoh router session to seamlessly interconnect all processes.
    """

    def __init__(
        self,
        managers: list[BaseManager],
        zenoh_endpoint: str = DEFAULT_ZENOH_ENDPOINT,
        start_router: bool = True,
    ) -> None:
        """
        Initialize orchestrator with a list of managers.

        Args:
            managers: List of BaseManager instances to execute.
            zenoh_endpoint: TCP endpoint for the local Zenoh router or remote router.
            start_router: Whether to host a local Zenoh router session.
        """
        self.managers: list[BaseManager] = managers
        self.zenoh_endpoint: str = zenoh_endpoint
        self.start_router: bool = start_router
        self._ctx = mp.get_context("spawn")
        self._stop_event: multiprocessing.synchronize.Event = self._ctx.Event()
        self._processes: list[mp.Process] = []
        self._router_session: zenoh.Session | None = None
        self._is_shutting_down: bool = False

    def _setup_signal_handlers(self) -> None:
        """Install signal traps in the main orchestrator process."""

        def _signal_handler(signum: int, _frame: FrameType | None) -> None:
            sig_name = signal.Signals(signum).name
            logger.warning(f"Main process received {sig_name}. Initiating graceful shutdown...")
            self.stop()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    def start(self) -> None:
        """Start Zenoh routing and spawn all manager processes."""
        self._setup_signal_handlers()

        # Start the local Zenoh router so all child client managers can interconnect
        if self.start_router:
            try:
                router_cfg = create_zenoh_config(mode="router", endpoint=self.zenoh_endpoint)
                self._router_session = zenoh.open(router_cfg)
                listen_ep = self.zenoh_endpoint.replace("127.0.0.1", "0.0.0.0")
                logger.info(f"Zenoh router active on {listen_ep}")
            except Exception as err:
                logger.info(
                    f"Zenoh router on {self.zenoh_endpoint} not started ({err}). "
                    "Assuming external router or peer communication is active."
                )
                self._router_session = None
        else:
            logger.info(
                f"Connecting managers as clients to external Zenoh router at {self.zenoh_endpoint}"
            )
            self._router_session = None

        logger.info(f"Orchestrator starting {len(self.managers)} manager process(es)...")

        for mgr in self.managers:
            proc = self._ctx.Process(
                target=mgr.run,
                args=(self._stop_event,),
                name=mgr.name,
                daemon=False,
            )
            proc.start()
            self._processes.append(proc)
            logger.info(f"Spawned '{mgr.name}' with PID {proc.pid}")

    def run(self) -> None:
        """Monitor processes until shutdown is triggered or all exit."""
        self.start()
        try:
            while not self._stop_event.is_set():
                # Check if any child process crashed or exited unexpectedly
                for proc in self._processes:
                    if not proc.is_alive():
                        if not self._stop_event.is_set():
                            logger.error(
                                f"Manager '{proc.name}' (PID {proc.pid}) exited unexpectedly "
                                f"with code {proc.exitcode}."
                            )
                            self.stop()
                            break
                time.sleep(0.2)
        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt caught in main monitor loop.")
            self.stop()
        finally:
            self.wait_for_shutdown()

    def stop(self) -> None:
        """Signal all managers to stop via Zenoh ControlCommand and the shared Event."""
        if not self._is_shutting_down:
            self._is_shutting_down = True
            logger.info("Broadcasting stop command to all managers...")

            # 1. Trigger shared multiprocessing event for local process loops immediately
            self._stop_event.set()

            # 2. Broadcast stop command over Zenoh
            if self._router_session is not None:
                try:
                    cmd = ControlCommand(action="STOP", target="all", sender="orchestrator")
                    payload = cmd.model_dump_json().encode("utf-8")
                    self._router_session.put("robot/system/control", payload)
                except Exception as err:
                    logger.debug(f"Failed to publish stop command over Zenoh: {err}")

    def wait_for_shutdown(self, timeout_sec: float = 2.0) -> None:
        """Wait for child processes to finish cleanly, terminating any hanging process."""
        self.stop()
        logger.info(f"Waiting up to {timeout_sec}s for child processes to exit...")

        for proc in self._processes:
            if proc.is_alive():
                proc.join(timeout=timeout_sec)
                if proc.is_alive():
                    logger.warning(
                        f"Manager '{proc.name}' (PID {proc.pid}) timed out. Terminating..."
                    )
                    proc.terminate()
                    proc.join(timeout=1.0)
                    if proc.is_alive():
                        logger.warning(
                            f"Manager '{proc.name}' (PID {proc.pid}) still alive. Killing..."
                        )
                        proc.kill()
                        proc.join(timeout=0.5)

        if self._router_session is not None:
            try:
                self._router_session.close()
                logger.debug("Zenoh router session closed.")
            except Exception as err:
                logger.debug(f"Error closing router session: {err}")
            finally:
                self._router_session = None

        logger.info("All manager processes stopped cleanly.")


def build_managers_for_mode(mode: str) -> list[BaseManager]:
    """
    Factory function to instantiate the managers required for a given execution mode.

    Args:
        mode: Execution mode ('demo', 'sim', 'pi', 'pi-hw', 'pc-proc').

    Returns:
        List of configured BaseManager instances.
    """
    if mode == "demo":
        return [
            DummyProducerManager(name="Producer-1", loop_rate_hz=2.0),
            DummyConsumerManager(name="Consumer-1", loop_rate_hz=2.0),
        ]
    elif mode == "sim":
        logger.info("Initializing simulation managers (Camera, BallDetector, SimController)...")
        return [
            CameraManager(config=SIM_CAMERA_CONFIG_PATH),
            BallDetectionManager(config=DEFAULT_BALL_DETECTOR_CONFIG_PATH),
            DummyConsumerManager(name="SimController", loop_rate_hz=10.0),
        ]
    elif mode == "pi":
        logger.info(
            "Initializing full standalone Raspberry Pi managers (Camera, BallDetector, Actuator)..."
        )
        return [
            CameraManager(config=REAL_CAMERA_CONFIG_PATH),
            BallDetectionManager(config=DEFAULT_BALL_DETECTOR_CONFIG_PATH),
            DummyConsumerManager(name="PiMotorActuator", loop_rate_hz=50.0),
        ]
    elif mode == "pi-hw":
        logger.info("Initializing Raspberry Pi hardware interface only (Camera, Actuator)...")
        return [
            CameraManager(config=REAL_CAMERA_CONFIG_PATH),
            DummyConsumerManager(name="PiMotorActuator", loop_rate_hz=50.0),
        ]
    elif mode == "pc-proc":
        logger.info("Initializing PC processing managers (BallDetector, Controller)...")
        return [
            BallDetectionManager(config=DEFAULT_BALL_DETECTOR_CONFIG_PATH),
            DummyConsumerManager(name="PCController", loop_rate_hz=20.0),
        ]
    else:
        raise ValueError(f"Unknown mode: {mode}")


def main() -> None:
    """CLI entry point for launching the manager orchestrator."""
    parser = argparse.ArgumentParser(description="Ball Balancing Robot - Process Orchestrator")
    parser.add_argument(
        "--mode",
        choices=["demo", "sim", "pi", "pi-hw", "pc-proc"],
        default="demo",
        help="System runtime mode (default: demo)",
    )
    parser.add_argument(
        "--zenoh-endpoint",
        default=DEFAULT_ZENOH_ENDPOINT,
        help=f"Zenoh endpoint (default: {DEFAULT_ZENOH_ENDPOINT})",
    )
    parser.add_argument(
        "--debug-window",
        action="store_true",
        help="Enable OpenCV debug window in BallDetectionManager",
    )
    args = parser.parse_args()

    # Configure root loguru formatting
    logger.remove()
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<magenta>[MAIN]</magenta> (PID {process}) - "
            "<level>{message}</level>"
        ),
        level="INFO",
    )

    # Sanitize endpoint format (e.g. handle tcp:// or tcp/)
    endpoint = args.zenoh_endpoint
    if endpoint.startswith("tcp://"):
        endpoint = "tcp/" + endpoint[6:]

    logger.info(f"Ball Balancing Robot launching in '{args.mode}' mode (PID {os.getpid()})...")
    managers = build_managers_for_mode(mode=args.mode)
    for mgr in managers:
        mgr.zenoh_endpoint = endpoint
        if args.debug_window and isinstance(mgr, BallDetectionManager):
            mgr.config.display_debug_window = True

    is_local = "127.0.0.1" in endpoint or "localhost" in endpoint
    start_router = (args.mode != "pc-proc") and is_local

    orchestrator = ManagerOrchestrator(
        managers=managers,
        zenoh_endpoint=endpoint,
        start_router=start_router,
    )

    try:
        orchestrator.run()
    except Exception as err:
        logger.exception(f"Fatal error in orchestrator: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

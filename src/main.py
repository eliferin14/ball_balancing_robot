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

from src.managers.base_manager import (
    DEFAULT_ZENOH_ENDPOINT,
    BaseManager,
    create_zenoh_config,
)
from src.managers.camera_manager import CameraManager, CameraSourceType
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
    ) -> None:
        """
        Initialize orchestrator with a list of managers.

        Args:
            managers: List of BaseManager instances to execute.
            zenoh_endpoint: TCP endpoint for the local Zenoh router.
        """
        self.managers: list[BaseManager] = managers
        self.zenoh_endpoint: str = zenoh_endpoint
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
        try:
            router_cfg = create_zenoh_config(mode="router", endpoint=self.zenoh_endpoint)
            self._router_session = zenoh.open(router_cfg)
            logger.info(f"Zenoh router active on {self.zenoh_endpoint}")
        except Exception as err:
            logger.info(
                f"Zenoh router on {self.zenoh_endpoint} not started ({err}). "
                "Assuming external router or peer communication is active."
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

            # 1. Broadcast stop command over Zenoh
            if self._router_session is not None:
                try:
                    cmd = ControlCommand(action="STOP", target="all", sender="orchestrator")
                    payload = cmd.model_dump_json().encode("utf-8")
                    self._router_session.put("robot/system/control", payload)
                except Exception as err:
                    logger.debug(f"Failed to publish stop command over Zenoh: {err}")

            # 2. Trigger shared multiprocessing event for local process loops
            self._stop_event.set()

    def wait_for_shutdown(self, timeout_sec: float = 4.0) -> None:
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

        if self._router_session is not None:
            try:
                self._router_session.close()
                logger.debug("Zenoh router session closed.")
            except Exception as err:
                logger.debug(f"Error closing router session: {err}")
            finally:
                self._router_session = None

        logger.info("All manager processes stopped cleanly.")


def build_managers_for_mode(
    mode: str,
    camera_source: str = "test",
    video_file: str | None = None,
) -> list[BaseManager]:
    """
    Factory function to instantiate the managers required for a given execution mode.

    Args:
        mode: Execution mode ('demo', 'sim', 'pi').
        camera_source: Source type for CameraManager ('test', 'real', 'file').
        video_file: Path to video file if camera_source is 'file'.

    Returns:
        List of configured BaseManager instances.
    """
    if mode == "demo":
        return [
            DummyProducerManager(name="Producer-1", loop_rate_hz=2.0),
            DummyConsumerManager(name="Consumer-1", loop_rate_hz=2.0),
        ]
    elif mode == "sim":
        logger.info("Initializing simulation managers with CameraManager...")
        resolved_src = CameraSourceType.FILE if video_file else CameraSourceType(camera_source)
        return [
            CameraManager(
                name="CameraManager",
                source_type=resolved_src,
                file_path=video_file,
                width=320,
                height=240,
                framerate=30,
            ),
            DummyConsumerManager(name="SimController", loop_rate_hz=10.0),
        ]
    elif mode == "pi":
        logger.info("Initializing Raspberry Pi hardware managers...")
        return [
            CameraManager(
                name="CameraManager",
                source_type=CameraSourceType.REAL,
                width=320,
                height=240,
                framerate=30,
            ),
            DummyConsumerManager(name="PiMotorActuator", loop_rate_hz=50.0),
        ]
    else:
        raise ValueError(f"Unknown mode: {mode}")


def main() -> None:
    """CLI entry point for launching the manager orchestrator."""
    parser = argparse.ArgumentParser(description="Ball Balancing Robot - Process Orchestrator")
    parser.add_argument(
        "--mode",
        choices=["demo", "sim", "pi"],
        default="demo",
        help="System runtime mode (default: demo)",
    )
    parser.add_argument(
        "--camera-source",
        choices=["test", "real", "file"],
        default="test",
        help="Camera input source for CameraManager (default: test)",
    )
    parser.add_argument(
        "--video-file",
        default=None,
        help="Path to video file when camera-source is file",
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

    logger.info(
        f"Ball Balancing Robot launching in '{args.mode}' mode (PID {os.getpid()})..."
    )
    managers = build_managers_for_mode(
        mode=args.mode,
        camera_source=args.camera_source,
        video_file=args.video_file,
    )
    orchestrator = ManagerOrchestrator(managers=managers)

    try:
        orchestrator.run()
    except Exception as err:
        logger.exception(f"Fatal error in orchestrator: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

import multiprocessing
import multiprocessing.synchronize
import os
import signal
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Any, TypeVar

import zenoh
from loguru import logger
from pydantic import BaseModel

from src.messages.system import ControlCommand, ManagerState, ManagerStatus

if TYPE_CHECKING:
    from loguru import Logger

T = TypeVar("T", bound=BaseModel)


DEFAULT_ZENOH_ENDPOINT = "tcp/127.0.0.1:7447"


def create_zenoh_config(
    mode: str = "client",
    endpoint: str | None = DEFAULT_ZENOH_ENDPOINT,
) -> zenoh.Config:
    """
    Generate a standard Zenoh configuration for peer, client, or router sessions.

    Args:
        mode: Either 'client', 'peer', or 'router'. Defaults to 'client'.
        endpoint: Optional TCP locator for connecting or listening.

    Returns:
        A configured zenoh.Config instance.
    """
    conf = zenoh.Config()
    conf.insert_json5("mode", f'"{mode}"')
    if mode == "router" and endpoint:
        # Bind router to all interfaces so remote network clients (e.g. PC viewer) can connect
        listen_ep = endpoint.replace("127.0.0.1", "0.0.0.0")
        conf.insert_json5("listen/endpoints", f'["{listen_ep}"]')
    elif mode in ("peer", "client") and endpoint:
        conf.insert_json5("connect/endpoints", f'["{endpoint}"]')
    return conf


class BaseManager(ABC):
    """
    Abstract Base Class for all Manager processes in the system.

    Provides:
    - Multi-process lifecycle control (start, step loop, stop).
    - Contextualized logging via loguru.
    - Automatic Zenoh session management with type-safe Pydantic pub/sub helpers.
    - OS signal and Zenoh-based stop handling.
    """

    def __init__(
        self,
        name: str,
        loop_rate_hz: float | None = None,
        log_file: Path | None = None,
        zenoh_mode: str = "client",
        zenoh_endpoint: str | None = DEFAULT_ZENOH_ENDPOINT,
        zenoh_config_json5: str | None = None,
    ) -> None:
        """
        Initialize the BaseManager.

        Args:
            name: Unique identifier for this manager.
            loop_rate_hz: Target execution frequency for the step() loop in Hz.
                          If None, step() will be executed as fast as possible.
            log_file: Optional path to append process log output to.
            zenoh_mode: Zenoh operating mode ('peer', 'client', 'router').
            zenoh_endpoint: Optional TCP endpoint for Zenoh communication.
            zenoh_config_json5: Optional raw JSON5 configuration string.
        """
        self.name: str = name
        self.loop_rate_hz: float | None = loop_rate_hz
        self.log_file: Path | None = log_file
        self.zenoh_mode: str = zenoh_mode
        self.zenoh_endpoint: str | None = zenoh_endpoint
        self.zenoh_config_json5: str | None = zenoh_config_json5

        # Process synchronization and state
        self._stop_event: multiprocessing.synchronize.Event | None = None
        self._internal_stop_requested: bool = False
        self._step_count: int = 0

        # Zenoh references (initialized in child process)
        self._session: zenoh.Session | None = None
        self._subscribers: list[zenoh.Subscriber] = []
        self._publishers: dict[str, zenoh.Publisher] = {}

        # Contextual logger (initialized in child process to avoid pickling open streams)
        self._logger: Any | None = None

    @property
    def logger(self) -> Logger:
        """Contextualized logger instance bound to this manager's name."""
        if self._logger is None:
            self._logger = logger.bind(manager=self.name)
        return self._logger

    def __getstate__(self) -> dict[str, Any]:
        """Exclude unpicklable objects when spawning processes."""
        state = self.__dict__.copy()
        state["_logger"] = None
        state["_session"] = None
        state["_subscribers"] = []
        state["_publishers"] = {}
        return state

    def is_stopped(self) -> bool:
        """Check whether termination has been requested."""
        if self._internal_stop_requested:
            return True
        if self._stop_event is not None and self._stop_event.is_set():
            return True
        return False

    def stop(self) -> None:
        """Signal this manager to stop its loop gracefully."""
        self._internal_stop_requested = True
        if self._stop_event is not None and not self._stop_event.is_set():
            self._stop_event.set()

    def _setup_logging(self) -> None:
        """Configure contextualized loguru sink for the manager process."""
        # Remove default sink and reconfigure format with manager name and PID
        logger.remove()
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>[{extra[manager]}]</cyan> (PID {process}) - "
            "<level>{message}</level>"
        )
        logger.add(sys.stdout, format=log_format, level="INFO", enqueue=True)

        if self.log_file is not None:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                str(self.log_file),
                format=log_format,
                level="DEBUG",
                rotation="10 MB",
                retention="5 days",
                enqueue=True,
            )

        self._logger = logger.bind(manager=self.name)

    def _setup_signal_handlers(self) -> None:
        """Register OS signal handlers to ensure clean shutdown on SIGINT/SIGTERM."""

        def _handle_signal(signum: int, _frame: FrameType | None) -> None:
            sig_name = signal.Signals(signum).name
            self.logger.info(f"Received signal {sig_name}, initiating graceful stop...")
            self.stop()

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except (ValueError, AttributeError):
            # In case running in non-main thread during unit tests
            pass

    def _open_zenoh_session(self) -> None:
        """Open the Zenoh session in the current process with automatic standalone fallback."""
        if self.zenoh_config_json5 is not None:
            cfg = zenoh.Config.from_json5(self.zenoh_config_json5)
            self._session = zenoh.open(cfg)
        else:
            try:
                cfg = create_zenoh_config(mode=self.zenoh_mode, endpoint=self.zenoh_endpoint)
                self._session = zenoh.open(cfg)
            except Exception as err:
                self.logger.warning(
                    f"Could not connect Zenoh with mode='{self.zenoh_mode}' "
                    f"and endpoint='{self.zenoh_endpoint}' ({err}). Falling back to peer mode."
                )
                fallback_cfg = create_zenoh_config(mode="peer", endpoint=None)
                self._session = zenoh.open(fallback_cfg)

        self.logger.debug("Zenoh session opened successfully.")

    def _close_zenoh_session(self) -> None:
        """Undeclare subscribers and close the Zenoh session."""
        for sub in self._subscribers:
            try:
                sub.undeclare()
            except Exception as e:
                self.logger.warning(f"Error undeclaring subscriber: {e}")
        self._subscribers.clear()

        for pub in self._publishers.values():
            try:
                pub.undeclare()
            except Exception as e:
                self.logger.warning(f"Error undeclaring publisher: {e}")
        self._publishers.clear()

        if self._session is not None:
            try:
                self._session.close()
                self.logger.debug("Zenoh session closed successfully.")
            except Exception as e:
                self.logger.warning(f"Error closing Zenoh session: {e}")
            finally:
                self._session = None

    def publish_model(self, key_expr: str, model: BaseModel) -> None:
        """
        Publish a Pydantic model serialized as JSON to the specified Zenoh key.

        Args:
            key_expr: Zenoh key expression (e.g. 'robot/camera/frame').
            model: Pydantic model instance to publish.
        """
        if self._session is None:
            raise RuntimeError(f"Cannot publish on '{key_expr}': Zenoh session is not open.")

        json_bytes = model.model_dump_json().encode("utf-8")
        self._session.put(key_expr, json_bytes)

    def subscribe_model(
        self,
        key_expr: str,
        model_cls: type[T],
        callback: Callable[[T], None],
    ) -> zenoh.Subscriber:
        """
        Subscribe to a Zenoh key, automatically deserializing the payload into a Pydantic model.

        Args:
            key_expr: Zenoh key expression to listen on.
            model_cls: Expected Pydantic model class.
            callback: Function to invoke with the deserialized model instance.

        Returns:
            The created zenoh.Subscriber instance.
        """
        if self._session is None:
            raise RuntimeError(f"Cannot subscribe to '{key_expr}': Zenoh session is not open.")

        def _zenoh_callback(sample: zenoh.Sample) -> None:
            try:
                raw_bytes = bytes(sample.payload)
                model_instance = model_cls.model_validate_json(raw_bytes)
                callback(model_instance)
            except Exception as err:
                self.logger.error(
                    f"Failed to parse message on '{key_expr}' as {model_cls.__name__}: {err}"
                )

        subscriber = self._session.declare_subscriber(key_expr, _zenoh_callback)
        self._subscribers.append(subscriber)
        return subscriber

    def publish_status(self, state: ManagerState, message: str | None = None) -> None:
        """Publish current manager status telemetry over Zenoh."""
        status = ManagerStatus(
            manager_name=self.name,
            state=state,
            pid=os.getpid(),
            loop_count=self._step_count,
            message=message,
        )
        try:
            self.publish_model(f"robot/system/status/{self.name}", status)
        except Exception as err:
            self.logger.debug(f"Unable to publish status ({err})")

    def _on_system_control(self, cmd: ControlCommand) -> None:
        """Callback for system control commands."""
        if cmd.target in ("all", self.name):
            if cmd.action.upper() == "STOP":
                self.logger.info(f"Received remote STOP command from {cmd.sender}.")
                self.stop()

    def run(self, stop_event: multiprocessing.synchronize.Event | None = None) -> None:
        """
        Main execution target executed in the child process.

        Args:
            stop_event: Process event signaling when to stop the loop.
        """
        self._stop_event = stop_event
        self._setup_logging()
        self._setup_signal_handlers()

        self.logger.info(f"Starting manager '{self.name}' (PID {os.getpid()})...")

        period: float = 0.0
        if self.loop_rate_hz is not None and self.loop_rate_hz > 0:
            period = 1.0 / self.loop_rate_hz

        try:
            self._open_zenoh_session()

            # Subscribe to system control commands
            self.subscribe_model("robot/system/control", ControlCommand, self._on_system_control)

            # Inform system of initial running status
            self.publish_status(ManagerState.INITIALIZING)

            # Child setup hook
            self.setup()
            self.publish_status(ManagerState.RUNNING)
            self.logger.info(f"Manager '{self.name}' setup complete, entering execution loop.")

            # Main execution loop
            while not self.is_stopped():
                loop_start = time.perf_counter()

                self.step()
                self._step_count += 1

                if period > 0:
                    elapsed = time.perf_counter() - loop_start
                    sleep_duration = period - elapsed
                    if sleep_duration > 0:
                        time.sleep(sleep_duration)

            self.logger.info(f"Manager '{self.name}' loop terminated cleanly.")
            self.publish_status(ManagerState.STOPPING)

        except Exception as err:
            self.logger.exception(f"Unhandled error in manager '{self.name}': {err}")
            self.publish_status(ManagerState.ERROR, str(err))
            raise
        finally:
            self.logger.info(f"Tearing down manager '{self.name}'...")
            try:
                self.teardown()
            except Exception as err:
                self.logger.exception(f"Error during teardown of '{self.name}': {err}")

            self.publish_status(ManagerState.STOPPED)
            self._close_zenoh_session()
            self.logger.info(f"Manager '{self.name}' shutdown complete.")

    @abstractmethod
    def setup(self) -> None:
        """Initialize resources, connections, algorithms before the main loop."""

    @abstractmethod
    def step(self) -> None:
        """Perform one execution cycle of the manager logic."""

    @abstractmethod
    def teardown(self) -> None:
        """Release resources, hardware, and files on shutdown."""

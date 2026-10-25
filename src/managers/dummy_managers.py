from pathlib import Path

from src.managers.base_manager import DEFAULT_ZENOH_ENDPOINT, BaseManager
from src.messages.telemetry import TelemetryMessage


class DummyProducerManager(BaseManager):
    """Example producer manager that periodically publishes telemetry over Zenoh."""

    def __init__(
        self,
        name: str = "DummyProducer",
        loop_rate_hz: float = 2.0,
        log_file: Path | None = None,
        zenoh_mode: str = "client",
        zenoh_endpoint: str | None = DEFAULT_ZENOH_ENDPOINT,
    ) -> None:
        super().__init__(
            name=name,
            loop_rate_hz=loop_rate_hz,
            log_file=log_file,
            zenoh_mode=zenoh_mode,
            zenoh_endpoint=zenoh_endpoint,
        )
        self._counter: int = 0

    def setup(self) -> None:
        """Called once before the step loop starts."""
        self.logger.info("Setting up DummyProducerManager resources.")

    def step(self) -> None:
        """Publishes a typed telemetry message on each cycle."""
        self._counter += 1
        msg = TelemetryMessage(
            sender=self.name,
            counter=self._counter,
            metrics={"uptime_sec": float(self._counter) / (self.loop_rate_hz or 1.0)},
        )
        self.publish_model("robot/telemetry/demo", msg)
        self.logger.info(f"Published telemetry #{msg.counter}")

    def teardown(self) -> None:
        """Called once when stopping."""
        self.logger.info("Tearing down DummyProducerManager.")


class DummyConsumerManager(BaseManager):
    """Example consumer manager that subscribes to telemetry messages over Zenoh."""

    def __init__(
        self,
        name: str = "DummyConsumer",
        loop_rate_hz: float = 2.0,
        log_file: Path | None = None,
        zenoh_mode: str = "client",
        zenoh_endpoint: str | None = DEFAULT_ZENOH_ENDPOINT,
    ) -> None:
        super().__init__(
            name=name,
            loop_rate_hz=loop_rate_hz,
            log_file=log_file,
            zenoh_mode=zenoh_mode,
            zenoh_endpoint=zenoh_endpoint,
        )
        self._last_received_counter: int = 0

    def _on_telemetry(self, msg: TelemetryMessage) -> None:
        """Handle incoming telemetry messages."""
        self._last_received_counter = msg.counter
        self.logger.info(
            f"Received from '{msg.sender}' | Counter: {msg.counter} | Metrics: {msg.metrics}"
        )

    def setup(self) -> None:
        """Register Zenoh subscriber."""
        self.logger.info("Setting up DummyConsumerManager and subscribing to telemetry.")
        self.subscribe_model("robot/telemetry/demo", TelemetryMessage, self._on_telemetry)

    def step(self) -> None:
        """Periodic background checks or passive monitoring."""
        self.logger.debug(f"Consumer step active, last counter seen: {self._last_received_counter}")

    def teardown(self) -> None:
        """Called once when stopping."""
        self.logger.info("Tearing down DummyConsumerManager.")

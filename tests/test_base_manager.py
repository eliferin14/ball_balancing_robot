import multiprocessing as mp
import time

import pytest
import zenoh

from src.managers.base_manager import BaseManager, create_zenoh_config
from src.managers.dummy_managers import DummyConsumerManager, DummyProducerManager
from src.messages.system import ControlCommand
from src.messages.telemetry import TelemetryMessage


class MockConcreteManager(BaseManager):
    """Simple test manager tracking its lifecycle transitions."""

    def __init__(self, name: str = "TestMgr", loop_rate_hz: float = 20.0) -> None:
        super().__init__(name=name, loop_rate_hz=loop_rate_hz)
        self.setup_called: bool = False
        self.step_calls: int = 0
        self.teardown_called: bool = False

    def setup(self) -> None:
        self.setup_called = True

    def step(self) -> None:
        self.step_calls += 1
        if self.step_calls >= 3:
            self.stop()

    def teardown(self) -> None:
        self.teardown_called = True


def test_manager_lifecycle_in_thread() -> None:
    """Test that setup, step, and teardown execute in sequence."""
    mgr = MockConcreteManager()
    mgr.run()

    assert mgr.setup_called is True
    assert mgr.step_calls >= 3
    assert mgr.teardown_called is True
    assert mgr.is_stopped() is True


def test_pydantic_zenoh_message_exchange() -> None:
    """Test publishing and subscribing to typed Pydantic models over Zenoh."""
    test_endpoint = "tcp/127.0.0.1:7481"
    router_session = zenoh.open(create_zenoh_config("router", test_endpoint))

    received_messages: list[TelemetryMessage] = []

    sender = DummyProducerManager(
        name="Sender",
        zenoh_endpoint=test_endpoint,
    )
    receiver = DummyConsumerManager(
        name="Receiver",
        zenoh_endpoint=test_endpoint,
    )

    sender._open_zenoh_session()
    receiver._open_zenoh_session()

    try:
        receiver.subscribe_model(
            "test/telemetry",
            TelemetryMessage,
            lambda msg: received_messages.append(msg),
        )

        time.sleep(0.3)

        test_msg = TelemetryMessage(
            sender="Sender",
            counter=42,
            metrics={"test_metric": 3.14},
        )
        sender.publish_model("test/telemetry", test_msg)

        timeout = 2.0
        start = time.time()
        while len(received_messages) == 0 and (time.time() - start) < timeout:
            time.sleep(0.05)

        assert len(received_messages) == 1
        assert received_messages[0].sender == "Sender"
        assert received_messages[0].counter == 42
        assert received_messages[0].metrics["test_metric"] == pytest.approx(3.14)
    finally:
        sender._close_zenoh_session()
        receiver._close_zenoh_session()
        router_session.close()


def test_multiprocess_stop_event() -> None:
    """Test that a child manager process terminates when the stop event is signaled."""
    ctx = mp.get_context("spawn")
    stop_event = ctx.Event()

    mgr = DummyProducerManager(name="SpawnProducer", loop_rate_hz=20.0)
    proc = ctx.Process(target=mgr.run, args=(stop_event,), daemon=False)
    proc.start()

    time.sleep(0.3)
    assert proc.is_alive()

    # Trigger stop
    stop_event.set()
    proc.join(timeout=3.0)

    assert not proc.is_alive()
    assert proc.exitcode == 0


def test_zenoh_remote_stop_command() -> None:
    """Test that a manager stops when receiving a Zenoh ControlCommand STOP."""
    test_endpoint = "tcp/127.0.0.1:7482"
    router_session = zenoh.open(create_zenoh_config("router", test_endpoint))

    ctx = mp.get_context("spawn")
    stop_event = ctx.Event()

    mgr = DummyProducerManager(
        name="RemoteStopMgr",
        loop_rate_hz=20.0,
        zenoh_endpoint=test_endpoint,
    )
    proc = ctx.Process(target=mgr.run, args=(stop_event,), daemon=False)
    proc.start()

    time.sleep(0.5)
    assert proc.is_alive()

    # Send STOP command via the router session
    try:
        cmd = ControlCommand(action="STOP", target="RemoteStopMgr", sender="TestCommander")
        payload = cmd.model_dump_json().encode("utf-8")
        router_session.put("robot/system/control", payload)
    finally:
        pass

    proc.join(timeout=4.0)
    assert not proc.is_alive()
    assert proc.exitcode == 0

    router_session.close()

import socket

import pytest


def get_free_port() -> int:
    """Find a dynamically available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def free_zenoh_endpoint() -> str:
    """Provide a unique local Zenoh TCP endpoint for tests."""
    return f"tcp/127.0.0.1:{get_free_port()}"

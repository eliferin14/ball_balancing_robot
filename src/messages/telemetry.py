
from pydantic import Field

from src.messages.system import BaseZenohMessage


class TelemetryMessage(BaseZenohMessage):
    """Generic telemetry / ping message for testing and system health."""
    sender: str = Field(..., description="Name of the emitting manager")
    counter: int = Field(0, description="Monotonically increasing sequence number")
    metrics: dict[str, float] = Field(default_factory=dict, description="Arbitrary metric values")

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ManagerState(StrEnum):
    """Lifecycle state of a manager process."""
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class BaseZenohMessage(BaseModel):
    """Base model for all messages passed over Zenoh."""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of when the message was created"
    )


class ManagerStatus(BaseZenohMessage):
    """Status telemetry message emitted by a manager."""
    manager_name: str = Field(..., description="Unique name of the manager process")
    state: ManagerState = Field(..., description="Current lifecycle state")
    pid: int | None = Field(None, description="Process ID of the manager")
    loop_count: int = Field(0, description="Total execution steps performed")
    message: str | None = Field(None, description="Optional status or error description")


class ControlCommand(BaseZenohMessage):
    """Control command sent across managers or by the orchestrator."""
    action: str = Field(..., description="Action to perform, e.g., 'STOP', 'PAUSE', 'RESUME'")
    target: str = Field("all", description="Target manager name or 'all'")
    sender: str = Field("orchestrator", description="Sender identifier")

from pydantic import Field

from src.messages.system import BaseZenohMessage

BALL_POSITION_TOPIC = "robot/ball/position"


class BallPosition(BaseZenohMessage):
    """Pydantic model representing the ball's position detected in a frame."""

    x: float = Field(..., description="X coordinate of the ball center in pixels")
    y: float = Field(..., description="Y coordinate of the ball center in pixels")
    detected: bool = Field(
        ...,
        description="True if the ball was successfully detected, False otherwise",
    )
    frame_id: int | None = Field(
        None,
        description="Sequence ID of the frame from which the ball was detected",
    )


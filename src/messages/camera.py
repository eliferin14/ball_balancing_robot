from pydantic import Field

from src.messages.system import BaseZenohMessage


class FrameMetadata(BaseZenohMessage):
    """Metadata describing a video frame transmitted zero-copy over Zenoh."""

    frame_id: int = Field(..., description="Monotonically increasing frame sequence identifier")
    width: int = Field(..., description="Frame width in pixels")
    height: int = Field(..., description="Frame height in pixels")
    channels: int = Field(3, description="Number of color channels (e.g., 3 for BGR/RGB)")
    format: str = Field("BGR", description="Color format encoding (e.g. 'BGR', 'RGB', 'GRAY')")
    source_type: str = Field(..., description="Source type used ('real', 'test', 'file')")


from abc import ABC, abstractmethod

import numpy as np


class BallDetectorInterface(ABC):
    """Abstract interface defining the contract for ball detection algorithms."""

    @abstractmethod
    def detect_ball(self, frame: np.ndarray) -> tuple[float, float] | None:
        """
        Detect the ball in a BGR image frame.

        Args:
            frame: Input BGR image as a NumPy array.

        Returns:
            Tuple of (x, y) pixel coordinates if detected, or None if not detected.
        """
        pass

    @abstractmethod
    def draw_debug_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw detection overlays (e.g. centroid circle, tracking trail, mask) on the frame.

        Args:
            frame: Input BGR image as a NumPy array.

        Returns:
            Decorated BGR image for visual debugging.
        """
        pass

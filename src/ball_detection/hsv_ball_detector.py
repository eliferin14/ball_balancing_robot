from collections import deque

import cv2
import numpy as np
from pydantic import BaseModel, Field

from src.ball_detection.ball_detector_interface import BallDetectorInterface


class HSVDetectorConfig(BaseModel):
    """Configuration parameters for HSV color segmentation ball detection."""

    hue_min: float = Field(default=140.0, ge=0.0, le=180.0, description="Minimum Hue (0-180)")
    hue_max: float = Field(default=180.0, ge=0.0, le=180.0, description="Maximum Hue (0-180)")
    sat_min: float = Field(
        default=50.0, ge=0.0, le=255.0, description="Minimum Saturation (0-255)"
    )
    sat_max: float = Field(
        default=255.0, ge=0.0, le=255.0, description="Maximum Saturation (0-255)"
    )
    val_min: float = Field(
        default=50.0, ge=0.0, le=255.0, description="Minimum Value/Brightness (0-255)"
    )
    val_max: float = Field(
        default=255.0, ge=0.0, le=255.0, description="Maximum Value/Brightness (0-255)"
    )
    closure_kernel_size: int = Field(
        default=5, ge=1, description="Kernel size for erosion/dilation cleaning"
    )
    path_length: int = Field(
        default=20, ge=1, description="Number of past positions retained for debug trail"
    )


class HSVBallDetector(BallDetectorInterface):
    """
    Ball detector implementation using HSV color thresholding and contour moments.
    """

    def __init__(self, config: HSVDetectorConfig | None = None) -> None:
        """
        Initialize HSVBallDetector with configuration parameters.

        Args:
            config: Configuration settings or None to use defaults.
        """
        self.config: HSVDetectorConfig = config if config is not None else HSVDetectorConfig()
        k_size = self.config.closure_kernel_size
        self._kernel: np.ndarray = np.ones((k_size, k_size), dtype=np.uint8)
        self._path: deque[tuple[float, float] | None] = deque(maxlen=self.config.path_length)
        self._last_mask: np.ndarray | None = None

    def detect_ball(self, frame: np.ndarray) -> tuple[float, float] | None:
        """
        Detect ball centroid using HSV thresholding and image moments.

        Args:
            frame: Input BGR image array.

        Returns:
            (x, y) coordinates if ball is found, otherwise None.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Handle potential hue wrap-around (e.g. hue 170 to 10 for red)
        if self.config.hue_min <= self.config.hue_max:
            lower = np.array(
                [self.config.hue_min, self.config.sat_min, self.config.val_min],
                dtype=np.uint8,
            )
            upper = np.array(
                [self.config.hue_max, self.config.sat_max, self.config.val_max],
                dtype=np.uint8,
            )
            mask = cv2.inRange(hsv, lower, upper)
        else:
            lower1 = np.array(
                [self.config.hue_min, self.config.sat_min, self.config.val_min],
                dtype=np.uint8,
            )
            upper1 = np.array(
                [180, self.config.sat_max, self.config.val_max],
                dtype=np.uint8,
            )
            lower2 = np.array(
                [0, self.config.sat_min, self.config.val_min],
                dtype=np.uint8,
            )
            upper2 = np.array(
                [self.config.hue_max, self.config.sat_max, self.config.val_max],
                dtype=np.uint8,
            )
            mask = cv2.bitwise_or(
                cv2.inRange(hsv, lower1, upper1),
                cv2.inRange(hsv, lower2, upper2),
            )

        # Morphological noise cleanup
        if self.config.closure_kernel_size > 1:
            mask = cv2.erode(mask, self._kernel)
            mask = cv2.dilate(mask, self._kernel)

        self._last_mask = mask

        # Calculate centroid via spatial moments
        moments = cv2.moments(mask)
        area = moments["m00"]

        if area > 10.0:  # Minimum pixel area threshold to discard minor noise
            cx = float(moments["m10"] / area)
            cy = float(moments["m01"] / area)
            position = (cx, cy)
            self._path.append(position)
            return position

        self._path.append(None)
        return None

    def draw_debug_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Render debug overlays showing the detected ball position and historic movement trail.

        Args:
            frame: Raw BGR input frame.

        Returns:
            Frame with visual annotations.
        """
        debug_frame = frame.copy()

        # Draw trajectory trail
        path_len = len(self._path)
        for i in range(1, path_len):
            p1 = self._path[i - 1]
            p2 = self._path[i]
            if p1 is not None and p2 is not None:
                thickness = max(1, (3 * i) // (self._path.maxlen or 1))
                cv2.line(
                    debug_frame,
                    (int(p1[0]), int(p1[1])),
                    (int(p2[0]), int(p2[1])),
                    (0, 255, 255),
                    thickness,
                )

        # Highlight latest detected position
        if path_len > 0 and self._path[-1] is not None:
            last_pos = self._path[-1]
            pt = (int(last_pos[0]), int(last_pos[1]))
            cv2.circle(debug_frame, pt, 8, (0, 255, 0), 2)
            cv2.circle(debug_frame, pt, 2, (0, 0, 255), -1)
            cv2.putText(
                debug_frame,
                f"Ball: ({last_pos[0]:.1f}, {last_pos[1]:.1f})",
                (pt[0] + 12, pt[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )
        else:
            cv2.putText(
                debug_frame,
                "Ball: NOT DETECTED",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        return debug_frame

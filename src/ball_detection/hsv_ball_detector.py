from collections import deque

import cv2
import numpy as np
from pydantic import BaseModel, Field

from src.ball_detection.ball_detector_interface import BallDetectorInterface


class HSVDetectorConfig(BaseModel):
    """Configuration parameters for HSV color segmentation ball detection."""

    hue_min: float = Field(default=35.0, ge=0.0, le=180.0, description="Minimum Hue (0-180)")
    hue_max: float = Field(default=85.0, ge=0.0, le=180.0, description="Maximum Hue (0-180)")
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
    min_area: float = Field(
        default=20.0,
        ge=1.0,
        description="Minimum pixel area for the largest connected component",
    )
    min_circularity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum circularity (4*pi*area / perimeter^2) for the largest component",
    )
    use_convex_hull: bool = Field(
        default=True,
        description="Whether to apply convex hull to seal reflection notches on the ball contour",
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
        self._kernel: np.ndarray = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (k_size, k_size)
        )
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

        # Morphological opening (removes specks) followed by closing (bridges holes)
        if self.config.closure_kernel_size > 1:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)

        # Connected component analysis to isolate and retain only the largest component
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )

        if num_labels > 1:
            # Foreground labels start at 1 (index 0 is background)
            areas = stats[1:, cv2.CC_STAT_AREA]
            max_idx = int(np.argmax(areas))
            largest_label = max_idx + 1
            largest_area = float(areas[max_idx])

            if largest_area >= self.config.min_area:
                component_mask = ((labels == largest_label).astype(np.uint8) * 255)

                # Contour extraction
                contours, _ = cv2.findContours(
                    component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                if contours:
                    main_contour = max(contours, key=cv2.contourArea)

                    # Convex hull seals boundary reflection notches
                    if self.config.use_convex_hull:
                        main_contour = cv2.convexHull(main_contour)
                        component_mask = np.zeros_like(mask)
                        cv2.drawContours(component_mask, [main_contour], -1, 255, -1)
                        moments = cv2.moments(main_contour)
                        if moments["m00"] > 0:
                            largest_area = float(moments["m00"])
                            cx = float(moments["m10"] / largest_area)
                            cy = float(moments["m01"] / largest_area)
                        else:
                            cx, cy = centroids[largest_label]
                    else:
                        cx, cy = centroids[largest_label]

                    perimeter = cv2.arcLength(main_contour, closed=True)
                    if perimeter > 0:
                        circularity = (4.0 * np.pi * largest_area) / (perimeter * perimeter)
                        if circularity >= self.config.min_circularity:
                            self._last_mask = component_mask
                            position = (float(cx), float(cy))
                            self._path.append(position)
                            return position

        # No component found or component failed min_area / circularity threshold
        self._last_mask = np.zeros_like(mask)
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
        # Render background scene in black & white (grayscale)
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            debug_frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            debug_frame = frame.copy()

        # Restore original color strictly for the final detected mask of the ball
        if self._last_mask is not None and self._last_mask.shape == frame.shape[:2]:
            mask_indices = self._last_mask > 0
            debug_frame[mask_indices] = frame[mask_indices]

            # Draw bright green outline border around the detected ball component
            if np.any(mask_indices):
                contours, _ = cv2.findContours(
                    self._last_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                cv2.drawContours(debug_frame, contours, -1, (0, 255, 0), 2)

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
            # Red center dot (outer green circle removed as requested)
            cv2.circle(debug_frame, pt, 3, (0, 0, 255), -1)
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

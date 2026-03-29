import cv2
import numpy as np
from collections import deque

class BallDetector():
    def __init__(self, frameWidth=320, frameHeight=240, hMin=0, hMax=179, sMin=0, sMax=255, vMin=0, vMax=255, kernelSize=5, positionRecorderSize=20):
        # Define lower and upper bound arrays for HSV
        self.hsv_lowerBounds = np.array([hMin, sMin, vMin])
        self.hsv_upperBounds = np.array([hMax, sMax, vMax])

        # Define the kernel for erosion and dilation (closing)
        self.closing_kernel = np.ones((kernelSize,kernelSize), np.uint8)

        # Initialise ball position
        self.ball_x = 0
        self.ball_y = 0

        # Set position recorder size
        self.positionRecorderSize = positionRecorderSize
        self.ball_path = deque()
        
        self.raw_image = None
        self.mask = None
        self.processed_image = None

    def detect(self, frame):
        """
        Processes the given BGR frame to detect the ball.
        """
        self.raw_image = frame

        # Convert BGR to HSV
        hsv_image = cv2.cvtColor(self.raw_image, cv2.COLOR_BGR2HSV)

        # Apply HSV thresholds to get the binary mask
        self.mask = cv2.inRange(hsv_image, self.hsv_lowerBounds, self.hsv_upperBounds)

        # Erosion and dilation to remove noise
        self.mask = cv2.erode(self.mask, self.closing_kernel)
        self.mask = cv2.dilate(self.mask, self.closing_kernel)

        # Calculate the center of mass
        moments = cv2.moments(self.mask)
        if moments["m00"] != 0:
            self.ball_x = int(moments["m10"] / moments["m00"])
            self.ball_y = int(moments["m01"] / moments["m00"])

            # Store the position
            self.ball_path.append((self.ball_x, self.ball_y))
            if len(self.ball_path) > self.positionRecorderSize:
                self.ball_path.popleft()
        else:
            self.ball_x, self.ball_y = None, None
            self.ball_path.clear()

        return self.ball_x, self.ball_y

    def draw_image(self):
        """
        Creates a debug view: selective color for the ball, grayscale for background.
        """
        if self.raw_image is None or self.mask is None:
            return None
            
        gray_image = cv2.cvtColor(self.raw_image, cv2.COLOR_BGR2GRAY)
        gray_image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)

        # Highlight detected ball region in color
        self.processed_image = np.where(self.mask[:, :, np.newaxis] == 255, self.raw_image, gray_image)

        # Draw the center and path
        if self.ball_x is not None and self.ball_y is not None:
            cv2.circle(self.processed_image, (self.ball_x, self.ball_y), 5, (0, 255, 0), -1)
            self.draw_path(self.processed_image)

        return self.processed_image
    
    def draw_path(self, image):
        for i in range(1, len(self.ball_path)):
            p1 = self.ball_path[i-1]
            p2 = self.ball_path[i]
            thickness = max(1, int(4 * i / self.positionRecorderSize))
            cv2.line(image, p1, p2, (0, 255, 0), thickness)

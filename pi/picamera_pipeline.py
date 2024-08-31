import cv2
import numpy as np
from picamera2 import Picamera2
from collections import deque

class BallDetector():
    def __init__(self, frameWidth=640, frameHeight=480, hMin=0, hMax=179, sMin=0, sMax=255, vMin=0, vMax=255, kernelSize=5, positionRecorderSize=20):

        # Initialize camera
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"size": (frameWidth, frameHeight)}))
        self.picam2.start()

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

    # Pipeline used to detect the ball
    def detect(self):

        # Get the image
        self.raw_image = self.picam2.capture_array()

        # Change color space (RGB -> BGR -> HSV)
        self.raw_image = cv2.cvtColor(self.raw_image, cv2.COLOR_RGB2BGR)
        self.image = cv2.cvtColor(self.raw_image, cv2.COLOR_BGR2HSV)

        # Apply HSV thresholds to get the binary mask
        self.mask = cv2.inRange(self.image, self.hsv_lowerBounds, self.hsv_upperBounds)

        # Erosion and dilation
        self.mask = cv2.erode(self.mask, self.closing_kernel)
        self.mask = cv2.dilate(self.mask, self.closing_kernel)

        # Calculate the center of mass
        moments = cv2.moments(self.mask)
        if moments["m00"] != 0:
            self.ball_x = int(moments["m10"] / moments["m00"])
            self.ball_y = int(moments["m01"] / moments["m00"])

            # Store the position
            self.ball_path.append( (self.ball_x, self.ball_y) )

            # If the queue is full, pop the last element
            if len(self.ball_path) >= self.positionRecorderSize:
                self.ball_path.popleft()

            print(len(self.ball_path))

        else:
            self.ball_x, self.ball_y = None, None
            self.ball_path.clear()

        return self.ball_x, self.ball_y

    def draw_image(self):
        self.gray_image = cv2.cvtColor(self.raw_image, cv2.COLOR_BGR2GRAY)
        self.gray_image = cv2.cvtColor(self.gray_image, cv2.COLOR_GRAY2BGR)

        # Apply the mask to the image
        #self.processed_image = cv2.bitwise_and(self.processed_image, self.processed_image, self.mask)
        self.processed_image = np.where(self.mask[:, :, np.newaxis] == 255, self.raw_image, self.gray_image)

        # Draw the center of the ball
        if self.ball_x is not None and self.ball_y is not None:
            cv2.circle(self.processed_image, (self.ball_x, self.ball_y), 5, (0,255,0), -1)

        # Draw the path
        self.draw_path(self.processed_image)

        return self.processed_image
    
    def draw_path(self, image):
        for i in range(1,len(self.ball_path)):
            p1 = self.ball_path[i-1]
            p2 = self.ball_path[i]
            cv2.line(image, p1, p2, (0,255,0), max( 1, int(4*i/len(self.ball_path)) ))
    
    def show_processed_image(self):
        self.draw_image()
        cv2.imshow("Processed image", self.processed_image)


if __name__ == "__main__":

    ball_detector = BallDetector(hMin=120, sMin=127, vMin=127)

    while(True):
        ball_detector.detect()
        processed_image = ball_detector.draw_image()
        cv2.imshow('image', processed_image)
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
import cv2
import numpy as np
import sys
import os

# Add src/pi to path so we can import CameraManager
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pi'))
from camera_manager import CameraManager

def nothing(x):
    pass

def main():
    # Initialize the camera using our robust manager
    cam = CameraManager(target_width=640, target_height=480)

    # Create a window
    cv2.namedWindow('image')

    # Create trackbars for color change
    # Hue is from 0-179 for Opencv
    cv2.createTrackbar('HMin', 'image', 0, 179, nothing)
    cv2.createTrackbar('SMin', 'image', 0, 255, nothing)
    cv2.createTrackbar('VMin', 'image', 0, 255, nothing)
    cv2.createTrackbar('HMax', 'image', 0, 179, nothing)
    cv2.createTrackbar('SMax', 'image', 0, 255, nothing)
    cv2.createTrackbar('VMax', 'image', 0, 255, nothing)

    # Set default value for Max HSV trackbars
    cv2.setTrackbarPos('HMax', 'image', 179)
    cv2.setTrackbarPos('SMax', 'image', 255)
    cv2.setTrackbarPos('VMax', 'image', 255)

    # Initialize HSV min/max values
    phMin = psMin = pvMin = phMax = psMax = pvMax = 0

    print("Starting HSV selector. Adjust trackbars to isolate the ball. Press 'q' to quit.")

    try:
        while True:
            image = cam.get_frame()
            if image is None:
                continue
            
            # Get current positions of all trackbars
            hMin = cv2.getTrackbarPos('HMin', 'image')
            sMin = cv2.getTrackbarPos('SMin', 'image')
            vMin = cv2.getTrackbarPos('VMin', 'image')
            hMax = cv2.getTrackbarPos('HMax', 'image')
            sMax = cv2.getTrackbarPos('SMax', 'image')
            vMax = cv2.getTrackbarPos('VMax', 'image')

            # Set minimum and maximum HSV values to display
            lower = np.array([hMin, sMin, vMin])
            upper = np.array([hMax, sMax, vMax])

            # Convert to HSV format and color threshold
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower, upper)

            # Erode and dilate to remove noise
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.erode(mask, kernel, iterations = 2)
            mask = cv2.dilate(mask, kernel, iterations = 2)

            result = cv2.bitwise_and(image, image, mask=mask)

            # Calculate moments of the binary image
            moments = cv2.moments(mask)

            # Calculate x, y coordinate of center
            if moments["m00"] != 0:
                cX = int(moments["m10"] / moments["m00"])
                cY = int(moments["m01"] / moments["m00"])
            else:
                cX, cY = 0, 0

            cv2.circle(result, (cX, cY), 5, (0, 255, 0), -1)

            # Print if there is a change in HSV value
            if((phMin != hMin) | (psMin != sMin) | (pvMin != vMin) | (phMax != hMax) | (psMax != sMax) | (pvMax != vMax) ):
                print(f"Lower: ({hMin}, {sMin}, {vMin}), Upper: ({hMax}, {sMax}, {vMax})")
                phMin, psMin, pvMin, phMax, psMax, pvMax = hMin, sMin, vMin, hMax, sMax, vMax

            # Display result image
            cv2.imshow('image', result)
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

import cv2
import sys
import os

# Add src/pi to path so we can import CameraManager
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pi'))
from camera_manager import CameraManager

def main():
    # Initialize the camera using our robust manager
    # Defaulting to 640x480 for tools unless processing speed is critical
    cam = CameraManager(target_width=640, target_height=480)
    
    print("Starting video stream. Press 'q' to quit.")
    
    try:
        while True:
            # Capture frame-by-frame
            frame = cam.get_frame()
            
            if frame is None:
                continue
                
            # Display the resulting frame
            cv2.imshow('Video Stream', frame)
            
            # Break the loop on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        # When everything is done, release the capture
        cam.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

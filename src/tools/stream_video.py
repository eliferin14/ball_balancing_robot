from picamera2 import Picamera2
import cv2

# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

while True:
    # Capture frame-by-frame
    frame = picam2.capture_array()
    
    # Display the resulting frame
    cv2.imshow('Video Stream', frame)
    
    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything is done, release the capture
cv2.destroyAllWindows()
picam2.stop()

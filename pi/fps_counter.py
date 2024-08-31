from picamera2 import Picamera2
import time
import cv2

def count_fps():
    # Initialize the camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (320,240)}))
    picam2.start()
    
    # Initialize variables
    fps = 0
    frame_count = 0
    start_time = time.time()
    
    while True:
        # Capture frame-by-frame
        frame = picam2.capture_array()

        # Swap red and blue channels
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Increment frame count
        frame_count += 1
        
        # Calculate FPS
        elapsed_time = time.time() - start_time
        if elapsed_time > 1:
            fps = frame_count / elapsed_time
            frame_count = 0
            start_time = time.time()
        
        # Display the resulting frame
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.imshow('Frame', frame)
        
        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release the camera and close windows
    picam2.stop()
    cv2.destroyAllWindows()

# Call the function
count_fps()

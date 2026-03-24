import cv2
import sys

class CameraManager:
    def __init__(self, width=640, height=480, target_width=320, target_height=240, framerate=None, crop=None):
        """
        GStreamer-based Camera Manager for Raspberry Pi.
        Uses appsink properties to ensure zero-latency / latest-frame processing.
        
        :param width: Sensor capture width
        :param height: Sensor capture height
        :param target_width: Width after hardware scaling
        :param target_height: Height after hardware scaling
        :param framerate: Optional framerate (set to None for auto)
        :param crop: Optional tuple (top, bottom, left, right) for hardware cropping
        """
        self.width = width
        self.height = height
        self.target_width = target_width
        self.target_height = target_height
        
        # Build GStreamer Pipeline
        # Removed hardcoded framerate to prevent crashes if the sensor doesn't support it.
        # appsink drop=True max-buffers=1 ensures that if the processing loop is slow,
        # older frames are dropped and read() always returns the most recent one.
        gst_elements = [
            f"libcamerasrc ! video/x-raw,width={self.width},height={self.height}",
            "queue max-size-buffers=1 leaky=downstream", # Low latency queue
            "videoconvert"
        ]
        
        if crop:
            t, b, l, r = crop
            gst_elements.append(f"videocrop top={t} bottom={b} left={l} right={r}")
            
        gst_elements.append(f"videoscale ! video/x-raw,width={self.target_width},height={self.target_height}")
        gst_elements.append("queue max-size-buffers=1 leaky=downstream") # Final buffer before app
        gst_elements.append("videoconvert ! video/x-raw,format=BGR ! appsink drop=True max-buffers=1")
        
        self.pipeline = " ! ".join(gst_elements)
        print(f"Starting GStreamer pipeline: {self.pipeline}")
        
        self.cap = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)
        
        if not self.cap.isOpened():
            print("Error: Could not open GStreamer pipeline.", file=sys.stderr)
            sys.exit(1)

    def get_frame(self):
        """
        Reads the most recent frame from the pipeline.
        Due to max-buffers=1 and drop=True, this is guaranteed to be the latest frame.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        """Releases the camera resources."""
        self.cap.release()

if __name__ == "__main__":
    # Quick test
    cam = CameraManager()
    try:
        while True:
            frame = cam.get_frame()
            if frame is not None:
                cv2.imshow("Latest Frame", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()

import cv2
import sys

class CameraManager:
    def __init__(self, target_width=320, target_height=240, crop=None):
        """
        GStreamer-based Camera Manager for Raspberry Pi.
        Designed for robustness on modern libcamera-based OS and legacy systems.
        """
        self.target_width = target_width
        self.target_height = target_height
        
        # Try libcamerasrc first (Modern Pi OS)
        if self._try_pipeline("libcamerasrc", crop):
            return
            
        # Try v4l2src as fallback (Legacy/Generic)
        print("libcamerasrc failed, trying v4l2src fallback...")
        if self._try_pipeline("v4l2src", crop):
            return

        print("Error: Could not open any GStreamer camera source.", file=sys.stderr)
        sys.exit(1)

    def _try_pipeline(self, source, crop):
        """Builds and attempts to open a GStreamer pipeline."""
        gst_elements = [source]
        
        # For libcamerasrc, we often need a basic cap to start
        if source == "libcamerasrc":
            gst_elements.append("video/x-raw")
        
        gst_elements.append("videoconvert")
        
        if crop:
            t, b, l, r = crop
            gst_elements.append(f"videocrop top={t} bottom={b} left={l} right={r}")
            
        gst_elements.append("videoscale")
        gst_elements.append(f"video/x-raw,width={self.target_width},height={self.target_height}")
        gst_elements.append("videoconvert")
        gst_elements.append("video/x-raw,format=BGR")
        gst_elements.append("appsink drop=True max-buffers=1")
        
        pipeline = " ! ".join(gst_elements)
        print(f"Attempting pipeline: {pipeline}")
        
        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if self.cap.isOpened():
            self.pipeline = pipeline
            return True
        return False

    def get_frame(self):
        """Reads the most recent frame from the pipeline."""
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        """Releases the camera resources."""
        if hasattr(self, 'cap'):
            self.cap.release()

if __name__ == "__main__":
    cam = CameraManager()
    try:
        while True:
            frame = cam.get_frame()
            if frame is not None:
                cv2.imshow("Camera Stream", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()

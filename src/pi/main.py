import cv2
import time
import sys
import numpy as np

# Local imports
from camera_manager import CameraManager
from ball_detector import BallDetector

class SystemManager:
    def __init__(self, mode="CAMERA"):
        self.mode = mode.upper()
        
        # 1. Initialize Camera (Targeting 320x240 for processing efficiency)
        self.camera = CameraManager(target_width=320, target_height=240, framerate=60)
        
        # 2. Initialize Ball Detector (Tune HSV via tools/hsv_range_selector.py)
        # Placeholder HSV values (Red ball example: 0, 100, 100 to 10, 255, 255)
        self.detector = BallDetector(frameWidth=320, frameHeight=240)
        
        self.fps = 0
        self.frame_count = 0
        self.last_fps_time = time.time()

    def run(self):
        print(f"Starting loop in {self.mode} mode. Press 'q' to quit.")
        try:
            while True:
                loop_start = time.time()
                
                # --- STEP 1: CAPTURE ---
                frame = self.camera.get_frame()
                if frame is None:
                    continue

                # --- STEP 2: PROCESSING ---
                ball_pos = (None, None)
                if self.mode in ["DETECTION", "CONTROL"]:
                    ball_pos = self.detector.detect(frame)

                # --- STEP 3: DEBUG VIEW GENERATION ---
                debug_view = self._get_debug_view(frame)
                
                # --- STEP 4: VISUALIZATION ---
                cv2.imshow("Robot Debug Stream", debug_view)
                
                # Update FPS
                self.frame_count += 1
                if time.time() - self.last_fps_time > 1.0:
                    self.fps = self.frame_count
                    self.frame_count = 0
                    self.last_fps_time = time.time()

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            self.cleanup()

    def _get_debug_view(self, frame):
        """Generates a mode-specific debug frame with overlays."""
        if self.mode == "CAMERA":
            view = frame.copy()
        elif self.mode in ["DETECTION", "CONTROL"]:
            # Get the 'selective color' view from detector
            view = self.detector.draw_image()
            if view is None: view = frame.copy()
            
            # Optionally stack the binary mask at the bottom or corner
            mask_small = cv2.resize(self.detector.mask, (80, 60))
            mask_bgr = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
            view[0:60, 0:80] = mask_bgr # Show mask in top-left corner
            
            # Draw coordinates if ball is found
            bx, by = self.detector.ball_x, self.detector.ball_y
            if bx is not None:
                cv2.putText(view, f"Pos: {bx},{by}", (10, 230), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Common overlays (FPS and Mode)
        cv2.putText(view, f"FPS: {self.fps}", (240, 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(view, f"MODE: {self.mode}", (10, 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        return view

    def cleanup(self):
        print("\nCleaning up resources...")
        self.camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "CAMERA"
    manager = SystemManager(mode=mode)
    manager.run()

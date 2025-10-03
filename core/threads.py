""" Created on Mon Apr 15 14:19:35 2024
    @author: dcupolillo """

import numpy as np
import cv2
import serial
import time
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import time
import imageio
try:
    if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except Exception:
    pass

class VideoThread(QThread):

    frame_captured = pyqtSignal(np.ndarray)

    def __init__(
            self,
            capture_device: int = 0,
    ) -> None:

        super().__init__()
        self.capture_device = capture_device
        self.running = False
        self.cap = None

    def run(self) -> None:
        
        # Use DirectShow backend for uEye camera compatibility
        self.cap = cv2.VideoCapture(self.capture_device, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Fallback to default backend
            self.cap = cv2.VideoCapture(self.capture_device)

        while self.running:

            ret, frame = self.cap.read()

            if ret:
                frame = cv2.flip(frame, 1)
                self.frame_captured.emit(frame)
            else:
                break

        if self.cap:
            self.cap.release()

    def start_video(
            self,
            save: bool = False,
            output: str = None
    ) -> None:

        self.save = save
        self.output = str(output) if output else None
        self.start()

    def stop_video(self) -> None:

        self.running = False
        self.wait()
        if self.cap:
            self.cap.release()

    def start(self) -> None:

        self.running = True
        super().start()

    def stop(self) -> None:

        self.stop_video()


class RecordingVideoThread(QThread):
    
    frame_recorded = pyqtSignal(np.ndarray)
    recording_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    recording_metadata = pyqtSignal(dict)
    
    def __init__(
            self,
            filename: str,
            protocol_duration: float,
            mouse_data: dict,
            capture_device: int = 0,
            parent=None
    ) -> None:
        
        super().__init__(parent)
        self.filename = filename
        self.protocol_duration = protocol_duration
        self.mouse_data = mouse_data
        self.capture_device = capture_device
        self.running = False
        self.cap = None
        self.video_writer = None
        self.video_path = None
        self.fps = 30
        self.frame_width = 0
        self.frame_height = 0
        self.imageio_writer = None  # imageio video writer
        self.imageio_writer = None  # imageio video writer
        self.frames_buffer = []  # Store frames in memory as fallback
        self.use_frame_buffer = False
        
    def run(self) -> None:
        
        try:
            # Use DirectShow backend for better industrial camera support (uEye UI-122xLE)
            self.cap = cv2.VideoCapture(self.capture_device, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                # Fallback to default backend if DirectShow fails
                self.cap = cv2.VideoCapture(self.capture_device)
                
            if not self.cap.isOpened():
                self.error_occurred.emit("Cannot open uEye camera")
                return
            
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Create timestamped filename
            base = Path(self.filename)
            ts = time.strftime('%H%M%S')
            self.video_path = str(base.with_name(f"{base.stem}_{ts}.avi"))
            
            # Ensure .avi extension
            if not self.video_path.lower().endswith('.avi'):
                dot = self.video_path.rfind('.')
                self.video_path = (self.video_path[:dot] if dot != -1 else self.video_path) + '.avi'
            
            # Initialize imageio video writer for reliable video recording
            # Ensure directory exists
            Path(self.video_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Change to MP4 for better compatibility with imageio
            self.video_path = str(Path(self.video_path).with_suffix('.mp4'))
            
            try:
                # Use imageio with ffmpeg backend for reliable video writing
                self.imageio_writer = imageio.get_writer(
                    self.video_path,
                    fps=self.fps,
                    codec='libx264',  # Widely supported H.264 codec
                    quality=8,  # Good quality (scale 1-10)
                    pixelformat='yuv420p'  # Compatible with most players
                )
                
            except Exception as e:
                self.error_occurred.emit(
                    f"Failed to initialize imageio video writer: {str(e)}\n"
                    f"Path: {self.video_path}")
                return
            
            # Emit metadata for RecordFrame to use
            metadata = {
                'video_path': self.video_path,
                'fps': self.fps,
                'frame_width': self.frame_width,
                'frame_height': self.frame_height
            }
            self.recording_metadata.emit(metadata)
            
            start_time = time.time()
            frame_number = 0
            frame_time = 1.0 / self.fps  # Target time per frame (0.033s for 30fps)
            
            while self.running and (time.time() - start_time) < self.protocol_duration:
                
                frame_start = time.time()
                ret, frame = self.cap.read()
                
                if ret:
                    # Flip horizontally
                    frame_flipped = cv2.flip(frame, 1)
                    
                    # Write clean frame to file using imageio (without overlays for better recording quality)
                    if self.imageio_writer:
                        # Convert BGR to RGB (imageio expects RGB)
                        frame_rgb = cv2.cvtColor(frame_flipped, cv2.COLOR_BGR2RGB)
                        self.imageio_writer.append_data(frame_rgb)
                        

                    
                    # Add text overlays only for display (every 3rd frame to reduce overhead)
                    if frame_number % 3 == 0:
                        display_frame = frame_flipped.copy()
                        elapsed_time = time.time() - start_time
                        
                        # Combine text overlays into fewer calls for better performance
                        cv2.putText(
                            display_frame, f'Frame={frame_number} | Time={elapsed_time:.1f}s', 
                            (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
                        
                        cv2.putText(
                            display_frame, f"{self.mouse_data['Mouse ID']} - {self.mouse_data['Behavior test']}",
                            (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
                        
                        # Emit frame for PyQt display (less frequently)
                        self.frame_recorded.emit(display_frame)
                    
                    frame_number += 1
                    
                    # Consistent timing to reduce USB load variations
                    processing_time = time.time() - frame_start
                    sleep_time = max(0, frame_time - processing_time)
                    if sleep_time > 0:
                        # Use consistent sleep to maintain steady USB data flow
                        self.msleep(int(sleep_time * 1000))
                    elif processing_time > frame_time:
                        # If processing is taking too long, yield CPU briefly
                        self.msleep(1)
                        
                else:
                    # If frame capture fails, still maintain timing
                    self.msleep(33)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.cleanup()
            self.recording_finished.emit()
            
    def cleanup(self):
        """Properly cleanup video resources to prevent file corruption"""
        try:
            if self.imageio_writer:
                self.imageio_writer.close()
                print(f"Video saved: {Path(self.video_path).name}")
        except Exception as e:
            print(f"Error closing video writer: {e}")
        
        try:
            if self.cap:
                self.cap.release()
        except Exception as e:
            print(f"Error releasing camera: {e}")
        
        cv2.destroyAllWindows()
        
    def start_recording(self):
        self.running = True
        # Set higher thread priority for stable video recording
        self.setPriority(QThread.HighPriority)
        self.start()
        
    def stop_recording(self):
        """Stop recording and ensure proper cleanup"""
        self.running = False
        
        # Wait for thread to finish with timeout
        if not self.wait(5000):  # 5 second timeout
            print("Warning: Recording thread timeout")
            self.terminate()  # Force terminate if needed


class SerialThread(QThread):

    def __init__(
            self,
            com_port: str,
            protocol
    ) -> None:

        super().__init__()
        self.com_port = com_port
        self.protocol = protocol

        self.ser = None

    def run(self):

        if not self.ser:
            self.ser = serial.Serial(
                self.com_port,
                baudrate=9600,
                write_timeout=10)

            if not self.ser.is_open:
                self.ser.open()

        self.protocol.run(self.ser)

    def stop(self):

        if self.ser and self.ser.is_open:
            self.protocol.stop()
            self.ser.close()
            self.ser = None
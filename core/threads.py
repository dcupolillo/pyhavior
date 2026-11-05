import numpy as np
import cv2
import time
from pathlib import Path
from typing import Optional
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from pyhavior.core.arduino import ArduinoBoard
from pyhavior.core.camera import Camera, CameraPreview, CameraError
from pyhavior.core.clock import SessionClock
try:
    if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except Exception:
    pass

class VideoThread(QThread):

    frame_captured = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(
            self,
            capture_device: int = 0,
    ) -> None:

        super().__init__()
        self.capture_device = capture_device
        self.running = False

    def run(self) -> None:

        preview = CameraPreview(self.capture_device)

        try:
            preview.open()
        except CameraError as e:
            self.error_occurred.emit(str(e))
            return

        try:
            while self.running:
                frame = preview.read()
                if frame is None:
                    if self.running:
                        self.error_occurred.emit("Lost the connection to the camera")
                    break
                self.frame_captured.emit(frame.image)
        finally:
            preview.close()

    def start_video(self) -> None:
        self.start()

    def stop_video(self) -> None:
        self.running = False
        self.wait()

    def start(self) -> None:
        """Start the video capture thread.
           Sets the running flag to True and calls the thread's start method."""
        self.running = True
        super().start()

    def stop(self) -> None:
        """Stop the video capture thread.
           Sets the running flag to False and waits for the thread to finish."""
        self.stop_video()


class RecordingVideoThread(QThread):
    
    """
    Records a `Camera` on the shared session clock.

    Lifecycle: `start_recording()` opens the camera (and writer) and emits
    `ready`; the thread then waits for `clock.start()`, records until the
    clock stops (or `stop_recording()` is called) and closes everything.
    The thread never decides when the session ends.
    """

    frame_recorded = pyqtSignal(np.ndarray)
    recording_finished = pyqtSignal()  # run() is over and the file is closed
    error_occurred = pyqtSignal(str)
    recording_metadata = pyqtSignal(dict)
    ready = pyqtSignal()  # camera and writer are open, waiting for the clock
    first_frame = pyqtSignal(float)  # session time of the first frame written

    def __init__(
            self,
            camera: Camera,
            clock: SessionClock,
            parent: QObject = None
    ) -> None:

        super().__init__(parent)
        self.camera = camera
        self.clock = clock
        self.running = False

    def run(self) -> None:

        # Set higher thread priority for stable video recording
        # once thread is running, safe to set priority
        self.setPriority(QThread.HighPriority)

        try:
            try:
                self.camera.open()
            except CameraError as e:
                self.error_occurred.emit(str(e))
                return

            self.recording_metadata.emit(self.camera.metadata())
            self.ready.emit()

            while not self.clock.started:
                if self.clock.stopped or not self.running:
                    return
                self.clock.wait_for_start(0.05)

            self._record_loop()

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.cleanup()
            self.recording_finished.emit()

    def _record_loop(self) -> None:

        frame_time = 1.0 / self.camera.fps
        first = True

        while self.running and self.clock.running:

            loop_start = time.perf_counter()
            frame = self.camera.read()

            if frame is None:
                # If frame capture fails, still maintain timing
                self.msleep(33)
                continue

            if first:
                self.first_frame.emit(frame.t)
                first = False

            # Plain frames for the preview, every 3rd one to reduce overhead.
            # Session info (elapsed time, mouse, protocol) lives in the session window.
            if frame.index % 3 == 0:
                self.frame_recorded.emit(frame.image)

            # Consistent timing to reduce USB load variations
            sleep_time = frame_time - (time.perf_counter() - loop_start)
            self.msleep(int(sleep_time * 1000) if sleep_time > 0 else 1)

    def cleanup(self) -> None:
        """Close the camera and writer to prevent file corruption."""
        video_path = self.camera.video_path
        self.camera.close()
        if video_path:
            print(f"Video saved: {Path(video_path).name}")

    def start_recording(self) -> None:
        self.running = True
        self.start()

    def stop_recording(self):
        """Stop recording and ensure proper cleanup"""
        self.running = False
        
        # Wait for thread to finish with timeout
        if not self.wait(5000):  # 5 second timeout
            print("Warning: Recording thread timeout")
            self.terminate()  # Force terminate if needed


class SerialThread(QThread):
    """
    Runs a protocol on an `ArduinoBoard`, optionally on a shared session clock.

    Session mode (`clock` given): `start()` opens the board and emits `ready`;
    the protocol then waits for `clock.start()` and runs until its duration
    elapses, `stop()` is called or the clock stops.

    Standalone mode (`clock=None`), used by the bench tools (fill tubes,
    digital/analog tests): the protocol is simply run on the board until
    `stop()`; those protocols know nothing about the clock.

    The board is always closed when the thread ends. Qt's built-in
    `finished` signal marks the end of the run.
    """

    ready = pyqtSignal()  # board is open (session mode: waiting for the clock)
    error_occurred = pyqtSignal(str)

    def __init__(
            self,
            board: ArduinoBoard,
            protocol,
            clock: Optional[SessionClock] = None
    ) -> None:

        super().__init__()
        self.board = board
        self.protocol = protocol
        self.clock = clock

    def run(self):

        try:
            self.board.open()
        except Exception as e:
            self.error_occurred.emit(f"Cannot open Arduino board: {e}")
            return

        try:
            self.ready.emit()
            if self.clock is None:
                self.protocol.run(self.board)
            else:
                self.protocol.run(self.board, self.clock)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            # The runner does not close the connection itself
            self.board.close()

    def stop(self):
        """Ask the protocol to stop; run() closes the board on its way out."""
        self.protocol.request_stop()

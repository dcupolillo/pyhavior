import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import imageio
import numpy as np

from pyhavior.core.clock import SessionClock


class CameraError(RuntimeError):
    """Raised when the camera or its writer cannot be set up."""


@dataclass(frozen=True)
class Frame:
    index: int  # index among successfully grabbed frames
    t: float  # session time (s) right after the frame was grabbed
    image: np.ndarray  # BGR, flipped if requested


class VideoWriter:
    """
    Write grayscale frames to an H.264 .mp4 and log one timestamp per frame
    to a sidecar CSV (`<video>_timestamps.csv`).

    The container fps is nominal; the CSV holds the true frame times.
    """

    def __init__(
            self,
            path: str,
            fps: float = 25,
            quality: int = 8
    ) -> None:

        self.path = Path(path).with_suffix('.mp4')
        self.timestamps_path = self.path.with_name(f"{self.path.stem}_timestamps.csv")
        self.fps = fps
        self.quality = quality
        self._writer = None
        self._csv_file = None
        self._csv = None
        self.n_written = 0

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = imageio.get_writer(
            str(self.path),
            fps=self.fps,
            codec='libx264',
            quality=self.quality,
            pixelformat='yuv420p')
        self._csv_file = open(self.timestamps_path, 'w', newline='')
        self._csv = csv.writer(self._csv_file)
        self._csv.writerow(['frame', 'session_time_s'])

    def write(self, frame: Frame) -> None:
        if self._writer is None:
            raise RuntimeError("VideoWriter is not open")
        gray = cv2.cvtColor(frame.image, cv2.COLOR_BGR2GRAY)
        self._writer.append_data(gray)
        self._csv.writerow([self.n_written, f"{frame.t:.6f}"])
        self.n_written += 1

    def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        if self._csv_file is not None:
            self._csv_file.close()
            self._csv_file = None
            self._csv = None


class Camera:
    """
    OpenCV camera whose frames are timestamped with a SessionClock.

    Usage:
        cam = Camera(device, clock, output_path=...)
        cam.open()                 # prepare phase: may raise CameraError
        clock.wait_for_start()
        while clock.running:
            frame = cam.read()     # None if the grab failed
            ...
        cam.close()

    `output_path=None` disables writing (preview only).
    `read()` timestamps with `clock.now()`, so call it after the clock started.
    """

    def __init__(
            self,
            device: int,
            clock: SessionClock,
            output_path: Optional[str] = None,
            fps: float = 25,
            flip_horizontal: bool = True
    ) -> None:

        self.device = device
        self.clock = clock
        self.fps = fps
        self.flip_horizontal = flip_horizontal
        self.writer = VideoWriter(output_path, fps) if output_path else None
        self._cap = None
        self._n_grabbed = 0
        self.frame_width = 0
        self.frame_height = 0

    @property
    def video_path(self) -> Optional[str]:
        return str(self.writer.path) if self.writer else None

    @property
    def timestamps_path(self) -> Optional[str]:
        return str(self.writer.timestamps_path) if self.writer else None

    @property
    def n_frames_written(self) -> int:
        return self.writer.n_written if self.writer else 0

    def open(self) -> None:
        """Open the device and writer. Raises CameraError on failure."""
        self._cap = cv2.VideoCapture(self.device)
        if not self._cap.isOpened():
            self._cap = None
            raise CameraError(f"Cannot open camera device {self.device}")

        # Buffer of 1 keeps the latest frame and reduces latency
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.frame_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if self.writer:
            try:
                self.writer.open()
            except Exception as e:
                self.close()
                raise CameraError(
                    f"Failed to initialize video writer: {e}\n"
                    f"Path: {self.writer.path}") from e

    def read(self, write: bool = True) -> Optional[Frame]:
        """Grab one frame, timestamp it and (optionally) write it to file."""
        if self._cap is None:
            raise CameraError("Camera is not open")

        ok, image = self._cap.read()
        if not ok:
            return None
        t = self.clock.now()

        if self.flip_horizontal:
            image = cv2.flip(image, 1)

        frame = Frame(self._n_grabbed, t, image)
        self._n_grabbed += 1

        if write and self.writer:
            self.writer.write(frame)
        return frame

    def metadata(self) -> dict:
        return {
            'video_path': self.video_path,
            'timestamps_path': self.timestamps_path,
            'fps': self.fps,
            'frame_width': self.frame_width,
            'frame_height': self.frame_height,
        }

    def close(self) -> None:
        if self.writer:
            try:
                self.writer.close()
            except Exception as e:
                print(f"Error closing video writer: {e}")
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                print(f"Error releasing camera: {e}")
            self._cap = None


class CameraPreview:
    """
    Live preview of a camera: no writer, no session clock.

    It wraps a `Camera` with a private clock that is started immediately,
    so the capture, buffering and flip logic is shared with recording.
    Only one object can own a device at a time: close the preview before
    opening a `Camera` on the same device.
    """

    def __init__(
            self,
            device: int = 0,
            flip_horizontal: bool = True
    ) -> None:

        self._clock = SessionClock()
        self._camera = Camera(
            device,
            self._clock,
            output_path=None,
            flip_horizontal=flip_horizontal)

    def open(self) -> None:
        """Open the device. Raises CameraError on failure."""
        self._camera.open()
        self._clock.start()

    def read(self) -> Optional[Frame]:
        """Grab one frame, or None if the grab failed."""
        return self._camera.read(write=False)

    def close(self) -> None:
        self._camera.close()

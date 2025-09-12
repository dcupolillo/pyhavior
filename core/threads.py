""" Created on Mon Apr 15 14:19:35 2024
    @author: dcupolillo """

import numpy as np
import cv2
import serial
from PyQt5.QtCore import QThread, pyqtSignal


class VideoThread(QThread):

    frame_captured = pyqtSignal(np.ndarray)

    def __init__(
            self,
            capture_device: int = 0
    ) -> None:

        super().__init__()
        self.capture_device = capture_device
        self.running = False

    def run(self) -> None:

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


class SerialThread(QThread):

    def __init__(
            self,
            com_port: str,
            protocol: object):

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
""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

import cv2
import numpy as np
from PyQt5 import QtGui
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel
from PyQt5.QtCore import pyqtSignal, Qt


class VideoWindow(QWidget):
    """Live video stream window."""

    video_window_closed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Live Video Stream")
        self.setGeometry(0, 0, 1280, 960)

        self.layout = QGridLayout()

        self.video_label = QLabel('Waiting for video stream...')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.video_label, 0, 0)

        self.setLayout(self.layout)

    def display_frame(self, frame: np.ndarray) -> None:
        """Display video frame in the preview window"""
        # ensure RGB format
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_image.shape
        bytes_per_line = width * channel

        # Convert the image to a format suitable for Qt
        # Qt expects a contiguous array in memory
        convert_to_Qt_format = QImage(
            rgb_image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888)

        p = convert_to_Qt_format.scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.KeepAspectRatio)

        self.video_label.setPixmap(QPixmap.fromImage(p))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle video window close event"""
        if hasattr(self, 'video_thread'):
            self.video_thread.stop()
        self.video_window_closed.emit()
        event.accept()
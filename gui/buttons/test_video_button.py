""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5.QtWidgets import QMessageBox, QPushButton, QWidget

from pyhavior.core.threads import VideoThread
from pyhavior.gui.windows import VideoWindow


class TestVideoButton(QPushButton):
    """Button to start/stop video preview."""

    def __init__(
            self,
            parent: QWidget = None,
            get_camera_device: callable = None
    ) -> None:
        super().__init__('Preview Video')

        self.setCheckable(True)
        self.clicked.connect(self.toggle_video_stream)
        self.video_window = VideoWindow()
        self.video_thread = None
        self.get_camera_device = get_camera_device  # Function to get current camera device

        self.video_window.video_window_closed.connect(
            self.untoggle_video_stream)

    def toggle_video_stream(self) -> None:
        if self.isChecked():
            if not self.video_thread:
                # Get the current camera device (defaults to 0 if not available)
                camera_device = 0
                if self.get_camera_device:
                    try:
                        camera_device = self.get_camera_device()
                    except Exception:
                        camera_device = 0

                if camera_device is None:
                    QMessageBox.information(
                        self,
                        'No camera selected',
                        'Video is disabled. Choose a camera with '
                        '"Select Camera" to preview it.')
                    self.setChecked(False)
                    return

                self.video_thread = VideoThread(capture_device=camera_device)
                self.video_thread.frame_captured.connect(
                    self.video_window.display_frame)
                self.video_thread.error_occurred.connect(self.on_video_error)
                self.video_thread.start()
            self.setText('Quit')
            self.video_window.show()
        else:
            self.untoggle_video_stream()

    def on_video_error(self, message: str) -> None:
        """The preview could not start or lost the camera."""

        QMessageBox.warning(self, 'Preview error', message)
        self.untoggle_video_stream()

    def untoggle_video_stream(self) -> None:
        self.setText('Preview Video')
        self.setChecked(False)
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        self.video_window.close()
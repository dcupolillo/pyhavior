""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5.QtWidgets import QPushButton, QWidget

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
            self.setText('Quit')
            if not self.video_thread:
                # Get the current camera device (defaults to 0 if not available)
                camera_device = 0
                if self.get_camera_device:
                    try:
                        camera_device = self.get_camera_device()
                    except:
                        camera_device = 0
                
                self.video_thread = VideoThread(capture_device=camera_device)
                self.video_thread.frame_captured.connect(
                    self.video_window.display_frame)
                self.video_thread.start()
            self.video_window.show()
        else:
            self.untoggle_video_stream()

    def untoggle_video_stream(self) -> None:
        self.setText('Test Video')
        self.setChecked(False)
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        self.video_window.close()
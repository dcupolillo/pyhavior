""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

import sys
import cv2
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout
from pyhavior.gui.frames import InfoDisplayFrame, SettingsFrame, SaveFrame, RecordFrame
try:
    if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except Exception:
    pass


class Main(QMainWindow):
    """Main window of the behavior-controlling interface."""

    def __init__(self) -> None:
        """
        Class representing the main window of the
        behavior-controlling interface.

        Lays out the main frames with additional functionalities.

        Returns
        -------
        None

        """
        super().__init__()
        self.init_window()
        self.init_frames()

    def init_window(self) -> None:

        self.setGeometry(100, 100, 700, 400)  # Made window wider
        self.setWindowTitle('Pyhavior')
        self.setWindowIcon(QIcon('..\\pyhavior_icon.png'))

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QGridLayout(self.main_widget)

    def init_frames(self) -> None:

        # Create info display frame first
        self.info_display_frame = InfoDisplayFrame()
        
        self.settings_frame = SettingsFrame(None)  # Will connect later
        self.layout.addWidget(self.settings_frame, 0, 0)
        
        # Add info display frame below buttons, above save frame
        self.layout.addWidget(self.info_display_frame, 1, 0)
        
        self.save_frame = SaveFrame()
        self.layout.addWidget(self.save_frame, 2, 0)

        self.record_frame = RecordFrame(self.save_frame, self.info_display_frame)
        self.layout.addWidget(self.record_frame, 3, 0, 1, 1)
        
        # Connect settings frame to record frame after creation
        self.settings_frame.record_frame = self.record_frame

    def closeEvent(
            self,
            event: QtGui.QCloseEvent
    ) -> None:
        """
        Handles the closing event of the main window.
        """
        if self.record_frame.is_recording:
            self.record_frame.stop_recording()
            event.accept()
        else:
            event.accept()


def run_app():
    """Run the Pyhavior application."""
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()

    app.setQuitOnLastWindowClosed(True)

    pyhavior_window = Main()
    pyhavior_window.show()

    if not QtWidgets.QApplication.instance():
        sys.exit(app.exec_())
    else:
        app.exec_()
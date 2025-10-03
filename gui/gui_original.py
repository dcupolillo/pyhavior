""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

import sys
from pathlib import Path
import json
import time
from datetime import date
import serial
import cv2
import serial.tools.list_ports
import numpy as np
from PyQt5 import QtGui
from PyQt5.QtGui import QIcon, QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QMainWindow,
    QGridLayout, QFrame, QLabel, QLineEdit,
    QPushButton,  QFileDialog, QComboBox,
    QDialog, QDateEdit, QMessageBox)
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QDate, Qt

import pyhavior.core.protocols as prt
from pyhavior.core.threads import VideoThread, SerialThread, RecordingVideoThread
import pyhavior.gui.info
from pyhavior.gui.simple_protocol_visualizer import SimpleProtocolVisualizerWindow
from pyhavior.gui.dialogs import EnterInfoDialog, EnterCOMDialog, KeyActionDialog
from pyhavior.gui.windows import VideoWindow, RecordingWindow
from pyhavior.gui.frames import InfoDisplayFrame, SettingsFrame, SaveFrame, RecordFrame
from pyhavior.gui.buttons import FillTubesButton, TestDOButton, TestAIButton, TestVideoButton
try:
    if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except Exception:
    pass


# Backward compatibility aliases
enterInfo = EnterInfoDialog


enterCOM = EnterCOMDialog


class FillTubesButton(QPushButton):

    def __init__(
            self,
            default_com_port: str = 'COM4'
    ) -> None:
        """
         Define functionalities for the button to start the peristaltic pump
         at the press of a keyboard button.

        Parameters
        ----------
        default_com_port : str, optional
            The default is 'COM4'.

        Returns
        -------
        None

        """

        super().__init__('Start Filling Tubes')

        self.com_port = default_com_port
        self.ser = None

        com_dialog = enterCOM()
        com_dialog.com_port.connect(self.handle_com_port)

        self.setCheckable(True)
        self.clicked.connect(self.toggle_pump)

        self.pump_thread = None

    def toggle_pump(
            self
    ) -> None:

        if self.isChecked():
            self.setText('Press to Stop')
            if not self.pump_thread or not self.pump_thread.isRunning():
                self.pump_thread = SerialThread(
                    self.com_port,
                    prt.FillTubes())
                self.pump_thread.start()

        else:
            self.untoggle_pump()

    def untoggle_pump(self):

        if self.pump_thread:
            self.pump_thread.stop()
            self.setText('Start Filling Tubes')
            self.setChecked(False)

    def handle_com_port(
            self,
            com_port: str
    ) -> None:

        if not com_port == self.com_port:
            self.com_port = com_port


class TestDO(QPushButton):

    def __init__(
            self,
            default_com_port: str = 'COM4'
    ) -> None:
        """
         Define functionalities for the button to start the peristaltic pump
         at the press of a keyboard button.

        Parameters
        ----------
        default_com_port : str, optional
            The default is 'COM4'.

        Returns
        -------
        None

        """

        super().__init__('Test Digital Outputs')
        self.com_port = default_com_port
        self.ser = None

        com_dialog = enterCOM()
        com_dialog.com_port.connect(self.handle_com_port)

        self.dialog = None

        self.setCheckable(True)
        self.clicked.connect(self.toggle_DO)

        self.DO_thread = False

    def toggle_DO(
            self
    ) -> None:

        if self.isChecked():
            self.setText('Press to Stop')
            if not self.DO_thread or not self.DO_thread.isRunning():
                self.DO_thread = SerialThread(
                    self.com_port,
                    prt.TestDigitalOutput())
                self.DO_thread.start()
                self.show_key_actions_dialog()

        else:
            self.untoggle_DO()

    def untoggle_DO(self):

        if self.DO_thread:
            self.DO_thread.stop()
            self.setText('Test Digital Outputs')
            self.setChecked(False)

            self.close_key_action_dialog()

    def handle_com_port(
            self,
            com_port: str
    ) -> None:

        if not com_port == self.com_port:
            self.com_port = com_port

    def show_key_actions_dialog(self):

        protocol = prt.TestDigitalOutput()
        key_commands = protocol.__dict__['keys']

        self.dialog = KeyActionDialog(key_commands, self)
        self.dialog.show()

    def close_key_action_dialog(self):

        if self.dialog:
            self.dialog.close()


class KeyActionDialog(QDialog):

    def __init__(
            self,
            key_commands,
            parent: QWidget=None
    ) -> None:

        super().__init__(parent)
        self.setWindowTitle("Key Actions")
        self.layout = QGridLayout(self)
        self.resize(300, 300)
        self.parent = parent

        font_bold = QFont()
        font_bold.setBold(True)

        for attr, key in sorted(key_commands.__dict__.items()):
            action_name = attr.replace('_', ' ').capitalize()
            label_text = f"<b>{key.upper()}</b>: {action_name}"
            label = QLabel(label_text)
            self.layout.addWidget(label)

    def closeEvent(
            self,
            event: QtGui.QCloseEvent 
    ) -> None:
        """Handle the dialog close event and untoggle the parent TestDO button."""
        if self.parent and hasattr(self.parent, 'untoggle_DO'):
            self.parent.untoggle_DO()
        event.accept()


class TestAI(QPushButton):

    def __init__(
            self,
            default_com_port: str = 'COM4'
    ) -> None:
        """
         Define functionalities for the button to start the peristaltic pump
         at the press of a keyboard button.

        Parameters
        ----------
        default_com_port : str, optional
            The default is 'COM4'.

        Returns
        -------
        None

        """

        super().__init__('Test Analog Inputs')
        self.com_port = default_com_port
        self.ser = None

        com_dialog = enterCOM()
        com_dialog.com_port.connect(self.handle_com_port)

        self.setCheckable(True)
        self.clicked.connect(self.toggle_AI)

    def toggle_AI(
            self
    ) -> None:

        if self.isChecked():
            self.setText('Press to Stop')
            self.AI_thread = SerialThread(
                self.com_port,
                prt.TestAnalog())
            self.AI_thread.start()

        else:
            self.untoggle_AI()

    def untoggle_AI(self):

        if self.AI_thread:
            self.AI_thread.stop()
            self.setText('Test Analog Inputs')
            self.setChecked(False)

    def handle_com_port(
            self,
            com_port: str
    ) -> None:

        if not com_port == self.com_port:
            self.com_port = com_port


class VideoWindow(QWidget):

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

    def display_frame(
            self,
            frame: np.ndarray
    ) -> None:
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

    def closeEvent(
            self,
            event: QtGui.QCloseEvent
    ) -> None:
        """Handle video window close event"""
        if hasattr(self, 'video_thread'):
            self.video_thread.stop()
        self.video_window_closed.emit()
        event.accept()


class RecordingWindow(QWidget):
    """Recording preview window using PyQt display"""

    recording_window_closed = pyqtSignal()

    def __init__(
            self,
            mouse_id: str = "",
            experiment: str = ""
    ) -> None:

        super().__init__()

        self.setWindowTitle(f"Recording: {mouse_id} - {experiment}")
        self.setGeometry(100, 100, 1280, 960)

        self.layout = QGridLayout()

        self.video_label = QLabel('Starting recording...')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.video_label, 0, 0)

        self.setLayout(self.layout)

    def display_frame(
            self,
            frame: np.ndarray
    ) -> None:
        """Display video frame in the recording window"""
        
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

    def closeEvent(
            self,
            event: QtGui.QCloseEvent
    ) -> None:
        """Handle recording window close event"""
        self.recording_window_closed.emit()
        event.accept()


class TestVideo(QPushButton):

    def __init__(
            self,
            parent: QWidget = None
    ) -> None:
        """
         Define functionalities for the button to start video.
        """

        super().__init__('Preview Video')

        self.setCheckable(True)
        self.clicked.connect(self.toggle_video_stream)
        self.video_window = VideoWindow()
        self.video_thread = None

        self.video_window.video_window_closed.connect(
            self.untoggle_video_stream)

    def toggle_video_stream(self) -> None:

        if self.isChecked():
            self.setText('Quit')
            if not self.video_thread:
                self.video_thread = VideoThread()
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


class InfoDisplayFrame(QFrame):
    """Frame to display mouse information and video metadata"""
    
    def __init__(self) -> None:
        super().__init__()
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        
        self.init_display()
        
    def init_display(self) -> None:
        """Initialize the display labels with single column layout"""
        
        # Set column stretch to center the single column
        self.layout.setColumnStretch(0, 1)  # Left spacer
        self.layout.setColumnStretch(1, 0)  # Label column
        self.layout.setColumnStretch(2, 0)  # Field column
        self.layout.setColumnStretch(3, 1)  # Right spacer
        
        # Title
        title = QLabel('Current Session Info')
        title.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(title, 0, 0, 1, 4)
        
        row = 1
        
        # Mouse info line edits (read-only)
        self.mouse_id_edit = QLineEdit('Not set')
        self.mouse_id_edit.setReadOnly(True)
        self.mouse_id_edit.setMinimumWidth(200)
        
        self.genotype_edit = QLineEdit('Not set')
        self.genotype_edit.setReadOnly(True)
        self.genotype_edit.setMinimumWidth(200)
        
        self.dob_edit = QLineEdit('Not set')
        self.dob_edit.setReadOnly(True)
        self.dob_edit.setMinimumWidth(200)
        
        self.experiment_edit = QLineEdit('Not set')
        self.experiment_edit.setReadOnly(True)
        self.experiment_edit.setMinimumWidth(200)
        
        self.treatment_edit = QLineEdit('Not set')
        self.treatment_edit.setReadOnly(True)
        self.treatment_edit.setMinimumWidth(200)
        
        # Single column layout for mouse info
        self.layout.addWidget(QLabel('Mouse ID:'), row, 1)
        self.layout.addWidget(self.mouse_id_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Genotype:'), row, 1)
        self.layout.addWidget(self.genotype_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Date of birth:'), row, 1)
        self.layout.addWidget(self.dob_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Experiment:'), row, 1)
        self.layout.addWidget(self.experiment_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Treatment:'), row, 1)
        self.layout.addWidget(self.treatment_edit, row, 2)
        row += 2  # Extra space before video section
        
        # Video metadata line edits (read-only)
        self.video_path_edit = QLineEdit('Not recording')
        self.video_path_edit.setReadOnly(True)
        self.video_path_edit.setMinimumWidth(200)
        
        self.video_fps_edit = QLineEdit('--')
        self.video_fps_edit.setReadOnly(True)
        self.video_fps_edit.setMinimumWidth(200)
        
        self.video_resolution_edit = QLineEdit('--')
        self.video_resolution_edit.setReadOnly(True)
        self.video_resolution_edit.setMinimumWidth(200)
        
        # Single column layout for video info
        self.layout.addWidget(QLabel('Video file:'), row, 1)
        self.layout.addWidget(self.video_path_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('FPS:'), row, 1)
        self.layout.addWidget(self.video_fps_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Resolution:'), row, 1)
        self.layout.addWidget(self.video_resolution_edit, row, 2)
        
    def update_mouse_info(self, data: dict) -> None:
        """Update the displayed mouse information"""
        self.mouse_id_edit.setText(data.get('Mouse ID', 'Not set'))
        self.genotype_edit.setText(data.get('Genotype', 'Not set'))
        self.dob_edit.setText(data.get('Date of birth', 'Not set'))
        self.experiment_edit.setText(data.get('Behavior test', 'Not set'))
        self.treatment_edit.setText(data.get('Treatment', 'Not set'))
        
    def update_video_metadata(self, metadata: dict) -> None:
        """Update the displayed video metadata during recording"""
        video_path = metadata.get('video_path', 'Unknown')
        if video_path != 'Unknown':
            filename = Path(video_path).name
            self.video_path_edit.setText(filename)
        else:
            self.video_path_edit.setText(video_path)
            
        fps = metadata.get('fps', '--')
        self.video_fps_edit.setText(str(fps))
        
        width = metadata.get('frame_width', '--')
        height = metadata.get('frame_height', '--')
        self.video_resolution_edit.setText(f"{width}x{height}")
        
    def clear_video_metadata(self) -> None:
        """Clear video metadata when recording stops"""
        self.video_path_edit.setText('Not recording')
        self.video_fps_edit.setText('--')
        self.video_resolution_edit.setText('--')


class Main(QMainWindow):

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

    def init_window(
            self
    ) -> None:

        self.setGeometry(100, 100, 700, 400)  # Made window wider
        self.setWindowTitle('Pyhavior')
        self.setWindowIcon(QIcon('..\\pyhavior_icon.png'))

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QGridLayout(self.main_widget)

    def init_frames(
            self
    ) -> None:

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


class SettingsFrame(QFrame):

    def __init__(
            self,
            record_frame: QFrame
    ) -> None:
        """
        Class representing the mouse information entries.
        """

        super().__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.init_attributes()
        self.init_entries()

        self.record_frame = record_frame

    def init_attributes(self) -> None:

        self.all_entries_filled = False

    def init_entries(self) -> None:

        settings_title = QLabel('Set up')
        settings_title.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(settings_title, 0, 0, 1, 3)

        button_size = (160, 40)  # Made buttons wider

        self.setting_button = QPushButton('Enter info')
        self.setting_button.setFixedSize(*button_size)
        self.setting_button.clicked.connect(self.set_info)
        self.layout.addWidget(self.setting_button, 1, 0)

        self.com_button = QPushButton('COM ports')
        self.com_button.setFixedSize(*button_size)
        self.com_button.clicked.connect(self.set_com)
        self.layout.addWidget(self.com_button, 1, 1)

        self.fill_tubes_button = FillTubesButton()
        self.fill_tubes_button.setFixedSize(*button_size)
        self.layout.addWidget(self.fill_tubes_button, 1, 2)

        self.check_video_button = TestVideo()
        self.check_video_button.setFixedSize(*button_size)
        self.layout.addWidget(self.check_video_button, 2, 0)

        self.test_digital_outputs_button = TestDO()
        self.test_digital_outputs_button.setFixedSize(*button_size)
        self.layout.addWidget(self.test_digital_outputs_button, 2, 1)

        self.test_analog_inputs_button = TestAI()
        self.test_analog_inputs_button.setFixedSize(*button_size)
        self.layout.addWidget(self.test_analog_inputs_button, 2, 2)

        self.protocol_visualizer_button = QPushButton('Protocol Visualizer')
        self.protocol_visualizer_button.setFixedSize(*button_size)
        self.protocol_visualizer_button.clicked.connect(self.open_protocol_visualizer)
        self.layout.addWidget(self.protocol_visualizer_button, 3, 0)

    def set_info(self) -> None: 

        info_dialog = enterInfo()
        info_dialog.info_entered.connect(self.record_frame.handle_info)
        info_dialog.exec_()

    def set_com(self) -> None:

        com_dialog = enterCOM()
        com_dialog.com_port.connect(
            self.record_frame.handle_com_port)
        com_dialog.exec_()

    def open_protocol_visualizer(self) -> None:
        """Open the protocol visualizer window"""
        print("Protocol visualizer button clicked!")  # Debug
        try:
            print("Creating SimpleProtocolVisualizerWindow...")  # Debug
            # Create and show the simple protocol visualizer window
            self.visualizer_window = SimpleProtocolVisualizerWindow(self)
            print("Showing window...")  # Debug
            self.visualizer_window.show()
            self.visualizer_window.raise_()  # Bring to front
            self.visualizer_window.activateWindow()  # Activate window
            print("Simple Protocol Visualizer should be visible now!")  # Debug
        except Exception as e:
            print(f"Error occurred: {e}")  # Debug
            import traceback
            traceback.print_exc()  # Full error trace
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to open Protocol Visualizer: {str(e)}"
            )


class SaveFrame(QFrame):

    dest_folder = pyqtSignal(str)

    def __init__(self) -> None:

        super().__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.init_entries()

    def init_entries(
            self
    ) -> None:

        title = QLabel('Save to')
        title.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(title, 0, 0, 1, 3)

        save_label = QLabel('Dest. folder: ')
        save_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(save_label, 1, 0, 1, 1)

        self.folder = QLineEdit()
        self.layout.addWidget(self.folder, 1, 1, 1, 1)

        self.choose_button = QPushButton('Choose')
        self.choose_button.setFixedSize(100, 30)
        self.choose_button.clicked.connect(self.choose_folder)
        self.layout.addWidget(self.choose_button, 1, 2, 1, 1)

    def choose_folder(self) -> None:

        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder")

        if folder_path:
            self.folder.setText(folder_path)
            self.dest_folder.emit(folder_path)
            print(f"Saving in: {folder_path}")


class RecordFrame(QFrame):

    # Ensure UI updates from worker threads are marshaled to the GUI thread
    stop_enabled = pyqtSignal(bool)
    show_error = pyqtSignal(str, str)

    def __init__(
            self,
            save_frame: QFrame,
            info_display_frame: QFrame = None,
            default_com_port: str = 'COM4'
    ) -> None:
        """
        Frame with functionalities for saving and recording.

        Parameters
        ----------
        save_frame : QFrame
            Another frame of the GUI.
        default_com_port : str, optional
            DESCRIPTION. The default is 'COM4'.

        Returns
        -------
        None

        """

        super().__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.init_buttons()
        self.init_attributes()

        self.com_port = default_com_port

        self.experiment_classes = {
            name: getattr(prt, name)
            for name in prt.__all__
        }

        info_dialog = enterInfo()
        info_dialog.info_entered.connect(self.handle_info)
        
        com_dialog = enterCOM()
        com_dialog.com_port.connect(self.handle_com_port)
        
        save_frame.dest_folder.connect(self.handle_dest_folder)

        self.is_recording = False
        self.recording_thread = None
        self.serial_thread = None
        self.recording_window = None
        
        # Initialize recording metadata attributes
        self.fps = 30
        self.frame_width = 640
        self.frame_height = 480
        self.video_path = None
        
        # Store reference to info display frame
        self.info_display_frame = info_display_frame
        
        # Connect stop_enabled signal to update UI
        self.stop_enabled.connect(self.stop_button.setEnabled)
        self.show_error.connect(self.display_error_message)

    def init_attributes(self) -> None:

        self.dest_folder_received = False
        self.info_entered_received = False

    def init_buttons(self) -> None:

        title = QLabel('Record')
        title.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(title, 0, 0, 1, 2)

        self.record_button = QPushButton('Record')
        self.record_button.clicked.connect(self.start_recording)
        self.record_button.setEnabled(False)
        self.layout.addWidget(self.record_button, 1, 0, 1, 1)

        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        self.layout.addWidget(self.stop_button, 1, 1, 1, 1)

    def handle_dest_folder(
            self,
            dest_folder: str
    ) -> None:

        self.dest_folder = dest_folder
        self.dest_folder_received = True
        self.check_all_signals_received()

    def handle_com_port(
            self,
            com_port: str
    ) -> None:

        if not com_port == self.com_port:
            self.com_port = com_port
        print(self.com_port)

    def handle_info(
            self,
            data: dict
    ) -> None:

        self.data = data
        self.info_entered_received = True
        
        # Update info display frame with mouse information
        if self.info_display_frame:
            self.info_display_frame.update_mouse_info(data)
        
        self.check_all_signals_received()

    def check_all_signals_received(self) -> None:

        if self.dest_folder_received and self.info_entered_received:
            self.record_button.setEnabled(True)

            self.folder_path = Path(self.dest_folder) / self.data['Mouse ID']

            self.folder_path.mkdir(parents=True, exist_ok=True)

            self.filename = (
                self.folder_path /
                f"{self.data['Mouse ID']}_"
                f"{self.data['Behavior test']}.avi")

            self.init_protocol()

    def init_protocol(
            self
    ) -> None:

        experiment = self.data['Behavior test']

        if experiment in self.experiment_classes:
            self.protocol = self.experiment_classes[experiment]()

        else:
            raise KeyError(
                f"Experiment {experiment} not recognized.")

    def display_error_message(
            self,
            title: str,
            message: str
     ) -> None:
        """Display error message in GUI thread"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()
        
    def on_recording_finished(self) -> None:
        """Handle recording completion"""
        self.is_recording = False
        self.record_button.setEnabled(True)  # Re-enable record button
        self.stop_enabled.emit(False)
        
        # Close recording window
        if self.recording_window:
            self.recording_window.close()
            self.recording_window = None
        
        # Clear video metadata from info display
        if self.info_display_frame:
            self.info_display_frame.clear_video_metadata()
        
        # Stop the serial thread if it's still running
        if self.serial_thread and self.serial_thread.isRunning():
            self.protocol.request_stop()
            self.serial_thread.stop()
            self.serial_thread.wait()  # Wait for thread to finish
            print("Serial thread stopped.")
        
        # Verify video file and save metadata
        if hasattr(self, 'video_start_time') and hasattr(self, 'serial_start_time'):
            self.save_data_to_json()
        
        # Check if video file was created successfully
        if self.video_path and Path(self.video_path).exists():
            file_size = Path(self.video_path).stat().st_size
            print(f"Video saved: {self.video_path} (Size: {file_size:,} bytes)")
            if file_size < 1000:  # Very small file might be corrupted
                print("Warning: Video file is very small and might be corrupted")
        else:
            print("Warning: Video file was not created or is missing")
        
        print(f"Recording finished at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    def on_recording_error(
            self,
            error_message: str
    ) -> None:
        """Handle recording errors"""
        print(f"Recording error: {error_message}")
        self.record_button.setEnabled(True)  # Re-enable record button on error
        self.show_error.emit("Recording Error", error_message)
        self.stop_recording()
        
    def on_recording_metadata(
            self,
            metadata: dict
    ) -> None:
        """Handle recording metadata from RecordingVideoThread"""
        self.video_path = metadata.get('video_path')
        self.fps = metadata.get('fps', 30)
        self.frame_width = metadata.get('frame_width', 640)
        self.frame_height = metadata.get('frame_height', 480)
        
        # Print metadata properly
        print("Recording metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        # Update info display frame with video metadata
        if self.info_display_frame:
            self.info_display_frame.update_video_metadata(metadata)

    def start_recording(self) -> None:

        if not self.is_recording:
            
            # Record start times
            self.serial_start_time = time.time()
            self.video_start_time = time.time()
            
            ts_serial = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.serial_start_time))
            ts_video = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.video_start_time))
            print(f'Serial start: {ts_serial}')
            print(f'Video start: {ts_video}')
            
            # Start serial thread
            self.serial_thread = SerialThread(self.com_port, self.protocol)
            self.serial_thread.start()
            
            # Start recording thread
            self.recording_thread = RecordingVideoThread(
                str(self.filename),
                self.protocol.duration,
                self.data,
                capture_device=0,
                parent=self
            )
            
            # Create and show recording window
            self.recording_window = RecordingWindow(
                self.data['Mouse ID'], 
                self.data['Behavior test']
            )
            self.recording_window.show()
            
            # Connect signals
            self.recording_thread.recording_finished.connect(self.on_recording_finished)
            self.recording_thread.error_occurred.connect(self.on_recording_error)
            self.recording_thread.recording_metadata.connect(self.on_recording_metadata)
            self.recording_thread.frame_recorded.connect(self.recording_window.display_frame)
            self.recording_window.recording_window_closed.connect(self.stop_recording)
            
            self.is_recording = True
            self.record_button.setEnabled(False)  # Disable record button during recording
            self.stop_enabled.emit(True)
            self.recording_thread.start_recording()
            

            
        else:
            print("Recording is already in progress.")

    def stop_recording(self):

        if self.is_recording:

            response = QMessageBox.question(
                self,
                'Stop Recording',
                "Recording is in progress. Are you sure you want to stop?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if response == QMessageBox.Yes:

                # Stop threads properly to prevent file corruption
                if self.recording_thread:
                    print("Stopping recording thread...")
                    self.recording_thread.stop_recording()
                    # Wait for recording thread to finish before continuing
                    if not self.recording_thread.wait(10000):  # 10 second timeout
                        print("Warning: Recording thread did not stop in time")
                    
                if self.serial_thread:
                    print("Stopping serial thread...")
                    self.protocol.request_stop()
                    self.serial_thread.stop()
                    
                self.is_recording = False
                self.record_button.setEnabled(True)  # Re-enable record button
                self.stop_enabled.emit(False)
                
                # Save metadata after ensuring threads have stopped
                if hasattr(self, 'video_start_time') and hasattr(self, 'serial_start_time'):
                    self.save_data_to_json()
                
                print("Recording stopped successfully.")

            else:
                print("Recording continues.")



    def save_data_to_json(self) -> None:
        """
        Save metadata to a .json file according to predefined formatting.
        """

        filename_path = Path(self.filename)
        base_name = filename_path.stem.split('_')[0]
        json_file_path = (
            filename_path.with_name(base_name).with_suffix('.json'))

        # Use the actual video path from the recording thread if available
        if self.video_path:
            video_file_resolved = str(Path(self.video_path).resolve())
        else:
            # Fallback to constructed path
            base = Path(self.filename)
            ts = time.strftime('%H%M%S', time.localtime(self.video_start_time))
            video_file_resolved = str(base.with_name(f"{base.stem}_{ts}.avi").resolve())

        experiment_data = {
            'Type': self.data['Behavior test'],
            'Date': date.today().strftime("%Y-%m-%d"),
            'Treatment': self.data['Treatment'],
            'Video Start Time': self.video_start_time,
            'Serial Start Time': self.serial_start_time,
            'Video File': video_file_resolved,
            'Camera FPS': self.fps,
            'Frame Width': self.frame_width,
            'Frame Height': self.frame_height,
            'com Port': self.com_port,
            'camera_index': 0,            
        }

        if json_file_path.exists():
            with json_file_path.open('r') as jsonFile:
                json_data = json.load(jsonFile)

            # Ensure 'Behavior test' is a list and append the new run
            if 'Behavior test' in json_data:
                if isinstance(json_data['Behavior test'], dict):
                    json_data['Behavior test'] = [json_data['Behavior test']]
                
                json_data['Behavior test'].append(experiment_data)
            
            else:
                json_data['Behavior test'] = [experiment_data]
        
        else:
            json_data = {
                'Mouse ID': self.data['Mouse ID'],
                'Genotype': self.data['Genotype'],
                'Date of Birth': self.data['Date of birth'],
                'Weight': None,
                'Behavior test': [experiment_data]
            }

        with json_file_path.open('w') as jsonFile:
            json.dump(json_data, jsonFile, indent=4)

    def get_date(self) -> str:
        """
        Returns the current date formatted as a string in "YYMMDD" format.
        """

        return date.today().strftime("%y%m%d")


def run_app():
    
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
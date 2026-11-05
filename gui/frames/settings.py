""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5 import QtCore
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QMessageBox

from pyhavior.gui.dialogs import EnterInfoDialog, EnterCOMDialog, SelectCameraDialog
from pyhavior.gui.buttons import FillTubesButton, TestDOButton, TestAIButton, TestVideoButton
from pyhavior.gui.windows import ProtocolVisualizerWindow


class SettingsFrame(QFrame):
    """Frame containing setup buttons and controls."""

    def __init__(self, record_frame: QFrame) -> None:
        super().__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.init_attributes()
        self.init_entries()

        self.record_frame = record_frame

    @property
    def record_frame(self) -> QFrame:
        return self._record_frame

    @record_frame.setter
    def record_frame(self, frame: QFrame) -> None:
        """The record frame is attached after construction (see gui.py)."""

        self._record_frame = frame
        if frame is not None:
            frame.session_active.connect(self.set_session_active)
            frame.hardware_busy = self.busy_reason

    def _session_buttons(self) -> list:
        """Buttons that must not be used while a session owns the devices."""

        return [
            self.setting_button,
            self.com_button,
            self.camera_button,
            self.check_video_button,
            self.fill_tubes_button,
            self.test_digital_outputs_button,
            self.test_analog_inputs_button,
        ]

    def set_session_active(self, active: bool) -> None:
        for button in self._session_buttons():
            button.setEnabled(not active)

    @staticmethod
    def _is_running(thread) -> bool:
        return bool(thread) and thread.isRunning()

    def preview_active(self) -> bool:
        return self._is_running(self.check_video_button.video_thread)

    def busy_reason(self):
        """Why a recording cannot start right now, or None if it can."""

        if self.preview_active() and self.record_frame.camera_device is not None:
            return "The camera preview is open. Close it before recording."

        bench_tools = (
            (self.fill_tubes_button, 'pump_thread', 'Fill tubes'),
            (self.test_digital_outputs_button, 'DO_thread', 'The digital output test'),
            (self.test_analog_inputs_button, 'AI_thread', 'The analog input test'))

        for button, attribute, name in bench_tools:
            if self._is_running(getattr(button, attribute, None)):
                return f"{name} is running and holds the Arduino. Stop it first."

        return None

    def init_attributes(self) -> None:
        self.all_entries_filled = False

    def init_entries(self) -> None:

        settings_title = QLabel('Set up')
        settings_title.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(settings_title, 0, 0, 1, 4)

        button_size = (160, 40)  # Made buttons wider

        self.setting_button = QPushButton('Enter info')
        self.setting_button.setFixedSize(*button_size)
        self.setting_button.clicked.connect(self.set_info)
        self.layout.addWidget(self.setting_button, 1, 0)

        self.com_button = QPushButton('COM ports')
        self.com_button.setFixedSize(*button_size)
        self.com_button.clicked.connect(self.set_com)
        self.layout.addWidget(self.com_button, 1, 1)

        self.camera_button = QPushButton('Select Camera')
        self.camera_button.setFixedSize(*button_size)
        self.camera_button.clicked.connect(self.select_camera)
        self.layout.addWidget(self.camera_button, 1, 2)

        self.check_video_button = TestVideoButton(
            get_camera_device=lambda: self.record_frame.camera_device)
        self.check_video_button.setFixedSize(*button_size)
        self.layout.addWidget(self.check_video_button, 1, 3)

        self.fill_tubes_button = FillTubesButton()
        self.fill_tubes_button.setFixedSize(*button_size)
        self.layout.addWidget(self.fill_tubes_button, 2, 0)

        self.test_digital_outputs_button = TestDOButton()
        self.test_digital_outputs_button.setFixedSize(*button_size)
        self.layout.addWidget(self.test_digital_outputs_button, 2, 1)

        self.test_analog_inputs_button = TestAIButton()
        self.test_analog_inputs_button.setFixedSize(*button_size)
        self.layout.addWidget(self.test_analog_inputs_button, 2, 2)

        self.protocol_visualizer_button = QPushButton('Protocol Visualizer')
        self.protocol_visualizer_button.setFixedSize(*button_size)
        self.protocol_visualizer_button.clicked.connect(self.open_protocol_visualizer)
        self.layout.addWidget(self.protocol_visualizer_button, 2, 3)

    def set_info(self) -> None:
        info_dialog = EnterInfoDialog()
        info_dialog.info_entered.connect(self.record_frame.handle_info)
        info_dialog.exec_()

    def set_com(self) -> None:
        com_dialog = EnterCOMDialog(allow_none=True)
        com_dialog.com_port.connect(
            self.record_frame.handle_com_port)
        com_dialog.arduino_disabled.connect(
            self.record_frame.handle_no_arduino)
        com_dialog.exec_()

    def select_camera(self) -> None:
        if self.preview_active():
            QMessageBox.information(
                self,
                'Camera in use',
                'Close the video preview before changing the camera.')
            return

        camera_dialog = SelectCameraDialog()
        camera_dialog.camera_selected.connect(
            self.record_frame.handle_camera_selection)
        camera_dialog.camera_disabled.connect(
            self.record_frame.handle_no_camera)
        camera_dialog.exec_()

    def open_protocol_visualizer(self) -> None:
        """Open the protocol visualizer window"""

        try:
            self.visualizer_window = ProtocolVisualizerWindow()
            self.visualizer_window.show()
            self.visualizer_window.raise_()  # Bring to front
            self.visualizer_window.activateWindow()  # Activate window
        
        except Exception as e:
            import traceback
            traceback.print_exc()  # Full error trace
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to open Protocol Visualizer: {str(e)}"
            )
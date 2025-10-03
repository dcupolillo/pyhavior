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
        com_dialog = EnterCOMDialog()
        com_dialog.com_port.connect(
            self.record_frame.handle_com_port)
        com_dialog.exec_()

    def select_camera(self) -> None:
        camera_dialog = SelectCameraDialog()
        camera_dialog.camera_selected.connect(
            self.record_frame.handle_camera_selection)
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
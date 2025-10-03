""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5.QtWidgets import QPushButton

from pyhavior.core.test_utils import TestDigitalOutput
from pyhavior.core.threads import SerialThread
from pyhavior.gui.dialogs import EnterCOMDialog, KeyActionDialog


class TestDOButton(QPushButton):
    """Button to test digital outputs with keyboard control."""

    def __init__(self, default_com_port: str = 'COM4') -> None:
        super().__init__('Test Digital Outputs')
        self.com_port = default_com_port
        self.ser = None

        com_dialog = EnterCOMDialog()
        com_dialog.com_port.connect(self.handle_com_port)

        self.dialog = None

        self.setCheckable(True)
        self.clicked.connect(self.toggle_DO)

        self.DO_thread = False

    def toggle_DO(self) -> None:
        if self.isChecked():
            self.setText('Press to Stop')
            if not self.DO_thread or not self.DO_thread.isRunning():
                self.DO_thread = SerialThread(
                    self.com_port,
                    TestDigitalOutput())
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

    def handle_com_port(self, com_port: str) -> None:
        if not com_port == self.com_port:
            self.com_port = com_port

    def show_key_actions_dialog(self):
        protocol = TestDigitalOutput()
        key_commands = protocol.__dict__['keys']

        self.dialog = KeyActionDialog(key_commands, self)
        self.dialog.show()

    def close_key_action_dialog(self):
        if self.dialog:
            self.dialog.close()
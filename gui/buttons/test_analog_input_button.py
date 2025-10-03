""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5.QtWidgets import QPushButton

from pyhavior.core.test_utils import TestAnalog
from pyhavior.core.threads import SerialThread
from pyhavior.gui.dialogs import EnterCOMDialog


class TestAIButton(QPushButton):
    """Button to test analog inputs."""

    def __init__(self, default_com_port: str = 'COM4') -> None:
        super().__init__('Test Analog Inputs')
        self.com_port = default_com_port
        self.ser = None

        com_dialog = EnterCOMDialog()
        com_dialog.com_port.connect(self.handle_com_port)

        self.setCheckable(True)
        self.clicked.connect(self.toggle_AI)

    def toggle_AI(self) -> None:
        if self.isChecked():
            self.setText('Press to Stop')
            self.AI_thread = SerialThread(
                self.com_port,
                TestAnalog())
            self.AI_thread.start()
        else:
            self.untoggle_AI()

    def untoggle_AI(self):
        if self.AI_thread:
            self.AI_thread.stop()
            self.setText('Test Analog Inputs')
            self.setChecked(False)

    def handle_com_port(self, com_port: str) -> None:
        if not com_port == self.com_port:
            self.com_port = com_port
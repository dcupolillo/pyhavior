""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5.QtWidgets import QPushButton

from pyhavior.core.test_utils import FillTubes
from pyhavior.core.threads import SerialThread
from pyhavior.gui.dialogs import EnterCOMDialog


class FillTubesButton(QPushButton):
    """Button to start the peristaltic pump at the press of a keyboard button."""

    def __init__(self, default_com_port: str = 'COM4') -> None:
        super().__init__('Start Filling Tubes')

        self.com_port = default_com_port
        self.ser = None

        com_dialog = EnterCOMDialog()
        com_dialog.com_port.connect(self.handle_com_port)

        self.setCheckable(True)
        self.clicked.connect(self.toggle_pump)

        self.pump_thread = None

    def toggle_pump(self) -> None:
        if self.isChecked():
            self.setText('Press to Stop')
            if not self.pump_thread or not self.pump_thread.isRunning():
                self.pump_thread = SerialThread(
                    self.com_port,
                    FillTubes())
                self.pump_thread.start()
        else:
            self.untoggle_pump()

    def untoggle_pump(self):
        if self.pump_thread:
            self.pump_thread.stop()
            self.setText('Start Filling Tubes')
            self.setChecked(False)

    def handle_com_port(self, com_port: str) -> None:
        if not com_port == self.com_port:
            self.com_port = com_port
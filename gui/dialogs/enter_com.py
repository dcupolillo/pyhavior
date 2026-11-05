""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

import serial.tools.list_ports
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QGridLayout, QLabel, QPushButton, QComboBox
)
from PyQt5.QtCore import pyqtSignal


class EnterCOMDialog(QDialog):
    """Dialog window to set the COM port for serial communication.
    
    Appears when clicking 'COM ports' button in Main window.
    """

    com_port = pyqtSignal(str)
    arduino_disabled = pyqtSignal()  # "No Arduino (dry run)" was chosen

    NO_ARDUINO_LABEL = 'None'

    def __init__(self, allow_none: bool = False) -> None:
        """
        Parameters
        ----------
        allow_none: bool
            Offer a "No Arduino" choice. Only meaningful for recording
            sessions: the bench tests need a real port.
        """
        super().__init__()

        self.setWindowTitle('COM ports')
        self.setWindowIcon(QIcon('..\\pyhavior_icon.png'))
        self.layout = QGridLayout(self)

        self.layout.addWidget(QLabel('COM port :'), 0, 0)

        self.com = QComboBox()

        default_index = 0

        for i, port in enumerate(serial.tools.list_ports.comports()):
            self.com.addItem(f"{port.device} - {port.description}", port.device)

            if "Arduino" in port.description:
                default_index = i

        if allow_none:
            self.com.addItem(self.NO_ARDUINO_LABEL, None)

        self.com.setCurrentIndex(default_index)

        self.layout.addWidget(self.com, 0, 1, 1, 2)

        self.ok_button = QPushButton('Ok')
        self.ok_button.clicked.connect(self.getcom_port)
        self.ok_button.setEnabled(self.com.count() > 0)
        self.layout.addWidget(self.ok_button, 1, 1)

        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.accept)
        self.layout.addWidget(self.cancel_button, 1, 2, 1, 1)

    def getcom_port(self) -> None:
        """Get selected COM port and emit signal."""
        selected_port = self.com.currentData()
        if selected_port is None:
            self.arduino_disabled.emit()
        else:
            self.com_port.emit(selected_port)
        self.accept()
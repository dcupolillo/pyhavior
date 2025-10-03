""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5 import QtGui
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QWidget
from PyQt5.QtCore import Qt


class KeyActionDialog(QDialog):
    """Dialog showing key commands for test actions."""

    def __init__(self, key_commands, parent: QWidget = None) -> None:
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

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle the dialog close event and untoggle the parent TestDO button."""
        if self.parent and hasattr(self.parent, 'untoggle_DO'):
            self.parent.untoggle_DO()
        event.accept()
""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5 import QtCore
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt5.QtCore import pyqtSignal


class SaveFrame(QFrame):
    """Frame for selecting save destination folder."""

    dest_folder = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.init_entries()

    def init_entries(self) -> None:
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
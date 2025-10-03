""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, 
    QComboBox, QDateEdit
)
from PyQt5.QtCore import pyqtSignal, QDate

from pyhavior.core import AVAILABLE_PROTOCOLS
import pyhavior.gui.info


class EnterInfoDialog(QDialog):
    """Dialog window asking for mouse info.
    
    Appears when clicking 'Enter info' button in Main Window.
    """

    info_entered = pyqtSignal(dict)

    # Load available behavioral protocols from sequence files only
    experiment_list = AVAILABLE_PROTOCOLS
    info = pyhavior.gui.info.info
    genotype_list = pyhavior.gui.info.genotype_list
    treatment_list = pyhavior.gui.info.treatment_list

    data = {key: None for key in info}

    def __init__(self) -> None:
        
        super().__init__()

        self.setWindowTitle("Enter info")
        self.setWindowIcon(QIcon('..\\pyhavior_icon.png'))
        self.layout = QGridLayout(self)

        labels = [f'{i}: ' for i in self.info]

        for n, label in enumerate(labels):
            self.layout.addWidget(QLabel(label), n, 0, 1, 1)

        self.id = QLineEdit()
        self.id.setPlaceholderText('Enter mouse ID')
        self.id.textChanged.connect(self.validate_entries)
        self.layout.addWidget(self.id, 0, 1)

        self.genotype = QComboBox()
        self.genotype.addItems([gt for gt in self.genotype_list])
        self.genotype.currentTextChanged.connect(self.validate_entries)
        self.layout.addWidget(self.genotype, 1, 1)

        self.dob = QDateEdit()
        self.dob.setCalendarPopup(True)
        self.dob.setDate(QDate.currentDate())
        self.dob.dateChanged.connect(self.validate_entries)
        self.layout.addWidget(self.dob, 2, 1)

        self.experiment = QComboBox()
        self.experiment.addItems(
            [protocol for protocol in self.experiment_list])
        self.experiment.currentTextChanged.connect(self.validate_entries)
        self.layout.addWidget(self.experiment, 3, 1)

        self.treatment = QComboBox()
        self.treatment.addItems([tr for tr in self.treatment_list])
        self.treatment.currentTextChanged.connect(self.validate_entries)
        self.layout.addWidget(self.treatment, 4, 1)

        self.ok_button = QPushButton('Ok')
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.ok_pressed)
        self.layout.addWidget(self.ok_button, 5, 0)

        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.accept)
        self.layout.addWidget(self.cancel_button, 5, 1)

    def validate_entries(self) -> None:
        """Enables/disables the Ok button when all infos are filled."""
        
        all_fields_filled = all([
            self.id.text().strip(),
            self.genotype.currentText().strip(),
            self.dob.text().strip(),
            self.experiment.currentText().strip(),
            self.treatment.currentText().strip()
        ])

        self.ok_button.setEnabled(all_fields_filled)

    def ok_pressed(self) -> None:
        """Prepares the data to emit and closes the dialog."""
        data = {
            'Mouse ID': self.id.text(),
            'Genotype': self.genotype.currentText(),
            'Date of birth': self.dob.date().toString(),
            'Behavior test': self.experiment.currentText(),
            'Treatment': self.treatment.currentText()
        }

        # throw data in console
        for key, attr in data.items():
            print(f'{key}: {attr}')

        # Emit the signal with the data
        self.info_entered.emit(data)
        self.accept()
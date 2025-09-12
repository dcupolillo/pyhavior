""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

import sys
from pathlib import Path
import json
import time
from datetime import date
import serial
import threading
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
from pyhavior.core.threads import VideoThread, SerialThread
import pyhavior.gui.info


class enterInfo(QDialog):

    info_entered = pyqtSignal(dict)

    experiment_list = prt.__all__
    info = pyhavior.gui.info.info
    genotype_list = pyhavior.gui.info.genotype_list
    treatment_list = pyhavior.gui.info.treatment_list

    data = {key: None for key in info}

    def __init__(
            self
    ) -> None:
        """
        Dialog window asking for mouse info.
        Appears when clicking 'Enter infor' button in Main Window.
        """

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

    def validate_entries(
            self
    ) -> None:
        """
        Enables/disables the Ok button when all infos are filled.
        """

        all_fields_filled = all([self.id.text().strip(),
                                 self.genotype.currentText().strip(),
                                 self.dob.text().strip(),
                                 self.experiment.currentText().strip(),
                                 self.treatment.currentText().strip()
                                 ])

        self.ok_button.setEnabled(all_fields_filled)

    def ok_pressed(
            self
    ) -> None:
        """
        Prepares the data to emit amd closes the dialog.
        """

        data = {'Mouse ID': self.id.text(),
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


class enterCOM(QDialog):

    com_port = pyqtSignal(str)

    def __init__(
            self
    ) -> None:
        """
        Dialog window to set the COM port for serial communication.
        Appears when clicking 'COM ports' button in Main window.
        """

        super().__init__()

        self.setWindowTitle('COM ports')
        self.setWindowIcon(QIcon('..\\pyhavior_icon.png'))
        self.layout = QGridLayout(self)

        self.layout.addWidget(QLabel('COM port :'), 0, 0)

        self.com = QComboBox()

        default_index = 0

        for i, port in enumerate(serial.tools.list_ports.comports()):
            self.com.addItem(f"{port.device} - {port.description}")

            if "Arduino" in port.description:
                default_index = i

        self.com.setCurrentIndex(default_index)

        self.layout.addWidget(self.com, 0, 1, 1, 2)

        self.ok_button = QPushButton('Ok')
        self.ok_button.clicked.connect(self.getcom_port)
        self.layout.addWidget(self.ok_button, 1, 1)

        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.accept)
        self.layout.addWidget(self.cancel_button, 1, 2, 1, 1)

    def getcom_port(
            self
    ) -> None:

        selected_port = self.com.currentText().split(' - ')[0]
        self.com_port.emit(selected_port)
        self.accept()


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
            parent=None
    ) -> None:

        super().__init__(parent)
        self.setWindowTitle("Key Actions")
        self.layout = QGridLayout(self)
        self.resize(300, 300)

        font_bold = QFont()
        font_bold.setBold(True)

        for attr, key in sorted(key_commands.__dict__.items()):
            action_name = attr.replace('_', ' ').capitalize()
            label_text = f"<b>{key.upper()}</b>: {action_name}"
            label = QLabel(label_text)
            self.layout.addWidget(label)


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

    def __init__(
            self
    ) -> None:

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

        frame = cv2.flip(frame, 1)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_image.shape
        bytes_per_line = width * channel

        convert_to_Qt_format = QImage(
            frame.data,
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
            event
    ) -> None:

        if hasattr(self, 'video_thread'):
            self.video_thread.stop()
        self.video_window_closed.emit()
        event.accept()


class TestVideo(QPushButton):

    def __init__(
            self,
            parent=None
    ) -> None:
        """
         Define functionalities for the button to start video.
        """

        super().__init__('Test Video')

        self.setCheckable(True)
        self.clicked.connect(self.toggle_video_stream)
        self.video_window = VideoWindow()
        self.video_thread = None

        self.video_window.video_window_closed.connect(
            self.untoggle_video_stream)

    def toggle_video_stream(
            self
    ) -> None:

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

    def untoggle_video_stream(
            self
    ) -> None:

        self.setText('Test Video')
        self.setChecked(False)
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        self.video_window.close()


class Main(QMainWindow):

    def __init__(
            self
    ) -> None:
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

        # self.setGeometry(100, 100, 600, 300)
        self.setWindowTitle('Pyhavior')
        self.setWindowIcon(QIcon('..\\pyhavior_icon.png'))

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QGridLayout(self.main_widget)

    def init_frames(
            self
    ) -> None:

        self.save_frame = SaveFrame()
        self.layout.addWidget(self.save_frame, 1, 0)

        self.record_frame = RecordFrame(self.save_frame)
        self.layout.addWidget(self.record_frame, 2, 0, 1, 1)

        self.settings_frame = SettingsFrame(self.record_frame)
        self.layout.addWidget(self.settings_frame, 0, 0)

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

    def init_attributes(
            self
    ) -> None:

        self.all_entries_filled = False

    def init_entries(
            self
    ) -> None:

        settings_title = QLabel('Set up')
        settings_title.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(settings_title, 0, 0, 1, 3)

        button_size = (120, 40)

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

    def set_info(
            self
    ) -> None:

        info_dialog = enterInfo()
        info_dialog.info_entered.connect(self.record_frame.handle_info)
        info_dialog.exec_()

    def set_com(
            self
    ) -> None:

        com_dialog = enterCOM()
        com_dialog.com_port.connect(self.record_frame.handle_com_port)
        com_dialog.exec_()


class SaveFrame(QFrame):

    dest_folder = pyqtSignal(str)

    def __init__(
            self
    ) -> None:

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
        self.choose_button.clicked.connect(self.choose_folder)
        self.layout.addWidget(self.choose_button, 1, 2, 1, 1)

    def choose_folder(
            self
    ) -> None:

        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder")

        if folder_path:

            self.folder.setText(folder_path)
            self.dest_folder.emit(folder_path)
            print(f"Saving at: {folder_path}")


class RecordFrame(QFrame):

    def __init__(
            self,
            save_frame: QFrame,
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

        self.experiment_classes = {name: getattr(prt, name)
                                   for name in prt.__all__}

        info_dialog = enterInfo()
        info_dialog.info_entered.connect(self.handle_info)
        com_dialog = enterCOM()
        com_dialog.com_port.connect(self.handle_com_port)
        save_frame.dest_folder.connect(self.handle_dest_folder)

        self.is_recording = False
        self.stop_event = threading.Event()

    def init_attributes(
            self
    ) -> None:

        self.dest_folder_received = False
        self.info_entered_received = False

    def init_buttons(
            self
    ) -> None:

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
        self.check_all_signals_received()

    def check_all_signals_received(self) -> None:

        if self.dest_folder_received and self.info_entered_received:
            self.record_button.setEnabled(True)

            self.folder_path = Path(self.dest_folder) / self.data['Mouse ID']

            self.folder_path.mkdir(parents=True, exist_ok=True)

            self.filename = (self.folder_path /
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
            raise KeyError(f"Experiment {experiment} not recognized.")

    def send_serial_command(
            self,
            baudrate: int = 9600
    ) -> None:

        # Initialize serial communication
        self.ser = serial.Serial(self.com_port, baudrate)

        if not self.ser.is_open:
            self.ser.open()

        self.serial_start_time = time.time()
        print(f'serial Start: {self.serial_start_time:.3f}')
        self.protocol.run(self.ser)
        self.ser.close()

    def record_video(
            self
    ) -> None:

        self.stop_button.setEnabled(True)

        self.video_cap = cv2.VideoCapture(0)

        if not self.video_cap.isOpened():
            raise IOError("Cannot open webcam")

        self.frame_width = int(self.video_cap.get(3))
        self.frame_height = int(self.video_cap.get(4))
        self.fps = 30

        fourcc = cv2.VideoWriter_fourcc(*'XVID')

        self.video_writer = cv2.VideoWriter(
            str(self.filename),
            fourcc,
            self.fps,
            (self.frame_width,
             self.frame_height))

        cv2.namedWindow("Recording", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(
            "Recording", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(
            "Recording", cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_KEEPRATIO)
        cv2.setWindowProperty(
            "Recording", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

        # start a timer
        self.video_start_time = time.time()

        print(f'video Start: {self.video_start_time:.3f}')
        print('delay: '
              f'{np.abs(self.video_start_time - self.serial_start_time):.3f}')
        frame_number = 0
        flag_start = False

        while (not self.stop_event.is_set() and
               time.time() - self.video_start_time < self.protocol.duration):

            ret, frame = self.video_cap.read()

            if ret:

                # flip horizontally
                frame = cv2.flip(frame, 1)

                self.video_writer.write(frame)

                elapsed_time = time.time() - self.video_start_time

                cv2.putText(frame,
                            (f'Frame = {str(frame_number)}'),
                            org=(500, 430),
                            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale=.5, color=(255, 255, 0), thickness=1,
                            lineType=cv2.LINE_AA, bottomLeftOrigin=False)

                cv2.putText(frame,
                            ('Time = ' + str(
                                "{:.2f}".format(elapsed_time)) + ' s'),
                            org=(500, 460), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale=.5, color=(255, 255, 0), thickness=1,
                            lineType=cv2.LINE_AA, bottomLeftOrigin=False)

                cv2.putText(frame,
                            (f"{self.data['Mouse ID']}"
                             f" - {self.data['Behavior test']}"),
                            org=(20, 10), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale=.5, color=(255, 255, 0), thickness=1,
                            lineType=cv2.LINE_AA, bottomLeftOrigin=False)

                if not flag_start:
                    # prints start timestamp only during first frame
                    self.video_start_time = time.time()
                    flag_start = True

                cv2.imshow("Recording", frame)
                frame_number += 1

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.ser.close()
                    break

        self.video_cap.release()
        self.video_writer.release()
        cv2.destroyAllWindows()

        self.save_data_to_json()

    def start_recording(self):

        if not self.is_recording:

            self.stop_event.clear()

            self.t1 = threading.Thread(
                target=self.record_video)

            self.t2 = threading.Thread(
                target=self.send_serial_command)

            self.is_recording = True
            self.stop_button.setEnabled(True)
            self.t1.start()
            self.t2.start()

            print(f'Running {self.protocol.__class__.__name__}..')

            # Start a cleanup thread
            cleanup_thread = threading.Thread(target=self.finish_recording)
            cleanup_thread.start()

        else:
            print("Recording is already in progress.")

    def finish_recording(self):

        # Wait for both threads to complete
        self.t1.join()
        self.t2.join()

        # Now that both threads are done, perform the cleanup
        self.is_recording = False
        self.stop_button.setEnabled(False)
        print("Recording stopped and threads cleaned up.")

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

                self.stop_event.set()
                self.protocol.request_stop()
                self.t1.join()
                self.t2.join()

                if hasattr(self, 'ser') and self.ser.isOpen():
                    self.ser.close()
                if hasattr(self, 'video_cap'):
                    self.video_cap.release()
                if hasattr(self, 'video_writer'):
                    self.video_writer.release()

                cv2.destroyAllWindows()
                self.is_recording = False

                print("Recording stopped successfully.")

            else:
                print("Recording continues.")

        else:
            print("No recording is currently active.")

    def save_data_to_json(self) -> None:
        """
        Save metadata to a .json file according to predefined formatting.
        """

        filename_path = Path(self.filename)
        base_name = filename_path.stem.split('_')[0]
        json_file_path = (
            filename_path.with_name(base_name).with_suffix('.json'))

        experiment_data = {
            'Type': self.data['Behavior test'],
            'Date': date.today().strftime("%Y-%m-%d"),
            'Treatment': self.data['Treatment'],
            'Video Start Time': self.video_start_time,
            'Serial Start Time': self.serial_start_time,
            'Video File': str(Path(self.filename).resolve())
        }

        if json_file_path.exists():
            with json_file_path.open('r') as jsonFile:
                json_data = json.load(jsonFile)

            if 'Behavior test' in json_data:
                if isinstance(json_data['Behavior test'], dict):
                    json_data['Behavior test'] = [json_data['Behavior test']]

                if (json_data['Behavior test'][0]['Type'] ==
                        experiment_data['Type']):
                    json_data['Behavior test'][0] = experiment_data
                else:
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

    def get_date(
            self
    ) -> str:
        """
        Returns the current date formatted as a string in "YYMMDD" format.
        """

        return date.today().strftime("%y%m%d")


# def main():
# 
#     app = QApplication([])
# 
#     m = Main()
#     m.show()
# 
#     sys.exit(app.exec_())


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

if __name__ == '__main__':
    run_app()
""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

import json
import time
from datetime import date
from pathlib import Path

from PyQt5 import QtCore
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal

from pyhavior.core import ProtocolRunner, AVAILABLE_PROTOCOLS
from pyhavior.core.threads import SerialThread, RecordingVideoThread
from pyhavior.gui.dialogs import EnterInfoDialog, EnterCOMDialog
from pyhavior.gui.windows import RecordingWindow


class RecordFrame(QFrame):
    """Frame with functionalities for saving and recording."""

    # Ensure UI updates from worker threads are marshaled to the GUI thread
    stop_enabled = pyqtSignal(bool)
    show_error = pyqtSignal(str, str)

    def __init__(
            self,
            save_frame: QFrame,
            info_display_frame: QFrame = None,
            default_com_port: str = 'COM4'
    ) -> None:
        super().__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.init_buttons()
        self.init_attributes()

        self.com_port = default_com_port
        self.camera_device = 0  # Default camera device

        # Updated to use ProtocolRunner for sequence-based protocols only
        self.experiment_classes = {}
        
        # Add sequence-based protocols (these are the actual behavioral protocols)
        for protocol_name in AVAILABLE_PROTOCOLS:
            self.experiment_classes[protocol_name] = (
                lambda name=protocol_name: ProtocolRunner(name)
            )

        info_dialog = EnterInfoDialog()
        info_dialog.info_entered.connect(self.handle_info)
        
        com_dialog = EnterCOMDialog()
        com_dialog.com_port.connect(self.handle_com_port)
        
        save_frame.dest_folder.connect(self.handle_dest_folder)

        self.is_recording = False
        self.recording_thread = None
        self.serial_thread = None
        self.recording_window = None
        
        # Initialize recording metadata attributes
        self.fps = 30
        self.frame_width = 640
        self.frame_height = 480
        self.video_path = None
        
        # Store reference to info display frame
        self.info_display_frame = info_display_frame
        
        # Initialize hardware info display with defaults
        if self.info_display_frame:
            self.info_display_frame.update_hardware_info(
                com_port=self.com_port, 
                camera_device=self.camera_device
            )
        
        # Connect stop_enabled signal to update UI
        self.stop_enabled.connect(self.stop_button.setEnabled)
        self.show_error.connect(self.display_error_message)

    def init_attributes(self) -> None:
        
        self.dest_folder_received = False
        self.info_entered_received = False

    def init_buttons(self) -> None:
        
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
        print(f"COM port set to: {self.com_port}")
        # Update info display with COM port
        if self.info_display_frame:
            self.info_display_frame.update_hardware_info(com_port=self.com_port)

    def handle_camera_selection(
            self,
            camera_device: int
    ) -> None:
        """Handle camera device selection from dialog."""
    
        self.camera_device = camera_device
        print(f"Camera device set to: {self.camera_device}")
        # Update info display with camera device
        if self.info_display_frame:
            self.info_display_frame.update_hardware_info(camera_device=self.camera_device)

    def handle_info(
            self,
            data: dict
    ) -> None:
    
        self.data = data
        self.info_entered_received = True
        
        # Update info display frame with mouse information
        if self.info_display_frame:
            self.info_display_frame.update_mouse_info(data)
        
        self.check_all_signals_received()

    def check_all_signals_received(self) -> None:
        
        if self.dest_folder_received and self.info_entered_received:
            self.record_button.setEnabled(True)

            self.folder_path = Path(self.dest_folder) / self.data['Mouse ID']

            self.folder_path.mkdir(parents=True, exist_ok=True)

            self.filename = (
                self.folder_path /
                f"{self.data['Mouse ID']}_"
                f"{self.data['Behavior test']}.avi")

            self.init_protocol()

    def init_protocol(self) -> None:
        
        experiment = self.data['Behavior test']

        if experiment in self.experiment_classes:
            self.protocol = self.experiment_classes[experiment]()
        else:
            raise KeyError(
                f"Experiment {experiment} not recognized.")

    def display_error_message(
            self,
            title: str,
            message: str
    ) -> None:
        """Display error message in GUI thread"""
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()
        
    def on_recording_finished(self) -> None:
        """Handle recording completion"""
        
        self.is_recording = False
        self.record_button.setEnabled(True)  # Re-enable record button
        self.stop_enabled.emit(False)
        
        if self.recording_window:
            self.recording_window.close()
            self.recording_window = None
        
        # Clear video metadata from info display
        if self.info_display_frame:
            self.info_display_frame.clear_video_metadata()
        
        # Stop the serial thread if it's still running
        if self.serial_thread and self.serial_thread.isRunning():
            self.protocol.request_stop()
            self.serial_thread.stop()
            self.serial_thread.wait()  # Wait for thread to finish
            print("Serial thread stopped.")
        
        # Verify video file and save metadata
        if hasattr(self, 'video_start_time') and hasattr(self, 'serial_start_time'):
            self.save_data_to_json()
        
        # Check if video file was created successfully
        if self.video_path and Path(self.video_path).exists():
            file_size = Path(self.video_path).stat().st_size
            print(f"Video saved: {self.video_path} (Size: {file_size:,} bytes)")
            if file_size < 1000:  # Very small file might be corrupted
                print("Warning: Video file is very small and might be corrupted")
        else:
            print("Warning: Video file was not created or is missing")
        
        print(f"Recording finished at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    def on_recording_error(
            self,
            error_message: str
    ) -> None:
        """Handle recording errors"""
    
        print(f"Recording error: {error_message}")
        self.record_button.setEnabled(True)  # Re-enable record button on error
        self.show_error.emit("Recording Error", error_message)
        self.stop_recording()
        
    def on_recording_metadata(
            self,
            metadata: dict
    ) -> None:
        """Handle recording metadata from RecordingVideoThread"""
        
        self.video_path = metadata.get('video_path')
        self.fps = metadata.get('fps', 30)
        self.frame_width = metadata.get('frame_width', 640)
        self.frame_height = metadata.get('frame_height', 480)
        
        # Print metadata properly
        print("Recording metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        # Update info display frame with video metadata
        if self.info_display_frame:
            self.info_display_frame.update_video_metadata(metadata)

    def start_recording(self) -> None:
        
        if not self.is_recording:
            
            self.serial_start_time = time.time()
            self.video_start_time = time.time()
            
            ts_serial = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.serial_start_time))
            ts_video = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.video_start_time))
            print(f'Serial start: {ts_serial}')
            print(f'Video start: {ts_video}')
            
            # Start serial thread
            self.serial_thread = SerialThread(self.com_port, self.protocol)
            self.serial_thread.start()
            
            # Start recording thread
            self.recording_thread = RecordingVideoThread(
                str(self.filename),
                self.protocol.duration,
                self.data,
                capture_device=self.camera_device,
                parent=self
            )
            
            # Create and show recording window
            self.recording_window = RecordingWindow(
                self.data['Mouse ID'], 
                self.data['Behavior test']
            )
            self.recording_window.show()
            
            # Connect signals
            self.recording_thread.recording_finished.connect(self.on_recording_finished)
            self.recording_thread.error_occurred.connect(self.on_recording_error)
            self.recording_thread.recording_metadata.connect(self.on_recording_metadata)
            self.recording_thread.frame_recorded.connect(self.recording_window.display_frame)
            self.recording_window.recording_window_closed.connect(self.stop_recording)
            
            self.is_recording = True
            self.record_button.setEnabled(False)  # Disable record button during recording
            self.stop_enabled.emit(True)
            self.recording_thread.start_recording()
        else:
            print("Recording is already in progress.")

    def stop_recording(self) -> None:
        
        if self.is_recording:
            response = QMessageBox.question(
                self,
                'Stop Recording',
                "Recording is in progress. Are you sure you want to stop?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if response == QMessageBox.Yes:

                # Stop threads properly to prevent file corruption
                if self.recording_thread:
                    print("Stopping recording thread...")
                    self.recording_thread.stop_recording()
                    # Wait for recording thread to finish before continuing
                    if not self.recording_thread.wait(10000):  # 10 second timeout
                        print("Warning: Recording thread did not stop in time")
                    
                if self.serial_thread:
                    print("Stopping serial thread...")
                    self.protocol.request_stop()
                    self.serial_thread.stop()
                    
                self.is_recording = False
                self.record_button.setEnabled(True)  # Re-enable record button
                self.stop_enabled.emit(False)
                
                # Save metadata after ensuring threads have stopped
                if hasattr(self, 'video_start_time') and hasattr(self, 'serial_start_time'):
                    self.save_data_to_json()
                
                print("Recording stopped successfully.")
            else:
                print("Recording continues.")

    def save_data_to_json(self) -> None:
        """Save metadata to a .json file according to predefined formatting."""
        
        filename_path = Path(self.filename)
        base_name = filename_path.stem.split('_')[0]
        json_file_path = (
            filename_path.with_name(base_name).with_suffix('.json'))

        # Use the actual video path from the recording thread if available
        if self.video_path:
            video_file_resolved = str(Path(self.video_path).resolve())
        else:
            # Fallback to constructed path
            base = Path(self.filename)
            ts = time.strftime('%H%M%S', time.localtime(self.video_start_time))
            video_file_resolved = str(base.with_name(f"{base.stem}_{ts}.avi").resolve())

        experiment_data = {
            'Type': self.data['Behavior test'],
            'Date': date.today().strftime("%Y-%m-%d"),
            'Treatment': self.data['Treatment'],
            'Video Start Time': self.video_start_time,
            'Serial Start Time': self.serial_start_time,
            'Video File': video_file_resolved,
            'Camera FPS': self.fps,
            'Frame Width': self.frame_width,
            'Frame Height': self.frame_height,
            'com Port': self.com_port,
            'camera_index': self.camera_device,            
        }

        if json_file_path.exists():
            with json_file_path.open('r') as jsonFile:
                json_data = json.load(jsonFile)

            # Ensure 'Behavior test' is a list and append the new run
            if 'Behavior test' in json_data:
                if isinstance(json_data['Behavior test'], dict):
                    json_data['Behavior test'] = [json_data['Behavior test']]
                
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

    def get_date(self) -> str:
        """Returns the current date formatted as a string in "YYMMDD" format."""
        
        return date.today().strftime("%y%m%d")
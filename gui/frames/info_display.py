""" Created on Mon Nov 27 15:39:53 2023
    @author: dcupolillo """

from pathlib import Path
from PyQt5 import QtCore
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit


class InfoDisplayFrame(QFrame):
    """Frame to display mouse information and video metadata."""
    
    def __init__(self) -> None:
        super().__init__()
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        
        self.init_display()
        
    def init_display(self) -> None:
        """Initialize the display labels with single column layout"""
        
        # Set column stretch to center the single column
        self.layout.setColumnStretch(0, 1)  # Left spacer
        self.layout.setColumnStretch(1, 0)  # Label column
        self.layout.setColumnStretch(2, 0)  # Field column
        self.layout.setColumnStretch(3, 1)  # Right spacer
        
        # Title
        title = QLabel('Current Session Info')
        title.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(title, 0, 0, 1, 4)
        
        row = 1
        
        # Mouse info line edits (read-only)
        self.mouse_id_edit = QLineEdit('Not set')
        self.mouse_id_edit.setReadOnly(True)
        self.mouse_id_edit.setMinimumWidth(200)
        
        self.genotype_edit = QLineEdit('Not set')
        self.genotype_edit.setReadOnly(True)
        self.genotype_edit.setMinimumWidth(200)
        
        self.dob_edit = QLineEdit('Not set')
        self.dob_edit.setReadOnly(True)
        self.dob_edit.setMinimumWidth(200)
        
        self.experiment_edit = QLineEdit('Not set')
        self.experiment_edit.setReadOnly(True)
        self.experiment_edit.setMinimumWidth(200)
        
        self.treatment_edit = QLineEdit('Not set')
        self.treatment_edit.setReadOnly(True)
        self.treatment_edit.setMinimumWidth(200)
        
        # Hardware configuration line edits (read-only)
        self.com_port_edit = QLineEdit('Not set')
        self.com_port_edit.setReadOnly(True)
        self.com_port_edit.setMinimumWidth(200)
        
        self.camera_device_edit = QLineEdit('Not set')
        self.camera_device_edit.setReadOnly(True)
        self.camera_device_edit.setMinimumWidth(200)
        
        # Single column layout for mouse info
        self.layout.addWidget(QLabel('Mouse ID:'), row, 1)
        self.layout.addWidget(self.mouse_id_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Genotype:'), row, 1)
        self.layout.addWidget(self.genotype_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Date of birth:'), row, 1)
        self.layout.addWidget(self.dob_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Experiment:'), row, 1)
        self.layout.addWidget(self.experiment_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Treatment:'), row, 1)
        self.layout.addWidget(self.treatment_edit, row, 2)
        row += 1
        
        # Hardware configuration section
        self.layout.addWidget(QLabel('COM Port:'), row, 1)
        self.layout.addWidget(self.com_port_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Camera Device:'), row, 1)
        self.layout.addWidget(self.camera_device_edit, row, 2)
        row += 2  # Extra space before video section
        
        # Video metadata line edits (read-only)
        self.video_path_edit = QLineEdit('Not recording')
        self.video_path_edit.setReadOnly(True)
        self.video_path_edit.setMinimumWidth(200)
        
        self.video_fps_edit = QLineEdit('--')
        self.video_fps_edit.setReadOnly(True)
        self.video_fps_edit.setMinimumWidth(200)
        
        self.video_resolution_edit = QLineEdit('--')
        self.video_resolution_edit.setReadOnly(True)
        self.video_resolution_edit.setMinimumWidth(200)
        
        # Single column layout for video info
        self.layout.addWidget(QLabel('Video file:'), row, 1)
        self.layout.addWidget(self.video_path_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('FPS:'), row, 1)
        self.layout.addWidget(self.video_fps_edit, row, 2)
        row += 1
        
        self.layout.addWidget(QLabel('Resolution:'), row, 1)
        self.layout.addWidget(self.video_resolution_edit, row, 2)
        
    def update_mouse_info(self, data: dict) -> None:
        """Update the displayed mouse information"""
        self.mouse_id_edit.setText(data.get('Mouse ID', 'Not set'))
        self.genotype_edit.setText(data.get('Genotype', 'Not set'))
        self.dob_edit.setText(data.get('Date of birth', 'Not set'))
        self.experiment_edit.setText(data.get('Behavior test', 'Not set'))
        self.treatment_edit.setText(data.get('Treatment', 'Not set'))
        
    def update_hardware_info(self, com_port: str = None, camera_device: int = None) -> None:
        """Update the displayed hardware configuration"""
        if com_port is not None:
            self.com_port_edit.setText(com_port)
        if camera_device is not None:
            self.camera_device_edit.setText(f"Camera {camera_device}")
        
    def update_video_metadata(self, metadata: dict) -> None:
        """Update the displayed video metadata during recording"""
        video_path = metadata.get('video_path', 'Unknown')
        if video_path != 'Unknown':
            filename = Path(video_path).name
            self.video_path_edit.setText(filename)
        else:
            self.video_path_edit.setText(video_path)
            
        fps = metadata.get('fps', '--')
        self.video_fps_edit.setText(str(fps))
        
        width = metadata.get('frame_width', '--')
        height = metadata.get('frame_height', '--')
        self.video_resolution_edit.setText(f"{width}x{height}")
        
    def clear_video_metadata(self) -> None:
        """Clear video metadata when recording stops"""
        self.video_path_edit.setText('Not recording')
        self.video_fps_edit.setText('--')
        self.video_resolution_edit.setText('--')
        
    def clear_hardware_info(self) -> None:
        """Clear hardware configuration when session ends"""
        self.com_port_edit.setText('Not set')
        self.camera_device_edit.setText('Not set')
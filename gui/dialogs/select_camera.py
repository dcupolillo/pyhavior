""" Created on October 3, 2025
    @author: dcupolillo """

import cv2
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QGridLayout, QLabel, QPushButton, QComboBox, QMessageBox
)
from PyQt5.QtCore import pyqtSignal


class SelectCameraDialog(QDialog):
    """Dialog window to select camera device for video recording.
    
    Appears when clicking 'Select Camera' button in Main window.
    """

    camera_selected = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle('Camera Selection')
        self.setWindowIcon(QIcon('..\\pyhavior_icon.png'))
        self.layout = QGridLayout(self)

        self.layout.addWidget(QLabel('Camera Device:'), 0, 0)

        self.camera_combo = QComboBox()
        self.populate_cameras()

        self.layout.addWidget(self.camera_combo, 0, 1, 1, 2)

        self.ok_button = QPushButton('Ok')
        self.ok_button.clicked.connect(self.get_camera_device)
        self.layout.addWidget(self.ok_button, 1, 1)

        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.clicked.connect(self.accept)
        self.layout.addWidget(self.cancel_button, 1, 2)

    def populate_cameras(self) -> None:
        """Scan for available camera devices."""
        self.camera_combo.clear()
        
        # Test camera indices 0-5 (covers most systems)
        available_cameras = []
        
        for i in range(6):
            # Try DirectShow first (better for industrial cameras like uEye)
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if not cap.isOpened():
                # Fallback to default backend
                cap = cv2.VideoCapture(i)
            
            if cap.isOpened():
                # Try to read a frame to verify camera works
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Get camera info if available
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    # Simple camera naming with index
                    camera_info = f"Camera {i} ({width}x{height}"
                    if fps > 0:
                        camera_info += f" @ {fps:.0f}fps"
                    camera_info += ")"
                    
                    available_cameras.append((i, camera_info))
                
                cap.release()
        
        if not available_cameras:
            self.camera_combo.addItem("No cameras found")
            self.ok_button.setEnabled(False)
        else:
            for cam_index, cam_info in available_cameras:
                self.camera_combo.addItem(cam_info)
            
            # Default to Camera 0 (first camera found)
            for i, (cam_index, cam_info) in enumerate(available_cameras):
                if cam_index == 0:
                    self.camera_combo.setCurrentIndex(i)
                    break

    def get_selected_camera_index(self) -> int:
        """Extract camera index from selected text."""
        current_text = self.camera_combo.currentText()
        
        # Find the camera in our available cameras list to get the index
        current_index = self.camera_combo.currentIndex()
        if current_index >= 0:
            # Re-scan to get the actual camera index (since we store it during population)
            camera_count = 0
            for i in range(6):
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(i)
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        if camera_count == current_index:
                            cap.release()
                            return i
                        camera_count += 1
                    cap.release()
        
        return None

    def get_camera_device(self) -> None:
        """Get selected camera device and emit signal."""
        camera_index = self.get_selected_camera_index()
        if camera_index is not None:
            self.camera_selected.emit(camera_index)
            self.accept()
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a valid camera device.")
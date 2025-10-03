""" 
Protocol Visualization Window
Created on October 2, 2025
@author: dcupolillo 
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QLabel, QMessageBox, QGraphicsView, 
    QGraphicsScene, QGraphicsLineItem, QGraphicsTextItem, 
    QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QColor, QFont, QCloseEvent, QPainter

from pyhavior.core import ProtocolRunner, AVAILABLE_PROTOCOLS


class ProtocolVisualizerWindow(QWidget):
    """
    Window for visualizing protocol waveforms
    """
    
    # Device type definitions with colors and labels
    DEVICE_TYPES = {
        'tone': {'color': 'mediumblue', 'y_offset': 0, 'label': 'Tone'},
        'shock': {'color': 'crimson', 'y_offset': 1, 'label': 'Shock'},
        'pump': {'color': 'forestgreen', 'y_offset': 2, 'label': 'Pump'},
        'buzzer': {'color': 'deeppink', 'y_offset': 3, 'label': 'Buzzer'},
        'white_noise': {'color': 'indigo', 'y_offset': 4, 'label': 'White Noise'}
    }

    def __init__(
            self,
            parent: QWidget = None
    ) -> None:
    
        super().__init__(parent)
        self.setWindowTitle("Protocol Visualizer")
        self.setGeometry(200, 200, 1000, 600)
        
        # Force window to be visible and on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        
        self.init_ui()
        self.load_protocols()
        
    def init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        # Protocol selection
        protocol_label = QLabel("Select Protocol:")
        
        self.protocol_combo = QComboBox()
        self.protocol_combo.setMinimumWidth(200)
        self.protocol_combo.currentTextChanged.connect(self.on_protocol_changed)
        
        # Visualize button
        self.visualize_button = QPushButton("Show Waveform")
        self.visualize_button.setMinimumSize(120, 35)
        self.visualize_button.clicked.connect(self.visualize_protocol)
        self.visualize_button.setEnabled(False)
        
        # Save button
        self.save_button = QPushButton("Save Image")
        self.save_button.setMinimumSize(100, 35)
        self.save_button.clicked.connect(self.save_visualization)
        self.save_button.setEnabled(False)
        
        header_layout.addWidget(protocol_label)
        header_layout.addWidget(self.protocol_combo)
        header_layout.addWidget(self.visualize_button)
        header_layout.addWidget(self.save_button)
        header_layout.addStretch()  # Push everything to the left
        
        layout.addLayout(header_layout)
        
        # Graphics view for waveform display
        try:
            self.graphics_view = QGraphicsView()
            self.graphics_scene = QGraphicsScene()
            self.graphics_view.setScene(self.graphics_scene)
            self.graphics_view.setMinimumSize(800, 400)
            layout.addWidget(self.graphics_view)
        except Exception as e:
            error_label = QLabel(f"Graphics view unavailable: {e}")
            layout.addWidget(error_label)
        
        # Status label
        self.status_label = QLabel("Select a protocol")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
    def load_protocols(self) -> None:
        """Load available protocols into the dropdown"""
        try:
            # Get available behavioral protocols from sequence files
            available_protocols = AVAILABLE_PROTOCOLS
            
            self.protocol_combo.clear()
            self.protocol_combo.addItem("-- Select Protocol --")
            
            for protocol_name in available_protocols:
                self.protocol_combo.addItem(protocol_name)
                
            self.status_label.setText(f"Loaded {len(available_protocols)} behavioral protocols")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load protocols: {e}")
            self.status_label.setText("Error loading protocols")
            
    def on_protocol_changed(
            self,
            protocol_name: str
    ) -> None:
        """Handle protocol selection change"""
        if protocol_name and protocol_name != "-- Select Protocol --":
            self.visualize_button.setEnabled(True)
            self.status_label.setText(f"Selected: {protocol_name}")
        else:
            self.visualize_button.setEnabled(False)
            self.save_button.setEnabled(False)  # Disable save when no protocol selected
            self.status_label.setText("Select a protocol to visualize its waveform")
            
    def visualize_protocol(self):
        """Visualize the selected protocol using PyQt graphics"""
        protocol_name = self.protocol_combo.currentText()
        
        if not protocol_name or protocol_name == "-- Select Protocol --":
            return
            
        try:
            # Clear the current scene
            self.graphics_scene.clear()
            
            # All protocols are now sequence-based
            protocol_instance = ProtocolRunner(protocol_name)
            
            # Generate waveform data
            waveform_data = self.generate_waveform_data(protocol_instance)
            
            if waveform_data:
                self.draw_waveform(waveform_data, protocol_name)
                self.status_label.setText(f"Displaying waveform for: {protocol_name}")
                self.save_button.setEnabled(True)  # Enable save after successful visualization
            else:
                self.draw_protocol_info(protocol_instance, protocol_name)
                self.status_label.setText(f"Displaying info for: {protocol_name}")
                self.save_button.setEnabled(True)  # Enable save after successful visualization
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Protocol visualizer error: {error_details}")  # Debug to console
            QMessageBox.critical(
                self, 
                "Visualization Error", 
                f"Failed to visualize protocol '{protocol_name}':\\n{str(e)}\\n\\nFull error printed to console."
            )
            self.status_label.setText("Error generating waveform")
    
    def save_visualization(self):
        """Save the current visualization as an image file"""
        if not self.graphics_scene.items():
            QMessageBox.warning(self, "No Visualization", "No visualization to save. Please generate a waveform first.")
            return
        
        # Get current protocol name for default filename
        protocol_name = self.protocol_combo.currentText()
        if not protocol_name or protocol_name == "-- Select Protocol --":
            protocol_name = "protocol"
        
        # Clean protocol name for filename
        safe_name = "".join(c for c in protocol_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        default_filename = f"{safe_name}_waveform.png"
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Visualization",
            default_filename,
            "PNG Images (*.png);;JPEG Images (*.jpg);;SVG Images (*.svg);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get scene rectangle
                scene_rect = self.graphics_scene.sceneRect()
                
                # Create a pixmap with the scene size
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap(int(scene_rect.width()), int(scene_rect.height()))
                pixmap.fill(Qt.white)  # White background
                
                # Render the scene to the pixmap
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                self.graphics_scene.render(painter)
                painter.end()
                
                # Save the pixmap
                success = pixmap.save(file_path)
                
                if success:
                    self.status_label.setText(f"Visualization saved to: {file_path}")
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Visualization saved successfully to:\n{file_path}")
                else:
                    QMessageBox.warning(
                        self, "Save Failed", "Failed to save the visualization.")
                    
            except Exception as e:
                QMessageBox.critical(
                    self, "Save Error", f"Error saving visualization:\n{str(e)}")
            
    def generate_waveform_data(
            self,
            protocol_instance
    ) -> dict:
        """
        Generate waveform data from protocol sequence for plotting digital signals.
        """
        
        try:
            if hasattr(protocol_instance, 'sequence') and protocol_instance.sequence:
                duration = getattr(protocol_instance, 'duration', 300)
                
                # Initialize waveform data structure
                waveform_data = {
                    'duration': duration,
                    'devices': {},
                    'device_types': self.DEVICE_TYPES
                }
                
                # Initialize each device with empty signal list
                for device in self.DEVICE_TYPES:
                    waveform_data['devices'][device] = []
                
                # Parse events using a unified approach for both ON/OFF pairs and duration-based events
                parsed_events = self.parse_protocol_events(protocol_instance.sequence)
                
                # Add parsed events to waveform data
                for device, events in parsed_events.items():
                    if device in self.DEVICE_TYPES:
                        waveform_data['devices'][device].extend(events)
                
                return waveform_data
            else:
                return None
                
        except Exception as e:
            print(f"Error generating waveform data: {e}")
            return None
    
    def draw_waveform(
            self,
            waveform_data: dict,
            protocol_name: str
    ) -> None:
        """Draw digital waveform signals using PyQt graphics"""
        
        duration = waveform_data['duration']
        devices = waveform_data['devices']
        device_types = waveform_data['device_types']
        
        # Set up coordinate system
        width = 800
        margin_x = 80
        channel_height = 60
        
        # Calculate active devices and total height
        active_devices = [dev for dev, signals in devices.items() if signals]
        
        # Fixed positions
        time_axis_y = 400
        time_axis_height = 50
        total_height = time_axis_y + time_axis_height
        
        # Set scene rect
        self.graphics_scene.setSceneRect(0, 0, width + 2*margin_x, total_height)
        
        # Time axis (always show at fixed position)
        pen_axis = QPen(QColor(0, 0, 0), 2)
        
        # Main time axis line
        time_axis = QGraphicsLineItem(
            margin_x, time_axis_y, width + margin_x, time_axis_y)
        time_axis.setPen(pen_axis)
        self.graphics_scene.addItem(time_axis)
        
        # Time axis labels
        time_steps = 5  # Number of time labels
        for i in range(time_steps + 1):
            time_val = (duration * i) / time_steps
            x_pos = margin_x + (width * i) / time_steps
            
            # Tick mark
            tick = QGraphicsLineItem(x_pos, time_axis_y - 5, x_pos, time_axis_y + 5)
            tick.setPen(pen_axis)
            self.graphics_scene.addItem(tick)
            
            # Time label (just the number, no 's')
            time_text = QGraphicsTextItem(f"{time_val:.0f}")
            time_text.setPos(x_pos - 10, time_axis_y + 10)
            self.graphics_scene.addItem(time_text)
        
        # X-axis label "Time (s)"
        xlabel_text = QGraphicsTextItem("Time (s)")
        xlabel_font = QFont("Arial", 12, QFont.Bold)
        xlabel_text.setFont(xlabel_font)
        # Center the label below the time axis
        xlabel_x = margin_x + width/2 - 30  # Approximate centering
        xlabel_y = time_axis_y + 35
        xlabel_text.setPos(xlabel_x, xlabel_y)
        self.graphics_scene.addItem(xlabel_text)
        
        # Draw device channels if any are active
        if active_devices:
            # Calculate available space between title and time axis
            available_space = time_axis_y - 80  # Space between title area and time axis
            channel_spacing = min(channel_height, available_space / len(active_devices))
            
            for i, device in enumerate(active_devices):
                # Start from bottom (near time axis) and stack upwards
                y_base = time_axis_y - (i + 1) * channel_spacing - 20
                signals = devices[device]
                device_info = device_types[device]
                
                # Device label
                label_text = QGraphicsTextItem(device_info['label'])
                label_text.setPos(10, y_base + 15)
                self.graphics_scene.addItem(label_text)
                
                # Draw signal pulses as square waves
                pen_signal = QPen(QColor(device_info['color']), 3)
                
                # Draw baseline segments between signals (same color/width as signal)
                signal_times = [(s['start'], s['end']) for s in signals]
                signal_times.sort()  # Sort by start time
                
                # Draw baseline from start to first signal
                if signal_times:
                    if signal_times[0][0] > 0:
                        baseline_start = QGraphicsLineItem(
                            margin_x, y_base + 40, 
                            margin_x + (signal_times[0][0] / duration) * width, y_base + 40)
                        baseline_start.setPen(pen_signal)
                        self.graphics_scene.addItem(baseline_start)
                    
                    # Draw baseline segments between signals
                    for i in range(len(signal_times) - 1):
                        gap_start_x = margin_x + (signal_times[i][1] / duration) * width
                        gap_end_x = margin_x + (signal_times[i+1][0] / duration) * width
                        if gap_end_x > gap_start_x:  # Only if there's a gap
                            baseline_gap = QGraphicsLineItem(
                                gap_start_x, y_base + 40, gap_end_x, y_base + 40)
                            baseline_gap.setPen(pen_signal)
                            self.graphics_scene.addItem(baseline_gap)
                    
                    # Draw baseline from last signal to end
                    if signal_times[-1][1] < duration:
                        baseline_end = QGraphicsLineItem(
                            margin_x + (signal_times[-1][1] / duration) * width, y_base + 40,
                            margin_x + width, y_base + 40)
                        baseline_end.setPen(pen_signal)
                        self.graphics_scene.addItem(baseline_end)
                else:
                    # No signals, draw full baseline
                    baseline_full = QGraphicsLineItem(
                        margin_x, y_base + 40, margin_x + width, y_base + 40)
                    baseline_full.setPen(pen_signal)
                    self.graphics_scene.addItem(baseline_full)
                
                for signal in signals:
                    start_time = signal['start']
                    end_time = signal['end']
                    
                    # Convert time to x coordinates
                    x_start = margin_x + (start_time / duration) * width
                    x_end = margin_x + (end_time / duration) * width
                    
                    # Square wave: off -> on -> off
                    y_off = y_base + 40  # Baseline
                    y_on = y_base + 10   # High state
                    
                    # Rising edge
                    rising_edge = QGraphicsLineItem(x_start, y_off, x_start, y_on)
                    rising_edge.setPen(pen_signal)
                    self.graphics_scene.addItem(rising_edge)
                    
                    # High state
                    high_state = QGraphicsLineItem(x_start, y_on, x_end, y_on)
                    high_state.setPen(pen_signal)
                    self.graphics_scene.addItem(high_state)
                    
                    # Falling edge
                    falling_edge = QGraphicsLineItem(x_end, y_on, x_end, y_off)
                    falling_edge.setPen(pen_signal)
                    self.graphics_scene.addItem(falling_edge)
    
    def parse_protocol_events(self, sequence):
        """
        Parse protocol sequence events using standardized ON/OFF pairs.
        Expected format: (time, message, 0, None, "DEVICE X ON/OFF")
        Returns: dict of {device: [{'start': time, 'end': time, 'description': str}]}
        """
        device_events = {}
        device_states = {}  # Track pending ON events waiting for OFF
        
        for event in sequence:
            if len(event) >= 5:
                event_time, msg, duration, msg_off, description = event[:5]
                print(f"Event: time={event_time}, description='{description}'")  # Debug
                print(f"Description upper: '{description.upper()}'")  # Debug
                print(f"'ON' in description: {'ON' in description.upper()}, 'OFF' in description: {'OFF' in description.upper()}")  # Debug
                device = self.extract_device_from_description(description)
                print(f"Extracted device: '{device}'")  # Debug
                
                if device == 'unknown':
                    continue
                    
                if device not in device_events:
                    device_events[device] = []
                
                if 'OFF' in description.upper():
                    # Device turning OFF (check OFF first!)
                    if device in device_states:
                        start_info = device_states[device]
                        device_events[device].append({
                            'start': start_info['start_time'],
                            'end': event_time,
                            'description': f"{start_info['description']} -> {description}"
                        })
                        del device_states[device]
                    else:
                        print(f"Warning: {device} OFF event at {event_time} without matching ON event")
                        
                elif 'ON' in description.upper():
                    # Device turning ON
                    if device in device_states:
                        print(f"Warning: {device} already ON at {event_time}, previous ON at {device_states[device]['start_time']}")
                    
                    device_states[device] = {
                        'start_time': event_time,
                        'description': description
                    }
        
        # Handle any remaining ON states without matching OFF (protocol incomplete)
        for device, state_info in device_states.items():
            print(f"Warning: {device} turned ON at {state_info['start_time']} but never turned OFF")
        
        return device_events
    
    def extract_device_from_description(self, description: str) -> str:
        """Extract device type from event description"""
        if not description:
            return 'unknown'
            
        description_lower = description.lower()
        
        # Check for each device type
        if 'tone' in description_lower:
            return 'tone'
        elif 'shock' in description_lower or 'shocker' in description_lower:
            return 'shock'
        elif 'pump' in description_lower:
            return 'pump'
        elif 'buzzer' in description_lower:
            return 'buzzer'
        elif 'white_noise' in description_lower or 'noise' in description_lower:
            return 'white_noise'
        else:
            return 'unknown'
    
    def draw_protocol_info(
            self,
            protocol_instance,
            protocol_name: str
    ) -> None:
        """Draw protocol information when waveform data is not available"""
        
        # Clear and set scene rect
        width = 600
        height = 400
        self.graphics_scene.setSceneRect(0, 0, width, height)
        
        # Title
        title_text = QGraphicsTextItem(f"Protocol: {protocol_name}")
        title_text.setFont(QFont("Arial", 16, QFont.Bold))
        title_text.setPos(50, 50)
        self.graphics_scene.addItem(title_text)
        
        # Protocol info
        y_pos = 100
        info_items = []
        
        if hasattr(protocol_instance, 'duration'):
            info_items.append(f"Duration: {protocol_instance.duration} seconds")
        
        # Add other protocol attributes
        for attr_name in dir(protocol_instance):
            if not attr_name.startswith('_') and not callable(getattr(protocol_instance, attr_name)):
                attr_value = getattr(protocol_instance, attr_name)
                if isinstance(attr_value, (int, float, str, bool)):
                    info_items.append(f"{attr_name}: {attr_value}")
        
        for item in info_items[:10]:  # Limit to 10 items
            info_text = QGraphicsTextItem(item)
            info_text.setFont(QFont("Arial", 12))
            info_text.setPos(70, y_pos)
            self.graphics_scene.addItem(info_text)
            y_pos += 30
    
    def closeEvent(
            self,
            event: QCloseEvent
    ) -> None:
        """Handle window closing"""
        self.graphics_scene.clear()
        event.accept()
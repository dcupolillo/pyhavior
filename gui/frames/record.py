import json
import time
from datetime import date
from pathlib import Path

from PyQt5 import QtCore
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal, QTimer

from pyhavior.core import ProtocolRunner, AVAILABLE_PROTOCOLS
from pyhavior.core.arduino import ArduinoBoard
from pyhavior.core.camera import Camera
from pyhavior.core.clock import SessionClock
from pyhavior.core.threads import SerialThread, RecordingVideoThread
from pyhavior.gui.dialogs import EnterInfoDialog, EnterCOMDialog
from pyhavior.gui.windows import RecordingWindow, SessionWindow


class RecordFrame(QFrame):
    """
    Frame with functionalities for saving and recording.

    It is also the session controller. A session goes through four phases:

    - idle: nothing is running.
    - preparing: the workers open their devices and report `ready`.
    - running: the shared `SessionClock` has started; the protocol and the
      video recording run against it.
    - stopping: the clock is stopped; waiting for the workers to finish.

    The session ends when the protocol finishes (or on user stop / error),
    never because of the video. `com_port=None` runs the protocol on a
    dry-run board (no Arduino) and `camera_device=None` records no video.
    """

    # Ensure UI updates from worker threads are marshaled to the GUI thread
    stop_enabled = pyqtSignal(bool)
    show_error = pyqtSignal(str, str)
    session_active = pyqtSignal(bool)  # True from session start to the end of finalizing

    PREPARE_TIMEOUT_MS = 20000

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

        self.com_port = default_com_port  # None = no Arduino (dry run)
        self.camera_device = 0  # None = no video

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

        self.protocol = None
        self._phase = 'idle'
        # Kept after a session ends (as a summary) until the next one starts
        self.session_window = None
        # Set by the settings frame: returns why a device is busy, or None
        self.hardware_busy = None
        self._reset_session_state()

        # Destination folder and mouse info must not change mid-session
        self.session_active.connect(
            lambda active: save_frame.setEnabled(not active))

        self._prepare_timer = QTimer(self)
        self._prepare_timer.setSingleShot(True)
        self._prepare_timer.timeout.connect(self._on_prepare_timeout)
        
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

    @property
    def is_recording(self) -> bool:
        return self._phase != 'idle'

    def _reset_session_state(self) -> None:
        """Forget everything about the previous session."""

        self.clock = None
        self.board = None
        self.camera = None
        self.serial_thread = None
        self.recording_thread = None
        self.recording_window = None
        self.arduino_log_path = None

        self._pending = set()  # workers that have not reported ready yet
        self._serial_done = True
        self._video_done = True
        self._user_stopped = False
        self._video_first_t = None  # session time of the first video frame
        self._video_error = None
        self._t_stop = None  # session time at which the session was ended

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

    def handle_no_arduino(self) -> None:
        """Run sessions on a dry-run board (no Arduino attached)."""

        self.com_port = None
        print("Arduino disabled: protocols will run as a dry run")
        if self.info_display_frame:
            self.info_display_frame.update_hardware_info(com_port=None)

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

    def handle_no_camera(self) -> None:
        """Run sessions without recording video."""

        self.camera_device = None
        print("Camera disabled: sessions will run without video")
        if self.info_display_frame:
            self.info_display_frame.update_hardware_info(camera_device=None)

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
        
    # ------------------------------------------------------------------
    # Session control
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        """Build the clock and the workers, and start the prepare phase."""

        if self.is_recording:
            print("Recording is already in progress.")
            return

        busy = self.hardware_busy() if self.hardware_busy else None
        if busy:
            self.show_error.emit("Device in use", busy)
            return

        # A fresh protocol per session: a stopped runner cannot be reused
        try:
            self.init_protocol()
        except Exception as e:
            self.show_error.emit("Protocol Error", str(e))
            return

        self._close_session_window()
        self._reset_session_state()

        base = Path(self.filename)
        stem = f"{base.stem}_{time.strftime('%H%M%S')}"

        self.clock = SessionClock()

        # No COM port means no Arduino: the protocol runs on a dry-run board
        self.board = ArduinoBoard(self.com_port, self.clock)
        self.arduino_log_path = base.with_name(f"{stem}_arduino.csv")

        self.serial_thread = SerialThread(self.board, self.protocol, self.clock)
        self.serial_thread.ready.connect(self._on_serial_ready)
        self.serial_thread.error_occurred.connect(self._on_serial_error)
        self.serial_thread.finished.connect(self._on_serial_finished)
        self._pending.add('serial')
        self._serial_done = False

        if self.camera_device is not None:
            self.camera = Camera(
                self.camera_device,
                self.clock,
                output_path=str(base.with_name(f"{stem}.mp4")))

            self.recording_thread = RecordingVideoThread(
                self.camera, self.clock)
            self.recording_thread.ready.connect(self._on_video_ready)
            self.recording_thread.error_occurred.connect(self._on_video_error)
            self.recording_thread.recording_metadata.connect(
                self.on_recording_metadata)
            self.recording_thread.first_frame.connect(self._on_first_frame)
            self.recording_thread.finished.connect(self._on_video_finished)
            self._pending.add('video')
            self._video_done = False

            self.recording_window = RecordingWindow(
                self.data['Mouse ID'],
                self.data['Behavior test'])
            self.recording_thread.frame_recorded.connect(
                self.recording_window.display_frame)
            # The video window is only a preview: closing it does not stop the session
            self.recording_window.recording_window_closed.connect(
                self._on_video_window_closed)
            self.recording_window.show()

        self.session_window = SessionWindow(
            self.clock,
            self.protocol,
            self.data['Mouse ID'],
            arduino_text=(
                self.com_port if self.com_port else 'dry run (no Arduino)'),
            video_text='starting...' if self.camera else 'off (no camera)')
        self.session_window.stop_requested.connect(self.stop_recording)
        self.session_window.show()

        self._phase = 'preparing'
        self.record_button.setEnabled(False)
        self.stop_enabled.emit(True)
        self.session_active.emit(True)
        self._prepare_timer.start(self.PREPARE_TIMEOUT_MS)

        if self.recording_thread:
            self.recording_thread.start_recording()
        self.serial_thread.start()

    def _worker_ready(self, name: str) -> None:

        if self._phase != 'preparing':
            return
        self._pending.discard(name)
        if not self._pending:
            self._begin_session()

    def _begin_session(self) -> None:
        """All workers are ready: start the clock for everyone at once."""

        self._prepare_timer.stop()
        self._phase = 'running'
        self.clock.start()
        self.session_window.set_phase('running')
        if self.camera:
            self.session_window.set_video_status('recording')

        started = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime(self.clock.t0_wall))
        print(f"Session started: {started} "
              f"(duration {self.protocol.duration}s, "
              f"arduino: {self.com_port or 'dry run'}, "
              f"video: {'yes' if self.camera else 'no'})")

    def _end_session(self) -> None:
        """Stop the clock and every worker. Safe to call repeatedly."""

        if self._phase in ('idle', 'stopping'):
            return

        self._prepare_timer.stop()
        if self.clock.started:
            self._t_stop = self.clock.now()
        self._phase = 'stopping'
        self.session_window.set_phase('stopping')
        self.protocol.request_stop()
        self.clock.stop()
        self._try_finalize()

    def _try_finalize(self) -> None:

        if (self._phase == 'stopping'
                and self._serial_done and self._video_done):
            self._finalize()

    def _finalize(self) -> None:
        """Close everything, save the session files and reset the UI."""

        self._prepare_timer.stop()
        self._close_recording_window()
        self.stop_enabled.emit(False)

        for thread in (self.serial_thread, self.recording_thread):
            if thread:
                thread.wait(2000)

        if self.clock.started:
            try:
                self.board.save_log(str(self.arduino_log_path))
            except Exception as e:
                print(f"Could not save the Arduino log: {e}")
            try:
                self.save_data_to_json()
            except Exception as e:
                self.show_error.emit(
                    "Save Error", f"Could not save session metadata: {e}")
            self._report_video()
        else:
            self._discard_empty_video()

        if self.info_display_frame:
            self.info_display_frame.clear_video_metadata()

        self._phase = 'idle'
        self.record_button.setEnabled(True)
        self.session_active.emit(False)

        if self.session_window:
            if not self.clock.started:
                note = 'Aborted'
            elif self._user_stopped:
                note = 'Stopped by user'
            else:
                note = 'Finished'
            self.session_window.set_phase('finished', note)

        print(f"Recording finished at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    def stop_recording(self) -> None:
        """Ask the user for confirmation and stop the session."""

        if self._phase not in ('preparing', 'running'):
            return

        response = QMessageBox.question(
            self,
            'Stop Recording',
            "Recording is in progress. Are you sure you want to stop?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)

        if response == QMessageBox.Yes and self._phase in ('preparing', 'running'):
            self._user_stopped = True
            self._end_session()
        else:
            print("Recording continues.")

    def shutdown(self) -> None:
        """Non-interactive stop that blocks until the files are closed."""

        if self._phase == 'idle':
            self._close_session_window()
            return

        self._user_stopped = True
        self._end_session()

        for thread in (self.serial_thread, self.recording_thread):
            if thread and not thread.wait(10000):
                print("Warning: a worker thread did not stop in time")

        self._serial_done = True
        self._video_done = True
        self._try_finalize()
        self._close_session_window()

    def _on_prepare_timeout(self) -> None:

        if self._phase != 'preparing':
            return
        missing = ', '.join(sorted(self._pending))
        self.show_error.emit(
            "Session Error", f"Timed out waiting for: {missing}.")
        self._end_session()

    # ------------------------------------------------------------------
    # Worker signals
    # ------------------------------------------------------------------

    def _on_serial_ready(self) -> None:
        self._worker_ready('serial')

    def _on_video_ready(self) -> None:
        self._worker_ready('video')

    def _on_serial_error(self, message: str) -> None:

        print(f"Arduino error: {message}")
        if self._phase in ('preparing', 'running'):
            self.show_error.emit("Arduino Error", message)
            self._end_session()

    def _on_video_error(self, message: str) -> None:

        print(f"Video error: {message}")

        if self._phase == 'preparing' and 'video' in self._pending:
            # The camera is optional: let the user decide
            self._prepare_timer.stop()
            response = QMessageBox.question(
                self,
                'Camera unavailable',
                f"{message}\n\nContinue the session without video?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)

            if self._phase != 'preparing':
                return  # the session ended while the dialog was open

            if response == QMessageBox.Yes:
                self._video_error = message
                self._pending.discard('video')
                self.camera = None
                self.session_window.set_video_status(
                    f'off (camera unavailable: {message})')
                self._close_recording_window()
                self._prepare_timer.start(self.PREPARE_TIMEOUT_MS)
                if not self._pending:
                    self._begin_session()
            else:
                self._end_session()

        elif self._phase == 'running':
            # The protocol is not affected: keep going without video
            self._video_error = message
            self.session_window.set_video_status(f'lost: {message}')
            self.show_error.emit(
                "Video Error",
                f"{message}\n\nThe session continues without video.")

    def _on_first_frame(self, t: float) -> None:
        self._video_first_t = t

    def _on_serial_finished(self) -> None:
        """The protocol is over (duration, user stop or error)."""

        self._serial_done = True
        self._end_session()
        self._try_finalize()

    def _on_video_finished(self) -> None:
        """The video is over; this never ends the session by itself."""

        self._video_done = True
        self._try_finalize()

    def on_recording_metadata(
            self,
            metadata: dict
    ) -> None:
        """Handle recording metadata from RecordingVideoThread"""
        
        # Print metadata properly
        print("Recording metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        # Update info display frame with video metadata
        if self.info_display_frame:
            self.info_display_frame.update_video_metadata(metadata)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_video_window_closed(self) -> None:
        """The video window is a preview: stop feeding it, keep recording."""

        if self.recording_thread and self.recording_window:
            try:
                self.recording_thread.frame_recorded.disconnect(
                    self.recording_window.display_frame)
            except TypeError:
                pass

    def _close_recording_window(self) -> None:

        if self.recording_window:
            # Closing it programmatically must not trigger the handler
            try:
                self.recording_window.recording_window_closed.disconnect(
                    self._on_video_window_closed)
            except TypeError:
                pass
            self.recording_window.close()
            self.recording_window = None

    def _close_session_window(self) -> None:

        if self.session_window:
            self.session_window.force_close()
            self.session_window = None

    def _report_video(self) -> None:

        if not self.camera or not self.camera.video_path:
            return

        video = Path(self.camera.video_path)
        if video.exists():
            file_size = video.stat().st_size
            print(f"Video saved: {video} (Size: {file_size:,} bytes, "
                  f"{self.camera.n_frames_written} frames)")
            if file_size < 1000:  # Very small file might be corrupted
                print("Warning: Video file is very small and might be corrupted")
        else:
            print("Warning: Video file was not created or is missing")

    def _discard_empty_video(self) -> None:
        """Remove the files of a session that never started."""

        if not self.camera or self.camera.n_frames_written:
            return
        for path in (self.camera.video_path, self.camera.timestamps_path):
            try:
                if path and Path(path).exists():
                    Path(path).unlink()
            except OSError as e:
                print(f"Could not remove {path}: {e}")

    def save_data_to_json(self) -> None:
        """Save metadata to a .json file according to predefined formatting."""
        
        filename_path = Path(self.filename)
        base_name = filename_path.stem.split('_')[0]
        json_file_path = (
            filename_path.with_name(base_name).with_suffix('.json'))

        camera = self.camera
        first = self._video_first_t

        experiment_data = {
            'Type': self.data['Behavior test'],
            'Date': date.today().strftime("%Y-%m-%d"),
            'Treatment': self.data['Treatment'],
            'Session Start Time': self.clock.t0_wall,
            'Session Duration': self._t_stop,
            'Stopped By User': self._user_stopped,
            'Serial Start Time': self.clock.t0_wall,
            'Video Start Time': (
                self.clock.to_wall(first) if first is not None else None),
            'Video Start Offset': first,
            'Video File': (
                str(Path(camera.video_path).resolve()) if camera else None),
            'Video Timestamps File': (
                str(Path(camera.timestamps_path).resolve()) if camera else None),
            'Frames Written': camera.n_frames_written if camera else None,
            'Video Error': self._video_error,
            'Camera FPS': camera.fps if camera else None,
            'Frame Width': camera.frame_width if camera else None,
            'Frame Height': camera.frame_height if camera else None,
            'Arduino': 'None' if self.board.dry_run else self.com_port,
            'com Port': self.com_port,
            'Arduino Log File': str(Path(self.arduino_log_path).resolve()),
            'Protocol Events': self.protocol.event_log,
            'camera_index': self.camera_device if camera else None,
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
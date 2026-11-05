""" Session status window: elapsed time and state of a recording session. """

from typing import Optional

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QGridLayout, QLabel, QProgressBar, QPushButton, QWidget
)

from pyhavior.core.clock import SessionClock


def format_time(seconds: float) -> str:
    """mm:ss.t, truncated to tenths so 59.96 never shows as 01:00.0."""

    tenths = int(max(seconds, 0) * 10)
    return f"{tenths // 600:02d}:{(tenths % 600) / 10:04.1f}"


class SessionWindow(QWidget):
    """
    Small window shown for every session, whatever devices are enabled.

    It only displays state. The elapsed time is read from the shared
    `SessionClock`, so it is the same timebase as the video timestamps and
    the Arduino log, and it does not depend on the camera.

    The window cannot be closed while the session is active: the Stop
    button (`stop_requested`) is the way to end it. Once the session is
    over it stays open as a summary until closed.
    """

    stop_requested = pyqtSignal()

    PHASE_TEXT = {
        'preparing': 'Preparing devices...',
        'running': 'RUNNING',
        'stopping': 'Stopping...',
        'finished': 'Finished',
    }
    PHASE_COLOR = {
        'preparing': '#b36b00',
        'running': '#1a7f37',
        'stopping': '#b36b00',
        'finished': '#555555',
    }

    def __init__(
            self,
            clock: SessionClock,
            protocol,
            mouse_id: str,
            arduino_text: str,
            video_text: str
    ) -> None:
        super().__init__()

        self.clock = clock
        self.protocol = protocol
        self.duration = float(protocol.duration)
        self._phase = 'preparing'
        self._frozen: Optional[float] = None  # elapsed time once stopped
        self._closable = False

        self.setWindowTitle(f"Session: {mouse_id}")
        self.setFixedWidth(380)

        layout = QGridLayout(self)

        self.phase_label = QLabel()
        self.phase_label.setAlignment(Qt.AlignCenter)
        phase_font = QFont()
        phase_font.setPointSize(14)
        phase_font.setBold(True)
        self.phase_label.setFont(phase_font)
        layout.addWidget(self.phase_label, 0, 0, 1, 2)

        self.elapsed_label = QLabel(format_time(0))
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        time_font = QFont('Consolas')
        time_font.setStyleHint(QFont.Monospace)
        time_font.setPointSize(32)
        time_font.setBold(True)
        self.elapsed_label.setFont(time_font)
        layout.addWidget(self.elapsed_label, 1, 0, 1, 2)

        self.total_label = QLabel()
        self.total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.total_label, 2, 0, 1, 2)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress, 3, 0, 1, 2)

        info = (
            ('Mouse:', mouse_id),
            ('Protocol:', getattr(protocol, 'protocol_name', '')),
        )
        row = 4
        for name, value in info:
            layout.addWidget(QLabel(name), row, 0)
            layout.addWidget(QLabel(str(value)), row, 1)
            row += 1

        self.arduino_label = QLabel(arduino_text)
        self.video_label = QLabel(video_text)
        self.next_label = QLabel('-')
        self.last_label = QLabel('-')
        for name, widget in (
                ('Arduino:', self.arduino_label),
                ('Video:', self.video_label),
                ('Next event:', self.next_label),
                ('Last event:', self.last_label)):
            layout.addWidget(QLabel(name), row, 0)
            layout.addWidget(widget, row, 1)
            row += 1

        self.hint_label = QLabel('')
        self.hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.hint_label, row, 0, 1, 2)
        row += 1

        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self._on_button)
        layout.addWidget(self.stop_button, row, 0, 1, 2)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(100)

        self.set_phase('preparing')
        self.refresh()

    # ------------------------------------------------------------------
    # State set by the controller
    # ------------------------------------------------------------------

    def set_phase(self, phase: str, note: Optional[str] = None) -> None:

        self._phase = phase
        self.phase_label.setText(note or self.PHASE_TEXT[phase])
        self.phase_label.setStyleSheet(
            f"color: {self.PHASE_COLOR[phase]};")

        if phase in ('stopping', 'finished') and self._frozen is None:
            self._frozen = self.clock.now() if self.clock.started else 0.0

        if phase == 'finished':
            self._closable = True
            self.stop_button.setText('Close')
            self.stop_button.setEnabled(True)
            self.next_label.setText('-')
        else:
            self.stop_button.setText('Stop')
            self.stop_button.setEnabled(phase in ('preparing', 'running'))

        self.hint_label.setText('')
        self.refresh()

    def set_video_status(self, text: str) -> None:
        self.video_label.setText(text)

    def force_close(self) -> None:
        """Close regardless of the phase (application shutdown)."""

        self._closable = True
        self.close()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def elapsed(self) -> float:

        if self._frozen is not None:
            return self._frozen
        return self.clock.now() if self.clock.started else 0.0

    def refresh(self) -> None:

        elapsed = self.elapsed()
        self.elapsed_label.setText(format_time(elapsed))
        self.total_label.setText(f"of {format_time(self.duration)}")
        self.progress.setValue(
            int(min(elapsed / self.duration, 1.0) * 1000)
            if self.duration > 0 else 0)

        if self._phase == 'running':
            upcoming = [
                event[0] for event in self.protocol.sequence
                if event[0] > elapsed]
            self.next_label.setText(
                format_time(min(upcoming)) if upcoming else 'none')

        event_log = self.protocol.event_log
        if event_log:
            last = event_log[-1]
            self.last_label.setText(
                f"{last['description']} ({format_time(last['actual'])})")

    def _on_button(self) -> None:

        if self._phase == 'finished':
            self.close()
        else:
            self.stop_requested.emit()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:

        if self._closable:
            self._timer.stop()
            event.accept()
        else:
            self.hint_label.setText('Use Stop to end the session.')
            event.ignore()

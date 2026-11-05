import csv
import threading
from pathlib import Path
from typing import Optional

import serial

from pyhavior.core.clock import SessionClock


class ArduinoBoard:
    """
    Serial connection to the Arduino, timestamped on a SessionClock.

    It exposes the subset of the `serial.Serial` API that protocols use
    (`write`, `is_open`, `close`, plus `in_waiting` and `readline`), so it
    can be passed to `protocol.run(board)` in place of a raw `Serial`.

    Every outgoing and incoming message is logged with `clock.now()` and
    saved to a CSV by `save_log()`. Messages sent before `clock.start()`
    are not logged.

    With `port=None` the board runs in dry-run mode: nothing is opened or
    sent, but `write` is still timestamped and logged, so a protocol can
    run (and be tested) without hardware.

    Usage:
        board = ArduinoBoard(port, clock)
        board.open()               # prepare phase: may raise serial errors
        clock.wait_for_start()
        protocol.run(board, clock)
        board.close()
        board.save_log(path)
    """

    def __init__(
            self,
            port: Optional[str],
            clock: SessionClock,
            baudrate: int = 9600,
            write_timeout: float = 10,
            timeout: Optional[float] = 0.1
    ) -> None:

        self.port = port
        self.clock = clock
        self.baudrate = baudrate
        self.write_timeout = write_timeout
        self.timeout = timeout  # read timeout (s); None blocks forever
        self._ser: Optional[serial.Serial] = None
        self._dry_open = False
        self._log: list = []  # (session_time, direction, payload)
        self._log_lock = threading.Lock()

    @property
    def dry_run(self) -> bool:
        return self.port is None

    @property
    def is_open(self) -> bool:
        if self.dry_run:
            return self._dry_open
        return self._ser is not None and self._ser.is_open

    @property
    def in_waiting(self) -> int:
        if self.dry_run or not self.is_open:
            return 0
        return self._ser.in_waiting

    def open(self) -> None:
        if self.is_open:
            return
        if self.dry_run:
            self._dry_open = True
            return
        self._ser = serial.Serial(
            self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.write_timeout)
        if not self._ser.is_open:
            self._ser.open()

    def write(self, data: bytes) -> int:
        if not self.is_open:
            raise serial.SerialException("Board is not open")
        n = len(data) if self.dry_run else self._ser.write(data)
        self._record('tx', data)
        return n

    def readline(self) -> bytes:
        if not self.is_open:
            raise serial.SerialException("Board is not open")
        if self.dry_run:
            # Mimic a read timeout with nothing received
            self.clock.wait_for_stop(self.timeout or 0.1)
            return b''
        line = self._ser.readline()
        if line:
            self._record('rx', line)
        return line

    def close(self) -> None:
        self._dry_open = False
        if self._ser is not None:
            try:
                if self._ser.is_open:
                    self._ser.close()
            finally:
                self._ser = None

    def _record(self, direction: str, payload: bytes) -> None:
        if not self.clock.started:
            return
        with self._log_lock:
            self._log.append((self.clock.now(), direction, bytes(payload)))

    @property
    def n_events(self) -> int:
        with self._log_lock:
            return len(self._log)

    def save_log(self, path: str) -> str:
        """Write the event log to CSV and return its path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_lock:
            rows = list(self._log)
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['session_time_s', 'direction', 'payload_hex'])
            for t, direction, payload in rows:
                w.writerow([f"{t:.6f}", direction, payload.hex()])
        return str(path)

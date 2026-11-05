import threading
import time
from typing import Optional


class SessionClock:
    """
    Shared session clock for a recording session used
    to coordinate and timestamp all workers.

    The controller creates one instance and passes it to every worker
    (serial, video, ...). Workers prepare their resources, call
    `wait_for_start()`, and then timestamp everything with `now()`.
    The controller calls `start()` once all workers are ready and
    `stop()` to end the session.

    Durations and offsets use the monotonic `time.perf_counter()`;
    the wall-clock time is captured once at start, only as a label.
    """

    def __init__(self) -> None:
        self._start_event = threading.Event()
        self._stop_event = threading.Event()
        self._t0_perf: Optional[float] = None
        self._t0_wall: Optional[float] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Set t0 and release all workers waiting on `wait_for_start`."""
        with self._lock:
            if self._start_event.is_set():
                return
            self._t0_perf = time.perf_counter()
            self._t0_wall = time.time()
            self._start_event.set()

    def stop(self) -> None:
        """Signal every worker that the session is over. Idempotent."""
        self._stop_event.set()

    def wait_for_start(self, timeout: Optional[float] = None) -> bool:
        """Block until `start()` is called. Returns False on timeout."""
        return self._start_event.wait(timeout)

    def wait_for_stop(self, timeout: Optional[float] = None) -> bool:
        """Block until `stop()` is called. Returns False on timeout."""
        return self._stop_event.wait(timeout)

    @property
    def started(self) -> bool:
        return self._start_event.is_set()

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()

    @property
    def running(self) -> bool:
        return self.started and not self.stopped

    @property
    def t0_wall(self) -> Optional[float]:
        """Wall-clock epoch time at start (for labelling only)."""
        return self._t0_wall

    def now(self) -> float:
        """Seconds elapsed since t0 (monotonic)."""
        if self._t0_perf is None:
            raise RuntimeError("SessionClock has not been started")
        return time.perf_counter() - self._t0_perf

    def to_wall(self, session_time: float) -> float:
        """Convert a `now()` timestamp to wall-clock epoch time."""
        if self._t0_wall is None:
            raise RuntimeError("SessionClock has not been started")
        return self._t0_wall + session_time

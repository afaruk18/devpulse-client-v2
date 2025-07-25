from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from devpulse_client.queue.event_store import EventStore


@dataclass
class HeartbeatTask:
    """
    Periodically logs a heartbeat event at a specified interval.

    This class manages the timing and execution of heartbeat events, ensuring that a heartbeat
    is logged to the EventStore only when the configured interval has elapsed since the last event.
    It tracks the last time a heartbeat was logged and provides a method to trigger a new event
    if appropriate.

    Attributes:
        interval (int): The minimum number of seconds between consecutive heartbeat events.
        _last (float | None): The UNIX timestamp of the last heartbeat event, or None if no event has been logged yet.

    Methods:
        tick(now: float) -> None:
            Checks if the interval has elapsed since the last heartbeat. If so, logs a new
            heartbeat event and updates the last event timestamp.
    """

    interval: int
    _last: float | None = None

    def tick(self, now: float) -> None:
        """
        Log a heartbeat event if the configured interval has elapsed since the last event, or if this is the first run.

        This method should be called periodically (e.g., in a main loop) with the current UNIX timestamp.
        It checks whether the specified interval has passed since the last heartbeat event was logged.
        If so, or if this is the first invocation (i.e., no previous heartbeat has been logged), it logs a new
        heartbeat event to the EventStore with the status "Alive" and updates the internal timestamp.

        Args:
            now (float): The current time as a UNIX timestamp (seconds since epoch).

        Behavior:
            - On the first invocation (when _last is None), logs a heartbeat event immediately.
            - On subsequent invocations, logs a heartbeat event only if at least `interval` seconds have passed
              since the last logged heartbeat.

        Side Effects:
            - Updates the internal _last timestamp to the current time if a heartbeat is logged.
            - Calls EventStore.heartbeat to record the heartbeat event with the current timestamp.
        """
        if self._last is None or now - self._last >= self.interval:
            self._last = now
            EventStore.heartbeat(timestamp=datetime.fromtimestamp(timestamp=now))

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from devpulse_client.queue.event_store import EventStore

from .window_title_provider import WindowTitleProvider


@dataclass
class WindowTrackerTask:
    _last_title: str | None = None
    _window_start: float | None = None
    interval: int = 0

    def tick(self, now: float) -> None:
        """
        Main tracking method that should be called periodically.

        Tracks window focus changes and logs events when the user switches
        to a different window, if the previous window was focused for at
        least the configured interval duration.

        Args:
            now: Current time as UNIX timestamp (seconds since epoch)
        """
        current_title = WindowTitleProvider.current_title()

        if self._has_window_changed(current_title):
            self._handle_window_change(current_title, now)

    def _has_window_changed(self, current_title: str) -> bool:
        """Check if the focused window has changed since last tick."""
        return current_title != self._last_title

    def _handle_window_change(self, new_title: str, now: float) -> None:
        """Handle when user switches to a different window."""
        self._log_previous_window_if_needed(now)
        self._start_tracking_new_window(new_title, now)

    def _log_previous_window_if_needed(self, now: float) -> None:
        """Log the previous window if it was focused long enough."""
        if self._should_log_previous_window(now):
            duration = now - self._window_start
            start_timestamp = datetime.fromtimestamp(self._window_start)
            end_timestamp = datetime.fromtimestamp(now)

            logger.info(
                f"Window '{self._last_title}' met duration threshold | "
                f"Start: {start_timestamp.isoformat()} | "
                f"End: {end_timestamp.isoformat()} | "
                f"Duration: {duration:.1f}s (>= {self.interval}s threshold)"
            )

            self._log_window_event(self._last_title, self._window_start, duration)

    def _should_log_previous_window(self, now: float) -> bool:
        """Check if the previous window should be logged."""
        return self._last_title is not None and self._window_start is not None and now - self._window_start >= self.interval

    def _start_tracking_new_window(self, window_title: str, now: float) -> None:
        """Begin tracking a new window focus session."""
        self._last_title = window_title
        self._window_start = now
        logger.debug(f"Started tracking window: '{window_title}'")

    def _log_window_event(self, window_title: str, start_time: float, duration: float) -> None:
        """Log a window event to the database with start and end timestamps."""
        start_timestamp = datetime.fromtimestamp(start_time)
        end_timestamp = datetime.fromtimestamp(start_time + duration)

        logger.info(f"Logging window event for '{window_title}' | Start: {start_timestamp.isoformat()} | End: {end_timestamp.isoformat()} | Duration: {duration:.1f}s")

        EventStore.log_window_event(window_title, start_time=start_timestamp, end_time=end_timestamp)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from devpulse_client.config.tracker_config import tracker_settings
from devpulse_client.queue.event_store import EventStore
from devpulse_client.tables.activity_table import ActivityEventType

from .idle_detector import IdleDetector
from .screen_lock_detector import ScreenLockDetector


@dataclass
class ActivityStateTask:
    _locked: bool | None = None
    _idle: bool | None = None
    _idle_detector: IdleDetector = IdleDetector()
    _lock_detector: ScreenLockDetector = ScreenLockDetector()

    def tick(self, now: float) -> tuple[bool | None, bool | None]:
        """
        Evaluate and log the current activity state based on screen lock and user idle status.

        This method should be called periodically (e.g., in a main loop) with the current UNIX timestamp.
        It determines whether the screen is locked and whether the user is idle, and logs activity events
        accordingly. The method updates the internal state to reflect the most recent lock and idle status.

        Behavior:
            - On the first invocation (when internal state is uninitialized):
                - If the screen is locked, logs a SCREEN_LOCKED event and sets the state to locked and not idle.
                - If the screen is unlocked, checks idle time:
                    - Logs INACTIVE if the user is idle (idle time >= IDLE_THRESHOLD).
                    - Logs ACTIVE if the user is not idle.
                    - Sets the state to unlocked and updates idle status.
            - On subsequent invocations:
                - If the screen transitions from unlocked to locked, logs a SCREEN_LOCKED event and updates state.
                - If the screen transitions from locked to unlocked, logs a SCREEN_UNLOCKED event, then logs ACTIVE,
                  and updates state.
            - If the screen is unlocked, checks for changes in idle status:
                - If the user transitions from active to idle, logs an INACTIVE event and updates state.
                - If the user transitions from idle to active, logs an ACTIVE event and updates state.

        Args:
            now (float): The current time as a UNIX timestamp (seconds since epoch).

        Returns:
            tuple[bool | None, bool | None]: The current (locked, idle) state after processing.
                - locked: True if the screen is locked, False if unlocked, None if undetermined.
                - idle: True if the user is idle, False if active, None if undetermined.

        Side Effects:
            - Logs activity events to the EventStore as appropriate.
            - Updates the internal _locked and _idle state variables.

        """
        timestamp = datetime.fromtimestamp(now)
        locked = self._lock_detector.is_locked()

        if self._locked is None:
            if locked:
                state = ActivityEventType.SCREEN_LOCKED
                logger.info(f"Logging activity: {state.value}")
                EventStore.log_activity(state.value, timestamp=timestamp)
                self._locked = True
                self._idle = False
            else:
                idle_seconds = self._idle_detector.seconds_idle()
                is_idle = idle_seconds >= tracker_settings.IDLE_THRESHOLD

                state = ActivityEventType.INACTIVE if is_idle else ActivityEventType.ACTIVE
                logger.info(f"Logging activity: {state.value}")
                EventStore.log_activity(state.value, timestamp=timestamp)

                self._locked = False
                self._idle = is_idle
        else:
            if locked and not self._locked:
                state = ActivityEventType.SCREEN_LOCKED
                logger.info(f"Logging activity: {state.value}")
                EventStore.log_activity(state.value, timestamp=timestamp)
                self._locked, self._idle = True, False
            elif not locked and self._locked:
                state = ActivityEventType.SCREEN_UNLOCKED
                logger.info(f"Logging activity: {state.value}")
                EventStore.log_activity(state.value, timestamp=timestamp)
                self._locked = False
                state = ActivityEventType.ACTIVE
                logger.info(f"Logging activity: {state.value}")
                EventStore.log_activity(state.value, timestamp=timestamp)

        if not locked:
            idle_seconds = self._idle_detector.seconds_idle()
            is_idle = idle_seconds >= tracker_settings.IDLE_THRESHOLD

            if self._idle is not None:
                if is_idle and not self._idle:
                    state = ActivityEventType.INACTIVE
                    logger.info(f"Logging activity: {state.value}")
                    EventStore.log_activity(state.value, timestamp=timestamp)
                    self._idle = True
                elif not is_idle and self._idle:
                    state = ActivityEventType.ACTIVE
                    logger.info(f"Logging activity: {state.value}")
                    EventStore.log_activity(state.value, timestamp=timestamp)
                    self._idle = False

        return self._locked, self._idle

import time
from datetime import datetime

from loguru import logger

from devpulse_client.config.tracker_config import tracker_settings
from devpulse_client.core import ActivityStateTask, HeartbeatTask, ScreenshotCapturer, WindowTrackerTask
from devpulse_client.queue.event_store import EventStore
from devpulse_client.tables.activity_table import ActivityEventType

class ActivityTracker:
    """Tracks idle/lock state and captures screenshots, persisting everything to Postgres."""

    SUPPORTED_SYSTEMS: set[str] = {"windows", "darwin", "linux"}

    def __init__(self) -> None:
        self.screenshot_dir = tracker_settings.screenshot_dir
        self.event_store = EventStore()
        self.capturer = ScreenshotCapturer(self.screenshot_dir)
        self.tasks: list = [
            HeartbeatTask(interval=tracker_settings.HEARTBEAT_EVERY),
            WindowTrackerTask(interval=tracker_settings.WINDOW_EVENT_INTERVAL),
            ActivityStateTask(),
        ]

    def run(self) -> None:
        """Main synchronous loop orchestrating all tracking operations."""
        logger.info("Starting activity tracker")

        # Abort early if the platform isn't supported
        if tracker_settings.system not in self.SUPPORTED_SYSTEMS:
            logger.error(f"Unsupported system: {tracker_settings.system}")
            return

        # Log the start of the activity tracker
        start_time = time.time()
        status = ActivityEventType.STARTED.value
        logger.info(f"Logging activity: {status}")
        self.event_store.log_activity(status, timestamp=datetime.fromtimestamp(start_time))
        
        
        
        try:
            while True:
                now = time.time()
                for t in self.tasks:
                    t.tick(now)
                time.sleep(0.1)  # Prevent high CPU usage
                
            
        finally:
            # Log the stop of the activity tracker
            stop_time = time.time()
            status = ActivityEventType.STOPPED.value
            logger.info(f"Logging activity: {status}")
            self.event_store.log_activity(status, timestamp=datetime.fromtimestamp(stop_time))
            
from devpulse_client.config.tracker_config import tracker_settings
from devpulse_client.core import ActivityStateTask, HeartbeatTask, ScreenshotCapturer, WindowTrackerTask, CaptchaTask
from devpulse_client.queue.event_store import EventStore
from devpulse_client.tables.activity_table import ActivityEventType
from datetime import datetime
from loguru import logger
import httpx
import time
from ..models.event_models import EventRequest

class ActivityTracker:
   

    SUPPORTED_SYSTEMS: set[str] = {"windows", "darwin", "linux"}
    SEND_INTERVAL = 5
    
    
    def __init__(self, server_url: str, access_token: str | None = None) -> None:
        self.server_url = server_url
        self.access_token = access_token
        self.screenshot_dir = tracker_settings.screenshot_dir
        self.event_store = EventStore()
        self.capturer = ScreenshotCapturer(self.screenshot_dir)
        self.tasks: list = [
            HeartbeatTask(interval=tracker_settings.HEARTBEAT_EVERY),
            WindowTrackerTask(interval=tracker_settings.WINDOW_EVENT_INTERVAL),
            ActivityStateTask(),
        ]
        
        # Add captcha task if enabled
        if tracker_settings.CAPTCHA_INTERVAL > 0:
            self.tasks.append(
                CaptchaTask(
                    interval=tracker_settings.CAPTCHA_INTERVAL,
                    info_timeout=tracker_settings.CAPTCHA_INFO_TIMEOUT
                )
            )
        self.ingest_endpoint = "/api/ingest/events"

    def run(self) -> None:
        logger.info("Starting activity tracker")

        if tracker_settings.system not in self.SUPPORTED_SYSTEMS:
            logger.error(f"Unsupported system: {tracker_settings.system}")
            return

        start_time = time.time()
        status = ActivityEventType.STARTED.value
        logger.info(f"Logging activity: {status}")
        self.event_store.log_activity(status, timestamp=datetime.fromtimestamp(start_time))
        last_send = start_time
        
        
        
        try:
            while True:
                now = time.time()
                for t in self.tasks:
                    t.tick(now)
                if now - last_send >= self.SEND_INTERVAL:
                    self.send_events()
                    last_send = now
                time.sleep(0.01) 
            
        finally:
            stop_time = time.time()
            status = ActivityEventType.STOPPED.value
            logger.info(f"Logging activity: {status}")
            self.event_store.log_activity(status, timestamp=datetime.fromtimestamp(stop_time))

    def send_events(self) -> None:
        event_request = EventRequest(events = EventStore.get_all_events())
        if len(event_request.events) == 0:
            return
        payload = event_request.model_dump(mode="json")
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        ingest_url = f"{self.server_url}{self.ingest_endpoint}"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(ingest_url, json=payload, headers=headers)
                if response.status_code == 200:
                    EventStore.clear()
                else:
                    logger.error(
                        f"Failed to send events: {response.status_code} {response.text}"
                    )
        except Exception as e:  
            logger.error(f"Error sending events: {e}")
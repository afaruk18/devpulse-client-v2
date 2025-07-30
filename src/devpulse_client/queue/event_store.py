from __future__ import annotations


from collections import deque
from dataclasses import dataclass, asdict
from typing import Deque, Dict, Any, List
from datetime import datetime, timedelta

from devpulse_client.config.tracker_config import tracker_settings
from devpulse_client.tables.activity_table import ActivityEventType


@dataclass()
class _ActivityEvent:
    username: str
    timestamp: datetime
    event: str


@dataclass()
class _HeartbeatEvent:
    username: str
    timestamp: datetime


@dataclass()
class _WindowEvent:
    username: str
    timestamp: datetime
    window_title: str
    duration: float
    start_time: datetime
    end_time: datetime | None

@dataclass()
class _CaptchaCreatedEvent:
    username: str
    timestamp: datetime
    event: str
    expression: str
    correct_answer: int


@dataclass()
class _CaptchaAnsweredEvent:
    username: str
    timestamp: datetime
    event: str
    expression: str
    user_answer: int
    correct_answer: int
    is_correct: bool


@dataclass()
class _CaptchaCancelledEvent:
    username: str
    timestamp: datetime
    event: str
    expression: str
    correct_answer: int

@dataclass()
class _CaptchaNotAnsweredEvent:
    username: str
    timestamp: datetime
    event: str
    expression: str
    correct_answer: int

@dataclass()
class _WrongCaptchaAnswerEvent:
    username: str
    timestamp: datetime
    event: str
    expression: str
    user_answer: int
    correct_answer: int

class EventStore:
    
    _events: Deque[_ActivityEvent | _HeartbeatEvent | _WindowEvent | _CaptchaCreatedEvent | _CaptchaAnsweredEvent | _CaptchaCancelledEvent | _CaptchaNotAnsweredEvent | _WrongCaptchaAnswerEvent] = deque() 
    

    @staticmethod
    def _push(event_obj: object) -> None:  # noqa: D401 – simple helper
       
        EventStore._events.append(asdict(event_obj))
        

    @staticmethod
    def log_activity(label: str, timestamp: datetime | None = None) -> None:  # noqa: D401
        
        ts = timestamp or datetime.now()

        EventStore._push(
            _ActivityEvent(
                username=tracker_settings.user,
                timestamp=ts,
                event=label,
            )
        )

       
    @staticmethod
    def heartbeat(timestamp: datetime | None = None) -> None:
        
        ts = timestamp or datetime.now()
        EventStore._push(
            _HeartbeatEvent(
                username=tracker_settings.user,
                timestamp=ts,
            )
        )

    @staticmethod
    def log_window_event(
        window_title: str,
        timestamp: datetime | None = None,
        duration: float = 0.0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> None:  # noqa: D401
        
        
        
        if start_time is not None and end_time is not None:
            actual_start_time = start_time
            actual_end_time = end_time
            actual_duration = (end_time - start_time).total_seconds()
            
            ts = start_time
        else:
            
            ts = timestamp or datetime.now()
            actual_start_time = ts
            actual_end_time = ts + timedelta(seconds=duration) if duration > 0 else None
            actual_duration = duration

        EventStore._push(
            _WindowEvent(
                username=tracker_settings.user,
                timestamp=ts,
                window_title=window_title,
                duration=actual_duration,
                start_time=actual_start_time,
                end_time=actual_end_time,
            )
        )
    @staticmethod
    def log_captcha_created(expression: str, correct_answer: int, timestamp: datetime | None = None) -> None:
        """Log a captcha creation event."""
        ts = timestamp or datetime.now()
        EventStore._push(
            _CaptchaCreatedEvent(
                username=tracker_settings.user,
                timestamp=ts,
                event="captcha_created",
                expression=expression,
                correct_answer=correct_answer,
            )
        )

    @staticmethod
    def log_captcha_answered(expression: str, user_answer: int, correct_answer: int, is_correct: bool, timestamp: datetime | None = None) -> None:
        """Log a captcha answer event."""
        ts = timestamp or datetime.now()
        EventStore._push(
            _CaptchaAnsweredEvent(
                username=tracker_settings.user,
                timestamp=ts,
                event="captcha_answered",
                expression=expression,
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
            )
        )

    @staticmethod
    def log_captcha_not_answered(expression: str, correct_answer: int, timestamp: datetime | None = None) -> None:
        ts = timestamp or datetime.now()
        EventStore._push(
            _CaptchaNotAnsweredEvent(
                username=tracker_settings.user,
                timestamp=ts,
                event="captcha_not_answered",
                expression=expression,
                correct_answer=correct_answer,
            )
        )

    @staticmethod
    def log_wrong_captcha_answer(expression: str, user_answer: int, correct_answer: int, timestamp: datetime | None = None) -> None:
        ts = timestamp or datetime.now()
        EventStore._push(
            _WrongCaptchaAnswerEvent(
                username=tracker_settings.user,
                timestamp=ts,
                event="wrong_captcha_answer",
                expression=expression,
                user_answer=user_answer,
                correct_answer=correct_answer,
            )
        )

   
    @staticmethod
    def get_all_events() -> List[Dict[str, Any]]:
        
        return list(EventStore._events)

    @staticmethod
    def clear() -> None:
        
        print("Clearing all events from the event store")
        EventStore._events.clear()
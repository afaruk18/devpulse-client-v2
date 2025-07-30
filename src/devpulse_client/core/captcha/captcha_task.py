from __future__ import annotations

import random
import subprocess
import shlex
import asyncio
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from devpulse_client.queue.event_store import EventStore
from devpulse_client.config.tracker_config import tracker_settings


@dataclass
class CaptchaEvent:
    """Event data for captcha challenges."""
    expression: str
    user_answer: int
    correct_answer: int
    is_correct: bool
    creation_time: datetime
    answer_time: datetime
    response_time_ms: int


class CaptchaTask:
    """
    Captcha task that presents math challenges to the user.
    
    This class manages periodic math challenges using zenity dialogs.
    It sends captcha events to the EventStore instead of logging to CSV.
    The task runs asynchronously to avoid blocking other functionality.
    """

    def __init__(self, interval: int = 10, info_timeout: int = 3):
        """
        Initialize the captcha task.
        
        Args:
            interval: Seconds between captcha challenges
            info_timeout: Seconds to show success dialog
        """
        self.interval = interval
        self.info_timeout = info_timeout
        self._last_challenge: Optional[float] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None
        self._captcha_thread: Optional[threading.Thread] = None

    @property
    def _loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Safely access the event loop."""
        return getattr(self, '_loop_attr', None)
    
    @_loop.setter
    def _loop(self, value: Optional[asyncio.AbstractEventLoop]) -> None:
        """Safely set the event loop."""
        self._loop_attr = value

    def tick(self, now: float) -> None:
        """
        Check if it's time for a new captcha challenge.
        
        Args:
            now: Current UNIX timestamp
        """
        if self._last_challenge is None or now - self._last_challenge >= self.interval:
            self._last_challenge = now
            # Run the captcha challenge asynchronously
            self._run_captcha_challenge_async()

    def _run_captcha_challenge_async(self) -> None:
        """Run a single captcha challenge asynchronously."""
        if self._loop is None:
            # Create event loop in a separate thread if not exists
            def run_async_captcha():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                try:
                    loop.run_until_complete(self._captcha_challenge_coroutine())
                finally:
                    loop.close()
                    self._loop = None
            
            self._captcha_thread = threading.Thread(target=run_async_captcha)
            self._captcha_thread.daemon = True
            self._captcha_thread.start()
        else:
            # Schedule the coroutine in the existing loop
            if self._task is None or self._task.done():
                self._task = asyncio.run_coroutine_threadsafe(
                    self._captcha_challenge_coroutine(), self._loop
                )

    async def _captcha_challenge_coroutine(self) -> None:
        """Async coroutine for running a captcha challenge."""
        try:
            # Generate math problem
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            op = random.choice(['+', '-'])
            expr = f"{a} {op} {b}"
            correct_answer = eval(expr)
            
            # Record creation time
            creation_time = datetime.now()

            # Show dialog and get user input asynchronously
            user_answer = await self._show_math_dialog_async(expr)
            
            if user_answer is None:
                # User cancelled, don't log anything
                return

            # Record answer time
            answer_time = datetime.now()
            response_time_ms = int((answer_time - creation_time).total_seconds() * 1000)

            is_correct = (user_answer == correct_answer)
            
            # Log the captcha event with timing information
            self._log_captcha_event(expr, user_answer, correct_answer, is_correct, 
                                  creation_time, answer_time, response_time_ms)

            if is_correct:
                await self._show_success_dialog_async()
            else:
                await self._show_error_dialog_async()

        except Exception as e:
            # Log error but don't crash the application
            print(f"Captcha challenge error: {e}")

    async def _show_math_dialog_async(self, expression: str) -> Optional[int]:
        """
        Show math challenge dialog and get user input (asynchronous version).
        
        Args:
            expression: Math expression to solve
            
        Returns:
            User's answer as integer, or None if cancelled
        """
        cmd = f"zenity --entry --title='Math Challenge' --text='Solve: {expression} = ?'"
        
        try:
            # Run subprocess asynchronously
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode != 0:
                return None  # User cancelled
                
            try:
                return int(stdout.decode().strip())
            except ValueError:
                await self._show_invalid_input_dialog_async()
                return None
                
        except Exception:
            return None

    async def _show_success_dialog_async(self) -> None:
        """Show success dialog (asynchronous version)."""
        cmd = f"zenity --info --timeout={self.info_timeout} --text='Correct! Next challenge soon.'"
        try:
            proc = await asyncio.create_subprocess_exec(*shlex.split(cmd))
            await proc.communicate()
        except Exception:
            pass  # Ignore dialog errors

    async def _show_error_dialog_async(self) -> None:
        """Show error dialog (asynchronous version)."""
        cmd = "zenity --warning --text='Incorrect! Try again.'"
        try:
            proc = await asyncio.create_subprocess_exec(*shlex.split(cmd))
            await proc.communicate()
        except Exception:
            pass  # Ignore dialog errors

    async def _show_invalid_input_dialog_async(self) -> None:
        """Show invalid input dialog (asynchronous version)."""
        cmd = "zenity --error --title='Invalid Input' --text='Please enter a valid integer.'"
        try:
            proc = await asyncio.create_subprocess_exec(*shlex.split(cmd))
            await proc.communicate()
        except Exception:
            pass  # Ignore dialog errors

    def _log_captcha_event(self, expression: str, user_answer: int, correct_answer: int, 
                          is_correct: bool, creation_time: datetime, answer_time: datetime, 
                          response_time_ms: int) -> None:
        """
        Log captcha event to the EventStore with timing information.
        
        Args:
            expression: Math expression that was presented
            user_answer: User's answer
            correct_answer: Correct answer
            is_correct: Whether user's answer was correct
            creation_time: When the captcha was created
            answer_time: When the user answered
            response_time_ms: Response time in milliseconds
        """
        # Create captcha event data with timing information
        event_data = {
            "username": tracker_settings.user,
            "timestamp": creation_time,  # Use creation time as primary timestamp
            "event": "captcha_challenge",
            "expression": expression,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "creation_time": creation_time,
            "answer_time": answer_time,
            "response_time_ms": response_time_ms
        }
        
        # Add to event store
        EventStore._push(event_data)

    def start(self) -> None:
        """Start the captcha task."""
        self._running = True

    def stop(self) -> None:
        """Stop the captcha task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        if self._captcha_thread and self._captcha_thread.is_alive():
            # Note: We can't easily stop the thread, but it will clean up when the loop closes
            pass

    def __getstate__(self):
        """Handle serialization by excluding async-related attributes."""
        state = self.__dict__.copy()
        # Remove async-related attributes that can't be serialized
        state.pop('_loop_attr', None)
        state.pop('_task', None)
        state.pop('_captcha_thread', None)
        return state
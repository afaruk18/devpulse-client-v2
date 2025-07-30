from __future__ import annotations

import random
import subprocess
import shlex
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
    timestamp: datetime


class CaptchaTask:
    """
    Captcha task that presents math challenges to the user.
    
    This class manages periodic math challenges using zenity dialogs.
    It sends captcha events to the EventStore instead of logging to CSV.
    The task runs in a separate thread to avoid blocking other functionality.
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

    def tick(self, now: float) -> None:
        """
        Check if it's time for a new captcha challenge.
        
        Args:
            now: Current UNIX timestamp
        """
        if self._last_challenge is None or now - self._last_challenge >= self.interval:
            self._last_challenge = now
            # Run the captcha challenge in a separate thread to avoid blocking
            import threading
            if not hasattr(self, '_captcha_thread') or not self._captcha_thread.is_alive():
                self._captcha_thread = threading.Thread(target=self._run_captcha_challenge_sync)
                self._captcha_thread.daemon = True
                self._captcha_thread.start()

    def _run_captcha_challenge_sync(self) -> None:
        """Run a single captcha challenge synchronously in a separate thread."""
        try:
            # Generate math problem
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            op = random.choice(['+', '-'])
            expr = f"{a} {op} {b}"
            correct_answer = eval(expr)

            # Log the captcha creation event
            self._log_captcha_created_event(expr, correct_answer)

            # Show dialog and get user input
            user_answer = self._show_math_dialog_sync(expr)
            
            if user_answer is None:
                # User cancelled, log the cancellation
                self._log_captcha_cancelled_event(expr, correct_answer)
                return

            is_correct = (user_answer == correct_answer)
            
            # Log the captcha answer event
            self._log_captcha_answered_event(expr, user_answer, correct_answer, is_correct)

            if is_correct:
                self._show_success_dialog_sync()
            else:
                self._show_error_dialog_sync()

        except Exception as e:
            # Log error but don't crash the application
            print(f"Captcha challenge error: {e}")



    def _show_math_dialog_sync(self, expression: str) -> Optional[int]:
        """
        Show math challenge dialog and get user input (synchronous version).
        
        Args:
            expression: Math expression to solve
            
        Returns:
            User's answer as integer, or None if cancelled
        """
        cmd = f"zenity --entry --title='Math Challenge' --text='Solve: {expression} = ?'"
        
        try:
            proc = subprocess.Popen(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            stdout, _ = proc.communicate()
            
            if proc.returncode != 0:
                return None  # User cancelled
                
            try:
                return int(stdout.decode().strip())
            except ValueError:
                self._show_invalid_input_dialog_sync()
                return None
                
        except Exception:
            return None



    def _show_success_dialog_sync(self) -> None:
        """Show success dialog (synchronous version)."""
        cmd = f"zenity --info --timeout={self.info_timeout} --text='Correct! Next challenge soon.'"
        try:
            subprocess.call(shlex.split(cmd))
        except Exception:
            pass  # Ignore dialog errors

    def _show_error_dialog_sync(self) -> None:
        """Show error dialog (synchronous version)."""
        cmd = "zenity --warning --text='Incorrect! Try again.'"
        try:
            subprocess.call(shlex.split(cmd))
        except Exception:
            pass  # Ignore dialog errors

    def _show_invalid_input_dialog_sync(self) -> None:
        """Show invalid input dialog (synchronous version)."""
        cmd = "zenity --error --title='Invalid Input' --text='Please enter a valid integer.'"
        try:
            subprocess.call(shlex.split(cmd))
        except Exception:
            pass  # Ignore dialog errors



    def _log_captcha_created_event(self, expression: str, correct_answer: int) -> None:
        """
        Log captcha creation event to the EventStore.
        
        Args:
            expression: Math expression that was presented
            correct_answer: Correct answer
        """
        EventStore.log_captcha_created(expression, correct_answer)

    def _log_captcha_answered_event(self, expression: str, user_answer: int, correct_answer: int, is_correct: bool) -> None:
        """
        Log captcha answer event to the EventStore.
        
        Args:
            expression: Math expression that was presented
            user_answer: User's answer
            correct_answer: Correct answer
            is_correct: Whether user's answer was correct
        """
        EventStore.log_captcha_answered(expression, user_answer, correct_answer, is_correct)

    def _log_captcha_cancelled_event(self, expression: str, correct_answer: int) -> None:
        """
        Log captcha cancellation event to the EventStore.
        
        Args:
            expression: Math expression that was presented
            correct_answer: Correct answer
        """
        EventStore.log_captcha_cancelled(expression, correct_answer)

    def _log_captcha_event(self, expression: str, user_answer: int, correct_answer: int, is_correct: bool) -> None:
        """
        Log captcha event to the EventStore (legacy method for backward compatibility).
        
        Args:
            expression: Math expression that was presented
            user_answer: User's answer
            correct_answer: Correct answer
            is_correct: Whether user's answer was correct
        """
        timestamp = datetime.now()
        
        # Create captcha event data
        event_data = {
            "username": tracker_settings.user,
            "timestamp": timestamp,
            "event": "captcha_challenge",
            "expression": expression,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct
        }
        
        # Add to event store
        EventStore._push(event_data)

    def start(self) -> None:
        """Start the captcha task."""
        self._running = True

    def stop(self) -> None:
        """Stop the captcha task."""
        self._running = False
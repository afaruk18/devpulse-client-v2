from __future__ import annotations

import random
import subprocess
import shlex
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from devpulse_client.queue.event_store import EventStore
from devpulse_client.config.tracker_config import tracker_settings
import asyncio
import threading

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
    def __init__(self, interval: int = 10, info_timeout: int = 3):
        
        self.interval = interval
        self.info_timeout = info_timeout
        self._last_challenge: Optional[float] = None
        self._running = True
        self._last_expr = None
        self._last_correct_answer = None
        self._last_answered = True
        self._loop = None
        self._task = None

    def tick(self, now: float) -> None:
      
        if self._last_challenge is None or now - self._last_challenge >= self.interval:
            # If previous captcha was not answered, log event
            if self._last_expr is not None and not self._last_answered:
                EventStore.log_captcha_not_answered(self._last_expr, self._last_correct_answer)
            self._last_challenge = now
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
            
            thread = threading.Thread(target=run_async_captcha)
            thread.daemon = True
            thread.start()
        else:
            # Schedule the coroutine in the existing loop
            if self._task is None or self._task.done():
                self._task = asyncio.run_coroutine_threadsafe(
                    self._captcha_challenge_coroutine(), self._loop
                )
    
    
    async def _captcha_challenge_coroutine(self) -> None:
        while True:
            try:
                # Generate math problem
                a = random.randint(1, 20)
                b = random.randint(1, 20)
                op = random.choice(['+', '-'])
                expr = f"{a} {op} {b}"
                correct_answer = eval(expr)
                self._last_expr = expr
                self._last_correct_answer = correct_answer
                self._last_answered = False
                # Show dialog and get user input
                creation_time = datetime.now()
                user_answer = await self._show_math_dialog_async(expr)
                if user_answer is None:
                    # User cancelled, don't log anything (handled in tick for not answered)
                    return
                answer_time = datetime.now()
                response_time_ms = int((answer_time - creation_time).total_seconds() * 1000)
                is_correct = (user_answer == correct_answer)
                self._log_captcha_event(expr, user_answer, correct_answer, is_correct, creation_time, answer_time, response_time_ms)
                self._last_answered = True
                if is_correct:
                    await self._show_success_dialog_async()
                    break
                else:
                    # Log wrong answer event and re-ask immediately
                    EventStore.log_wrong_captcha_answer(expr, user_answer, correct_answer)
                    await self._show_error_dialog_async()
                    # Loop again to re-ask the same question
            except Exception as e:
                print(f"Captcha challenge error: {e}")
                break



    async def _show_math_dialog_async(self, expression: str) -> Optional[int]:
        
        cmd = f"zenity --entry --title='Math Challenge' --text='Solve: {expression} = ?'"
        
        try:
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
       
        cmd = f"zenity --info --timeout={self.info_timeout} --text='Correct! Next challenge soon.'"
        try:
            proc = await asyncio.create_subprocess_exec(*shlex.split(cmd))
            await proc.communicate()
        except Exception:
            pass  # Ignore dialog errors

    async def _show_error_dialog_async(self) -> None:
        """Show error dialog (synchronous version)."""
        cmd = "zenity --warning --text='Incorrect! Try again.'"
        try:
            proc = await asyncio.create_subprocess_exec(*shlex.split(cmd))
            await proc.communicate()
        except Exception:
            pass  # Ignore dialog errors

    async def _show_invalid_input_dialog_async(self) -> None:
        """Show invalid input dialog (synchronous version)."""
        cmd = "zenity --error --title='Invalid Input' --text='Please enter a valid integer.'"
        try:
            proc = await asyncio.create_subprocess_exec(*shlex.split(cmd))
            await proc.communicate()
        except Exception:
            pass  # Ignore dialog errors



    
            
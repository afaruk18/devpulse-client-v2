from __future__ import annotations

from datetime import datetime
from pathlib import Path

import mss
from PIL import Image

from devpulse_client.config.tracker_config import tracker_settings


class ScreenshotCapturer:
    """Grab screenshots of every monitor and store them in *screenshot_dir*.

    A primary implementation using the *mss* library works on Windows, macOS (darwin)
    and Linux.  If *mss* fails (e.g. missing X server on a head-less Linux box or the
    user hasn’t granted macOS screen-recording permission yet) platform-specific
    fall-backs are attempted so that we at least save a screenshot when possible.
    """

    def __init__(self, screenshot_dir: Path) -> None:
        self._dir = screenshot_dir

    def capture_all_monitors(self) -> None:
        """Capture all monitors for the current platform.

        The method tries the cross-platform *mss* implementation first.  If that
        raises an exception we fall back to a platform-specific routine so that
        we still return a screenshot whenever possible.
        """

        try:
            self._capture_with_mss()
            return
        except Exception:
            # *mss* failed – try a platform-specific strategy before giving up
            system = tracker_settings.system
            if system == "win32":
                self._capture_win32()
            elif system == "darwin":
                self._capture_darwin()
            elif system == "linux":
                self._capture_linux()
            else:
                raise  # Unreachable since checked at app.py

    def _save_image(self, img: Image.Image, monitor_idx: int) -> None:
        """Helper to save *img* into *screenshot_dir* with timestamp naming."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = self._dir / f"monitor{monitor_idx}_{stamp}.{tracker_settings.IMAGE_FORMAT}"

        if tracker_settings.IMAGE_FORMAT.lower() == "jpeg":
            img.save(fname, quality=tracker_settings.IMAGE_QUALITY)
        else:
            img.save(fname)

    def _capture_with_mss(self) -> None:
        """Primary implementation using *mss* – works on all major platforms."""
        with mss.mss() as sct:
            for i, mon in enumerate(sct.monitors[1:], 1):  # skip the "all" monitor 0
                shot = sct.grab(mon)
                img = Image.frombytes("RGB", shot.size, shot.rgb)
                self._save_image(img, i)

    def _capture_win32(self) -> None:
        """Fallback for Windows using Pillow’s *ImageGrab* API. Takes whole screen."""
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab(all_screens=True)
            self._save_image(img, 1)
        except Exception as exc:  # pragma: no cover – final fail
            raise RuntimeError("Unable to capture screen on Windows") from exc

    def _capture_darwin(self) -> None:
        """Fallback for macOS using the *screencapture* CLI utility. Takes whole screen."""
        import subprocess
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name

        # "-x": silent, no sounds; "-m": capture main monitor only
        result = subprocess.run(["screencapture", "-x", path], check=False)
        if result.returncode != 0:
            raise RuntimeError("screencapture failed on macOS")

        img = Image.open(path)
        self._save_image(img, 1)

    def _capture_linux(self) -> None:
        """Fallback for Linux using the *scrot* utility (if installed). Takes whole screen."""
        import subprocess
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name

        result = subprocess.run(["scrot", "--silent", path], check=False)
        if result.returncode != 0:
            raise RuntimeError("scrot failed on Linux – is it installed?")

        img = Image.open(path)
        self._save_image(img, 1)

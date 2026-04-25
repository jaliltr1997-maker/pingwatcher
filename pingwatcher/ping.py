import math
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from .models import PingResult


class PingCommandBuilder:
    @staticmethod
    def build(address: str, timeout_ms: int, packet_count: int) -> list[str]:
        system = platform.system().lower()
        timeout_sec = max(1, math.ceil(timeout_ms / 1000))

        if system == "windows":
            return ["ping", "-n", str(packet_count), "-w", str(timeout_ms), address]

        is_android = "android" in platform.platform().lower() or Path("/system/bin/ping").exists()
        if is_android:
            return ["ping", "-c", str(packet_count), "-W", str(timeout_sec), address]

        if system in {"linux", "darwin"}:
            return ["ping", "-c", str(packet_count), "-W", str(timeout_sec), address]

        return ["ping", address]


class PingParser:
    LATENCY_PATTERNS = [
        r"time[=<]([0-9]+(?:\.[0-9]+)?)",
        r"Average = ([0-9]+)",
        r"avg\/?max\/?mdev = ([0-9]+(?:\.[0-9]+)?)/",
    ]

    @classmethod
    def extract_latency(cls, output: str) -> float | None:
        for pattern in cls.LATENCY_PATTERNS:
            match = re.search(pattern, output, flags=re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    return None
        return None


class PingWorker(QThread):
    result_ready = pyqtSignal(object)
    status_changed = pyqtSignal(str)

    def __init__(self, address: str, interval_ms: int, timeout_ms: int, packet_count: int):
        super().__init__()
        self._address = address
        self._interval_ms = interval_ms
        self._timeout_ms = timeout_ms
        self._packet_count = packet_count
        self._running = True
        self._paused = False

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def run(self) -> None:
        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue

            result = self._ping_once()
            self.result_ready.emit(result)
            self.status_changed.emit(self._build_status_text(result))

            elapsed = 0
            while self._running and elapsed < self._interval_ms:
                time.sleep(0.05)
                elapsed += 50

    def _ping_once(self) -> PingResult:
        command = PingCommandBuilder.build(
            address=self._address,
            timeout_ms=self._timeout_ms,
            packet_count=self._packet_count,
        )

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=(self._timeout_ms / 1000) + 4,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            output = f"{completed.stdout}\n{completed.stderr}"
            success = completed.returncode == 0
            latency = PingParser.extract_latency(output) if success else None
            return PingResult(address=self._address, success=success, latency_ms=latency)
        except subprocess.TimeoutExpired:
            return PingResult(address=self._address, success=False)
        except Exception:
            return PingResult(address=self._address, success=False)

    @staticmethod
    def _build_status_text(result: PingResult) -> str:
        if not result.success:
            return "Disconnected / waiting..."
        if result.latency_ms is None:
            return "Connected"
        return f"Connected · {result.latency_ms:.1f} ms"

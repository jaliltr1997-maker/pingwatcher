from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class PingResult:
    address: str
    success: bool
    latency_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class MonitoringStats:
    total: int = 0
    success: int = 0
    failed: int = 0
    latencies: list[float] = field(default_factory=list)

    def reset(self) -> None:
        self.total = 0
        self.success = 0
        self.failed = 0
        self.latencies.clear()

    def add_result(self, result: PingResult) -> None:
        self.total += 1
        if result.success:
            self.success += 1
            if result.latency_ms is not None:
                self.latencies.append(result.latency_ms)
        else:
            self.failed += 1

    @property
    def success_rate(self) -> str:
        if self.total == 0:
            return "—"
        return f"{(self.success / self.total) * 100:.1f}%"

    @property
    def average(self) -> str:
        if not self.latencies:
            return "—"
        return f"{sum(self.latencies) / len(self.latencies):.1f} ms"

    @property
    def minimum(self) -> str:
        if not self.latencies:
            return "—"
        return f"{min(self.latencies):.1f} ms"

    @property
    def maximum(self) -> str:
        if not self.latencies:
            return "—"
        return f"{max(self.latencies):.1f} ms"

    @property
    def jitter(self) -> str:
        if len(self.latencies) < 2:
            return "—"
        diffs = [abs(self.latencies[i] - self.latencies[i - 1]) for i in range(1, len(self.latencies))]
        return f"{sum(diffs) / len(diffs):.1f} ms"

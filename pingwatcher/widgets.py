from collections import deque

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QWidget


class LatencyGraph(QWidget):
    def __init__(self, max_points: int = 120):
        super().__init__()
        self.setMinimumHeight(180)
        self._max_points = max_points
        self._latencies = deque(maxlen=max_points)
        self._failures = deque(maxlen=max_points)
        self._dark_mode = True

    def set_dark_mode(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        self.update()

    def append(self, latency_ms: float | None, failed: bool) -> None:
        self._latencies.append(latency_ms)
        self._failures.append(failed)
        self.update()

    def clear(self) -> None:
        self._latencies.clear()
        self._failures.clear()
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        background = QColor("#0d1117" if self._dark_mode else "#f6f8fa")
        border = QColor("#30363d" if self._dark_mode else "#d0d7de")
        line_color = QColor("#58a6ff" if self._dark_mode else "#0969da")
        fail_color = QColor("#f85149")

        painter.fillRect(self.rect(), background)
        painter.setPen(QPen(border, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        valid_points = [(idx, value) for idx, value in enumerate(self._latencies) if value is not None]
        if len(valid_points) < 2:
            painter.setPen(QColor("#8b949e"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No ping data yet")
            return

        margin_left, margin_right, margin_top, margin_bottom = 40, 12, 12, 24
        width = self.width() - margin_left - margin_right
        height = self.height() - margin_top - margin_bottom

        maximum = max(value for _, value in valid_points)
        scale_max = max(10.0, maximum * 1.2)

        path = QPainterPath()
        for draw_index, (point_index, latency) in enumerate(valid_points):
            x = margin_left + width * point_index / max(1, len(self._latencies) - 1)
            y = margin_top + height - (latency / scale_max) * height
            if draw_index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.setPen(QPen(line_color, 2))
        painter.drawPath(path)

        painter.setPen(QPen(fail_color, 2))
        for index, is_failed in enumerate(self._failures):
            if not is_failed:
                continue
            x = int(margin_left + width * index / max(1, len(self._latencies) - 1))
            y = margin_top + height // 2
            painter.drawLine(x - 3, y - 3, x + 3, y + 3)
            painter.drawLine(x + 3, y - 3, x - 3, y + 3)


class StatsPanel(QFrame):
    KEYS = ("total", "success", "failed", "success_rate", "avg", "min", "max", "jitter")

    def __init__(self):
        super().__init__()
        grid = QGridLayout(self)
        self._value_labels: dict[str, QLabel] = {}

        for row, key in enumerate(self.KEYS):
            title = QLabel(f"{key.replace('_', ' ').title()}:")
            value = QLabel("—")
            grid.addWidget(title, row, 0)
            grid.addWidget(value, row, 1)
            self._value_labels[key] = value

    def update_values(self, values: dict[str, str]) -> None:
        for key, label in self._value_labels.items():
            label.setText(str(values.get(key, "—")))

from collections import deque

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QWidget


class LatencyGraph(QWidget):
    def __init__(self, max_points: int = 120):
        super().__init__()
        self.setMinimumHeight(220)
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

        bg = QColor("#0D1117" if self._dark_mode else "#F6F8FA")
        border = QColor("#30363D" if self._dark_mode else "#D0D7DE")
        text = QColor("#8B949E" if self._dark_mode else "#57606A")
        line_color = QColor("#58A6FF" if self._dark_mode else "#0969DA")
        fail_color = QColor("#F85149")

        painter.fillRect(self.rect(), bg)
        painter.setPen(QPen(border, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        margin_left, margin_right, margin_top, margin_bottom = 46, 14, 18, 30
        width = self.width() - margin_left - margin_right
        height = self.height() - margin_top - margin_bottom

        painter.setPen(QPen(border, 1, Qt.DashLine))
        for row in range(5):
            y = margin_top + int(height * row / 4)
            painter.drawLine(margin_left, y, margin_left + width, y)

        valid_points = [(idx, value) for idx, value in enumerate(self._latencies) if value is not None]
        if len(valid_points) < 2:
            painter.setPen(text)
            painter.drawText(self.rect(), Qt.AlignCenter, "هنوز داده کافی برای رسم نمودار وجود ندارد")
            return

        max_latency = max(value for _, value in valid_points)
        scale_max = max(10.0, max_latency * 1.2)

        for row in range(5):
            y = margin_top + int(height * row / 4)
            val = scale_max - (scale_max * row / 4)
            painter.setPen(text)
            painter.drawText(2, y + 4, margin_left - 8, 16, Qt.AlignRight | Qt.AlignVCenter, f"{val:.0f}")

        line_path = QPainterPath()
        first = True
        for point_index, latency in valid_points:
            x = margin_left + width * point_index / max(1, len(self._latencies) - 1)
            y = margin_top + height - (latency / scale_max) * height
            if first:
                line_path.moveTo(x, y)
                first = False
            else:
                line_path.lineTo(x, y)

        fill_path = QPainterPath(line_path)
        last_x = margin_left + width * valid_points[-1][0] / max(1, len(self._latencies) - 1)
        fill_path.lineTo(last_x, margin_top + height)
        fill_path.lineTo(margin_left, margin_top + height)
        fill_path.closeSubpath()

        gradient = QLinearGradient(0, margin_top, 0, margin_top + height)
        glow_top = QColor(line_color)
        glow_top.setAlpha(90)
        glow_bottom = QColor(line_color)
        glow_bottom.setAlpha(6)
        gradient.setColorAt(0.0, glow_top)
        gradient.setColorAt(1.0, glow_bottom)

        painter.fillPath(fill_path, gradient)
        painter.setPen(QPen(line_color, 2.2))
        painter.drawPath(line_path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(line_color)
        for point_index, latency in valid_points:
            x = margin_left + width * point_index / max(1, len(self._latencies) - 1)
            y = margin_top + height - (latency / scale_max) * height
            painter.drawEllipse(int(x) - 2, int(y) - 2, 4, 4)

        painter.setPen(QPen(fail_color, 1.8))
        for idx, failed in enumerate(self._failures):
            if not failed:
                continue
            x = int(margin_left + width * idx / max(1, len(self._latencies) - 1))
            y = margin_top + height // 2
            painter.drawLine(x - 4, y - 4, x + 4, y + 4)
            painter.drawLine(x + 4, y - 4, x - 4, y + 4)

        painter.setPen(text)
        painter.drawText(margin_left, self.height() - 8, "زمان ←")


class StatsPanel(QFrame):
    KEYS = ("total", "success", "failed", "success_rate", "avg", "min", "max", "jitter")

    def __init__(self):
        super().__init__()
        grid = QGridLayout(self)
        self._value_labels: dict[str, QLabel] = {}

        for row, key in enumerate(self.KEYS):
            title = QLabel(f"{key.replace('_', ' ').title()}:")
            value = QLabel("—")
            value.setObjectName("statsValue")
            grid.addWidget(title, row, 0)
            grid.addWidget(value, row, 1)
            self._value_labels[key] = value

    def update_values(self, values: dict[str, str]) -> None:
        for key, label in self._value_labels.items():
            label.setText(str(values.get(key, "—")))

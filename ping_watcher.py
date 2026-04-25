import csv
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Ping Watcher Pro"
CONFIG_PATH = Path.home() / ".ping_watcher_settings.json"


class PingResult:
    def __init__(self, address: str, success: bool, latency_ms=None):
        self.address = address
        self.success = success
        self.latency_ms = latency_ms
        self.timestamp = datetime.now()


class Settings:
    def __init__(self):
        self.data = {
            "interval_ms": 1000,
            "timeout_ms": 1200,
            "packet_count": 1,
            "dark_mode": True,
            "notify_connect": True,
            "notify_disconnect": True,
            "show_failed_in_graph": True,
        }
        self.load()

    def load(self):
        if CONFIG_PATH.exists():
            try:
                loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        CONFIG_PATH.write_text(json.dumps(self.data, indent=2), encoding="utf-8")


class PingWorker(QThread):
    result = pyqtSignal(object)
    status = pyqtSignal(str)

    def __init__(self, address: str, interval_ms: int, timeout_ms: int, packet_count: int):
        super().__init__()
        self.address = address
        self.interval_ms = interval_ms
        self.timeout_ms = timeout_ms
        self.packet_count = packet_count
        self._running = True
        self._paused = False

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def _ping_cmd(self):
        system = platform.system().lower()
        # Android typically reports "Linux" + has /system/bin/ping
        is_android = "android" in platform.platform().lower() or Path("/system/bin/ping").exists()

        if system == "windows":
            return ["ping", "-n", str(self.packet_count), "-w", str(self.timeout_ms), self.address]

        if is_android:
            # Android ping accepts -W seconds on most builds
            timeout_sec = max(1, math.ceil(self.timeout_ms / 1000))
            return ["ping", "-c", str(self.packet_count), "-W", str(timeout_sec), self.address]

        if system == "darwin":
            timeout_sec = max(1, math.ceil(self.timeout_ms / 1000))
            return ["ping", "-c", str(self.packet_count), "-W", str(timeout_sec), self.address]

        timeout_sec = max(1, math.ceil(self.timeout_ms / 1000))
        return ["ping", "-c", str(self.packet_count), "-W", str(timeout_sec), self.address]

    @staticmethod
    def _parse_latency(text: str):
        patterns = [
            r"time[=<]([0-9]+(?:\.[0-9]+)?)",  # windows / unix
            r"Average = ([0-9]+)",
            r"avg\/?max\/?mdev = ([0-9]+(?:\.[0-9]+)?)/",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    return None
        return None

    def ping_once(self):
        cmd = self._ping_cmd()
        try:
            cp = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=(self.timeout_ms / 1000) + 4,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            ok = cp.returncode == 0
            latency = self._parse_latency(cp.stdout + "\n" + cp.stderr) if ok else None
            return PingResult(self.address, ok, latency)
        except subprocess.TimeoutExpired:
            return PingResult(self.address, False, None)
        except Exception:
            return PingResult(self.address, False, None)

    def run(self):
        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue
            res = self.ping_once()
            self.result.emit(res)
            self.status.emit(
                f"Connected · {res.latency_ms:.1f} ms" if res.success and res.latency_ms is not None else (
                    "Connected" if res.success else "Disconnected / waiting..."
                )
            )
            slept = 0
            while self._running and slept < self.interval_ms:
                time.sleep(0.05)
                slept += 50


class LatencyGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(180)
        self.values = deque(maxlen=120)
        self.failed = deque(maxlen=120)
        self.dark_mode = True

    def add(self, latency_ms, failed=False):
        self.values.append(latency_ms)
        self.failed.append(failed)
        self.update()

    def clear_data(self):
        self.values.clear()
        self.failed.clear()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QColor("#0d1117" if self.dark_mode else "#f6f8fa")
        border = QColor("#30363d" if self.dark_mode else "#d0d7de")
        line_color = QColor("#58a6ff" if self.dark_mode else "#0969da")
        fail_color = QColor("#f85149")

        p.fillRect(self.rect(), bg)
        p.setPen(QPen(border, 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))

        valid = [(i, v) for i, v in enumerate(self.values) if v is not None]
        if len(valid) < 2:
            p.setPen(QColor("#8b949e"))
            p.drawText(self.rect(), Qt.AlignCenter, "No ping data yet")
            return

        ml, mr, mt, mb = 40, 12, 12, 24
        w = self.width() - ml - mr
        h = self.height() - mt - mb

        max_v = max(v for _, v in valid) * 1.2
        max_v = max(max_v, 10)

        path = QPainterPath()
        for idx, (i, v) in enumerate(valid):
            x = ml + w * i / max(1, len(self.values) - 1)
            y = mt + h - (v / max_v) * h
            if idx == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        p.setPen(QPen(line_color, 2))
        p.drawPath(path)

        p.setPen(QPen(fail_color, 2))
        for i, flag in enumerate(self.failed):
            if flag:
                x = int(ml + w * i / max(1, len(self.values) - 1))
                y = mt + h // 2
                p.drawLine(x - 3, y - 3, x + 3, y + 3)
                p.drawLine(x + 3, y - 3, x - 3, y + 3)


class StatsCard(QFrame):
    def __init__(self):
        super().__init__()
        layout = QGridLayout(self)
        self.labels = {}
        rows = ["total", "success", "failed", "success_rate", "avg", "min", "max", "jitter"]
        for i, k in enumerate(rows):
            key = QLabel(k.replace("_", " ").title() + ":")
            value = QLabel("—")
            value.setObjectName("value")
            layout.addWidget(key, i, 0)
            layout.addWidget(value, i, 1)
            self.labels[k] = value

    def set_values(self, dct):
        for k, v in dct.items():
            if k in self.labels:
                self.labels[k].setText(str(v))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.worker = None
        self.history = []
        self.last_status = None
        self.latencies = []
        self.counters = {"total": 0, "success": 0, "failed": 0}

        self.setWindowTitle(f"{APP_NAME} - Windows/Android Ready")
        self.resize(1100, 760)
        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        top = QHBoxLayout()
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("IP / domain (e.g. 8.8.8.8 or google.com)")
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        self.theme_btn = QPushButton("Toggle Theme")

        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_ping)
        self.pause_btn.clicked.connect(self.pause_resume)
        self.stop_btn.clicked.connect(self.stop_ping)
        self.theme_btn.clicked.connect(self.toggle_theme)

        top.addWidget(self.address_input, 3)
        top.addWidget(self.start_btn)
        top.addWidget(self.pause_btn)
        top.addWidget(self.stop_btn)
        top.addWidget(self.theme_btn)

        self.status = QLabel("Ready")
        self.graph = LatencyGraph()
        self.stats = StatsCard()

        self.tabs = QTabWidget()
        monitor = QWidget()
        monitor_l = QVBoxLayout(monitor)
        monitor_l.addLayout(top)
        monitor_l.addWidget(self.status)
        monitor_l.addWidget(self.graph)
        monitor_l.addWidget(self.stats)

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["Time", "Address", "Status", "Latency"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        hist = QWidget()
        hist_l = QVBoxLayout(hist)
        hist_l.addWidget(self.history_table)
        hist_buttons = QHBoxLayout()
        export_csv = QPushButton("Export CSV")
        export_json = QPushButton("Export JSON")
        clear_hist = QPushButton("Clear")
        export_csv.clicked.connect(self.export_csv)
        export_json.clicked.connect(self.export_json)
        clear_hist.clicked.connect(self.clear_history)
        hist_buttons.addWidget(export_csv)
        hist_buttons.addWidget(export_json)
        hist_buttons.addWidget(clear_hist)
        hist_buttons.addStretch()
        hist_l.addLayout(hist_buttons)

        settings_tab = QWidget()
        set_l = QGridLayout(settings_tab)
        self.interval_spin = QSpinBox(); self.interval_spin.setRange(200, 10000)
        self.timeout_spin = QSpinBox(); self.timeout_spin.setRange(100, 20000)
        self.packet_spin = QSpinBox(); self.packet_spin.setRange(1, 10)
        self.interval_spin.setValue(self.settings.data["interval_ms"])
        self.timeout_spin.setValue(self.settings.data["timeout_ms"])
        self.packet_spin.setValue(self.settings.data["packet_count"])
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        set_l.addWidget(QLabel("Interval (ms)"), 0, 0); set_l.addWidget(self.interval_spin, 0, 1)
        set_l.addWidget(QLabel("Timeout (ms)"), 1, 0); set_l.addWidget(self.timeout_spin, 1, 1)
        set_l.addWidget(QLabel("Packets"), 2, 0); set_l.addWidget(self.packet_spin, 2, 1)
        set_l.addWidget(save_btn, 3, 0, 1, 2)

        self.tabs.addTab(monitor, "Monitor")
        self.tabs.addTab(hist, "History")
        self.tabs.addTab(settings_tab, "Settings")
        outer.addWidget(self.tabs)

    def _valid_address(self, addr: str):
        ip_v4 = re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", addr)
        if ip_v4:
            return all(0 <= int(part) <= 255 for part in addr.split("."))
        domain = re.match(r"^[a-zA-Z0-9.-]+$", addr)
        return bool(domain)

    def start_ping(self):
        addr = self.address_input.text().strip()
        if not addr or not self._valid_address(addr):
            QMessageBox.warning(self, "Invalid input", "Please enter a valid IP or domain.")
            return

        self.stop_ping()
        self.latencies.clear()
        self.counters = {"total": 0, "success": 0, "failed": 0}
        self.graph.clear_data()

        self.worker = PingWorker(
            address=addr,
            interval_ms=self.settings.data["interval_ms"],
            timeout_ms=self.settings.data["timeout_ms"],
            packet_count=self.settings.data["packet_count"],
        )
        self.worker.result.connect(self.on_result)
        self.worker.status.connect(self.status.setText)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

    def pause_resume(self):
        if not self.worker:
            return
        if self.worker._paused:
            self.worker.resume()
            self.pause_btn.setText("Pause")
        else:
            self.worker.pause()
            self.pause_btn.setText("Resume")

    def stop_ping(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.stop_btn.setEnabled(False)

    def _notify(self, title: str, msg: str):
        # Non-blocking fallback (works on Windows/Linux/macOS; Android packaging can replace this later)
        self.status.setText(f"{title}: {msg}")

    def on_result(self, r: PingResult):
        self.counters["total"] += 1
        if r.success:
            self.counters["success"] += 1
            if r.latency_ms is not None:
                self.latencies.append(r.latency_ms)
            self.graph.add(r.latency_ms if r.latency_ms is not None else 0.0, failed=False)
            if self.last_status is False and self.settings.data["notify_connect"]:
                self._notify("Connection restored", r.address)
        else:
            self.counters["failed"] += 1
            self.graph.add(None, failed=self.settings.data["show_failed_in_graph"])
            if self.last_status is True and self.settings.data["notify_disconnect"]:
                self._notify("Connection lost", r.address)

        self.last_status = r.success
        self.history.append(r)
        self._append_history_row(r)
        self._refresh_stats()

    def _append_history_row(self, r: PingResult):
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        vals = [
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            r.address,
            "Success" if r.success else "Failed",
            f"{r.latency_ms:.1f}" if r.latency_ms is not None else "",
        ]
        for c, v in enumerate(vals):
            self.history_table.setItem(row, c, QTableWidgetItem(v))
        if self.history_table.rowCount() > 2500:
            self.history_table.removeRow(0)
            self.history = self.history[-2500:]

    def _refresh_stats(self):
        total = self.counters["total"]
        succ = self.counters["success"]
        fail = self.counters["failed"]
        rate = f"{(succ / total * 100):.1f}%" if total else "—"
        if self.latencies:
            avg = sum(self.latencies) / len(self.latencies)
            jitter = (
                sum(abs(self.latencies[i] - self.latencies[i - 1]) for i in range(1, len(self.latencies)))
                / (len(self.latencies) - 1)
                if len(self.latencies) > 1 else 0
            )
            stats = {
                "total": total,
                "success": succ,
                "failed": fail,
                "success_rate": rate,
                "avg": f"{avg:.1f} ms",
                "min": f"{min(self.latencies):.1f} ms",
                "max": f"{max(self.latencies):.1f} ms",
                "jitter": f"{jitter:.1f} ms",
            }
        else:
            stats = {
                "total": total,
                "success": succ,
                "failed": fail,
                "success_rate": rate,
                "avg": "—",
                "min": "—",
                "max": "—",
                "jitter": "—",
            }
        self.stats.set_values(stats)

    def export_csv(self):
        if not self.history:
            QMessageBox.information(self, "No data", "History is empty.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export CSV", "ping_history.csv", "CSV Files (*.csv)")
        if not filename:
            return
        with open(filename, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "address", "status", "latency_ms"])
            for r in self.history:
                w.writerow([
                    r.timestamp.isoformat(timespec="seconds"),
                    r.address,
                    "success" if r.success else "failed",
                    "" if r.latency_ms is None else f"{r.latency_ms:.1f}",
                ])

    def export_json(self):
        if not self.history:
            QMessageBox.information(self, "No data", "History is empty.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export JSON", "ping_history.json", "JSON Files (*.json)")
        if not filename:
            return
        payload = [
            {
                "timestamp": r.timestamp.isoformat(timespec="seconds"),
                "address": r.address,
                "status": "success" if r.success else "failed",
                "latency_ms": r.latency_ms,
            }
            for r in self.history
        ]
        Path(filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def clear_history(self):
        self.history.clear()
        self.history_table.setRowCount(0)

    def save_settings(self):
        self.settings.data["interval_ms"] = self.interval_spin.value()
        self.settings.data["timeout_ms"] = self.timeout_spin.value()
        self.settings.data["packet_count"] = self.packet_spin.value()
        self.settings.save()
        QMessageBox.information(self, "Saved", f"Settings saved to {CONFIG_PATH}")

    def toggle_theme(self):
        self.settings.data["dark_mode"] = not self.settings.data["dark_mode"]
        self.settings.save()
        self._apply_theme()

    def _apply_theme(self):
        dark = self.settings.data["dark_mode"]
        self.graph.dark_mode = dark
        if dark:
            self.setStyleSheet(
                "QWidget { background:#0d1117; color:#e6edf3; }"
                "QLineEdit, QTableWidget, QTabWidget::pane, QFrame { background:#161b22; border:1px solid #30363d; }"
                "QPushButton { background:#21262d; border:1px solid #30363d; padding:8px 10px; }"
                "QPushButton:hover { background:#30363d; }"
                "QHeaderView::section { background:#1c2230; border:none; color:#8b949e; }"
            )
        else:
            self.setStyleSheet(
                "QWidget { background:#f6f8fa; color:#24292f; }"
                "QLineEdit, QTableWidget, QTabWidget::pane, QFrame { background:#ffffff; border:1px solid #d0d7de; }"
                "QPushButton { background:#f3f4f6; border:1px solid #d0d7de; padding:8px 10px; }"
                "QPushButton:hover { background:#eaeef2; }"
                "QHeaderView::section { background:#ffffff; border:none; color:#57606a; }"
            )
        self.graph.update()

    def closeEvent(self, event):
        self.stop_ping()
        self.settings.save()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

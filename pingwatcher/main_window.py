import csv
import json
import re
from pathlib import Path

from PyQt5.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import MonitoringStats, PingResult
from .ping import PingWorker
from .settings import AppSettings, SettingsStore
from .widgets import LatencyGraph, StatsPanel


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore):
        super().__init__()
        self._settings_store = settings_store
        self._settings = settings_store.load()

        self._worker: PingWorker | None = None
        self._history: list[PingResult] = []
        self._stats = MonitoringStats()
        self._last_online_status: bool | None = None

        self.setWindowTitle("Ping Watcher Pro")
        self.resize(1100, 760)

        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_monitor_tab(), "Monitor")
        self._tabs.addTab(self._build_history_tab(), "History")
        self._tabs.addTab(self._build_settings_tab(), "Settings")

        layout.addWidget(self._tabs)

    def _build_monitor_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        controls = QHBoxLayout()
        self._address_input = QLineEdit()
        self._address_input.setPlaceholderText("IP / domain (e.g. 8.8.8.8 or google.com)")

        self._start_btn = QPushButton("Start")
        self._pause_btn = QPushButton("Pause")
        self._stop_btn = QPushButton("Stop")
        self._theme_btn = QPushButton("Toggle Theme")

        self._start_btn.clicked.connect(self.start_monitoring)
        self._pause_btn.clicked.connect(self.toggle_pause)
        self._stop_btn.clicked.connect(self.stop_monitoring)
        self._theme_btn.clicked.connect(self.toggle_theme)

        self._pause_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)

        controls.addWidget(self._address_input, 3)
        controls.addWidget(self._start_btn)
        controls.addWidget(self._pause_btn)
        controls.addWidget(self._stop_btn)
        controls.addWidget(self._theme_btn)

        self._status_label = QLabel("Ready")
        self._graph = LatencyGraph()
        self._stats_panel = StatsPanel()

        layout.addLayout(controls)
        layout.addWidget(self._status_label)
        layout.addWidget(self._graph)
        layout.addWidget(self._stats_panel)
        return container

    def _build_history_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._history_table = QTableWidget(0, 4)
        self._history_table.setHorizontalHeaderLabels(["Time", "Address", "Status", "Latency"])
        self._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        buttons = QHBoxLayout()
        export_csv_btn = QPushButton("Export CSV")
        export_json_btn = QPushButton("Export JSON")
        clear_btn = QPushButton("Clear")

        export_csv_btn.clicked.connect(self.export_csv)
        export_json_btn.clicked.connect(self.export_json)
        clear_btn.clicked.connect(self.clear_history)

        buttons.addWidget(export_csv_btn)
        buttons.addWidget(export_json_btn)
        buttons.addWidget(clear_btn)
        buttons.addStretch()

        layout.addWidget(self._history_table)
        layout.addLayout(buttons)
        return container

    def _build_settings_tab(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(200, 10000)
        self._interval_spin.setValue(self._settings.interval_ms)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(100, 20000)
        self._timeout_spin.setValue(self._settings.timeout_ms)

        self._packet_spin = QSpinBox()
        self._packet_spin.setRange(1, 10)
        self._packet_spin.setValue(self._settings.packet_count)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)

        grid.addWidget(QLabel("Interval (ms)"), 0, 0)
        grid.addWidget(self._interval_spin, 0, 1)
        grid.addWidget(QLabel("Timeout (ms)"), 1, 0)
        grid.addWidget(self._timeout_spin, 1, 1)
        grid.addWidget(QLabel("Packets"), 2, 0)
        grid.addWidget(self._packet_spin, 2, 1)
        grid.addWidget(save_btn, 3, 0, 1, 2)

        return container

    def start_monitoring(self) -> None:
        address = self._address_input.text().strip()
        if not self._is_valid_address(address):
            QMessageBox.warning(self, "Invalid input", "Please enter a valid IP or domain.")
            return

        self.stop_monitoring()
        self._stats.reset()
        self._history.clear()
        self._history_table.setRowCount(0)
        self._graph.clear()
        self._last_online_status = None

        self._worker = PingWorker(
            address=address,
            interval_ms=self._settings.interval_ms,
            timeout_ms=self._settings.timeout_ms,
            packet_count=self._settings.packet_count,
        )
        self._worker.result_ready.connect(self._handle_result)
        self._worker.status_changed.connect(self._status_label.setText)
        self._worker.start()

        self._start_btn.setEnabled(False)
        self._pause_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)

    def stop_monitoring(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait()
            self._worker = None

        self._start_btn.setEnabled(True)
        self._pause_btn.setEnabled(False)
        self._pause_btn.setText("Pause")
        self._stop_btn.setEnabled(False)

    def toggle_pause(self) -> None:
        if self._worker is None:
            return

        if self._worker._paused:
            self._worker.resume()
            self._pause_btn.setText("Pause")
        else:
            self._worker.pause()
            self._pause_btn.setText("Resume")

    def _handle_result(self, result: PingResult) -> None:
        self._stats.add_result(result)
        self._history.append(result)
        self._append_history_row(result)

        failed = not result.success and self._settings.show_failed_in_graph
        self._graph.append(latency_ms=result.latency_ms, failed=failed)

        self._maybe_notify_status_change(result)
        self._update_stats_panel()

    def _maybe_notify_status_change(self, result: PingResult) -> None:
        if result.success and self._last_online_status is False and self._settings.notify_on_connect:
            self._status_label.setText(f"Connection restored: {result.address}")

        if not result.success and self._last_online_status is True and self._settings.notify_on_disconnect:
            self._status_label.setText(f"Connection lost: {result.address}")

        self._last_online_status = result.success

    def _update_stats_panel(self) -> None:
        self._stats_panel.update_values(
            {
                "total": str(self._stats.total),
                "success": str(self._stats.success),
                "failed": str(self._stats.failed),
                "success_rate": self._stats.success_rate,
                "avg": self._stats.average,
                "min": self._stats.minimum,
                "max": self._stats.maximum,
                "jitter": self._stats.jitter,
            }
        )

    def _append_history_row(self, result: PingResult) -> None:
        row = self._history_table.rowCount()
        self._history_table.insertRow(row)

        values = [
            result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            result.address,
            "Success" if result.success else "Failed",
            f"{result.latency_ms:.1f}" if result.latency_ms is not None else "",
        ]
        for column, value in enumerate(values):
            self._history_table.setItem(row, column, QTableWidgetItem(value))

        max_rows = 2500
        if self._history_table.rowCount() > max_rows:
            self._history_table.removeRow(0)
            self._history = self._history[-max_rows:]

    def save_settings(self) -> None:
        self._settings.interval_ms = self._interval_spin.value()
        self._settings.timeout_ms = self._timeout_spin.value()
        self._settings.packet_count = self._packet_spin.value()
        self._settings_store.save(self._settings)
        QMessageBox.information(self, "Saved", "Settings were saved.")

    def toggle_theme(self) -> None:
        self._settings.dark_mode = not self._settings.dark_mode
        self._settings_store.save(self._settings)
        self._apply_theme()

    def _apply_theme(self) -> None:
        dark = self._settings.dark_mode
        self._graph.set_dark_mode(dark)

        if dark:
            self.setStyleSheet(
                "QWidget { background:#0d1117; color:#e6edf3; }"
                "QLineEdit, QTableWidget, QTabWidget::pane, QFrame { background:#161b22; border:1px solid #30363d; }"
                "QPushButton { background:#21262d; border:1px solid #30363d; padding:8px 10px; }"
                "QPushButton:hover { background:#30363d; }"
                "QHeaderView::section { background:#1c2230; border:none; color:#8b949e; }"
            )
            return

        self.setStyleSheet(
            "QWidget { background:#f6f8fa; color:#24292f; }"
            "QLineEdit, QTableWidget, QTabWidget::pane, QFrame { background:#ffffff; border:1px solid #d0d7de; }"
            "QPushButton { background:#f3f4f6; border:1px solid #d0d7de; padding:8px 10px; }"
            "QPushButton:hover { background:#eaeef2; }"
            "QHeaderView::section { background:#ffffff; border:none; color:#57606a; }"
        )

    def export_csv(self) -> None:
        if not self._history:
            QMessageBox.information(self, "No data", "History is empty.")
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Export CSV", "ping_history.csv", "CSV Files (*.csv)")
        if not filename:
            return

        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "address", "status", "latency_ms"])
            for result in self._history:
                writer.writerow(
                    [
                        result.timestamp.isoformat(timespec="seconds"),
                        result.address,
                        "success" if result.success else "failed",
                        "" if result.latency_ms is None else f"{result.latency_ms:.1f}",
                    ]
                )

    def export_json(self) -> None:
        if not self._history:
            QMessageBox.information(self, "No data", "History is empty.")
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Export JSON", "ping_history.json", "JSON Files (*.json)")
        if not filename:
            return

        payload = [
            {
                "timestamp": result.timestamp.isoformat(timespec="seconds"),
                "address": result.address,
                "status": "success" if result.success else "failed",
                "latency_ms": result.latency_ms,
            }
            for result in self._history
        ]
        Path(filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def clear_history(self) -> None:
        self._history.clear()
        self._history_table.setRowCount(0)

    @staticmethod
    def _is_valid_address(address: str) -> bool:
        if not address:
            return False

        is_ipv4 = re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", address)
        if is_ipv4:
            return all(0 <= int(part) <= 255 for part in address.split("."))

        is_domain = re.match(r"^[a-zA-Z0-9.-]+$", address)
        return bool(is_domain)

    def closeEvent(self, event) -> None:
        self.stop_monitoring()
        self._settings_store.save(self._settings)
        event.accept()

import csv
import json
import re
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
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
    QComboBox,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .dns import DEFAULT_DNS_TARGETS
from .models import MonitoringStats, PingResult
from .ping import PingWorker
from .settings import SettingsStore
from .widgets import LatencyGraph, StatsPanel


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore):
        super().__init__()
        self._settings_store = settings_store
        self._settings = settings_store.load()

        self._worker: PingWorker | None = None
        self._dns_workers: dict[str, PingWorker] = {}
        self._history: list[PingResult] = []
        self._stats = MonitoringStats()
        self._last_online_status: bool | None = None
        self._dns_row_by_address: dict[str, int] = {}

        self.setWindowTitle("Ping Watcher Pro · Visual Network Monitor")
        self.resize(1260, 820)

        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_monitor_tab(), "Monitor")
        self._tabs.addTab(self._build_dns_tab(), "DNS Monitor")
        self._tabs.addTab(self._build_history_tab(), "History")
        self._tabs.addTab(self._build_settings_tab(), "Settings")

        layout.addWidget(self._tabs)

    def _build_monitor_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        controls = QHBoxLayout()
        self._address_input = QLineEdit()
        self._address_input.setPlaceholderText("IP / domain (e.g. 8.8.8.8 or google.com)")

        self._dns_quick_select = QComboBox()
        self._dns_quick_select.addItem("Quick DNS…", "")
        for target in DEFAULT_DNS_TARGETS:
            self._dns_quick_select.addItem(f"{target.name} ({target.address})", target.address)
        self._dns_quick_select.currentIndexChanged.connect(self._apply_quick_dns)

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
        controls.addWidget(self._dns_quick_select, 2)
        controls.addWidget(self._start_btn)
        controls.addWidget(self._pause_btn)
        controls.addWidget(self._stop_btn)
        controls.addWidget(self._theme_btn)

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")

        self._graph = LatencyGraph(max_points=140)
        self._stats_panel = StatsPanel()

        layout.addLayout(controls)
        layout.addWidget(self._status_label)
        layout.addWidget(self._graph)
        layout.addWidget(self._stats_panel)
        return container

    def _build_dns_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        top = QHBoxLayout()
        self._dns_filter_combo = QComboBox()
        self._dns_filter_combo.addItems(["all", "external", "internal"])
        self._dns_filter_combo.currentTextChanged.connect(self._refresh_dns_table)

        self._dns_start_selected_btn = QPushButton("Start Selected")
        self._dns_stop_selected_btn = QPushButton("Stop Selected")
        self._dns_start_all_btn = QPushButton("Start All")
        self._dns_stop_all_btn = QPushButton("Stop All")
        self._dns_load_to_single_btn = QPushButton("Load Selected to Single Monitor")

        self._dns_start_selected_btn.clicked.connect(self._start_selected_dns)
        self._dns_stop_selected_btn.clicked.connect(self._stop_selected_dns)
        self._dns_start_all_btn.clicked.connect(self._start_all_dns)
        self._dns_stop_all_btn.clicked.connect(self._stop_all_dns)
        self._dns_load_to_single_btn.clicked.connect(self._load_selected_dns_to_single)

        top.addWidget(QLabel("Group:"))
        top.addWidget(self._dns_filter_combo)
        top.addStretch()
        top.addWidget(self._dns_start_selected_btn)
        top.addWidget(self._dns_stop_selected_btn)
        top.addWidget(self._dns_start_all_btn)
        top.addWidget(self._dns_stop_all_btn)
        top.addWidget(self._dns_load_to_single_btn)

        self._dns_table = QTableWidget(0, 8)
        self._dns_table.setHorizontalHeaderLabels(
            ["Select", "Name", "Address", "Group", "Status", "Latency", "Last Check", "Mode"]
        )
        self._dns_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._dns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        layout.addLayout(top)
        layout.addWidget(self._dns_table)

        self._refresh_dns_table()
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

    def _apply_quick_dns(self):
        addr = self._dns_quick_select.currentData()
        if addr:
            self._address_input.setText(addr)

    def _refresh_dns_table(self) -> None:
        self._dns_table.setRowCount(0)
        self._dns_row_by_address.clear()

        filter_name = self._dns_filter_combo.currentText() if hasattr(self, "_dns_filter_combo") else "all"
        targets = [
            t for t in DEFAULT_DNS_TARGETS
            if filter_name == "all" or t.group == filter_name
        ]

        for target in targets:
            row = self._dns_table.rowCount()
            self._dns_table.insertRow(row)

            selected_item = QTableWidgetItem()
            selected_item.setCheckState(Qt.Unchecked)
            self._dns_table.setItem(row, 0, selected_item)
            self._dns_table.setItem(row, 1, QTableWidgetItem(target.name))
            self._dns_table.setItem(row, 2, QTableWidgetItem(target.address))
            self._dns_table.setItem(row, 3, QTableWidgetItem(target.group))
            self._dns_table.setItem(row, 4, QTableWidgetItem("Idle"))
            self._dns_table.setItem(row, 5, QTableWidgetItem("—"))
            self._dns_table.setItem(row, 6, QTableWidgetItem("—"))
            self._dns_table.setItem(row, 7, QTableWidgetItem("Single/Batch"))
            self._dns_row_by_address[target.address] = row

    def _selected_dns_addresses(self) -> list[str]:
        addresses: list[str] = []
        for row in range(self._dns_table.rowCount()):
            is_checked = self._dns_table.item(row, 0).checkState() == Qt.Checked
            if is_checked:
                addresses.append(self._dns_table.item(row, 2).text())
        return addresses

    def _start_selected_dns(self) -> None:
        self._start_dns_workers(self._selected_dns_addresses())

    def _stop_selected_dns(self) -> None:
        self._stop_dns_workers(self._selected_dns_addresses())

    def _start_all_dns(self) -> None:
        addresses = [self._dns_table.item(row, 2).text() for row in range(self._dns_table.rowCount())]
        self._start_dns_workers(addresses)

    def _stop_all_dns(self) -> None:
        self._stop_dns_workers(list(self._dns_workers.keys()))

    def _load_selected_dns_to_single(self) -> None:
        addresses = self._selected_dns_addresses()
        if not addresses:
            QMessageBox.information(self, "No selection", "حداقل یک DNS را انتخاب کنید.")
            return
        self._address_input.setText(addresses[0])
        self._tabs.setCurrentIndex(0)

    def _start_dns_workers(self, addresses: list[str]) -> None:
        if not addresses:
            QMessageBox.information(self, "No selection", "هیچ DNS انتخاب نشده است.")
            return

        for address in addresses:
            if address in self._dns_workers:
                continue

            worker = PingWorker(
                address=address,
                interval_ms=self._settings.interval_ms,
                timeout_ms=self._settings.timeout_ms,
                packet_count=self._settings.packet_count,
            )
            worker.result_ready.connect(lambda result, addr=address: self._handle_dns_result(addr, result))
            worker.start()
            self._dns_workers[address] = worker
            self._mark_dns_row_state(address, "Running", QColor("#D29922"), mode="Batch")

    def _stop_dns_workers(self, addresses: list[str]) -> None:
        for address in addresses:
            worker = self._dns_workers.get(address)
            if worker is None:
                continue
            worker.stop()
            worker.wait()
            del self._dns_workers[address]
            self._mark_dns_row_state(address, "Stopped", QColor("#6E7781"), mode="Batch")

    def _handle_dns_result(self, address: str, result: PingResult) -> None:
        self._mark_dns_row_ping_data(address, result)

    def _mark_dns_row_state(self, address: str, text: str, color: QColor, mode: str) -> None:
        row = self._dns_row_by_address.get(address)
        if row is None:
            return
        status_item = self._dns_table.item(row, 4)
        status_item.setText(text)
        status_item.setForeground(color)
        self._dns_table.item(row, 7).setText(mode)

    def _mark_dns_row_ping_data(self, address: str, result: PingResult) -> None:
        row = self._dns_row_by_address.get(address)
        if row is None:
            return

        if result.success:
            self._mark_dns_row_state(address, "Online ✅", QColor("#3FB950"), mode="Batch")
            latency = f"{result.latency_ms:.1f} ms" if result.latency_ms is not None else "—"
        else:
            self._mark_dns_row_state(address, "Offline ❌", QColor("#F85149"), mode="Batch")
            latency = "—"

        self._dns_table.item(row, 5).setText(latency)
        self._dns_table.item(row, 6).setText(result.timestamp.strftime("%H:%M:%S"))

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
                "QWidget { background:#0D1117; color:#E6EDF3; font-family:'Segoe UI'; }"
                "QLineEdit, QTableWidget, QTabWidget::pane, QFrame, QComboBox { background:#161B22; border:1px solid #30363D; border-radius:8px; }"
                "QPushButton { background:#21262D; border:1px solid #30363D; padding:8px 10px; border-radius:8px; }"
                "QPushButton:hover { background:#30363D; }"
                "QHeaderView::section { background:#1C2230; border:none; color:#8B949E; padding:8px; }"
                "QTableWidget::item:selected { background:#1f2937; }"
                "#statusLabel { font-size:14px; font-weight:600; color:#58A6FF; padding:4px; }"
            )
            return

        self.setStyleSheet(
            "QWidget { background:#F6F8FA; color:#24292F; font-family:'Segoe UI'; }"
            "QLineEdit, QTableWidget, QTabWidget::pane, QFrame, QComboBox { background:#FFFFFF; border:1px solid #D0D7DE; border-radius:8px; }"
            "QPushButton { background:#F3F4F6; border:1px solid #D0D7DE; padding:8px 10px; border-radius:8px; }"
            "QPushButton:hover { background:#EAEEF2; }"
            "QHeaderView::section { background:#FFFFFF; border:none; color:#57606A; padding:8px; }"
            "QTableWidget::item:selected { background:#DFEBF7; }"
            "#statusLabel { font-size:14px; font-weight:600; color:#0969DA; padding:4px; }"
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
        self._stop_all_dns()
        self._settings_store.save(self._settings)
        event.accept()

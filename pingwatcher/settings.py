import json
from dataclasses import dataclass, asdict
from pathlib import Path


SETTINGS_PATH = Path.home() / ".ping_watcher_settings.json"


@dataclass(slots=True)
class AppSettings:
    interval_ms: int = 1000
    timeout_ms: int = 1200
    packet_count: int = 1
    dark_mode: bool = True
    notify_on_connect: bool = True
    notify_on_disconnect: bool = True
    show_failed_in_graph: bool = True


class SettingsStore:
    def __init__(self, path: Path = SETTINGS_PATH):
        self._path = path

    def load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            defaults = asdict(AppSettings())
            defaults.update({k: v for k, v in raw.items() if k in defaults})
            return AppSettings(**defaults)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self._path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")

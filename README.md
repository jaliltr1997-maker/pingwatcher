# Ping Watcher Pro

A refreshed PyQt5 network monitor with improved reliability, settings persistence, history export, and a ping engine that handles Windows, Linux/macOS, and Android-style ping flags.

## Features added

- Better ping command compatibility (`Windows`, `Linux/macOS`, `Android`-style environments).
- Safer latency parsing and timeout handling.
- Input validation for IP/domain.
- Stats improvements (success rate, min/max/avg/jitter).
- History export to **CSV** and **JSON**.
- Persistent settings and theme mode.
- Cleaner UX with Monitor / History / Settings tabs.

## Run (desktop)

```bash
pip install PyQt5
python ping_watcher.py
```

## Build for Windows

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name PingWatcher ping_watcher.py
```

Output executable is generated in `dist/PingWatcher.exe`.

## Android path (recommended)

PyQt5 is not the best native Android target. Recommended architecture:

1. Keep this project as the monitoring core and desktop app.
2. Reuse the ping/business logic in a shared Python module.
3. Build Android UI with **Kivy + Buildozer** (or Flutter/React Native app with a Python/HTTP backend).

If you want, the next step can be generating a Kivy Android client that uses the same stats/history model.

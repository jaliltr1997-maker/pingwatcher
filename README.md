# Ping Watcher Pro

نسخه‌ی refactor شده با رویکرد **Clean Code** و معماری ماژولار.

## ساختار جدید پروژه

## نسخه‌های Release

- **Desktop (Python / PyQt):** `v1.1.0`
- **Android (Flutter):** `v1.1.0+2`

- `pingwatcher/models.py`: مدل‌های داده (`PingResult`, `MonitoringStats`)
- `pingwatcher/settings.py`: مدیریت تنظیمات و persistence
- `pingwatcher/ping.py`: ساخت دستور ping + parser + worker thread
- `pingwatcher/widgets.py`: ویجت‌های قابل‌استفاده مجدد (نمودار و پنل آمار)
- `pingwatcher/main_window.py`: orchestration لایه‌ی UI و رفتارها
- `pingwatcher/app.py`: entrypoint اپلیکیشن
- `ping_watcher.py`: اجرای مستقیم برنامه (backward-compatible)

## ویژگی‌ها

- کد تمیزتر، کلاس‌های کوچک‌تر و مسئولیت‌های واضح‌تر.
- سازگاری بهتر ping بین Windows/Linux/macOS و محیط‌های Android-like.
- نمودار latency + نمایش failure marker.
- آمار کامل: total/success/failed/rate/avg/min/max/jitter.
- تاریخچه با خروجی CSV/JSON.
- تنظیمات پایدار در `~/.ping_watcher_settings.json`.

## اجرا

```bash
pip install PyQt5
python ping_watcher.py
```

## ساخت خروجی ویندوز

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name PingWatcher ping_watcher.py
```

## مسیر اندروید

برای Android پیشنهاد می‌شود UI را با Kivy/Buildozer بسازید و منطق مشترک را از ماژول‌های `pingwatcher/` reuse کنید.

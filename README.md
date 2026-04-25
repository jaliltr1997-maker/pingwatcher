# Ping Watcher Pro

نسخه‌ی refactor شده با رویکرد **Clean Code** + UI جذاب‌تر برای مانیتورینگ لحظه‌ای کیفیت اینترنت.

## امکانات جدید مهم

- نمودار حرفه‌ای‌تر latency با:
  - Grid و مقیاس خوانا
  - Fill gradient زیر خط
  - Marker خطاها (X قرمز)
  - نمایش بصری بهتر وضعیت لحظه‌ای
- تب جدید **DNS Monitor** برای مانیتورینگ DNSها به‌صورت:
  - تکی (Load به تب Monitor)
  - چندتایی (Start Selected / Start All)
- لیست آماده DNSهای خارجی و داخلی در یکجا.

## DNSهای پیش‌فرض

- External: Google, Cloudflare, Quad9, OpenDNS
- Internal: Shecan, Radar, Electro, Local Gateway

## ساختار جدید پروژه

- `pingwatcher/models.py`: مدل‌های داده (`PingResult`, `MonitoringStats`)
- `pingwatcher/settings.py`: مدیریت تنظیمات و persistence
- `pingwatcher/ping.py`: ساخت دستور ping + parser + worker thread
- `pingwatcher/widgets.py`: ویجت‌های قابل‌استفاده مجدد (نمودار و پنل آمار)
- `pingwatcher/dns.py`: لیست DNSهای داخلی/خارجی
- `pingwatcher/main_window.py`: orchestration لایه‌ی UI و رفتارها
- `pingwatcher/app.py`: entrypoint اپلیکیشن
- `ping_watcher.py`: اجرای مستقیم برنامه (backward-compatible)

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

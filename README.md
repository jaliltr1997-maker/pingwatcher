# Ping Watcher Pro

این ریپو الان دو بخش دارد:

1. **نسخه دسکتاپ PyQt** (پوشه `pingwatcher/` + `ping_watcher.py`)
2. **نسخه اندروید Flutter** با UI/UX مدرن (پوشه `flutter_ping_watcher/`)

---

## Android (Flutter)

### امکانات نسخه Flutter
- داشبورد جذاب با گرادیانت و کارت‌های شیشه‌ای (Glass UI)
- نمودار latency با `fl_chart`
- مانیتورینگ تکی (Single Host)
- مانیتورینگ DNS تکی/چندتایی (Start Selected / Start All)
- لیست DNSهای داخلی و خارجی
- تاریخچه وضعیت و latency
- تنظیمات (Dark Mode + Interval) با ذخیره در `SharedPreferences`

### اجرا
```bash
cd flutter_ping_watcher
flutter pub get
flutter run
```

### ساخت APK
```bash
cd flutter_ping_watcher
flutter build apk --release
```

---

## Desktop (PyQt)

```bash
pip install PyQt5
python ping_watcher.py
```

## ساخت خروجی ویندوز

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name PingWatcher ping_watcher.py
```

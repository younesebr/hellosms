[app]

# (str) عنوان برنامه
title = HelloSms

# (str) نام بسته
package.name = hellosms

# (str) دامنه بسته
package.domain = org.hellosms

# (str) مسیر کد منبع
source.dir = .

# (list) فایل‌های منبع اصلی
source.include_exts = py,png,jpg,kv,atlas,json,ttf

# (str) فایل اصلی برنامه
source.main = main.py

# (list) فایل‌های اضافی
source.include_patterns = assets/*,images/*.png,fonts/*.ttf

# (list) فایل‌های حذف شده
source.exclude_patterns = license,images/*/*.jpg

# (str) نسخه برنامه
version = 1.0.0

# (str) نسخه کد
version.code = 1

# (list) مجوزهای اندروید
android.permissions = READ_PHONE_STATE,READ_CALL_LOG,SEND_SMS,READ_PHONE_NUMBERS,INTERNET,ACCESS_NETWORK_STATE

# (int) حداقل نسخه SDK اندروید
android.minapi = 30

# (int) نسخه SDK هدف
android.api = 33

# (str) نسخه NDK
android.ndk = 25b

# (bool) استفاده از AndroidX
android.gradle_dependencies = androidx.core:core:1.9.0

# (list) ویژگی‌های اندروید
android.features = android.hardware.telephony

# (str) نام کلاس Activity اصلی
android.entrypoint = org.kivy.android.PythonActivity

# (list) وابستگی‌های پایتون
# android به صورت خودکار توسط buildozer اضافه می‌شود
requirements = python3,kivy>=2.2.0,plyer,pyjnius,android,arabic-reshaper,python-bidi

# (str) نسخه پایتون
python.version3 = 3.11

# (bool) استفاده از Cython
# (str) مسیر Cython
# (str) مسیر Cython compiler

# (list) بسته‌های اضافی
# (list) بسته‌های حذف شده

# (str) آیکون برنامه
# icon.filename = %(source.dir)s/data/icon.png

# (str) آیکون splash
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) جهت‌گیری صفحه
orientation = portrait

# (bool) نمایش تمام صفحه
fullscreen = 0

# (list) فایل‌های اضافی برای کپی
# (list) فایل‌های اضافی برای حذف

# (str) نام کاربری Google Play
# (str) مسیر کلید keystore
# (str) نام کلید keystore
# (str) رمز keystore
# (str) نام کلید
# (str) رمز کلید

[buildozer]

# (int) سطح لاگ
log_level = 2

# (int) سطح لاگ در کنسول
log_level = 2

# (bool) نمایش خروجی کامل
warn_on_root = 1


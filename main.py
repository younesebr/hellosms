"""
برنامه اصلی HelloSms - ارسال خودکار پیامک پس از رد یا از دست رفتن تماس
"""

import json
import os
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivy.logger import Logger
from kivy.clock import Clock
import arabic_reshaper
from bidi.algorithm import get_display

from service import AndroidCallMonitor, send_sms

# مسیر فایل تنظیمات
SETTINGS_FILE = 'hellosms_settings.json'


def get_persian_font():
    """یافتن فونت فارسی مناسب برای سیستم"""
    # لیست فونت‌های فارسی که باید بررسی شوند
    persian_fonts = []
    
    if platform == 'win':
        # فونت‌های فارسی Windows
        windows_fonts = [
            'C:/Windows/Fonts/tahoma.ttf',
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/calibri.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
        ]
        persian_fonts.extend(windows_fonts)
    elif platform == 'android':
        # فونت‌های فارسی Android
        android_fonts = [
            '/system/fonts/NotoSansArabic-Regular.ttf',
            '/system/fonts/DroidSansArabic.ttf',
            '/system/fonts/Roboto-Regular.ttf',
        ]
        persian_fonts.extend(android_fonts)
    
    # بررسی فونت‌های محلی در پوشه fonts
    local_fonts = [
        'fonts/Vazir.ttf',
        'fonts/Tahoma.ttf',
        'fonts/Arial.ttf',
    ]
    persian_fonts.extend(local_fonts)
    
    # بررسی وجود فونت‌ها
    for font_path in persian_fonts:
        if os.path.exists(font_path):
            Logger.info(f"HelloSms: Using Persian font: {font_path}")
            return font_path
    
    # اگر هیچ فونت فارسی پیدا نشد، از فونت پیش‌فرض استفاده می‌شود
    Logger.warning("HelloSms: No Persian font found, using default font")
    return None

# پیکربندی arabic_reshaper برای فارسی بهتر
try:
    # تنظیمات برای reshape بهتر کاراکترهای فارسی
    arabic_reshaper.config['delete_harakat'] = False
    arabic_reshaper.config['delete_tatweel'] = False
    arabic_reshaper.config['support_ligatures'] = True
except:
    pass


class PersianTextInput(TextInput):
    """TextInput سفارشی برای پشتیبانی از فارسی با reshape و bidi خودکار"""
    
    def __init__(self, **kwargs):
        # تنظیم _is_reshaping قبل از super().__init__ تا در on_text قابل استفاده باشد
        self._is_reshaping = False
        
        # ذخیره متن اصلی (بدون reshape و bidi)
        original_text = kwargs.get('text', '')
        
        # برای نمایش: reshape + bidi
        display_text = original_text
        if original_text and re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', original_text):
            try:
                reshaped = arabic_reshaper.reshape(original_text)
                display_text = get_display(reshaped)
            except:
                pass
        
        kwargs['text'] = display_text
        super().__init__(**kwargs)
        # ذخیره متن اصلی (بدون reshape و bidi)
        self._original_text = original_text
    
    def insert_text(self, substring, from_undo=False):
        """درج متن با reshape و bidi خودکار"""
        if self._is_reshaping:
            return super().insert_text(substring, from_undo)
        
        # اضافه کردن به متن اصلی
        cursor_pos = self.cursor[0]
        # تبدیل موقعیت cursor از bidi به موقعیت واقعی (تقریبی)
        # برای سادگی، از موقعیت فعلی استفاده می‌کنیم
        self._original_text = self._original_text[:cursor_pos] + substring + self._original_text[cursor_pos:]
        
        # reshape و bidi کردن substring برای نمایش
        display_substring = substring
        if substring and re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', substring):
            try:
                reshaped = arabic_reshaper.reshape(substring)
                display_substring = get_display(reshaped)
            except:
                pass
        
        result = super().insert_text(display_substring, from_undo)
        
        # reshape و bidi کردن کل متن برای اطمینان از صحت
        Clock.schedule_once(lambda dt: self._reshape_all_text(), 0.1)
        
        return result
    
    def _reshape_all_text(self):
        """reshape و bidi کردن کل متن بر اساس متن اصلی"""
        if self._is_reshaping:
            return
        
        self._is_reshaping = True
        try:
            text = self._original_text
            if text and re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
                try:
                    reshaped = arabic_reshaper.reshape(text)
                    bidi_text = get_display(reshaped)
                    if self.text != bidi_text:
                        cursor_pos = self.cursor[0]
                        self.text = bidi_text
                        # حفظ موقعیت cursor (تقریبی)
                        if cursor_pos <= len(bidi_text):
                            self.cursor = (cursor_pos, 0)
                except Exception as e:
                    Logger.warning(f"HelloSms: Error reshaping all text: {e}")
        finally:
            self._is_reshaping = False
    
    def on_text(self, instance, value):
        """هنگام تغییر متن - reshape و bidi کردن کل متن"""
        # بررسی اینکه _is_reshaping وجود دارد (برای جلوگیری از خطا در زمان اولیه)
        if not hasattr(self, '_is_reshaping'):
            return
        
        if self._is_reshaping:
            return
        
        # اگر متن به صورت دستی تغییر کرد (paste/cut)، متن اصلی را به‌روزرسانی کنیم
        # این کار پیچیده است، پس فقط reshape می‌کنیم
        if value and re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', value):
            Clock.schedule_once(lambda dt: self._reshape_all_text(), 0.1)
    
    def get_original_text(self):
        """دریافت متن اصلی (بدون reshape و bidi)"""
        return self._original_text


class HelloSmsApp(App):
    """کلاس اصلی برنامه"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.call_monitor = None
        self.settings = self.load_settings()
    
    def build(self):
        """ساخت رابط کاربری"""
        # یافتن فونت فارسی
        persian_font = get_persian_font()
        
        # لایه اصلی عمودی
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # عنوان برنامه
        title = Label(
            text=self.reshape_persian('HelloSms - ارسال خودکار پیامک'),
            size_hint_y=None,
            height=60,
            font_size='24sp',
            bold=True,
            halign='right',
            valign='middle',
            text_size=(None, None)
        )
        if persian_font:
            title.font_name = persian_font
        title.bind(texture_size=title.setter('size'))
        main_layout.add_widget(title)
        
        # سوییچ فعال/غیرفعال
        switch_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        switch_label = Label(
            text=self.reshape_persian('سرویس فعال:'),
            size_hint_x=0.7,
            halign='right',
            valign='middle',
            text_size=(None, None)
        )
        if persian_font:
            switch_label.font_name = persian_font
        switch_label.bind(texture_size=switch_label.setter('size'))
        
        self.service_switch = Switch(
            active=self.settings.get('sms_enabled', {}).get('value', True),
            size_hint_x=0.3
        )
        self.service_switch.bind(active=self.on_switch_active)
        
        switch_layout.add_widget(switch_label)
        switch_layout.add_widget(self.service_switch)
        main_layout.add_widget(switch_layout)
        
        # برچسب متن پیامک
        sms_label = Label(
            text=self.reshape_persian('متن پیامک:'),
            size_hint_y=None,
            height=40,
            halign='right',
            valign='middle',
            text_size=(None, None)
        )
        if persian_font:
            sms_label.font_name = persian_font
        sms_label.bind(texture_size=sms_label.setter('size'))
        main_layout.add_widget(sms_label)
        
        # ورودی متن پیامک با اسکرول
        scroll = ScrollView(size_hint_y=0.4)
        default_text = self.settings.get('sms_text', {}).get('value', 
            'سلام، متأسفانه نتواستم تماس شما را پاسخ دهم. لطفاً در زمان دیگری تماس بگیرید.')
        # استفاده از PersianTextInput برای پشتیبانی از فارسی
        # reshape کردن خودکار متن فارسی انجام می‌شود
        self.sms_text_input = PersianTextInput(
            text=default_text,  # متن اصلی را نگه می‌داریم
            multiline=True,
            size_hint_y=None,
            font_size='16sp',
            padding=[10, 10, 10, 10]
        )
        if persian_font:
            self.sms_text_input.font_name = persian_font
        self.sms_text_input.bind(minimum_height=self.sms_text_input.setter('height'))
        scroll.add_widget(self.sms_text_input)
        main_layout.add_widget(scroll)
        
        # دکمه ذخیره
        save_button = Button(
            text=self.reshape_persian('ذخیره تنظیمات'),
            size_hint_y=None,
            height=50,
            font_size='18sp'
        )
        if persian_font:
            save_button.font_name = persian_font
        save_button.bind(on_press=self.save_settings)
        main_layout.add_widget(save_button)
        
        # برچسب وضعیت
        self.status_label = Label(
            text=self.reshape_persian('وضعیت: آماده'),
            size_hint_y=None,
            height=40,
            halign='right',
            valign='middle',
            text_size=(None, None),
            color=(0, 1, 0, 1)
        )
        if persian_font:
            self.status_label.font_name = persian_font
        self.status_label.bind(texture_size=self.status_label.setter('size'))
        main_layout.add_widget(self.status_label)
        
        # راه‌اندازی مانیتورینگ تماس
        if platform == 'android':
            Clock.schedule_once(self.setup_call_monitor, 1)
        else:
            self.status_label.text = self.reshape_persian('وضعیت: فقط در اندروید کار می‌کند')
            self.status_label.color = (1, 0.5, 0, 1)
        
        return main_layout
    
    def reshape_persian(self, text):
        """تبدیل متن فارسی برای نمایش صحیح - reshape + bidi"""
        if not text:
            return text
        try:
            # اگر متن فقط انگلیسی یا عدد است، reshape نکن
            if not re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
                return text
            
            # reshape کردن متن فارسی
            reshaped_text = arabic_reshaper.reshape(text)
            # تبدیل به bidi برای نمایش راست به چپ
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception as e:
            Logger.warning(f"HelloSms: Error reshaping text: {e}")
            return text
    
    def load_settings(self):
        """بارگذاری تنظیمات از فایل JSON"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            Logger.error(f"HelloSms: Error loading settings: {e}")
        
        # تنظیمات پیش‌فرض
        return {
            'sms_enabled': {'value': True},
            'sms_text': {'value': 'سلام، متأسفانه نتواستم تماس شما را پاسخ دهم. لطفاً در زمان دیگری تماس بگیرید.'}
        }
    
    def save_settings(self, instance):
        """ذخیره تنظیمات در فایل JSON"""
        try:
            self.settings['sms_enabled'] = {'value': self.service_switch.active}
            # ذخیره متن اصلی (بدون reshape) از PersianTextInput
            if hasattr(self.sms_text_input, 'get_original_text'):
                text_value = self.sms_text_input.get_original_text()
            else:
                text_value = self.sms_text_input.text
            self.settings['sms_text'] = {'value': text_value}
            
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            
            self.status_label.text = self.reshape_persian('وضعیت: تنظیمات ذخیره شد')
            self.status_label.color = (0, 1, 0, 1)
            
            Logger.info("HelloSms: Settings saved")
            
            # به‌روزرسانی مانیتورینگ
            if platform == 'android':
                self.setup_call_monitor()
        
        except Exception as e:
            Logger.error(f"HelloSms: Error saving settings: {e}")
            self.status_label.text = self.reshape_persian('وضعیت: خطا در ذخیره تنظیمات')
            self.status_label.color = (1, 0, 0, 1)
    
    def on_switch_active(self, instance, value):
        """هنگام تغییر وضعیت سوییچ"""
        self.settings['sms_enabled'] = {'value': value}
        if platform == 'android':
            self.setup_call_monitor()
    
    def setup_call_monitor(self, dt=None):
        """راه‌اندازی مانیتورینگ تماس"""
        try:
            if platform != 'android':
                return
            
            # بررسی اینکه سرویس فعال است یا نه
            if not self.settings.get('sms_enabled', {}).get('value', True):
                if self.call_monitor:
                    # غیرفعال کردن مانیتورینگ
                    self.call_monitor = None
                    self.status_label.text = self.reshape_persian('وضعیت: سرویس غیرفعال')
                    self.status_label.color = (1, 0.5, 0, 1)
                return
            
            # بررسی اینکه متن پیامک خالی نباشد
            sms_text = self.settings.get('sms_text', {}).get('value', '')
            if not sms_text.strip():
                self.status_label.text = self.reshape_persian('وضعیت: لطفاً متن پیامک را وارد کنید')
                self.status_label.color = (1, 0, 0, 1)
                return
            
            # راه‌اندازی مانیتورینگ
            if not self.call_monitor:
                self.call_monitor = AndroidCallMonitor(self.on_missed_call)
                self.status_label.text = self.reshape_persian('وضعیت: سرویس فعال و آماده')
                self.status_label.color = (0, 1, 0, 1)
                Logger.info("HelloSms: Call monitor started")
        
        except Exception as e:
            Logger.error(f"HelloSms: Error setting up call monitor: {e}")
            self.status_label.text = self.reshape_persian(f'وضعیت: خطا - {str(e)}')
            self.status_label.color = (1, 0, 0, 1)
    
    def on_missed_call(self, phone_number):
        """هنگام رد یا از دست رفتن تماس"""
        try:
            # بررسی اینکه سرویس فعال است
            if not self.settings.get('sms_enabled', {}).get('value', True):
                return
            
            # دریافت متن پیامک
            sms_text = self.settings.get('sms_text', {}).get('value', '')
            if not sms_text.strip():
                Logger.warning("HelloSms: SMS text is empty")
                return
            
            # ارسال پیامک
            if phone_number:
                success = send_sms(phone_number, sms_text)
                if success:
                    Logger.info(f"HelloSms: SMS sent to {phone_number}")
                    # به‌روزرسانی وضعیت در UI
                    Clock.schedule_once(
                        lambda dt: setattr(
                            self.status_label, 
                            'text', 
                            self.reshape_persian(f'وضعیت: پیامک ارسال شد به {phone_number}')
                        ), 
                        0
                    )
                else:
                    Logger.error(f"HelloSms: Failed to send SMS to {phone_number}")
                    Clock.schedule_once(
                        lambda dt: setattr(
                            self.status_label, 
                            'text', 
                            self.reshape_persian('وضعیت: خطا در ارسال پیامک')
                        ), 
                        0
                    )
        
        except Exception as e:
            Logger.error(f"HelloSms: Error in on_missed_call: {e}")


if __name__ == '__main__':
    HelloSmsApp().run()

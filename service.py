"""
سرویس اندروید برای مانیتورینگ تماس‌ها و ارسال پیامک
"""

from kivy.logger import Logger
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method
    from android import mActivity
    
    Context = autoclass('android.content.Context')
    TelephonyManager = autoclass('android.telephony.TelephonyManager')
    PhoneStateListener = autoclass('android.telephony.PhoneStateListener')
    SmsManager = autoclass('android.telephony.SmsManager')
    Intent = autoclass('android.content.Intent')
    BroadcastReceiver = autoclass('android.content.BroadcastReceiver')
    IntentFilter = autoclass('android.content.IntentFilter')


class AndroidCallMonitor:
    """کلاس مانیتورینگ تماس برای اندروید"""
    
    def __init__(self, callback):
        """
        Args:
            callback: تابعی که هنگام رد یا از دست رفتن تماس فراخوانی می‌شود
                     باید یک شماره تلفن را به عنوان آرگومان دریافت کند
        """
        self.callback = callback
        self.last_state = None
        self.last_number = None
        self.call_answered = False
        
        if platform == 'android':
            self.setup_monitor()
    
    def setup_monitor(self):
        """تنظیم مانیتورینگ تماس"""
        try:
            telephony_manager = mActivity.getSystemService(Context.TELEPHONY_SERVICE)
            
            class CallStateListener(PythonJavaClass):
                __javaclass__ = 'android/telephony/PhoneStateListener'
                
                def __init__(self, monitor):
                    super().__init__()
                    self.monitor = monitor
                
                @java_method('(I)V')
                def onCallStateChanged(self, state, phone_number):
                    """هنگام تغییر وضعیت تماس"""
                    try:
                        # حالت‌های تماس
                        IDLE = 0
                        RINGING = 1
                        OFFHOOK = 2
                        
                        if state == RINGING:
                            # تماس ورودی
                            number = str(phone_number) if phone_number else None
                            self.monitor.last_number = number
                            self.monitor.call_answered = False
                            Logger.info(f"HelloSms: Incoming call from {number}")
                        
                        elif state == OFFHOOK:
                            # تماس پاسخ داده شده
                            self.monitor.call_answered = True
                            Logger.info("HelloSms: Call answered")
                        
                        elif state == IDLE:
                            # تماس قطع شده
                            if self.monitor.last_number and not self.monitor.call_answered:
                                # تماس پاسخ داده نشده یا رد شده
                                Logger.info(f"HelloSms: Missed/rejected call from {self.monitor.last_number}")
                                # فراخوانی callback
                                if self.monitor.callback:
                                    self.monitor.callback(self.monitor.last_number)
                            
                            # ریست کردن وضعیت
                            self.monitor.call_answered = False
                            self.monitor.last_number = None
                    
                    except Exception as e:
                        Logger.error(f"HelloSms: Error in CallStateListener: {e}")
            
            self.listener = CallStateListener(self)
            telephony_manager.listen(self.listener, PhoneStateListener.LISTEN_CALL_STATE)
            Logger.info("HelloSms: Call monitor initialized")
        
        except Exception as e:
            Logger.error(f"HelloSms: Error setting up call monitor: {e}")


def send_sms(phone_number, message):
    """
    ارسال پیامک
    
    Args:
        phone_number: شماره تلفن گیرنده
        message: متن پیامک
    
    Returns:
        bool: True در صورت موفقیت، False در غیر این صورت
    """
    if platform != 'android':
        Logger.warning("HelloSms: Cannot send SMS on non-Android platform")
        return False
    
    try:
        # پاکسازی شماره تلفن
        phone_number = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # دریافت SmsManager
        sms_manager = SmsManager.getDefault()
        
        # تقسیم پیامک در صورت طولانی بودن
        parts = sms_manager.divideMessage(message)
        
        if len(parts) == 1:
            # پیامک کوتاه
            sms_manager.sendTextMessage(
                phone_number,
                None,
                message,
                None,
                None
            )
        else:
            # پیامک طولانی
            sms_manager.sendMultipartTextMessage(
                phone_number,
                None,
                parts,
                None,
                None
            )
        
        Logger.info(f"HelloSms: SMS sent successfully to {phone_number}")
        return True
    
    except Exception as e:
        Logger.error(f"HelloSms: Error sending SMS: {e}")
        return False





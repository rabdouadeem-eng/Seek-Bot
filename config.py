# app/config.py
# ============================================================
# 🔍 Seek Bot - إعدادات البوت
# ============================================================

import os
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env (إن وجد)
load_dotenv()

class Config:
    """
    جميع إعدادات البوت في مكان واحد.
    يمكنك تغيير أي قيمة هنا أو عبر ملف .env
    """
    
    # ==========================================================
    # 1. إعدادات Binance (اختيارية – للقراءة العامة فقط)
    # ==========================================================
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    
    # ==========================================================
    # 2. إعدادات التداول الأساسية
    # ==========================================================
    SYMBOL = os.getenv("SYMBOL", "BTCUSDT")          # الزوج (BTCUSDT, ETHUSDT, XAUUSDT...)
    TIMEFRAME = os.getenv("TIMEFRAME", "15m")        # الفترة الزمنية (1m, 5m, 15m, 1h, 4h, 1d)
    LOOKBACK_CANDLES = int(os.getenv("LOOKBACK_CANDLES", "20"))   # عدد الشموع لتحديد القمة/القاع
    
    # ==========================================================
    # 3. إدارة المخاطر
    # ==========================================================
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.02"))   # 2% من الرصيد لكل صفقة
    MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5")) # الحد الأقصى للصفقات اليومية
    MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.05")) # 5% حد الخسارة اليومي
    
    # ==========================================================
    # 4. رأس المال الابتدائي (للتداول الورقي)
    # ==========================================================
    INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000"))  # 10,000 دولار افتراضي
    
    # ==========================================================
    # 5. إعدادات الاستراتيجية (القيعان والقمم)
    # ==========================================================
    MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.6"))   # الحد الأدنى لثقة الإشارة (0.6 = 60%)
    RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
    MACD_FAST = int(os.getenv("MACD_FAST", "12"))
    MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
    MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))
    BB_PERIOD = int(os.getenv("BB_PERIOD", "20"))
    BB_STD = float(os.getenv("BB_STD", "2.0"))
    
    # ==========================================================
    # 6. إعدادات متقدمة (اختيارية)
    # ==========================================================
    BREAK_EVEN_AFTER = float(os.getenv("BREAK_EVEN_AFTER", "0.005"))  # 0.5% ربح لنقل SL إلى نقطة الدخول
    TRAILING_STOP = os.getenv("TRAILING_STOP", "false").lower() == "true"  # تفعيل/إلغاء الوقف المتحرك
    TRAILING_DISTANCE = float(os.getenv("TRAILING_DISTANCE", "0.01"))  # 1% مسافة الوقف المتحرك

# اختبار سريع للتحقق من الإعدادات
if __name__ == "__main__":
    print("="*50)
    print("🔍 Seek Bot - الإعدادات الحالية")
    print("="*50)
    print(f"الزوج: {Config.SYMBOL}")
    print(f"الإطار الزمني: {Config.TIMEFRAME}")
    print(f"عدد الشموع لتحديد القمة/القاع: {Config.LOOKBACK_CANDLES}")
    print(f"نسبة المخاطرة: {Config.RISK_PER_TRADE*100}%")
    print(f"الحد الأقصى للصفقات اليومية: {Config.MAX_TRADES_PER_DAY}")
    print(f"الرصيد الابتدائي: ${Config.INITIAL_BALANCE:.2f}")
    print(f"حد الخسارة اليومي: {Config.MAX_DAILY_LOSS_PCT*100}%")
    print("="*50)
    print("✅ تم تحميل الإعدادات بنجاح.")

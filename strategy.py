# app/strategy.py
# ============================================================
# 🔍 Seek Bot - استراتيجية القيعان والقمم (Swing Trading)
# ============================================================

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 1. دوال حساب المؤشرات الفنية (بدون مكتبات خارجية)
# ============================================================

def calculate_rsi(df, period=14):
    """
    حساب مؤشر القوة النسبية (RSI).
    RSI أقل من 30 = منطقة تشبع بيعي (إشارة شراء محتملة)
    RSI أعلى من 70 = منطقة تشبع شرائي (إشارة بيع محتملة)
    """
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]  # نرجع قيمة آخر شمعة فقط

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    حساب مؤشر MACD.
    - تقاطع إيجابي (MACD يقطع Signal للأعلى) = إشارة صعود.
    - تقاطع سلبي (MACD يقطع Signal للأسفل) = إشارة هبوط.
    """
    exp1 = df['close'].ewm(span=fast).mean()
    exp2 = df['close'].ewm(span=slow).mean()
    macd = exp1 - exp2
    macd_signal = macd.ewm(span=signal).mean()
    return macd.iloc[-1], macd_signal.iloc[-1]  # نرجع قيم آخر شمعة

def calculate_bollinger(df, period=20, std_dev=2):
    """
    حساب نطاقات بولينجر (Bollinger Bands).
    - السعر عند النطاق السفلي = منطقة شراء محتملة.
    - السعر عند النطاق العلوي = منطقة بيع محتملة.
    """
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return lower.iloc[-1], sma.iloc[-1], upper.iloc[-1]  # نرجع قيم آخر شمعة

# ============================================================
# 2. دوال التعرف على أنماط الشموع (Candlestick Patterns)
# ============================================================

def is_bullish_candle(row):
    """شمعة خضراء (الإغلاق أعلى من الافتتاح)"""
    return row['close'] > row['open']

def is_bearish_candle(row):
    """شمعة حمراء (الإغلاق أقل من الافتتاح)"""
    return row['close'] < row['open']

# ============================================================
# 3. الدالة الرئيسية: كشف الإشارة
# ============================================================

def detect_signal(df, lookback=20, config=None):
    """
    كشف إشارة شراء (Buy) أو بيع (Sell) بناءً على:
    1. القيعان والقمم المحلية (آخر lookback شمعة).
    2. تأكيد من المؤشرات (RSI, MACD, Bollinger).
    
    Args:
        df (pd.DataFrame): بيانات الشموع (يجب أن تحتوي على open, high, low, close).
        lookback (int): عدد الشموع لتحديد القاع/القمة (افتراضي 20).
        config (object): كائن الإعدادات (اختياري، لقراءة نسب المؤشرات).
    
    Returns:
        dict: {
            "type": "BUY" أو "SELL" أو None,
            "entry": سعر الدخول,
            "sl": وقف الخسارة,
            "tp": جني الأرباح,
            "confidence": درجة الثقة (0-1)
        }
    """
    if df is None or len(df) < lookback + 5:
        return None
    
    # استخراج آخر شمعة كاملة
    last = df.iloc[-1]
    price = last['close']
    
    # تحديد القاع والقمة المحليين (آخر lookback شمعة)
    recent_low = df['low'].tail(lookback).min()
    recent_high = df['high'].tail(lookback).max()
    
    # حساب المؤشرات (بناءً على البيانات كاملة)
    rsi = calculate_rsi(df)
    macd, macd_signal = calculate_macd(df)
    bb_lower, _, bb_upper = calculate_bollinger(df)
    
    # ============================================================
    # منطق القاع (شراء)
    # ============================================================
    # الشرط الأول: السعر قريب من القاع أو لامسه
    price_at_bottom = price <= recent_low * 1.002
    # الشرط الثاني: شمعة انعكاسية صاعدة
    bullish_candle = is_bullish_candle(last)
    # الشرط الثالث: تأكيد من المؤشرات (واحد على الأقل)
    indicators_buy = (rsi < 30) or (macd > macd_signal) or (price <= bb_lower)
    
    is_buy = price_at_bottom and bullish_candle and indicators_buy
    
    # ============================================================
    # منطق القمة (بيع)
    # ============================================================
    # الشرط الأول: السعر قريب من القمة أو لامسها
    price_at_top = price >= recent_high * 0.998
    # الشرط الثاني: شمعة انعكاسية هابطة
    bearish_candle = is_bearish_candle(last)
    # الشرط الثالث: تأكيد من المؤشرات (واحد على الأقل)
    indicators_sell = (rsi > 70) or (macd < macd_signal) or (price >= bb_upper)
    
    is_sell = price_at_top and bearish_candle and indicators_sell
    
    # ============================================================
    # بناء النتيجة وحساب درجة الثقة
    # ============================================================
    confidence = 0.5  # ثقة ابتدائية
    
    if is_buy:
        # زيادة الثقة مع كل شرط متحقق
        if rsi < 30: confidence += 0.3
        elif rsi < 40: confidence += 0.15
        if macd > macd_signal: confidence += 0.1
        if price <= bb_lower: confidence += 0.1
        if bullish_candle: confidence += 0.05
        
        confidence = min(confidence, 1.0)
        
        return {
            "type": "BUY",
            "entry": round(price, 2),
            "sl": round(recent_low - 5, 2),   # وقف خسارة تحت القاع بـ 5 نقاط
            "tp": round(recent_high, 2),      # الهدف الأول هو القمة المحلية
            "confidence": round(confidence, 2)
        }
    
    elif is_sell:
        # زيادة الثقة مع كل شرط متحقق
        if rsi > 70: confidence += 0.3
        elif rsi > 60: confidence += 0.15
        if macd < macd_signal: confidence += 0.1
        if price >= bb_upper: confidence += 0.1
        if bearish_candle: confidence += 0.05
        
        confidence = min(confidence, 1.0)
        
        return {
            "type": "SELL",
            "entry": round(price, 2),
            "sl": round(recent_high + 5, 2),  # وقف خسارة فوق القمة بـ 5 نقاط
            "tp": round(recent_low, 2),       # الهدف الأول هو القاع المحلي
            "confidence": round(confidence, 2)
        }
    
    # في حالة عدم وجود إشارة واضحة
    return None

# ============================================================
# 4. اختبار سريع (للتحقق من صحة الدوال)
# ============================================================

if __name__ == "__main__":
    # إنشاء بيانات وهمية (محاكاة لآخر 30 شمعة)
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=30, freq='15min')
    df = pd.DataFrame({
        'open': np.random.normal(100, 1, 30),
        'high': np.random.normal(101, 1, 30),
        'low': np.random.normal(99, 1, 30),
        'close': np.random.normal(100, 1, 30),
    }, index=dates)
    
    # محاكاة قاع وقمة
    df.iloc[-1, df.columns.get_loc('close')] = 98.5   # قاع وهمي
    df.iloc[-1, df.columns.get_loc('open')] = 99.0
    df.iloc[-1, df.columns.get_loc('high')] = 99.0
    df.iloc[-1, df.columns.get_loc('low')] = 98.0
    
    print("="*50)
    print("🧪 اختبار استراتيجية القيعان والقمم")
    print("="*50)
    
    signal = detect_signal(df, lookback=10)
    
    if signal:
        print(f"📊 الإشارة: {signal['type']}")
        print(f"   الدخول: {signal['entry']}")
        print(f"   SL: {signal['sl']}")
        print(f"   TP: {signal['tp']}")
        print(f"   الثقة: {signal['confidence']*100:.0f}%")
    else:
        print("⏸️ لا توجد إشارة حالياً")
    
    print("\n✅ تم الانتهاء من الاختبار")

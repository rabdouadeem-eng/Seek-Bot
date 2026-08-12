# app/strategy.py (معدل – شروط أقل صرامة)
import pandas as pd
import numpy as np

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_macd(df, fast=12, slow=26, signal=9):
    exp1 = df['close'].ewm(span=fast).mean()
    exp2 = df['close'].ewm(span=slow).mean()
    macd = exp1 - exp2
    macd_signal = macd.ewm(span=signal).mean()
    return macd.iloc[-1], macd_signal.iloc[-1]

def calculate_bollinger(df, period=20, std_dev=2):
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return lower.iloc[-1], sma.iloc[-1], upper.iloc[-1]

def is_bullish(row):
    return row['close'] > row['open']

def is_bearish(row):
    return row['close'] < row['open']

def detect_signal(df, lookback=10):  # ← خفضناها من 20 إلى 10
    if df is None or len(df) < lookback + 5:
        return None
    
    last = df.iloc[-1]
    price = last['close']
    
    recent_low = df['low'].tail(lookback).min()
    recent_high = df['high'].tail(lookback).max()
    
    rsi = calculate_rsi(df)
    macd, macd_signal = calculate_macd(df)
    bb_lower, _, bb_upper = calculate_bollinger(df)
    
    # شروط الشراء (مخففة)
    buy = (price <= recent_low * 1.005 and is_bullish(last) and
           (rsi < 40 or macd > macd_signal or price <= bb_lower))  # ← RSI < 40 بدلاً من 30
    
    # شروط البيع (مخففة)
    sell = (price >= recent_high * 0.995 and is_bearish(last) and
            (rsi > 60 or macd < macd_signal or price >= bb_upper))  # ← RSI > 60 بدلاً من 70
    
    confidence = 0.4  # ← خفضنا الثقة الأساسية
    if buy:
        if rsi < 40: confidence += 0.3
        elif rsi < 50: confidence += 0.15
        if macd > macd_signal: confidence += 0.1
        if price <= bb_lower: confidence += 0.1
        return {
            "type": "BUY",
            "entry": round(price, 2),
            "sl": round(recent_low - 5, 2),
            "tp": round(recent_high, 2),
            "confidence": round(min(confidence, 1.0), 2)
        }
    elif sell:
        if rsi > 60: confidence += 0.3
        elif rsi > 50: confidence += 0.15
        if macd < macd_signal: confidence += 0.1
        if price >= bb_upper: confidence += 0.1
        return {
            "type": "SELL",
            "entry": round(price, 2),
            "sl": round(recent_high + 5, 2),
            "tp": round(recent_low, 2),
            "confidence": round(min(confidence, 1.0), 2)
        }
    return None

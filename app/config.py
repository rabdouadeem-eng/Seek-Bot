# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # مصدر البيانات (binance أو yahoo)
    DATA_SOURCE = os.getenv("DATA_SOURCE", "binance")

    # الرمز (BTCUSDT لـ Binance، XAUUSD=X لـ Yahoo)
    SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
    TIMEFRAME = os.getenv("TIMEFRAME", "15m")
    LOOKBACK_CANDLES = int(os.getenv("LOOKBACK_CANDLES", "20"))

    # إدارة المخاطر
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.02"))
    MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5"))
    INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000"))
    MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.6"))

    # إعدادات Yahoo (اختياري)
    SYMBOL_YAHOO = os.getenv("SYMBOL_YAHOO", "XAUUSD=X")
    

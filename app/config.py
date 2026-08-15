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

    # إعدادات OANDA (فوركس/ذهب حقيقي عبر REST API — موثوق أكثر من Yahoo على Render)
    OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
    OANDA_ENV = os.getenv("OANDA_ENV", "practice")  # practice أو live
    SYMBOL_OANDA = os.getenv("SYMBOL_OANDA", "XAU_USD")

    # إعدادات Twelve Data (فوركس/ذهب — بديل OANDA غير المتاح في الجزائر)
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    SYMBOL_TWELVEDATA = os.getenv("SYMBOL_TWELVEDATA", "XAU/USD")
    

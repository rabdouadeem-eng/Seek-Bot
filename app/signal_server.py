# app/signal_server.py
# ============================================================
# 🔍 Seek Bot - خادم الإشارات الموحد (متعدد المصادر)
# ============================================================

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .config import Config
from .broker import BinanceBroker, YahooBroker
from .strategy import detect_signal

logger = logging.getLogger(__name__)

class DataSourceManager:
    def __init__(self):
        self.binance = BinanceBroker()
        self.yahoo = YahooBroker()
        self.cache = {}
    
    def get_broker(self, symbol: str):
        # يختار المصدر تلقائياً حسب الرمز
        if "USDT" in symbol or (symbol.endswith("USD") and not "=" in symbol):
            return self.binance
        return self.yahoo
    
    def get_candles(self, symbol: str, timeframe: str = "1h", limit: int = 30):
        broker = self.get_broker(symbol)
        try:
            df = broker.get_candles(symbol, timeframe, limit)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"فشل جلب {symbol} من المصدر الأساسي: {e}")
        
        fallback_broker = self.yahoo if isinstance(broker, BinanceBroker) else self.binance
        try:
            df = fallback_broker.get_candles(symbol, timeframe, limit)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.error(f"فشل جلب {symbol} من المصدر البديل: {e}")
        
        return None


class SignalEngine:
    def __init__(self):
        self.data_manager = DataSourceManager()
        self.last_signals = {}
    
    def get_signal(self, symbol: str, lookback: int = None) -> dict:
        if lookback is None:
            lookback = Config.LOOKBACK_CANDLES
        
        df = self.data_manager.get_candles(symbol, Config.TIMEFRAME, lookback + 10)
        if df is None or df.empty:
            return {
                "symbol": symbol,
                "type": "HOLD",
                "entry": 0,
                "sl": 0,
                "tp": 0,
                "confidence": 0.0,
                "reason": "بيانات غير كافية",
                "timestamp": datetime.now().isoformat()
            }
        
        sig = detect_signal(df, lookback)
        if sig:
            sig["symbol"] = symbol
            sig["timestamp"] = datetime.now().isoformat()
            sig["reason"] = self._generate_reason(sig, df)
            self.last_signals[symbol] = sig
            return sig
        else:
            return {
                "symbol": symbol,
                "type": "HOLD",
                "entry": 0,
                "sl": 0,
                "tp": 0,
                "confidence": 0.0,
                "reason": "لا توجد إشارة واضحة",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_all_signals(self, symbols: List[str] = None) -> Dict[str, dict]:
        # ✅ قائمة موحدة تضم الفوركس، الذهب، والعملات الرقمية
        if symbols is None:
            symbols = [
                "EURUSD=X", "GBPUSD=X", "XAUUSD=X",   # Yahoo
                "BTCUSDT", "ETHUSDT", "BNBUSDT",      # Binance
                "SOLUSDT", "XRPUSDT"                  # Binance إضافية
            ]
        
        results = {}
        for sym in symbols:
            results[sym] = self.get_signal(sym)
        
        return results
    
    def _generate_reason(self, sig: dict, df) -> str:
        if sig["type"] == "BUY":
            reasons = []
            last = df.iloc[-1]
            recent_low = df['low'].tail(Config.LOOKBACK_CANDLES).min()
            if last['close'] <= recent_low * 1.005:
                reasons.append("السعر قريب من القاع")
            if sig.get("confidence", 0) > 0.7:
                reasons.append("ثقة عالية")
            return " + ".join(reasons) if reasons else "إشارة شراء"
        
        elif sig["type"] == "SELL":
            reasons = []
            last = df.iloc[-1]
            recent_high = df['high'].tail(Config.LOOKBACK_CANDLES).max()
            if last['close'] >= recent_high * 0.995:
                reasons.append("السعر قريب من القمة")
            if sig.get("confidence", 0) > 0.7:
                reasons.append("ثقة عالية")
            return " + ".join(reasons) if reasons else "إشارة بيع"
        
        return "لا توجد إشارة"


signal_engine = SignalEngine()

def get_signal_response(symbol: str):
    return signal_engine.get_signal(symbol)

def get_all_signals_response():
    return signal_engine.get_all_signals()


async def auto_update_signals(interval: int = 60):
    while True:
        try:
            symbols = [
                "EURUSD=X", "GBPUSD=X", "XAUUSD=X",
                "BTCUSDT", "ETHUSDT", "BNBUSDT",
                "SOLUSDT", "XRPUSDT"
            ]
            signal_engine.get_all_signals(symbols)
            logger.info(f"🔄 تم تحديث الإشارات تلقائياً: {len(symbols)} رمز")
        except Exception as e:
            logger.error(f"❌ خطأ في التحديث التلقائي: {e}")
        await asyncio.sleep(interval)

def start_auto_updater():
    import threading
    def run():
        asyncio.run(auto_update_signals(60))
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    logger.info("🚀 تم تشغيل المحدّث التلقائي للإشارات (متعدد المصادر)")

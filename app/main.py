# app/main.py
# ============================================================
# 🔍 Seek Bot - الخادم الرئيسي مع خادم إشارات متكامل
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging
from .config import Config
from .broker import DataBroker  # ✅ استيراد DataBroker بدلاً من YahooBroker و BinanceBroker
from .strategy import detect_signal
from .paper_trading import PaperTrading

# استيراد خادم الإشارات
from .signal_server import SignalEngine, start_auto_updater

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Seek Bot - Signal Server", version="2.0")

# ============================================================
# 1. تهيئة المصادر
# ============================================================

# ✅ استخدام DataBroker (يجمع بين Binance و CoinCap، أو Yahoo حسب DATA_SOURCE)
broker = DataBroker()
# ✅ اختيار الرمز الصحيح حسب المصدر
if broker.data_source == "twelvedata":
    symbol = Config.SYMBOL_TWELVEDATA
elif broker.data_source == "oanda":
    symbol = Config.SYMBOL_OANDA
elif broker.data_source == "yahoo":
    symbol = Config.SYMBOL_YAHOO
else:
    symbol = Config.SYMBOL

logger.info(f"📡 المصدر: DataBroker ({broker.data_source}) | الرمز: {symbol}")

# تهيئة التداول الورقي
paper = PaperTrading(Config.INITIAL_BALANCE)

# تهيئة محرك الإشارات (للمعالجة المتعددة)
signal_engine = SignalEngine()

# ============================================================
# 2. نماذج البيانات
# ============================================================

class TradeRequest(BaseModel):
    symbol: str
    side: str
    entry: float          # ✅ كان ناقص — /trade كان يستعمله فيطيح بخطأ
    volume: float = 0
    sl: float
    tp: float

# ============================================================
# 3. نقاط النهاية - الواجهة الرئيسية
# ============================================================

@app.get("/")
def root():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>🔍 Seek Bot</title></head>
    <body style="font-family: sans-serif; background: #0E1116; color: #E6EDF3; padding: 20px;">
        <h1>🔍 Seek Bot - خادم الإشارات</h1>
        <p>✅ البوت يعمل على <strong>DataBroker</strong></p>
        <hr>
        <h3>📊 نقاط النهاية المتاحة:</h3>
        <ul>
            <li><a href="/signal" style="color: #FBBF24;">/signal</a> - الإشارة الحالية</li>
            <li><a href="/signals/all" style="color: #FBBF24;">/signals/all</a> - جميع الإشارات</li>
            <li><a href="/signal/BTCUSDT" style="color: #FBBF24;">/signal/BTCUSDT</a> - إشارة لرمز معين</li>
            <li><a href="/candles" style="color: #FBBF24;">/candles</a> - بيانات الشموع</li>
            <li><a href="/status" style="color: #FBBF24;">/status</a> - حالة المحفظة</li>
        </ul>
        <p style="color: #8B949E; margin-top: 20px;">⚡ جميع الصفقات وهمية (Paper Trading)</p>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ============================================================
# 4. نقاط النهاية - الإشارات (الأساسية)
# ============================================================

@app.get("/signal")
def get_signal():
    """إشارة للرمز الافتراضي"""
    df = broker.get_candles(symbol, Config.TIMEFRAME, Config.LOOKBACK_CANDLES + 10)
    logger.info(f"📊 عدد الشموع: {len(df) if df is not None else 0}")
    if df is None:
        return {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}
    sig = detect_signal(df, Config.LOOKBACK_CANDLES)
    return sig or {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}

@app.get("/signal/{symbol}")
def get_signal_by_symbol(symbol: str):
    """إشارة لرمز معين (مثل /signal/BTCUSDT)"""
    return signal_engine.get_signal(symbol)

@app.get("/signals/all")
def get_all_signals():
    """جلب إشارات لجميع الأزواج المدعومة دفعة واحدة"""
    return signal_engine.get_all_signals()

@app.get("/signals/crypto")
def get_crypto_signals():
    """✅ إشارات الكريبتو (BTC + meme coins) — منفصلة عن الرمز الرئيسي"""
    return signal_engine.get_crypto_signals()

# ============================================================
# 5. نقاط النهاية - البيانات والصفقات
# ============================================================

@app.get("/candles")
def get_candles():
    """جلب آخر 30 شمعة للرمز الافتراضي"""
    df = broker.get_candles(symbol, Config.TIMEFRAME, 30)
    if df is None or df.empty:
        return {"candles": []}
    candles = []
    for index, row in df.iterrows():
        candles.append({
            "time": index.strftime("%H:%M"),
            "open": round(row["open"], 2),
            "high": round(row["high"], 2),
            "low": round(row["low"], 2),
            "close": round(row["close"], 2)
        })
    return {"candles": candles}

@app.get("/status")
def get_status():
    """حالة المحفظة الورقية"""
    return paper.get_summary()

@app.get("/trades")
def get_trades():
    """قائمة الصفقات المفتوحة والمغلقة"""
    return {
        "open": paper.get_open_positions(),
        "history": paper.get_trade_history()
    }

@app.post("/trade")
def execute_trade(req: TradeRequest):
    """تنفيذ صفقة وهمية"""
    can, msg = paper.can_trade(Config.MAX_TRADES_PER_DAY, 0.05)
    if not can:
        raise HTTPException(400, msg)
    if req.volume <= 0:
        risk = paper.balance * Config.RISK_PER_TRADE
        sl_dist = abs(req.entry - req.sl)
        req.volume = round(risk / sl_dist if sl_dist > 0 else 0.01, 2)
    if req.volume <= 0:
        raise HTTPException(400, "حجم غير صالح")
    success, result = paper.open_trade(req.symbol, req.side, req.entry, req.sl, req.tp, req.volume)
    if not success:
        raise HTTPException(400, result)
    return {"status": "success", "trade": result}

# ============================================================
# 6. بدء التشغيل - تشغيل المحدّث التلقائي
# ============================================================

@app.on_event("startup")
def startup_signal_updater():
    """تشغيل تحديث الإشارات التلقائي في الخلفية"""
    try:
        start_auto_updater()
        logger.info("🚀 تم تشغيل المحدّث التلقائي للإشارات")
    except Exception as e:
        logger.warning(f"⚠️ فشل تشغيل المحدّث التلقائي: {e}")

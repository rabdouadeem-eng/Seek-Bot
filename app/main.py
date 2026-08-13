# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging
from .config import Config
from .broker import YahooBroker
from .strategy import detect_signal
from .paper_trading import PaperTrading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Seek Bot", version="1.0")

broker = YahooBroker()
symbol = Config.SYMBOL_YAHOO

logger.info(f"📡 المصدر: Yahoo | الرمز: {symbol}")
paper = PaperTrading(Config.INITIAL_BALANCE)

class TradeRequest(BaseModel):
    symbol: str
    side: str
    volume: float = 0
    sl: float
    tp: float

@app.get("/")
def root():
    return HTMLResponse("<h1>🔍 Seek Bot يعمل على Yahoo</h1><p>افتح /signal أو /candles للتحقق.</p>")

@app.get("/signal")
def get_signal():
    df = broker.get_candles(symbol, Config.TIMEFRAME, Config.LOOKBACK_CANDLES + 10)
    logger.info(f"📊 عدد الشموع: {len(df) if df is not None else 0}")
    if df is None:
        return {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}
    sig = detect_signal(df, Config.LOOKBACK_CANDLES)
    return sig or {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}

@app.get("/candles")
def get_candles():
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
    return paper.get_summary()

@app.get("/trades")
def get_trades():
    return {"open": paper.get_open_positions(), "history": paper.get_trade_history()}

@app.post("/trade")
def execute_trade(req: TradeRequest):
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

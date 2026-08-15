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

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """✅ لوحة تحكم بصرية لـ Seek Bot (تعرض الإشارة، الشموع، وحالة المحفظة)"""
    html = """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>🔍 Seek Bot - لوحة التحكم</title>
        <style>
            body { font-family: sans-serif; background: #0E1116; color: #E6EDF3; padding: 16px; margin: 0; }
            h1 { font-size: 20px; margin-bottom: 4px; }
            .sub { color: #8B949E; font-size: 13px; margin-bottom: 16px; }
            .card { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px; margin-bottom: 14px; }
            .card h3 { margin: 0 0 10px 0; font-size: 15px; color: #8B949E; }
            .signal-type { font-size: 24px; font-weight: bold; }
            .buy { color: #3FB950; }
            .sell { color: #F85149; }
            .hold { color: #D29922; }
            .price { font-size: 18px; color: #E6EDF3; margin-top: 4px; }
            .row { display: flex; justify-content: space-between; margin: 6px 0; font-size: 14px; }
            .row span:first-child { color: #8B949E; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; background: #21262D; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
            .grid .box { background: #0D1117; border-radius: 8px; padding: 10px; text-align: center; }
            .grid .box .val { font-size: 20px; font-weight: bold; }
            .grid .box .lbl { font-size: 12px; color: #8B949E; }
            #refresh-note { color: #8B949E; font-size: 12px; text-align: center; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>🔍 Seek Bot</h1>
        <div class="sub">لوحة تحكم بصرية — استراتيجية القيعان والقمم</div>

        <div class="card">
            <h3>الإشارة الحالية</h3>
            <div id="signal-box">جاري التحميل...</div>
        </div>

        <div class="card">
            <h3>حالة المحفظة (Paper Trading)</h3>
            <div class="grid" id="status-box">
                <div class="box"><div class="val">-</div><div class="lbl">الرصيد</div></div>
                <div class="box"><div class="val">-</div><div class="lbl">الربح/الخسارة</div></div>
                <div class="box"><div class="val">-</div><div class="lbl">صفقات مفتوحة</div></div>
                <div class="box"><div class="val">-</div><div class="lbl">إجمالي الصفقات</div></div>
                <div class="box"><div class="val">-</div><div class="lbl">رابحة</div></div>
                <div class="box"><div class="val">-</div><div class="lbl">خاسرة</div></div>
                <div class="box"><div class="val">-</div><div class="lbl">نسبة النجاح</div></div>
                <div class="box"><div class="val">-</div><div class="lbl">صفقات اليوم</div></div>
            </div>
        </div>

        <div class="card">
            <h3>سجل الصفقات (Paper Trading)</h3>
            <table id="trades-table" style="width:100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="color:#8B949E; text-align: right;">
                        <th style="padding:4px;">الحالة</th>
                        <th style="padding:4px;">الاتجاه</th>
                        <th style="padding:4px;">دخول</th>
                        <th style="padding:4px;">خروج</th>
                        <th style="padding:4px;">ربح $</th>
                    </tr>
                </thead>
                <tbody id="trades-body">
                    <tr><td colspan="5" style="padding:8px; color:#8B949E;">جاري التحميل...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3>آخر الأسعار (30 شمعة)</h3>
            <div id="candles-box">جاري التحميل...</div>
        </div>

        <div id="refresh-note">يتحدث تلقائياً كل 30 ثانية</div>

        <script>
        async function loadData() {
            try {
                const sig = await (await fetch('/signal')).json();
                const cls = sig.type === 'BUY' ? 'buy' : sig.type === 'SELL' ? 'sell' : 'hold';
                document.getElementById('signal-box').innerHTML = `
                    <div class="signal-type ${cls}">${sig.type || 'HOLD'} ${sig.confidence ? '('+Math.round(sig.confidence*100)+'%)' : ''}</div>
                    <div class="price">السعر: ${sig.entry || '-'}</div>
                    <div class="row"><span>وقف الخسارة (SL)</span><span>${sig.sl || '-'}</span></div>
                    <div class="row"><span>جني الأرباح (TP)</span><span>${sig.tp || '-'}</span></div>
                    ${sig.reason ? '<div class="row"><span>السبب</span><span class="badge">'+sig.reason+'</span></div>' : ''}
                `;
            } catch (e) {
                document.getElementById('signal-box').innerHTML = 'تعذر جلب الإشارة';
            }

            try {
                const st = await (await fetch('/status')).json();
                const winRate = (st.wins + st.losses) > 0 ? Math.round((st.wins / (st.wins + st.losses)) * 100) : '-';
                document.getElementById('status-box').innerHTML = `
                    <div class="box"><div class="val">$${st.balance ?? '-'}</div><div class="lbl">الرصيد</div></div>
                    <div class="box"><div class="val">$${st.total_pnl ?? '-'}</div><div class="lbl">الربح/الخسارة</div></div>
                    <div class="box"><div class="val">${st.open_positions ?? '-'}</div><div class="lbl">صفقات مفتوحة</div></div>
                    <div class="box"><div class="val">${st.total_trades ?? '-'}</div><div class="lbl">إجمالي الصفقات</div></div>
                    <div class="box"><div class="val buy">${st.wins ?? '-'}</div><div class="lbl">رابحة</div></div>
                    <div class="box"><div class="val sell">${st.losses ?? '-'}</div><div class="lbl">خاسرة</div></div>
                    <div class="box"><div class="val">${winRate}${winRate !== '-' ? '%' : ''}</div><div class="lbl">نسبة النجاح</div></div>
                    <div class="box"><div class="val">${st.daily_trades ?? '-'}</div><div class="lbl">صفقات اليوم</div></div>
                `;
            } catch (e) {}

            try {
                const tr = await (await fetch('/trades')).json();
                const rows = [];
                (tr.open || []).forEach(t => rows.push({...t, status: 'مفتوحة'}));
                (tr.history || []).slice(-20).reverse().forEach(t => rows.push({...t, status: 'مغلقة'}));
                document.getElementById('trades-body').innerHTML = rows.length ? rows.map(t => `
                    <tr style="border-top:1px solid #21262D;">
                        <td style="padding:4px;">${t.status}</td>
                        <td style="padding:4px;" class="${t.side === 'BUY' ? 'buy' : 'sell'}">${t.side}</td>
                        <td style="padding:4px;">${t.entry ?? '-'}</td>
                        <td style="padding:4px;">${t.exit ?? '-'}</td>
                        <td style="padding:4px;" class="${(t.profit ?? 0) >= 0 ? 'buy' : 'sell'}">${t.profit ?? '-'}</td>
                    </tr>
                `).join('') : '<tr><td colspan="5" style="padding:8px; color:#8B949E;">لا توجد صفقات بعد</td></tr>';
            } catch (e) {
                document.getElementById('trades-body').innerHTML = '<tr><td colspan="5" style="padding:8px;">تعذر جلب الصفقات</td></tr>';
            }

            try {
                const c = await (await fetch('/candles')).json();
                const last5 = (c.candles || []).slice(-5).reverse();
                document.getElementById('candles-box').innerHTML = last5.map(k =>
                    `<div class="row"><span>${k.time}</span><span>${k.close}</span></div>`
                ).join('') || 'لا توجد بيانات';
            } catch (e) {
                document.getElementById('candles-box').innerHTML = 'تعذر جلب الشموع';
            }
        }
        loadData();
        setInterval(loadData, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

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
# 6. بدء التشغيل - تشغيل المحدّث التلقائي + التداول التلقائي
# ============================================================

AUTO_TRADE_MIN_CONFIDENCE = 0.8  # ✅ عتبة عالية (مطابقة لـ PRO-TRADING-BOT)

async def auto_trade_loop(interval: int = 60):
    """✅ يفتح الصفقة تلقائياً ويسجلها عند بلوغ الثقة العتبة العالية، ويغلق الصفقات عند SL/TP"""
    import asyncio
    while True:
        try:
            sig = signal_engine.get_signal(signal_engine.active_symbol)

            # إغلاق الصفقات المفتوحة إذا بلغت SL/TP
            current_price = broker.get_current_price(signal_engine.active_symbol)
            if current_price:
                closed = paper.check_sl_tp(signal_engine.active_symbol, current_price)
                for c in closed:
                    logger.info(f"🔴 أُغلقت تلقائياً {c['side']} {c['symbol']} | الربح: ${c['profit']}")

            # فتح صفقة جديدة تلقائياً عند ثقة عالية، وفقط إذا لا توجد صفقة مفتوحة لنفس الرمز
            if sig.get("type") in ("BUY", "SELL") and sig.get("confidence", 0) >= AUTO_TRADE_MIN_CONFIDENCE:
                already_open = any(
                    p["symbol"] == signal_engine.active_symbol and p["status"] == "OPEN"
                    for p in paper.get_open_positions()
                )
                if not already_open:
                    can, msg = paper.can_trade(Config.MAX_TRADES_PER_DAY, 0.05)
                    if can:
                        success, result = paper.open_trade(
                            signal_engine.active_symbol, sig["type"],
                            sig["entry"], sig["sl"], sig["tp"]
                        )
                        if success:
                            logger.info(f"🟢 صفقة تلقائية {sig['type']} {signal_engine.active_symbol} بثقة {sig['confidence']}")
                    else:
                        logger.info(f"⏸️ تخطي الفتح التلقائي: {msg}")
        except Exception as e:
            logger.error(f"❌ خطأ في التداول التلقائي: {e}")
        await asyncio.sleep(interval)

def start_auto_trader():
    import threading, asyncio as _asyncio
    def run():
        _asyncio.run(auto_trade_loop(60))
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    logger.info(f"🤖 تم تشغيل التداول التلقائي — عتبة الثقة: {AUTO_TRADE_MIN_CONFIDENCE}")

@app.on_event("startup")
def startup_signal_updater():
    """تشغيل تحديث الإشارات التلقائي والتداول التلقائي في الخلفية"""
    try:
        start_auto_updater()
        logger.info("🚀 تم تشغيل المحدّث التلقائي للإشارات")
    except Exception as e:
        logger.warning(f"⚠️ فشل تشغيل المحدّث التلقائي: {e}")
    try:
        start_auto_trader()
    except Exception as e:
        logger.warning(f"⚠️ فشل تشغيل التداول التلقائي: {e}")

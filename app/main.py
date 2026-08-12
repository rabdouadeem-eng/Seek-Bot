# app/main.py
# ============================================================
# 🔍 Seek Bot - الخادم الرئيسي (App Signal)
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging

from .config import Config
from .broker import BinanceBroker, YahooBroker
from .strategy import detect_signal
from .paper_trading import PaperTrading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Seek Bot", version="1.0")

if Config.DATA_SOURCE.lower() == "yahoo":
    broker = YahooBroker()
    symbol = Config.SYMBOL_YAHOO
else:
    broker = BinanceBroker()
    symbol = Config.SYMBOL

logger.info(f"📡 المصدر: {Config.DATA_SOURCE} | الرمز: {symbol}")

paper = PaperTrading(Config.INITIAL_BALANCE)

class TradeRequest(BaseModel):
    symbol: str
    side: str
    volume: float = 0
    sl: float
    tp: float


@app.get("/")
def root():
    html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔍 Seek Bot</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: #0E1116; color: #E6EDF3; padding:20px; }
            .container { max-width:1200px; margin:0 auto; }
            .card { background:#161B22; border:1px solid #262C36; border-radius:16px; padding:20px; margin-bottom:16px; }
            h1 { color:#FBBF24; }
            .stats { display:grid; grid-template-columns: repeat(auto-fit,minmax(140px,1fr)); gap:12px; }
            .stat { background:#0E1116; padding:12px; border-radius:12px; text-align:center; border:1px solid #262C36; }
            .stat .label { color:#8B949E; font-size:12px; }
            .stat .value { font-size:22px; font-weight:700; }
            .green { color:#2EA043; } .red { color:#DA3633; } .gold { color:#FBBF24; } .blue { color:#58A6FF; }
            .badge { display:inline-block; padding:4px 14px; border-radius:20px; font-weight:bold; }
            .badge-buy { background:#2EA043; color:white; }
            .badge-sell { background:#DA3633; color:white; }
            .badge-neutral { background:#262C36; color:#8B949E; }
            table { width:100%; border-collapse:collapse; margin-top:10px; }
            th, td { padding:8px 12px; border-bottom:1px solid #1C2128; text-align:right; }
            th { color:#8B949E; font-size:13px; }
            .empty { color:#8B949E; text-align:center; padding:20px; }
            .footer { margin-top:30px; text-align:center; color:#8B949E; font-size:13px; border-top:1px solid #262C36; padding-top:20px; }
            .btn { background:#262C36; color:white; border:none; padding:8px 20px; border-radius:8px; cursor:pointer; margin-bottom:16px; }
            #priceChart { max-height: 200px; width: 100%; }
        </style>
    </head>
    <body>
    <div class="container">
        <h1>🔍 Seek Bot <small style="color:#8B949E;font-size:18px;">صندوق التداول الورقي</small></h1>
        <button class="btn" onclick="refreshAll()">🔄 تحديث</button>
        
        <div class="card">
            <div class="stats" id="stats">
                <div class="stat"><div class="label">💰 الرصيد</div><div class="value gold" id="balance">--</div></div>
                <div class="stat"><div class="label">📈 إجمالي الربح</div><div class="value" id="pnl">--</div></div>
                <div class="stat"><div class="label">📊 صفقات مفتوحة</div><div class="value blue" id="openPos">--</div></div>
                <div class="stat"><div class="label">📋 إجمالي الصفقات</div><div class="value" id="totalTrades">--</div></div>
            </div>
        </div>
        
        <div class="card">
            <h3>📈 الإشارة الحالية</h3>
            <div id="signal"><span class="badge badge-neutral">⏳ جاري الفحص...</span></div>
            <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:14px;color:#8B949E;">
                <span>الدخول: <strong id="entry" style="color:#E6EDF3;">--</strong></span>
                <span>SL: <strong id="sl" style="color:#DA3633;">--</strong></span>
                <span>TP: <strong id="tp" style="color:#2EA043;">--</strong></span>
                <span>الثقة: <strong id="conf" style="color:#FBBF24;">--</strong></span>
            </div>
        </div>

        <!-- الشارت الصغير -->
        <div class="card">
            <h3>📊 حركة السعر (آخر 30 شمعة)</h3>
            <canvas id="priceChart" height="180"></canvas>
        </div>
        
        <div class="card"><h3>📊 الصفقات المفتوحة</h3><div id="openTable"><p class="empty">لا توجد صفقات</p></div></div>
        <div class="card"><h3>📋 سجل الصفقات</h3><div id="historyTable"><p class="empty">لا توجد صفقات</p></div></div>
        <div class="footer">⚡ Seek Bot v1.0 · بيانات من <span style="color:#FBBF24;">""" + Config.DATA_SOURCE.upper() + """</span> · جميع الصفقات وهمية (Paper Trading)</div>
    </div>
    <script>
        let chart = null;

        async function loadChart() {
            try {
                const res = await fetch('/candles');
                const data = await res.json();
                const ctx = document.getElementById('priceChart').getContext('2d');
                
                if (data.candles.length === 0) {
                    if (chart) { chart.destroy(); chart = null; }
                    return;
                }

                const labels = data.candles.map(c => c.time);
                const prices = data.candles.map(c => c.close);
                
                if (chart) { chart.destroy(); }
                
                chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'سعر الإغلاق',
                            data: prices,
                            borderColor: '#FBBF24',
                            backgroundColor: 'rgba(251, 191, 36, 0.15)',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 2,
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { labels: { color: '#8B949E', boxWidth: 10 } }
                        },
                        scales: {
                            x: { ticks: { color: '#8B949E', maxTicksLimit: 8, font: { size: 9 } } },
                            y: { ticks: { color: '#8B949E', font: { size: 9 } } }
                        }
                    }
                });
            } catch(e) { console.error('خطأ في الشارت:', e); }
        }

        async function fetchData() {
            try {
                const s = await fetch('/status'); const status = await s.json();
                document.getElementById('balance').textContent = '$'+status.balance.toFixed(2);
                const pnl = document.getElementById('pnl');
                pnl.textContent = '$'+status.total_pnl.toFixed(2);
                pnl.className = 'value '+(status.total_pnl>=0?'green':'red');
                document.getElementById('openPos').textContent = status.open_positions;
                document.getElementById('totalTrades').textContent = status.total_trades;
                
                const sig = await fetch('/signal'); const signal = await sig.json();
                const sigDiv = document.getElementById('signal');
                if(signal.type) {
                    sigDiv.innerHTML = `<span class="badge badge-${signal.type.toLowerCase()}">${signal.type}</span>`;
                    document.getElementById('entry').textContent = signal.entry.toFixed(2);
                    document.getElementById('sl').textContent = signal.sl.toFixed(2);
                    document.getElementById('tp').textContent = signal.tp.toFixed(2);
                    document.getElementById('conf').textContent = (signal.confidence*100).toFixed(0)+'%';
                } else {
                    sigDiv.innerHTML = `<span class="badge badge-neutral">⏸️ لا توجد إشارة</span>`;
                    ['entry','sl','tp','conf'].forEach(id => document.getElementById(id).textContent='--');
                }
                
                const t = await fetch('/trades'); const trades = await t.json();
                const openTable = document.getElementById('openTable');
                if(trades.open.length) {
                    let html = `<table><tr><th>الرمز</th><th>النوع</th><th>الدخول</th><th>SL</th><th>TP</th><th>الحجم</th></tr>`;
                    trades.open.forEach(t => {
                        html += `<tr><td><b>${t.symbol}</b></td><td><span class="badge badge-${t.side.toLowerCase()}">${t.side}</span></td>
                                <td>${t.entry}</td><td style="color:#DA3633;">${t.sl}</td><td style="color:#2EA043;">${t.tp}</td><td>${t.volume}</td></tr>`;
                    });
                    html += `</table>`;
                    openTable.innerHTML = html;
                } else openTable.innerHTML = '<p class="empty">لا توجد صفقات مفتوحة</p>';
                
                const hist = document.getElementById('historyTable');
                if(trades.history.length) {
                    let html = `<table><tr><th>الرمز</th><th>النوع</th><th>الدخول</th><th>الخروج</th><th>الربح</th></tr>`;
                    trades.history.slice(-5).reverse().forEach(t => {
                        html += `<tr><td><b>${t.symbol}</b></td><td><span class="badge badge-${t.side.toLowerCase()}">${t.side}</span></td>
                                <td>${t.entry}</td><td>${t.exit||'--'}</td><td class="${t.profit>=0?'green':'red'}">$${t.profit.toFixed(2)}</td></tr>`;
                    });
                    html += `</table>`;
                    hist.innerHTML = html;
                } else hist.innerHTML = '<p class="empty">لا توجد صفقات</p>';
            } catch(e) { console.error(e); }
        }

        function refreshAll() {
            fetchData();
            loadChart();
        }

        fetchData();
        loadChart();
        setInterval(refreshAll, 15000);
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


# ============================================================
# نقاط النهاية (API) – App Signal
# ============================================================

@app.get("/signal")
def get_signal():
    df = broker.get_candles(symbol, Config.TIMEFRAME, Config.LOOKBACK_CANDLES + 10)
    logger.info(f"📊 عدد الشموع المستلمة: {len(df) if df is not None else 0}")
    if df is None:
        return {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}
    sig = detect_signal(df, Config.LOOKBACK_CANDLES)
    if sig:
        logger.info(f"✅ إشارة: {sig['type']} | السعر: {sig['entry']}")
    else:
        logger.info("⏸️ لا توجد إشارة حالياً")
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
    return {
        "open": paper.get_open_positions(),
        "history": paper.get_trade_history()
    }

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

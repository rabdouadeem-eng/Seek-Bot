# app/main.py
# ============================================================
# 🔍 Seek Bot - داشبورد احترافي (مستوحى من Pro Trading Bot)
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging
from .config import Config
from .broker import DataBroker
from .strategy import detect_signal
from .paper_trading import PaperTrading
from .signal_server import SignalEngine, start_auto_updater

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Seek Bot - Dashboard", version="2.0")

# ============================================================
# 1. تهيئة المكونات
# ============================================================
broker = DataBroker()
symbol = Config.SYMBOL
paper = PaperTrading(Config.INITIAL_BALANCE)
signal_engine = SignalEngine()

logger.info(f"📡 المصدر: DataBroker | الرمز: {symbol}")

# ============================================================
# 2. نماذج البيانات
# ============================================================
class TradeRequest(BaseModel):
    symbol: str
    side: str
    volume: float = 0
    sl: float
    tp: float

class SettingsRequest(BaseModel):
    capital: float
    risk_percent: float
    tp_percent: float
    sl_percent: float

# ============================================================
# 3. نقاط النهاية - الإشارات والبيانات
# ============================================================
@app.get("/signal")
def get_signal():
    df = broker.get_candles(symbol, Config.TIMEFRAME, Config.LOOKBACK_CANDLES + 10)
    if df is None:
        return {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}
    sig = detect_signal(df, Config.LOOKBACK_CANDLES)
    return sig or {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}

@app.get("/signal/{symbol}")
def get_signal_by_symbol(symbol: str):
    return signal_engine.get_signal(symbol)

@app.get("/signals/all")
def get_all_signals():
    return signal_engine.get_all_signals()

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

@app.post("/settings")
def save_settings(req: SettingsRequest):
    # هنا يمكنك حفظ الإعدادات في ملف أو قاعدة بيانات
    # حالياً سنعيدها فقط للتأكيد
    return {
        "status": "saved",
        "capital": req.capital,
        "risk": req.risk_percent,
        "tp": req.tp_percent,
        "sl": req.sl_percent
    }

# ============================================================
# 4. الصفحة الرئيسية - داشبورد متكامل
# ============================================================
@app.get("/")
def root():
    html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔍 Seek Bot - Dashboard</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0E1116; color: #E6EDF3; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            .card { background: #161B22; border: 1px solid #262C36; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
            h1, h2, h3 { margin-bottom: 12px; }
            h1 { color: #FBBF24; font-size: 28px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 16px; }
            .stat-box { background: #0E1116; padding: 16px; border-radius: 12px; border: 1px solid #262C36; text-align: center; }
            .stat-box .label { font-size: 12px; color: #8B949E; text-transform: uppercase; letter-spacing: 0.5px; }
            .stat-box .value { font-size: 24px; font-weight: 700; margin-top: 4px; }
            .green { color: #2EA043; } .red { color: #DA3633; } .gold { color: #FBBF24; } .blue { color: #58A6FF; }
            
            .signal-card { background: #0E1116; border-radius: 12px; padding: 16px; border: 1px solid #262C36; margin-bottom: 12px; }
            .signal-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
            .signal-type { font-weight: 700; font-size: 18px; }
            .signal-price { font-size: 16px; color: #8B949E; }
            .signal-reason { font-size: 13px; color: #8B949E; margin-top: 8px; padding: 8px; background: #161B22; border-radius: 8px; }
            .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 14px; }
            .badge-buy { background: #2EA043; color: #fff; }
            .badge-sell { background: #DA3633; color: #fff; }
            .badge-hold { background: #262C36; color: #8B949E; }
            
            table { width: 100%; border-collapse: collapse; margin-top: 12px; }
            th, td { padding: 10px 12px; border-bottom: 1px solid #1C2128; text-align: right; }
            th { color: #8B949E; font-size: 13px; font-weight: 600; }
            .empty-state { color: #8B949E; text-align: center; padding: 30px; }
            
            .form-row { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; margin-bottom: 12px; }
            .form-row label { color: #8B949E; font-size: 14px; min-width: 120px; }
            .form-row input { background: #0E1116; border: 1px solid #262C36; border-radius: 8px; padding: 8px 12px; color: #E6EDF3; flex: 1; min-width: 100px; }
            .btn { padding: 8px 20px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
            .btn-primary { background: #FBBF24; color: #0E1116; }
            .btn-primary:hover { opacity: 0.8; transform: scale(1.02); }
            .btn-sm { padding: 4px 12px; font-size: 12px; background: #262C36; color: #E6EDF3; }
            .footer { margin-top: 30px; text-align: center; color: #8B949E; font-size: 13px; border-top: 1px solid #262C36; padding-top: 20px; }
            
            @media (max-width: 600px) { .stats-grid { grid-template-columns: 1fr 1fr; } }
        </style>
    </head>
    <body>
    <div class="container">
        <h1>🔍 Seek Bot <span style="color:#8B949E; font-size:18px; font-weight:normal;">داشبورد التداول</span></h1>
        
        <!-- بطاقة الإحصائيات -->
        <div class="card">
            <h3>📊 لوحة الإحصائيات</h3>
            <div class="stats-grid" id="statsGrid">
                <div class="stat-box"><div class="label">💰 الرصيد</div><div class="value gold" id="balance">--</div></div>
                <div class="stat-box"><div class="label">📈 إجمالي الربح</div><div class="value" id="pnl">--</div></div>
                <div class="stat-box"><div class="label">✅ صفقات رابحة</div><div class="value green" id="wins">--</div></div>
                <div class="stat-box"><div class="label">❌ صفقات خاسرة</div><div class="value red" id="losses">--</div></div>
                <div class="stat-box"><div class="label">🎯 نسبة النجاح</div><div class="value blue" id="winRate">--</div></div>
                <div class="stat-box"><div class="label">📊 صفقات مفتوحة</div><div class="value" id="openPos" style="color:#FBBF24;">--</div></div>
            </div>
        </div>

        <!-- رأس المال والمخاطرة -->
        <div class="card">
            <h3>🛡️ رأس المال والمخاطرة</h3>
            <div class="form-row">
                <label>رأس المال ($)</label>
                <input type="number" id="capitalInput" value="10000" step="100">
                <label>مخاطرة %</label>
                <input type="number" id="riskInput" value="2.0" step="0.1">
                <label>هدف الربح %</label>
                <input type="number" id="tpInput" value="3.0" step="0.1">
                <label>وقف الخسارة %</label>
                <input type="number" id="slInput" value="1.5" step="0.1">
                <button class="btn btn-primary" onclick="saveSettings()">💾 حفظ الإعدادات</button>
            </div>
        </div>

        <!-- الإشارات الحية -->
        <div class="card">
            <h3>📈 الإشارات الحية</h3>
            <div id="signalsContainer">
                <div class="empty-state">⏳ جاري تحميل الإشارات...</div>
            </div>
        </div>

        <!-- سجل الصفقات -->
        <div class="card">
            <h3>📋 سجل الصفقات (Paper Trading)</h3>
            <div id="tradesContainer">
                <div class="empty-state">⏳ جاري تحميل السجل...</div>
            </div>
        </div>

        <div class="footer">
            ⚡ Seek Bot v2.0 · جميع الصفقات وهمية (Paper Trading) · تحديث تلقائي كل 15 ثانية
        </div>
    </div>

    <script>
        // ============================================================
        // 1. جلب الإحصائيات
        // ============================================================
        async function fetchStatus() {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('balance').textContent = '$' + data.balance.toFixed(2);
                const pnl = document.getElementById('pnl');
                pnl.textContent = '$' + data.total_pnl.toFixed(2);
                pnl.className = 'value ' + (data.total_pnl >= 0 ? 'green' : 'red');
                document.getElementById('wins').textContent = data.wins || 0;
                document.getElementById('losses').textContent = data.losses || 0;
                document.getElementById('winRate').textContent = data.win_rate ? data.win_rate.toFixed(1) + '%' : '0%';
                document.getElementById('openPos').textContent = data.open_positions || 0;
            } catch(e) { console.error('Status error:', e); }
        }

        // ============================================================
        // 2. جلب الإشارات وعرضها
        // ============================================================
        async function fetchSignals() {
            try {
                const res = await fetch('/signals/all');
                const data = await res.json();
                const container = document.getElementById('signalsContainer');
                if (!data || Object.keys(data).length === 0) {
                    container.innerHTML = '<div class="empty-state">لا توجد إشارات حالياً</div>';
                    return;
                }
                let html = '';
                for (const [symbol, signal] of Object.entries(data)) {
                    const type = signal.type || 'HOLD';
                    const isBuy = type === 'BUY';
                    const isSell = type === 'SELL';
                    const badgeClass = isBuy ? 'badge-buy' : (isSell ? 'badge-sell' : 'badge-hold');
                    const confidence = signal.confidence ? (signal.confidence * 100).toFixed(0) : '0';
                    const price = signal.entry || '--';
                    const reason = signal.reason || 'لا يوجد سبب محدد';
                    html += `
                        <div class="signal-card">
                            <div class="signal-header">
                                <div>
                                    <span class="badge ${badgeClass}">${type}</span>
                                    <span style="font-weight:600; margin-right:10px;">${symbol}</span>
                                    <span style="color:#8B949E; font-size:14px;">الثقة: ${confidence}%</span>
                                </div>
                                <div class="signal-price">💰 ${price}</div>
                            </div>
                            <div class="signal-reason">📝 ${reason}</div>
                        </div>
                    `;
                }
                container.innerHTML = html;
            } catch(e) { 
                console.error('Signals error:', e);
                document.getElementById('signalsContainer').innerHTML = '<div class="empty-state">❌ خطأ في جلب الإشارات</div>';
            }
        }

        // ============================================================
        // 3. جلب سجل الصفقات
        // ============================================================
        async function fetchTrades() {
            try {
                const res = await fetch('/trades');
                const data = await res.json();
                const container = document.getElementById('tradesContainer');
                const history = data.history || [];
                if (history.length === 0) {
                    container.innerHTML = '<div class="empty-state">📭 لا توجد صفقات بعد</div>';
                    return;
                }
                let html = `
                    <table>
                        <thead>
                            <tr><th>الزوج</th><th>الاتجاه</th><th>الدخول</th><th>TP</th><th>SL</th><th>الربح ($)</th><th>الحالة</th></tr>
                        </thead>
                        <tbody>
                `;
                history.slice(-10).reverse().forEach(t => {
                    const profit = t.profit || 0;
                    const profitClass = profit >= 0 ? 'green' : 'red';
                    html += `
                        <tr>
                            <td><b>${t.symbol}</b></td>
                            <td>${t.side}</td>
                            <td>${t.entry}</td>
                            <td>${t.tp || '--'}</td>
                            <td>${t.sl || '--'}</td>
                            <td class="${profitClass}">${profit.toFixed(2)}</td>
                            <td>${t.status || 'CLOSED'}</td>
                        </tr>
                    `;
                });
                html += '</tbody></table>';
                container.innerHTML = html;
            } catch(e) { 
                console.error('Trades error:', e);
                document.getElementById('tradesContainer').innerHTML = '<div class="empty-state">❌ خطأ في جلب السجل</div>';
            }
        }

        // ============================================================
        // 4. حفظ الإعدادات
        // ============================================================
        async function saveSettings() {
            const capital = document.getElementById('capitalInput').value;
            const risk = document.getElementById('riskInput').value;
            const tp = document.getElementById('tpInput').value;
            const sl = document.getElementById('slInput').value;
            try {
                const res = await fetch('/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ capital, risk_percent: risk, tp_percent: tp, sl_percent: sl })
                });
                const data = await res.json();
                alert('✅ تم حفظ الإعدادات بنجاح!');
                console.log('Settings saved:', data);
            } catch(e) {
                alert('❌ فشل حفظ الإعدادات');
                console.error(e);
            }
        }

        // ============================================================
        // 5. التحديث التلقائي
        // ============================================================
        function refreshAll() {
            fetchStatus();
            fetchSignals();
            fetchTrades();
        }

        // تحديث أولي
        refreshAll();
        // تحديث كل 15 ثانية
        setInterval(refreshAll, 15000);
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ============================================================
# 5. بدء التشغيل - المحدّث التلقائي
# ============================================================
@app.on_event("startup")
def startup_signal_updater():
    try:
        start_auto_updater()
        logger.info("🚀 تم تشغيل المحدّث التلقائي للإشارات")
    except Exception as e:
        logger.warning(f"⚠️ فشل تشغيل المحدّث التلقائي: {e}")

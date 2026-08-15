# app/main.py
# ============================================================
# 🔍 Seek Bot - داشبورد متكامل (مثل Pro Trading Bot)
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

broker = DataBroker()
symbol = Config.SYMBOL
paper = PaperTrading(Config.INITIAL_BALANCE)
signal_engine = SignalEngine()

class TradeRequest(BaseModel):
    symbol: str
    side: str
    volume: float = 0
    sl: float
    tp: float

# ============================================================
# الصفحة الرئيسية - داشبورد احترافي
# ============================================================
@app.get("/")
def root():
    html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔍 Seek Bot - داشبورد</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body {
                font-family: 'Cairo', sans-serif;
                background: #0E1116;
                color: #E6EDF3;
                padding: 20px;
                min-height: 100vh;
            }
            .container { max-width: 1400px; margin:0 auto; }
            
            /* Header */
            .header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:15px; padding:16px 20px; background:#161B22; border-radius:16px; border:1px solid #262C36; margin-bottom:20px; }
            .header h1 { color:#FBBF24; font-size:24px; }
            .header h1 small { color:#8B949E; font-size:14px; font-weight:normal; }
            .header .status { color:#2EA043; font-size:14px; background:#161B22; padding:6px 14px; border-radius:20px; border:1px solid #2EA043; }
            
            /* Cards */
            .card { background:#161B22; border:1px solid #262C36; border-radius:16px; padding:20px; margin-bottom:16px; }
            .card-title { color:#FBBF24; font-size:18px; font-weight:600; margin-bottom:16px; border-bottom:1px solid #262C36; padding-bottom:10px; }
            
            /* Stats Grid */
            .stats-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:12px; }
            .stat-item { background:#0E1116; padding:14px; border-radius:12px; text-align:center; border:1px solid #262C36; }
            .stat-item .label { color:#8B949E; font-size:12px; }
            .stat-item .value { font-size:24px; font-weight:700; margin-top:4px; }
            .stat-item .value.green { color:#2EA043; }
            .stat-item .value.red { color:#DA3633; }
            .stat-item .value.gold { color:#FBBF24; }
            .stat-item .value.blue { color:#58A6FF; }
            
            /* Form */
            .form-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:16px; }
            .form-group label { display:block; color:#8B949E; font-size:13px; margin-bottom:4px; }
            .form-group input { width:100%; padding:8px 12px; background:#0E1116; border:1px solid #262C36; border-radius:8px; color:#E6EDF3; font-size:14px; }
            .form-group input:focus { outline:none; border-color:#FBBF24; }
            .btn { padding:8px 24px; background:#FBBF24; color:#0E1116; border:none; border-radius:8px; font-weight:600; cursor:pointer; transition:0.3s; font-family:'Cairo',sans-serif; }
            .btn:hover { opacity:0.8; transform:scale(1.02); }
            
            /* Signals */
            .signal-card { background:#0E1116; border-radius:12px; padding:16px; margin-bottom:12px; border-right:4px solid #8B949E; }
            .signal-card .header-sig { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; }
            .signal-card .pair { font-size:18px; font-weight:700; }
            .signal-card .price { color:#8B949E; font-size:14px; }
            .badge { padding:4px 14px; border-radius:20px; font-weight:700; font-size:14px; }
            .badge-buy { background:#2EA043; color:white; }
            .badge-sell { background:#DA3633; color:white; }
            .badge-hold { background:#D29922; color:white; }
            .signal-card .reason { color:#8B949E; font-size:13px; margin-top:8px; line-height:1.6; background:#161B22; padding:8px 12px; border-radius:8px; }
            
            /* Table */
            .table-wrap { overflow-x:auto; }
            table { width:100%; border-collapse:collapse; font-size:14px; }
            th { text-align:right; padding:10px 12px; color:#8B949E; border-bottom:1px solid #262C36; }
            td { padding:10px 12px; border-bottom:1px solid #1C2128; }
            .profit-pos { color:#2EA043; }
            .profit-neg { color:#DA3633; }
            .empty-msg { color:#8B949E; text-align:center; padding:20px; }
            
            .footer { text-align:center; color:#8B949E; font-size:13px; margin-top:20px; border-top:1px solid #262C36; padding-top:20px; }
            
            @media (max-width:600px) { .stats-grid { grid-template-columns:1fr 1fr; } .form-grid { grid-template-columns:1fr; } }
        </style>
    </head>
    <body>
    <div class="container">

        <!-- ===== HEADER ===== -->
        <div class="header">
            <h1>🔍 Seek Bot <small>داشبورد التداول الورقي</small></h1>
            <div class="status">🟢 يعمل | <span id="lastUpdate">جاري التحميل...</span></div>
        </div>

        <!-- ===== STATS ===== -->
        <div class="card">
            <div class="card-title">📊 لوحة الإحصائيات</div>
            <div class="stats-grid" id="statsGrid">
                <div class="stat-item"><div class="label">✅ صفقات رابحة</div><div class="value green" id="wins">0</div></div>
                <div class="stat-item"><div class="label">🎯 نسبة النجاح</div><div class="value gold" id="winRate">0%</div></div>
                <div class="stat-item"><div class="label">📊 إجمالي الصفقات</div><div class="value blue" id="totalTrades">0</div></div>
                <div class="stat-item"><div class="label">❌ صفقات خاسرة</div><div class="value red" id="losses">0</div></div>
            </div>
        </div>

        <!-- ===== RISK MANAGEMENT ===== -->
        <div class="card">
            <div class="card-title">🛡️ رأس المال والمخاطرة</div>
            <form id="settingsForm" class="form-grid">
                <div class="form-group"><label>💰 رأس المال ($)</label><input type="number" id="capital" value="10000" step="100"></div>
                <div class="form-group"><label>⚖️ مخاطرة %</label><input type="number" id="risk" value="2" step="0.5" min="0.5" max="5"></div>
                <div class="form-group"><label>🎯 هدف الربح %</label><input type="number" id="tp" value="3" step="0.5"></div>
                <div class="form-group"><label>🛑 وقف الخسارة %</label><input type="number" id="sl" value="1.5" step="0.5"></div>
                <div class="form-group" style="display:flex; align-items:flex-end;"><button type="submit" class="btn">💾 حفظ الإعدادات</button></div>
            </form>
            <div style="margin-top:10px; font-size:13px; color:#8B949E;" id="settingsStatus">الإعدادات الحالية: رأس المال $10000, مخاطرة 2%, TP 3%, SL 1.5%</div>
        </div>

        <!-- ===== SIGNALS ===== -->
        <div class="card">
            <div class="card-title">📈 الإشارات الحية</div>
            <div id="signalsContainer">⏳ جاري تحميل الإشارات...</div>
        </div>

        <!-- ===== TRADES ===== -->
        <div class="card">
            <div class="card-title">📋 سجل الصفقات (Paper Trading)</div>
            <div class="table-wrap" id="tradesContainer">
                <table>
                    <thead><tr><th>الزوج</th><th>الاتجاه</th><th>دخول</th><th>TP</th><th>SL</th><th>الربح $</th><th>الحالة</th><th>المدة</th></tr></thead>
                    <tbody id="tradesBody"><tr><td colspan="8" class="empty-msg">لا توجد صفقات بعد</td></tr></tbody>
                </table>
            </div>
        </div>

        <div class="footer">⚡ Seek Bot v2.0 · جميع الصفقات وهمية (Paper Trading) · يتم التحديث تلقائياً كل 15 ثانية</div>
    </div>

    <script>
        // ============================================================
        // JavaScript - تحديث الداشبورد تلقائياً
        // ============================================================
        const API = '';

        async function fetchDashboard() {
            try {
                // 1. الإحصائيات
                const statusRes = await fetch(API + '/status');
                const status = await statusRes.json();
                document.getElementById('wins').textContent = status.wins || 0;
                document.getElementById('losses').textContent = status.losses || 0;
                document.getElementById('totalTrades').textContent = status.total_trades || 0;
                document.getElementById('winRate').textContent = (status.win_rate || 0) + '%';
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString('ar-EG');

                // 2. الإشارات
                const sigRes = await fetch(API + '/signals/all');
                const signals = await sigRes.json();
                const sigContainer = document.getElementById('signalsContainer');
                if (Object.keys(signals).length === 0) {
                    sigContainer.innerHTML = '<div class="empty-msg">⏸️ لا توجد إشارات حالياً</div>';
                } else {
                    let sigHtml = '';
                    for (const [symbol, data] of Object.entries(signals)) {
                        const type = data.type || 'HOLD';
                        const badgeClass = type === 'BUY' ? 'badge-buy' : (type === 'SELL' ? 'badge-sell' : 'badge-hold');
                        const confidence = (data.confidence * 100).toFixed(0) || 0;
                        const price = data.entry || '--';
                        const reason = data.reason || 'لا يوجد سبب محدد';
                        const displayType = type === 'HOLD' ? 'مراقبة' : type;
                        sigHtml += `
                            <div class="signal-card" style="border-right-color: ${type === 'BUY' ? '#2EA043' : (type === 'SELL' ? '#DA3633' : '#D29922')};">
                                <div class="header-sig">
                                    <div>
                                        <span class="pair">${symbol}</span>
                                        <span class="price">${price}</span>
                                    </div>
                                    <div>
                                        <span class="badge ${badgeClass}">${displayType} (${confidence}%)</span>
                                    </div>
                                </div>
                                <div class="reason">📝 ${reason}</div>
                                <div style="margin-top:8px; display:flex; gap:10px;">
                                    <button class="btn" style="background:#2EA043; padding:4px 16px; font-size:12px; color:white;" onclick="alert('تنفيذ شراء وهمي لـ ${symbol}')">شراء</button>
                                    <button class="btn" style="background:#DA3633; padding:4px 16px; font-size:12px; color:white;" onclick="alert('تنفيذ بيع وهمي لـ ${symbol}')">بيع</button>
                                </div>
                            </div>
                        `;
                    }
                    sigContainer.innerHTML = sigHtml;
                }

                // 3. سجل الصفقات
                const tradesRes = await fetch(API + '/trades');
                const tradesData = await tradesRes.json();
                const history = tradesData.history || [];
                const tbody = document.getElementById('tradesBody');
                if (history.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" class="empty-msg">📭 لا توجد صفقات بعد</td></tr>';
                } else {
                    let rows = '';
                    // عرض آخر 10 صفقات مقلوبة (الأحدث أولاً)
                    history.slice(-10).reverse().forEach(t => {
                        const profitClass = t.profit >= 0 ? 'profit-pos' : 'profit-neg';
                        const statusText = t.status === 'OPEN' ? '🟢 مفتوحة' : '🔴 مغلقة';
                        const duration = t.close_time ? '--' : 'قيد التنفيذ';
                        rows += `<tr>
                            <td><strong>${t.symbol}</strong></td>
                            <td><span class="badge ${t.side === 'BUY' ? 'badge-buy' : 'badge-sell'}">${t.side}</span></td>
                            <td>${t.entry}</td>
                            <td>${t.tp || '--'}</td>
                            <td>${t.sl || '--'}</td>
                            <td class="${profitClass}">${t.profit ? '$'+t.profit.toFixed(2) : '$0.00'}</td>
                            <td>${statusText}</td>
                            <td>${duration}</td>
                        </tr>`;
                    });
                    tbody.innerHTML = rows;
                }

            } catch(e) {
                console.error('خطأ في التحديث:', e);
                document.getElementById('signalsContainer').innerHTML = '<div class="empty-msg">⚠️ خطأ في جلب البيانات</div>';
            }
        }

        // ============================================================
        // حفظ الإعدادات (يُظهر رسالة فقط حالياً، لكن يمكن ربطه بـ API)
        // ============================================================
        document.getElementById('settingsForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const capital = document.getElementById('capital').value;
            const risk = document.getElementById('risk').value;
            const tp = document.getElementById('tp').value;
            const sl = document.getElementById('sl').value;
            document.getElementById('settingsStatus').textContent = 
                `✅ تم حفظ الإعدادات: رأس المال $${capital}, مخاطرة ${risk}%, TP ${tp}%, SL ${sl}% (سيتم تطبيقها في التحديث التالي)`;
            // هنا يمكن إرسال البيانات إلى نقطة /settings (سنضيفها لاحقاً)
        });

        // تحميل أولي وتحديث كل 15 ثانية
        fetchDashboard();
        setInterval(fetchDashboard, 15000);
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


# ============================================================
# نقاط النهاية (API) - موجودة مسبقاً
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

@app.on_event("startup")
def startup_signal_updater():
    try:
        start_auto_updater()
        logger.info("🚀 تم تشغيل المحدّث التلقائي للإشارات")
    except Exception as e:
        logger.warning(f"⚠️ فشل تشغيل المحدّث التلقائي: {e}")

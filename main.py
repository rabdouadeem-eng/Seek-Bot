# app/main.py
# ============================================================
# 🔍 Seek Bot - صندوق التداول المستقل (الخادم الرئيسي)
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

# استيراد المكونات الداخلية (سننشئها في الخطوات القادمة)
from app.config import Config
from app.broker import BinanceBroker
from app.strategy import detect_signal
from app.paper_trading import PaperTrading

# ============================================================
# 1. تهيئة التطبيق والمكونات
# ============================================================

app = FastAPI(
    title="Seek Bot - صندوق التداول المستقل",
    version="1.0",
    description="بوت تداول ورقي (Paper Trading) يعتمد على استراتيجية القيعان والقمم مع بيانات حية من Binance"
)

# تهيئة المكونات
broker = BinanceBroker()
paper = PaperTrading(Config.INITIAL_BALANCE)

# ============================================================
# 2. نموذج الطلب (Pydantic)
# ============================================================

class TradeRequest(BaseModel):
    symbol: str
    side: str  # "BUY" أو "SELL"
    volume: float
    sl: float
    tp: float

# ============================================================
# 3. نقطة النهاية الرئيسية (لوحة التحكم)
# ============================================================

@app.get("/")
def root():
    html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔍 Seek Bot - صندوق التداول</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: #0E1116; 
                color: #E6EDF3; 
                padding: 20px; 
                min-height: 100vh;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { 
                background: #161B22; 
                border: 1px solid #262C36; 
                border-radius: 16px; 
                padding: 20px; 
                margin-bottom: 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }
            h1 { color: #FBBF24; font-size: 28px; }
            h1 small { color: #8B949E; font-size: 18px; font-weight: normal; }
            .badge { 
                display: inline-block; 
                padding: 4px 12px; 
                border-radius: 20px; 
                font-weight: bold;
                font-size: 14px;
            }
            .badge-buy { background: #2EA043; color: white; }
            .badge-sell { background: #DA3633; color: white; }
            .badge-neutral { background: #262C36; color: #8B949E; }
            
            .stats-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
                gap: 16px; 
                margin-top: 8px;
            }
            .stat-item { 
                background: #0E1116; 
                padding: 12px 16px; 
                border-radius: 12px; 
                border: 1px solid #262C36; 
                text-align: center;
            }
            .stat-label { font-size: 12px; color: #8B949E; text-transform: uppercase; letter-spacing: 0.5px; }
            .stat-value { font-size: 22px; font-weight: 700; margin-top: 4px; }
            .green { color: #2EA043; }
            .red { color: #DA3633; }
            .gold { color: #FBBF24; }
            .blue { color: #58A6FF; }
            
            table { width: 100%; border-collapse: collapse; margin-top: 12px; }
            th, td { padding: 10px 12px; text-align: right; border-bottom: 1px solid #1C2128; }
            th { color: #8B949E; font-weight: 600; font-size: 13px; }
            td { font-size: 14px; }
            .empty-message { color: #8B949E; text-align: center; padding: 20px; }
            
            .btn {
                padding: 8px 18px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.2s ease;
                font-size: 14px;
                color: white;
            }
            .btn:hover { transform: scale(1.03); opacity: 0.9; }
            .btn-buy { background: #2EA043; }
            .btn-sell { background: #DA3633; }
            .btn-refresh { background: #262C36; color: #E6EDF3; }
            
            .footer { margin-top: 30px; text-align: center; color: #8B949E; font-size: 13px; border-top: 1px solid #262C36; padding-top: 20px; }
            .highlight { color: #FBBF24; }
            
            @media (max-width: 600px) {
                .stats-grid { grid-template-columns: 1fr 1fr; }
                body { padding: 12px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 20px;">
                <h1>🔍 Seek Bot <small>صندوق التداول الورقي</small></h1>
                <button class="btn btn-refresh" onclick="fetchData()">🔄 تحديث</button>
            </div>
            
            <!-- بطاقة الرصيد والإحصائيات -->
            <div class="card" id="statusCard">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <h3 style="color: #E6EDF3;">💰 المحفظة</h3>
                    <span id="lastUpdate" style="color: #8B949E; font-size: 12px;">⏳ جاري التحميل...</span>
                </div>
                <div class="stats-grid" id="statsGrid">
                    <div class="stat-item"><div class="stat-label">الرصيد</div><div class="stat-value gold" id="balance">--</div></div>
                    <div class="stat-item"><div class="stat-label">إجمالي الربح</div><div class="stat-value" id="totalPnl">--</div></div>
                    <div class="stat-item"><div class="stat-label">صفقات مفتوحة</div><div class="stat-value blue" id="openPositions">--</div></div>
                    <div class="stat-item"><div class="stat-label">إجمالي الصفقات</div><div class="stat-value" id="totalTrades">--</div></div>
                </div>
            </div>
            
            <!-- بطاقة الإشارة -->
            <div class="card">
                <h3 style="color: #E6EDF3;">📈 الإشارة الحالية</h3>
                <div id="signalDisplay" style="padding: 12px 0; font-size: 16px;">
                    <span class="badge badge-neutral">⏳ جاري الفحص...</span>
                </div>
                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 14px; color: #8B949E;">
                    <span>الدخول: <strong id="entryPrice" style="color: #E6EDF3;">--</strong></span>
                    <span>وقف الخسارة: <strong id="slPrice" style="color: #DA3633;">--</strong></span>
                    <span>جني الأرباح: <strong id="tpPrice" style="color: #2EA043;">--</strong></span>
                    <span>الثقة: <strong id="confidenceDisplay" style="color: #FBBF24;">--</strong></span>
                </div>
            </div>
            
            <!-- الصفقات المفتوحة -->
            <div class="card">
                <h3 style="color: #E6EDF3;">📊 الصفقات المفتوحة</h3>
                <div id="openTradesTable"><p class="empty-message">📭 لا توجد صفقات مفتوحة</p></div>
            </div>
            
            <!-- سجل الصفقات -->
            <div class="card">
                <h3 style="color: #E6EDF3;">📋 سجل الصفقات</h3>
                <div id="historyTradesTable"><p class="empty-message">📭 لا توجد صفقات</p></div>
            </div>
            
            <div class="footer">
                ⚡ Seek Bot v1.0 · بيانات من <span class="highlight">Binance</span> · جميع الصفقات وهمية (Paper Trading)
            </div>
        </div>

        <script>
            const API_BASE = '';
            
            async function fetchData() {
                try {
                    // 1. جلب الحالة
                    const statusRes = await fetch(API_BASE + '/status');
                    const status = await statusRes.json();
                    
                    document.getElementById('balance').textContent = `$${status.balance.toFixed(2)}`;
                    document.getElementById('totalPnl').textContent = `$${status.total_pnl.toFixed(2)}`;
                    document.getElementById('totalPnl').className = `stat-value ${status.total_pnl >= 0 ? 'green' : 'red'}`;
                    document.getElementById('openPositions').textContent = status.open_positions;
                    document.getElementById('totalTrades').textContent = status.total_trades;
                    document.getElementById('lastUpdate').textContent = `🕐 آخر تحديث: ${new Date().toLocaleTimeString('ar-EG')}`;
                    
                    // 2. جلب الإشارة
                    const signalRes = await fetch(API_BASE + '/signal');
                    const signal = await signalRes.json();
                    
                    const signalDiv = document.getElementById('signalDisplay');
                    if (signal.type) {
                        const badgeClass = signal.type === 'BUY' ? 'badge-buy' : 'badge-sell';
                        signalDiv.innerHTML = `<span class="badge ${badgeClass}">${signal.type}</span>`;
                        document.getElementById('entryPrice').textContent = signal.entry.toFixed(2);
                        document.getElementById('slPrice').textContent = signal.sl.toFixed(2);
                        document.getElementById('tpPrice').textContent = signal.tp.toFixed(2);
                        document.getElementById('confidenceDisplay').textContent = (signal.confidence * 100).toFixed(0) + '%';
                    } else {
                        signalDiv.innerHTML = `<span class="badge badge-neutral">⏸️ لا توجد إشارة</span>`;
                        document.getElementById('entryPrice').textContent = '--';
                        document.getElementById('slPrice').textContent = '--';
                        document.getElementById('tpPrice').textContent = '--';
                        document.getElementById('confidenceDisplay').textContent = '--';
                    }
                    
                    // 3. جلب الصفقات المفتوحة
                    const tradesRes = await fetch(API_BASE + '/trades');
                    const tradesData = await tradesRes.json();
                    
                    // الصفقات المفتوحة
                    const openTable = document.getElementById('openTradesTable');
                    if (tradesData.open.length > 0) {
                        let html = `<table><thead><tr><th>الرمز</th><th>النوع</th><th>الدخول</th><th>SL</th><th>TP</th><th>الحجم</th></tr></thead><tbody>`;
                        tradesData.open.forEach(t => {
                            html += `<tr>
                                <td><strong>${t.symbol}</strong></td>
                                <td><span class="badge ${t.side === 'BUY' ? 'badge-buy' : 'badge-sell'}">${t.side}</span></td>
                                <td>${t.entry.toFixed(2)}</td>
                                <td style="color:#DA3633;">${t.sl.toFixed(2)}</td>
                                <td style="color:#2EA043;">${t.tp.toFixed(2)}</td>
                                <td>${t.volume.toFixed(2)}</td>
                            </tr>`;
                        });
                        html += `</tbody></table>`;
                        openTable.innerHTML = html;
                    } else {
                        openTable.innerHTML = `<p class="empty-message">📭 لا توجد صفقات مفتوحة</p>`;
                    }
                    
                    // سجل الصفقات (آخر 5)
                    const historyTable = document.getElementById('historyTradesTable');
                    if (tradesData.history.length > 0) {
                        let html = `<table><thead><tr><th>الرمز</th><th>النوع</th><th>الدخول</th><th>الخروج</th><th>الربح</th></tr></thead><tbody>`;
                        const last5 = tradesData.history.slice(-5).reverse();
                        last5.forEach(t => {
                            const profitClass = t.profit >= 0 ? 'green' : 'red';
                            html += `<tr>
                                <td><strong>${t.symbol}</strong></td>
                                <td><span class="badge ${t.side === 'BUY' ? 'badge-buy' : 'badge-sell'}">${t.side}</span></td>
                                <td>${t.entry.toFixed(2)}</td>
                                <td>${t.exit ? t.exit.toFixed(2) : '--'}</td>
                                <td class="${profitClass}">$${t.profit.toFixed(2)}</td>
                            </tr>`;
                        });
                        html += `</tbody></table>`;
                        historyTable.innerHTML = html;
                    } else {
                        historyTable.innerHTML = `<p class="empty-message">📭 لا توجد صفقات</p>`;
                    }
                    
                } catch(e) {
                    console.error('خطأ في جلب البيانات:', e);
                    document.getElementById('balance').textContent = '⚠️ خطأ';
                }
            }
            
            // تحديث تلقائي كل 15 ثانية
            fetchData();
            setInterval(fetchData, 15000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ============================================================
# 4. نقاط النهاية API (الإشارة، الحالة، الصفقات، التداول)
# ============================================================

@app.get("/signal")
def get_signal():
    """جلب آخر إشارة من الاستراتيجية"""
    df = broker.get_candles(Config.SYMBOL, Config.TIMEFRAME, Config.LOOKBACK_CANDLES + 10)
    if df is None or df.empty:
        return {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}
    signal = detect_signal(df, Config.LOOKBACK_CANDLES)
    if signal is None:
        return {"type": None, "entry": 0, "sl": 0, "tp": 0, "confidence": 0}
    return signal

@app.get("/status")
def get_status():
    """جلب حالة المحفظة الورقية"""
    return paper.get_summary()

@app.get("/trades")
def get_trades():
    """جلب الصفقات المفتوحة والمغلقة"""
    open_positions = paper.get_open_positions()
    history = paper.get_trade_history()
    return {"open": open_positions, "history": history}

@app.post("/trade")
def execute_trade(req: TradeRequest):
    """تنفيذ صفقة وهمية (يدوياً عبر API)"""
    # التحقق من إمكانية التداول
    can, msg = paper.can_trade(Config.MAX_TRADES_PER_DAY, 0.05)
    if not can:
        raise HTTPException(400, msg)
    
    # حساب حجم اللوت (إذا لم يتم تحديده)
    if req.volume <= 0:
        balance = paper.balance
        risk_amount = balance * Config.RISK_PER_TRADE
        sl_distance = abs(req.entry - req.sl)
        volume = risk_amount / sl_distance if sl_distance > 0 else 0.01
        req.volume = round(volume, 2)
    
    if req.volume <= 0:
        raise HTTPException(400, "حجم الصفقة غير صالح")
    
    success, result = paper.open_trade(req.symbol, req.side, req.entry, req.sl, req.tp, req.volume)
    if not success:
        raise HTTPException(400, result)
    return {"status": "success", "trade": result}

# ============================================================
# 5. تشغيل البوت (للتجربة المحلية)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

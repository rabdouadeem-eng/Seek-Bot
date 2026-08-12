# app/paper_trading.py
# ============================================================
# 🔍 Seek Bot - التداول الورقي (Paper Trading)
# يحاكي الصفقات، يدير الرصيد، ويطبق إدارة المخاطر
# ============================================================

import time
import json
import os
from datetime import datetime, date
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class PaperTrading:
    """
    محاكاة التداول الورقي.
    يحافظ على رصيد وهمي، يفتح ويغلق الصفقات، ويسجل كل شيء.
    """
    
    def __init__(self, initial_balance: float = 10000, memory_file: str = "trades_memory.json"):
        """
        Args:
            initial_balance (float): الرصيد الابتدائي.
            memory_file (str): ملف لحفظ الصفقات (للاستمرارية بين جلسات البوت).
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.memory_file = memory_file
        self.positions: List[Dict] = []   # الصفقات المفتوحة
        self.trades_history: List[Dict] = []  # سجل الصفقات المنتهية
        self.today = date.today()
        self.daily_trades = 0
        self.daily_loss = 0.0
        
        # محاولة تحميل الذاكرة السابقة (إن وجدت)
        self._load_memory()
    
    def _load_memory(self):
        """تحميل الصفقات السابقة من ملف (إن وجد)"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trades_history = data.get('trades_history', [])
                    self.balance = data.get('balance', self.initial_balance)
                    self.positions = data.get('positions', [])
                    logger.info(f"📂 تم تحميل {len(self.trades_history)} صفقة سابقة")
            except Exception as e:
                logger.warning(f"⚠️ فشل تحميل الذاكرة: {e}")
    
    def _save_memory(self):
        """حفظ الصفقات في ملف (للاستمرارية)"""
        try:
            data = {
                'trades_history': self.trades_history,
                'balance': self.balance,
                'positions': self.positions,
                'last_update': datetime.now().isoformat()
            }
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"⚠️ فشل حفظ الذاكرة: {e}")
    
    def _reset_daily(self):
        """إعادة تعيين العدادات اليومية (يُستدعى تلقائياً)"""
        today = date.today()
        if today != self.today:
            self.today = today
            self.daily_trades = 0
            self.daily_loss = 0.0
    
    def can_trade(self, max_trades_per_day: int, max_daily_loss_pct: float) -> Tuple[bool, str]:
        """
        التحقق من إمكانية فتح صفقة جديدة بناءً على الحدود اليومية.
        
        Args:
            max_trades_per_day (int): الحد الأقصى للصفقات يومياً.
            max_daily_loss_pct (float): نسبة الخسارة اليومية المسموحة (مثلاً 0.05 = 5%).
        
        Returns:
            (bool, str): (مسموح, سبب الرفض إن وجد)
        """
        self._reset_daily()
        
        if self.daily_trades >= max_trades_per_day:
            return False, f"الحد الأقصى للصفقات اليومية ({max_trades_per_day}) تم بلوغه"
        
        max_loss = self.balance * max_daily_loss_pct
        if self.daily_loss > max_loss:
            return False, f"حد الخسارة اليومي (${max_loss:.2f}) تم بلوغه"
        
        return True, "✅ يمكن التداول"
    
    def open_trade(self, symbol: str, side: str, entry: float, sl: float, tp: float, volume: float = None) -> Tuple[bool, Any]:
        """
        فتح صفقة جديدة (وهمية).
        
        Args:
            symbol (str): الزوج (مثل BTCUSDT).
            side (str): "BUY" أو "SELL".
            entry (float): سعر الدخول.
            sl (float): سعر وقف الخسارة.
            tp (float): سعر جني الأرباح.
            volume (float, optional): حجم الصفقة (إن لم يُحدد يُحسب تلقائياً).
        
        Returns:
            (bool, dict): (نجاح, بيانات الصفقة أو رسالة الخطأ)
        """
        self._reset_daily()
        
        # حساب الحجم إذا لم يُحدد
        if volume is None or volume <= 0:
            risk_amount = self.balance * 0.02  # 2% افتراضياً
            sl_distance = abs(entry - sl)
            if sl_distance > 0:
                volume = risk_amount / sl_distance
            else:
                volume = 0.01
            volume = round(volume, 2)
        
        # التحقق من كفاية الرصيد (للشراء)
        if side.upper() == "BUY":
            cost = entry * volume
            if cost > self.balance:
                return False, f"الرصيد غير كافٍ (المطلوب ${cost:.2f}، المتاح ${self.balance:.2f})"
        
        # إنشاء بيانات الصفقة
        trade = {
            "id": int(time.time() * 1000) + len(self.trades_history),
            "symbol": symbol.upper(),
            "side": side.upper(),
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "volume": volume,
            "open_time": datetime.now().isoformat(),
            "status": "OPEN",
            "profit": 0.0,
            "exit": None,
            "close_time": None
        }
        
        # خصم الرصيد (للشراء)
        if side.upper() == "BUY":
            self.balance -= entry * volume
        # للبيع: نخصم الهامش (محاكاة) أو لا نخصم في البداية (حسب النظام)
        # نفضل هنا عدم الخصم للبيع لأننا سنخسر إذا صعد السعر
        
        self.positions.append(trade)
        self.daily_trades += 1
        self._save_memory()
        
        logger.info(f"🟢 فتح صفقة {side} {symbol} @ {entry:.2f} | الحجم: {volume:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")
        return True, trade
    
    def close_trade(self, trade_id: int, current_price: float) -> Tuple[bool, Any]:
        """
        إغلاق صفقة مفتوحة (يدوياً أو تلقائياً).
        
        Args:
            trade_id (int): معرف الصفقة.
            current_price (float): سعر الإغلاق.
        
        Returns:
            (bool, dict): (نجاح, بيانات الصفقة المغلقة)
        """
        for idx, pos in enumerate(self.positions):
            if pos["id"] == trade_id and pos["status"] == "OPEN":
                # حساب الربح/الخسارة
                if pos["side"] == "BUY":
                    profit = (current_price - pos["entry"]) * pos["volume"]
                else:  # SELL
                    profit = (pos["entry"] - current_price) * pos["volume"]
                
                profit = round(profit, 2)
                
                # تحديث بيانات الصفقة
                pos["status"] = "CLOSED"
                pos["exit"] = round(current_price, 2)
                pos["profit"] = profit
                pos["close_time"] = datetime.now().isoformat()
                
                # تحديث الرصيد (إضافة الربح للرصيد، أو خصم الخسارة)
                self.balance += profit  # إذا كانت الخسارة سالبة، ستخصم تلقائياً
                self.balance = round(self.balance, 2)
                
                # تحديث الخسارة اليومية
                if profit < 0:
                    self.daily_loss += abs(profit)
                
                # نقل الصفقة إلى السجل
                self.trades_history.append(pos)
                self.positions.pop(idx)
                self._save_memory()
                
                logger.info(f"🔴 إغلاق صفقة {pos['side']} {pos['symbol']} @ {current_price:.2f} | الربح: ${profit:.2f}")
                return True, pos
        
        return False, "الصفقة غير موجودة أو مغلقة بالفعل"
    
    def check_sl_tp(self, symbol: str, current_price: float) -> List[Dict]:
        """
        فحص جميع الصفقات المفتوحة وتفعيل SL أو TP تلقائياً.
        
        Args:
            symbol (str): الزوج المراد فحصه.
            current_price (float): السعر الحالي.
        
        Returns:
            list: قائمة الصفقات التي تم إغلاقها تلقائياً.
        """
        closed = []
        for pos in self.positions[:]:  # نسخة للتعديل
            if pos["symbol"] != symbol.upper() or pos["status"] != "OPEN":
                continue
            
            trigger = False
            if pos["side"] == "BUY":
                if current_price <= pos["sl"] or current_price >= pos["tp"]:
                    trigger = True
            else:  # SELL
                if current_price >= pos["sl"] or current_price <= pos["tp"]:
                    trigger = True
            
            if trigger:
                success, result = self.close_trade(pos["id"], current_price)
                if success:
                    closed.append(result)
        
        return closed
    
    def get_open_positions(self) -> List[Dict]:
        """الحصول على قائمة الصفقات المفتوحة"""
        return [p for p in self.positions if p["status"] == "OPEN"]
    
    def get_trade_history(self) -> List[Dict]:
        """الحصول على سجل الصفقات المنتهية (آخر 100)"""
        return self.trades_history[-100:]
    
    def get_summary(self) -> Dict:
        """الحصول على ملخص حالة المحفظة"""
        total_pnl = sum(t["profit"] for t in self.trades_history)
        open_positions = len(self.get_open_positions())
        
        return {
            "balance": round(self.balance, 2),
            "initial_balance": round(self.initial_balance, 2),
            "total_pnl": round(total_pnl, 2),
            "open_positions": open_positions,
            "total_trades": len(self.trades_history),
            "daily_trades": self.daily_trades,
            "wins": len([t for t in self.trades_history if t["profit"] > 0]),
            "losses": len([t for t in self.trades_history if t["profit"] < 0]),
        }
    
    def reset(self):
        """إعادة تعيين المحفظة إلى الرصيد الابتدائي"""
        self.balance = self.initial_balance
        self.positions = []
        self.trades_history = []
        self.daily_trades = 0
        self.daily_loss = 0.0
        self._save_memory()
        logger.info("🔄 تم إعادة ضبط المحفظة إلى الحالة الابتدائية")


# اختبار سريع
if __name__ == "__main__":
    print("="*50)
    print("🧪 اختبار التداول الورقي (Paper Trading)")
    print("="*50)
    
    paper = PaperTrading(initial_balance=10000)
    
    # فتح صفقة شراء وهمية
    print("\n📈 فتح صفقة شراء BTCUSDT @ 60000")
    success, trade = paper.open_trade("BTCUSDT", "BUY", 60000, 59000, 62000, 0.1)
    print(f"   {'✅' if success else '❌'} {trade if success else trade}")
    
    print("\n📊 المحفظة بعد الشراء:")
    summary = paper.get_summary()
    print(f"   الرصيد: ${summary['balance']:.2f}")
    print(f"   الصفقات المفتوحة: {summary['open_positions']}")
    
    # محاكاة ارتفاع السعر إلى 61000
    print("\n📈 السعر يرتفع إلى 61000")
    closed = paper.check_sl_tp("BTCUSDT", 61000)
    if closed:
        print(f"   ✅ تم إغلاق الصفقة بربح: ${closed[0]['profit']:.2f}")
    
    print("\n📊 المحفظة بعد الإغلاق:")
    summary = paper.get_summary()
    print(f"   الرصيد: ${summary['balance']:.2f}")
    print(f"   إجمالي الربح: ${summary['total_pnl']:.2f}")
    print(f"   إجمالي الصفقات: {summary['total_trades']}")
    
    print("\n✅ تم الانتهاء من الاختبار")

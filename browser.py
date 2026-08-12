# app/broker.py
# ============================================================
# 🔍 Seek Bot - طبقة جلب البيانات (Binance Public API)
# ============================================================

import requests
import pandas as pd
import time
from datetime import datetime
import logging

# إعداد التسجيل البسيط
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceBroker:
    """
    طبقة الاتصال بـ Binance.
    تستخدم الـ Public API فقط، لذلك لا تحتاج إلى مفاتيح للقراءة.
    """
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.ping_url = f"{self.base_url}/ping"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "SeekBot/1.0"
        })
    
    def _check_connection(self):
        """التحقق من الاتصال بـ Binance"""
        try:
            resp = self.session.get(self.ping_url, timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def get_candles(self, symbol: str, interval: str = "15m", limit: int = 100):
        """
        جلب بيانات الشموع (OHLCV) من Binance.
        
        Args:
            symbol (str): الزوج (مثل BTCUSDT, ETHUSDT)
            interval (str): الإطار الزمني (1m, 5m, 15m, 1h, 4h, 1d)
            limit (int): عدد الشموع المطلوبة
        
        Returns:
            pd.DataFrame: عمودي time, open, high, low, close, volume
            أو None في حالة الفشل.
        """
        url = f"{self.base_url}/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        
        try:
            logger.info(f"📡 جلب بيانات {symbol} ({interval}) - آخر {limit} شمعة")
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            if not data:
                logger.warning("⚠️ لا توجد بيانات من Binance")
                return None
            
            # تحويل إلى DataFrame
            df = pd.DataFrame(data, columns=[
                'time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_vol', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # تحويل الوقت
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            df.set_index('time', inplace=True)
            
            # تحويل الأعمدة إلى float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # الاحتفاظ فقط بالأعمدة المهمة
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            logger.info(f"✅ تم جلب {len(df)} شمعة لـ {symbol}")
            return df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ خطأ في الاتصال بـ Binance: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع: {e}")
            return None
    
    def get_current_price(self, symbol: str):
        """
        جلب السعر الحالي للزوج.
        
        Args:
            symbol (str): الزوج (مثل BTCUSDT)
        
        Returns:
            float: السعر الحالي، أو None في حالة الفشل.
        """
        url = f"{self.base_url}/ticker/price"
        params = {"symbol": symbol.upper()}
        
        try:
            resp = self.session.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            price = float(data['price'])
            logger.info(f"💰 السعر الحالي لـ {symbol}: {price}")
            return price
        except Exception as e:
            logger.error(f"❌ فشل جلب السعر الحالي: {e}")
            return None
    
    def get_multiple_prices(self, symbols: list):
        """
        جلب أسعار عدة أزواج دفعة واحدة.
        
        Args:
            symbols (list): قائمة بالأزواج (مثل ['BTCUSDT', 'ETHUSDT'])
        
        Returns:
            dict: {symbol: price}
        """
        url = f"{self.base_url}/ticker/price"
        try:
            resp = self.session.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            result = {}
            for item in data:
                if item['symbol'] in symbols:
                    result[item['symbol']] = float(item['price'])
            return result
        except Exception as e:
            logger.error(f"❌ فشل جلب الأسعار المتعددة: {e}")
            return {}
    
    def get_server_time(self):
        """جلب وقت الخادم (للتزامن)"""
        url = f"{self.base_url}/time"
        try:
            resp = self.session.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json()['serverTime']
        except:
            return int(time.time() * 1000)


# اختبار سريع للتحقق من الاتصال
if __name__ == "__main__":
    print("="*50)
    print("🧪 اختبار الاتصال بـ Binance")
    print("="*50)
    
    broker = BinanceBroker()
    
    # 1. اختبار الاتصال
    if broker._check_connection():
        print("✅ الاتصال بـ Binance ناجح")
    else:
        print("❌ فشل الاتصال بـ Binance")
        exit()
    
    # 2. جلب بيانات BTCUSDT
    df = broker.get_candles("BTCUSDT", "15m", 10)
    if df is not None:
        print("\n📊 آخر 5 شموع لـ BTCUSDT:")
        print(df.tail())
    
    # 3. جلب السعر الحالي
    price = broker.get_current_price("BTCUSDT")
    if price:
        print(f"\n💰 سعر BTCUSDT الحالي: ${price:.2f}")
    
    print("\n✅ تم الانتهاء من الاختبار")

# app/broker.py
import requests
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# ============================================================
# CoinCap Broker (مجاني، بدون مفتاح، يعمل على Render)
# ============================================================
class CoinCapBroker:
    def __init__(self):
        self.base_url = "https://api.coincap.io/v2"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        })
    
    def get_candles(self, symbol, interval="15m", limit=100):
        # تحويل الرمز إلى صيغة CoinCap (BTCUSDT → bitcoin)
        symbol_map = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binance-coin",
            "SOLUSDT": "solana",
            "XRPUSDT": "xrp",
            "ADAUSDT": "cardano"
        }
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())
        
        # تحويل الإطار الزمني
        interval_map = {
            "1m": "m1", "5m": "m5", "15m": "m15",
            "30m": "m30", "1h": "h1", "2h": "h2",
            "6h": "h6", "12h": "h12", "1d": "d1"
        }
        coin_interval = interval_map.get(interval, "m15")
        
        url = f"{self.base_url}/assets/{coin_id}/history"
        params = {
            "interval": coin_interval,
            "limit": limit
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if not data or 'data' not in data:
                logger.warning(f"⚠️ بيانات فارغة لـ {symbol}")
                return None
            
            # تحويل إلى DataFrame
            candles = data['data']
            if not candles:
                return None
            
            df = pd.DataFrame(candles)
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            df.rename(columns={
                'priceUsd': 'close',
                'volumeUsd': 'volume'
            }, inplace=True)
            
            # إضافة أعمدة open, high, low (CoinCap لا يوفرها مباشرة، نستخدم close كتقريب)
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']
            
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
            logger.info(f"✅ تم جلب {len(df)} شمعة لـ {symbol}")
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ فشل طلب CoinCap لـ {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع: {e}")
            return None
    
    def get_current_price(self, symbol):
        symbol_map = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binance-coin",
            "SOLUSDT": "solana",
            "XRPUSDT": "xrp",
            "ADAUSDT": "cardano"
        }
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())
        url = f"{self.base_url}/assets/{coin_id}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return float(data['data']['priceUsd'])
        except Exception as e:
            logger.error(f"❌ فشل جلب السعر الحالي: {e}")
            return None

# ============================================================
# Binance Broker (احتياطي)
# ============================================================
class BinanceBroker:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        })
    
    def get_candles(self, symbol, interval="15m", limit=100):
        url = f"{self.base_url}/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None
            df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume',
                                             'close_time', 'quote_vol', 'trades', 'taker_buy_base',
                                             'taker_buy_quote', 'ignore'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            df.set_index('time', inplace=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Binance error: {e}")
            return None
    
    def get_current_price(self, symbol):
        url = f"{self.base_url}/ticker/price"
        try:
            resp = self.session.get(url, params={"symbol": symbol.upper()}, timeout=10)
            return float(resp.json()['price'])
        except:
            return None

# ============================================================
# اختيار المصدر تلقائياً (Binance أولاً، ثم CoinCap)
# ============================================================
class DataBroker:
    def __init__(self):
        self.binance = BinanceBroker()
        self.coincap = CoinCapBroker()
    
    def get_candles(self, symbol, interval="15m", limit=100):
        # حاول Binance أولاً
        df = self.binance.get_candles(symbol, interval, limit)
        if df is not None and not df.empty:
            return df
        
        # إذا فشل، استخدم CoinCap
        logger.info(f"🔄 استخدام CoinCap كبديل لـ {symbol}")
        return self.coincap.get_candles(symbol, interval, limit)
    
    def get_current_price(self, symbol):
        price = self.binance.get_current_price(symbol)
        if price:
            return price
        return self.coincap.get_current_price(symbol)

# للتوافق مع الكود القديم (احتفظ بالاسم)
BinanceBroker = DataBroker

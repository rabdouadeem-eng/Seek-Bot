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
        symbol_map = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binance-coin",
            "SOLUSDT": "solana",
            "XRPUSDT": "xrp",
            "ADAUSDT": "cardano"
        }
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())

        interval_map = {
            "1m": "m1", "5m": "m5", "15m": "m15",
            "30m": "m30", "1h": "h1", "2h": "h2",
            "6h": "h6", "12h": "h12", "1d": "d1"
        }
        coin_interval = interval_map.get(interval, "m15")

        url = f"{self.base_url}/assets/{coin_id}/history"
        params = {"interval": coin_interval, "limit": limit}

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if not data or 'data' not in data:
                logger.warning(f"⚠️ بيانات فارغة لـ {symbol}")
                return None

            candles = data['data']
            if not candles:
                return None

            df = pd.DataFrame(candles)
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            df.rename(columns={'priceUsd': 'close', 'volumeUsd': 'volume'}, inplace=True)

            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']

            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

            logger.info(f"✅ تم جلب {len(df)} شمعة لـ {symbol} (CoinCap)")
            return df[['open', 'high', 'low', 'close', 'volume']]

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ فشل طلب CoinCap لـ {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع (CoinCap): {e}")
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
            logger.error(f"❌ فشل جلب السعر الحالي (CoinCap): {e}")
            return None


# ============================================================
# Binance Broker (كريبتو)
# ============================================================
class BinanceAPIBroker:
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
            logger.info(f"✅ تم جلب {len(df)} شمعة لـ {symbol} (Binance)")
            return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"❌ فشل طلب Binance لـ {symbol}: {e}")
            return None

    def get_current_price(self, symbol):
        url = f"{self.base_url}/ticker/price"
        try:
            resp = self.session.get(url, params={"symbol": symbol.upper()}, timeout=10)
            resp.raise_for_status()
            return float(resp.json()['price'])
        except Exception as e:
            logger.error(f"❌ فشل جلب السعر الحالي (Binance): {e}")
            return None


# ============================================================
# Yahoo Finance Broker (الذهب/الفضة/الفوركس - XAUUSD, EURUSD...)
# ============================================================
class YahooBroker:
    def __init__(self):
        self._yf = None
        try:
            import yfinance as yf
            self._yf = yf
        except ImportError:
            logger.error("❌ حزمة yfinance غير مثبتة (أضفها إلى requirements.txt)")

    _interval_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "60m", "2h": "60m", "1d": "1d"
    }
    _period_map = {
        "1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d",
        "1h": "730d", "2h": "730d", "1d": "5y"
    }

    def get_candles(self, symbol, interval="15m", limit=100):
        if self._yf is None:
            return None
        yf_interval = self._interval_map.get(interval, "15m")
        yf_period = self._period_map.get(interval, "60d")
        try:
            ticker = self._yf.Ticker(symbol)
            df = ticker.history(period=yf_period, interval=yf_interval)
            if df is None or df.empty:
                logger.warning(f"⚠️ بيانات فارغة لـ {symbol} (Yahoo)")
                return None
            df = df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume"
            })
            df = df[["open", "high", "low", "close", "volume"]].tail(limit)
            logger.info(f"✅ تم جلب {len(df)} شمعة لـ {symbol} (Yahoo)")
            return df
        except Exception as e:
            logger.error(f"❌ فشل طلب Yahoo لـ {symbol}: {e}")
            return None

    def get_current_price(self, symbol):
        if self._yf is None:
            return None
        try:
            ticker = self._yf.Ticker(symbol)
            df = ticker.history(period="1d", interval="1m")
            if df is None or df.empty:
                return None
            return float(df["Close"].iloc[-1])
        except Exception as e:
            logger.error(f"❌ فشل جلب السعر الحالي (Yahoo): {e}")
            return None


# ============================================================
# اختيار المصدر حسب Config.DATA_SOURCE
#   - "yahoo": Yahoo فقط (للذهب/الفضة/الفوركس، مثل XAUUSD=X)
#   - "binance" (افتراضي): Binance ثم CoinCap كبديل (للكريبتو)
# ============================================================
class DataBroker:
    def __init__(self):
        self.binance = BinanceAPIBroker()
        self.coincap = CoinCapBroker()
        self.yahoo = YahooBroker()

        try:
            from .config import Config
            self.data_source = getattr(Config, "DATA_SOURCE", "binance")
        except Exception:
            self.data_source = "binance"

    def get_candles(self, symbol, interval="15m", limit=100):
        if self.data_source == "yahoo":
            df = self.yahoo.get_candles(symbol, interval, limit)
            if df is not None and not df.empty:
                return df
            logger.warning(f"⚠️ Yahoo فشل لـ {symbol}، لا يوجد بديل مهيأ لهذا الرمز")
            return None

        # المسار الافتراضي: كريبتو عبر Binance ثم CoinCap
        df = self.binance.get_candles(symbol, interval, limit)
        if df is not None and not df.empty:
            return df

        logger.info(f"🔄 استخدام CoinCap كبديل لـ {symbol}")
        return self.coincap.get_candles(symbol, interval, limit)

    def get_current_price(self, symbol):
        if self.data_source == "yahoo":
            return self.yahoo.get_current_price(symbol)

        price = self.binance.get_current_price(symbol)
        if price:
            return price
        return self.coincap.get_current_price(symbol)

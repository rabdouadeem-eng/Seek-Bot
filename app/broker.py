# app/broker.py
import requests
import pandas as pd
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

# ============================================================
# Binance Broker (للعملات الرقمية)
# ============================================================
class BinanceBroker:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
    
    def get_candles(self, symbol, interval="15m", limit=100):
        url = f"{self.base_url}/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        try:
            resp = requests.get(url, params=params, timeout=10)
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
            resp = requests.get(url, params={"symbol": symbol.upper()}, timeout=5)
            return float(resp.json()['price'])
        except:
            return None

# ============================================================
# Yahoo Broker (للذهب والفوركس – بدون API Key)
# ============================================================
class YahooBroker:
    def __init__(self):
        pass
    
    def get_candles(self, symbol, interval="15m", limit=100):
        tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                  "1h": "60m", "4h": "240m", "1d": "1d"}
        yf_interval = tf_map.get(interval, "15m")
        days = max(7, limit // 10 + 1)
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f"{days}d", interval=yf_interval)
            if df.empty:
                return None
            df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low',
                                    'Close': 'close', 'Volume': 'volume'})
            if len(df) > limit:
                df = df.iloc[-limit:]
            return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Yahoo error: {e}")
            return None
    
    def get_current_price(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
            return None
        except:
            return None

import requests
import time
import hmac
import hashlib
import base64
import random
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class KuCoinClient:
    def __init__(self, api_key: str = "", api_secret: str = "", api_passphrase: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.base_url = "https://api.kucoin.com"
        self.session = requests.Session()

        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'crypto-telegram-bot/1.0'
        })

        # Check if we have API keys
        self.has_keys = bool(api_key and api_secret and api_passphrase)
        if self.has_keys:
            logger.info("KuCoin client initialized with API keys")
        else:
            logger.info("KuCoin client initialized with demo data")

    def _generate_signature(self, timestamp: str, method: str, endpoint: str, body: str = "") -> str:
        """Generate API signature"""
        if not self.api_secret:
            return ""

        message = timestamp + method + endpoint + body
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')

        return signature

    def _get_headers(self, method: str, endpoint: str, body: str = "") -> Dict:
        """Get request headers with signature"""
        timestamp = str(int(time.time() * 1000))

        headers = {
            'KC-API-TIMESTAMP': timestamp,
            'KC-API-KEY': self.api_key,
        }

        if self.has_keys:
            signature = self._generate_signature(timestamp, method, endpoint, body)
            passphrase = base64.b64encode(
                hmac.new(
                    self.api_secret.encode('utf-8'),
                    self.api_passphrase.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode('utf-8')

            headers.update({
                'KC-API-SIGN': signature,
                'KC-API-PASSPHRASE': passphrase,
                'KC-API-KEY-VERSION': '2'
            })

        return headers

    async def get_klines(self, symbol: str, interval: str = "5min", limit: int = 200) -> List[List]:
        """Get candlestick data"""
        try:
            if not self.has_keys:
                return self._get_demo_klines(symbol, limit)

            endpoint = f"/api/v1/market/candles"

            # Convert interval format
            interval_map = {
                "1min": "1min",
                "5min": "5min", 
                "15min": "15min",
                "1hour": "1hour",
                "1day": "1day"
            }
            kucoin_interval = interval_map.get(interval, "5min")

            # Calculate time range
            interval_seconds = {
                "1min": 60,
                "5min": 300,
                "15min": 900,
                "1hour": 3600,
                "1day": 86400
            }

            seconds = interval_seconds.get(kucoin_interval, 300)
            start_time = int(time.time() - (limit * seconds))
            end_time = int(time.time())

            params = {
                'symbol': symbol,
                'type': kucoin_interval,
                'startAt': start_time,
                'endAt': end_time
            }

            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self._get_headers('GET', endpoint),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200000' and data.get('data'):
                    return data['data']

            logger.warning(f"KuCoin API error, using demo data: {response.status_code}")
            return self._get_demo_klines(symbol, limit)

        except Exception as e:
            logger.error(f"Error getting klines: {e}")
            return self._get_demo_klines(symbol, limit)

    def _get_demo_klines(self, symbol: str, limit: int) -> List[List]:
        """Generate realistic demo candlestick data"""
        demo_data = []

        # Base prices for different symbols
        base_prices = {
            'BTC-USDT': 45000,
            'ETH-USDT': 3000, 
            'SOL-USDT': 120
        }

        base_price = base_prices.get(symbol, 45000)
        current_time = int(time.time())

        # Generate trend direction
        trend_direction = random.choice([1, -1])  # 1 for up, -1 for down

        for i in range(limit):
            timestamp = current_time - (i * 300)  # 5 min intervals

            # Add trend and volatility
            trend_factor = (limit - i) / limit * trend_direction * 0.02  # 2% trend over period
            volatility = random.uniform(-0.01, 0.01)  # 1% random volatility

            price_multiplier = 1 + trend_factor + volatility

            open_price = base_price * price_multiplier
            close_price = open_price * (1 + random.uniform(-0.005, 0.005))  # 0.5% candle range
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.003))  # Wick up
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.003))   # Wick down
            volume = random.uniform(50, 200)

            # KuCoin format: [time, open, close, high, low, volume, turnover]
            demo_data.append([
                str(timestamp),
                str(round(open_price, 2)),
                str(round(close_price, 2)),
                str(round(high_price, 2)),
                str(round(low_price, 2)),
                str(round(volume, 4)),
                str(round(volume * close_price, 2))
            ])

        return list(reversed(demo_data))  # Return chronological order

    async def get_orderbook(self, symbol: str) -> Dict:
        """Get order book data"""
        try:
            if not self.has_keys:
                return self._get_demo_orderbook(symbol)

            endpoint = f"/api/v1/market/orderbook/level2_20"
            params = {'symbol': symbol}

            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self._get_headers('GET', endpoint),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200000' and data.get('data'):
                    return data['data']

            logger.warning(f"KuCoin orderbook error, using demo data: {response.status_code}")
            return self._get_demo_orderbook(symbol)

        except Exception as e:
            logger.error(f"Error getting orderbook: {e}")
            return self._get_demo_orderbook(symbol)

    def _get_demo_orderbook(self, symbol: str) -> Dict:
        """Generate realistic demo orderbook data"""
        base_prices = {
            'BTC-USDT': 45000,
            'ETH-USDT': 3000,
            'SOL-USDT': 120
        }

        base_price = base_prices.get(symbol, 45000)
        spread_pct = random.uniform(0.0001, 0.0005)  # 0.01% to 0.05% spread
        spread = base_price * spread_pct

        bids = []
        asks = []

        # Generate realistic bid/ask levels
        for i in range(20):
            # Bid levels (below mid price)
            bid_price = base_price - spread/2 - (i * base_price * 0.0001)
            bid_size = random.uniform(0.1, 10.0) * (1 / (1 + i * 0.1))  # Decreasing size
            bids.append([str(round(bid_price, 2)), str(round(bid_size, 4))])

            # Ask levels (above mid price)  
            ask_price = base_price + spread/2 + (i * base_price * 0.0001)
            ask_size = random.uniform(0.1, 10.0) * (1 / (1 + i * 0.1))  # Decreasing size
            asks.append([str(round(ask_price, 2)), str(round(ask_size, 4))])

        return {
            'bids': bids,
            'asks': asks,
            'sequence': str(int(time.time()))
        }

    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker data"""
        try:
            if not self.has_keys:
                return {}

            endpoint = f"/api/v1/market/orderbook/level1"
            params = {'symbol': symbol}

            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self._get_headers('GET', endpoint),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200000' and data.get('data'):
                    return data['data']

            return {}

        except Exception as e:
            logger.error(f"Error getting ticker: {e}")
            return {}
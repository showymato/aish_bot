import asyncio
from typing import Dict, Optional
import logging

from utils.indicators import TechnicalIndicators
from utils.sr_levels import SRLevels
from utils.orderbook import OrderBookAnalyzer

logger = logging.getLogger(__name__)

class BTCStrategy:
    def __init__(self, kucoin_client):
        self.client = kucoin_client
        self.symbol = "BTC-USDT"
        self.indicators = TechnicalIndicators()
        self.sr_calculator = SRLevels()
        self.orderbook_analyzer = OrderBookAnalyzer()

    def safe_value(self, value, default):
        """Safely handle NaN values"""
        try:
            if value is None or (isinstance(value, float) and str(value).lower() == 'nan'):
                return default
            return float(value)
        except:
            return default

    async def get_signal(self) -> Optional[Dict]:
        """Get BTC strategy signal - Trend Rider + S/R Filter"""
        try:
            # Get market data
            klines = await self.client.get_klines(self.symbol, "5min", 200)
            orderbook = await self.client.get_orderbook(self.symbol)

            if not klines:
                logger.warning("No klines data for BTC")
                return None

            # Parse OHLCV data - KuCoin format: [time, open, close, high, low, volume, turnover]
            closes = [float(k[2]) for k in klines]
            highs = [float(k[3]) for k in klines]
            lows = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            if len(closes) < 50:  # Minimum data required
                logger.warning("Insufficient data for BTC analysis")
                return None

            # Calculate indicators
            ema50 = self.indicators.ema(closes, 50)
            ema200 = self.indicators.ema(closes, 200)
            rsi = self.indicators.rsi(closes, 14)
            atr = self.indicators.atr(highs, lows, closes, 14)
            vwap = self.indicators.vwap(highs, lows, closes, volumes)

            # Current values (safely handle NaN)
            current_price = closes[-1]
            current_ema50 = self.safe_value(ema50[-1], current_price)
            current_ema200 = self.safe_value(ema200[-1], current_price)
            current_rsi = self.safe_value(rsi[-1], 50)
            current_atr = self.safe_value(atr[-1], current_price * 0.02)
            current_vwap = self.safe_value(vwap[-1], current_price)

            # Calculate S/R levels
            pivot_levels = self.sr_calculator.pivot_points(highs[-1], lows[-1], closes[-1])
            weekly_levels = self.sr_calculator.weekly_high_low(highs, lows, min(168, len(highs)))

            # Analyze orderbook
            orderbook_data = self.orderbook_analyzer.analyze_depth(orderbook)

            # Strategy Logic: Trend Rider + S/R Filter
            signal = None
            confidence = 0.5

            # Long conditions
            if (current_ema50 > current_ema200 and 
                current_price > current_vwap and 
                current_rsi > 50):

                # Check if near support
                near_s1 = self.sr_calculator.is_near_level(current_price, pivot_levels['S1'], 1.0)
                near_s2 = self.sr_calculator.is_near_level(current_price, pivot_levels['S2'], 1.0)
                near_weekly_low = self.sr_calculator.is_near_level(current_price, weekly_levels['weekly_low'], 1.5)

                if near_s1 or near_s2 or near_weekly_low or current_price > pivot_levels['S1']:
                    signal = "LONG"
                    confidence += 0.2

                    # Orderbook confirmation
                    if orderbook_data['imbalance'] > 0.1:
                        confidence += 0.1

            # Short conditions  
            elif (current_ema50 < current_ema200 and 
                  current_price < current_vwap and 
                  current_rsi < 50):

                # Check if near resistance
                near_r1 = self.sr_calculator.is_near_level(current_price, pivot_levels['R1'], 1.0)
                near_r2 = self.sr_calculator.is_near_level(current_price, pivot_levels['R2'], 1.0)
                near_weekly_high = self.sr_calculator.is_near_level(current_price, weekly_levels['weekly_high'], 1.5)

                if near_r1 or near_r2 or near_weekly_high or current_price < pivot_levels['R1']:
                    signal = "SHORT"
                    confidence += 0.2

                    # Orderbook confirmation
                    if orderbook_data['imbalance'] < -0.1:
                        confidence += 0.1

            if not signal:
                signal = "HOLD"
                confidence = 0.3

            # Calculate entry, SL, TP
            entry_price = current_price

            if signal == "LONG":
                stop_loss = max(pivot_levels['S1'] * 0.999, current_price - (current_atr * 1.0))
                take_profit = min(pivot_levels['R1'], current_price + (current_atr * 1.5))
            elif signal == "SHORT":
                stop_loss = min(pivot_levels['R1'] * 1.001, current_price + (current_atr * 1.0))
                take_profit = max(pivot_levels['S1'], current_price - (current_atr * 1.5))
            else:
                stop_loss = current_price * 0.98
                take_profit = current_price * 1.02

            return {
                'symbol': 'BTC/USDT',
                'side': signal,
                'entry': round(entry_price, 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'sr_levels': {
                    'S1': pivot_levels['S1'],
                    'S2': pivot_levels['S2'],
                    'R1': pivot_levels['R1'],
                    'R2': pivot_levels['R2']
                },
                'orderbook_bias': orderbook_data['bias'],
                'confidence': min(confidence, 0.95),
                'strategy_name': 'Trend Rider + S/R Filter',
                'current_rsi': round(current_rsi, 1),
                'current_atr': round(current_atr, 2)
            }

        except Exception as e:
            logger.error(f"BTC strategy error: {e}")
            return None
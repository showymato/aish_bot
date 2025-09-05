import asyncio
from typing import Dict, Optional
import logging

from utils.indicators import TechnicalIndicators
from utils.sr_levels import SRLevels
from utils.orderbook import OrderBookAnalyzer

logger = logging.getLogger(__name__)

class ETHStrategy:
    def __init__(self, kucoin_client):
        self.client = kucoin_client
        self.symbol = "ETH-USDT"
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
        """Get ETH strategy signal - Mean Reversion + Breakout + S/R"""
        try:
            # Get market data
            klines = await self.client.get_klines(self.symbol, "15min", 100)
            orderbook = await self.client.get_orderbook(self.symbol)

            if not klines:
                return None

            # Parse OHLCV data
            closes = [float(k[2]) for k in klines]
            highs = [float(k[3]) for k in klines]
            lows = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            if len(closes) < 30:
                return None

            # Calculate indicators
            bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(closes, 20, 2)
            ema20 = self.indicators.ema(closes, 20)
            ema50 = self.indicators.ema(closes, 50)
            macd_line, macd_signal, macd_hist = self.indicators.macd(closes, 12, 26, 9)

            # Current values (safely handle NaN)
            current_price = closes[-1]
            current_bb_upper = self.safe_value(bb_upper[-1], current_price * 1.02)
            current_bb_lower = self.safe_value(bb_lower[-1], current_price * 0.98)
            current_bb_middle = self.safe_value(bb_middle[-1], current_price)
            current_ema20 = self.safe_value(ema20[-1], current_price)
            current_ema50 = self.safe_value(ema50[-1], current_price)
            current_macd_hist = self.safe_value(macd_hist[-1], 0)

            # Calculate S/R levels
            pivot_levels = self.sr_calculator.pivot_points(highs[-1], lows[-1], closes[-1])

            # Analyze orderbook
            orderbook_data = self.orderbook_analyzer.analyze_depth(orderbook)

            # Strategy Logic: Mean Reversion + Breakout
            signal = None
            confidence = 0.5

            # Long conditions (mean reversion from lower BB)
            if (current_price <= current_bb_lower and 
                current_ema20 > current_ema50 and 
                current_macd_hist > 0):

                # Check if support zone holds
                near_s1 = self.sr_calculator.is_near_level(current_price, pivot_levels['S1'], 1.0)
                if near_s1 or current_price > pivot_levels['S2']:
                    signal = "LONG"
                    confidence += 0.25

            # Short conditions (mean reversion from upper BB)
            elif (current_price >= current_bb_upper and 
                  current_ema20 < current_ema50 and 
                  current_macd_hist < 0):

                # Check if resistance zone rejects
                near_r1 = self.sr_calculator.is_near_level(current_price, pivot_levels['R1'], 1.0)
                if near_r1 or current_price < pivot_levels['R2']:
                    signal = "SHORT"
                    confidence += 0.25

            # Breakout conditions
            elif current_price > current_bb_upper and current_ema20 > current_ema50:
                # Bullish breakout above resistance
                if current_price > pivot_levels['R1']:
                    signal = "LONG"
                    confidence += 0.2
            elif current_price < current_bb_lower and current_ema20 < current_ema50:
                # Bearish breakdown below support
                if current_price < pivot_levels['S1']:
                    signal = "SHORT" 
                    confidence += 0.2

            if not signal:
                signal = "HOLD"
                confidence = 0.3

            # Orderbook confirmation
            if signal == "LONG" and orderbook_data['imbalance'] > 0.1:
                confidence += 0.15
            elif signal == "SHORT" and orderbook_data['imbalance'] < -0.1:
                confidence += 0.15

            # Calculate entry, SL, TP
            entry_price = current_price
            atr_estimate = (max(highs[-20:]) - min(lows[-20:])) / 20  # Simple ATR estimate

            if signal == "LONG":
                stop_loss = max(current_bb_lower * 0.995, current_price - atr_estimate)
                take_profit = current_bb_middle
            elif signal == "SHORT":
                stop_loss = min(current_bb_upper * 1.005, current_price + atr_estimate)
                take_profit = current_bb_middle
            else:
                stop_loss = current_price * 0.98
                take_profit = current_price * 1.02

            return {
                'symbol': 'ETH/USDT',
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
                'strategy_name': 'Mean Reversion + Breakout',
                'bb_position': 'Upper' if current_price > current_bb_upper else 'Lower' if current_price < current_bb_lower else 'Middle'
            }

        except Exception as e:
            logger.error(f"ETH strategy error: {e}")
            return None
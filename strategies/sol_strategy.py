import asyncio
from typing import Dict, Optional
import logging

from utils.indicators import TechnicalIndicators
from utils.sr_levels import SRLevels
from utils.orderbook import OrderBookAnalyzer

logger = logging.getLogger(__name__)

class SOLStrategy:
    def __init__(self, kucoin_client):
        self.client = kucoin_client
        self.symbol = "SOL-USDT"
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
        """Get SOL strategy signal - Scalper Momentum + S/R Zones"""
        try:
            # Get market data (1min for scalping)
            klines = await self.client.get_klines(self.symbol, "1min", 100)
            orderbook = await self.client.get_orderbook(self.symbol)

            if not klines:
                return None

            # Parse OHLCV data
            closes = [float(k[2]) for k in klines]
            highs = [float(k[3]) for k in klines]
            lows = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            if len(closes) < 25:
                return None

            # Calculate indicators
            ema9 = self.indicators.ema(closes, 9)
            ema21 = self.indicators.ema(closes, 21)
            stoch_k, stoch_d = self.indicators.stochastic_rsi(closes, 14, 3, 3)
            obv = self.indicators.obv(closes, volumes)
            vwap = self.indicators.vwap(highs, lows, closes, volumes)

            # Current values (safely handle NaN)
            current_price = closes[-1]
            current_ema9 = self.safe_value(ema9[-1], current_price)
            current_ema21 = self.safe_value(ema21[-1], current_price)
            current_stoch_k = self.safe_value(stoch_k[-1], 50)
            current_vwap = self.safe_value(vwap[-1], current_price)

            # OBV trend (rising/falling)
            obv_trend = "rising" if len(obv) >= 3 and self.safe_value(obv[-1], 0) > self.safe_value(obv[-3], 0) else "falling"

            # Previous day high/low (simulate with recent high/low)
            pd_high = max(highs[-min(60, len(highs)):])
            pd_low = min(lows[-min(60, len(lows)):])

            # Calculate S/R levels
            pivot_levels = self.sr_calculator.pivot_points(highs[-1], lows[-1], closes[-1])
            vwap_bands = self.sr_calculator.vwap_bands([current_vwap] * 20, 20, 1.0)

            # Analyze orderbook
            orderbook_data = self.orderbook_analyzer.analyze_depth(orderbook)

            # Strategy Logic: Scalper Momentum
            signal = None
            confidence = 0.5

            # Long conditions
            if (current_ema9 > current_ema21 and
                current_stoch_k < 30 and  # Oversold (relaxed from 20)
                current_price > current_vwap and
                obv_trend == "rising"):

                # Check if holding previous day low or intraday support
                near_pd_low = self.sr_calculator.is_near_level(current_price, pd_low, 1.0)
                near_vwap_lower = self.sr_calculator.is_near_level(current_price, vwap_bands['vwap_lower'], 0.5)

                if near_pd_low or near_vwap_lower or current_price > pivot_levels['S1']:
                    signal = "LONG"
                    confidence += 0.3

            # Short conditions
            elif (current_ema9 < current_ema21 and
                  current_stoch_k > 70 and  # Overbought (relaxed from 80)
                  current_price < current_vwap and
                  obv_trend == "falling"):

                # Check if rejecting previous day high or intraday resistance
                near_pd_high = self.sr_calculator.is_near_level(current_price, pd_high, 1.0)
                near_vwap_upper = self.sr_calculator.is_near_level(current_price, vwap_bands['vwap_upper'], 0.5)

                if near_pd_high or near_vwap_upper or current_price < pivot_levels['R1']:
                    signal = "SHORT"
                    confidence += 0.3

            if not signal:
                signal = "HOLD"
                confidence = 0.3

            # Orderbook confirmation (important for scalping)
            if signal == "LONG" and orderbook_data['imbalance'] > 0.15:
                confidence += 0.2
            elif signal == "SHORT" and orderbook_data['imbalance'] < -0.15:
                confidence += 0.2

            # Calculate entry, SL, TP (tight for scalping)
            entry_price = current_price

            if signal == "LONG":
                stop_loss = current_price * 0.9965  # 0.35% SL
                take_profit = current_price * 1.006  # 0.6% TP
            elif signal == "SHORT":
                stop_loss = current_price * 1.0035  # 0.35% SL
                take_profit = current_price * 0.994  # 0.6% TP
            else:
                stop_loss = current_price * 0.99
                take_profit = current_price * 1.01

            return {
                'symbol': 'SOL/USDT',
                'side': signal,
                'entry': round(entry_price, 3),
                'stop_loss': round(stop_loss, 3),
                'take_profit': round(take_profit, 3),
                'sr_levels': {
                    'S1': pivot_levels['S1'],
                    'S2': pivot_levels['S2'],
                    'R1': pivot_levels['R1'],
                    'R2': pivot_levels['R2']
                },
                'orderbook_bias': orderbook_data['bias'],
                'confidence': min(confidence, 0.95),
                'strategy_name': 'Scalper Momentum + S/R',
                'stoch_rsi': round(current_stoch_k, 1),
                'obv_trend': obv_trend,
                'pd_high': round(pd_high, 3),
                'pd_low': round(pd_low, 3)
            }

        except Exception as e:
            logger.error(f"SOL strategy error: {e}")
            return None
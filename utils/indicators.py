import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    @staticmethod
    def safe_float(value, default=0.0) -> float:
        """Safely convert value to float"""
        try:
            if value is None or str(value).lower() in ['nan', 'none']:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def ema(data: List[float], period: int) -> List[float]:
        """Exponential Moving Average"""
        try:
            if len(data) < period:
                return [np.nan] * len(data)

            df = pd.Series(data)
            ema = df.ewm(span=period, adjust=False).mean()
            return ema.tolist()
        except Exception as e:
            logger.error(f"EMA calculation error: {e}")
            return [data[-1]] * len(data) if data else []

    @staticmethod
    def rsi(data: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index"""
        try:
            if len(data) < period + 1:
                return [50.0] * len(data)  # Return neutral RSI

            df = pd.Series(data)
            delta = df.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            # Avoid division by zero
            rs = gain / loss.replace(0, np.inf)
            rsi = 100 - (100 / (1 + rs))

            # Fill NaN values
            rsi = rsi.fillna(50.0)

            return rsi.tolist()
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return [50.0] * len(data) if data else []

    @staticmethod
    def macd(data: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """MACD indicator"""
        try:
            if len(data) < slow:
                zeros = [0.0] * len(data)
                return zeros, zeros, zeros

            df = pd.Series(data)
            ema_fast = df.ewm(span=fast).mean()
            ema_slow = df.ewm(span=slow).mean()

            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line

            # Fill NaN values
            macd_line = macd_line.fillna(0.0)
            signal_line = signal_line.fillna(0.0)
            histogram = histogram.fillna(0.0)

            return macd_line.tolist(), signal_line.tolist(), histogram.tolist()
        except Exception as e:
            logger.error(f"MACD calculation error: {e}")
            zeros = [0.0] * len(data) if data else []
            return zeros, zeros, zeros

    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, std: float = 2) -> Tuple[List[float], List[float], List[float]]:
        """Bollinger Bands"""
        try:
            if len(data) < period:
                return data.copy(), data.copy(), data.copy()

            df = pd.Series(data)
            middle = df.rolling(window=period).mean()
            std_dev = df.rolling(window=period).std()

            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)

            # Fill NaN values
            upper = upper.fillna(method='bfill').fillna(data[-1] * 1.02)
            middle = middle.fillna(method='bfill').fillna(data[-1])
            lower = lower.fillna(method='bfill').fillna(data[-1] * 0.98)

            return upper.tolist(), middle.tolist(), lower.tolist()
        except Exception as e:
            logger.error(f"Bollinger Bands calculation error: {e}")
            return data.copy(), data.copy(), data.copy()

    @staticmethod
    def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
        """Average True Range"""
        try:
            if len(high) < period + 1:
                # Return approximate ATR based on high-low range
                avg_range = sum(h - l for h, l in zip(high, low)) / len(high) if high and low else 100
                return [avg_range] * len(high)

            high_s = pd.Series(high)
            low_s = pd.Series(low)
            close_s = pd.Series(close)

            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift())
            tr3 = abs(low_s - close_s.shift())

            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()

            # Fill NaN values
            atr = atr.fillna(method='bfill').fillna(true_range.mean())

            return atr.tolist()
        except Exception as e:
            logger.error(f"ATR calculation error: {e}")
            avg_range = sum(h - l for h, l in zip(high, low)) / len(high) if high and low else 100
            return [avg_range] * len(high)

    @staticmethod
    def vwap(high: List[float], low: List[float], close: List[float], volume: List[float]) -> List[float]:
        """Volume Weighted Average Price"""
        try:
            if len(close) != len(volume) or len(close) == 0:
                return close.copy()

            typical_price = [(h + l + c) / 3 for h, l, c in zip(high, low, close)]
            pv = [tp * v for tp, v in zip(typical_price, volume)]

            vwap = []
            cum_pv = 0
            cum_vol = 0

            for i in range(len(pv)):
                cum_pv += pv[i]
                cum_vol += volume[i]

                if cum_vol > 0:
                    vwap.append(cum_pv / cum_vol)
                else:
                    vwap.append(close[i])

            return vwap
        except Exception as e:
            logger.error(f"VWAP calculation error: {e}")
            return close.copy()

    @staticmethod
    def stochastic_rsi(data: List[float], period: int = 14, k_period: int = 3, d_period: int = 3) -> Tuple[List[float], List[float]]:
        """Stochastic RSI"""
        try:
            rsi_values = TechnicalIndicators.rsi(data, period)

            if len(rsi_values) < period:
                neutral = [50.0] * len(data)
                return neutral, neutral

            rsi_s = pd.Series(rsi_values)

            # Calculate %K
            lowest_rsi = rsi_s.rolling(window=period).min()
            highest_rsi = rsi_s.rolling(window=period).max()

            # Avoid division by zero
            rsi_range = highest_rsi - lowest_rsi
            rsi_range = rsi_range.replace(0, 100)  # If no range, use 100

            k_percent = 100 * ((rsi_s - lowest_rsi) / rsi_range)
            k_smoothed = k_percent.rolling(window=k_period).mean()
            d_smoothed = k_smoothed.rolling(window=d_period).mean()

            # Fill NaN values
            k_smoothed = k_smoothed.fillna(50.0)
            d_smoothed = d_smoothed.fillna(50.0)

            return k_smoothed.tolist(), d_smoothed.tolist()
        except Exception as e:
            logger.error(f"Stochastic RSI calculation error: {e}")
            neutral = [50.0] * len(data)
            return neutral, neutral

    @staticmethod
    def obv(close: List[float], volume: List[float]) -> List[float]:
        """On Balance Volume"""
        try:
            if len(close) != len(volume) or len(close) < 2:
                return [0.0] * len(close)

            obv = [0]

            for i in range(1, len(close)):
                if close[i] > close[i-1]:
                    obv.append(obv[-1] + volume[i])
                elif close[i] < close[i-1]:
                    obv.append(obv[-1] - volume[i])
                else:
                    obv.append(obv[-1])

            return obv
        except Exception as e:
            logger.error(f"OBV calculation error: {e}")
            return [0.0] * len(close)
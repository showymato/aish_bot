import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class SRLevels:
    @staticmethod
    def safe_float(value, default=0.0) -> float:
        """Safely convert value to float"""
        try:
            if value is None or (isinstance(value, float) and np.isnan(value)):
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
        """Calculate daily pivot points"""
        try:
            pivot = (high + low + close) / 3

            r1 = (2 * pivot) - low
            s1 = (2 * pivot) - high
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            r3 = high + 2 * (pivot - low)
            s3 = low - 2 * (high - pivot)

            return {
                'P': round(pivot, 2),
                'R1': round(r1, 2),
                'R2': round(r2, 2),
                'R3': round(r3, 2),
                'S1': round(s1, 2),
                'S2': round(s2, 2),
                'S3': round(s3, 2)
            }
        except Exception as e:
            logger.error(f"Pivot points calculation error: {e}")
            return {
                'P': round(close, 2),
                'R1': round(close * 1.01, 2),
                'R2': round(close * 1.02, 2),
                'R3': round(close * 1.03, 2),
                'S1': round(close * 0.99, 2),
                'S2': round(close * 0.98, 2),
                'S3': round(close * 0.97, 2)
            }

    @staticmethod
    def weekly_high_low(highs: List[float], lows: List[float], periods: int = 168) -> Dict[str, float]:
        """Calculate weekly high/low"""
        try:
            if not highs or not lows:
                return {'weekly_high': 0, 'weekly_low': 0}

            if len(highs) < periods:
                periods = len(highs)

            if periods == 0:
                return {'weekly_high': 0, 'weekly_low': 0}

            recent_highs = highs[-periods:]
            recent_lows = lows[-periods:]

            return {
                'weekly_high': round(max(recent_highs), 2),
                'weekly_low': round(min(recent_lows), 2)
            }
        except Exception as e:
            logger.error(f"Weekly high/low calculation error: {e}")
            last_price = highs[-1] if highs else 1000
            return {
                'weekly_high': round(last_price * 1.1, 2),
                'weekly_low': round(last_price * 0.9, 2)
            }

    @staticmethod
    def vwap_bands(vwap_values: List[float], period: int = 20, multiplier: float = 1.0) -> Dict[str, float]:
        """Calculate VWAP bands as dynamic S/R"""
        try:
            if len(vwap_values) < period or period == 0:
                return {'vwap_upper': 0, 'vwap_lower': 0}

            recent_vwap = vwap_values[-period:]
            # Filter out NaN values
            valid_vwap = [v for v in recent_vwap if v is not None and not (isinstance(v, float) and np.isnan(v))]

            if not valid_vwap:
                return {'vwap_upper': 0, 'vwap_lower': 0}

            vwap_std = np.std(valid_vwap)
            current_vwap = valid_vwap[-1] if valid_vwap else 0

            return {
                'vwap_upper': round(current_vwap + (vwap_std * multiplier), 2),
                'vwap_lower': round(current_vwap - (vwap_std * multiplier), 2)
            }
        except Exception as e:
            logger.error(f"VWAP bands calculation error: {e}")
            last_vwap = vwap_values[-1] if vwap_values else 1000
            return {
                'vwap_upper': round(last_vwap * 1.01, 2),
                'vwap_lower': round(last_vwap * 0.99, 2)
            }

    @staticmethod
    def is_near_level(price: float, level: float, tolerance_pct: float = 0.5) -> bool:
        """Check if price is near a support/resistance level"""
        try:
            if level == 0:
                return False

            tolerance = level * (tolerance_pct / 100)
            return abs(price - level) <= tolerance
        except Exception as e:
            logger.error(f"Level proximity check error: {e}")
            return False

    @staticmethod
    def find_nearest_sr(price: float, sr_levels: Dict) -> Dict[str, float]:
        """Find nearest support and resistance levels"""
        try:
            resistance_levels = sr_levels.get('resistance', [])
            support_levels = sr_levels.get('support', [])

            # Find nearest resistance above current price
            resistance_above = [r for r in resistance_levels if r > price]
            nearest_resistance = min(resistance_above) if resistance_above else sr_levels.get('R1', price * 1.02)

            # Find nearest support below current price  
            support_below = [s for s in support_levels if s < price]
            nearest_support = max(support_below) if support_below else sr_levels.get('S1', price * 0.98)

            return {
                'nearest_resistance': nearest_resistance,
                'nearest_support': nearest_support
            }
        except Exception as e:
            logger.error(f"Nearest S/R calculation error: {e}")
            return {
                'nearest_resistance': price * 1.02,
                'nearest_support': price * 0.98
            }
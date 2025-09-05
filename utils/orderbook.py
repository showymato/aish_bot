from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class OrderBookAnalyzer:
    @staticmethod
    def analyze_depth(orderbook: Dict) -> Dict:
        """Analyze order book depth and imbalance"""
        try:
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return {
                    'bid_depth': 0,
                    'ask_depth': 0,
                    'imbalance': 0,
                    'spread': 0,
                    'midprice': 0,
                    'bias': 'Neutral'
                }

            bids = orderbook['bids']
            asks = orderbook['asks']

            if not bids or not asks:
                return {
                    'bid_depth': 0,
                    'ask_depth': 0,
                    'imbalance': 0,
                    'spread': 0,
                    'midprice': 0,
                    'bias': 'Neutral'
                }

            # Calculate depths (sum of sizes in top 10 levels)
            bid_depth = sum(float(bid[1]) for bid in bids[:10] if len(bid) > 1)
            ask_depth = sum(float(ask[1]) for ask in asks[:10] if len(ask) > 1)

            # Calculate imbalance (-1 to 1, positive = bullish)
            total_depth = bid_depth + ask_depth
            imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0

            # Best bid/ask prices
            best_bid = float(bids[0][0]) if len(bids[0]) > 0 else 0
            best_ask = float(asks[0][0]) if len(asks[0]) > 0 else 0

            # Spread and midprice
            spread = best_ask - best_bid if best_bid > 0 and best_ask > 0 else 0
            midprice = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else 0

            # Determine bias
            if imbalance > 0.2:
                bias = "Bullish (strong bid depth)"
            elif imbalance < -0.2:
                bias = "Bearish (strong ask depth)"
            else:
                bias = "Neutral"

            return {
                'bid_depth': round(bid_depth, 2),
                'ask_depth': round(ask_depth, 2),
                'imbalance': round(imbalance, 3),
                'spread': round(spread, 2),
                'midprice': round(midprice, 2),
                'bias': bias,
                'best_bid': best_bid,
                'best_ask': best_ask
            }

        except Exception as e:
            logger.error(f"Error analyzing orderbook: {e}")
            return {
                'bid_depth': 0,
                'ask_depth': 0,
                'imbalance': 0,
                'spread': 0,
                'midprice': 0,
                'bias': 'Error'
            }

    @staticmethod
    def detect_walls(orderbook: Dict, threshold_multiplier: float = 3.0) -> Dict:
        """Detect large bid/ask walls"""
        try:
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return {'bid_walls': [], 'ask_walls': []}

            bids = orderbook['bids'][:20]  # Top 20 levels
            asks = orderbook['asks'][:20]

            if not bids or not asks:
                return {'bid_walls': [], 'ask_walls': []}

            # Calculate average sizes
            bid_sizes = [float(bid[1]) for bid in bids if len(bid) > 1]
            ask_sizes = [float(ask[1]) for ask in asks if len(ask) > 1]

            if not bid_sizes or not ask_sizes:
                return {'bid_walls': [], 'ask_walls': []}

            avg_bid_size = sum(bid_sizes) / len(bid_sizes)
            avg_ask_size = sum(ask_sizes) / len(ask_sizes)

            # Find walls (orders significantly larger than average)
            bid_walls = []
            ask_walls = []

            for bid in bids:
                if len(bid) > 1:
                    size = float(bid[1])
                    if size > avg_bid_size * threshold_multiplier:
                        bid_walls.append({
                            'price': float(bid[0]),
                            'size': size,
                            'ratio': size / avg_bid_size if avg_bid_size > 0 else 0
                        })

            for ask in asks:
                if len(ask) > 1:
                    size = float(ask[1])
                    if size > avg_ask_size * threshold_multiplier:
                        ask_walls.append({
                            'price': float(ask[0]),
                            'size': size,
                            'ratio': size / avg_ask_size if avg_ask_size > 0 else 0
                        })

            return {
                'bid_walls': bid_walls[:3],  # Top 3 walls
                'ask_walls': ask_walls[:3]
            }

        except Exception as e:
            logger.error(f"Error detecting walls: {e}")
            return {'bid_walls': [], 'ask_walls': []}

    @staticmethod
    def calculate_book_pressure(orderbook: Dict, depth_levels: int = 5) -> float:
        """Calculate weighted order book pressure"""
        try:
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return 0.0

            bids = orderbook['bids'][:depth_levels]
            asks = orderbook['asks'][:depth_levels]

            if not bids or not asks:
                return 0.0

            # Weight orders by inverse of distance from mid
            best_bid = float(bids[0][0]) if len(bids[0]) > 0 else 0
            best_ask = float(asks[0][0]) if len(asks[0]) > 0 else 0

            if best_bid == 0 or best_ask == 0:
                return 0.0

            midprice = (best_bid + best_ask) / 2

            weighted_bid_pressure = 0
            weighted_ask_pressure = 0

            for bid in bids:
                if len(bid) > 1:
                    price = float(bid[0])
                    size = float(bid[1])
                    distance = abs(midprice - price)
                    weight = 1 / (1 + distance) if distance > 0 else 1
                    weighted_bid_pressure += size * weight

            for ask in asks:
                if len(ask) > 1:
                    price = float(ask[0])
                    size = float(ask[1])
                    distance = abs(price - midprice)
                    weight = 1 / (1 + distance) if distance > 0 else 1
                    weighted_ask_pressure += size * weight

            total_pressure = weighted_bid_pressure + weighted_ask_pressure
            pressure = (weighted_bid_pressure - weighted_ask_pressure) / total_pressure if total_pressure > 0 else 0

            return round(pressure, 3)

        except Exception as e:
            logger.error(f"Error calculating book pressure: {e}")
            return 0.0
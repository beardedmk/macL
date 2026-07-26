"""
Healthy candle calculator module for the Institutional Signal Intelligence Engine.

Determines whether the latest candle is a healthy bullish or bearish candle 
based on custom geometric rules for body and wick proportions. Strictly 
isolated from storage, signal generation, and other feature calculations.
"""

from typing import Any, Dict

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import MarketSnapshot


class HealthyCandleCalculator:
    """
    Calculates the health and geometric properties of the latest candle.
    Evaluates body percentage and wick symmetry to classify the candle 
    as a strong directional move.
    """

    def __init__(self) -> None:
        """Initializes the calculator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def calculate(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """
        Evaluates the latest candle from the MarketSnapshot against 
        institutional candle health rules.
        
        Args:
            snapshot: The current market state snapshot containing the latest candle.
            
        Returns:
            A dictionary containing:
            - healthy_candle (bool): True if the candle meets health criteria.
            - candle_type (str): "GREEN", "RED", "DOJI", or "NEUTRAL".
            - body_percent (float): Body size as a percentage of total range.
            - upper_wick_percent (float): Upper wick size as a percentage of total range.
            - lower_wick_percent (float): Lower wick size as a percentage of total range.
            
        Raises:
            ValidationError: If the snapshot is invalid or missing a candle.
        """
        if not isinstance(snapshot, MarketSnapshot):
            raise ValidationError("Input must be a valid MarketSnapshot object.")
            
        if snapshot.candle is None:
            raise ValidationError("MarketSnapshot must contain a valid Candle to calculate health.")

        candle = snapshot.candle
        high = candle.high
        low = candle.low
        open_price = candle.open
        close_price = candle.close

        total_range = high - low
        
        # Handle zero-range (doji/one-price) candles
        if total_range <= 0.0:
            return {
                "healthy_candle": False,
                "candle_type": "DOJI",
                "body_percent": 0.0,
                "upper_wick_percent": 0.0,
                "lower_wick_percent": 0.0
            }

        body = abs(close_price - open_price)
        upper_wick = high - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low

        body_pct = body / total_range
        upper_pct = upper_wick / total_range
        lower_pct = lower_wick / total_range

        is_green = close_price > open_price
        is_red = close_price < open_price

        healthy = False
        candle_type = "NEUTRAL"
        
        # Tolerance for considering wicks "approximately equal" (10% of total range)
        wick_tolerance = 0.10 

        if is_green:
            candle_type = "GREEN"
            # Rule 1: Full body (strongest)
            if upper_wick == 0.0 and lower_wick == 0.0:
                healthy = True
            # Rule 2: Small upper wick and longer lower tail (or no upper wick)
            elif lower_wick > upper_wick or upper_wick == 0.0:
                if (upper_wick == 0.0 and body_pct >= 0.30) or body_pct >= 0.50:
                    healthy = True
            # Rule 3: Upper wick ≈ lower wick with body >= 50%
            elif abs(upper_pct - lower_pct) <= wick_tolerance and body_pct >= 0.50:
                healthy = True

        elif is_red:
            candle_type = "RED"
            # Rule 1: Full body (strongest)
            if upper_wick == 0.0 and lower_wick == 0.0:
                healthy = True
            # Rule 2: Small lower wick and longer upper tail (or no lower wick)
            elif upper_wick > lower_wick or lower_wick == 0.0:
                if (lower_wick == 0.0 and body_pct >= 0.30) or body_pct >= 0.50:
                    healthy = True
            # Rule 3: Upper wick ≈ lower wick with body >= 50%
            elif abs(upper_pct - lower_pct) <= wick_tolerance and body_pct >= 0.50:
                healthy = True

        return {
            "healthy_candle": healthy,
            "candle_type": candle_type,
            "body_percent": body_pct,
            "upper_wick_percent": upper_pct,
            "lower_wick_percent": lower_pct
        }
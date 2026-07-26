"""
Institutional score calculator module for the Institutional Signal Intelligence Engine.

Calculates a normalized institutional participation score based on market 
microstructure inputs from the current MarketSnapshot. Strictly isolated 
from storage, signal generation, and machine learning logic.
"""

from typing import Any, Dict, Optional

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import MarketSnapshot


class InstitutionalScoreCalculator:
    """
    Calculates a composite institutional participation score (0.0 to 100.0)
    by evaluating candle health, option chain presence, volume, and price range.
    Gracefully degrades if any input data is missing.
    """

    def __init__(self, healthy_candle_calculator: Optional[Any] = None) -> None:
        """
        Initializes the calculator with an optional HealthyCandleCalculator 
        to evaluate candle health internally without relying on FeatureSnapshot.
        
        Args:
            healthy_candle_calculator: Optional instance of HealthyCandleCalculator.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._healthy_calculator = healthy_candle_calculator
        
        # Normalization baselines for scoring
        self._volume_baseline: float = 50000.0
        self._range_baseline: float = 50.0

    def calculate(self, snapshot: MarketSnapshot) -> Dict[str, float]:
        """
        Evaluates the MarketSnapshot and computes the institutional score.
        
        Args:
            snapshot: The current market state snapshot.
            
        Returns:
            A dictionary containing the calculated institutional_score.
            
        Raises:
            ValidationError: If the input snapshot is invalid.
        """
        if not isinstance(snapshot, MarketSnapshot):
            raise ValidationError("Input must be a valid MarketSnapshot object.")

        score = 0.0

        # 1. Healthy Candle (25 points)
        healthy = False
        if self._healthy_calculator is not None and snapshot.candle is not None:
            try:
                result = self._healthy_calculator.calculate(snapshot)
                healthy = bool(result.get("healthy_candle", False))
            except Exception as e:
                self._logger.warning(f"Internal healthy candle calculation failed: {e}")
                
        if healthy:
            score += 25.0

        # 2. Option Chain Availability (25 points)
        if snapshot.option_chain is not None:
            score += 25.0

        # 3. Volume (25 points)
        if snapshot.tick is not None and snapshot.tick.volume > 0:
            vol_norm = min(snapshot.tick.volume / self._volume_baseline, 1.0)
            score += 25.0 * vol_norm

        # 4. Candle Range (25 points)
        if snapshot.candle is not None:
            candle_range = snapshot.candle.high - snapshot.candle.low
            if candle_range > 0:
                range_norm = min(candle_range / self._range_baseline, 1.0)
                score += 25.0 * range_norm

        # Ensure the score is strictly bounded between 0.0 and 100.0
        final_score = min(max(score, 0.0), 100.0)

        return {"institutional_score": final_score}
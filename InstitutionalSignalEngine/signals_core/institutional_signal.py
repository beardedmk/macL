"""
Institutional signal generator module for the Institutional Signal Intelligence Engine.

Generates a high-confidence BUY or SELL signal based exclusively on the 
overall institutional score. Strictly isolated from storage, machine learning, 
and other feature dependencies.
"""

from typing import Any, Dict

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class InstitutionalSignalGenerator:
    """
    Stateless signal generator that evaluates the overall institutional 
    participation score to determine strong bullish or bearish positioning.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates the FeatureSnapshot and generates a signal based on
        the institutional score.

        Args:
            features: The current engineered feature snapshot.

        Returns:
            A dictionary containing the signal, confidence, and reason.

        Raises:
            SignalGenerationError: If the input is invalid.
        """
        if not isinstance(features, FeatureSnapshot):
            raise SignalGenerationError("Input must be a valid FeatureSnapshot object.")

        score = features.institutional_score

        # Direct configuration access
        base_conf = config.signal.base_confidence
        bonus = config.signal.confirmation_bonus
        max_conf = config.signal.max_confidence
        min_buy = config.signal.min_institutional_score_buy
        min_sell = config.signal.min_institutional_score_sell
        extreme = config.signal.extreme_institutional_score
        strongest = config.signal.strongest_institutional_zone

        signal = NO_SIGNAL
        confidence = 0.0
        reason = "Institutional score is neutral"

        # BUY: Strong institutional bullish participation
        if score >= min_buy:
            signal = "BUY"
            confidence = base_conf
            reason = "Strong institutional bullish participation"
            
            # Bonus 1: Exceeds threshold by at least 10 points
            if score >= (min_buy + 10.0):
                confidence += bonus
                
            # Bonus 2: Reaches extreme score
            if score >= extreme:
                confidence += bonus
                
            # Bonus 3: Within the strongest institutional zone
            if score >= strongest:
                confidence += bonus

        # SELL: Strong institutional bearish participation
        elif score <= min_sell:
            signal = "SELL"
            confidence = base_conf
            reason = "Strong institutional bearish participation"
            
            # Bonus 1: Exceeds threshold by at least 10 points (below threshold)
            if score <= (min_sell - 10.0):
                confidence += bonus
                
            # Bonus 2: Reaches extreme low score (symmetric to extreme)
            if score <= (100.0 - extreme):
                confidence += bonus
                
            # Bonus 3: Within the strongest institutional zone for sell
            if score <= (100.0 - strongest):
                confidence += bonus

        # Cap confidence at maximum allowed
        final_confidence = min(confidence, max_conf)

        return {
            "signal": signal,
            "confidence": final_confidence,
            "reason": reason
        }
"""
Dominance signal generator module for the Institutional Signal Intelligence Engine.

Generates a preliminary BUY or SELL signal based exclusively on the market 
dominance features. Strictly isolated from storage, machine learning, and 
other feature dependencies.
"""

from typing import Any, Dict

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class DominanceSignalGenerator:
    """
    Stateless signal generator that evaluates market dominance (Call vs Put OI) 
    to determine institutional positioning.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates the FeatureSnapshot and generates a signal based on
        market dominance.

        Args:
            features: The current engineered feature snapshot.

        Returns:
            A dictionary containing the signal, confidence, and reason.

        Raises:
            SignalGenerationError: If the input is invalid.
        """
        if not isinstance(features, FeatureSnapshot):
            raise SignalGenerationError("Input must be a valid FeatureSnapshot object.")

        # Direct access to explicitly named fields
        dominance = features.dominance
        ce_oi = features.ce_total_oi
        pe_oi = features.pe_total_oi

        # Direct configuration access
        base_conf = config.signal.base_confidence
        bonus = config.signal.confirmation_bonus
        max_conf = config.signal.max_confidence
        min_diff = config.signal.min_dominance_difference
        min_oi = config.signal.min_winning_oi

        signal = NO_SIGNAL
        confidence = 0.0
        reason = "No significant dominance divergence"

        # BUY: PE dominance is stronger (dominance <= 50 - min_diff)
        if dominance <= (50.0 - min_diff):
            signal = "BUY"
            confidence = base_conf
            reason = "Put-side dominance is stronger than Call-side dominance"
            
            # Bonus 1: Dominance difference exceeds threshold
            if (50.0 - dominance) >= min_diff:
                confidence += bonus
                
            # Bonus 2: Winning side OI exceeds configurable threshold
            if pe_oi >= min_oi:
                confidence += bonus
                
            # Bonus 3: Dominance exceeds 70% on PE side (i.e., <= 30%)
            if dominance <= 30.0:
                confidence += bonus

        # SELL: CE dominance is stronger (dominance >= 50 + min_diff)
        elif dominance >= (50.0 + min_diff):
            signal = "SELL"
            confidence = base_conf
            reason = "Call-side dominance is stronger than Put-side dominance"
            
            # Bonus 1: Dominance difference exceeds threshold
            if (dominance - 50.0) >= min_diff:
                confidence += bonus
                
            # Bonus 2: Winning side OI exceeds configurable threshold
            if ce_oi >= min_oi:
                confidence += bonus
                
            # Bonus 3: Dominance exceeds 70% on CE side
            if dominance >= 70.0:
                confidence += bonus

        # Cap confidence at maximum allowed
        final_confidence = min(confidence, max_conf)

        return {
            "signal": signal,
            "confidence": final_confidence,
            "reason": reason
        }
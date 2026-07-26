"""
Breadth signal generator module for the Institutional Signal Intelligence Engine.

Generates a preliminary BUY or SELL signal based exclusively on the market 
breadth features. Strictly isolated from storage, machine learning, and 
other feature dependencies.
"""

from typing import Any, Dict

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class BreadthSignalGenerator:
    """
    Stateless signal generator that evaluates market breadth distribution 
    between Call and Put options to determine institutional positioning.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates the FeatureSnapshot and generates a signal based on
        CE and PE breadth differences.

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
        breadth = features.breadth
        ce_breadth = features.ce_breadth
        pe_breadth = features.pe_breadth

        # Direct configuration access
        base_conf = config.signal.base_confidence
        bonus = config.signal.confirmation_bonus
        max_conf = config.signal.max_confidence
        min_diff = config.signal.min_breadth_difference

        signal = NO_SIGNAL
        confidence = 0.0
        reason = "No significant breadth divergence"
        
        pe_diff = pe_breadth - ce_breadth
        ce_diff = ce_breadth - pe_breadth

        # BUY: PE breadth > CE breadth and difference >= threshold
        if pe_breadth > ce_breadth and pe_diff >= min_diff:
            signal = "BUY"
            confidence = base_conf
            reason = "Institutional Put participation is stronger than Call participation"
            
            # Bonus 1: Breadth difference exceeds threshold
            if pe_diff >= min_diff:
                confidence += bonus
                
            # Bonus 2: Total active strikes exceeds 70% of available strikes (overall breadth > 70%)
            if breadth > 70.0:
                confidence += bonus
                
            # Bonus 3: Winning side exceeds 60% breadth
            if pe_breadth > 60.0:
                confidence += bonus

        # SELL: CE breadth > PE breadth and difference >= threshold
        elif ce_breadth > pe_breadth and ce_diff >= min_diff:
            signal = "SELL"
            confidence = base_conf
            reason = "Institutional Call participation is stronger than Put participation"
            
            # Bonus 1: Breadth difference exceeds threshold
            if ce_diff >= min_diff:
                confidence += bonus
                
            # Bonus 2: Total active strikes exceeds 70% of available strikes
            if breadth > 70.0:
                confidence += bonus
                
            # Bonus 3: Winning side exceeds 60% breadth
            if ce_breadth > 60.0:
                confidence += bonus

        # Cap confidence at maximum allowed
        final_confidence = min(confidence, max_conf)

        return {
            "signal": signal,
            "confidence": final_confidence,
            "reason": reason
        }
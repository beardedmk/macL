"""
Healthy candle signal generator module for the Institutional Signal Intelligence Engine.

Generates a preliminary BUY or SELL signal based exclusively on the healthy candle
feature. Strictly isolated from storage, machine learning, and other feature dependencies.
"""

from typing import Any, Dict

from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class HealthyCandleSignalGenerator:
    """
    Stateless signal generator that evaluates the healthy candle feature
    to produce a preliminary directional signal.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates the FeatureSnapshot and generates a signal based on
        the healthy candle state.

        Args:
            features: The current engineered feature snapshot.

        Returns:
            A dictionary containing the signal, confidence, and reason.

        Raises:
            SignalGenerationError: If the input is invalid.
        """
        if not isinstance(features, FeatureSnapshot):
            raise SignalGenerationError("Input must be a valid FeatureSnapshot object.")

        if features.healthy_candle and features.candle_type == "GREEN":
            return {
                "signal": "BUY",
                "confidence": 60.0,
                "reason": "Healthy green candle detected"
            }
            
        if features.healthy_candle and features.candle_type == "RED":
            return {
                "signal": "SELL",
                "confidence": 60.0,
                "reason": "Healthy red candle detected"
            }

        return {
            "signal": NO_SIGNAL,
            "confidence": 0.0,
            "reason": "No healthy candle pattern detected"
        }
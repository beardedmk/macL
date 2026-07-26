"""
Momentum signal generator module for the Institutional Signal Intelligence Engine.

Generates a preliminary BUY or SELL signal based exclusively on the momentum 
center's velocity and acceleration. Strictly isolated from storage, machine 
learning, and other feature dependencies.
"""

from typing import Any, Dict

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class MomentumSignalGenerator:
    """
    Stateless signal generator that evaluates momentum center kinematics 
    (velocity and acceleration) to produce a preliminary directional signal.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates the FeatureSnapshot and generates a signal based on
        momentum center velocity and acceleration.

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
        velocity = features.momentum_velocity
        acceleration = features.momentum_acceleration

        # Direct configuration access
        base_confidence = config.signal.base_confidence
        confirmation_bonus = config.signal.confirmation_bonus
        max_confidence = config.signal.max_confidence
        min_velocity = config.signal.min_momentum_velocity
        min_acceleration = config.signal.min_momentum_acceleration

        signal = NO_SIGNAL
        confidence = 0.0
        reason_parts = []

        # Determine signal direction
        if velocity > 0 and acceleration >= 0:
            signal = "BUY"
            reason_parts.append("Momentum center moving upward")
            confidence = base_confidence
            
            # +10 if acceleration confirms velocity (speeding up in positive direction)
            if acceleration > 0:
                confidence += confirmation_bonus
                
            # +10 if |velocity| exceeds threshold
            if abs(velocity) > min_velocity:
                confidence += confirmation_bonus
                
            # +10 if |acceleration| exceeds threshold
            if abs(acceleration) > min_acceleration:
                confidence += confirmation_bonus

        elif velocity < 0 and acceleration <= 0:
            signal = "SELL"
            reason_parts.append("Momentum center moving downward")
            confidence = base_confidence
            
            # +10 if acceleration confirms velocity (speeding up in negative direction)
            if acceleration < 0:
                confidence += confirmation_bonus
                
            # +10 if |velocity| exceeds threshold
            if abs(velocity) > min_velocity:
                confidence += confirmation_bonus
                
            # +10 if |acceleration| exceeds threshold
            if abs(acceleration) > min_acceleration:
                confidence += confirmation_bonus

        else:
            signal = NO_SIGNAL
            confidence = 0.0
            reason_parts.append("Momentum center neutral")

        # Cap confidence at maximum allowed
        final_confidence = min(confidence, max_confidence)

        return {
            "signal": signal,
            "confidence": final_confidence,
            "reason": " | ".join(reason_parts)
        }
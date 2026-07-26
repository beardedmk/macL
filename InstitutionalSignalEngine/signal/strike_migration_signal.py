"""
Strike migration signal generator module for the Institutional Signal Intelligence Engine.

Generates a preliminary BUY or SELL signal based exclusively on the independent 
migration directions of Call (CE) and Put (PE) writers. Strictly isolated from 
storage, machine learning, and other feature dependencies.
"""

from typing import Any, Dict

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class StrikeMigrationSignalGenerator:
    """
    Stateless signal generator that evaluates the divergence in strike migration 
    between Call and Put writers to determine institutional positioning.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates the FeatureSnapshot and generates a signal based on
        CE and PE strike migration directions and magnitudes.

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
        ce_dir = features.ce_migration_direction
        pe_dir = features.pe_migration_direction
        ce_dist = abs(features.ce_migration_distance)
        pe_dist = abs(features.pe_migration_distance)
        ce_speed = features.ce_migration_speed
        pe_speed = features.pe_migration_speed

        # Direct configuration access
        base_conf = config.signal.base_confidence
        bonus = config.signal.confirmation_bonus
        max_conf = config.signal.max_confidence
        min_dist = config.signal.min_strike_migration_distance
        min_speed = config.signal.min_strike_migration_speed

        signal = NO_SIGNAL
        confidence = 0.0
        reason = "No meaningful strike migration"

        # BUY: Call writers shifting DOWN, Put writers shifting UP (Bullish positioning)
        if ce_dir == "DOWN" and pe_dir == "UP":
            signal = "BUY"
            confidence = base_conf
            reason = "CE migrated downward while PE migrated upward"
            
            # +10 if both migration distances exceed threshold
            if ce_dist >= min_dist and pe_dist >= min_dist:
                confidence += bonus
                
            # +10 if both migration speeds exceed threshold
            if ce_speed >= min_speed and pe_speed >= min_speed:
                confidence += bonus
                
            # +10 for simultaneous CE and PE migration (inherently true in this branch)
            confidence += bonus

        # SELL: Call writers shifting UP, Put writers shifting DOWN (Bearish positioning)
        elif ce_dir == "UP" and pe_dir == "DOWN":
            signal = "SELL"
            confidence = base_conf
            reason = "CE migrated upward while PE migrated downward"
            
            # +10 if both migration distances exceed threshold
            if ce_dist >= min_dist and pe_dist >= min_dist:
                confidence += bonus
                
            # +10 if both migration speeds exceed threshold
            if ce_speed >= min_speed and pe_speed >= min_speed:
                confidence += bonus
                
            # +10 for simultaneous CE and PE migration (inherently true in this branch)
            confidence += bonus

        # Cap confidence at maximum allowed
        final_confidence = min(confidence, max_conf)

        return {
            "signal": signal,
            "confidence": final_confidence,
            "reason": reason
        }
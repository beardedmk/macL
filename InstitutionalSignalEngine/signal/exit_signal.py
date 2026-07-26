"""
Exit signal generator module for the Institutional Signal Intelligence Engine.

Generates exit recommendations (EXIT or HOLD) for existing BUY or SELL 
positions based on changes in market conditions. Strictly isolated from 
entry signal generation, feature calculation, and machine learning.
"""

from typing import Any, Dict

from config import config
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class ExitSignalGenerator:
    """
    Stateless generator that evaluates current market features against 
    configured risk thresholds to determine if an existing position 
    should be exited.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, current_position: str, features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates the current position and FeatureSnapshot to determine 
        if an exit action is required.

        Args:
            current_position: The current position state ("BUY", "SELL", or "NONE").
            features: The current engineered feature snapshot.

        Returns:
            A dictionary containing the action ("EXIT" or "HOLD") and the reason.

        Raises:
            SignalGenerationError: If the inputs are invalid.
        """
        if current_position not in {"BUY", "SELL", "NONE"}:
            raise SignalGenerationError(
                f"Invalid current_position: '{current_position}'. Must be BUY, SELL, or NONE."
            )
        if not isinstance(features, FeatureSnapshot):
            raise SignalGenerationError("Features input must be a valid FeatureSnapshot object.")

        if current_position == "NONE":
            return {"action": "HOLD", "reason": "No active position to exit."}

        # Configuration
        min_exit_score = config.signal.minimum_exit_score
        max_neg_vel = config.signal.maximum_negative_velocity
        max_neg_accel = config.signal.maximum_negative_acceleration
        exit_on_opp_candle = config.signal.exit_on_opposite_candle

        # Features
        inst_score = features.institutional_score
        vel = features.momentum_velocity
        accel = features.momentum_acceleration
        healthy = features.healthy_candle
        candle_type = features.candle_type

        if current_position == "BUY":
            # Check exit conditions for BUY
            if inst_score < min_exit_score:
                return {
                    "action": "EXIT", 
                    "reason": f"Institutional score {inst_score:.2f} dropped below exit threshold {min_exit_score:.2f}."
                }
            
            if vel <= max_neg_vel:
                return {
                    "action": "EXIT", 
                    "reason": f"Momentum velocity {vel:.2f} reached negative threshold {max_neg_vel:.2f}."
                }
                
            if accel <= max_neg_accel:
                return {
                    "action": "EXIT", 
                    "reason": f"Momentum acceleration {accel:.2f} reached negative threshold {max_neg_accel:.2f}."
                }
                
            if exit_on_opp_candle and healthy and candle_type == "RED":
                return {
                    "action": "EXIT", 
                    "reason": "Opposite healthy red candle detected."
                }

        elif current_position == "SELL":
            # Check exit conditions for SELL
            if inst_score > (100.0 - min_exit_score):
                return {
                    "action": "EXIT", 
                    "reason": f"Institutional score {inst_score:.2f} exceeded exit threshold {100.0 - min_exit_score:.2f}."
                }
            
            if vel >= abs(max_neg_vel):
                return {
                    "action": "EXIT", 
                    "reason": f"Momentum velocity {vel:.2f} reached positive threshold {abs(max_neg_vel):.2f}."
                }
                
            if accel >= abs(max_neg_accel):
                return {
                    "action": "EXIT", 
                    "reason": f"Momentum acceleration {accel:.2f} reached positive threshold {abs(max_neg_accel):.2f}."
                }
                
            if exit_on_opp_candle and healthy and candle_type == "GREEN":
                return {
                    "action": "EXIT", 
                    "reason": "Opposite healthy green candle detected."
                }

        return {"action": "HOLD", "reason": "No exit conditions met."}
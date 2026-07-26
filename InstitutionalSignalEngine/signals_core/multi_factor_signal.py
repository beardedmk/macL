"""
Multi-factor signal generator module for the Institutional Signal Intelligence Engine.

Combines outputs from all independent signal generators into a single final 
institutional trading signal using an ensemble voting mechanism. Strictly 
isolated from storage, machine learning, and feature calculation.
"""

from typing import Any, Dict, List

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory


class MultiFactorSignalGenerator:
    """
    Stateless, thread-safe ensemble signal generator that evaluates the 
    collective outputs of individual signal generators to produce a 
    high-confidence final trading signal.
    """

    def __init__(self) -> None:
        """Initializes the generator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def generate(self, generator_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates a dictionary of individual generator outputs and generates 
        a unified ensemble signal based on voting and confidence thresholds.

        Args:
            generator_outputs: Dictionary mapping generator names to their 
                               output dictionaries (signal, confidence, reason).

        Returns:
            A dictionary containing the final ensemble signal, confidence, 
            and concatenated reasons.

        Raises:
            SignalGenerationError: If the input structure is fundamentally invalid.
        """
        if not isinstance(generator_outputs, dict):
            raise SignalGenerationError("Input must be a dictionary of generator outputs.")

        # Direct configuration access
        min_confirms = config.signal.minimum_confirmations
        min_avg_conf = config.signal.minimum_average_confidence

        buy_confidences: List[float] = []
        sell_confidences: List[float] = []
        buy_reasons: List[str] = []
        sell_reasons: List[str] = []

        # Aggregate votes and confidences
        for name, output in generator_outputs.items():
            if not isinstance(output, dict):
                self._logger.warning(f"Ignoring invalid output format from generator '{name}'.")
                continue

            sig = str(output.get("signal", NO_SIGNAL))
            conf = float(output.get("confidence", 0.0))
            reason = str(output.get("reason", ""))

            if sig == "BUY":
                buy_confidences.append(conf)
                if reason:
                    buy_reasons.append(f"[{name}] {reason}")
            elif sig == "SELL":
                sell_confidences.append(conf)
                if reason:
                    sell_reasons.append(f"[{name}] {reason}")

        # Evaluate BUY conditions
        if len(buy_confidences) >= min_confirms:
            avg_buy_conf = sum(buy_confidences) / len(buy_confidences)
            if avg_buy_conf >= min_avg_conf:
                return {
                    "signal": "BUY",
                    "confidence": avg_buy_conf,
                    "reason": " | ".join(buy_reasons) if buy_reasons else "Multi-factor BUY confirmed"
                }

        # Evaluate SELL conditions
        if len(sell_confidences) >= min_confirms:
            avg_sell_conf = sum(sell_confidences) / len(sell_confidences)
            if avg_sell_conf >= min_avg_conf:
                return {
                    "signal": "SELL",
                    "confidence": avg_sell_conf,
                    "reason": " | ".join(sell_reasons) if sell_reasons else "Multi-factor SELL confirmed"
                }

        # Fallback to NO_SIGNAL
        return {
            "signal": NO_SIGNAL,
            "confidence": 0.0,
            "reason": "Insufficient confirmations or confidence for ensemble signal"
        }
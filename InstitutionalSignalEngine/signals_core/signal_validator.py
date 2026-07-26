"""
Signal validator module for the Institutional Signal Intelligence Engine.

Validates generated trading signals against quality and structural rules 
before they are stored or forwarded to downstream components. Strictly 
isolated from feature calculation, signal generation, and machine learning.
"""

from typing import Any, Dict, List

from config import config
from constants import BUY, NO_SIGNAL, SELL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory


class SignalValidator:
    """
    Stateless validator that performs structural and quality checks on 
    generated signal dictionaries. It collects all validation errors 
    rather than failing on the first issue.
    """

    def __init__(self) -> None:
        """Initializes the validator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def validate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates a signal dictionary against configured quality rules.

        Args:
            signal: A dictionary containing 'signal', 'confidence', and 'reason'.

        Returns:
            A dictionary containing a boolean 'valid' flag and a list of 'errors'.

        Raises:
            SignalGenerationError: If the input is not a dictionary.
        """
        if not isinstance(signal, dict):
            raise SignalGenerationError("Input must be a dictionary representing a signal.")

        errors: List[str] = []

        sig = signal.get("signal")
        conf = signal.get("confidence")
        reason = signal.get("reason")

        # 1. Validate signal type
        valid_signals = {BUY, SELL, NO_SIGNAL}
        if sig not in valid_signals:
            errors.append(f"Invalid signal type: '{sig}'. Must be one of {valid_signals}.")

        # 2. Validate confidence bounds
        if not isinstance(conf, (int, float)):
            errors.append(f"Confidence must be a numeric value, got {type(conf).__name__}.")
        else:
            min_conf = config.signal.minimum_valid_confidence
            max_conf = config.signal.maximum_confidence
            
            if conf < min_conf:
                errors.append(f"Confidence {conf} is below the minimum threshold of {min_conf}.")
            if conf > max_conf:
                errors.append(f"Confidence {conf} exceeds the maximum threshold of {max_conf}.")

        # 3. Validate reason for actionable signals (BUY/SELL)
        if sig in {BUY, SELL}:
            if not reason or not isinstance(reason, str):
                errors.append("A non-empty string 'reason' is required for BUY and SELL signals.")
            else:
                min_len = config.signal.minimum_reason_length
                if len(reason) < min_len:
                    errors.append(
                        f"Reason length ({len(reason)}) is below the minimum required length of {min_len}."
                    )

        # NO_SIGNAL is always considered valid structurally if it passes basic type checks
        is_valid = len(errors) == 0

        if not is_valid:
            self._logger.debug(f"Signal validation failed for '{sig}': {errors}")

        return {
            "valid": is_valid,
            "errors": errors
        }
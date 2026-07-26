"""
Risk filter module for the Institutional Signal Intelligence Engine.

Filters validated trading signals based on configurable market risk rules 
before they are executed or stored. Strictly isolated from signal generation, 
structural validation, and machine learning.
"""

from typing import Any, Dict, List

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot


class RiskFilter:
    """
    Stateless filter that evaluates validated signals against market risk 
    thresholds to determine if they should be allowed to proceed.
    """

    def __init__(self) -> None:
        """Initializes the filter with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def filter(self, signal: Dict[str, Any], features: FeatureSnapshot) -> Dict[str, Any]:
        """
        Evaluates a validated signal and current market features against 
        configured risk thresholds.

        Args:
            signal: A validated signal dictionary.
            features: The current engineered feature snapshot.

        Returns:
            A dictionary containing an 'allowed' boolean and a list of 'reasons' 
            for rejection.

        Raises:
            SignalGenerationError: If the inputs are invalid.
        """
        if not isinstance(signal, dict):
            raise SignalGenerationError("Signal input must be a dictionary.")
        if not isinstance(features, FeatureSnapshot):
            raise SignalGenerationError("Features input must be a valid FeatureSnapshot object.")

        reasons: List[str] = []
        sig = signal.get("signal")

        # NO_SIGNAL always passes
        if sig == NO_SIGNAL:
            return {"allowed": True, "reasons": []}

        conf = float(signal.get("confidence", 0.0))
        
        # Extract required features
        inst_score = features.institutional_score
        breadth = features.breadth
        dominance = features.dominance
        accel = features.momentum_acceleration

        # Configuration
        min_conf = config.signal.minimum_execution_confidence
        min_inst = config.signal.minimum_execution_institutional_score
        min_breadth = config.signal.minimum_execution_breadth
        min_dom = config.signal.minimum_execution_dominance
        max_accel = config.signal.maximum_allowed_acceleration

        # 1. Confidence check
        if conf < min_conf:
            reasons.append(f"Confidence {conf:.2f} is below execution threshold {min_conf:.2f}.")

        # 2. Institutional score check
        if inst_score < min_inst:
            reasons.append(f"Institutional score {inst_score:.2f} is below threshold {min_inst:.2f}.")

        # 3. Breadth check
        if breadth < min_breadth:
            reasons.append(f"Breadth {breadth:.2f} is below threshold {min_breadth:.2f}.")

        # 4. Dominance check: measures deviation from neutral (50.0)
        # A minimum_execution_dominance of 50.0 means no dominance filter.
        # A value of 60.0 requires dominance to be >= 60.0 or <= 40.0.
        dominance_deviation = abs(dominance - 50.0)
        required_deviation = abs(min_dom - 50.0)
        if dominance_deviation < required_deviation:
            reasons.append(f"Dominance deviation {dominance_deviation:.2f} is below required {required_deviation:.2f}.")

        # 5. Acceleration check (extreme acceleration indicates erratic market)
        if abs(accel) > max_accel:
            reasons.append(f"Absolute momentum acceleration {abs(accel):.2f} exceeds maximum allowed {max_accel:.2f}.")

        allowed = len(reasons) == 0

        if not allowed:
            self._logger.debug(f"Signal '{sig}' rejected by risk filter: {reasons}")

        return {
            "allowed": allowed,
            "reasons": reasons
        }
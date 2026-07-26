"""
Signal provider adapter module for the Institutional Signal Intelligence Engine.

Bridges legacy dictionary-based signal generators with the new SignalProvider 
Protocol, ensuring seamless integration with the SignalRegistry and Aggregator.
"""

from typing import Any

from core.logger import LoggerFactory
from models import FeatureSnapshot
from signals.signal_models import SignalDirection, SignalResult


class SignalProviderAdapter:
    """
    Adapter that wraps a legacy signal generator to implement the 
    SignalProvider Protocol.
    """

    def __init__(self, legacy_generator: Any, weight: float = 1.0) -> None:
        """
        Args:
            legacy_generator: An instance of a legacy signal generator 
                              (e.g., HealthyCandleSignalGenerator).
            weight: The relative importance of this signal in the 
                    multi-factor aggregation (default 1.0).
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._generator = legacy_generator
        self._weight = weight
        
        # Derive a clean name from the class name (e.g., "HealthyCandle")
        class_name = legacy_generator.__class__.__name__
        self.name = class_name.replace("SignalGenerator", "")

    @property
    def weight(self) -> float:
        return self._weight

    def generate(self, features: FeatureSnapshot) -> SignalResult:
        """
        Executes the legacy generator and maps its dictionary output 
        to a standardized SignalResult.
        """
        try:
            raw_output = self._generator.generate(features)
        except Exception as e:
            self._logger.error(f"Legacy generator {self.name} failed: {e}")
            # Return a safe neutral result on failure to prevent pipeline collapse
            return SignalResult(
                signal_name=self.name,
                direction=SignalDirection.NEUTRAL,
                score=0.0,
                confidence=0.0,
                weight=self._weight,
                timestamp=features.timestamp,
                metadata={"error": str(e)}
            )

        raw_signal = str(raw_output.get("signal", "NO_SIGNAL"))
        confidence = float(raw_output.get("confidence", 0.0))
        reason = str(raw_output.get("reason", ""))

        # Map legacy string signals to SignalDirection enum
        if raw_signal == "BUY":
            direction = SignalDirection.BULLISH
            score = confidence
        elif raw_signal == "SELL":
            direction = SignalDirection.BEARISH
            score = confidence
        else:
            direction = SignalDirection.NEUTRAL
            score = 0.0

        return SignalResult(
            signal_name=self.name,
            direction=direction,
            score=score,
            confidence=confidence,
            weight=self._weight,
            timestamp=features.timestamp,
            metadata={
                "reason": reason,
                "raw_signal": raw_signal
            }
        )

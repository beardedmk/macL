"""
Signal engine module for the Institutional Signal Intelligence Engine.

Combines engineered features into a unified SignalSnapshot by evaluating 
all registered signal generators and merging their outputs. This layer 
is strictly responsible for decision logic. Isolated from storage and 
machine learning.
"""

import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import config
from constants import NO_SIGNAL
from core.exceptions import SignalGenerationError
from core.logger import LoggerFactory
from models import FeatureSnapshot, SignalSnapshot


class SignalEngine:
    """
    Thread-safe orchestration engine for generating rule-based trading signals.
    Accepts signal generator objects via dependency injection, executes them 
    independently against a FeatureSnapshot, and merges their outputs into 
    a single unified SignalSnapshot.
    """

    def __init__(self, generators: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the signal engine with an optional dictionary of 
        pre-registered signal generators.
        
        Args:
            generators: Optional dictionary mapping generator names to 
                        generator instances.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        self._generators: Dict[str, Any] = generators or {}
        
        self._min_confidence: float = config.signal.min_confidence
        
        self._logger.info(
            f"SignalEngine initialized with {len(self._generators)} generators."
        )

    def register_generator(self, name: str, generator: Any) -> None:
        """
        Registers a new signal generator under a specific name.
        
        Args:
            name: The unique identifier for the generator.
            generator: The generator instance (must implement a generate method).
            
        Raises:
            SignalGenerationError: If the generator does not have a generate method.
        """
        if not hasattr(generator, "generate") or not callable(getattr(generator, "generate")):
            raise SignalGenerationError(
                f"Generator '{name}' must implement a callable 'generate' method."
            )
            
        with self._lock:
            self._generators[name] = generator
            self._logger.info(f"Registered signal generator: {name}")

    def unregister_generator(self, name: str) -> None:
        """
        Removes a registered signal generator.
        
        Args:
            name: The unique identifier of the generator to remove.
        """
        with self._lock:
            if name in self._generators:
                del self._generators[name]
                self._logger.info(f"Unregistered signal generator: {name}")

    def clear(self) -> None:
        """Clears all registered generators from the engine."""
        with self._lock:
            self._generators.clear()
            self._logger.info("All signal generators cleared.")

    def generate(self, features: FeatureSnapshot) -> SignalSnapshot:
        """
        Executes all registered generators against the provided FeatureSnapshot 
        and merges their outputs into a unified SignalSnapshot.
        
        Merge strategy:
        - signal: From the generator with the highest confidence.
        - confidence: Maximum confidence across all generators.
        - reason: Concatenated reasons from all contributing generators.
        - price: From the highest-confidence generator, or 0.0 if unavailable.
        - timestamp: Inherited from the FeatureSnapshot.
        
        Args:
            features: The current engineered feature snapshot.
            
        Returns:
            A unified SignalSnapshot.
            
        Raises:
            SignalGenerationError: If the input is invalid or an unrecoverable 
                                   engine-level failure occurs.
        """
        if not isinstance(features, FeatureSnapshot):
            raise SignalGenerationError("Input must be a valid FeatureSnapshot object.")

        # Take a snapshot of generators to avoid holding the lock during execution
        with self._lock:
            active_generators = dict(self._generators)

        if not active_generators:
            return self._build_default_snapshot(features.timestamp, features.index_name)

        # Collect outputs from all generators
        outputs: List[Dict[str, Any]] = []
        
        for name, generator in active_generators.items():
            try:
                raw_output = generator.generate(features)
                parsed = self._parse_generator_output(name, raw_output)
                if parsed is not None:
                    outputs.append(parsed)
            except Exception as e:
                # Isolate failures: one generator must not stop the engine
                self._logger.error(
                    f"Generator '{name}' failed during execution: {e}. Skipping."
                )

        # Merge all valid outputs into a single SignalSnapshot
        return self._merge_outputs(features, outputs)

    def _parse_generator_output(self, name: str, raw_output: Any) -> Optional[Dict[str, Any]]:
        """
        Normalizes a generator's output into a standard dictionary format.
        
        Args:
            name: The generator's name (used for reason tagging).
            raw_output: The raw return value from the generator.
            
        Returns:
            A normalized dictionary, or None if the output is unusable.
        """
        if raw_output is None:
            return None
            
        if isinstance(raw_output, dict):
            result = dict(raw_output)
            result.setdefault("signal", NO_SIGNAL)
            result.setdefault("confidence", 0.0)
            result.setdefault("reason", "")
            result.setdefault("price", 0.0)
            result["source"] = name
            return result
            
        if isinstance(raw_output, str):
            return {
                "signal": raw_output,
                "confidence": 0.0,
                "reason": f"{name}:{raw_output}",
                "price": 0.0,
                "source": name
            }
            
        self._logger.warning(
            f"Generator '{name}' returned unsupported type: {type(raw_output)}. Skipping."
        )
        return None

    def _merge_outputs(self, features: FeatureSnapshot, outputs: List[Dict[str, Any]]) -> SignalSnapshot:
        """
        Merges multiple generator outputs into a single SignalSnapshot.
        The generator with the highest confidence determines the primary signal.
        
        Args:
            features: The source FeatureSnapshot for timestamp and metadata.
            outputs: List of normalized generator output dictionaries.
            
        Returns:
            A unified SignalSnapshot.
        """
        if not outputs:
            return self._build_default_snapshot(features.timestamp, features.index_name)

        # Find the output with the highest confidence
        best_output = max(outputs, key=lambda o: float(o.get("confidence", 0.0)))
        
        final_signal = str(best_output.get("signal", NO_SIGNAL))
        final_confidence = float(best_output.get("confidence", 0.0))
        final_price = float(best_output.get("price", 0.0))
        
        # Concatenate reasons from all contributing generators
        reasons: List[str] = []
        for output in outputs:
            source = output.get("source", "unknown")
            reason = output.get("reason", "")
            signal = output.get("signal", NO_SIGNAL)
            confidence = output.get("confidence", 0.0)
            if signal != NO_SIGNAL or confidence > 0.0:
                reasons.append(f"[{source}] {signal} ({confidence:.2f}) {reason}")
                
        final_reason = " | ".join(reasons) if reasons else "No active signals"

        # Apply minimum confidence threshold
        if final_confidence < self._min_confidence:
            final_reason = f"REJECTED (confidence {final_confidence:.2f} < {self._min_confidence:.2f}) | {final_reason}"
            final_signal = NO_SIGNAL

        try:
            return SignalSnapshot(
                timestamp=features.timestamp,
                signal=final_signal,
                confidence=final_confidence,
                reason=final_reason,
                price=final_price
            )
        except Exception as e:
            raise SignalGenerationError(f"Failed to construct final SignalSnapshot: {e}") from e

    def _build_default_snapshot(self, timestamp: datetime, index_name: str) -> SignalSnapshot:
        """
        Builds a default no-signal snapshot when no generators are active 
        or all generators fail.
        
        Args:
            timestamp: The timestamp to assign.
            index_name: The index name for context.
            
        Returns:
            A default SignalSnapshot with NO_SIGNAL.
        """
        return SignalSnapshot(
            timestamp=timestamp,
            signal=NO_SIGNAL,
            confidence=0.0,
            reason=f"No generators active for {index_name}",
            price=0.0
        )
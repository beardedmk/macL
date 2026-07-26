"""
Feature engine module for the Institutional Signal Intelligence Engine.

Orchestrates all feature calculators and produces a unified FeatureSnapshot 
from a MarketSnapshot. Strictly isolated from storage, signal generation, 
and machine learning logic.
"""

import threading
from typing import Any, Dict, Optional

from core.exceptions import FeatureCalculationError
from core.logger import LoggerFactory
from models import FeatureSnapshot, MarketSnapshot


class FeatureEngine:
    """
    Thread-safe orchestration engine for calculating engineered features.
    Accepts calculator objects via dependency injection and executes them 
    independently to build a comprehensive FeatureSnapshot.
    """

    def __init__(self, calculators: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the feature engine with an optional dictionary of 
        pre-registered calculators.
        
        Args:
            calculators: Optional dictionary mapping calculator names to 
                         calculator instances.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        self._calculators: Dict[str, Any] = calculators or {}
        
        self._logger.info(
            f"FeatureEngine initialized with {len(self._calculators)} calculators."
        )

    def register_calculator(self, name: str, calculator: Any) -> None:
        """
        Registers a new feature calculator under a specific name.
        
        Args:
            name: The unique identifier for the calculator.
            calculator: The calculator instance (must implement a calculate method).
            
        Raises:
            FeatureCalculationError: If the calculator does not have a calculate method.
        """
        if not hasattr(calculator, "calculate") or not callable(getattr(calculator, "calculate")):
            raise FeatureCalculationError(
                f"Calculator '{name}' must implement a callable 'calculate' method."
            )
            
        with self._lock:
            self._calculators[name] = calculator
            self._logger.info(f"Registered feature calculator: {name}")

    def unregister_calculator(self, name: str) -> None:
        """
        Removes a registered feature calculator.
        
        Args:
            name: The unique identifier of the calculator to remove.
        """
        with self._lock:
            if name in self._calculators:
                del self._calculators[name]
                self._logger.info(f"Unregistered feature calculator: {name}")

    def clear(self) -> None:
        """Clears all registered calculators from the engine."""
        with self._lock:
            self._calculators.clear()
            self._logger.info("All feature calculators cleared.")
# 
# 
    def calculate(self, snapshot: MarketSnapshot) -> FeatureSnapshot:
        """
        Executes all registered calculators against the provided MarketSnapshot 
        and aggregates the results into a FeatureSnapshot.
        
        Args:
            snapshot: The current market state snapshot.
            
        Returns:
            A fully populated FeatureSnapshot.
            
        Raises:
            FeatureCalculationError: If the input snapshot is invalid or 
                                     unrecoverable engine-level failures occur.
        """
        if not isinstance(snapshot, MarketSnapshot):
            raise FeatureCalculationError("Input must be a valid MarketSnapshot object.")
            
        if snapshot.tick is None:
            raise FeatureCalculationError("MarketSnapshot must contain a valid Tick to calculate features.")

        # Initialize default values for all features using explicit names
        feature_values: Dict[str, Any] = {
            "dominance": 0.0,
            "ce_total_oi": 0,
            "pe_total_oi": 0,
            "breadth": 0.0,
            "momentum_center": None,
            "momentum_velocity": 0.0,
            "momentum_acceleration": 0.0,
            "vwap_distance": 0.0,
            "healthy_candle": False,
            "candle_type": "UNKNOWN",
            "body_percent": 0.0,
            "upper_wick_percent": 0.0,
            "lower_wick_percent": 0.0,
            "institutional_score": 0.0,
            "confidence": 0.0,
                        # Strike Migration Defaults
            "ce_migration_direction": "NEUTRAL",
            "ce_migration_distance": 0.0,
            "ce_migration_speed": 0.0,
            "pe_migration_direction": "NEUTRAL",
            "pe_migration_distance": 0.0,
            "pe_migration_speed": 0.0,
            "dominant_ce_strike": None,
            "dominant_pe_strike": None,
        }

        # Take a snapshot of the current calculators to avoid holding the lock during execution
        with self._lock:
            active_calculators = dict(self._calculators)

        # Execute each calculator independently
        for name, calculator in active_calculators.items():
            try:
                result = calculator.calculate(snapshot)
                
                # Handle both single-value returns and dictionary returns
                if isinstance(result, dict):
                    for key, value in result.items():
                        if key in feature_values:
                            feature_values[key] = value
                else:
                    if name in feature_values:
                        feature_values[name] = result
                        
            except Exception as e:
                # Isolate failures: log the error but do not corrupt the entire engine
                self._logger.error(
                    f"Calculator '{name}' failed during execution: {e}. "
                    "Using default values for its features."
                )

        # Construct the final FeatureSnapshot
        try:
            return FeatureSnapshot(
                timestamp=snapshot.tick.timestamp,
                index_name=snapshot.tick.index_name,
                dominance=float(feature_values["dominance"]),
                ce_total_oi=int(feature_values["ce_total_oi"]),
                pe_total_oi=int(feature_values["pe_total_oi"]),
                breadth=float(feature_values["breadth"]),
                momentum_center=feature_values["momentum_center"],
                momentum_velocity=float(feature_values["momentum_velocity"]),
                momentum_acceleration=float(feature_values["momentum_acceleration"]),
                vwap_distance=float(feature_values["vwap_distance"]),
                healthy_candle=bool(feature_values["healthy_candle"]),
                candle_type=str(feature_values["candle_type"]),
                body_percent=float(feature_values["body_percent"]),
                upper_wick_percent=float(feature_values["upper_wick_percent"]),
                lower_wick_percent=float(feature_values["lower_wick_percent"]),
                institutional_score=float(feature_values["institutional_score"]),
                confidence=float(feature_values["confidence"]),
                 # Strike Migration Fields
                ce_migration_direction=str(feature_values["ce_migration_direction"]),
                ce_migration_distance=float(feature_values["ce_migration_distance"]),
                ce_migration_speed=float(feature_values["ce_migration_speed"]),
                pe_migration_direction=str(feature_values["pe_migration_direction"]),
                pe_migration_distance=float(feature_values["pe_migration_distance"]),
                pe_migration_speed=float(feature_values["pe_migration_speed"]),
                dominant_ce_strike=feature_values["dominant_ce_strike"],
                dominant_pe_strike=feature_values["dominant_pe_strike"]
            )
        except Exception as e:
            raise FeatureCalculationError(f"Failed to construct final FeatureSnapshot: {e}") from e
"""
Strike migration calculator module for the Institutional Signal Intelligence Engine.

Tracks how institutional activity migrates between option strikes over time 
by independently monitoring the dominant Call and Put open interest. 
Strictly isolated from storage, signal generation, and machine learning logic.
"""

import threading
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, Optional, Tuple

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import MarketSnapshot


class StrikeMigrationCalculator:
    """
    Calculates the independent migration of dominant Call (CE) and Put (PE) 
    option strikes over a configurable history window. Tracks direction, 
    distance, and speed for both sides using their own independent historical 
    timestamps to enable precise convergence/divergence analysis.
    """

    def __init__(self, history_length: int = 10) -> None:
        """
        Initializes the calculator with a specific history window size.
        
        Args:
            history_length: Maximum number of historical snapshots to retain 
                            for migration calculation.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        self._history_length = max(1, history_length)
        
        # Stores tuples of (timestamp, dominant_ce_strike, dominant_pe_strike)
        self._history: Deque[Tuple[datetime, Optional[float], Optional[float]]] = deque(maxlen=self._history_length)

    def calculate(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """
        Evaluates the current option chain to find dominant strikes and 
        calculates independent migration metrics for both CE and PE sides 
        based on historical data. Each side uses its own most recent valid 
        timestamp for speed calculations.
        
        Args:
            snapshot: The current market state snapshot.
            
        Returns:
            A dictionary containing independent migration metrics for CE and PE, 
            along with the current dominant strikes.
            
        Raises:
            ValidationError: If the input snapshot is invalid or missing an option chain.
        """
        if not isinstance(snapshot, MarketSnapshot):
            raise ValidationError("Input must be a valid MarketSnapshot object.")
            
        if snapshot.option_chain is None or not snapshot.option_chain.options:
            raise ValidationError("MarketSnapshot must contain a valid OptionChainSnapshot with options.")
            
        if snapshot.tick is None:
            raise ValidationError("MarketSnapshot must contain a valid Tick for timestamp tracking.")

        # 1. Identify dominant CE and PE strikes (highest Open Interest)
        dominant_ce: Optional[float] = None
        dominant_pe: Optional[float] = None
        
        max_ce_oi = -1
        max_pe_oi = -1
        
        for opt in snapshot.option_chain.options:
            if opt.option_type == "CE" and opt.oi > max_ce_oi:
                max_ce_oi = opt.oi
                dominant_ce = opt.strike
            elif opt.option_type == "PE" and opt.oi > max_pe_oi:
                max_pe_oi = opt.oi
                dominant_pe = opt.strike

        current_ts = snapshot.tick.timestamp

        # 2. Update history and calculate migration metrics
        with self._lock:
            self._history.append((current_ts, dominant_ce, dominant_pe))
            
            # Default result structure
            result: Dict[str, Any] = {
                "ce_migration_direction": "NEUTRAL",
                "ce_migration_distance": 0.0,
                "ce_migration_speed": 0.0,
                "pe_migration_direction": "NEUTRAL",
                "pe_migration_distance": 0.0,
                "pe_migration_speed": 0.0,
                "dominant_ce_strike": dominant_ce,
                "dominant_pe_strike": dominant_pe
            }
            
            if len(self._history) < 2:
                return result
                
            # Find the most recent previous valid CE and PE strikes independently
            prev_ce: Optional[float] = None
            prev_ce_ts: Optional[datetime] = None
            prev_pe: Optional[float] = None
            prev_pe_ts: Optional[datetime] = None
            
            for ts, ce, pe in reversed(list(self._history)[:-1]):
                if prev_ce is None and ce is not None:
                    prev_ce = ce
                    prev_ce_ts = ts
                if prev_pe is None and pe is not None:
                    prev_pe = pe
                    prev_pe_ts = ts
                    
                # Stop early if we found both
                if prev_ce is not None and prev_pe is not None:
                    break

            # 3. Calculate CE Migration Metrics using its own timestamp
            if dominant_ce is not None and prev_ce is not None and prev_ce_ts is not None:
                ce_distance = dominant_ce - prev_ce
                result["ce_migration_distance"] = float(ce_distance)
                result["ce_migration_direction"] = "UP" if ce_distance > 0 else ("DOWN" if ce_distance < 0 else "NEUTRAL")
                
                time_diff = (current_ts - prev_ce_ts).total_seconds()
                result["ce_migration_speed"] = float(abs(ce_distance) / time_diff) if time_diff > 0 else 0.0

            # 4. Calculate PE Migration Metrics using its own timestamp
            if dominant_pe is not None and prev_pe is not None and prev_pe_ts is not None:
                pe_distance = dominant_pe - prev_pe
                result["pe_migration_distance"] = float(pe_distance)
                result["pe_migration_direction"] = "UP" if pe_distance > 0 else ("DOWN" if pe_distance < 0 else "NEUTRAL")
                
                time_diff = (current_ts - prev_pe_ts).total_seconds()
                result["pe_migration_speed"] = float(abs(pe_distance) / time_diff) if time_diff > 0 else 0.0

            return result
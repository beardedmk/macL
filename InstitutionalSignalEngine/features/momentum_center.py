"""
Momentum center calculator module for the Institutional Signal Intelligence Engine.

Tracks the market's moving "magnet strike" (momentum center) using the latest 
OptionChainSnapshot history. Calculates the center, its velocity, and acceleration.
Strictly isolated from storage, signal generation, and machine learning logic.
"""

import threading
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Tuple

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import MarketSnapshot


class MomentumCenterCalculator:
    """
    Calculates the market's momentum center (magnet strike) based on the 
    strike with the highest combined Open Interest (CE + PE). Tracks the 
    movement, velocity, and acceleration of this center over a configurable 
    history window.
    """

    def __init__(self, history_length: int = 10) -> None:
        """
        Initializes the calculator with a specific history window size.
        
        Args:
            history_length: Maximum number of historical snapshots to retain 
                            for velocity and acceleration calculations.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        self._history_length = max(1, history_length)
        
        # Stores tuples of (timestamp, momentum_center)
        self._history: Deque[Tuple[datetime, Optional[float]]] = deque(maxlen=self._history_length)

    def calculate(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """
        Evaluates the current option chain to find the momentum center and 
        calculates its velocity and acceleration based on historical data.
        
        Args:
            snapshot: The current market state snapshot.
            
        Returns:
            A dictionary containing the momentum center, velocity, and acceleration.
            
        Raises:
            ValidationError: If the input snapshot is invalid or missing a tick.
        """
        if not isinstance(snapshot, MarketSnapshot):
            raise ValidationError("Input must be a valid MarketSnapshot object.")
            
        if snapshot.tick is None:
            raise ValidationError("MarketSnapshot must contain a valid Tick for timestamp tracking.")

        current_ts = snapshot.tick.timestamp
        momentum_center: Optional[float] = None

        # 1. Calculate current momentum center (strike with max combined OI)
        if snapshot.option_chain is not None and snapshot.option_chain.options:
            strike_oi: Dict[float, int] = {}
            for opt in snapshot.option_chain.options:
                if opt.strike not in strike_oi:
                    strike_oi[opt.strike] = 0
                strike_oi[opt.strike] += opt.oi
            
            if strike_oi:
                momentum_center = max(strike_oi, key=strike_oi.get)

        # 2. Update history and calculate kinematics
        with self._lock:
            self._history.append((current_ts, momentum_center))
            
            result: Dict[str, Any] = {
                "momentum_center": momentum_center,
                "momentum_velocity": 0.0,
                "momentum_acceleration": 0.0
            }
            
            # Filter out any None values from history to ensure valid calculations
            valid_points: List[Tuple[datetime, float]] = [
                (ts, c) for ts, c in self._history if c is not None
            ]
            
            if len(valid_points) < 2:
                return result
                
            curr_ts, curr_c = valid_points[-1]
            prev_ts, prev_c = valid_points[-2]
            
            time_diff_1 = (curr_ts - prev_ts).total_seconds()
            if time_diff_1 > 0:
                curr_vel = (curr_c - prev_c) / time_diff_1
                result["momentum_velocity"] = float(curr_vel)
                
                if len(valid_points) >= 3:
                    prev_prev_ts, prev_prev_c = valid_points[-3]
                    time_diff_0 = (prev_ts - prev_prev_ts).total_seconds()
                    
                    if time_diff_0 > 0:
                        prev_vel = (prev_c - prev_prev_c) / time_diff_0
                        # Acceleration = change in velocity / time interval
                        result["momentum_acceleration"] = float((curr_vel - prev_vel) / time_diff_1)
                        
            return result
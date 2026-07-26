"""
Dominance engine module for the Institutional Signal Intelligence Engine.

Measures which side of the market currently dominates (Call writers vs Put 
writers) by analyzing the total Open Interest distribution across the 
option chain. Strictly isolated from storage, signal generation, and 
machine learning logic.
"""

from typing import Any, Dict

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import MarketSnapshot


class DominanceCalculator:
    """
    Stateless calculator that measures market dominance by summing the 
    total Open Interest (OI) for Call (CE) and Put (PE) options. 
    Computes a normalized dominance percentage indicating whether Call 
    writers or Put writers are in control.
    """

    def __init__(self) -> None:
        """Initializes the calculator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def calculate(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """
        Evaluates the current option chain to calculate market dominance.
        
        Args:
            snapshot: The current market state snapshot.
            
        Returns:
            A dictionary containing the dominance percentage (0.0 to 100.0), 
            total CE OI, and total PE OI.
            
        Raises:
            ValidationError: If the input snapshot is invalid.
        """
        if not isinstance(snapshot, MarketSnapshot):
            raise ValidationError("Input must be a valid MarketSnapshot object.")

        default_result: Dict[str, Any] = {
            "dominance": 50.0,
            "ce_total_oi": 0,
            "pe_total_oi": 0
        }

        # Graceful degradation if option chain data is unavailable
        if snapshot.option_chain is None or not snapshot.option_chain.options:
            return default_result

        ce_total_oi = 0
        pe_total_oi = 0

        # Sum total Open Interest for CE and PE
        for opt in snapshot.option_chain.options:
            if opt.option_type == "CE":
                ce_total_oi += opt.oi
            elif opt.option_type == "PE":
                pe_total_oi += opt.oi

        total_oi = ce_total_oi + pe_total_oi

        # Compute dominance percentage
        if total_oi == 0:
            dominance = 50.0
        else:
            dominance = (ce_total_oi / total_oi) * 100.0

        # Ensure strict normalization between 0.0 and 100.0
        dominance = min(max(dominance, 0.0), 100.0)

        return {
            "dominance": dominance,
            "ce_total_oi": ce_total_oi,
            "pe_total_oi": pe_total_oi
        }
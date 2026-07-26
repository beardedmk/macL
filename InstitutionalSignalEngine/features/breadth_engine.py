"""
Breadth engine module for the Institutional Signal Intelligence Engine.

Calculates market breadth from the current OptionChainSnapshot by measuring 
how widely institutional participation (Open Interest) is distributed across 
option strikes. Strictly isolated from storage, signal generation, and 
machine learning logic.
"""

from typing import Any, Dict

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import MarketSnapshot


class BreadthCalculator:
    """
    Stateless calculator that measures market breadth by analyzing the 
    distribution of active strikes (OI > 0) across the option chain.
    Computes normalized participation percentages for CE, PE, and the 
    overall market.
    """

    def __init__(self) -> None:
        """Initializes the calculator with a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)

    def calculate(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """
        Evaluates the current option chain to calculate market breadth metrics.
        
        Args:
            snapshot: The current market state snapshot.
            
        Returns:
            A dictionary containing overall breadth, CE breadth, PE breadth, 
            and counts of active strikes.
            
        Raises:
            ValidationError: If the input snapshot is invalid.
        """
        if not isinstance(snapshot, MarketSnapshot):
            raise ValidationError("Input must be a valid MarketSnapshot object.")

        default_result: Dict[str, Any] = {
            "breadth": 0.0,
            "ce_breadth": 0.0,
            "pe_breadth": 0.0,
            "active_ce_strikes": 0,
            "active_pe_strikes": 0,
            "total_active_strikes": 0
        }

        # Graceful degradation if option chain data is unavailable
        if snapshot.option_chain is None or not snapshot.option_chain.options:
            return default_result

        total_ce = 0
        active_ce = 0
        total_pe = 0
        active_pe = 0

        # Analyze participation across strikes
        for opt in snapshot.option_chain.options:
            if opt.option_type == "CE":
                total_ce += 1
                if opt.oi > 0:
                    active_ce += 1
            elif opt.option_type == "PE":
                total_pe += 1
                if opt.oi > 0:
                    active_pe += 1

        # Compute normalized participation (0.0 to 100.0)
        ce_breadth = (active_ce / total_ce * 100.0) if total_ce > 0 else 0.0
        pe_breadth = (active_pe / total_pe * 100.0) if total_pe > 0 else 0.0
        
        total_active = active_ce + active_pe
        total_strikes = total_ce + total_pe
        overall_breadth = (total_active / total_strikes * 100.0) if total_strikes > 0 else 0.0

        return {
            "breadth": overall_breadth,
            "ce_breadth": ce_breadth,
            "pe_breadth": pe_breadth,
            "active_ce_strikes": active_ce,
            "active_pe_strikes": active_pe,
            "total_active_strikes": total_active
        }
"""
Option chain builder module for the Institutional Signal Intelligence Engine.

Maintains the latest option chain state from incoming OptionChainSnapshot 
updates. Strictly isolated from storage, feature engineering, and signal 
generation.
"""

import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import OptionChainSnapshot, OptionTick


class OptionChainBuilder:
    """
    Thread-safe builder that maintains the latest state of the option chain,
    allowing fast lookups by strike and option type.
    """

    def __init__(self) -> None:
        """Initializes the option chain builder with empty state."""
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._options: Dict[Tuple[float, str], OptionTick] = {}
        self._atm_strike: Optional[float] = None
        self._expiry: Optional[datetime] = None
        self._index_name: Optional[str] = None
        self._timestamp: Optional[datetime] = None

    def update(self, snapshot: OptionChainSnapshot) -> None:
        """
        Updates the internal option chain state with data from a new snapshot.
        Contracts are updated incrementally based on the provided ticks.
        
        Args:
            snapshot: The incoming OptionChainSnapshot.
            
        Raises:
            ValidationError: If the snapshot is invalid.
        """
        if not isinstance(snapshot, OptionChainSnapshot):
            raise ValidationError("Input must be a valid OptionChainSnapshot object.")
            
        with self._lock:
            self._index_name = snapshot.index_name
            self._expiry = snapshot.expiry
            self._atm_strike = snapshot.atm_strike
            self._timestamp = snapshot.timestamp
            
            for opt in snapshot.options:
                key = (opt.strike, opt.option_type)
                self._options[key] = opt

    def get_snapshot(self) -> OptionChainSnapshot:
        """
        Retrieves a complete snapshot of the current option chain state.
        
        Returns:
            An OptionChainSnapshot representing the latest state.
            
        Raises:
            ValidationError: If the chain has not been initialized yet.
        """
        with self._lock:
            if self._index_name is None or self._timestamp is None:
                raise ValidationError("Option chain has not been initialized with any data.")
                
            return OptionChainSnapshot(
                timestamp=self._timestamp,
                index_name=self._index_name,
                expiry=self._expiry,
                atm_strike=self._atm_strike,
                options=list(self._options.values())
            )

    def get_option(self, strike: float, option_type: str) -> Optional[OptionTick]:
        """
        Retrieves a specific option contract by strike and type.
        
        Args:
            strike: The strike price.
            option_type: The option type (e.g., 'CE', 'PE').
            
        Returns:
            The OptionTick if found, otherwise None.
        """
        with self._lock:
            return self._options.get((strike, option_type))

    def get_all_options(self) -> List[OptionTick]:
        """
        Retrieves all currently tracked option contracts.
        
        Returns:
            A list of all OptionTick objects.
        """
        with self._lock:
            return list(self._options.values())

    def get_atm_strike(self) -> Optional[float]:
        """
        Retrieves the latest At-The-Money (ATM) strike price.
        
        Returns:
            The ATM strike price, or None if not set.
        """
        with self._lock:
            return self._atm_strike

    def clear(self) -> None:
        """Clears all stored option chain data and resets the state."""
        with self._lock:
            self._options.clear()
            self._atm_strike = None
            self._expiry = None
            self._index_name = None
            self._timestamp = None
            self._logger.info("Option chain builder state cleared.")
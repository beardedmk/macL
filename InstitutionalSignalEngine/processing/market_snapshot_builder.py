"""
Market snapshot builder module for the Institutional Signal Intelligence Engine.

Combines the latest Tick, Candles, and OptionChainSnapshot into a unified 
MarketSnapshot object for downstream feature engineering. Strictly isolated 
from storage, feature calculation, and signal generation.
"""

import threading
from typing import Dict, Optional

from config import TimeFrame, config
from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import Candle, MarketSnapshot, OptionChainSnapshot, Tick


class MarketSnapshotBuilder:
    """
    Thread-safe builder that aggregates the latest market data components 
    into a unified MarketSnapshot. Maintains independent state for all 
    supported timeframes.
    """

    def __init__(self) -> None:
        """Initializes the market snapshot builder with empty state."""
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._tick: Optional[Tick] = None
        self._candles: Dict[TimeFrame, Candle] = {}
        self._option_chain: Optional[OptionChainSnapshot] = None
        
        self._default_timeframe: TimeFrame = config.signal.default_chart_timeframe

    def update_tick(self, tick: Tick) -> None:
        """
        Updates the latest tick in the internal state.
        
        Args:
            tick: The incoming Tick object.
            
        Raises:
            ValidationError: If the tick is invalid.
        """
        if not isinstance(tick, Tick):
            raise ValidationError("Input must be a valid Tick object.")
            
        with self._lock:
            self._tick = tick

    def update_candle(self, timeframe: TimeFrame, candle: Candle) -> None:
        """
        Updates the latest candle for a specific timeframe.
        
        Args:
            timeframe: The timeframe of the candle.
            candle: The incoming Candle object.
            
        Raises:
            ValidationError: If the timeframe or candle is invalid.
        """
        if not isinstance(timeframe, TimeFrame):
            raise ValidationError("Timeframe must be a valid TimeFrame enum.")
        if not isinstance(candle, Candle):
            raise ValidationError("Input must be a valid Candle object.")
            
        with self._lock:
            self._candles[timeframe] = candle

    def update_option_chain(self, snapshot: OptionChainSnapshot) -> None:
        """
        Updates the latest option chain snapshot.
        
        Args:
            snapshot: The incoming OptionChainSnapshot.
            
        Raises:
            ValidationError: If the snapshot is invalid.
        """
        if not isinstance(snapshot, OptionChainSnapshot):
            raise ValidationError("Input must be a valid OptionChainSnapshot object.")
            
        with self._lock:
            self._option_chain = snapshot

    def build_snapshot(self) -> MarketSnapshot:
        """
        Builds and returns a complete MarketSnapshot using the latest 
        available data. Missing components remain None.
        
        The candle included in the snapshot corresponds to the default 
        chart timeframe defined in the application configuration.
        
        Returns:
            A MarketSnapshot object.
        """
        with self._lock:
            return MarketSnapshot(
                tick=self._tick,
                candle=self._candles.get(self._default_timeframe),
                option_chain=self._option_chain
            )

    def clear(self) -> None:
        """Clears all stored market data and resets the state."""
        with self._lock:
            self._tick = None
            self._candles.clear()
            self._option_chain = None
            self._logger.info("Market snapshot builder state cleared.")
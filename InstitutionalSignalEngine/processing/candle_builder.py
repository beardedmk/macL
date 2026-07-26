"""
Candle builder module for the Institutional Signal Intelligence Engine.

Aggregates incoming Tick objects into OHLCV Candle objects for all 
supported timeframes. Strictly isolated from storage, indicators, 
feature engineering, and signal generation.
"""

import threading
from datetime import datetime
from typing import Dict, List, Optional

from config import TimeFrame
from core.exceptions import ValidationError
from core.logger import LoggerFactory
from models import Candle, Tick


# Mapping of supported TimeFrame enums to their duration in seconds
TIMEFRAME_SECONDS: Dict[TimeFrame, int] = {
    TimeFrame.ONE_SECOND: 1,
    TimeFrame.TWO_SECONDS: 2,
    TimeFrame.THREE_SECONDS: 3,
    TimeFrame.FIVE_SECONDS: 5,
    TimeFrame.TEN_SECONDS: 10,
    TimeFrame.FIFTEEN_SECONDS: 15,
    TimeFrame.THIRTY_SECONDS: 30,
    TimeFrame.FORTY_FIVE_SECONDS: 45,
    TimeFrame.ONE_MINUTE: 60,
    TimeFrame.THREE_MINUTES: 180,
    TimeFrame.FIVE_MINUTES: 300,
    TimeFrame.FIFTEEN_MINUTES: 900,
    TimeFrame.THIRTY_MINUTES: 1800,
}


class _CandleState:
    """Internal state tracker for an in-progress candle."""
    
    def __init__(self, start_time: datetime, open_price: float, volume: int) -> None:
        self.start_time: datetime = start_time
        self.end_time: datetime = start_time
        self.open: float = open_price
        self.high: float = open_price
        self.low: float = open_price
        self.close: float = open_price
        self.volume: int = volume


class CandleBuilder:
    """
    Thread-safe builder that aggregates raw Ticks into OHLCV Candles 
    across all configured timeframes simultaneously.
    """

    def __init__(self) -> None:
        """
        Initializes the candle builder with independent state trackers 
        for each supported timeframe.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._states: Dict[TimeFrame, Optional[_CandleState]] = {tf: None for tf in TIMEFRAME_SECONDS}
        self._completed: Dict[TimeFrame, List[Candle]] = {tf: [] for tf in TIMEFRAME_SECONDS}

    def add_tick(self, tick: Tick) -> None:
        """
        Processes a raw tick and updates the candle state for all timeframes.
        Detects candle completions and moves them to the completed buffer.
        
        Args:
            tick: The strongly typed Tick object to process.
            
        Raises:
            ValidationError: If the tick is invalid or malformed.
        """
        if not isinstance(tick, Tick):
            raise ValidationError("Input must be a valid Tick object.")
            
        if tick.ltp < 0 or tick.volume < 0:
            raise ValidationError(f"Invalid tick values: ltp={tick.ltp}, volume={tick.volume}")

        with self._lock:
            tick_ts = int(tick.timestamp.timestamp())
            tz_info = tick.timestamp.tzinfo
            
            for tf, interval_sec in TIMEFRAME_SECONDS.items():
                # Calculate the exact start and end boundaries for this tick's timeframe
                candle_start_ts = (tick_ts // interval_sec) * interval_sec
                candle_start_dt = datetime.fromtimestamp(candle_start_ts, tz=tz_info)
                candle_end_dt = datetime.fromtimestamp(candle_start_ts + interval_sec, tz=tz_info)
                
                state = self._states[tf]
                
                if state is None:
                    # First tick for this timeframe; initialize the candle
                    self._states[tf] = _CandleState(candle_start_dt, tick.ltp, tick.volume)
                    self._states[tf].end_time = candle_end_dt
                    
                elif candle_start_ts > int(state.start_time.timestamp()):
                    # The tick belongs to a new time bucket; the previous candle is completed
                    completed_candle = Candle(
                        start_time=state.start_time,
                        end_time=state.end_time,
                        open=state.open,
                        high=state.high,
                        low=state.low,
                        close=state.close,
                        volume=state.volume
                    )
                    self._completed[tf].append(completed_candle)
                    
                    # Initialize the new candle
                    self._states[tf] = _CandleState(candle_start_dt, tick.ltp, tick.volume)
                    self._states[tf].end_time = candle_end_dt
                    
                else:
                    # The tick belongs to the current in-progress candle; update OHLCV
                    state.high = max(state.high, tick.ltp)
                    state.low = min(state.low, tick.ltp)
                    state.close = tick.ltp
                    state.volume += tick.volume
                    state.end_time = candle_end_dt

    def get_current_candle(self, timeframe: TimeFrame) -> Optional[Candle]:
        """
        Retrieves the current in-progress candle for a specific timeframe.
        
        Args:
            timeframe: The timeframe to query.
            
        Returns:
            A Candle object representing the current state, or None if no ticks 
            have been processed for this timeframe yet.
            
        Raises:
            ValidationError: If the timeframe is not supported.
        """
        if timeframe not in TIMEFRAME_SECONDS:
            raise ValidationError(f"Unsupported timeframe: {timeframe}")
            
        with self._lock:
            state = self._states.get(timeframe)
            if state is None:
                return None
                
            return Candle(
                start_time=state.start_time,
                end_time=state.end_time,
                open=state.open,
                high=state.high,
                low=state.low,
                close=state.close,
                volume=state.volume
            )

    def get_completed_candles(self) -> Dict[TimeFrame, List[Candle]]:
        """
        Retrieves and clears all completed candles across all timeframes.
        
        Returns:
            A dictionary mapping each TimeFrame to a list of completed Candle objects.
        """
        with self._lock:
            completed_snapshot = {tf: list(candles) for tf, candles in self._completed.items()}
            
            # Clear the internal buffers after snapshotting
            for tf in self._completed:
                self._completed[tf] = []
                
            return completed_snapshot
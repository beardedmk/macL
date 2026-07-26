"""
Models module for the Institutional Signal Intelligence Engine.

This module defines all shared dataclasses representing the core domain objects
used across the application. It strictly contains data structures with no 
business logic, calculations, or storage operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from config import MarketRegime


@dataclass
class Tick:
    """Represents a single live market tick for an index."""
    timestamp: datetime
    index_name: str
    ltp: float
    volume: int


@dataclass
class Candle:
    """Represents an aggregated OHLCV candle."""
    start_time: datetime
    end_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class OptionTick:
    """Represents a single tick for a specific option contract."""
    strike: float
    option_type: str
    ltp: float
    oi: int
    oi_change: int
    volume: int


@dataclass
class OptionChainSnapshot:
    """Represents a complete snapshot of the option chain at a specific time."""
    timestamp: datetime
    index_name: str
    expiry: datetime
    atm_strike: float
    options: List[OptionTick] = field(default_factory=list)

# ... [Previous imports and classes remain unchanged] ...

@dataclass
# ... [Previous fields remain unchanged] ...

@dataclass
class FeatureSnapshot:
    """Represents a snapshot of all engineered features at a specific time."""
    timestamp: datetime
    index_name: str
    dominance: float
    ce_total_oi: int
    pe_total_oi: int
    breadth: float
    momentum_center: Optional[float]

    momentum_velocity: float
    momentum_acceleration: float
    vwap_distance: float
    healthy_candle: bool
    candle_type: str
    body_percent: float
    upper_wick_percent: float
    lower_wick_percent: float
    institutional_score: float
    confidence: float
    
    # Strike Migration Features
    ce_migration_direction: str
    ce_migration_distance: float
    ce_migration_speed: float
    pe_migration_direction: str
    pe_migration_distance: float
    pe_migration_speed: float
    dominant_ce_strike: Optional[float]
    dominant_pe_strike: Optional[float]


# ... [Rest of the file remains unchanged] ...
@dataclass
class SignalSnapshot:
    """Represents a generated rule-based signal."""
    timestamp: datetime
    signal: str
    confidence: float
    reason: str
    price: float


@dataclass
class MarketSnapshot:
    """
    Aggregates all market data, features, and signals into a single 
    comprehensive snapshot for a specific point in time.
    """
    tick: Optional[Tick] = None
    candle: Optional[Candle] = None
    option_chain: Optional[OptionChainSnapshot] = None
    features: Optional[FeatureSnapshot] = None
    signal: Optional[SignalSnapshot] = None


@dataclass
class SessionInfo:
    """Represents the current market regime and its timing parameters."""
    regime: MarketRegime
    start_time: datetime
    end_time: datetime
    weight: float


@dataclass
class ReplayFrame:
    """Represents a single frame of historical data for replay/backtesting."""
    timestamp: datetime
    snapshot: MarketSnapshot


@dataclass
class EngineStatistics:
    """Tracks real-time operational counters and statistics for the engine."""
    ticks_processed: int = 0
    candles_created: int = 0
    signals_generated: int = 0
    signals_rejected: int = 0
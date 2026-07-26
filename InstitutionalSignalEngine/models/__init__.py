# Models package
"""
Models module for the Institutional Signal Intelligence Engine.

Defines all shared dataclasses representing the core domain objects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any, Dict


@dataclass
class Tick:
    """Represents a single live market tick."""
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


@dataclass
class FeatureSnapshot:
    """Represents a snapshot of all engineered features at a specific time."""
    timestamp: datetime
    index_name: str
    
    # Dominance & Breadth
    dominance: float
    ce_total_oi: int
    pe_total_oi: int
    breadth: float
    
    # Momentum Center
    momentum_center: Optional[float]
    momentum_velocity: float
    momentum_acceleration: float
    
    # VWAP (Placeholder for future calculator)
    vwap_distance: float
    
    # Healthy Candle Geometry
    healthy_candle: bool
    candle_type: str
    body_percent: float
    upper_wick_percent: float
    lower_wick_percent: float
    
    # Institutional Score
    institutional_score: float
    confidence: float
    
    # Strike Migration
    ce_migration_direction: str
    ce_migration_distance: float
    ce_migration_speed: float
    pe_migration_direction: str
    pe_migration_distance: float
    pe_migration_speed: float
    dominant_ce_strike: Optional[float]
    dominant_pe_strike: Optional[float]


@dataclass
class MarketSnapshot:
    """Aggregates all market data into a single comprehensive snapshot."""
    tick: Optional[Tick] = None
    candle: Optional[Candle] = None
    option_chain: Optional[OptionChainSnapshot] = None
    features: Optional[FeatureSnapshot] = None
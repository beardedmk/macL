"""
Configuration module for the Institutional Signal Intelligence Engine.

This module defines all configuration dataclasses used across the application.
It strictly separates configuration concerns and aggregates them into a root
ApplicationConfig object. No environment variables are loaded here; all values
are explicitly defined or injected via dependency injection.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List


class IndexSymbol(str, Enum):
    """Supported Indian Index Symbols."""
    NIFTY = "NIFTY"
    BANKNIFTY = "BANKNIFTY"
    SENSEX = "SENSEX"


class ExpiryType(str, Enum):
    """Supported option expiry types."""
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class TimeFrame(str, Enum):
    """Supported chart and signal timeframes (seconds and minutes)."""
    ONE_SECOND = "1s"
    TWO_SECONDS = "2s"
    THREE_SECONDS = "3s"
    FIVE_SECONDS = "5s"
    TEN_SECONDS = "10s"
    FIFTEEN_SECONDS = "15s"
    THIRTY_SECONDS = "30s"
    FORTY_FIVE_SECONDS = "45s"
    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"


class MarketRegime(str, Enum):
    """Institutional market regime classifications."""
    OPENING_INSTITUTIONAL = "OPENING_INSTITUTIONAL"
    MORNING_TREND = "MORNING_TREND"
    MIDDAY_DEADZONE = "MIDDAY_DEADZONE"
    AFTERNOON_BUILDUP = "AFTERNOON_BUILDUP"
    CLOSING_INSTITUTIONAL = "CLOSING_INSTITUTIONAL"
    LATE_CLOSE = "LATE_CLOSE"


class LogLevel(str, Enum):
    """Standard logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class AuthenticationConfig:
    """Configuration for data provider authentication."""
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    token_refresh_url: str = ""


@dataclass
class WebSocketConfig:
    """Configuration for live market data WebSocket connection."""
    url: str = "wss://ws.example.com/feed"
    reconnect_interval_sec: int = 5
    ping_interval_sec: int = 10
    max_reconnect_attempts: int = 10


@dataclass
class MarketConfig:
    """Configuration for general market hours and supported indices."""
    supported_indices: List[IndexSymbol] = field(
        default_factory=lambda: [IndexSymbol.NIFTY, IndexSymbol.BANKNIFTY, IndexSymbol.SENSEX]
    )
    supported_expiry_types: List[ExpiryType] = field(
        default_factory=lambda: [ExpiryType.WEEKLY, ExpiryType.MONTHLY]
    )
    timezone: str = "Asia/Kolkata"
    pre_open: str = "09:00"
    pre_open_end: str = "09:15"
    market_open: str = "09:15"
    market_close: str = "15:30"


@dataclass
class SessionTiming:
    """Defines the timing and training weight for a specific market regime."""
    start_time: str
    end_time: str
    weight: float


@dataclass
class SessionConfig:
    """Configuration for market regimes, their timings, and training weights."""
    regimes: Dict[MarketRegime, SessionTiming] = field(
        default_factory=lambda: {
            MarketRegime.OPENING_INSTITUTIONAL: SessionTiming("09:15", "09:30", 3.0),
            MarketRegime.MORNING_TREND: SessionTiming("09:30", "11:00", 2.0),
            MarketRegime.MIDDAY_DEADZONE: SessionTiming("11:00", "13:30", 0.5),
            MarketRegime.AFTERNOON_BUILDUP: SessionTiming("13:30", "14:45", 1.5),
            MarketRegime.CLOSING_INSTITUTIONAL: SessionTiming("14:45", "15:05", 3.0),
            MarketRegime.LATE_CLOSE: SessionTiming("15:05", "15:30", 1.5),
        }
    )


@dataclass
class StorageConfig:
    """Configuration for disk-first storage paths and directories."""
    base_path: Path = Path("./data")
    raw_ticks_dir: str = "raw_ticks"
    candles_dir: str = "candles"
    features_dir: str = "features"
    signals_dir: str = "signals"
    labels_dir: str = "labels"
    option_chain_dir: str = "option_chain"
    metadata_dir: str = "metadata"
    sessions_dir: str = "sessions"
    models_dir: str = "models"
    logs_dir: str = "logs"
    
    feature_store_format: str = "parquet"
    signal_store_format: str = "parquet"
    tick_store_format: str = "parquet"
    compression: str = "snappy"
    flush_interval_seconds: int = 1
    batch_size: int = 100
    auto_rotate_daily: bool = True


@dataclass
class DashboardConfig:
    """Configuration for the local UI dashboard."""
    host: str = "127.0.0.1"
    port: int = 8050
    refresh_interval_ms: int = 500
    momentum_refresh_interval_ms: int = 1000
    enable_debug: bool = False
    
    chart_history_candles: int = 120
    crosshair_enabled: bool = True
    auto_follow_latest: bool = True

@dataclass
class SignalConfig:
    """Configuration for rule-based signal generation and thresholds."""
    default_chart_timeframe: TimeFrame = TimeFrame.FIVE_MINUTES
    signal_timeframe: TimeFrame = TimeFrame.THREE_MINUTES
    min_confidence: float = 0.60
    min_dominance: float = 0.50
    min_institutional_score: float = 0.70
    min_breadth: float = 0.50
    
    signal_expiry_seconds: int = 60
    store_all_signals: bool = True
    store_rejected_signals: bool = True
    
    # Momentum Signal Configuration
    min_momentum_velocity: float = 0.5
    min_momentum_acceleration: float = 0.1
    base_confidence: float = 50.0
    confirmation_bonus: float = 10.0
    max_confidence: float = 80.0

    # Strike Migration Signal Configuration
    min_strike_migration_distance: float = 50.0
    min_strike_migration_speed: float = 10.0

    # Breadth Signal Configuration
    min_breadth_difference: float = 10.0

     # Dominance Signal Configuration
    min_dominance_difference: float = 10.0
    min_winning_oi: int = 100000

    # Institutional Signal Configuration
    min_institutional_score_buy: float = 70.0
    min_institutional_score_sell: float = 30.0
    extreme_institutional_score: float = 85.0
    strongest_institutional_zone: float = 90.0

    # Multi-Factor Ensemble Configuration
    minimum_confirmations: int = 3
    minimum_average_confidence: float = 65.0
    strong_signal_confidence: float = 80.0

    # Signal Validator Configuration
    minimum_reason_length: int = 10
    minimum_valid_confidence: float = 60.0
    maximum_confidence: float = 100.0

    # Risk Filter Configuration
    minimum_execution_confidence: float = 70.0
    minimum_execution_institutional_score: float = 60.0
    minimum_execution_breadth: float = 50.0
    minimum_execution_dominance: float = 50.0
    maximum_allowed_acceleration: float = 5.0

    # Exit Signal Configuration
    minimum_exit_score: float = 40.0
    maximum_negative_velocity: float = -1.0
    maximum_negative_acceleration: float = -0.5
    exit_on_opposite_candle: bool = True


@dataclass
class FeatureConfig:
    """Feature registry containing boolean toggles for engineered features."""
    dominance: bool = True
    breadth: bool = True
    healthy_candle: bool = True
    strike_migration: bool = True
    momentum_center: bool = True
    momentum_velocity: bool = True
    momentum_acceleration: bool = True
    vwap_distance: bool = True
    opening_range: bool = True
    atr: bool = True
    volatility: bool = True
    institutional_score: bool = True
    
    cache_features: bool = True
    persist_features: bool = True
    calculate_in_parallel: bool = True

@dataclass
class LoggingConfig:
    """Configuration for application logging and rotation."""
    log_level: LogLevel = LogLevel.INFO
    log_file_name: str = "engine.log"
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class ReplayConfig:
    """Configuration for historical data replay and backtesting."""
    enabled: bool = False
    start_date: str = ""
    end_date: str = ""
    supported_speeds: List[float] = field(
        default_factory=lambda: [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
    )
    default_speed: float = 1.0


@dataclass
class ModelConfig:
    """Configuration for future ML model training parameters."""
    training_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "momentum": 0.3,
            "volume": 0.2,
            "price_action": 0.3,
            "volatility": 0.2,
        }
    )
    target_columns: List[str] = field(default_factory=lambda: ["target_return"])


@dataclass
class VersionConfig:
    """Centralized version control for application components."""
    application: str = "0.1.0"
    feature: str = "1.0.0"
    rule: str = "1.0.0"
    dataset: str = "1.0.0"
    model: str = "1.0.0"


@dataclass
class ApplicationConfig:
    """
    Root configuration object aggregating all domain-specific configurations.
    
    This class serves as the single source of truth for application settings,
    injected into core components via dependency injection.
    """
    app_name: str = "InstitutionalSignalEngine"
    
    versions: VersionConfig = field(default_factory=VersionConfig)
    auth: AuthenticationConfig = field(default_factory=AuthenticationConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    feature: FeatureConfig = field(default_factory=FeatureConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    replay: ReplayConfig = field(default_factory=ReplayConfig)
    model: ModelConfig = field(default_factory=ModelConfig)


# Global singleton instance for dependency injection across modules
config = ApplicationConfig()
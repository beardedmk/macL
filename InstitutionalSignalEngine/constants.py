"""
Constants module for the Institutional Signal Intelligence Engine.

This module contains strictly constant values used across the application.
It contains no business logic, no functions, no dataclasses, and no side effects.
"""

# ====================================
# 1. Application Constants
# ====================================
APP_DESCRIPTION: str = "Enterprise-grade signal intelligence for Indian Index Options"
APP_NAME: str = "Institutional Signal Intelligence Engine"
AUTHOR: str = "Institutional Signal Engine Team"
COPYRIGHT: str = "Copyright (c) 2024. All rights reserved."
DEFAULT_TIMEZONE: str = "Asia/Kolkata"

# ====================================
# 2. Market Constants
# ====================================
INDEX_BANKNIFTY: str = "BANKNIFTY"
INDEX_NIFTY: str = "NIFTY"
INDEX_SENSEX: str = "SENSEX"

INDEX_NAMES: tuple[str, ...] = (INDEX_BANKNIFTY, INDEX_NIFTY, INDEX_SENSEX)
LOT_SIZE_PLACEHOLDERS: dict[str, int] = {INDEX_BANKNIFTY: 15, INDEX_NIFTY: 25, INDEX_SENSEX: 10}
MAX_OPTION_DEPTH: int = 5
MAX_STRIKE_DISTANCE: int = 10
PRICE_PRECISION: int = 2

# ====================================
# 3. Signal Constants
# ====================================
BUY_CE: str = "BUY_CE"
BUY_PE: str = "BUY_PE"
EXIT: str = "EXIT"
NO_SIGNAL: str = "NO_SIGNAL"
WAIT: str = "WAIT"

# ====================================
# 4. Confidence Levels
# ====================================
HIGH: float = 0.8
LOW: float = 0.4
MEDIUM: float = 0.6
VERY_HIGH: float = 1.0
VERY_LOW: float = 0.2

# ====================================
# 5. Storage Constants
# ====================================
# Directory names
CANDLES_DIR: str = "candles"
FEATURES_DIR: str = "features"
LABELS_DIR: str = "labels"
LOGS_DIR: str = "logs"
METADATA_DIR: str = "metadata"
MODELS_DIR: str = "models"
OPTION_CHAIN_DIR: str = "option_chain"
RAW_TICKS_DIR: str = "raw_ticks"
SESSIONS_DIR: str = "sessions"
SIGNALS_DIR: str = "signals"

# File extensions
CSV_EXTENSION: str = ".csv"
JSON_EXTENSION: str = ".json"
LOG_EXTENSION: str = ".log"
PARQUET_EXTENSION: str = ".parquet"

# Storage Filenames
FEATURE_FILE: str = f"{FEATURES_DIR}{PARQUET_EXTENSION}"
LABEL_FILE: str = f"{LABELS_DIR}{PARQUET_EXTENSION}"
OPTION_CHAIN_FILE: str = f"{OPTION_CHAIN_DIR}{PARQUET_EXTENSION}"
RAW_TICKS_FILE: str = f"{RAW_TICKS_DIR}{PARQUET_EXTENSION}"
SIGNAL_FILE: str = f"{SIGNALS_DIR}{PARQUET_EXTENSION}"

# ====================================
# 6. Dataset Columns
# ====================================
ACCELERATION: str = "acceleration"
ASK: str = "ask"
ATM_STRIKE: str = "atm_strike"
ATR: str = "atr"
BID: str = "bid"
BREADTH: str = "breadth"
CE_OI: str = "ce_oi"
CE_PRICE: str = "ce_price"
CE_VOLUME: str = "ce_volume"
CLOSE: str = "close"
CONFIDENCE: str = "confidence"
DATASET_VERSION: str = "dataset_version"
DOMINANCE: str = "dominance"
FEATURE_VERSION: str = "feature_version"
FUTURE_RETURN_1M: str = "future_return_1m"
FUTURE_RETURN_30S: str = "future_return_30s"
FUTURE_RETURN_3M: str = "future_return_3m"
FUTURE_RETURN_5M: str = "future_return_5m"
HEALTHY_CANDLE: str = "healthy_candle"
HIGH: str = "high"
INDEX_NAME: str = "index_name"
INDEX_PRICE: str = "index_price"
INSTITUTIONAL_SCORE: str = "institutional_score"
LOW: str = "low"
LTP: str = "ltp"
MAE: str = "mae"
MFE: str = "mfe"
MODEL_VERSION: str = "model_version"
MOMENTUM: str = "momentum"
OI: str = "oi"
OI_CHANGE: str = "oi_change"
OPEN: str = "open"
OPTION_TYPE: str = "option_type"
PE_OI: str = "pe_oi"
PE_PRICE: str = "pe_price"
PE_VOLUME: str = "pe_volume"
RULE_VERSION: str = "rule_version"
SESSION: str = "session"
SESSION_NAME: str = "session_name"
SESSION_WEIGHT: str = "session_weight"
SIGNAL: str = "signal"
STRIKE: str = "strike"
TIMESTAMP: str = "timestamp"
VELOCITY: str = "velocity"
VOLATILITY: str = "volatility"
VOLUME: str = "volume"
VWAP: str = "vwap"
VWAP_DISTANCE: str = "vwap_distance"

# ====================================
# 7. Feature Names
# ====================================
ACCELERATION_FEATURE: str = "acceleration"
ATR_FEATURE: str = "atr"
BREADTH_FEATURE: str = "breadth"
DOMINANCE_FEATURE: str = "dominance"
HEALTHY_CANDLE_FEATURE: str = "healthy_candle"
INSTITUTIONAL_SCORE_FEATURE: str = "institutional_score"
MOMENTUM_CENTER_FEATURE: str = "momentum_center"
MOMENTUM_FEATURE: str = "momentum"
OPENING_RANGE_FEATURE: str = "opening_range"
STRIKE_MIGRATION_FEATURE: str = "strike_migration"
VELOCITY_FEATURE: str = "velocity"
VOLATILITY_FEATURE: str = "volatility"
VWAP_FEATURE: str = "vwap"

# ====================================
# 8. Candle Constants
# ====================================
DOJI: str = "DOJI"
GREEN: str = "GREEN"
HAMMER: str = "HAMMER"
INVERTED_HAMMER: str = "INVERTED_HAMMER"
MARUBOZU: str = "MARUBOZU"
RED: str = "RED"
SPINNING_TOP: str = "SPINNING_TOP"

# ====================================
# 9. Option Types
# ====================================
ATM: str = "ATM"
CALL: str = "CALL"
CE: str = "CE"
ITM: str = "ITM"
OTM: str = "OTM"
PE: str = "PE"
PUT: str = "PUT"

# ====================================
# 10. Market Directions
# ====================================
BEARISH: str = "BEARISH"
BULLISH: str = "BULLISH"
SIDEWAYS: str = "SIDEWAYS"
VOLATILE: str = "VOLATILE"

# ====================================
# 11. Dataset Status
# ====================================
LABELED: str = "LABELED"
PROCESSED: str = "PROCESSED"
RAW: str = "RAW"
TRAINED: str = "TRAINED"
VALIDATED: str = "VALIDATED"

# ====================================
# 12. ML Labels
# ====================================
BUY_LABEL: str = "BUY"
SELL_LABEL: str = "SELL"
TARGET: str = "target"
TARGET_CLASS: str = "target_class"
TARGET_REGRESSION: str = "target_regression"
WAIT_LABEL: str = "WAIT"

# ====================================
# 13. Dashboard Refresh Constants
# ====================================
FAST_REFRESH_MS: int = 100
NORMAL_REFRESH_MS: int = 500
SLOW_REFRESH_MS: int = 2000

# ====================================
# 14. Colors
# ====================================
BACKGROUND_COLOR: str = "#1e1e1e"
BUY_COLOR: str = "#00c853"
GRID_COLOR: str = "#333333"
SELL_COLOR: str = "#ff1744"
TEXT_COLOR: str = "#ffffff"
WAIT_COLOR: str = "#ffab00"

# ====================================
# 15. Logging
# ====================================
AUTH_LOGGER: str = "auth"
DATA_LOGGER: str = "data"
FEATURE_LOGGER: str = "features"
ROOT_LOGGER: str = "engine"
SIGNAL_LOGGER: str = "signals"
WS_LOGGER: str = "websocket"

# ====================================
# 16. Miscellaneous
# ====================================
DEFAULT_ENCODING: str = "utf-8"
EMPTY_STRING: str = ""
FALSE_LABEL: int = 0
INVALID: str = "INVALID"
TRUE_LABEL: int = 1
UNKNOWN: str = "UNKNOWN"
"""
Custom exceptions module for the Institutional Signal Intelligence Engine.

This module defines the centralized exception hierarchy used across the 
application. All custom exceptions inherit from the base EngineError to 
allow for consistent and targeted error handling.
"""


class EngineError(Exception):
    """Base exception for all errors raised by the Institutional Signal Intelligence Engine."""


class ConfigurationError(EngineError):
    """Raised when there is an invalid, missing, or incompatible application configuration."""


class AuthenticationError(EngineError):
    """Raised when data provider authentication fails or tokens are invalid."""


class WebSocketError(EngineError):
    """Raised when a general WebSocket connection or protocol error occurs."""


class ConnectionLostError(WebSocketError):
    """Raised when the active WebSocket connection is unexpectedly dropped."""


class PacketDecodeError(WebSocketError):
    """Raised when incoming market data packets cannot be parsed or decoded."""


class OptionChainError(EngineError):
    """Raised when there is an error fetching, parsing, or processing the option chain."""


class StorageError(EngineError):
    """Raised when disk read/write operations, file rotations, or data persistence fail."""


class ReplayError(EngineError):
    """Raised when historical data replay or backtesting execution encounters an error."""


class FeatureCalculationError(EngineError):
    """Raised when engineered feature calculations fail or produce invalid mathematical results."""


class SignalGenerationError(EngineError):
    """Raised when the rule-based signal generation engine encounters an unexpected state."""


class ValidationError(EngineError):
    """Raised when input data, market ticks, or internal states fail validation checks."""


class MarketClosedError(EngineError):
    """Raised when an operation requiring live market data is attempted outside trading hours."""


class DataIntegrityError(EngineError):
    """Raised when stored or incoming data is corrupted, missing expected fields, or inconsistent."""


class TimeoutError(EngineError):
    """Raised when an operation, such as network requests or data fetching, exceeds its allowed time limit."""
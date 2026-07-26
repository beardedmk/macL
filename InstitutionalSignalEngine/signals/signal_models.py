"""
Signal models module for the Institutional Signal Intelligence Engine.

Defines the standardized, immutable data models and enumerations used across 
the entire Signal layer. This module contains no business logic or calculations; 
it strictly enforces the structural contract for signal generation and aggregation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List
from uuid import UUID, uuid4

from core.exceptions import ValidationError


class SignalDirection(str, Enum):
    """Represents the directional bias of a signal."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class SignalDecision(str, Enum):
    """Represents the final actionable decision derived from aggregated signals."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_TRADE = "NO_TRADE"


class SignalStrength(str, Enum):
    """Represents the qualitative strength of a signal."""
    VERY_WEAK = "VERY_WEAK"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


@dataclass(frozen=True)
class SignalResult:
    """
    Represents the output of an individual signal generator.
    
    This immutable model ensures that every signal module returns a 
    standardized structure for the SignalEngine to process.
    """
    signal_name: str
    direction: SignalDirection
    score: float
    confidence: float
    weight: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validates the signal result fields upon initialization."""
        if not isinstance(self.signal_name, str) or not self.signal_name:
            raise ValidationError("signal_name must be a non-empty string.")
        if not isinstance(self.direction, SignalDirection):
            raise ValidationError(f"direction must be a SignalDirection enum, got {type(self.direction)}.")
        if not (0.0 <= self.score <= 100.0):
            raise ValidationError(f"score must be between 0.0 and 100.0, got {self.score}.")
        if not (0.0 <= self.confidence <= 100.0):
            raise ValidationError(f"confidence must be between 0.0 and 100.0, got {self.confidence}.")
        if self.weight < 0.0:
            raise ValidationError(f"weight must be >= 0.0, got {self.weight}.")
        if not isinstance(self.timestamp, datetime):
            raise ValidationError(f"timestamp must be a datetime object, got {type(self.timestamp)}.")


@dataclass(frozen=True)
class FinalSignal:
    """
    Represents the final, aggregated trading signal produced by the SignalEngine.
    
    This immutable model encapsulates the collective decision, scores, and 
    reasoning derived from multiple individual SignalResult objects.
    """
    timestamp: datetime
    decision: SignalDecision
    bullish_score: float
    bearish_score: float
    confidence: float
    reason_summary: str
    signal_id: UUID = field(default_factory=uuid4)
    supporting_signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validates the final signal fields upon initialization."""
        if not isinstance(self.timestamp, datetime):
            raise ValidationError(f"timestamp must be a datetime object, got {type(self.timestamp)}.")
        if not isinstance(self.decision, SignalDecision):
            raise ValidationError(f"decision must be a SignalDecision enum, got {type(self.decision)}.")
        if not (0.0 <= self.bullish_score <= 100.0):
            raise ValidationError(f"bullish_score must be between 0.0 and 100.0, got {self.bullish_score}.")
        if not (0.0 <= self.bearish_score <= 100.0):
            raise ValidationError(f"bearish_score must be between 0.0 and 100.0, got {self.bearish_score}.")
        if not (0.0 <= self.confidence <= 100.0):
            raise ValidationError(f"confidence must be between 0.0 and 100.0, got {self.confidence}.")
        if not isinstance(self.reason_summary, str):
            raise ValidationError(f"reason_summary must be a string, got {type(self.reason_summary)}.")
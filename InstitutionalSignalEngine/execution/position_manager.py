"""
Position manager module for the Institutional Signal Intelligence Engine.

Manages the lifecycle of trading positions (state tracking only) independently 
of signal generation. Strictly isolated from broker execution, storage, 
machine learning, and indicator calculation.
"""

import threading
from datetime import datetime
from typing import Any, Dict, Optional

from core.exceptions import ValidationError
from core.logger import LoggerFactory


class PositionManager:
    """
    Thread-safe state manager for tracking open trading positions, 
    calculating unrealized P&L, and recording trade lifecycle metadata.
    """

    def __init__(self) -> None:
        """Initializes the position manager with empty state and a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._current_position: str = "NONE"
        self._entry_price: float = 0.0
        self._entry_time: Optional[datetime] = None
        self._quantity: int = 0
        self._stop_loss: float = 0.0
        self._target: float = 0.0
        self._metadata: Dict[str, Any] = {}
        
        self._current_market_price: float = 0.0
        self._last_update_time: Optional[datetime] = None

    def open_position(
        self, 
        position_type: str, 
        entry_price: float, 
        entry_time: datetime, 
        quantity: int, 
        stop_loss: float, 
        target: float, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Opens a new trading position.
        
        Args:
            position_type: "BUY" or "SELL".
            entry_price: The price at which the position is opened.
            entry_time: The timestamp of the entry.
            quantity: The number of units/contracts.
            stop_loss: The stop loss price for the position.
            target: The target price for the position.
            metadata: Optional dictionary containing additional entry context.
            
        Raises:
            ValidationError: If the position type is invalid or a position is already open.
        """
        if position_type not in {"BUY", "SELL"}:
            raise ValidationError(f"Invalid position type: '{position_type}'. Must be BUY or SELL.")
            
        with self._lock:
            if self._current_position != "NONE":
                raise ValidationError(
                    f"Cannot open position: A {self._current_position} position is already open."
                )
                
            self._current_position = position_type
            self._entry_price = entry_price
            self._entry_time = entry_time
            self._quantity = quantity
            self._stop_loss = stop_loss
            self._target = target
            self._metadata = metadata or {}
            
            # Initialize market price tracking
            self._current_market_price = entry_price
            self._last_update_time = entry_time
            
            self._logger.info(
                f"Opened {position_type} position | Price: {entry_price} | "
                f"Qty: {quantity} | SL: {stop_loss} | Target: {target}"
            )

    def close_position(self, exit_price: float, exit_time: datetime) -> Dict[str, Any]:
        """
        Closes the currently open trading position and returns a trade record.
        
        Args:
            exit_price: The price at which the position is closed.
            exit_time: The timestamp of the exit.
            
        Returns:
            A dictionary containing the complete trade record (entry/exit details, PnL, duration).
            
        Raises:
            ValidationError: If no position is currently open.
        """
        with self._lock:
            if self._current_position == "NONE":
                raise ValidationError("Cannot close position: No position is currently open.")
                
            position_type = self._current_position
            entry_price = self._entry_price
            quantity = self._quantity
            entry_time = self._entry_time
            metadata = self._metadata
            
            # Calculate realized P&L
            if position_type == "BUY":
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity
                
            duration_seconds = (exit_time - entry_time).total_seconds()
            
            trade_record = {
                "position_type": position_type,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": quantity,
                "stop_loss": self._stop_loss,
                "target": self._target,
                "realized_pnl": pnl,
                "duration_seconds": duration_seconds,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "metadata": metadata
            }
            
            # Reset state
            self._current_position = "NONE"
            self._entry_price = 0.0
            self._entry_time = None
            self._quantity = 0
            self._stop_loss = 0.0
            self._target = 0.0
            self._metadata = {}
            self._current_market_price = 0.0
            self._last_update_time = None
            
            self._logger.info(
                f"Closed {position_type} position | Exit Price: {exit_price} | "
                f"PnL: {pnl} | Duration: {duration_seconds}s"
            )
            
            return trade_record

    def update_market_price(self, current_price: float, update_time: Optional[datetime] = None) -> None:
        """
        Updates the current market price for unrealized P&L calculation.
        
        Args:
            current_price: The latest market price.
            update_time: Optional timestamp for the price update. Defaults to None.
        """
        with self._lock:
            self._current_market_price = current_price
            self._last_update_time = update_time

    def get_current_position(self) -> str:
        """
        Retrieves the current position type.
        
        Returns:
            "BUY", "SELL", or "NONE".
        """
        with self._lock:
            return self._current_position

    def has_open_position(self) -> bool:
        """
        Checks if there is an active open position.
        
        Returns:
            True if a position is open, False otherwise.
        """
        with self._lock:
            return self._current_position != "NONE"

    def get_unrealized_pnl(self) -> float:
        """
        Calculates the unrealized P&L based on the last supplied market price.
        
        Returns:
            The unrealized P&L as a float. Returns 0.0 if no position is open.
        """
        with self._lock:
            if self._current_position == "NONE":
                return 0.0
                
            if self._current_position == "BUY":
                return (self._current_market_price - self._entry_price) * self._quantity
            else:
                return (self._entry_price - self._current_market_price) * self._quantity

    def reset(self) -> None:
        """Clears all position state and resets the manager to its initial state."""
        with self._lock:
            self._current_position = "NONE"
            self._entry_price = 0.0
            self._entry_time = None
            self._quantity = 0
            self._stop_loss = 0.0
            self._target = 0.0
            self._metadata = {}
            self._current_market_price = 0.0
            self._last_update_time = None
            self._logger.info("Position manager state reset.")
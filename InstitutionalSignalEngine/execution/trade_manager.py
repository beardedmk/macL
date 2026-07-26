"""
Trade manager module for the Institutional Signal Intelligence Engine.

Orchestrates the complete trade lifecycle by coordinating the PositionManager 
and OrderManager. Strictly isolated from signal generation, indicator 
calculation, broker execution, and storage.
"""

import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from core.exceptions import ValidationError
from core.logger import LoggerFactory
from execution.order_manager import OrderManager
from execution.position_manager import PositionManager


class TradeManager:
    """
    Thread-safe orchestration layer that coordinates order and position 
    lifecycles to manage complete trades. Prevents duplicate active trades 
    and ensures strict state synchronization between orders and positions.
    """

    def __init__(
        self, 
        position_manager: PositionManager, 
        order_manager: OrderManager
    ) -> None:
        """
        Initializes the trade manager with required dependencies.
        
        Args:
            position_manager: The manager responsible for position state.
            order_manager: The manager responsible for order state.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._position_manager = position_manager
        self._order_manager = order_manager
        
        self._active_order_id: Optional[str] = None
        self._pending_trade_params: Optional[Dict[str, Any]] = None
        self._last_trade_summary: Optional[Dict[str, Any]] = None

    def open_trade(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        stop_loss: float,
        target: float,
        metadata: Optional[Dict[str, Any]] = None,
        order_id: Optional[str] = None
    ) -> str:
        """
        Initiates a new trade by creating a pending order.
        
        Args:
            symbol: The trading instrument symbol.
            side: "BUY" or "SELL".
            quantity: The number of units/contracts.
            price: The limit or market price.
            stop_loss: The stop loss price for the position.
            target: The target price for the position.
            metadata: Optional context for the trade.
            order_id: Optional explicit order ID. Generated if not provided.
            
        Returns:
            The unique order ID for the created trade.
            
        Raises:
            ValidationError: If a trade is already active or inputs are invalid.
        """
        with self._lock:
            if self._active_order_id is not None or self._position_manager.has_open_position():
                raise ValidationError("Cannot open trade: A trade is already active.")

            if order_id is None:
                order_id = uuid.uuid4().hex

            # Store parameters needed for position opening upon fill
            self._pending_trade_params = {
                "stop_loss": stop_loss,
                "target": target,
                "metadata": metadata or {}
            }

            self._order_manager.create_order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                metadata=metadata
            )
            
            self._active_order_id = order_id
            self._logger.info(f"Trade initiated | Order {order_id} | {side} {quantity} {symbol} @ {price}")
            
            return order_id

    def fill_trade(
        self, 
        order_id: str, 
        fill_price: float, 
        fill_time: Optional[datetime] = None
    ) -> None:
        """
        Marks the pending order as filled and opens the corresponding position.
        
        Args:
            order_id: The order ID to fill.
            fill_price: The actual execution price.
            fill_time: Optional timestamp of the fill.
            
        Raises:
            ValidationError: If the order ID does not match the active trade.
        """
        with self._lock:
            if order_id != self._active_order_id:
                raise ValidationError(
                    f"Cannot fill trade: Order '{order_id}' is not the active trade."
                )
                
            order_details = self._order_manager.get_order(order_id)
            fill_time = fill_time or datetime.now()
            
            # Transition order state
            self._order_manager.fill_order(order_id, fill_price, fill_time)
            
            # Open position state
            if self._pending_trade_params is None:
                raise ValidationError("Missing pending trade parameters for position opening.")
                
            self._position_manager.open_position(
                position_type=order_details["side"],
                entry_price=fill_price,
                entry_time=fill_time,
                quantity=order_details["quantity"],
                stop_loss=self._pending_trade_params["stop_loss"],
                target=self._pending_trade_params["target"],
                metadata=self._pending_trade_params["metadata"]
            )
            
            # Clear pending state as position is now open
            self._pending_trade_params = None
            self._logger.info(f"Trade filled and position opened | Order {order_id} @ {fill_price}")

    def close_trade(
        self, 
        exit_price: float, 
        exit_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Closes the currently open position and finalizes the trade.
        
        Args:
            exit_price: The price at which the position is closed.
            exit_time: Optional timestamp of the exit.
            
        Returns:
            A dictionary containing the complete trade record.
            
        Raises:
            ValidationError: If no position is currently open.
        """
        with self._lock:
            if not self._position_manager.has_open_position():
                raise ValidationError("Cannot close trade: No position is currently open.")
                
            exit_time = exit_time or datetime.now()
            
            # Close position and get the final trade record
            trade_record = self._position_manager.close_position(exit_price, exit_time)
            
            # Update internal state
            self._last_trade_summary = trade_record
            self._active_order_id = None
            
            self._logger.info(
                f"Trade closed | PnL: {trade_record['realized_pnl']} | "
                f"Duration: {trade_record['duration_seconds']}s"
            )
            
            return trade_record

    def cancel_trade(self, order_id: str) -> None:
        """
        Cancels a pending trade order before it is filled.
        
        Args:
            order_id: The order ID to cancel.
            
        Raises:
            ValidationError: If the order ID does not match the active trade.
        """
        with self._lock:
            if order_id != self._active_order_id:
                raise ValidationError(
                    f"Cannot cancel trade: Order '{order_id}' is not the active trade."
                )
                
            self._order_manager.cancel_order(order_id)
            
            # Clear internal state
            self._active_order_id = None
            self._pending_trade_params = None
            
            self._logger.info(f"Trade cancelled | Order {order_id}")


    def update_market_price(self, current_price: float) -> None:
        """
        Updates the current market price for the open position to calculate 
        unrealized PnL. Delegates to the underlying PositionManager.
        
        Args:
            current_price: The latest market price.
        """
        with self._lock:
            self._position_manager.update_market_price(current_price)

    def get_active_trade(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves details of the currently active trade (order and/or position).
        
        Returns:
            A dictionary containing active trade details, or None if no trade is active.
        """
        with self._lock:
            if self._active_order_id is None and not self._position_manager.has_open_position():
                return None
                
            result: Dict[str, Any] = {
                "order_id": self._active_order_id,
                "has_open_position": self._position_manager.has_open_position(),
                "current_position": self._position_manager.get_current_position(),
                "unrealized_pnl": self._position_manager.get_unrealized_pnl()
            }
            
            if self._active_order_id:
                try:
                    result["order_details"] = self._order_manager.get_order(self._active_order_id)
                except ValidationError:
                    pass  # Order might have been cleared in a race condition
                    
            return result

    def has_active_trade(self) -> bool:
        """
        Checks if there is an active trade (either pending order or open position).
        
        Returns:
            True if a trade is active, False otherwise.
        """
        with self._lock:
            return self._active_order_id is not None or self._position_manager.has_open_position()

    def get_trade_summary(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the summary of the last completed trade, or the current 
        unrealized state if a position is still open.
        
        Returns:
            A dictionary containing the trade summary, or None if no trades have occurred.
        """
        with self._lock:
            if self._position_manager.has_open_position():
                return {
                    "status": "OPEN",
                    "current_position": self._position_manager.get_current_position(),
                    "unrealized_pnl": self._position_manager.get_unrealized_pnl()
                }
                
            return self._last_trade_summary

    def reset(self) -> None:
        """Clears all trade, order, and position states."""
        with self._lock:
            self._position_manager.reset()
            self._order_manager.reset()
            
            self._active_order_id = None
            self._pending_trade_params = None
            self._last_trade_summary = None
            
            self._logger.info("Trade manager state reset. All trades, orders, and positions cleared.")
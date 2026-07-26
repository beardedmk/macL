"""
Order manager module for the Institutional Signal Intelligence Engine.

Manages the lifecycle of trading orders (state tracking only) independently 
of positions, signal generation, and broker execution. Strictly isolated 
from storage, machine learning, and broker APIs.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from core.exceptions import ValidationError
from core.logger import LoggerFactory


class OrderStatus(str, Enum):
    """Supported order lifecycle states."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


# Terminal states that cannot transition further
_TERMINAL_STATES = {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}


@dataclass
class _OrderRecord:
    """Internal representation of a single order's state and metadata."""
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    status: OrderStatus
    created_time: datetime
    updated_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderManager:
    """
    Thread-safe state manager for tracking the lifecycle of trading orders.
    Enforces strict state transition rules and maintains complete order history.
    """

    def __init__(self) -> None:
        """Initializes the order manager with an empty order book and a dedicated logger."""
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        self._orders: Dict[str, _OrderRecord] = {}

    def create_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Creates a new order in PENDING status.
        
        Args:
            order_id: Unique identifier for the order.
            symbol: The trading instrument symbol.
            side: "BUY" or "SELL".
            quantity: The number of units/contracts.
            price: The limit or market price of the order.
            metadata: Optional dictionary containing additional order context.
            
        Raises:
            ValidationError: If the order_id already exists or inputs are invalid.
        """
        if side not in {"BUY", "SELL"}:
            raise ValidationError(f"Invalid order side: '{side}'. Must be BUY or SELL.")
            
        if quantity <= 0:
            raise ValidationError(f"Invalid quantity: {quantity}. Must be greater than zero.")
            
        if price < 0:
            raise ValidationError(f"Invalid price: {price}. Must be non-negative.")

        with self._lock:
            if order_id in self._orders:
                raise ValidationError(f"Order '{order_id}' already exists.")
                
            now = datetime.now()
            self._orders[order_id] = _OrderRecord(
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                status=OrderStatus.PENDING,
                created_time=now,
                updated_time=now,
                metadata=metadata or {}
            )
            
            self._logger.info(
                f"Created order {order_id} | {side} {quantity} {symbol} @ {price}"
            )

    def fill_order(self, order_id: str, fill_price: float, fill_time: Optional[datetime] = None) -> None:
        """
        Transitions a PENDING order to FILLED status.
        
        Args:
            order_id: The unique identifier of the order to fill.
            fill_price: The actual execution price.
            fill_time: Optional timestamp of the fill. Defaults to current time.
            
        Raises:
            ValidationError: If the order does not exist or is in a terminal state.
        """
        self._transition(order_id, OrderStatus.FILLED, fill_price=fill_price, fill_time=fill_time)
        self._logger.info(f"Order {order_id} FILLED @ {fill_price}")

    def cancel_order(self, order_id: str) -> None:
        """
        Transitions a PENDING order to CANCELLED status.
        
        Args:
            order_id: The unique identifier of the order to cancel.
            
        Raises:
            ValidationError: If the order does not exist or is in a terminal state.
        """
        self._transition(order_id, OrderStatus.CANCELLED)
        self._logger.info(f"Order {order_id} CANCELLED")

    def reject_order(self, order_id: str, reason: str) -> None:
        """
        Transitions a PENDING order to REJECTED status.
        
        Args:
            order_id: The unique identifier of the order to reject.
            reason: The reason for rejection.
            
        Raises:
            ValidationError: If the order does not exist or is in a terminal state.
        """
        self._transition(order_id, OrderStatus.REJECTED, rejection_reason=reason)
        self._logger.info(f"Order {order_id} REJECTED: {reason}")

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Retrieves the complete state of an order as a dictionary.
        
        Args:
            order_id: The unique identifier of the order.
            
        Returns:
            A dictionary containing all order fields.
            
        Raises:
            ValidationError: If the order does not exist.
        """
        with self._lock:
            record = self._orders.get(order_id)
            if record is None:
                raise ValidationError(f"Order '{order_id}' not found.")
                
            return {
                "order_id": record.order_id,
                "symbol": record.symbol,
                "side": record.side,
                "quantity": record.quantity,
                "price": record.price,
                "status": record.status.value,
                "created_time": record.created_time,
                "updated_time": record.updated_time,
                "metadata": dict(record.metadata)
            }

    def get_status(self, order_id: str) -> str:
        """
        Retrieves the current status of an order.
        
        Args:
            order_id: The unique identifier of the order.
            
        Returns:
            The order status as a string.
            
        Raises:
            ValidationError: If the order does not exist.
        """
        with self._lock:
            record = self._orders.get(order_id)
            if record is None:
                raise ValidationError(f"Order '{order_id}' not found.")
            return record.status.value

    def is_active(self, order_id: str) -> bool:
        """
        Checks if an order is still active (PENDING).
        
        Args:
            order_id: The unique identifier of the order.
            
        Returns:
            True if the order is PENDING, False otherwise.
            
        Raises:
            ValidationError: If the order does not exist.
        """
        with self._lock:
            record = self._orders.get(order_id)
            if record is None:
                raise ValidationError(f"Order '{order_id}' not found.")
            return record.status == OrderStatus.PENDING

    def reset(self) -> None:
        """Clears all orders and resets the manager to its initial state."""
        with self._lock:
            self._orders.clear()
            self._logger.info("Order manager state reset. All orders cleared.")

    def _transition(
        self,
        order_id: str,
        target_status: OrderStatus,
        fill_price: Optional[float] = None,
        fill_time: Optional[datetime] = None,
        rejection_reason: Optional[str] = None
    ) -> None:
        """
        Internal method to enforce state transition rules and update order state.
        
        Args:
            order_id: The unique identifier of the order.
            target_status: The desired target status.
            fill_price: Optional fill price for FILLED transitions.
            fill_time: Optional fill timestamp for FILLED transitions.
            rejection_reason: Optional reason for REJECTED transitions.
            
        Raises:
            ValidationError: If the order does not exist or is in a terminal state.
        """
        with self._lock:
            record = self._orders.get(order_id)
            if record is None:
                raise ValidationError(f"Order '{order_id}' not found.")
                
            if record.status in _TERMINAL_STATES:
                raise ValidationError(
                    f"Cannot transition order '{order_id}': already in terminal "
                    f"state '{record.status.value}'."
                )
                
            record.status = target_status
            record.updated_time = fill_time or datetime.now()
            
            if fill_price is not None:
                record.price = fill_price
                
            if rejection_reason is not None:
                record.metadata["rejection_reason"] = rejection_reason
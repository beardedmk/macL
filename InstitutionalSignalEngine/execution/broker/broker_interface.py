"""
Broker interface module for the Institutional Signal Intelligence Engine.

Defines the abstract contract for all broker adapters. The ExecutionEngine 
communicates strictly with this interface, ensuring complete decoupling 
from any specific broker's SDK, API, or implementation details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BrokerInterface(ABC):
    """
    Abstract base class defining the standard contract for broker integrations.
    
    All concrete broker adapters (e.g., PaytmMoneyAdapter, AngelOneAdapter) 
    must inherit from this interface and implement all abstract methods.
    This class contains no state, no business logic, and no implementation details.
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Authenticates with the broker and establishes a trading session.
        
        Raises:
            Exception: If authentication or connection fails.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Closes the active broker session and releases resources.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Checks the current connection status with the broker.
        
        Returns:
            True if the broker session is active and authenticated, False otherwise.
        """
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Places a new order with the broker.
        
        Args:
            symbol: The trading instrument symbol.
            side: The order side ("BUY" or "SELL").
            quantity: The number of units/contracts.
            order_type: The order type (e.g., "MARKET", "LIMIT", "SL", "SL-M").
            price: The limit price (required for LIMIT orders).
            trigger_price: The trigger price (required for SL/SL-M orders).
            metadata: Optional broker-specific parameters or tags.
            
        Returns:
            A dictionary containing the broker's response, including the 
            broker_order_id and status.
        """
        pass

    @abstractmethod
    def modify_order(
        self,
        broker_order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Modifies an existing pending order.
        
        Args:
            broker_order_id: The unique order ID assigned by the broker.
            quantity: The new quantity (if changing).
            price: The new limit price (if changing).
            trigger_price: The new trigger price (if changing).
            
        Returns:
            A dictionary containing the broker's modification response.
        """
        pass

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> Dict[str, Any]:
        """
        Cancels a pending order.
        
        Args:
            broker_order_id: The unique order ID assigned by the broker.
            
        Returns:
            A dictionary containing the broker's cancellation response.
        """
        pass

    @abstractmethod
    def get_order(self, broker_order_id: str) -> Dict[str, Any]:
        """
        Retrieves the details and current status of a specific order.
        
        Args:
            broker_order_id: The unique order ID assigned by the broker.
            
        Returns:
            A dictionary containing the order details.
        """
        pass

    @abstractmethod
    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Retrieves the complete order book for the current trading day.
        
        Returns:
            A list of dictionaries, each representing an order.
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieves all open positions (both equity and derivatives).
        
        Returns:
            A list of dictionaries, each representing a position.
        """
        pass

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Retrieves all long-term equity holdings in the demat account.
        
        Returns:
            A list of dictionaries, each representing a holding.
        """
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, Any]:
        """
        Retrieves the available funds and margin details for the account.
        
        Returns:
            A dictionary containing account balance and margin information.
        """
        pass

    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """
        Retrieves the user's profile and account details.
        
        Returns:
            A dictionary containing user profile information.
        """
        pass
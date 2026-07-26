"""
Market data interface module for the Institutional Signal Intelligence Engine.

Defines the abstract contract for market data providers. Strictly read-only;
live order execution is intentionally excluded from this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MarketDataInterface(ABC):
    """
    Abstract base class defining the standard contract for market data providers.
    All concrete adapters must implement these read-only and streaming methods.
    """

    @abstractmethod
    def connect(self) -> None:
        """Authenticates and establishes a session with the market data provider."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes the active session and releases resources."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the REST session is active and authenticated."""
        pass

    @abstractmethod
    def connect_websocket(self) -> None:
        """Establishes the WebSocket connection for live streaming."""
        pass

    @abstractmethod
    def disconnect_websocket(self) -> None:
        """Gracefully shuts down the WebSocket connection."""
        pass

    @abstractmethod
    def subscribe(self, scrip_id: int, exchange: str, scrip_type: str, mode: str) -> None:
        """Subscribes to live market data for a specific instrument."""
        pass

    @abstractmethod
    def unsubscribe(self, scrip_id: int, exchange: str, scrip_type: str, mode: str) -> None:
        """Unsubscribes from live market data for a specific instrument."""
        pass

    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """Retrieves user profile and account details."""
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, Any]:
        """Retrieves available funds and margin details."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Retrieves all open positions."""
        pass

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Retrieves all long-term equity holdings."""
        pass
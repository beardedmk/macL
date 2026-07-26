"""
Paytm Money market data adapter module for the Institutional Signal Intelligence Engine.

Orchestrates the PaytmRestClient and PaytmWebSocketClient to provide a unified,
clean facade implementing the MarketDataInterface.
"""

from typing import Any, Callable, Dict, List, Optional

from auth.authentication import AuthenticationManager
from core.logger import LoggerFactory
from execution.market_data.market_data_interface import MarketDataInterface
from execution.market_data.packet_decoder import PacketDecoder
from execution.market_data.paytm_rest_client import PaytmRestClient
from execution.market_data.paytm_websocket_client import PaytmWebSocketClient
from execution.market_data.subscription_manager import SubscriptionManager


class PaytmMarketDataAdapter(MarketDataInterface):
    """
    Unified facade for Paytm Money market data access.
    Orchestrates REST and WebSocket clients while hiding their complexity.
    """

    def __init__(
        self, 
        auth_manager: AuthenticationManager,
        on_packet_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        self._logger = LoggerFactory().get_logger(__name__)
        
        self._auth_manager = auth_manager
        self._sub_manager = SubscriptionManager()
        self._decoder = PacketDecoder()
        
        self._rest_client = PaytmRestClient(auth_manager)
        self._ws_client = PaytmWebSocketClient(
            auth_manager=auth_manager,
            subscription_manager=self._sub_manager,
            packet_decoder=self._decoder,
            on_packet_callback=on_packet_callback or (lambda x: None)
        )

    def connect(self) -> None:
        """Authenticates and verifies REST session."""
        if not self._auth_manager.is_authenticated():
            self._logger.info("Not authenticated. Attempting login...")
            self._auth_manager.login()
            
        if self._rest_client.verify_connection():
            self._logger.info("Successfully connected to Paytm Money REST API.")
        else:
            raise RuntimeError("Failed to verify Paytm Money REST connection.")

    def disconnect(self) -> None:
        """Closes REST session and WebSocket."""
        self.disconnect_websocket()
        self._rest_client.close()
        self._sub_manager.clear()
        self._logger.info("Paytm Market Data Adapter fully disconnected.")

    def is_connected(self) -> bool:
        """Returns True if the REST session is active."""
        return self._auth_manager.is_authenticated()

    def connect_websocket(self) -> None:
        """Starts the WebSocket streaming client."""
        self._ws_client.start()

    def disconnect_websocket(self) -> None:
        """Stops the WebSocket streaming client."""
        self._ws_client.stop()

    def subscribe(self, scrip_id: int, exchange: str, scrip_type: str, mode: str) -> None:
        """Subscribes to live market data for a specific instrument."""
        self._ws_client.subscribe(scrip_id, exchange, scrip_type, mode)

    def unsubscribe(self, scrip_id: int, exchange: str, scrip_type: str) -> None:
        """Unsubscribes from live market data for a specific instrument."""
        self._ws_client.unsubscribe(scrip_id, exchange, scrip_type)

    def get_profile(self) -> Dict[str, Any]:
        return self._rest_client.get_profile()

    def get_account_balance(self) -> Dict[str, Any]:
        return self._rest_client.get_account_balance()

    def get_positions(self) -> List[Dict[str, Any]]:
        return self._rest_client.get_positions()

    def get_holdings(self) -> List[Dict[str, Any]]:
        return self._rest_client.get_holdings()
"""
Paytm Money WebSocket client module for the Institutional Signal Intelligence Engine.

Handles live market data streaming, automatic reconnection with exponential 
backoff, and automatic resubscription via the SubscriptionManager.
"""

import json
import threading
import time
from typing import Any, Callable, Optional

import websocket

from auth.authentication import AuthenticationManager
from core.exceptions import EngineError
from core.logger import LoggerFactory
from execution.market_data.packet_decoder import PacketDecoder
from execution.market_data.subscription_manager import SubscriptionManager


class PaytmWebSocketClient:
    """
    Thread-safe WebSocket client for Paytm Money market data streaming.
    Features automatic reconnection and resubscription.
    """

    def __init__(
        self,
        auth_manager: AuthenticationManager,
        subscription_manager: SubscriptionManager,
        packet_decoder: PacketDecoder,
        on_packet_callback: Callable[[Any], None]
    ) -> None:
        self._logger = LoggerFactory().get_logger(__name__)
        self._auth_manager = auth_manager
        self._sub_manager = subscription_manager
        self._decoder = packet_decoder
        self._on_packet_callback = on_packet_callback
        
        self._lock = threading.Lock()
        self._is_running = False
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        
        self._ws_url = "wss://developer-ws.paytmmoney.com/broadcast/user/v1/data"
        self._base_reconnect_delay = 2.0
        self._max_reconnect_delay = 60.0

    def start(self) -> None:
        """Starts the WebSocket connection in a background daemon thread."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            
        self._logger.info("Starting Paytm WebSocket background thread...")
        self._ws_thread = threading.Thread(target=self._run_forever, daemon=True)
        self._ws_thread.start()

    def stop(self) -> None:
        """Stops the WebSocket connection and terminates the background thread."""
        self._logger.info("Stopping Paytm WebSocket client...")
        with self._lock:
            self._is_running = False
            
        if self._ws:
            self._ws.close()
            
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=3.0)
            
        self._logger.info("Paytm WebSocket client stopped.")

    def subscribe(self, scrip_id: int, exchange: str, scrip_type: str, mode: str) -> None:
        """Registers the subscription and sends the ADD payload."""
        self._sub_manager.add_subscription(scrip_id, exchange, scrip_type, mode)
        self._send_subscription_action("ADD", scrip_id, exchange, scrip_type, mode)

    def unsubscribe(self, scrip_id: int, exchange: str, scrip_type: str) -> None:
        """Removes the subscription and sends the REMOVE payload."""
        self._sub_manager.remove_subscription(scrip_id, exchange, scrip_type)
        # Mode is not strictly required for removal, defaulting to FULL
        self._send_subscription_action("REMOVE", scrip_id, exchange, scrip_type, "FULL")

    def _send_subscription_action(self, action: str, scrip_id: int, exchange: str, scrip_type: str, mode: str) -> None:
        with self._lock:
            if not self._is_running or not self._ws:
                self._logger.warning(f"Cannot {action.lower()} {scrip_id}: WebSocket not running.")
                return
                
        payload = [{
            "actionType": action,
            "modeType": mode,
            "exchangeType": exchange,
            "scripType": scrip_type,
            "scripId": str(scrip_id)
        }]
        try:
            self._ws.send(json.dumps(payload))
        except Exception as e:
            self._logger.error(f"Failed to send {action} payload for {scrip_id}: {e}")

    def _run_forever(self) -> None:
        """Internal loop managing connection and exponential backoff reconnection."""
        reconnect_delay = self._base_reconnect_delay
        
        while self._is_running:
            try:
                self._connect()
                # If connected successfully, reset delay
                reconnect_delay = self._base_reconnect_delay
                
                # Block until connection drops
                while self._is_running and self._ws and self._ws.keep_running:
                    time.sleep(1)
                    
            except Exception as e:
                self._logger.error(f"WebSocket connection failed: {e}")
                
            if self._is_running:
                self._logger.info(f"Reconnecting in {reconnect_delay} seconds...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, self._max_reconnect_delay)

    def _connect(self) -> None:
        """Establishes the WebSocket connection and resubscribes."""
        token = self._auth_manager.get_access_token()
        if not token:
            # Attempt to refresh token if expired
            try:
                self._auth_manager.refresh_token()
                token = self._auth_manager.get_access_token()
            except Exception as e:
                raise EngineError(f"Failed to obtain token for WebSocket: {e}")

        ws_url = f"{self._ws_url}?x_jwt_token={token}"
        
        self._ws = websocket.WebSocketApp(
            ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self._ws.run_forever(ping_interval=25, ping_timeout=10)

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        self._logger.info("Paytm WebSocket connected successfully.")
        # Auto-resubscribe
        payloads = self._sub_manager.get_resubscribe_payloads()
        for payload in payloads:
            try:
                ws.send(json.dumps([payload]))
            except Exception as e:
                self._logger.error(f"Failed to resubscribe during reconnect: {e}")
        self._logger.info(f"Restored {len(payloads)} subscriptions.")

    def _on_message(self, ws: websocket.WebSocketApp, message: bytes) -> None:
        if not isinstance(message, bytes):
            return
        
        packets = self._decoder.decode(message)
        for packet in packets:
            try:
                self._on_packet_callback(packet)
            except Exception as e:
                self._logger.error(f"Error in packet callback: {e}")

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        self._logger.error(f"Paytm WebSocket error: {error}")

    def _on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        self._logger.warning(f"Paytm WebSocket closed. Code: {close_status_code}, Message: {close_msg}")
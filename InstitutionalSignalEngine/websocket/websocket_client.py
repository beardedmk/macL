"""
WebSocket client module for the Institutional Signal Intelligence Engine.

Manages the live WebSocket connection to the market data provider, handling
authentication, automatic reconnection, and packet decoding. Strictly 
isolated from feature calculation, storage, and strategy logic.
"""

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import websocket

from auth.authentication import AuthenticationManager
from config import config
from core.exceptions import ConnectionLostError, WebSocketError
from core.logger import LoggerFactory
from websocket.packet_decoder import PacketDecoder


class WebSocketClient:
    """
    Thread-safe WebSocket client for streaming live market data.
    Handles connection lifecycle, automatic reconnection, and dispatches
    decoded market packets to a user-provided callback.
    """

    def __init__(
        self,
        auth_manager: AuthenticationManager,
        packet_decoder: PacketDecoder,
        on_packet_callback: Callable[[Any], None]
    ) -> None:
        """
        Initializes the WebSocket client with required dependencies.
        
        Args:
            auth_manager: Handles authentication and token retrieval.
            packet_decoder: Decodes raw JSON packets into domain models.
            on_packet_callback: User-provided function to receive decoded packets.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._auth_manager = auth_manager
        self._decoder = packet_decoder
        self._on_packet_callback = on_packet_callback

        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        
        self._lock = threading.Lock()
        self._is_running = False
        self._is_connected = False
        self._reconnect_attempts = 0
        
        self._url = config.websocket.url
        self._reconnect_interval = config.websocket.reconnect_interval_sec
        self._max_reconnect_attempts = config.websocket.max_reconnect_attempts
        self._ping_interval = config.websocket.ping_interval_sec

    def start(self) -> None:
        """Starts the WebSocket connection in a background daemon thread."""
        with self._lock:
            if self._is_running:
                self._logger.warning("WebSocket client is already running.")
                return
            self._is_running = True
            
        self._logger.info("Starting WebSocket client background thread...")
        self._ws_thread = threading.Thread(target=self._run_forever, daemon=True)
        self._ws_thread.start()

    def stop(self) -> None:
        """Stops the WebSocket connection and terminates the background thread."""
        self._logger.info("Stopping WebSocket client...")
        with self._lock:
            self._is_running = False
            
        self.disconnect()
        
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=5.0)
            
        self._logger.info("WebSocket client stopped.")

    def connect(self) -> None:
        """
        Establishes the WebSocket connection.
        Ensures authentication is valid before attempting to connect.
        
        Raises:
            WebSocketError: If connection setup fails.
        """
        if not self._auth_manager.is_authenticated():
            self._logger.info("Not authenticated. Attempting login before connect...")
            try:
                self._auth_manager.login()
            except Exception as e:
                raise WebSocketError(f"Authentication failed prior to connect: {e}") from e

        token = self._auth_manager.get_access_token()
        if not token:
            raise WebSocketError("Cannot connect: No valid access token available.")

        # Construct URL with token (generic approach, adaptable to specific broker query params)
        connect_url = f"{self._url}?access_token={token}"
        
        self._logger.info(f"Connecting to WebSocket: {self._url}")
        
        try:
            self._ws = websocket.WebSocketApp(
                connect_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # run_forever blocks, so it should be called within the background thread
            self._ws.run_forever(
                ping_interval=self._ping_interval,
                ping_timeout=10
            )
        except Exception as e:
            raise WebSocketError(f"Failed to establish WebSocket connection: {e}") from e

    def disconnect(self) -> None:
        """Closes the active WebSocket connection."""
        with self._lock:
            self._is_connected = False
            
        if self._ws:
            self._logger.info("Closing WebSocket connection...")
            self._ws.close()
            self._ws = None

    def reconnect(self) -> None:
        """
        Attempts to reconnect to the WebSocket using configured intervals.
        
        Raises:
            ConnectionLostError: If maximum reconnection attempts are exceeded.
        """
        self.disconnect()
        
        while self._is_running and self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            self._logger.info(
                f"Reconnection attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} "
                f"in {self._reconnect_interval} seconds..."
            )
            time.sleep(self._reconnect_interval)
            
            try:
                self.connect()
                # If connect succeeds and doesn't immediately throw, reset attempts
                self._reconnect_attempts = 0
                return
            except WebSocketError as e:
                self._logger.error(f"Reconnection attempt failed: {e}")
                
        self._logger.critical("Maximum reconnection attempts reached. Giving up.")
        self._is_running = False
        raise ConnectionLostError("Failed to reconnect after maximum attempts.")

    def subscribe(self, instruments: List[str]) -> None:
        """
        Subscribes to a list of instrument tokens/symbols.
        
        Args:
            instruments: List of instrument identifiers to subscribe to.
        """
        message = {"action": "subscribe", "instruments": instruments}
        self.send(json.dumps(message))
        self._logger.info(f"Subscribed to {len(instruments)} instruments.")

    def unsubscribe(self, instruments: List[str]) -> None:
        """
        Unsubscribes from a list of instrument tokens/symbols.
        
        Args:
            instruments: List of instrument identifiers to unsubscribe from.
        """
        message = {"action": "unsubscribe", "instruments": instruments}
        self.send(json.dumps(message))
        self._logger.info(f"Unsubscribed from {len(instruments)} instruments.")

    def send(self, message: str) -> None:
        """
        Sends a raw string message over the WebSocket connection.
        
        Args:
            message: The string payload to send.
            
        Raises:
            WebSocketError: If the connection is not active or sending fails.
        """
        if not self.is_connected():
            raise WebSocketError("Cannot send message: WebSocket is not connected.")
            
        try:
            if self._ws:
                self._ws.send(message)
        except Exception as e:
            raise WebSocketError(f"Failed to send message: {e}") from e

    def is_connected(self) -> bool:
        """
        Checks if the WebSocket is currently connected.
        
        Returns:
            True if connected, False otherwise.
        """
        with self._lock:
            return self._is_connected

    def _run_forever(self) -> None:
        """Internal loop to manage connection and automatic reconnection."""
        while self._is_running:
            try:
                self.connect()
            except WebSocketError as e:
                self._logger.error(f"Connection lost or failed: {e}")
                
            if self._is_running:
                try:
                    self.reconnect()
                except ConnectionLostError:
                    self._logger.critical("Reconnection failed. Stopping client.")
                    self._is_running = False
                    break

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        """Callback executed when the WebSocket connection is successfully opened."""
        with self._lock:
            self._is_connected = True
            self._reconnect_attempts = 0
        self._logger.info("WebSocket connection opened successfully.")

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """
        Callback executed when a message is received. Decodes the packet
        and passes it to the user-provided callback.
        """
        try:
            data = json.loads(message)
            
            # Route to appropriate decoder based on payload structure
            if "options" in data and isinstance(data["options"], list):
                decoded_packet = self._decoder.decode_option_chain(data)
            else:
                decoded_packet = self._decoder.decode_tick(data)
                
            self._on_packet_callback(decoded_packet)
            
        except json.JSONDecodeError:
            self._logger.warning("Received non-JSON message from WebSocket.")
        except Exception as e:
            self._logger.error(f"Failed to process incoming message: {e}")

    def on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """Callback executed when a WebSocket error occurs."""
        self._logger.error(f"WebSocket error: {error}")
        with self._lock:
            self._is_connected = False

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """Callback executed when the WebSocket connection is closed."""
        with self._lock:
            self._is_connected = False
        self._logger.warning(
            f"WebSocket connection closed. Code: {close_status_code}, Message: {close_msg}"
        )
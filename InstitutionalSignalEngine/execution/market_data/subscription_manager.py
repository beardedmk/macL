"""
Subscription manager module for the Institutional Signal Intelligence Engine.

Tracks active market data subscriptions to enable automatic resubscription 
upon WebSocket reconnection. Thread-safe and stateful.
"""

import threading
from typing import Any, Dict, List


class SubscriptionManager:
    """
    Thread-safe manager for tracking active market data subscriptions.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscriptions: Dict[str, Dict[str, Any]] = {}

    def add_subscription(self, scrip_id: int, exchange: str, scrip_type: str, mode: str) -> None:
        """Registers a new subscription."""
        key = f"{exchange}:{scrip_type}:{scrip_id}"
        with self._lock:
            self._subscriptions[key] = {
                "scrip_id": scrip_id,
                "exchange": exchange,
                "scrip_type": scrip_type,
                "mode": mode
            }

    def remove_subscription(self, scrip_id: int, exchange: str, scrip_type: str) -> None:
        """Removes an existing subscription."""
        key = f"{exchange}:{scrip_type}:{scrip_id}"
        with self._lock:
            self._subscriptions.pop(key, None)

    def get_resubscribe_payloads(self) -> List[Dict[str, Any]]:
        """
        Generates the list of subscription payloads required to restore 
        all active subscriptions after a reconnect.
        """
        with self._lock:
            return [
                {
                    "actionType": "ADD",
                    "modeType": sub["mode"],
                    "exchangeType": sub["exchange"],
                    "scripType": sub["scrip_type"],
                    "scripId": str(sub["scrip_id"])
                }
                for sub in self._subscriptions.values()
            ]

    def clear(self) -> None:
        """Clears all tracked subscriptions."""
        with self._lock:
            self._subscriptions.clear()
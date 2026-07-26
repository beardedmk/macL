"""
Paytm Money REST client module for the Institutional Signal Intelligence Engine.

Handles all read-only REST API communication with the Paytm Money Open API.
Uses a persistent requests.Session for connection pooling and efficiency.
"""

import threading
from typing import Any, Dict, List, Optional

import requests

from auth.authentication import AuthenticationManager
from core.exceptions import EngineError
from core.logger import LoggerFactory


class PaytmRestClient:
    """
    Thread-safe client for read-only Paytm Money REST API endpoints.
    """

    def __init__(self, auth_manager: AuthenticationManager) -> None:
        self._logger = LoggerFactory().get_logger(__name__)
        self._auth_manager = auth_manager
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._base_url = "https://developer.paytmmoney.com"

    def _get_headers(self) -> Dict[str, str]:
        token = self._auth_manager.get_access_token()
        if not token:
            raise EngineError("No valid access token available. Please authenticate first.")
        return {"x-jwt-token": token, "Content-Type": "application/json"}

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self._base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method == "GET":
                response = self._session.get(url, headers=headers, params=params, timeout=10)
            else:
                response = self._session.post(url, headers=headers, json=json_data, timeout=10)
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.text if e.response is not None else str(e)
            self._logger.error(f"HTTP Error from Paytm Money REST: {error_msg}")
            raise EngineError(f"Paytm Money REST HTTP Error: {error_msg}") from e
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Network error communicating with Paytm Money REST: {e}")
            raise EngineError(f"Paytm Money REST Network Error: {e}") from e

    def verify_connection(self) -> bool:
        """Verifies authentication by fetching the user profile."""
        try:
            self.get_profile()
            return True
        except EngineError:
            return False

    def get_profile(self) -> Dict[str, Any]:
        response = self._make_request("GET", "/accounts/v1/user/details")
        data = response.get("data", {})
        return {
            "user_id": data.get("user_id", "UNKNOWN"),
            "email": data.get("email", "UNKNOWN"),
            "name": data.get("name", "UNKNOWN"),
            "broker": "Paytm Money"
        }

    def get_account_balance(self) -> Dict[str, Any]:
        response = self._make_request("GET", "/accounts/v1/user/balance")
        data = response.get("data", {})
        return {
            "available_cash": data.get("available_cash", 0.0),
            "available_margin": data.get("available_margin", 0.0),
            "utilized_margin": data.get("utilized_margin", 0.0)
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        response = self._make_request("GET", "/portfolio/v1/positions")
        data = response.get("data", [])
        return [{
            "symbol": pos.get("tradingsymbol", "UNKNOWN"),
            "product": pos.get("product", "UNKNOWN"),
            "quantity": pos.get("quantity", 0),
            "unrealized_pnl": pos.get("unrealized_profit", 0.0),
            "realized_pnl": pos.get("realized_profit", 0.0)
        } for pos in data]

    def get_holdings(self) -> List[Dict[str, Any]]:
        response = self._make_request("GET", "/portfolio/v1/holdings")
        data = response.get("data", [])
        return [{
            "symbol": holding.get("tradingsymbol", "UNKNOWN"),
            "quantity": holding.get("quantity", 0),
            "average_price": holding.get("average_price", 0.0),
            "current_price": holding.get("current_price", 0.0),
            "unrealized_pnl": holding.get("unrealized_profit", 0.0)
        } for holding in data]

    def close(self) -> None:
        """Closes the persistent HTTP session."""
        with self._lock:
            self._session.close()
            self._logger.info("Paytm REST client session closed.")
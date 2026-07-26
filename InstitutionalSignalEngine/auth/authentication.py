"""
Authentication module for the Institutional Signal Intelligence Engine.

Handles secure authentication, token management, and session lifecycle
with the market data provider. All operations are thread-safe and 
strictly rely on application configuration.
"""

import threading
from typing import Optional

import requests

from config import config
from core.exceptions import AuthenticationError
from core.logger import LoggerFactory


class AuthenticationManager:
    """
    Manages authentication state, token retrieval, and token refresh
    cycles with the market data provider in a thread-safe manner.
    """

    def __init__(self) -> None:
        """
        Initializes the authentication manager with configuration parameters
        and sets up thread-safe locking for token management.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._access_token: Optional[str] = config.auth.access_token or None
        self._refresh_url: str = config.auth.token_refresh_url
        self._api_key: str = config.auth.api_key
        self._api_secret: str = config.auth.api_secret

    def login(self) -> None:
        """
        Authenticates with the market data provider using configured 
        credentials and retrieves the initial access token.
        
        Raises:
            AuthenticationError: If the login request fails or returns no token.
        """
        self._logger.info("Initiating authentication login...")
        try:
            payload = {
                "api_key": self._api_key,
                "api_secret": self._api_secret,
                "grant_type": "client_credentials"
            }
            
            response = requests.post(self._refresh_url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            token = data.get("access_token")
            
            if not token:
                raise AuthenticationError("Login response did not contain an access token.")
                
            with self._lock:
                self._access_token = token
                
            self._logger.info("Authentication login successful.")
            
        except requests.RequestException as e:
            self._logger.error(f"Login request failed: {e}")
            raise AuthenticationError(f"Failed to authenticate: {e}") from e
        except Exception as e:
            self._logger.error(f"Unexpected error during login: {e}")
            raise AuthenticationError(f"Unexpected login error: {e}") from e

    def refresh_token(self) -> None:
        """
        Refreshes the current access token using the configured refresh endpoint.
        
        Raises:
            AuthenticationError: If the refresh request fails or returns no token.
        """
        self._logger.info("Initiating token refresh...")
        try:
            current_token = self.get_access_token()
            payload = {
                "api_key": self._api_key,
                "api_secret": self._api_secret,
                "refresh_token": current_token,
                "grant_type": "refresh_token"
            }
            
            response = requests.post(self._refresh_url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            token = data.get("access_token")
            
            if not token:
                raise AuthenticationError("Refresh response did not contain an access token.")
                
            with self._lock:
                self._access_token = token
                
            self._logger.info("Token refresh successful.")
            
        except requests.RequestException as e:
            self._logger.error(f"Token refresh request failed: {e}")
            raise AuthenticationError(f"Failed to refresh token: {e}") from e
        except Exception as e:
            self._logger.error(f"Unexpected error during token refresh: {e}")
            raise AuthenticationError(f"Unexpected refresh error: {e}") from e

    def logout(self) -> None:
        """
        Clears the current access token and terminates the authenticated session.
        """
        with self._lock:
            self._access_token = None
        self._logger.info("User logged out and token cleared.")

    def is_authenticated(self) -> bool:
        """
        Checks if the manager currently holds a valid access token.
        
        Returns:
            True if an access token is present, False otherwise.
        """
        with self._lock:
            return bool(self._access_token)

    def get_access_token(self) -> Optional[str]:
        """
        Retrieves the current access token in a thread-safe manner.
        
        Returns:
            The current access token string, or None if not authenticated.
        """
        with self._lock:
            return self._access_token
"""
Authentication manager module for the Institutional Signal Intelligence Engine.

Handles the Paytm Money OAuth 2.0 flow, JWT generation, token persistence,
and validation. Strictly isolated from market data and execution logic.
"""

import base64
import json
import os
import secrets
import threading
import time
import webbrowser
from typing import Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import Flask, request

from core.exceptions import EngineError
from core.logger import LoggerFactory

# Load environment variables at module level
load_dotenv()


class AuthenticationManager:
    """
    Manages the Paytm Money authentication lifecycle, including OAuth login,
    JWT generation, and token persistence. Thread-safe and dependency-injection ready.
    """

    def __init__(self) -> None:
        self._logger = LoggerFactory().get_logger(__name__)
        self._lock = threading.Lock()
        
        self._api_key = os.getenv("API_KEY")
        self._api_secret = os.getenv("API_SECRET")
        self._redirect_uri = os.getenv("REDIRECT_URI", "http://127.0.0.1:5000/callback")
        
        if not self._api_key or not self._api_secret:
            raise EngineError("API_KEY and API_SECRET must be set in environment variables.")

        self._login_url = "https://login.paytmmoney.com/merchant-login"
        self._token_url = "https://developer.paytmmoney.com/accounts/v2/gettoken"
        self._user_details_url = "https://developer.paytmmoney.com/accounts/v1/user/details"
        self._token_file = "token.json"
        self._state = secrets.token_hex(16)
        
        self._access_token: Optional[str] = None
        self._public_access_token: Optional[str] = None
        self._read_access_token: Optional[str] = None
        
        self._login_event = threading.Event()
        self._flask_app = Flask(__name__)
        self._setup_flask_routes()

    def _setup_flask_routes(self) -> None:
        @self._flask_app.route("/callback")
        def callback() -> str:
            state = request.args.get("state")
            req_token = request.args.get("requestToken") or request.args.get("request_token")
            
            if state != self._state:
                self._logger.error("Invalid state parameter in callback.")
                return "Invalid state."
            if not req_token:
                self._logger.error("Request token missing in callback.")
                return "Request Token Missing."
                
            try:
                self._generate_jwt(req_token)
            except Exception as e:
                self._logger.error(f"Failed to generate JWT: {e}")
                return str(e)
                
            self._login_event.set()
            return "<h2>Login Successful</h2><h3>You may close this window and return to the terminal.</h3>"

    def _jwt_expiry(self, token: str) -> int:
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(payload))["exp"]
        except Exception as e:
            self._logger.error(f"Failed to decode JWT expiry: {e}")
            return 0

    def _save_tokens(self, data: dict) -> None:
        with open(self._token_file, "w") as f:
            json.dump({
                "access_token": data["access_token"],
                "public_access_token": data["public_access_token"],
                "read_access_token": data["read_access_token"],
            }, f, indent=4)
        self._logger.info("Tokens saved successfully to disk.")

    def _load_tokens(self) -> bool:
        if not os.path.exists(self._token_file):
            return False
            
        try:
            with open(self._token_file, "r") as f:
                data = json.load(f)
                
            if self._jwt_expiry(data["access_token"]) <= time.time():
                self._logger.info("Saved tokens have expired.")
                return False
                
            # Verify token with a lightweight API call
            headers = {"x-jwt-token": data["access_token"]}
            response = requests.get(self._user_details_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                self._logger.info("Saved tokens are invalid.")
                return False
                
            with self._lock:
                self._access_token = data["access_token"]
                self._public_access_token = data["public_access_token"]
                self._read_access_token = data["read_access_token"]
                
            self._logger.info("Successfully loaded and validated saved tokens.")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to load tokens: {e}")
            return False

    def _generate_jwt(self, request_token: str) -> None:
        payload = {
            "api_key": self._api_key,
            "api_secret_key": self._api_secret,
            "request_token": request_token
        }
        
        response = requests.post(self._token_url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        with self._lock:
            self._access_token = data["access_token"]
            self._public_access_token = data["public_access_token"]
            self._read_access_token = data["read_access_token"]
            
        self._save_tokens(data)
        self._logger.info("Successfully generated and saved new JWT tokens.")

    def login(self) -> None:
        """
        Initiates the OAuth login flow. If valid saved tokens exist, 
        it skips the browser login and uses them directly.
        """
        if self._load_tokens():
            return

        self._logger.info("No valid saved tokens found. Initiating browser login...")
        
        # Start Flask server in a background daemon thread
        server_thread = threading.Thread(
            target=lambda: self._flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False),
            daemon=True
        )
        server_thread.start()
        
        # Open browser
        params = {"apiKey": self._api_key, "state": self._state}
        url = f"{self._login_url}?{urlencode(params)}"
        self._logger.info(f"Opening login page in browser: {url}")
        webbrowser.open(url)
        
        # Wait for the callback to set the event
        self._logger.info("Waiting for authentication callback...")
        self._login_event.wait()
        self._logger.info("Authentication completed successfully.")

    def is_authenticated(self) -> bool:
        """Checks if a valid access token is currently loaded."""
        with self._lock:
            if not self._access_token:
                return False
            return self._jwt_expiry(self._access_token) > time.time()

    def get_access_token(self) -> Optional[str]:
        """Returns the current access token."""
        with self._lock:
            return self._access_token

    def get_public_access_token(self) -> Optional[str]:
        """Returns the current public access token (used for WebSocket)."""
        with self._lock:
            return self._public_access_token

    def get_read_access_token(self) -> Optional[str]:
        """Returns the current read access token."""
        with self._lock:
            return self._read_access_token
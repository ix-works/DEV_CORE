#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWT Authentication Provider for SAP BTP Cloud

Handles JWT token-based authentication for SAP Business Technology Platform.
Supports XSUAA (Extended SAP User Account and Authentication) OAuth2 flow.
"""
import json
import time
from typing import Dict, Optional
from auth.i_auth_provider import IAuthProvider


class JWTAuthProvider(IAuthProvider):
    """
    JWT Authentication provider for SAP BTP/Cloud systems.

    Uses OAuth2 JWT tokens for authentication.
    Automatically refreshes tokens when they expire.
    """

    # Default token expiry buffer (refresh before actual expiry)
    TOKEN_EXPIRY_BUFFER = 60  # seconds

    def __init__(self, token_url: str, client_id: str, client_secret: str,
                 uaa_url: str = None, token: str = None):
        """
        Initialize JWT Auth provider.

        Args:
            token_url: OAuth2 token endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            uaa_url: UAA server URL (optional, for token validation)
            token: Existing JWT token (optional, for re-use)
        """
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._uaa_url = uaa_url
        self._access_token = token
        self._refresh_token = None
        self._expires_at = None
        self._token_type = 'Bearer'

        if token:
            # Parse token to get expiry (if available)
            self._parse_token_expiry(token)

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get JWT authentication headers.

        Returns:
            Dict with Authorization header (Bearer token)
        """
        if not self._access_token or not self.is_valid():
            self.refresh_credentials()

        return {
            'Authorization': f'{self._token_type} {self._access_token}'
        }

    def refresh_credentials(self) -> None:
        """
        Fetch new JWT token via OAuth2 client credentials flow.

        Raises:
            SAPConnectionError: If token fetch fails
        """
        from sap_adt_lib import SAPConnectionError
        import requests
        from urllib3.exceptions import InsecureRequestWarning
        import os

        # Suppress SSL warnings
        if os.getenv('ADT_SAP_SSL_VERIFY', 'false').lower() not in ('true', '1', 'yes'):
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

        # Prepare OAuth2 request
        data = {
            'grant_type': 'client_credentials',
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'response_type': 'token'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self._token_url,
                data=data,
                headers=headers,
                verify=False,
                timeout=30
            )

            if response.status_code != 200:
                raise SAPConnectionError(
                    f"JWT token fetch failed: HTTP {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text
                )

            token_data = response.json()

            self._access_token = token_data.get('access_token')
            self._refresh_token = token_data.get('refresh_token')
            self._token_type = token_data.get('token_type', 'Bearer')

            # Calculate expiry
            expires_in = token_data.get('expires_in', 3600)
            self._expires_at = time.time() + expires_in - self.TOKEN_EXPIRY_BUFFER

        except Exception as e:
            if isinstance(e, SAPConnectionError):
                raise
            raise SAPConnectionError(f"JWT token refresh failed: {e}")

    def is_valid(self) -> bool:
        """
        Check if current token is valid.

        Returns:
            True if token exists and hasn't expired
        """
        if not self._access_token:
            return False

        if self._expires_at is None:
            return True  # Can't determine expiry, assume valid

        return time.time() < self._expires_at

    @property
    def auth_type(self) -> str:
        """Return auth type identifier."""
        return 'jwt'

    def _parse_token_expiry(self, token: str) -> None:
        """
        Parse JWT token to extract expiry time.

        Args:
            token: JWT token string
        """
        try:
            # JWT is base64 encoded, split by '.'
            parts = token.split('.')
            if len(parts) >= 2:
                # Decode payload (middle part)
                import base64
                payload = parts[1]
                # Add padding if needed
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                payload_data = json.loads(decoded)

                # Get expiry
                exp = payload_data.get('exp')
                if exp:
                    self._expires_at = exp - self.TOKEN_EXPIRY_BUFFER
        except Exception:
            # Can't parse, will refresh when needed
            pass

    @property
    def access_token(self) -> str:
        """Get current access token."""
        return self._access_token

    @property
    def expires_at(self) -> Optional[int]:
        """Get token expiry timestamp."""
        return self._expires_at


class XSUAAAuthProvider(JWTAuthProvider):
    """
    XSUAA-specific authentication for SAP BTP.

    Extends JWTAuthProvider with XSUAA-specific features like
    subdomain handling and token exchange.
    """

    def __init__(self, subdomain: str, client_id: str, client_secret: str,
                 token_url: str = None, uaa_url: str = None):
        """
        Initialize XSUAA Auth provider.

        Args:
            subdomain: BTP subdomain (e.g., 'abc123-trial')
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            token_url: OAuth2 token endpoint (auto-constructed if not provided)
            uaa_url: UAA server URL (auto-constructed if not provided)
        """
        if not token_url:
            # Construct default XSUAA token URL
            token_url = f"https://{subdomain}.authentication.{self._get_landscape_domain()}/oauth/token"

        if not uaa_url:
            uaa_url = f"https://{subdomain}.authentication.{self._get_landscape_domain()}"

        super().__init__(token_url, client_id, client_secret, uaa_url)
        self._subdomain = subdomain

    def _get_landscape_domain(self) -> str:
        """
        Get BTP landscape domain from subdomain.

        Args:
            subdomain: BTP subdomain

        Returns:
            Landscape domain (e.g., 'eu10.hana.ondemand.com')
        """
        # Extract landscape from subdomain if possible
        if '.authentication.' in self._subdomain:
            # Already has full domain
            return self._subdomain.split('.authentication.')[1]
        # Default to EU10 landscape
        return 'eu10.hana.ondemand.com'

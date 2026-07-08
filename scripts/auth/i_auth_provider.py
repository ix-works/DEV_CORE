#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IAuthProvider Interface

Interface for SAP ADT authentication providers.
All authentication implementations must follow this contract.

Based on mcp-abap-adt reference implementation.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class IAuthProvider(ABC):
    """
    Interface for SAP ADT authentication providers.

    Implementations provide different authentication methods:
    - BasicAuth: Username/password (on-prem SAP)
    - JWTAuth: JWT tokens (SAP BTP/Cloud)
    - ServiceKeyAuth: Service key credentials (SAP BTP/Cloud)
    """

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for HTTP requests.

        Returns:
            Dict with authentication headers (e.g., Authorization header)
        """
        pass

    @abstractmethod
    def refresh_credentials(self) -> None:
        """
        Refresh authentication credentials.

        For BasicAuth: no-op (credentials don't expire)
        For JWTAuth: fetch new JWT token
        For ServiceKeyAuth: fetch new token via client credentials
        """
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        """
        Check if current credentials are valid.

        Returns:
            True if credentials are valid and can be used
        """
        pass

    @property
    @abstractmethod
    def auth_type(self) -> str:
        """
        Get authentication type identifier.

        Returns:
            One of: 'basic', 'jwt', 'service_key'
        """
        pass

    def get_csrf_token(self, session, url: str, headers: Dict[str, str]) -> str:
        """
        Get CSRF token for POST/PUT/DELETE operations.

        Default implementation handles standard SAP CSRF flow.
        Override if custom flow needed.

        Args:
            session: requests.Session object
            url: URL for CSRF token fetch
            headers: Base headers to use

        Returns:
            CSRF token string

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

        csrf_headers = headers.copy()
        csrf_headers.update(self.get_auth_headers())
        csrf_headers['x-csrf-token'] = 'Fetch'

        try:
            response = session.get(url, headers=csrf_headers, verify=False, timeout=30)
            csrf_token = response.headers.get('x-csrf-token')
            if not csrf_token:
                raise SAPConnectionError("No x-csrf-token in response")
            return csrf_token
        except Exception as e:
            raise SAPConnectionError(f"CSRF token fetch failed: {e}")

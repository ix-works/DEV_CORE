#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Key Authentication Provider for SAP BTP Cloud

Handles authentication using SAP BTP service key credentials.
Service keys contain client credentials and endpoints for cloud services.
"""
import json
from typing import Dict, Optional
from pathlib import Path
from auth.i_auth_provider import IAuthProvider
from auth.jwt_auth_provider import JWTAuthProvider


class ServiceKeyAuthProvider(IAuthProvider):
    """
    Service Key Authentication provider for SAP BTP/Cloud systems.

    Loads service key JSON file and uses it for OAuth2 authentication.
    Service keys typically contain:
    - uaa: OAuth2 endpoints and client credentials
    - endpoints: Service-specific URLs
    """

    def __init__(self, service_key_path: str = None, service_key_data: dict = None):
        """
        Initialize Service Key Auth provider.

        Args:
            service_key_path: Path to service key JSON file
            service_key_data: Service key data as dict (alternative to file)

        Raises:
            ValueError: If neither path nor data provided, or file doesn't exist
        """
        if service_key_path:
            self._service_key = self._load_service_key_file(service_key_path)
        elif service_key_data:
            self._service_key = service_key_data
        else:
            raise ValueError("Either service_key_path or service_key_data must be provided")

        # Extract OAuth2 credentials from service key
        self._jwt_provider = self._create_jwt_provider()

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers using JWT provider.

        Returns:
            Dict with Authorization header
        """
        return self._jwt_provider.get_auth_headers()

    def refresh_credentials(self) -> None:
        """Refresh JWT token via JWT provider."""
        self._jwt_provider.refresh_credentials()

    def is_valid(self) -> bool:
        """Check if JWT token is valid."""
        return self._jwt_provider.is_valid()

    @property
    def auth_type(self) -> str:
        """Return auth type identifier."""
        return 'service_key'

    @property
    def service_key(self) -> dict:
        """Get service key data."""
        return self._service_key

    @property
    def endpoints(self) -> dict:
        """Get service endpoints from service key."""
        return self._service_key.get('endpoints', {})

    def _load_service_key_file(self, path: str) -> dict:
        """
        Load service key from JSON file.

        Args:
            path: Path to service key file

        Returns:
            Service key data as dict

        Raises:
            ValueError: If file doesn't exist or is invalid JSON
        """
        service_key_path = Path(path)
        if not service_key_path.exists():
            raise ValueError(f"Service key file not found: {path}")

        try:
            with open(service_key_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in service key file: {e}")

    def _create_jwt_provider(self) -> JWTAuthProvider:
        """
        Create JWT provider from service key credentials.

        Returns:
            JWTAuthProvider instance configured from service key

        Raises:
            ValueError: If service key missing required fields
        """
        uaa = self._service_key.get('uaa', {})

        if not uaa:
            raise ValueError("Service key missing 'uaa' section")

        # Get OAuth2 credentials
        client_id = uaa.get('clientid')
        client_secret = uaa.get('clientsecret')

        if not client_id or not client_secret:
            raise ValueError("Service key missing clientid or clientsecret")

        # Get token URL
        token_url = uaa.get('url')
        if not token_url:
            # Try to construct from other fields
            token_url = uaa.get('tokenendpoint')

        if not token_url:
            raise ValueError("Service key missing token URL")

        return JWTAuthProvider(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            uaa_url=uaa.get('url')
        )

    def get_adt_base_url(self) -> Optional[str]:
        """
        Get ADT base URL from service key endpoints.

        Service keys may contain 'uri' or 'url' fields with ADT endpoints.

        Returns:
            ADT base URL or None
        """
        endpoints = self.service_key.get('endpoints', {})

        # Try common field names
        for key in ['uri', 'url', 'adt_uri', 'adt_url']:
            if key in self.service_key:
                return self.service_key[key]

        # Check endpoints section
        for key in ['adt', 'adt_uri', 'adt_url', 'uri', 'url']:
            if key in endpoints:
                return endpoints[key]

        return None

    @property
    def subdomain(self) -> Optional[str]:
        """Get BTP subdomain from service key."""
        uaa = self._service_key.get('uaa', {})
        url = uaa.get('url', '')

        # Extract subdomain from URL (e.g., abc123.eu10.hana.ondemand.com)
        if url:
            # Remove protocol
            url = url.replace('https://', '').replace('http://', '')
            # Split and get first part
            parts = url.split('.')
            if parts:
                return parts[0]

        return None

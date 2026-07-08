#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Key Parser for SAP BTP

Parses and validates SAP BTP service key JSON files.
Service keys contain OAuth2 credentials and endpoint URLs.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse


class ServiceKeyParser:
    """
    Parser for SAP BTP service key files.

    Service keys are JSON files with structure:
    {
        "uaa": {
            "clientid": "...",
            "clientsecret": "...",
            "url": "https://...",
            "tokenendpoint": "https://..."
        },
        "endpoints": {
            "adt": "https://..."
        }
    }
    """

    @staticmethod
    def parse_file(service_key_path: str) -> Dict[str, Any]:
        """
        Parse service key JSON file.

        Args:
            service_key_path: Path to service key file

        Returns:
            Parsed service key data

        Raises:
            ValueError: If file doesn't exist or is invalid JSON
        """
        path = Path(service_key_path)
        if not path.exists():
            raise ValueError(f"Service key file not found: {service_key_path}")

        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in service key file: {e}")

    @staticmethod
    def validate_service_key(service_key: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate service key has required fields.

        Args:
            service_key: Service key data

        Returns:
            Dict with 'valid' (bool), 'missing' (list), and 'errors' (list)

        Example:
            >>> result = ServiceKeyParser.validate_service_key(key_data)
            >>> if result['valid']:
            >>>     print("Service key is valid")
        """
        missing = []
        errors = []

        # Check for required UAA section
        uaa = service_key.get('uaa')
        if not uaa:
            missing.append('uaa')
        else:
            # Check UAA fields
            if not uaa.get('clientid'):
                missing.append('uaa.clientid')
            if not uaa.get('clientsecret'):
                missing.append('uaa.clientsecret')
            if not uaa.get('url') and not uaa.get('tokenendpoint'):
                missing.append('uaa.url or uaa.tokenendpoint')

        # Check for endpoints section
        endpoints = service_key.get('endpoints')
        if not endpoints:
            errors.append("No 'endpoints' section - ADT URL may not be available")

        # Check for ADT endpoint specifically
        if endpoints:
            adt_url = (endpoints.get('adt') or
                      endpoints.get('adt_uri') or
                      endpoints.get('adt_url') or
                      endpoints.get('uri') or
                      endpoints.get('url'))
            if not adt_url:
                errors.append("No ADT endpoint found in service key")

        return {
            'valid': len(missing) == 0,
            'missing': missing,
            'errors': errors
        }

    @staticmethod
    def extract_adt_url(service_key: Dict[str, Any]) -> Optional[str]:
        """
        Extract ADT base URL from service key.

        Args:
            service_key: Service key data

        Returns:
            ADT base URL or None
        """
        endpoints = service_key.get('endpoints', {})

        # Try common field names
        for key in ['adt', 'adt_uri', 'adt_url', 'uri', 'url']:
            url = endpoints.get(key) or service_key.get(key)
            if url:
                # Validate it looks like a URL
                if url.startswith('http'):
                    return url.rstrip('/')

        return None

    @staticmethod
    def extract_subdomain(service_key: Dict[str, Any]) -> Optional[str]:
        """
        Extract BTP subdomain from service key.

        Args:
            service_key: Service key data

        Returns:
            BTP subdomain (e.g., 'abc123-trial') or None
        """
        uaa = service_key.get('uaa', {})
        url = uaa.get('url', '')

        if url:
            # Parse URL and extract subdomain
            try:
                parsed = urlparse(url)
                hostname = parsed.netloc  # e.g., abc123.eu10.hana.ondemand.com
                if hostname:
                    # Get subdomain (first part before first dot)
                    subdomain = hostname.split('.')[0]
                    return subdomain
            except Exception:
                pass

        # Try clientid - sometimes contains subdomain info
        client_id = uaa.get('clientid', '')
        if client_id:
            # Some service keys have pattern like 'sb-abc123!b'
            parts = client_id.split('!')
            if len(parts) > 1:
                return parts[0].replace('sb-', '')

        return None

    @staticmethod
    def get_oauth_credentials(service_key: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract OAuth2 credentials from service key.

        Args:
            service_key: Service key data

        Returns:
            Dict with 'token_url', 'client_id', 'client_secret'
        """
        uaa = service_key.get('uaa', {})

        # Get token URL
        token_url = (uaa.get('tokenendpoint') or
                     uaa.get('url') or '')

        return {
            'token_url': token_url,
            'client_id': uaa.get('clientid', ''),
            'client_secret': uaa.get('clientsecret', ''),
            'uaa_url': uaa.get('url', '')
        }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Connection Helper for SAP BTP

Helper functions for connecting to SAP BTP cloud systems.
"""
import os
from typing import Optional, Dict
from cloud.service_key_parser import ServiceKeyParser
from auth import ServiceKeyAuthProvider, create_auth_provider


def get_btp_connection_from_service_key(service_key_path: str) -> Dict[str, any]:
    """
    Create BTP connection configuration from service key file.

    Args:
        service_key_path: Path to service key JSON file

    Returns:
        Dict with:
            - base_url: ADT base URL
            - auth_provider: ServiceKeyAuthProvider instance
            - system_info: System information dict

    Raises:
        ValueError: If service key is invalid
        FileNotFoundError: If service key file doesn't exist
    """
    # Parse service key
    service_key = ServiceKeyParser.parse_file(service_key_path)

    # Validate
    validation = ServiceKeyParser.validate_service_key(service_key)
    if not validation['valid']:
        missing = ', '.join(validation['missing'])
        raise ValueError(f"Invalid service key. Missing: {missing}")

    # Extract ADT URL
    base_url = ServiceKeyParser.extract_adt_url(service_key)
    if not base_url:
        raise ValueError("Service key missing ADT endpoint URL")

    # Create auth provider
    auth_provider = ServiceKeyAuthProvider(service_key_data=service_key)

    # Extract system info
    subdomain = ServiceKeyParser.extract_subdomain(service_key)
    oauth_creds = ServiceKeyParser.get_oauth_credentials(service_key)

    return {
        'base_url': base_url,
        'auth_provider': auth_provider,
        'system_info': {
            'subdomain': subdomain,
            'token_url': oauth_creds['token_url'],
            'client_id': oauth_creds['client_id'],
            'system_type': 'cloud'
        }
    }


def detect_system_type_from_env() -> str:
    """
    Detect SAP system type from environment variables.

    Checks for:
    - 'cloud' or 'btp' in ADT_SAP_URL
    - ADT_SAP_SERVICE_KEY env variable
    - JWT-related env variables

    Returns:
        'cloud' if BTP/cloud detected, 'onprem' otherwise
    """
    url = os.getenv('ADT_SAP_URL', '')
    service_key = os.getenv('ADT_SAP_SERVICE_KEY', '')
    jwt_url = os.getenv('ADT_SAP_JWT_URL', '')

    if 'cloud' in url.lower() or 'btp' in url.lower():
        return 'cloud'
    if service_key or jwt_url:
        return 'cloud'

    return 'onprem'


def create_connection_auto() -> Dict[str, any]:
    """
    Auto-detect system type and create appropriate connection.

    Checks environment for:
    1. Service key (BTP cloud)
    2. JWT credentials (BTP cloud)
    3. Basic credentials (on-prem)

    Returns:
        Dict with base_url and auth_provider

    Raises:
        ValueError: If no valid credentials found
    """
    system_type = detect_system_type_from_env()

    if system_type == 'cloud':
        # Try service key first
        service_key_path = os.getenv('ADT_SAP_SERVICE_KEY')
        if service_key_path:
            return get_btp_connection_from_service_key(service_key_path)

        # Try JWT credentials
        jwt_url = os.getenv('ADT_SAP_JWT_URL')
        client_id = os.getenv('ADT_SAP_CLIENT_ID')
        client_secret = os.getenv('ADT_SAP_CLIENT_SECRET')

        if jwt_url and client_id and client_secret:
            from auth import JWTAuthProvider
            base_url = os.getenv('ADT_SAP_URL')
            if not base_url:
                raise ValueError("ADT_SAP_URL required for JWT auth")

            return {
                'base_url': base_url,
                'auth_provider': JWTAuthProvider(
                    token_url=jwt_url,
                    client_id=client_id,
                    client_secret=client_secret
                ),
                'system_info': {'system_type': 'cloud'}
            }

    # Fall back to Basic Auth
    from auth import BasicAuthProvider
    base_url = os.getenv('ADT_SAP_URL')
    username = os.getenv('ADT_SAP_USER')
    password = os.getenv('ADT_SAP_PASSWORD')
    client = os.getenv('ADT_SAP_CLIENT', '000')

    if not all([base_url, username, password]):
        raise ValueError(
            "Missing credentials. Either provide:\n"
            "  - Service key (ADT_SAP_SERVICE_KEY)\n"
            "  - JWT credentials (ADT_SAP_JWT_URL + ADT_SAP_CLIENT_ID + ADT_SAP_CLIENT_SECRET)\n"
            "  - Basic credentials (ADT_SAP_URL + ADT_SAP_USER + ADT_SAP_PASSWORD)"
        )

    return {
        'base_url': base_url,
        'auth_provider': BasicAuthProvider(
            username=username,
            password=password,
            client=client
        ),
        'system_info': {'system_type': 'onprem'}
    }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Providers for SAP ADT

This module provides various authentication methods for SAP ADT:
- BasicAuth: Username/password (on-premise)
- JWTAuth: JWT tokens (SAP BTP/Cloud)
- ServiceKeyAuth: Service key credentials (SAP BTP/Cloud)
"""

from auth.i_auth_provider import IAuthProvider
from auth.basic_auth_provider import BasicAuthProvider
from auth.jwt_auth_provider import JWTAuthProvider, XSUAAAuthProvider
from auth.service_key_auth_provider import ServiceKeyAuthProvider
from auth.saml_auth_provider import SAMLAuthProvider, detect_saml_system

__all__ = [
    'IAuthProvider',
    'BasicAuthProvider',
    'JWTAuthProvider',
    'XSUAAAuthProvider',
    'ServiceKeyAuthProvider',
    'SAMLAuthProvider',
    'detect_saml_system',
    'create_auth_provider'
]


def create_auth_provider(auth_type: str = 'basic', **kwargs) -> IAuthProvider:
    """
    Factory function to create authentication providers.

    Args:
        auth_type: Type of authentication ('basic', 'jwt', 'service_key', 'xsuaa', 'saml')
        **kwargs: Additional arguments passed to provider constructor

    Returns:
        IAuthProvider instance

    Raises:
        ValueError: If auth_type is unknown

    Examples:
        # Basic auth
        provider = create_auth_provider(
            'basic',
            username='DEVELOPER',
            password='developer4',
            client='000'
        )

        # JWT auth
        provider = create_auth_provider(
            'jwt',
            token_url='https://.../oauth/token',
            client_id='...',
            client_secret='...'
        )

        # Service key auth
        provider = create_auth_provider(
            'service_key',
            service_key_path='/path/to/service-key.json'
        )

        # SAML SSO auth
        provider = create_auth_provider(
            'saml',
            base_url='https://my415633.s4hana.cloud.sap',
            username='user@example.com',
            password='password'
        )
    """
    if auth_type == 'basic':
        return BasicAuthProvider(
            username=kwargs.get('username', ''),
            password=kwargs.get('password', ''),
            client=kwargs.get('client')
        )
    elif auth_type == 'jwt':
        return JWTAuthProvider(
            token_url=kwargs.get('token_url'),
            client_id=kwargs.get('client_id'),
            client_secret=kwargs.get('client_secret'),
            uaa_url=kwargs.get('uaa_url'),
            token=kwargs.get('token')
        )
    elif auth_type == 'xsuaa':
        return XSUAAAuthProvider(
            subdomain=kwargs.get('subdomain'),
            client_id=kwargs.get('client_id'),
            client_secret=kwargs.get('client_secret'),
            token_url=kwargs.get('token_url'),
            uaa_url=kwargs.get('uaa_url')
        )
    elif auth_type == 'service_key':
        return ServiceKeyAuthProvider(
            service_key_path=kwargs.get('service_key_path'),
            service_key_data=kwargs.get('service_key_data')
        )
    elif auth_type == 'saml':
        return SAMLAuthProvider(
            base_url=kwargs.get('base_url', ''),
            username=kwargs.get('username', ''),
            password=kwargs.get('password', ''),
            cookies_file=kwargs.get('cookies_file')
        )
    else:
        raise ValueError(f"Unknown auth type: {auth_type}. "
                        f"Supported: 'basic', 'jwt', 'xsuaa', 'service_key', 'saml'")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAML SSO Authentication Provider for SAP ADT

Handles SAML SSO authentication for SAP S/4HANA Cloud public edition.
Uses browser automation to handle the SAML login flow and extract session cookies.
"""
import json
import os
import time
from typing import Dict, Optional, List
from pathlib import Path
from auth.i_auth_provider import IAuthProvider


class SAMLAuthProvider(IAuthProvider):
    """
    SAML SSO Authentication provider for SAP S/4HANA Cloud.

    This provider handles SAML authentication by:
    1. Using browser automation to perform SAML login
    2. Extracting session cookies from authenticated browser session
    3. Using cookies for subsequent ADT API calls

    The cookies are stored and can be persisted for reuse.
    """

    # SAP S/4HANA Cloud identity provider patterns
    IDP_PATTERNS = [
        'accounts.cloud.sap',
        'cloud.sap',
        '.s4hana.cloud.sap',
    ]

    def __init__(self, base_url: str, username: str, password: str,
                 cookies_file: Optional[str] = None):
        """
        Initialize SAML Auth provider.

        Args:
            base_url: SAP system base URL (e.g., https://my415633.s4hana.cloud.sap)
            username: SAP username (email for cloud systems)
            password: SAP password
            cookies_file: Optional path to persist cookies (JSON format)
        """
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._cookies_file = cookies_file
        self._cookies: Dict[str, str] = {}
        self._session_cookies: List[Dict] = []

        # Load persisted cookies if available
        if cookies_file and Path(cookies_file).exists():
            self._load_cookies()

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers.

        For SAML, authentication is via cookies, not headers.
        The cookies are applied to the session separately.

        Returns:
            Empty dict (cookies used instead)
        """
        return {}

    def refresh_credentials(self) -> None:
        """
        Refresh credentials by performing SAML login.

        For SAML, this is a no-op since cookies are managed externally
        via browser automation. Use set_cookies() to update cookies.
        """
        # SAML cookies are managed externally via browser automation
        # This is a no-op for compatibility with the IAuthProvider interface
        pass

    def is_valid(self) -> bool:
        """
        Check if SAML session is valid.

        Returns:
            True if session cookies exist
        """
        return bool(self._cookies)

    @property
    def auth_type(self) -> str:
        """Return auth type identifier."""
        return 'saml'

    @property
    def cookies(self) -> Dict[str, str]:
        """Get session cookies."""
        return self._cookies.copy()

    @property
    def session_cookies(self) -> List[Dict]:
        """Get session cookies in requests.Session format."""
        return self._session_cookies.copy()

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Set session cookies from external source (e.g., browser automation).

        Args:
            cookies: Dict of cookie name -> value
        """
        self._cookies = cookies.copy()

        # Extract domain from base_url for cookies
        from urllib.parse import urlparse
        domain = ''
        if self._base_url:
            parsed = urlparse(self._base_url)
            domain = parsed.netloc

        self._session_cookies = [
            {
                'name': name,
                'value': value,
                'domain': domain,
                'path': '/',
                'secure': True,
            }
            for name, value in cookies.items()
        ]

        # Persist cookies if file path configured
        if self._cookies_file:
            self._save_cookies()

    def set_cookies_from_browser(self, browser_cookies: List[Dict]) -> None:
        """
        Set cookies from browser automation result.

        Args:
            browser_cookies: List of cookie dicts from browser (Playwright format)
        """
        self._cookies = {}
        self._session_cookies = []

        for cookie in browser_cookies:
            # Get cookie attributes
            name = cookie.get('name', '')
            value = cookie.get('value', '')

            if not name:
                continue

            self._cookies[name] = value

            # Store full cookie data for requests.Session
            self._session_cookies.append({
                'name': name,
                'value': value,
                'domain': cookie.get('domain', ''),
                'path': cookie.get('path', '/'),
                'secure': cookie.get('secure', True),
                'httpOnly': cookie.get('httpOnly', False),
            })

        # Persist cookies if file path configured
        if self._cookies_file:
            self._save_cookies()

    def get_sap_session_id(self) -> Optional[str]:
        """
        Get the SAP session ID cookie value.

        Returns:
            SAP_SESSIONID cookie value or None
        """
        for name, value in self._cookies.items():
            if name.startswith('SAP_SESSIONID'):
                return value
        return None

    def _load_cookies(self) -> None:
        """Load cookies from file."""
        if not self._cookies_file or not Path(self._cookies_file).exists():
            return

        try:
            with open(self._cookies_file, 'r') as f:
                data = json.load(f)
                self._cookies = data.get('cookies', {})
                self._session_cookies = data.get('session_cookies', [])
        except Exception as e:
            # Don't fail if cookies can't be loaded
            pass

    def _save_cookies(self) -> None:
        """Save cookies to file."""
        if not self._cookies_file:
            return

        try:
            cookies_dir = Path(self._cookies_file).parent
            cookies_dir.mkdir(parents=True, exist_ok=True)

            data = {
                'cookies': self._cookies,
                'session_cookies': self._session_cookies,
                'base_url': self._base_url,
                'username': self._username,
                'obtained_at': time.time(),
            }

            with open(self._cookies_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            # Don't fail if cookies can't be saved
            pass

    def clear_cookies(self) -> None:
        """Clear stored cookies."""
        self._cookies = {}
        self._session_cookies = []

        # Delete cookies file if exists
        if self._cookies_file and Path(self._cookies_file).exists():
            try:
                Path(self._cookies_file).unlink()
            except Exception:
                pass


def detect_saml_system(url: str) -> bool:
    """
    Detect if a URL is likely a SAML SSO system.

    Args:
        url: SAP system URL

    Returns:
        True if URL matches S/4HANA Cloud patterns
    """
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in SAMLAuthProvider.IDP_PATTERNS)

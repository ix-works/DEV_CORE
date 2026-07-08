#!/usr/bin/env python3
"""
SAP ADT API Library
Common functions for SAP ADT (ABAP Development Tools) API operations
"""
import re
import time
import html
import xml.etree.ElementTree as ET
import requests
import base64
import os
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv

# Ensure scripts directory is in path for imports
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

# Import auth providers for BTP cloud support
try:
    from auth.i_auth_provider import IAuthProvider
    from auth.basic_auth_provider import BasicAuthProvider
    from auth.jwt_auth_provider import JWTAuthProvider
    from auth.service_key_auth_provider import ServiceKeyAuthProvider
    from auth.saml_auth_provider import SAMLAuthProvider, detect_saml_system
    from auth import create_auth_provider
    AUTH_PROVIDERS_AVAILABLE = True
except ImportError:
    # If auth providers are not available, fall back to basic auth
    AUTH_PROVIDERS_AVAILABLE = False
    detect_saml_system = lambda x: False
    IAuthProvider = None  # type: ignore
    BasicAuthProvider = None  # type: ignore
    JWTAuthProvider = None  # type: ignore
    ServiceKeyAuthProvider = None  # type: ignore
    SAMLAuthProvider = None  # type: ignore
    create_auth_provider = None  # type: ignore

# Suppress SSL warnings for self-signed certs (default: verify=false)
if os.getenv('ADT_SAP_SSL_VERIFY', 'false').lower() not in ('true', '1', 'yes'):
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


# =============================================================================
# Custom Exception Classes
# =============================================================================

class SAPADTError(Exception):
    """Base exception for all SAP ADT errors"""

    def __init__(self, message, status_code=None, response_text=None, endpoint=None, **kwargs):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        self.endpoint = endpoint
        super().__init__(self.message)

    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class SAPConnectionError(SAPADTError):
    """Error connecting to SAP system"""
    pass


class SAPAuthenticationError(SAPADTError):
    """Authentication failed (401/403)"""
    pass


class SAPObjectNotFoundError(SAPADTError):
    """Object not found (404)"""
    pass


class SAPObjectExistsError(SAPADTError):
    """Object already exists"""
    pass


class SAPLockError(SAPADTError):
    """Object is locked by another user"""

    def __init__(self, message, lock_owner=None, **kwargs):
        super().__init__(message, **kwargs)
        self.lock_owner = lock_owner


class SAPActivationError(SAPADTError):
    """Object activation failed"""

    def __init__(self, message, errors=None, **kwargs):
        super().__init__(message, **kwargs)
        self.errors = errors or []


class SAPValidationError(SAPADTError):
    """Invalid input or configuration"""
    pass


class SAPTransportError(SAPADTError):
    """Transport-related error"""
    pass


def parse_sap_error(response):
    """
    Parse SAP ADT error response and return appropriate exception.

    Args:
        response: requests.Response object

    Returns:
        Appropriate SAPADTError subclass instance
    """
    status = response.status_code
    text = response.text

    # Extract message from XML if possible
    message = text
    try:

        msg_match = re.search(r'<message[^>]*>([^<]+)</message>', text)
        if msg_match:
            message = msg_match.group(1)
    except Exception:
        pass

    # Map status codes to exception types
    if status == 401:
        return SAPAuthenticationError(
            "Authentication failed. Check SAP_USER and SAP_PASSWORD.",
            status_code=status, response_text=text
        )
    elif status == 403:
        if 'locked' in text.lower():
            # Try to extract lock owner
            owner = None
            try:
        
                owner_match = re.search(r'locked by[:\s]+(\w+)', text, re.IGNORECASE)
                if owner_match:
                    owner = owner_match.group(1)
            except Exception:
                pass
            return SAPLockError(
                f"Object is locked by another user{': ' + owner if owner else ''}",
                lock_owner=owner, status_code=status, response_text=text
            )
        return SAPAuthenticationError(
            f"Access denied: {message}",
            status_code=status, response_text=text
        )
    elif status == 404:
        return SAPObjectNotFoundError(
            f"Object not found: {message}",
            status_code=status, response_text=text
        )
    elif status == 400:
        if 'already exist' in text.lower():
            return SAPObjectExistsError(
                f"Object already exists: {message}",
                status_code=status, response_text=text
            )
        return SAPValidationError(
            f"Invalid request: {message}",
            status_code=status, response_text=text
        )
    elif status == 500:
        return SAPADTError(
            f"Server error: {message}",
            status_code=status, response_text=text
        )
    else:
        return SAPADTError(
            f"Request failed: {message}",
            status_code=status, response_text=text
        )


# =============================================================================
# Utility Functions
# =============================================================================

def retry_on_failure(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    Decorator to retry a function on failure.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch

    Usage:
        @retry_on_failure(max_retries=3, exceptions=(SAPConnectionError,))
        def some_api_call():
            ...
    """

    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        return wrapper
    return decorator


def validate_object_name(name, object_type='class'):
    """
    Validate SAP object name follows naming conventions.

    Args:
        name: Object name to validate
        object_type: Type of object ('class', 'table', 'structure', etc.)

    Raises:
        SAPValidationError if name is invalid
    """
    if not name:
        raise SAPValidationError("Object name cannot be empty")

    name_upper = name.upper()

    # Check length (max 30 characters for most objects)
    if len(name) > 30:
        raise SAPValidationError(f"Object name '{name}' exceeds 30 characters")

    # Check for valid characters (alphanumeric and underscore)

    if not re.match(r'^[A-Z][A-Z0-9_]*$', name_upper):
        raise SAPValidationError(
            f"Object name '{name}' must start with a letter and contain only "
            "letters, numbers, and underscores"
        )

    # Class names should follow ZCL_/YCL_ or {PACKAGE}_CL_ naming
    if object_type and object_type.lower() == 'class':
        if name_upper.startswith(('ZCL_', 'YCL_')) or '_CL_' in name_upper:
            return True
        if name_upper.startswith(('ZCL', 'YCL')) or '_CL' in name_upper:
            raise SAPValidationError(
                f"Class name '{name}' must use ZCL_/YCL_ or *_CL_ prefix"
            )

    # Check for customer namespace (Z or Y prefix)
    if not name_upper.startswith(('Z', 'Y')):
        raise SAPValidationError(
            f"Object name '{name}' must start with Z or Y (customer namespace)"
        )

    return True


def validate_package_name(package):
    """
    Validate SAP package name.

    Args:
        package: Package name to validate

    Raises:
        SAPValidationError if package name is invalid
    """
    if not package:
        raise SAPValidationError("Package name cannot be empty")

    package_upper = package.upper()

    if package != package_upper:
        raise SAPValidationError(
            f"Package name '{package}' must be uppercase"
        )

    # Check for valid characters

    if not re.match(r'^[A-Z$][A-Z0-9_$]*$', package_upper):
        raise SAPValidationError(
            f"Package name '{package}' contains invalid characters"
        )

    return True


# =============================================================================
# Environment and Configuration
# =============================================================================

# Module-level variable to store explicit working directory (set via --cwd)
# This is checked BEFORE searching for .conn_adt
_explicit_working_dir = None


def set_explicit_working_dir(path: str) -> None:
    """
    Set an explicit working directory for finding .conn_adt.

    This should be called before any SAP operations if you want to override
    the automatic directory discovery. Useful when scripts are run from
    plugin cache directories.

    Args:
        path: Path to the directory containing .conn_adt

    Example:
        set_explicit_working_dir('C:\\Users\\project\\folder')
    """
    global _explicit_working_dir, conn_path, ADT_SAP_URL, ADT_SAP_USER, ADT_SAP_PASSWORD, ADT_SAP_CLIENT, ADT_SAP_LANGUAGE

    _explicit_working_dir = Path(path).resolve()

    # Re-discover and reload .conn_adt from the new location
    conn_path = find_conn_file()

    # Clear and reload environment variables
    ADT_SAP_URL = None
    ADT_SAP_USER = None
    ADT_SAP_PASSWORD = None
    ADT_SAP_CLIENT = None
    ADT_SAP_LANGUAGE = 'EN'

    if conn_path.exists():
        # FIX 2026-05-14: load_dotenv default override=False → mevcut env var'lar
        # yenisini ezmez. set_explicit_working_dir farklı sisteme switch etmek için
        # override=True şart (örn. <PROJECT_NAME>→<LEGACY_SOURCE> geçişi).
        # Önce os.environ'dan temizle, sonra override=True ile yükle.
        for k in ('ADT_SAP_URL', 'ADT_SAP_USER', 'ADT_SAP_PASSWORD',
                  'ADT_SAP_CLIENT', 'ADT_SAP_LANGUAGE', 'ADT_SAP_SSL_VERIFY'):
            os.environ.pop(k, None)
        load_dotenv(dotenv_path=conn_path, override=True)
        ADT_SAP_URL = os.getenv('ADT_SAP_URL')
        ADT_SAP_USER = os.getenv('ADT_SAP_USER')
        ADT_SAP_PASSWORD = os.getenv('ADT_SAP_PASSWORD')
        ADT_SAP_CLIENT = os.getenv('ADT_SAP_CLIENT')
        ADT_SAP_LANGUAGE = os.getenv('ADT_SAP_LANGUAGE', 'EN')


def get_explicit_working_dir() -> Optional[Path]:
    """
    Get the explicit working directory if set.

    Returns:
        Path to explicit working directory, or None if not set
    """
    return _explicit_working_dir


def find_conn_file():
    """Find .conn_adt file for SAP ADT credentials.

    Uses .conn_adt (not .env) to avoid conflicts with other tools that use
    generic SAP_* environment variables. All variables are prefixed with ADT_
    to ensure isolation.

    IMPORTANT: The .conn_adt file should be in the directory where Claude Code is opened.
    This supports folder structures like:
        sap_work/
          client_a/.conn_adt  (credentials for client A)
          client_b/.conn_adt  (credentials for client B)

    NOTE: Some runners set PWD to the plugin's scripts folder even when your real
    working directory is your project folder. We therefore search multiple candidate
    working directories and pick the first one that actually contains a .conn_adt.

    Returns: Path to .conn_adt file (may not exist yet - will be created with template)
    """

    # CRITICAL: If explicit working directory was set, use it FIRST
    if _explicit_working_dir:
        conn_file = _explicit_working_dir / '.conn_adt'
        if conn_file.exists():
            return conn_file
        # Return the path even if it doesn't exist (for template creation)
        return conn_file

    def iter_candidate_dirs():
        # CRITICAL: Check environment variables that point to Claude Code's working directory FIRST
        # These are set by Claude Code to indicate the real project directory
        for env_var in ['CLAUDE_PROJECT_DIR', 'CLAUDE_CWD', 'INIT_CWD', 'COPILOT_CWD']:
            value = os.getenv(env_var)
            if value:
                p = Path(value)
                if p.exists():
                    yield p.resolve()

        # Use the process working directory (where Claude Code was opened)
        # This should be the user's project directory, NOT the plugin scripts directory
        cwd = Path.cwd().resolve()

        # If cwd is inside a plugin cache or scripts directory, it's likely wrong
        # (happens when skill uses 'cd' before running the script)
        # In that case, try to find a better parent directory
        if '.claude' in str(cwd) or 'plugins' in str(cwd):
            # Look for parent directories that might contain .conn_adt
            # Search up to 5 levels up
            for i in range(1, 6):
                parent = cwd.parents[i-1] if len(cwd.parents) >= i else None
                if parent and (parent / '.conn_adt').exists():
                    yield parent.resolve()
                    break

        yield cwd

        # PWD last (often incorrect on Windows)
        value = os.getenv('PWD')
        if value:
            p = Path(value)
            if p.exists():
                yield p.resolve()

    for base_dir in iter_candidate_dirs():
        conn_file = base_dir / '.conn_adt'
        if conn_file.exists():
            return conn_file

    # Default create location: the actual process cwd (not PWD)
    return Path.cwd().resolve() / '.conn_adt'


# Find .conn_adt file path in user's project (not plugin directory)
conn_path = find_conn_file()

# Load .conn_adt if it exists (uses ADT_ prefixed variables to avoid conflicts)
if conn_path.exists():
    load_dotenv(dotenv_path=conn_path)

# SAP Connection Configuration - uses ADT_ prefix to avoid conflicts with other SAP tools
# These will ONLY be set if loaded from .conn_adt file, not from system environment
ADT_SAP_URL = os.getenv('ADT_SAP_URL')
ADT_SAP_USER = os.getenv('ADT_SAP_USER')
ADT_SAP_PASSWORD = os.getenv('ADT_SAP_PASSWORD')
ADT_SAP_CLIENT = os.getenv('ADT_SAP_CLIENT')
ADT_SAP_LANGUAGE = os.getenv('ADT_SAP_LANGUAGE', 'EN')

# SAP BTP Cloud Configuration
ADT_BTP_SERVICE_KEY_PATH = os.getenv('ADT_BTP_SERVICE_KEY_PATH')  # Path to service key JSON file
ADT_BTP_AUTH_TYPE = os.getenv('ADT_BTP_AUTH_TYPE', 'basic')  # 'basic', 'jwt', or 'service_key'


def get_conn_path():
    """Return the path where .conn_adt should be located."""
    return conn_path


def debug_conn_discovery():
    """
    Debug function to show where .conn_adt was found and what was loaded.
    Useful for diagnosing credential issues.

    Returns:
        dict with debug information
    """
    return {
        'conn_path': str(conn_path),
        'conn_exists': conn_path.exists() if conn_path else False,
        'working_dir_sources': {
            'CLAUDE_CWD': os.getenv('CLAUDE_CWD'),
            'INIT_CWD': os.getenv('INIT_CWD'),
            'PWD': os.getenv('PWD'),
            'cwd()': str(Path.cwd()),
        },
        'loaded_config': {
            'ADT_SAP_URL': ADT_SAP_URL,
            'ADT_SAP_USER': ADT_SAP_USER,
            'ADT_SAP_PASSWORD': '***' if ADT_SAP_PASSWORD else None,
            'ADT_SAP_CLIENT': ADT_SAP_CLIENT,
        }
    }


def check_sap_config():
    """
    Check SAP configuration status.

    Supports both On-Premise (basic auth) and BTP Cloud (service key) configurations.

    Returns:
        dict with keys:
        - 'configured': bool - True if valid config exists
        - 'conn_exists': bool - True if .conn_adt file exists
        - 'conn_path': str - Path where .conn_adt is/should be
        - 'missing': list - Missing required fields
        - 'placeholders': list - Fields with placeholder values
        - 'auth_type': str - 'basic', 'service_key', or None
    """
    placeholder_values = [
        'your-sap-server.com', 'YOUR_USERNAME', 'YOUR_PASSWORD',
        'https://your-sap-server.com:44300'
    ]

    # Check for BTP service key configuration
    service_key_path = os.getenv('ADT_BTP_SERVICE_KEY_PATH')
    auth_type = os.getenv('ADT_BTP_AUTH_TYPE', '').lower()

    # Determine auth type
    if service_key_path:
        auth_type = 'service_key'
        # Check if service key file exists
        sk_path = Path(service_key_path)
        if not sk_path.is_absolute() and conn_path:
            sk_path = conn_path.parent / service_key_path

        if sk_path.exists():
            # Service key exists - validate URL
            if not ADT_SAP_URL:
                return {
                    'configured': False,
                    'conn_exists': conn_path.exists(),
                    'conn_path': str(conn_path),
                    'missing': ['ADT_SAP_URL'],
                    'placeholders': [],
                    'auth_type': 'service_key'
                }
            # Service key auth is valid
            return {
                'configured': True,
                'conn_exists': conn_path.exists(),
                'conn_path': str(conn_path),
                'missing': [],
                'placeholders': [],
                'auth_type': 'service_key'
            }

    # Basic auth configuration (default)
    config = {
        'ADT_SAP_URL': ADT_SAP_URL,
        'ADT_SAP_USER': ADT_SAP_USER,
        'ADT_SAP_PASSWORD': ADT_SAP_PASSWORD,
        'ADT_SAP_CLIENT': ADT_SAP_CLIENT
    }

    missing = []
    placeholders = []

    for key, value in config.items():
        if not value:
            missing.append(key)
        elif any(pv in str(value) for pv in placeholder_values):
            placeholders.append(key)

    return {
        'configured': len(missing) == 0 and len(placeholders) == 0,
        'conn_exists': conn_path.exists(),
        'conn_path': str(conn_path),
        'missing': missing,
        'placeholders': placeholders,
        'auth_type': 'basic'
    }


def create_conn_file(sap_url, sap_user, sap_password, sap_client, sap_language='EN'):
    """
    Create .conn_adt file with provided SAP credentials.

    Args:
        sap_url: SAP server URL (e.g., https://server.com:44300)
        sap_user: SAP username
        sap_password: SAP password
        sap_client: SAP client number (e.g., 100)
        sap_language: Language code (default: EN)

    Returns:
        str: Path to created .conn_adt file
    """
    conn_content = f"""# SAP ADT Connection Configuration
# Generated by ABAP Developer Plugin
# Uses ADT_ prefix to avoid conflicts with other SAP tools

ADT_SAP_URL={sap_url}
ADT_SAP_USER={sap_user}
ADT_SAP_PASSWORD={sap_password}
ADT_SAP_CLIENT={sap_client}
ADT_SAP_LANGUAGE={sap_language}
"""
    conn_path.write_text(conn_content)

    # Reload environment variables
    load_dotenv(dotenv_path=conn_path, override=True)

    # Update module-level variables
    global ADT_SAP_URL, ADT_SAP_USER, ADT_SAP_PASSWORD, ADT_SAP_CLIENT, ADT_SAP_LANGUAGE
    ADT_SAP_URL = sap_url
    ADT_SAP_USER = sap_user
    ADT_SAP_PASSWORD = sap_password
    ADT_SAP_CLIENT = sap_client
    ADT_SAP_LANGUAGE = sap_language

    return str(conn_path)


def create_conn_template():
    """
    Create .conn_adt template file with placeholder values.

    Returns:
        str: Path to created .conn_adt file
    """
    template = """# SAP ADT Connection Configuration
# Please update these values with your SAP system credentials
# Uses ADT_ prefix to avoid conflicts with other SAP tools

# === On-Premise SAP System (Basic Auth) ===
ADT_SAP_URL=https://your-sap-server.com:44300
ADT_SAP_USER=YOUR_USERNAME
ADT_SAP_PASSWORD=YOUR_PASSWORD
ADT_SAP_CLIENT=100
ADT_SAP_LANGUAGE=EN

# === SAP BTP Cloud (Service Key Auth) ===
# For BTP cloud systems, use service key instead of username/password:
# 1. Download service key from your BTP subaccount (XSUAA)
# 2. Save it as a JSON file (e.g., .conn_btp_cloud.json)
# 3. Update ADT_BTP_SERVICE_KEY_PATH to point to that file
# ADT_BTP_SERVICE_KEY_PATH=.conn_btp_cloud.json
# ADT_BTP_AUTH_TYPE=service_key

# Optional: SSL certificate verification (default: false for self-signed certs)
# ADT_SAP_SSL_VERIFY=false
"""
    conn_path.write_text(template)
    return str(conn_path)


def validate_sap_config():
    """
    Validate SAP configuration and provide helpful error messages.
    If .conn_adt doesn't exist, creates a template file for the user to fill in.

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    status = check_sap_config()

    if status['configured']:
        return True, None

    # If .conn_adt doesn't exist, create a template
    if not status['conn_exists']:
        create_conn_template()
        msg = f"\n[SAP ADT] Configuration Required!\n"
        msg += f"[SAP ADT] Created .conn_adt template at: {status['conn_path']}\n"
        msg += "\n[SAP ADT] Please configure your SAP connection:\n\n"
        msg += "For On-Premise SAP (Basic Auth):\n"
        msg += "  - ADT_SAP_URL: SAP server URL (e.g., https://server.com:44300)\n"
        msg += "  - ADT_SAP_USER: Your SAP username\n"
        msg += "  - ADT_SAP_PASSWORD: Your SAP password\n"
        msg += "  - ADT_SAP_CLIENT: SAP client number (e.g., 100)\n\n"
        msg += "For SAP BTP Cloud (Service Key):\n"
        msg += "  - ADT_SAP_URL: Your BTP system URL\n"
        msg += "  - ADT_BTP_SERVICE_KEY_PATH: Path to service key JSON file\n"
        msg += "  - ADT_BTP_AUTH_TYPE: service_key\n"
        msg += "\n[SAP ADT] Then retry your operation.\n"
        return False, msg

    # .conn_adt exists but has issues
    msg = f"\n[SAP ADT] Configuration Incomplete!\n"
    msg += f"[SAP ADT] .conn_adt location: {status['conn_path']}\n"
    msg += f"[SAP ADT] Auth type: {status.get('auth_type', 'unknown')}\n"

    if status['missing']:
        msg += f"[SAP ADT] Missing values: {', '.join(status['missing'])}\n"
    if status['placeholders']:
        msg += f"[SAP ADT] Placeholder values need updating: {', '.join(status['placeholders'])}\n"

    msg += "\n[SAP ADT] Please update your .conn_adt file with valid SAP credentials.\n"
    return False, msg


def set_session_credentials(sap_url, sap_user, sap_password, sap_client, sap_language='EN'):
    """
    Set SAP credentials as session environment variables.

    This allows credentials to be provided programmatically (e.g., by LLM agent)
    without creating a .conn_adt file. Credentials are valid for the current
    Python process only and are not persisted to disk.

    Args:
        sap_url: SAP server URL (e.g., https://server.com:44300)
        sap_user: SAP username
        sap_password: SAP password
        sap_client: SAP client number (e.g., 100)
        sap_language: Language code (default: EN)

    Returns:
        dict with keys:
            - success: bool
            - message: str

    Example:
        set_session_credentials(
            "https://sap.example.com:44300",
            "DEVELOPER",
            "secret123",
            "100"
        )
    """
    global ADT_SAP_URL, ADT_SAP_USER, ADT_SAP_PASSWORD, ADT_SAP_CLIENT, ADT_SAP_LANGUAGE

    try:
        # Set environment variables for current process
        os.environ['ADT_SAP_URL'] = sap_url
        os.environ['ADT_SAP_USER'] = sap_user
        os.environ['ADT_SAP_PASSWORD'] = sap_password
        os.environ['ADT_SAP_CLIENT'] = sap_client
        os.environ['ADT_SAP_LANGUAGE'] = sap_language

        # Update module-level variables
        ADT_SAP_URL = sap_url
        ADT_SAP_USER = sap_user
        ADT_SAP_PASSWORD = sap_password
        ADT_SAP_CLIENT = sap_client
        ADT_SAP_LANGUAGE = sap_language

        return {
            'success': True,
            'message': 'Session credentials set successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to set session credentials: {str(e)}'
        }


def clear_session_credentials():
    """
    Clear session SAP credentials from environment.

    This removes the ADT_* environment variables from the current process.
    Useful for testing or when switching between different SAP systems.

    Returns:
        bool: True if credentials were cleared, False otherwise
    """
    global ADT_SAP_URL, ADT_SAP_USER, ADT_SAP_PASSWORD, ADT_SAP_CLIENT, ADT_SAP_LANGUAGE

    cleared = False

    for key in ['ADT_SAP_URL', 'ADT_SAP_USER', 'ADT_SAP_PASSWORD', 'ADT_SAP_CLIENT', 'ADT_SAP_LANGUAGE']:
        if key in os.environ:
            del os.environ[key]
            cleared = True

    # Reset module-level variables
    ADT_SAP_URL = None
    ADT_SAP_USER = None
    ADT_SAP_PASSWORD = None
    ADT_SAP_CLIENT = None
    ADT_SAP_LANGUAGE = 'EN'

    return cleared

    return False, msg


class SAPADTClient:
    """SAP ADT API Client with support for On-Premise and BTP Cloud authentication"""

    def __init__(self, url=None, user=None, password=None, client=None, language=None,
                 auth_provider=None, auth_type=None):
        """
        Initialize SAP ADT Client

        Args:
            url: SAP system URL
            user: Username (for basic auth)
            password: Password (for basic auth)
            client: SAP client number
            language: Language code
            auth_provider: Optional IAuthProvider instance for custom auth
            auth_type: Optional auth type hint ('basic', 'jwt', 'service_key')
        """
        # Validate configuration if using defaults from .conn_adt
        if not any([url, user, password, client, auth_provider]):
            is_valid, error_msg = validate_sap_config()
            if not is_valid:
                raise SAPConnectionError(error_msg)

        self.url = url or ADT_SAP_URL
        self.user = user or ADT_SAP_USER
        self.password = password or ADT_SAP_PASSWORD
        self.client = client or ADT_SAP_CLIENT
        self.language = language or ADT_SAP_LANGUAGE
        self.csrf_token = None
        self.cookies = None

        # Debug logging - initialize before auth provider (used in error handling)
        self.debug_enabled = (os.getenv('ADT_SAP_DEBUG') == '1') or (os.getenv('SAP_ADT_DEBUG') == '1')
        self.debug_log_path = None
        if self.debug_enabled:
            explicit_dir = get_explicit_working_dir()
            log_dir = explicit_dir if explicit_dir else Path.cwd()
            self.debug_log_path = log_dir / "sap_adt_debug.log"
            try:
                self.debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass  # Fail silently if debug log can't be created

        # Initialize auth provider
        self._auth_provider = auth_provider or self._create_auth_provider(auth_type)

        # Connection pooling via requests.Session
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry as _Retry
        self.session = requests.Session()
        ssl_verify = os.getenv('ADT_SAP_SSL_VERIFY', 'false').lower()
        self.session.verify = ssl_verify in ('true', '1', 'yes')

        _adapter = HTTPAdapter(
            pool_connections=4,
            pool_maxsize=10,
            max_retries=_Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=('GET', 'HEAD', 'PUT', 'POST', 'DELETE'),
            ),
        )
        self.session.mount('https://', _adapter)
        self.session.mount('http://', _adapter)
        self.session.headers.update({'Accept-Encoding': 'gzip, deflate'})

        # Set initial headers with auth from provider
        auth_headers = self._get_auth_headers()
        self.session.headers.update(auth_headers)
        is_saml_init = self._auth_provider and getattr(self._auth_provider, 'auth_type', '') == 'saml'
        if not is_saml_init:
            self.session.headers.update({
                'sap-client': self.client,
                # ADR 0005-D: logon dilini session-genelinde TR yap. SAP, obje master
                # dilini session'ın logon diline göre belirler (body masterLanguage tek
                # başına yetmez). sap-language'ı session default header yapınca İLK auth
                # dahil tüm istekler TR logon olur → Z obje masterLanguage=TR.
                # (gap-analysis #20; feedback_mcp-post-shell-en-master-lang)
                'sap-language': self.language,
                'x-sap-adt-sessiontype': 'stateful',
            })
        else:
            self.session.headers.update({
                'sap-language': self.language,
                'x-sap-adt-sessiontype': 'stateful',
            })

        # Apply SAML cookies if using SAML auth provider
        if self._auth_provider and self._auth_provider.auth_type == 'saml':
            self._apply_saml_cookies()

        # Configurable timeouts (seconds) - override via environment variables
        self.timeout_short = int(os.getenv('ADT_TIMEOUT_SHORT', '30'))
        self.timeout_default = int(os.getenv('ADT_TIMEOUT_DEFAULT', '60'))
        self.timeout_long = int(os.getenv('ADT_TIMEOUT_LONG', '120'))

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial delay in seconds
        self.retry_on_timeout = True
        self.retry_on_csrf_fail = True
        self.retry_on_5xx = True
        self.retry_on_lock_conflict = False  # Lock conflicts need manual intervention

        # Last lock CORRNR returned by SAP in the lock response XML.
        # SAP's CORRNR in the lock response is authoritative — it may differ from
        # the corrNr we sent on the LOCK request if stale E071 entries exist.
        self._last_lock_corrnr = None

        # IS_LINK_UP flag from lock response: 'X' means SAP already linked the object
        # to an S-type task under the workbench request. In that case CORRNR holds the
        # S-type task number, not the K-type workbench request — not a conflict.
        self._last_lock_is_link_up = None

        # Effective transport to use for the PUT after a successful lock.
        # Normally equals the user-requested transport, but when IS_LINK_UP=X the
        # S-type task number (CORRNR) should be passed to set_object_source().
        self._last_lock_effective_transport = None

    def _detect_system_type(self) -> str:
        """Detect if this is a SAP BTP Cloud or On-Premise system"""
        if not self.url:
            return 'onprem'

        url_lower = self.url.lower()

        # BTP Cloud indicators
        btp_indicators = [
            '.hana.ondemand.com',
            '.abap.eu10.hana.ondemand.com',
            '.abap.us10.hana.ondemand.com',
            '.abap.ap10.hana.ondemand.com',
            '.abap.jp10.hana.ondemand.com',
            '.authentication.',
            '.cloud.sap',           # S/4HANA Cloud
            '.s4hana.cloud.sap',    # S/4HANA Cloud specific
        ]

        for indicator in btp_indicators:
            if indicator in url_lower:
                return 'cloud'

        return 'onprem'

    def _create_auth_provider(self, auth_type_hint=None) -> Optional[IAuthProvider]:
        """
        Create the appropriate auth provider based on configuration

        Args:
            auth_type_hint: Optional hint for auth type ('basic', 'jwt', 'service_key', 'saml')

        Returns:
            IAuthProvider instance or None (falls back to basic auth)
        """
        if not AUTH_PROVIDERS_AVAILABLE:
            return None

        # Explicit auth type from environment
        env_auth_type = os.getenv('ADT_BTP_AUTH_TYPE', '').lower()

        # Service key path from environment
        service_key_path = os.getenv('ADT_BTP_SERVICE_KEY_PATH')

        # SAML cookies file path for session persistence
        saml_cookies_file = os.getenv('ADT_SAML_COOKIES_FILE')

        # OAuth2/IAS config (headless token auth for BTP Cloud)
        ias_token_url = os.getenv('ADT_IAS_TOKEN_URL', '')
        ias_client_id = os.getenv('ADT_IAS_CLIENT_ID', '')
        ias_client_secret = os.getenv('ADT_IAS_CLIENT_SECRET', '')
        has_ias_config = bool(ias_token_url and ias_client_id and ias_client_secret)

        # Determine auth type — priority: hint > explicit env > config presence > auto-detect
        if auth_type_hint:
            auth_type = auth_type_hint.lower()
        elif env_auth_type:
            auth_type = env_auth_type
        elif service_key_path:
            auth_type = 'service_key'
        elif saml_cookies_file:
            auth_type = 'saml'
        elif has_ias_config:
            auth_type = 'jwt'
        elif self._detect_system_type() == 'cloud':
            if detect_saml_system(self.url):
                auth_type = 'saml'
            else:
                auth_type = 'basic'
        else:
            auth_type = 'basic'

        try:
            if auth_type == 'service_key' and service_key_path:
                service_key_path_obj = Path(service_key_path)
                if not service_key_path_obj.is_absolute():
                    base_dir = conn_path.parent if conn_path else Path.cwd()
                    service_key_path_obj = base_dir / service_key_path
                if service_key_path_obj.exists():
                    return ServiceKeyAuthProvider(service_key_path=str(service_key_path_obj))
                if self.debug_enabled:
                    self._debug(f"[DEBUG] Service key file not found: {service_key_path_obj}, using basic auth")

            elif auth_type == 'jwt':
                # OAuth2 client credentials via IAS (headless, no browser needed)
                # Requires in .conn_adt:
                #   ADT_IAS_TOKEN_URL=https://<tenant>.accounts.ondemand.com/oauth2/token
                #   ADT_IAS_CLIENT_ID=<client_id>
                #   ADT_IAS_CLIENT_SECRET=<client_secret>
                if has_ias_config:
                    return JWTAuthProvider(
                        token_url=ias_token_url,
                        client_id=ias_client_id,
                        client_secret=ias_client_secret,
                    )
                if self.debug_enabled:
                    self._debug('[DEBUG] jwt auth requested but ADT_IAS_TOKEN_URL/CLIENT_ID/CLIENT_SECRET not set')

            elif auth_type == 'saml' and self.url:
                cookies_file = saml_cookies_file
                if not cookies_file:
                    explicit_dir = get_explicit_working_dir()
                    base_dir = explicit_dir if explicit_dir else Path.cwd()
                    cookies_file = base_dir / f".saml_cookies_{self.url.replace('https://', '').replace('http://', '').replace('/', '_')}.json"
                else:
                    cf_path = Path(cookies_file)
                    if not cf_path.is_absolute():
                        explicit_dir = get_explicit_working_dir()
                        base_dir = explicit_dir if explicit_dir else (conn_path.parent if conn_path and conn_path.exists() else Path.cwd())
                        cookies_file = str((base_dir / cf_path).resolve())
                return SAMLAuthProvider(
                    base_url=self.url,
                    username=self.user,
                    password=self.password,
                    cookies_file=str(cookies_file)
                )

            # Default to Basic Auth
            return BasicAuthProvider(
                username=self.user,
                password=self.password
            )

        except Exception as e:
            # If auth provider creation fails, log and fall back to None
            if self.debug_enabled:
                self._debug(f"[DEBUG] Auth provider creation failed: {e}, using basic auth")
            return None

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers from the auth provider

        Returns:
            Dict with Authorization header (and other auth-related headers)
            For SAML, returns empty dict (cookies handle auth)
        """
        if self._auth_provider:
            # Refresh credentials if needed (for JWT tokens)
            try:
                if not self._auth_provider.is_valid():
                    self._auth_provider.refresh_credentials()
                headers = self._auth_provider.get_auth_headers()
                # For SAML, don't add fallback auth - cookies handle it
                if self._auth_provider.auth_type == 'saml':
                    return {}
                return headers
            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] Auth provider error: {e}, falling back to basic auth")

        # Fallback to basic auth
        auth_string = f"{self.user}:{self.password}"
        auth_bytes = auth_string.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')
        return {'Authorization': f'Basic {base64_auth}'}

    def _get_auth_header(self):
        """Generate Basic Authentication header (legacy, for backward compatibility)"""
        headers = self._get_auth_headers()
        return headers.get('Authorization', '')

    def _debug(self, message: str) -> None:
        """Write debug message to log file if debug mode is enabled."""
        if not hasattr(self, 'debug_enabled') or not self.debug_enabled:
            return
        if not hasattr(self, 'debug_log_path') or not self.debug_log_path:
            return
        try:
            with open(self.debug_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"{message}\n")
        except Exception:
            pass  # Fail silently

    def _get_cookie_safe(self, name: str, default: str = '') -> str:
        """Safely get a cookie value without crashing on duplicates.

        After multiple stateful session calls, requests.cookiejar accumulates
        multiple entries for cookies like 'sap-contextid' with different path values.
        Calling .get(name) raises CookieConflictError. This method iterates
        and returns the first match.

        Args:
            name: Cookie name to retrieve
            default: Value to return if cookie not found

        Returns:
            Cookie value or default
        """
        for cookie in self.session.cookies:
            if cookie.name == name:
                return cookie.value
        return default

    def _set_cookie_dedup(self, name: str, value: str, domain: str = '', path: str = '/'):
        """Set a cookie with deduplication - removes existing entries first.

        Prevents CookieConflictError by clearing all existing entries with
        the given name before setting the new one.

        Args:
            name: Cookie name
            value: Cookie value
            domain: Cookie domain
            path: Cookie path (default: /)
        """
        # Clear all existing entries with this name
        # Note: cookiejar.clear() only accepts domain/path as kwargs, not name
        to_remove = [c for c in self.session.cookies
                     if c.name == name and (not domain or c.domain == domain) and c.path == path]
        for c in to_remove:
            self.session.cookies.clear(c.domain, c.path)
        # Set the new cookie
        self.session.cookies.set(name, value, domain=domain, path=path)

    def _update_cookies(self, response):
        """Merge response cookies into session to maintain SAP stateful session.

        Bug Fix: sap-contextid cookies accumulate with different path values,
        causing CookieConflictError. Use deduplication for known problematic cookies.
        """
        if response is None or not hasattr(response, 'cookies') or not response.cookies:
            return

        # Cookies that require deduplication (accumulate with different paths)
        dedup_cookies = {'sap-contextid'}

        for cookie in response.cookies:
            if cookie.name in dedup_cookies:
                # Use dedup to prevent CookieConflictError
                self._set_cookie_dedup(
                    cookie.name,
                    cookie.value,
                    domain=cookie.domain or '',
                    path=cookie.path or '/'
                )
            else:
                # Normal update for other cookies
                self.session.cookies.set(cookie.name, cookie.value,
                                         domain=cookie.domain or '',
                                         path=cookie.path or '/')

        # Keep self.cookies in sync for backward compatibility
        if self.cookies is None:
            self.cookies = response.cookies
        else:
            self.cookies.update(response.cookies)

    def _apply_saml_cookies(self):
        """Apply SAML session cookies from the auth provider to the requests session."""
        if not self._auth_provider or self._auth_provider.auth_type != 'saml':
            return

        if not self._auth_provider.is_valid():
            if self.debug_enabled:
                self._debug("[DEBUG] No valid SAML session cookies available")
            return

        # Apply cookies from the SAML provider to the session
        for cookie_dict in self._auth_provider.session_cookies:
            self.session.cookies.set(
                name=cookie_dict['name'],
                value=cookie_dict['value'],
                domain=cookie_dict.get('domain', ''),
                path=cookie_dict.get('path', '/'),
                secure=cookie_dict.get('secure', True)
            )

        if self.debug_enabled:
            session_id = self._auth_provider.get_sap_session_id()
            if session_id:
                self._debug(f"[DEBUG] Applied SAML session cookies: SAP_SESSIONID=...{session_id[-20:]}")

    def set_saml_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Set SAML session cookies from external source (e.g., browser automation).

        Args:
            cookies: Dict of cookie name -> value
        """
        if self._auth_provider and self._auth_provider.auth_type == 'saml':
            self._auth_provider.set_cookies(cookies)
            self._apply_saml_cookies()
        else:
            if self.debug_enabled:
                self._debug("[DEBUG] Cannot set SAML cookies: auth provider is not SAML type")

    def is_saml_session_valid(self) -> bool:
        """
        Check if SAML session is valid and has cookies.

        Returns:
            True if SAML session has valid cookies
        """
        return (
            self._auth_provider and
            self._auth_provider.auth_type == 'saml' and
            self._auth_provider.is_valid()
        )

    def _get_headers(self, accept_type="application/vnd.sap.adt.core.v1+xml", content_type=None):
        """Generate standard SAP ADT headers.

        For SAML sessions (BTP Cloud Public Edition), sap-client is intentionally
        omitted: the client is embedded in the session cookie (sap-usercontext) and
        the BTP reverse proxy ignores the sap-client URL/header parameter anyway.
        """
        is_saml = self._auth_provider and getattr(self._auth_provider, 'auth_type', '') == 'saml'
        headers = {
            'Authorization': self._get_auth_header(),
            'Accept': accept_type,
            'x-sap-adt-sessiontype': 'stateful'
        }
        if not is_saml:
            headers['sap-client'] = self.client

        if content_type:
            headers['Content-Type'] = content_type

        if self.csrf_token:
            headers['X-CSRF-Token'] = self.csrf_token

        return headers

    def _should_retry(self, response, attempt, operation=''):
        """Determine if a request should be retried based on response

        Args:
            response: requests.Response object
            attempt: Current attempt number
            operation: Description of operation for logging

        Returns:
            tuple: (should_retry: bool, reason: str)
        """
        if attempt >= self.max_retries:
            return False, "Max retries exceeded"

        status = response.status_code

        # Timeout errors - retry
        if status == 408 or status == 504:
            if self.retry_on_timeout:
                return True, f"Timeout (attempt {attempt + 1})"

        # CSRF token validation failed - retry with fresh token
        if 'CSRF token validation failed' in response.text:
            if self.retry_on_csrf_fail:
                return True, f"CSRF token expired (attempt {attempt + 1})"

        # 5xx server errors - retry with backoff
        if status >= 500:
            if self.retry_on_5xx:
                return True, f"Server error {status} (attempt {attempt + 1})"

        # Lock conflicts - don't retry (requires manual intervention)
        if 'is locked by' in response.text.lower() or 'lock' in response.text.lower():
            return False, "Object locked - manual intervention required"

        # Network/connection errors
        if hasattr(response, 'connection_error'):
            if self.retry_on_timeout:
                return True, f"Connection error (attempt {attempt + 1})"

        return False, None

    def _retry_request(self, request_func, operation='API request'):
        """Execute a request with retry logic for transient failures

        Args:
            request_func: Callable that performs the request
            operation: Description for logging

        Returns:
            requests.Response object

        Raises:
            SAPConnectionError: If connection fails after retries
            SAPADTError: If API returns non-retryable error
        """
    

        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = request_func()

                # Check if we should retry
                should_retry, reason = self._should_retry(response, attempt, operation)

                if should_retry:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"  [RETRY] {operation} - {reason}, retrying in {delay}s...")
                    time.sleep(delay)

                    # For CSRF failures, force-fetch a FRESH token (skip cache).
                    # A cached token within TTL can be stale server-side — this is
                    # exactly the 403 we just saw, so trusting the cache again
                    # would loop forever.
                    if 'CSRF' in reason:
                        self.fetch_csrf_token(force_refresh=True)

                    continue

                # Success or non-retryable error
                return response

            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries - 1 and self.retry_on_timeout:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"  [RETRY] {operation} - Timeout (attempt {attempt + 1}), retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    raise SAPConnectionError(
                        f"Connection timeout after {attempt + 1} attempts: {str(e)}",
                        url=self.url
                    )

            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1 and self.retry_on_timeout:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"  [RETRY] {operation} - Connection error (attempt {attempt + 1}), retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    raise SAPConnectionError(
                        f"Connection failed after {attempt + 1} attempts: {str(e)}",
                        url=self.url
                    )

        # Should not reach here, but just in case
        raise SAPConnectionError(
            f"Request failed after {self.max_retries} retries: {str(last_error) if last_error else 'Unknown error'}",
            url=self.url
        )

    def _csrf_cache_path(self) -> Optional[Path]:
        """Return path to on-disk CSRF token cache, or None if not determinable."""
        try:
            explicit_dir = get_explicit_working_dir()
            base_dir = explicit_dir if explicit_dir else conn_path.parent if conn_path and conn_path.exists() else None
            if base_dir:
                return Path(base_dir) / '.csrf_token.json'
        except Exception:
            pass
        return None

    def _load_csrf_from_cache(self) -> Optional[str]:
        """Load CSRF token from disk cache if still fresh (< 6h)."""
        cache_path = self._csrf_cache_path()
        if not cache_path or not cache_path.exists():
            return None
        try:
            data = json.loads(cache_path.read_text())
            age = time.time() - float(data.get('fetched_at', 0))
            if age < 21600:
                return data.get('token')
        except Exception:
            pass
        return None

    def _save_csrf_to_cache(self, token: str) -> None:
        """Persist CSRF token to disk cache with timestamp."""
        cache_path = self._csrf_cache_path()
        if not cache_path:
            return
        try:
            cache_path.write_text(json.dumps({'token': token, 'fetched_at': time.time()}))
        except Exception:
            pass

    def _invalidate_csrf_cache(self) -> None:
        """Delete on-disk CSRF cache (called on 403 CSRF failure)."""
        cache_path = self._csrf_cache_path()
        if cache_path and cache_path.exists():
            try:
                cache_path.unlink()
            except Exception:
                pass

    def fetch_csrf_token(self, force_refresh: bool = False):
        """Fetch CSRF token for write operations.

        For BTP Cloud (SAML) systems: uses /sap/bc/adt/compatibility/graph which
        requires authentication (unlike /discovery which is publicly accessible).
        Also checks/updates an on-disk cache so short-lived CLI processes reuse
        the same token across invocations (valid for the SAML session lifetime).

        Args:
            force_refresh: If True, skip the cache and fetch a new token from
                SAP. Callers that have just seen a 403 "CSRF token validation
                failed" response MUST pass True — a cached token within its TTL
                can still be invalid server-side (session killed, app server
                restart, etc.) and reading it back would cause the same 403 to
                repeat indefinitely.

        Raises:
            SAPConnectionError: If connection fails
            SAPAuthenticationError: If authentication fails
        """
        if force_refresh:
            self._invalidate_csrf_cache()
            self.csrf_token = None
        else:
            cached = self._load_csrf_from_cache()
            if cached:
                self.csrf_token = cached
                return cached

        is_saml = self._auth_provider and getattr(self._auth_provider, 'auth_type', '') == 'saml'
        csrf_endpoint = '/sap/bc/adt/compatibility/graph' if (is_saml or self._is_btp_cloud_url()) else '/sap/bc/adt/discovery'

        headers = self._get_headers()
        headers['X-CSRF-Token'] = 'Fetch'

        try:
            response = self.session.get(
                f"{self.url}{csrf_endpoint}",
                headers=headers,
                timeout=self.timeout_short
            )

            if response.status_code == 401 or response.status_code == 403:
                raise SAPAuthenticationError(
                    f"Authentication failed for {self.url}. Check credentials."
                )
            elif response.status_code >= 500:
                raise SAPConnectionError(
                    f"SAP server error at {self.url}",
                    url=self.url,
                    status_code=response.status_code
                )

            self.csrf_token = response.headers.get('X-CSRF-Token')
            self.cookies = response.cookies
            self.session.cookies.update(response.cookies)

            if not self.csrf_token:
                raise SAPConnectionError(
                    "Failed to obtain CSRF token from SAP",
                    url=f"{self.url}{csrf_endpoint}"
                )

            self._save_csrf_to_cache(self.csrf_token)
            return self.csrf_token

        except requests.exceptions.Timeout:
            raise SAPConnectionError(
                f"Connection timeout to {self.url}",
                url=self.url
            )
        except requests.exceptions.ConnectionError as e:
            raise SAPConnectionError(
                f"Cannot connect to SAP at {self.url}: {str(e)}",
                url=self.url
            )

    def _request_with_csrf_retry(self, method, url, headers=None, timeout=None, **kwargs):
        """Execute HTTP request with CSRF token management and automatic retry.

        Ensures a CSRF token exists before the request.  If the server responds
        with 403 + CSRF validation error, refreshes the token and retries once.

        Args:
            method: HTTP method string ('get', 'post', 'put', 'delete')
            url: Full URL to request
            headers: Pre-built headers dict (will be mutated on retry to
                     inject fresh CSRF token).  If *None*, ``_get_headers()``
                     is called automatically.
            timeout: Request timeout in seconds.  Defaults to
                     ``self.timeout_default``.
            **kwargs: Extra keyword arguments forwarded to
                      ``self.session.request()`` (e.g. ``data``, ``params``).

        Returns:
            ``requests.Response``
        """
        if not self.csrf_token:
            self.fetch_csrf_token()

        if headers is None:
            headers = self._get_headers()
        if timeout is None:
            timeout = self.timeout_default

        response = self.session.request(method, url, headers=headers, timeout=timeout, **kwargs)
        self._update_cookies(response)

        # Retry once on CSRF token expiry — self-healing: zehirli on-disk cache'i
        # temizle + SAP'den force-refresh (elle .csrf_token.json silmek gerekmesin).
        # 'CSRF token validation failed' (403) ya da X-CSRF-Token: Required başlığı.
        csrf_rejected = response.status_code == 403 and (
            'CSRF' in response.text
            or response.headers.get('x-csrf-token', '').lower() == 'required'
        )
        if csrf_rejected:
            if self.debug_enabled:
                self._debug(f"[DEBUG] CSRF token rejected on {method.upper()} {url}, force-refresh + retry")
            self.fetch_csrf_token(force_refresh=True)
            headers['X-CSRF-Token'] = self.csrf_token
            response = self.session.request(method, url, headers=headers, timeout=timeout, **kwargs)
            self._update_cookies(response)

        return response

    def _is_btp_cloud_url(self):
        """Return True if the configured URL looks like a BTP Cloud / S/4HANA Cloud Public Edition host."""
        if not self.url:
            return False
        url_lower = self.url.lower()
        return any(pattern in url_lower for pattern in (
            '.s4hana.cloud.sap',
            '.hana.ondemand.com',
        ))

    @staticmethod
    def _response_is_html(response):
        """Return True if the response body appears to be an HTML login/redirect page instead of ADT XML."""
        ctype = response.headers.get('Content-Type', '').lower()
        if 'html' in ctype:
            return True
        body_start = response.text[:200].lstrip().lower()
        return body_start.startswith('<html') or body_start.startswith('<!doctype')

    def check_logon(self):
        """Lightweight connectivity/auth check.

        Tries multiple ADT endpoints in order (some SAP systems don't have
        the discovery service fully activated). Returns success if any
        endpoint is reachable with valid auth.

        BTP Cloud note: /sap/bc/adt/discovery is publicly reachable and returns
        HTTP 200 even without authentication. This method detects HTML SAML-redirect
        responses and reports them as auth failures rather than false successes.

        Returns:
            dict: {success: bool, status_code: int|None, message: str, btp_cloud: bool}
        """
        is_btp = self._is_btp_cloud_url()

        # Define endpoints with their required Accept headers
        endpoints_to_try = [
            ("/sap/bc/adt/discovery", "application/atomsvc+xml"),
            ("/sap/bc/adt", "application/vnd.sap.adt.core.v1+xml"),
            ("/sap/bc/adt/repository/nodestructure", "application/vnd.sap.adt.core.v1+xml"),
        ]

        for endpoint, accept_type in endpoints_to_try:
            try:
                response = self.session.get(
                    f"{self.url}{endpoint}",
                    headers=self._get_headers(accept_type=accept_type),
                    timeout=self.timeout_short,
                    allow_redirects=False
                )

                # Detect SAML redirect HTML masquerading as a 200 success
                if response.status_code == 200 and self._response_is_html(response):
                    return {
                        'success': False,
                        'status_code': 200,
                        'btp_cloud': is_btp,
                        'message': (
                            'Received HTML login page instead of ADT XML. '
                            'This system requires SAML SSO authentication. '
                            'Run login_saml_sso.py first to obtain session cookies, '
                            'then set ADT_SAML_COOKIES_FILE in .conn_adt.'
                        )
                    }

                # Success — but for BTP Cloud /discovery warn it may be a public endpoint
                if response.status_code in (200, 302):
                    if is_btp and endpoint == '/sap/bc/adt/discovery':
                        # /discovery is publicly reachable on BTP Cloud — do a second
                        # authenticated probe to confirm real session
                        try:
                            probe = self.session.get(
                                f"{self.url}/sap/bc/adt/compatibility/graph",
                                headers=self._get_headers(accept_type='application/xml'),
                                timeout=self.timeout_short,
                                allow_redirects=False
                            )
                            if self._response_is_html(probe):
                                return {
                                    'success': False,
                                    'status_code': 200,
                                    'btp_cloud': True,
                                    'message': (
                                        '[BTP Cloud] /discovery returned 200 but authenticated ADT probe returned '
                                        'HTML login page. Basic Auth is NOT supported on this BTP Cloud system. '
                                        'Run login_saml_sso.py to obtain SAML session cookies, '
                                        'then set ADT_SAML_COOKIES_FILE=.saml_cookies.json in .conn_adt.'
                                    )
                                }
                        except Exception:
                            pass
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'btp_cloud': is_btp,
                        'message': f'Logon successful (endpoint: {endpoint})'
                    }

                # Auth failures are definitive
                if response.status_code in (401, 403):
                    return {
                        'success': False,
                        'status_code': response.status_code,
                        'btp_cloud': is_btp,
                        'message': 'Authentication failed (check ADT_SAP_USER/ADT_SAP_PASSWORD)'
                    }

                # 404/406 — try next endpoint
                if response.status_code in (404, 406):
                    continue

                continue

            except requests.exceptions.Timeout:
                return {'success': False, 'status_code': None, 'btp_cloud': is_btp,
                        'message': f'Connection timeout to {self.url}'}
            except requests.exceptions.ConnectionError as e:
                return {'success': False, 'status_code': None, 'btp_cloud': is_btp,
                        'message': f'Cannot connect to SAP at {self.url}: {str(e)}'}
            except Exception as e:
                return {'success': False, 'status_code': None, 'btp_cloud': is_btp,
                        'message': str(e)}

        return {
            'success': False,
            'status_code': None,
            'btp_cloud': is_btp,
            'message': 'No working ADT endpoints found'
        }

    def get_object_source(self, object_url, return_etag=False, version=None):
        """Get ABAP object source code

        Args:
            object_url: Object URL (e.g., '/sap/bc/adt/oo/classes/zcl_my_class')
            return_etag: If True, returns tuple (source, etag) for use with set_object_source
            version: Optional version to fetch — 'active' or 'inactive'.
                     When None, SAP returns the most recent version (inactive if one exists).
                     Use version='active' for post-activation verification (Bug 14 fix).

        Returns:
            str: ABAP source code (if return_etag=False)
            tuple: (source, etag) if return_etag=True - etag is required for PUT operations

        Raises:
            SAPADTObjectNotFoundError: If object doesn't exist
            SAPConnectionError: If connection fails
        """
        # Ensure /source/main suffix
        if not object_url.endswith('/source/main'):
            object_url = object_url.rstrip('/') + '/source/main'

        params = {}
        if version:
            params['version'] = version

        try:
            response = self.session.get(
                f"{self.url}{object_url}",
                headers=self._get_headers('text/plain'),
                params=params,
                timeout=self.timeout_short
            )

            if response.status_code == 404:
                object_name = object_url.split('/')[-2]
                raise SAPObjectNotFoundError(
                    message=f"Object not found: {object_name}",
                    status_code=404,
                    endpoint=object_url
                )
            elif response.status_code == 200:
                # Fix SAP's double line breaks (\r\r\n -> \n)
                source = response.text.replace('\r\r\n', '\n').replace('\r\n', '\n').replace('\r', '\n')

                if return_etag:
                    # ETag is REQUIRED for PUT operations (SAP checks If-Match header)
                    etag = response.headers.get('ETag') or response.headers.get('etag')
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] get_object_source - ETag from response: {etag}")
                    return source, etag
                return source
            else:
                raise SAPADTError(
                    f"Failed to get source for {object_url}",
                    status_code=response.status_code,
                    endpoint=object_url
                )

        except requests.exceptions.Timeout:
            raise SAPConnectionError(
                f"Timeout getting source from {object_url}",
                url=object_url
            )

    def get_object_revisions(self, object_url):
        """Get object revision history.

        Returns a list of revisions for an object, including version, date, author, etc.
        Based on abap-adt-api revisions functionality.

        Args:
            object_url: URL of the object (e.g., /sap/bc/adt/oo/classes/zcl_my_class)

        Returns:
            List of revision dicts with keys: uri, date, author, version, versionTitle
        """
        # First, get object structure to find revisions link
        try:
            headers = self._get_headers()
            headers['Accept'] = 'application/vnd.sap.adt.objectstructure+xml'

            response = self.session.get(
                f"{self.url}{object_url}",
                headers=headers,
                timeout=self.timeout_short
            )

            if response.status_code == 404:
                raise SAPObjectNotFoundError(
                    f"Object not found: {object_url}",
                    status_code=404,
                    endpoint=object_url
                )

            # Parse object structure to find revisions link
            # The revisions link has rel="http://www.sap.com/adt/relations/versions"
    
            revisions_link_match = re.search(
                r'<link[^>]*rel="http://www\.sap\.com/adt/relations/versions"[^>]*href="([^"]+)"',
                response.text
            )

            if not revisions_link_match:
                # Try alternate format
                revisions_link_match = re.search(
                    r'<link[^>]*href="([^"]+)"[^>]*rel="http://www\.sap\.com/adt/relations/versions"',
                    response.text
                )

            if not revisions_link_match:
                return []

            revisions_url = revisions_link_match.group(1)
            # Make it absolute if relative
            if revisions_url.startswith('/'):
                revisions_url = f"{self.url}{revisions_url}"

            # Get revisions feed
            headers = self._get_headers()
            headers['Accept'] = 'application/atom+xml;type=feed'

            response = self.session.get(
                revisions_url,
                headers=headers,
                timeout=self.timeout_short
            )

            if response.status_code != 200:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] get_object_revisions - failed with status {response.status_code}")
                return []

            # Parse Atom feed for revisions
            revisions = []
            entries = re.findall(r'<atom:entry>(.*?)</atom:entry>', response.text, re.DOTALL)

            for entry in entries:
                # Extract revision information from each entry
                uri_match = re.search(r'<atom:content[^>]*src="([^"]+)"', entry)
                version_match = re.search(r'<atom:link[^>]*type="application/vnd\.sap\.adt\.transportrequests\.v1\+xml"[^>]*adtcore:name="([^"]+)"', entry)
                if not version_match:
                    version_match = re.search(r'<atom:link[^>]*adtcore:name="([^"]+)"', entry)
                title_match = re.search(r'<atom:title>([^<]+)</atom:title>', entry)
                date_match = re.search(r'<atom:updated>([^<]+)</atom:updated>', entry)
                author_match = re.search(r'<atom:name>([^<]+)</atom:name>', entry)

                revision = {
                    'uri': uri_match.group(1) if uri_match else '',
                    'version': version_match.group(1) if version_match else '',
                    'versionTitle': title_match.group(1) if title_match else '',
                    'date': date_match.group(1) if date_match else '',
                    'author': author_match.group(1) if author_match else 'Unknown'
                }
                revisions.append(revision)

            return revisions

        except SAPObjectNotFoundError:
            raise
        except Exception as e:
            if self.debug_enabled:
                self._debug(f"[DEBUG] get_object_revisions - exception: {str(e)[:100]}")
            return []

    def set_object_source(self, object_url, source_code, lock_handle, transport=None, etag=None, max_retries=5):
        """Push ABAP object source code to SAP with fallback strategies.

        Note: Automatically retries with different transport parameter approaches.
        Different SAP versions may require corrNr as query param or X-sap-adt-transport header.
        Also handles implicit locking when explicit lock endpoints are not available.

        IMPORTANT: SAP requires If-Match header with ETag for PUT operations on classes.
        If etag is not provided, this method will fetch it automatically.

        Updated to match abap-adt-api pattern: lockHandle is passed as query parameter.
        """
        # Ensure /source/main suffix
        if not object_url.endswith('/source/main'):
            object_url = object_url.rstrip('/') + '/source/main'

        # CRITICAL: Get ETag if not provided - SAP requires If-Match header for class updates!
        # See CL_KU_CLASS_REST_HANDLER.put() which raises cx_adt_res_invalid_etag if missing
        # BUG FIX: When an inactive version exists (e.g. from interrupted push+activate),
        # SAP validates against the INACTIVE version's ETag, not the active one.
        # We must try the inactive ETag first, then fall back to active.
        if not etag:
            if self.debug_enabled:
                self._debug("[DEBUG] set_object_source - ETag not provided, fetching from server...")
            try:
                source_url_for_etag = object_url
                # Try inactive version first (has the most recent ETag when stale inactive exists)
                try:
                    resp_inactive = self.session.get(
                        f"{self.url}{source_url_for_etag}",
                        headers=self._get_headers('text/plain'),
                        params={'version': 'inactive'},
                        timeout=self.timeout_short
                    )
                    if resp_inactive.status_code == 200:
                        inactive_etag = resp_inactive.headers.get('ETag') or resp_inactive.headers.get('etag')
                        if inactive_etag:
                            if self.debug_enabled:
                                self._debug(f"[DEBUG] set_object_source - Inactive ETag found: {inactive_etag}")
                            # Also get active ETag to compare
                            resp_active = self.session.get(
                                f"{self.url}{source_url_for_etag}",
                                headers=self._get_headers('text/plain'),
                                params={'version': 'active'},
                                timeout=self.timeout_short
                            )
                            active_etag = None
                            if resp_active.status_code == 200:
                                active_etag = resp_active.headers.get('ETag') or resp_active.headers.get('etag')
                            if active_etag and inactive_etag != active_etag:
                                if self.debug_enabled:
                                    self._debug(f"[DEBUG] set_object_source - STALE INACTIVE detected! "
                                                f"Active ETag: {active_etag}, Inactive ETag: {inactive_etag}. Using inactive.")
                                etag = inactive_etag
                            else:
                                etag = inactive_etag  # Same or only inactive exists
                except Exception as e_inactive:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] set_object_source - Inactive version check failed: {str(e_inactive)[:100]}")
                # Fall back to active version ETag if inactive didn't yield one
                if not etag:
                    base_url = object_url.replace('/source/main', '')
                    _, etag = self.get_object_source(base_url, return_etag=True)
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_object_source - Final ETag for If-Match: {etag}")
            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_object_source - Failed to get ETag: {str(e)[:100]}")
                # Continue without ETag - some systems may not require it

        # Define different transport approaches to try
        # Format: (use_header, use_param, description)
        transport_approaches = [
            (True, False, 'X-sap-adt-transport header only'),
            (False, True, 'corrNr query parameter only'),
            (True, True, 'both header and parameter'),
            (False, False, 'no transport (object may not need it)'),
        ]

        # Try each transport approach
        for attempt_num, (use_header, use_param, desc) in enumerate(transport_approaches, 1):
            if self.debug_enabled:
                self._debug(f"[DEBUG] set_object_source - approach {attempt_num}: {desc}")

            headers = self._get_headers('text/plain', 'text/plain')

            # CRITICAL: Add If-Match header with ETag - required by SAP for class updates!
            if etag:
                headers['If-Match'] = etag
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_object_source - Adding If-Match header: {etag}")

            # Build query parameters - lockHandle is always passed as query param (abap-adt-api pattern)
            params = {}

            # Add lock handle as query parameter (abap-adt-api pattern)
            # This is the CORRECT way - NOT as a header!
            if lock_handle and lock_handle not in ['NO_LOCK_SUPPORT', 'IMPLICIT_LOCK', None, '']:
                params['lockHandle'] = lock_handle

            # Set transport parameters
            if transport:
                if use_header:
                    headers['X-sap-adt-transport'] = transport
                if use_param:
                    params['corrNr'] = transport

            if self.debug_enabled and lock_handle:
                self._debug(f"[DEBUG] set_object_source - using lockHandle as query param: {lock_handle[:50]}...")

            response = self._request_with_csrf_retry(
                'put', f"{self.url}{object_url}",
                headers=headers,
                data=source_code.encode('utf-8'),
                params=params,
            )

            # Check for 423 lock error when we have NO_LOCK_SUPPORT
            if (response.status_code == 423 and
                lock_handle == 'NO_LOCK_SUPPORT' and
                ('lockHandle' in response.text or 'invalid lock' in response.text.lower())):

                if self.debug_enabled:
                    self._debug("[DEBUG] set_object_source - Got 423 lock error with NO_LOCK_SUPPORT")
                    self._debug("[DEBUG] set_object_source - SAP requires explicit lock but endpoint unavailable")
                    self._debug("[DEBUG] set_object_source - This is a fundamental limitation, cannot proceed via ADT")

                # This is a hard error - SAP requires locks but we can't get them via ADT
                raise SAPLockError(
                    f"Cannot edit object via ADT on this SAP system. "
                    f"The system requires explicit locking but doesn't support ADT lock endpoints. "
                    f"Please use SAP GUI (SE24/SE80) to edit this object. "
                    f"Error: {response.text[:200]}",
                    status_code=response.status_code,
                    response_text=response.text[:500]
                )

            if response.status_code in [200, 201, 204]:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_object_source - SUCCESS with approach {attempt_num}")
                return True

            # Handle 412 Precondition Failed (ETag mismatch) - retry with inactive ETag
            if response.status_code == 412:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_object_source - 412 ETag mismatch, attempting inactive ETag retry")
                try:
                    resp_inact = self.session.get(
                        f"{self.url}{object_url}",
                        headers=self._get_headers('text/plain'),
                        params={'version': 'inactive'},
                        timeout=self.timeout_short
                    )
                    if resp_inact.status_code == 200:
                        retry_etag = resp_inact.headers.get('ETag') or resp_inact.headers.get('etag')
                        if retry_etag and retry_etag != etag:
                            if self.debug_enabled:
                                self._debug(f"[DEBUG] set_object_source - Retrying with inactive ETag: {retry_etag}")
                            headers['If-Match'] = retry_etag
                            etag = retry_etag  # Update for subsequent attempts
                            retry_resp = self._request_with_csrf_retry(
                                'put', f"{self.url}{object_url}",
                                headers=headers,
                                data=source_code.encode('utf-8'),
                                params=params,
                            )
                            if retry_resp.status_code in [200, 201, 204]:
                                if self.debug_enabled:
                                    self._debug("[DEBUG] set_object_source - SUCCESS with inactive ETag retry")
                                return True
                except Exception as e_retry:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] set_object_source - 412 retry failed: {str(e_retry)[:100]}")

            # If this approach failed with specific parameter error, try next approach
            if 'Parameter' in response.text and 'could not be found' in response.text:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_object_source - parameter error with approach {attempt_num}, trying next")
                continue  # Try next approach

            # For other errors, check if we should try next approach or fail
            if attempt_num == len(transport_approaches):
                # Last attempt failed
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_object_source - All {len(transport_approaches)} transport approaches failed")
                # ADT hata yanıtı ÇOK-MESAJLI XML olabilir (headline + satır-numaralı asıl
                # hata). Eskiden response.text[:300] ile kesiliyordu → gerçek (line-no) hata
                # gizleniyordu (ZSD001 C4 patinajı: "unknown comments" headline'dı, asıl hata
                # truncate'liydi). Artık TAM yanıt yakalanır. (Fix 2026-06-15, kullanıcı içgörüsü.)
                _full = response.text or ''
                print(f"[set_object_source] FULL ERROR RESPONSE ({response.status_code}), "
                      f"{len(_full)} chars:\n{_full}")
                raise SAPADTError(
                    f"Failed to set source after {len(transport_approaches)} attempts. "
                    f"Response ({response.status_code}), FULL:\n{_full}",
                    status_code=response.status_code,
                    response_text=_full
                )

        return True

    def set_include_source(self, include_url, source_code, lock_handle, transport=None, etag=None):
        """PUT source code directly to a method-level include URL.

        Unlike set_object_source(), this method does NOT append '/source/main'.
        Use for method-include fallback when activation fails with "Implementation missing".

        The include_url should point to the specific include endpoint, e.g.:
            /sap/bc/adt/oo/classes/ZCL_FOO/includes/implementations/MY_METHOD

        Args:
            include_url: ADT path to the include (no base URL, no /source/main suffix)
            source_code: Method body to PUT (full METHOD...ENDMETHOD block)
            lock_handle: Active lock handle from lock_object()
            transport: Transport corrNr (same transport as for source/main PUT)
            etag: If-Match ETag; fetched automatically from include URL if None
        """
        # Auto-fetch ETag from the include URL if not provided
        if not etag:
            try:
                resp = self.session.get(
                    f"{self.url}{include_url}",
                    headers=self._get_headers('text/plain'),
                    timeout=self.timeout_short
                )
                if resp.status_code == 200:
                    etag = resp.headers.get('ETag') or resp.headers.get('etag')
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] set_include_source - Fetched ETag: {etag}")
            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] set_include_source - ETag fetch failed: {str(e)[:80]}")

        headers = self._get_headers('text/plain', 'text/plain; charset=utf-8')
        headers['X-sap-adt-sessiontype'] = 'stateful'
        if etag:
            headers['If-Match'] = etag

        params = {'lockHandle': lock_handle}
        if transport:
            params['corrNr'] = transport

        if self.debug_enabled:
            self._debug(f"[DEBUG] set_include_source - PUT {include_url}, transport={transport}, etag={etag}")

        response = self.session.put(
            f"{self.url}{include_url}",
            headers=headers,
            params=params,
            data=source_code.encode('utf-8'),
            timeout=self.timeout_default
        )
        self._update_cookies(response)

        if response.status_code in (200, 204):
            return True
        else:
            raise SAPADTError(
                f"Method include PUT failed ({response.status_code}): {response.text[:300]}",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

    def _extract_lock_handle(self, response):
        """Extract lock handle from a lock response (header or XML body).

        Args:
            response: requests.Response from a lock endpoint

        Returns:
            Lock handle string or None
        """
        # Priority 1: Check response header
        lock_handle = response.headers.get('X-sap-adt-lockHandle')
        if lock_handle:
            return lock_handle

        # Priority 2: Regex on XML body
        match = re.search(r'<LOCK_HANDLE>([^<]+)</LOCK_HANDLE>', response.text)
        if match:
            return match.group(1)

        # Priority 3: Full XML parse
        try:
            root = ET.fromstring(response.text)
            for elem in root.iter():
                if 'LOCK_HANDLE' in elem.tag and elem.text:
                    return elem.text
        except ET.ParseError:
            pass

        return None

    def _extract_lock_xml_field(self, response, field_name):
        """Extract a named field from a lock response XML body (e.g. CORRNR, LOCK_HANDLE).

        Args:
            response: requests.Response from a lock endpoint
            field_name: XML element name to extract (e.g. 'CORRNR')

        Returns:
            Field value string or None
        """
        # Regex on XML body (fast path)
        match = re.search(rf'<{re.escape(field_name)}>([^<]+)</{re.escape(field_name)}>', response.text)
        if match:
            return match.group(1).strip()

        # Full XML parse (handles namespace prefixes)
        try:
            root = ET.fromstring(response.text)
            for elem in root.iter():
                local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if local == field_name and elem.text:
                    return elem.text.strip()
        except ET.ParseError:
            pass

        return None

    def _verify_and_return_lock(self, response, object_url, transport, label=''):
        """Extract lock handle + CORRNR + IS_LINK_UP from a successful (200) lock response.

        Stores:
          self._last_lock_corrnr          — SAP-assigned transport (authoritative)
          self._last_lock_is_link_up      — 'X' if object is in a FOREIGN transport
          self._last_lock_effective_transport — transport caller should use for PUT

        CORRNR semantics (confirmed from SAP source: CL_ADT_CTS_MANAGEMENT.get_transport_info):
          - SAP always returns the K-type WORKBENCH REQUEST number (e.g. FIDK901507)
          - NOT the S-type child task (SAP handles that internally)
          - In the normal case CORRNR == the transport we requested

        IS_LINK_UP semantics (confirmed from SAP source: is_obj_recorded_in_foreign_req):
          - IS_LINK_UP='X' means the object is recorded in a FOREIGN transport request
            where the current user has NO task (another developer's transport)
          - IS_LINK_UP=empty means the current user HAS a task in the transport (safe)
          - IMPORTANT: IS_LINK_UP='X' is NOT "S-type child task" — that was incorrect
            (S-type tasks return K-type in CORRNR which always matches, IS_LINK_UP=empty)

        If CORRNR != transport:
          - IS_LINK_UP='X' → FOREIGN transport (another developer's) → fail fast
          - IS_LINK_UP=empty → different transport of the same user (stale E071) → fail fast

        Returns:
            lock_handle string, or 'IMPLICIT_LOCK' when SAP omits it.
        """
        lock_handle = self._extract_lock_handle(response)
        corrnr_actual = self._extract_lock_xml_field(response, 'CORRNR')
        is_link_up = self._extract_lock_xml_field(response, 'IS_LINK_UP')

        self._last_lock_corrnr = corrnr_actual
        self._last_lock_is_link_up = is_link_up
        self._last_lock_effective_transport = corrnr_actual or transport

        prefix = f"[DEBUG] lock_object{(' ' + label) if label else ''}"
        if self.debug_enabled:
            self._debug(
                f"{prefix} - lock_handle: {(lock_handle or '')[:50]}... "
                f"CORRNR: {corrnr_actual}, IS_LINK_UP: {is_link_up}"
            )

        if corrnr_actual and transport and corrnr_actual.upper() != transport.upper():
            # CORRNR mismatch: SAP assigned a different transport than requested.
            # Fail fast in both cases — no PUT attempted, no ghost E071 entry written.
            print(f"\n[TRANSPORT MISMATCH] SAP assigned transport: {corrnr_actual}")
            print(f"[TRANSPORT MISMATCH] Requested transport  : {transport}")
            try:
                actual_handle = lock_handle or 'IMPLICIT_LOCK'
                if actual_handle and actual_handle != 'IMPLICIT_LOCK':
                    self.unlock_object(object_url, actual_handle)
                    print(f"[OK] Lock released to prevent ghost transport.")
            except Exception:
                print(f"[WARNING] Could not release lock — use SM12 to clear it manually.")

            if is_link_up == 'X':
                # IS_LINK_UP='X': object is in a FOREIGN transport — another developer's.
                # Source: CL_ADT_CTS_MANAGEMENT.is_obj_recorded_in_foreign_req() returns
                # abap_true when current user has NO task in the transport holding the lock.
                raise SAPLockError(
                    f"Object is recorded in FOREIGN transport {corrnr_actual} (IS_LINK_UP=X).\n\n"
                    f"This transport belongs to another developer — pushing to it would\n"
                    f"inject your changes without the owner's knowledge.\n\n"
                    f"Fix:\n"
                    f"  1. SE01/SE09 → open transport {corrnr_actual} → remove object entry\n"
                    f"     (only if authorised — coordinate with the transport owner)\n"
                    f"  2. SM12 → release enqueue lock for this object if any\n"
                    f"  3. Retry the push with transport {transport}\n\n"
                    f"[ACTION REQUIRED] STOP. Do NOT retry automatically. Report to user.",
                    status_code=409,
                    response_text=response.text[:500]
                )
            else:
                # IS_LINK_UP=empty: object is in a DIFFERENT transport of the same user.
                # (Stale E071 entry from an older workbench request, or user has
                #  multiple active transports for the same package/layer.)
                raise SAPLockError(
                    f"SAP assigned transport {corrnr_actual} but {transport} was requested.\n\n"
                    f"A stale E071 entry or transport layer mismatch caused SAP to override\n"
                    f"the corrNr hint. The object is in your own transport {corrnr_actual}.\n\n"
                    f"Fix:\n"
                    f"  1. SE01/SE09 → open transport {corrnr_actual} → move/delete object entry\n"
                    f"  2. SM12 → release enqueue lock for this object\n"
                    f"  3. Retry the push with transport {transport}\n\n"
                    f"  Or: use transport {corrnr_actual} instead of {transport}.\n"
                    f"  Diagnostic: SELECT STRKORR FROM E070 WHERE TRKORR = '{corrnr_actual}'\n"
                    f"  (STRKORR shows parent K-type request if {corrnr_actual} is a task)",
                    status_code=409,
                    response_text=response.text[:500]
                )
        else:
            if corrnr_actual:
                print(f"      [INFO] SAP-assigned transport (CORRNR): {corrnr_actual}")
            else:
                print(f"      [INFO] SAP did not return CORRNR in lock response (cannot verify transport assignment)")

        return lock_handle or 'IMPLICIT_LOCK'

    def lock_object(self, object_url, access_mode='MODIFY', transport=None, max_attempts=4, allow_no_transport=False):
        """
        Lock an ABAP object with multiple fallback strategies.

        Tries different locking mechanisms in order:
        1. Standard REST lock endpoint (/sap/bc/adt/locks)
        2. Core object lock endpoint (/sap/bc/adt/core/objectlock)
        3. Object-specific lock (via object URL with _action=LOCK)
        4. Implicit locking (no explicit lock, relies on stateful session)
        5. Return 'NO_LOCK_SUPPORT' if all attempts fail

        Note: Some SAP systems may not support the explicit lock endpoint.
        In those cases, this function returns a placeholder lock handle
        and operations proceed without explicit locking.

        IMPORTANT: Always pass the target transport so SAP CTS registers the lock
        under the correct transport (corrNr). Without corrNr, SAP auto-creates a
        new transport which causes 409 deadlock conflicts on subsequent pushes.

        Args:
            object_url: URL of the object to lock
            access_mode: 'MODIFY' or 'READ'
            transport: Transport request number (corrNr). If provided, the lock is
                       registered under this transport, preventing SAP from creating
                       a ghost transport automatically.
            max_attempts: Maximum number of lock strategies to try

        Returns:
            Lock handle string, or 'NO_LOCK_SUPPORT' if locks not available
        """
        if self.debug_enabled:
            self._debug(f"[DEBUG] lock_object - URL: {object_url}, access_mode: {access_mode}")

        # WORKFLOW GUARD: Hard stop when transport is missing.
        # Without corrNr, SAP CTS auto-creates a ghost transport during lock which
        # causes 409 deadlocks on the subsequent set_object_source()/delete call.
        # allow_no_transport=True is reserved for cleanup-only callers (clear_enqueue_lock)
        # that do lock→unlock with no write in between and therefore won't trigger a CTS entry.
        if not transport and not allow_no_transport:
            raise SAPADTError(
                "[TRANSPORT REQUIRED] lock_object() must be called with a transport (corrNr).\n"
                "\n"
                "Without corrNr, SAP CTS auto-creates a ghost transport and registers the lock\n"
                "under it. The subsequent set_object_source() with the real transport gets 409.\n"
                "\n"
                "Fix — resolve transport BEFORE locking, then pass it:\n"
                "    transport = 'TRXXXXXX'\n"
                "    lock_handle = client.lock_object(object_url, transport=transport)\n"
                "\n"
                "See references/WORKFLOWS.md -> Low-Level Pattern for the full correct template."
            )

        # Ensure we have CSRF token
        if not self.csrf_token:
            if self.debug_enabled:
                self._debug("[DEBUG] lock_object - fetching CSRF token")
            self.fetch_csrf_token()

        # Build lock request body (used for strategies 1-3)
        lock_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:objectReference adtcore:uri="{object_url}" adtcore:name=""/>
</adtcore:objectReferences>'''

        # Define lock strategies to try in order
        # Format: (endpoint, use_query_param, description)
        lock_strategies = [
            ('/sap/bc/adt/locks', True, 'Standard REST lock endpoint'),
            ('/sap/bc/adt/core/objectlock', True, 'Core object lock endpoint'),
            (None, False, 'Object-specific lock via URL'),
        ]

        # Try each lock strategy
        for attempt_num, (endpoint, use_query_param, description) in enumerate(lock_strategies, 1):
            if self.debug_enabled:
                self._debug(f"[DEBUG] lock_object attempt {attempt_num}/{len(lock_strategies)}: {description}")

            try:
                if endpoint:
                    # Strategy 1 & 2: REST endpoint based locking
                    headers = self._get_headers(
                        'application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.lock.result;q=0.8, application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.lock.result2;q=0.9',
                        'application/xml'
                    )
                    headers['X-sap-adt-sessiontype'] = 'stateful'

                    params = {}
                    if use_query_param:
                        params['_action'] = 'LOCK'
                        params['accessMode'] = access_mode
                        if transport:
                            params['corrNr'] = transport

                    response = self.session.post(
                        f"{self.url}{endpoint}",
                        headers=headers,
                        data=lock_body,
                        params=params,
                        timeout=self.timeout_short
                    )
                    self._update_cookies(response)
                else:
                    # Strategy 3: Object-specific lock via object URL with _action=LOCK
                    # This matches abap-adt-api pattern: POST to object URL with _action=LOCK
                    # NO body, just query parameters
                    headers = self._get_headers()
                    # Use the correct Accept header for lock response (abap-adt-api pattern)
                    headers['Accept'] = 'application/*,application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.lock.result'
                    headers['X-sap-adt-sessiontype'] = 'stateful'

                    lock_params = {'_action': 'LOCK', 'accessMode': access_mode}
                    if transport:
                        lock_params['corrNr'] = transport
                    response = self.session.post(
                        f"{self.url}{object_url}",
                        headers=headers,
                        params=lock_params,
                        timeout=self.timeout_short
                    )
                    self._update_cookies(response)

                if self.debug_enabled:
                    self._debug(f"[DEBUG] lock_object attempt {attempt_num} - status: {response.status_code}")

                # Success!
                if response.status_code == 200:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] lock_object - locked successfully with strategy {attempt_num}")

                    return self._verify_and_return_lock(response, object_url, transport, label=f'strategy {attempt_num}')

                # 404 - This endpoint doesn't exist, try next strategy
                elif response.status_code == 404:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] lock_object attempt {attempt_num} - endpoint not found (404), trying next strategy")
                    continue

                # 403 - CSRF token might be expired, refresh and retry this strategy once
                elif response.status_code == 403 and 'CSRF' in response.text:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] lock_object attempt {attempt_num} - CSRF error, refreshing token and retrying")
                    try:
                        # Bug 18a: force-refresh the token (bypasses the disk cache
                        # which can hold a stale-but-in-TTL token). Also update the
                        # `headers` dict that was built before the fetch since it
                        # still carries the old `X-CSRF-Token`.
                        self.fetch_csrf_token(force_refresh=True)
                        headers['X-CSRF-Token'] = self.csrf_token

                        # Retry the same strategy with fresh token
                        if endpoint:
                            retry_params = {'_action': 'LOCK', 'accessMode': access_mode}
                            if transport:
                                retry_params['corrNr'] = transport
                            response = self.session.post(
                                f"{self.url}{endpoint}",
                                headers=headers,
                                data=lock_body,
                                params=retry_params,
                                timeout=self.timeout_short
                            )
                            self._update_cookies(response)
                        else:
                            # Strategy 3: object-specific lock (no body) — rebuild headers
                            # so they pick up the freshly fetched token via _get_headers()
                            headers = self._get_headers()
                            headers['Accept'] = 'application/*,application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.lock.result'
                            headers['X-sap-adt-sessiontype'] = 'stateful'
                            retry_params = {'_action': 'LOCK', 'accessMode': access_mode}
                            if transport:
                                retry_params['corrNr'] = transport
                            response = self.session.post(
                                f"{self.url}{object_url}",
                                headers=headers,
                                params=retry_params,
                                timeout=self.timeout_short
                            )
                            self._update_cookies(response)

                        # Check if retry succeeded
                        if response.status_code == 200:
                            if self.debug_enabled:
                                self._debug(f"[DEBUG] lock_object - locked successfully after CSRF refresh with strategy {attempt_num}")

                            return self._verify_and_return_lock(response, object_url, transport, label=f'strategy {attempt_num} after CSRF refresh')
                        else:
                            if self.debug_enabled:
                                self._debug(f"[DEBUG] lock_object attempt {attempt_num} - retry after CSRF refresh failed with status {response.status_code}")
                            continue
                    except Exception as retry_ex:
                        if self.debug_enabled:
                            self._debug(f"[DEBUG] lock_object attempt {attempt_num} - CSRF refresh retry failed: {str(retry_ex)[:50]}")
                        continue

                # Handle 403 errors - could be lock conflict or stale lock from same user
                elif response.status_code == 403:
                    response_text = response.text if response.text else ''

                    # Try to extract lock owner from the 403 response
                    # SAP returns: <message>User X is already editing object Y</message>
                    # Also check T100KEY-V1 for the user
            
                    lock_owner = None
                    current_user = self.user.upper() if hasattr(self, 'user') and self.user else ''

                    # Try multiple patterns to find the lock owner
                    owner_patterns = [
                        r'<T100KEY-V1>\s*([A-Z0-9_]+)\s*</T100KEY-V1>',
                        r'user\s+([A-Z0-9_]+)\s+is\s+already\s+editing',
                        r'kullanıcı\s+([A-Z0-9_]+)\s+zaten',
                        r'benutzer\s+([A-Z0-9_]+)\s+bearbeitet',
                        r'utilisateur\s+([A-Z0-9_]+)\s+modifie',
                    ]

                    for pattern in owner_patterns:
                        match = re.search(pattern, response_text, re.IGNORECASE)
                        if match:
                            lock_owner = match.group(1).upper()
                            break

                    if self.debug_enabled:
                        self._debug(f"[DEBUG] lock_object attempt {attempt_num} - 403 detected, lock_owner={lock_owner}, current_user={current_user}")

                    # Check if the lock is held by the SAME user (stale lock from previous session)
                    if lock_owner and lock_owner == current_user:
                        if self.debug_enabled:
                            self._debug("[DEBUG] lock_object - Same user has stale lock")

                        # Try to recover from stale lock
                        try:
                            # Try object-specific unlock
                            unlock_headers = self._get_headers()
                            unlock_headers['Accept'] = 'application/xml'
                            unlock_headers['X-sap-adt-sessiontype'] = 'stateful'

                            unlock_resp = self.session.post(
                                f"{self.url}{object_url}",
                                headers=unlock_headers,
                                params={'_action': 'UNLOCK', 'accessMode': access_mode},
                                timeout=self.timeout_short
                            )
                            self._update_cookies(unlock_resp)

                            if self.debug_enabled:
                                self._debug(f"[DEBUG] lock_object - Unlock response: {unlock_resp.status_code}")

                            # Add a small delay to allow SAP to process the unlock
                        
                            time.sleep(0.5)

                            # Try lock again after unlock
                            self.fetch_csrf_token()
                            headers = self._get_headers()
                            headers['Accept'] = 'application/*,application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.lock.result'
                            headers['X-sap-adt-sessiontype'] = 'stateful'

                            relock_params = {'_action': 'LOCK', 'accessMode': access_mode}
                            if transport:
                                relock_params['corrNr'] = transport
                            response = self.session.post(
                                f"{self.url}{object_url}",
                                headers=headers,
                                params=relock_params,
                                timeout=self.timeout_short
                            )
                            self._update_cookies(response)

                            if response.status_code == 200:
                                if self.debug_enabled:
                                    self._debug(f"[DEBUG] lock_object - Successfully recovered from stale lock")
                                return self._verify_and_return_lock(response, object_url, transport, label='after stale lock recovery')

                        except Exception as unlock_ex:
                            if self.debug_enabled:
                                self._debug(f"[DEBUG] lock_object - Unlock/retry failed: {str(unlock_ex)[:50]}")

                        # Unlock failed, but SAP allows same-user edits even with stale enqueue lock
                        # Return NO_LOCK_SUPPORT and let PUT proceed - it should work
                        if self.debug_enabled:
                            self._debug("[DEBUG] lock_object - Stale lock from same user, returning NO_LOCK_SUPPORT (PUT will likely work)")
                        return 'NO_LOCK_SUPPORT'

                    # If DIFFERENT user has the lock, raise exception
                    if lock_owner:
                        raise SAPLockError(
                            f"Object is locked by user '{lock_owner}'.\n\n"
                            f"Options:\n"
                            f"  1. Wait for them to finish editing\n"
                            f"  2. Ask {lock_owner} to close their SAP session\n"
                            f"  3. Use SM12 to release lock 'EADT_LOCK' (if you have authorization)\n\n"
                            f"Object: {object_url.split('/')[-1]}",
                            lock_owner=lock_owner,
                            status_code=403,
                            response_text=response_text[:500]
                        )

                    # Other 403 - authorization issue, try next strategy
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] lock_object attempt {attempt_num} - 403 authorization issue, trying next strategy")
                    continue

                # 409 - Transport conflict: object locked under a different transport
                elif response.status_code == 409:
                    response_text = response.text if response.text else ''
                    # Try to extract the conflicting transport number from XML
                    conflict_transport = None
                    import re as _re
                    t_match = _re.search(r'transport\s+([A-Z]{3}\d+K\d+|[A-Z0-9]{8,})', response_text, _re.IGNORECASE)
                    if t_match:
                        conflict_transport = t_match.group(1)
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] lock_object - 409 transport conflict, conflicting transport: {conflict_transport}")
                    msg = (
                        f"Object is locked under transport {conflict_transport or 'unknown'} "
                        f"(target was {transport or 'not specified'}).\n\n"
                        f"This usually means a previous push locked the object under a different transport.\n\n"
                        f"Fix:\n"
                        f"  1. Go to SM12 -> delete the enqueue lock for this object\n"
                        f"  2. Go to SE01/SE09 -> find transport {conflict_transport or conflict_transport} -> move object to {transport or 'your target transport'}\n"
                        f"  3. Retry the push"
                    )
                    raise SAPLockError(msg, status_code=409, response_text=response_text[:500])

                # Other errors - try next strategy
                else:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] lock_object attempt {attempt_num} - failed with status {response.status_code}")
                    # Try next strategy
                    continue

            except SAPLockError:
                raise
            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] lock_object attempt {attempt_num} - exception: {str(e)[:100]}")
                # Check if this is our custom lock conflict exception
                if 'locked by user' in str(e):
                    raise  # Re-raise lock conflict exceptions
                # Try next strategy
                continue

        # All REST-based lock strategies failed
        # Only return NO_LOCK_SUPPORT if we got 404 (endpoint not found)
        # If we got other errors, the lock endpoint exists but has issues
        if self.debug_enabled:
            self._debug("[DEBUG] lock_object - All REST lock strategies failed")

        # Return placeholder - operations will proceed without explicit locking
        if self.debug_enabled:
            self._debug("[DEBUG] lock_object - returning NO_LOCK_SUPPORT (will try implicit locking)")
        return 'NO_LOCK_SUPPORT'

    def unlock_object(self, object_url, lock_handle):
        """
        Unlock an ABAP object with fallback strategies.

        Updated to match abap-adt-api pattern: POST to object URL with _action=UNLOCK
        and URL-encoded lockHandle parameter.

        Args:
            object_url: URL of the object to unlock
            lock_handle: Lock handle from lock_object()

        Returns:
            True if unlocked successfully or no lock was held
        """
        # Skip if locks not supported on this system or implicit lock
        if lock_handle in ['NO_LOCK_SUPPORT', 'IMPLICIT_LOCK', None, '']:
            if self.debug_enabled:
                self._debug(f"[DEBUG] unlock_object - skipping unlock for lock_handle: {lock_handle}")
            return True

        # Strategy 1: Try object-specific unlock (abap-adt-api pattern)
        # POST to object URL with _action=UNLOCK and URL-encoded lockHandle
        if self.debug_enabled:
            self._debug(f"[DEBUG] unlock_object - trying object-specific unlock (abap-adt-api pattern)")

        try:
            from urllib.parse import quote

            headers = self._get_headers()
            headers['X-sap-adt-sessiontype'] = 'stateful'

            # URL-encode the lock handle (abap-adt-api pattern)
            response = self.session.post(
                f"{self.url}{object_url}",
                headers=headers,
                params={'_action': 'UNLOCK', 'lockHandle': quote(lock_handle)},
                timeout=self.timeout_short
            )
            self._update_cookies(response)

            if response.status_code in [200, 204]:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] unlock_object - unlocked successfully via object-specific unlock")
                return True
            else:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] unlock_object - object-specific unlock failed: {response.status_code}")
        except Exception as e:
            if self.debug_enabled:
                self._debug(f"[DEBUG] unlock_object - object-specific unlock exception: {str(e)[:100]}")

        # Strategy 2 & 3: Fallback to REST endpoints (legacy)
        unlock_strategies = [
            ('/sap/bc/adt/locks', 'Standard REST lock endpoint'),
            ('/sap/bc/adt/core/objectlock', 'Core object lock endpoint'),
        ]

        for endpoint, description in unlock_strategies:
            if self.debug_enabled:
                self._debug(f"[DEBUG] unlock_object - trying: {description}")

            try:
                headers = self._get_headers()

                response = self.session.delete(
                    f"{self.url}{endpoint}",
                    headers=headers,
                    params={'_action': 'UNLOCK', 'lockHandle': lock_handle},
                    timeout=self.timeout_short
                )
                self._update_cookies(response)

                if response.status_code in [200, 204]:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] unlock_object - unlocked successfully via {description}")
                    return True
                elif response.status_code == 404:
                    # This endpoint doesn't exist, try next strategy
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] unlock_object - {description} not found (404)")
                    continue
                else:
                    # Try next strategy for other errors
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] unlock_object - {description} failed: {response.status_code}")
                    continue

            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] unlock_object - {description} exception: {str(e)[:100]}")
                continue

        # All unlock attempts failed, but don't raise exception
        # Locks timeout automatically, so this is not critical
        if self.debug_enabled:
            self._debug("[DEBUG] unlock_object - all strategies failed, lock will timeout automatically")
        return True

    def is_object_locked(self, object_url):
        """
        Check if an object is currently locked.

        Returns:
            dict with keys: locked, lock_owner, lock_handle (if locked by current user)
            Returns None if check fails
        """
        try:
            headers = self._get_headers()

            response = self.session.get(
                f"{self.url}/sap/bc/adt/locks",
                headers=headers,
                params={'objectRef': object_url},
                timeout=self.timeout_short
            )

            if response.status_code == 200:
                # Check if locked by parsing response
                text = response.text
                if 'LOCK_HANDLE' in text or 'lockHandle' in text:
            
                    owner_match = re.search(r'LOCK_OWNER>([^<]+)</', text)
                    handle_match = re.search(r'LOCK_HANDLE>([^<]+)</', text)

                    return {
                        'locked': True,
                        'lock_owner': owner_match.group(1) if owner_match else 'unknown',
                        'lock_handle': handle_match.group(1) if handle_match else None
                    }
                return {'locked': False, 'lock_owner': None, 'lock_handle': None}
            elif response.status_code == 404:
                return {'locked': False, 'lock_owner': None, 'lock_handle': None}
            else:
                return None
        except Exception:
            return None

    def lock_object_with_retry(self, object_url, access_mode='MODIFY', transport=None, max_retries=3, retry_delay=2, allow_no_transport=False):
        """
        Lock an object with retry logic for transient failures.

        Args:
            object_url: URL of the object to lock
            access_mode: 'MODIFY' or 'READ'
            transport: Transport request number (corrNr). Always pass this to prevent
                       SAP CTS from auto-creating a ghost transport during lock.
            max_retries: Maximum number of retry attempts
            retry_delay: Seconds to wait between retries

        Returns:
            lock_handle if successful

        Raises:
            Exception with details if lock fails after all retries
        """
    

        last_error = None
        for attempt in range(max_retries):
            try:
                return self.lock_object(object_url, access_mode, transport=transport, allow_no_transport=allow_no_transport)
            except Exception as e:
                last_error = e
                error_text = str(e)

                # Check for stale lock (403 or specific error messages)
                if '403' in error_text or 'locked by' in error_text.lower() or 'stale' in error_text.lower():
                    # Check who has the lock
                    lock_info = self.is_object_locked(object_url)
                    if lock_info and lock_info.get('locked'):
                        raise SAPLockError(
                            f"Object is locked by user '{lock_info.get('lock_owner', 'unknown')}'. "
                            f"Please unlock it manually or wait for the lock to expire.",
                            lock_owner=lock_info.get('lock_owner')
                        )

                # Retry for transient errors
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    # Refresh CSRF token before retry
                    self.fetch_csrf_token()

        raise SAPLockError(f"Failed to lock object after {max_retries} attempts: {last_error}")

    def safe_unlock(self, object_url, lock_handle):
        """
        Safely unlock an object, ignoring errors.

        Use this in finally blocks to ensure cleanup.

        Returns:
            True if unlocked successfully, False otherwise
        """
        if not lock_handle:
            return True
        try:
            self.unlock_object(object_url, lock_handle)
            return True
        except Exception:
            return False

    def object_lock(self, object_url, access_mode='MODIFY'):
        """
        Context manager for safe object locking.

        Usage:
            with client.object_lock('/sap/bc/adt/oo/classes/zcl_test') as lock_handle:
                # Do modifications
                client.update_source(...)
            # Object is automatically unlocked

        Returns:
            Context manager that yields the lock_handle
        """
        from contextlib import contextmanager

        @contextmanager
        def lock_context():
            lock_handle = None
            try:
                lock_handle = self.lock_object_with_retry(object_url, access_mode)
                yield lock_handle
            finally:
                self.safe_unlock(object_url, lock_handle)

        return lock_context()

    def syntax_check_via_activation(self, object_name, object_url):
        """Check syntax using SAP ADT activation endpoint in pre-audit mode.

        This performs a syntax check without actually activating the object.

        Returns:
            dict with 'valid' (bool), 'errors' (list), 'warnings' (list)

        Note:
            Uses the activation endpoint with pre-audit mode which checks
            syntax but does not activate. The response format is the same
            as activate_object() but activationExecuted will be false.
        """
        # Determine object type from URL
        object_type = self._extract_object_type(object_url)
        parent_uri = self._extract_parent_uri(object_url)

        # Build activation request for pre-audit (syntax check only)
        activation_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:objectReference adtcore:uri="{object_url}" adtcore:type="{object_type}" adtcore:name="{object_name}" adtcore:parentUri="{parent_uri}"/>
</adtcore:objectReferences>'''

        headers = self._get_headers(
            'application/xml',
            'application/vnd.sap.adt.objectactivation.result.v1+xml'
        )

        # Use preaudit mode - checks syntax but does NOT activate
        response = self._request_with_csrf_retry(
            'post', f"{self.url}/sap/bc/adt/activation",
            headers=headers,
            data=activation_body,
            params={'method': 'activate', 'preauditRequested': 'true'},
        )

        if response.status_code == 403:
            # Object is locked - parse lock owner for actionable error
            lock_user = 'another user'
            try:
                user_match = re.search(r'<entry key="T100KEY-V1">([^<]+)</entry>', response.text)
                if not user_match:
                    user_match = re.search(r"<entry key='T100KEY-V1'>([^<]+)</entry>", response.text)
                if user_match:
                    lock_user = user_match.group(1).strip()
            except Exception:
                pass
            return {
                'valid': False,
                'errors': [{'message': f'Object locked by {lock_user}. Release lock in SM12 or close other sessions.'}],
                'warnings': [],
                'locked': True,
                'lock_user': lock_user,
                'activation_executed': False,
                'check_executed': False
            }

        if response.status_code != 200:
            raise SAPADTError(
                f"Syntax check failed: HTTP {response.status_code}",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        # Handle empty response (some SAP configurations return empty for pure pre-audit)
        if not response.text or len(response.text.strip()) < 50:
            return {
                'valid': True,  # Assume valid if no errors returned
                'errors': [],
                'warnings': [],
                'activation_executed': False,
                'check_executed': True
            }

        # Parse the XML response (same format as activate_object)


        result = {
            'valid': False,
            'activation_executed': False,
            'check_executed': False,
            'generation_executed': False,
            'errors': [],
            'warnings': []
        }

        try:
            root = ET.fromstring(response.text)

            # Namespace for checklist
            ns_chkl = {'chkl': 'http://www.sap.com/abapxml/checklist'}

            # Check properties
            props = root.find('.//chkl:properties', ns_chkl)
            if props is not None:
                result['activation_executed'] = props.get('activationExecuted', 'false') == 'true'
                result['check_executed'] = props.get('checkExecuted', 'false') == 'true'
                result['generation_executed'] = props.get('generationExecuted', 'false') == 'true'

            # Collect messages (errors and warnings)
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

                if tag_name == 'msg':
                    msg_type = elem.get('type', 'W')
                    obj_descr = elem.get('objDescr', '')
                    line = elem.get('line', '0')
                    href = elem.get('href', '')

                    text = ''
                    for child in elem.iter():
                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if child_tag == 'txt' and child.text:
                            text = child.text
                            break

                    message_info = {
                        'type': msg_type,
                        'message': text,
                        'object': obj_descr,
                        'line': line,
                        'href': href
                    }

                    if msg_type == 'E':
                        result['errors'].append(message_info)
                    elif msg_type == 'W':
                        result['warnings'].append(message_info)

            # Valid if:
            # 1. checkExecuted=true and no errors → SAP ran the check, it passed
            # 2. No errors and SAP skipped check (already clean / generation only) → valid
            # 3. Errors present → always invalid
            if result['errors']:
                result['valid'] = False
            elif result['check_executed']:
                result['valid'] = True
            elif not result['errors']:
                # SAP skipped the check (object already clean or only generation ran)
                result['valid'] = True
            else:
                result['valid'] = False

        except ET.ParseError as e:
            result['valid'] = False
            result['errors'] = [{'message': f'Could not parse syntax check response: {e}'}]

        return result

    def clear_enqueue_lock(self, object_url, transport=None):
        """Clear a stale SAP enqueue lock by acquiring and releasing it.

        When the same user holds a leftover enqueue lock from a previous session,
        this performs a lock→unlock cycle to clear it.

        Args:
            object_url: URL of the object whose enqueue lock should be cleared
            transport: Optional transport corrNr. Pass this when known to avoid
                       SAP CTS auto-creating a ghost transport during the lock step.

        Returns:
            True if the cycle succeeded, False otherwise
        """
        if self.debug_enabled:
            self._debug(f"[DEBUG] clear_enqueue_lock - attempting lock→unlock cycle for {object_url}")

        try:
            # allow_no_transport=True: this is a cleanup-only lock→unlock, no write follows,
            # so no CTS entry is triggered even without corrNr.
            lock_handle = self.lock_object(object_url, transport=transport, allow_no_transport=True)
            if lock_handle and lock_handle not in ['NO_LOCK_SUPPORT', 'IMPLICIT_LOCK']:
                self.unlock_object(object_url, lock_handle)
                if self.debug_enabled:
                    self._debug("[DEBUG] clear_enqueue_lock - lock→unlock cycle succeeded")
                return True
            elif lock_handle in ['NO_LOCK_SUPPORT', 'IMPLICIT_LOCK']:
                # Lock endpoint doesn't support explicit locks, nothing to clear
                if self.debug_enabled:
                    self._debug(f"[DEBUG] clear_enqueue_lock - no explicit lock to clear ({lock_handle})")
                return True
        except Exception as e:
            if self.debug_enabled:
                self._debug(f"[DEBUG] clear_enqueue_lock - failed: {str(e)[:150]}")
            return False

        return False

    def find_ghost_transports(self, user=None, lookback_seconds=60):
        """Query E070 for empty K-type transports created recently by the current user.

        Called after a SAPLockError on 409 to surface ghost transports the failed
        lock attempt may have created so the user knows which ones to delete in SE10.

        Args:
            user: SAP user to filter by (default: self.user)
            lookback_seconds: How far back in seconds to look (default: 60)

        Returns:
            list of transport numbers (strings), empty list if none found or query fails
        """
        from datetime import datetime, timedelta

        target_user = (user or self.user).upper()
        now = datetime.now()
        cutoff = now - timedelta(seconds=lookback_seconds)
        date_str = cutoff.strftime('%Y%m%d')
        time_str = cutoff.strftime('%H%M%S')
        today_str = now.strftime('%Y%m%d')

        query = (
            f"SELECT TRKORR, AS4TEXT FROM E070 WHERE MANDT = '{self.client}' "
            f"AND AS4USER = '{target_user}' AND TRSTATUS = 'D' AND TRFUNCTION = 'K' "
            f"AND AS4TEXT = 'Generated Request for Change Recording' "
            f"AND AS4DATE >= '{date_str}' AND AS4DATE <= '{today_str}' "
            f"AND AS4TIME >= '{time_str}'"
        )

        try:
            if not self.csrf_token:
                self.fetch_csrf_token()

            headers = self._get_headers('application/vnd.sap.adt.datapreview.table.v1+xml')
            headers['Content-Type'] = 'text/plain'

            response = self.session.post(
                f"{self.url}/sap/bc/adt/datapreview/freestyle",
                headers=headers,
                params={'rowNumber': 50},
                data=query.encode('utf-8'),
                timeout=self.timeout_default
            )

            if response.status_code != 200:
                return []

            root = ET.fromstring(response.text)
            ns = {'dp': 'http://www.sap.com/adt/dataPreview'}
            columns = root.findall('.//dp:columns', ns)
            if not columns:
                return []

            col_map = {}
            for col in columns:
                meta = col.find('dp:metadata', ns)
                if meta is not None:
                    name = meta.get('{http://www.sap.com/adt/dataPreview}name', '')
                    col_map[name] = col

            trkorr_col = col_map.get('TRKORR')
            if trkorr_col is None:
                return []

            ghosts = []
            for cell in trkorr_col.findall('dp:data', ns):
                val = cell.get('{http://www.sap.com/adt/dataPreview}value', '').strip()
                if val:
                    ghosts.append(val)

            return ghosts

        except Exception:
            return []

    def _parse_activation_response(self, response, object_name):
        """Parse a chkl: or ioc: activation response and return a result dict.

        Handles three response shapes (Bug 13/15 fix):
          1. Empty body (len < 50)  → immediate success
          2. <ioc:inactiveObjects>  → SAP refused; returns list of refs that must be activated
          3. <chkl:messages>        → normal check result; parse activationExecuted / errors

        Returns dict with keys:
          success (bool), activation_executed (bool), check_executed (bool),
          generation_executed (bool), errors (list), warnings (list),
          response (str), ioc_refs (list of (uri, type, name) tuples)
        """
        IOC_NS = 'http://www.sap.com/abapxml/inactiveCtsObjects'
        ADT_CORE_NS = 'http://www.sap.com/adt/core'

        result = {
            'success': False,
            'activation_executed': False,
            'check_executed': False,
            'generation_executed': False,
            'errors': [],
            'warnings': [],
            'response': response.text,
            'ioc_refs': [],
        }

        text = response.text or ''

        # Shape 1: empty body = SAP activated with no messages
        if not text or len(text.strip()) < 50:
            result['success'] = True
            result['activation_executed'] = True
            return result

        # Shape 2: ioc:inactiveObjects — SAP rejected single-object activation,
        # returns list of all sub-objects that must be activated together (Bug 13/15)
        if 'inactiveObjects' in text or f'{{{IOC_NS}}}' in text or 'ioc:inactiveObjects' in text:
            try:
                root = ET.fromstring(text)
                refs = []
                for entry in root.iter(f'{{{IOC_NS}}}entry'):
                    ref = entry.find(f'{{{IOC_NS}}}object/{{{IOC_NS}}}ref')
                    if ref is None:
                        ref = entry.find(f'{{{IOC_NS}}}ref')
                    if ref is not None:
                        uri = ref.get(f'{{{ADT_CORE_NS}}}uri') or ref.get('uri', '')
                        atype = ref.get(f'{{{ADT_CORE_NS}}}type') or ref.get('type', '')
                        name = ref.get(f'{{{ADT_CORE_NS}}}name') or ref.get('name', object_name)
                        if atype and '/RQ' not in atype:
                            refs.append((uri, atype, name))
                result['ioc_refs'] = refs
            except ET.ParseError:
                pass
            return result

        # Shape 3: chkl:messages
        try:
            root = ET.fromstring(text)
            ns_chkl = {'chkl': 'http://www.sap.com/abapxml/checklist'}

            props = root.find('.//chkl:properties', ns_chkl)
            if props is not None:
                result['activation_executed'] = props.get('activationExecuted', 'false') == 'true'
                result['check_executed'] = props.get('checkExecuted', 'false') == 'true'
                result['generation_executed'] = props.get('generationExecuted', 'false') == 'true'

            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name == 'msg':
                    msg_type = elem.get('type', 'W')
                    obj_descr = elem.get('objDescr', '')
                    line = elem.get('line', '0')
                    href = elem.get('href', '')
                    msg_text = ''
                    for child in elem.iter():
                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if child_tag == 'txt' and child.text:
                            msg_text = child.text
                            break
                    message_info = {'type': msg_type, 'message': msg_text,
                                    'object': obj_descr, 'line': line, 'href': href}
                    if msg_type == 'E':
                        result['errors'].append(message_info)
                    elif msg_type == 'W':
                        result['warnings'].append(message_info)

            if result['errors']:
                result['success'] = False
            elif result['activation_executed']:
                result['success'] = True
            elif result['generation_executed']:
                result['success'] = True
            else:
                result['success'] = False
                result['errors'].append({
                    'type': 'W',
                    'message': 'SAP returned activationExecuted=false with no errors and no generation. '
                               'Object may be inactive. Please verify in SE24 or activate manually.',
                    'object': object_name, 'line': '0', 'href': ''
                })

        except ET.ParseError as e:
            if 'activationExecuted="true"' in text:
                result['success'] = True
                result['activation_executed'] = True
            elif 'generationExecuted="true"' in text and 'type="E"' not in text:
                result['success'] = True
                result['generation_executed'] = True
            else:
                result['errors'] = [{'message': f'Could not parse activation response: {e}',
                                     'type': 'E', 'object': object_name, 'line': '0', 'href': ''}]

        return result

    def activate_object(self, object_name, object_url):
        """Activate an ABAP object using two-phase pre-audit + batch activation.

        Phase 1 (pre-audit): POST with preauditRequested=true on the seed object.
          - If SAP returns ioc:inactiveObjects → collect all sub-object refs (Bug 15 fix)
          - If SAP returns chkl:messages with errors → fail fast (syntax errors in source)
          - If SAP returns empty or success → object is already active, nothing to do

        Phase 2 (batch activate): POST all collected refs with no preaudit flag.
          - Empty response body → activation succeeded
          - chkl:messages with type="E" → syntax/semantic errors in sub-objects
          - ioc:inactiveObjects → still more deps (report remaining list to user)

        This replaces the old single-shot activation that only sent the CLAS/OC root ref
        and failed silently when the class had inactive method includes (CLAS/OM/*) or
        setup objects (CLAS/OSU). (Bug 13 + Bug 15 fix)

        Returns:
            dict with 'success' (bool), 'errors' (list), 'warnings' (list), 'response' (str)
        """
        object_type = self._extract_object_type(object_url)
        parent_uri = self._extract_parent_uri(object_url)

        ADT_CORE_NS = 'http://www.sap.com/adt/core'

        headers = self._get_headers(
            'application/xml',
            'application/vnd.sap.adt.objectactivation.result.v1+xml'
        )

        seed_body = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<adtcore:objectReferences xmlns:adtcore="{ADT_CORE_NS}">'
            f'<adtcore:objectReference adtcore:uri="{object_url}" adtcore:type="{object_type}"'
            f' adtcore:name="{object_name}" adtcore:parentUri="{parent_uri}"/>'
            f'</adtcore:objectReferences>'
        )

        # ── Phase 1: pre-audit ──────────────────────────────────────────────────
        if self.debug_enabled:
            self._debug(f"[DEBUG] activate_object phase 1 (pre-audit): {object_name} ({object_type})")

        r1 = self._request_with_csrf_retry(
            'post', f"{self.url}/sap/bc/adt/activation",
            headers=headers,
            data=seed_body,
            params={'method': 'activate', 'preauditRequested': 'true'},
        )

        if r1.status_code == 403:
            return self._handle_activation_403(r1, object_name, object_url, seed_body, headers)

        if r1.status_code != 200:
            return {
                'success': False, 'activation_executed': False, 'check_executed': False,
                'generation_executed': False,
                'errors': [{'message': f'HTTP {r1.status_code} - Activation pre-audit failed',
                            'type': 'E', 'object': object_name, 'line': '0', 'href': ''}],
                'warnings': [], 'response': r1.text[:500]
            }

        p1 = self._parse_activation_response(r1, object_name)

        if self.debug_enabled:
            self._debug(f"[DEBUG] activate_object phase 1 result: success={p1['success']}, "
                        f"ioc_refs={len(p1['ioc_refs'])}, errors={len(p1['errors'])}")

        # Phase 1 returned hard errors (syntax errors) — no point proceeding
        if p1['errors'] and any(e.get('type') == 'E' for e in p1['errors']):
            return p1

        # Phase 1 succeeded outright (empty body or activationExecuted=true with no ioc_refs)
        if p1['success'] and not p1['ioc_refs']:
            return p1

        # ── Phase 2: batch activate ─────────────────────────────────────────────
        # Collect refs: start from ioc_refs if SAP returned them, else use seed ref
        if p1['ioc_refs']:
            refs = p1['ioc_refs']
            if self.debug_enabled:
                self._debug(f"[DEBUG] activate_object phase 2: activating {len(refs)} refs from ioc:inactiveObjects")
        else:
            refs = [(object_url, object_type, object_name)]

        batch = ''.join(
            f'<adtcore:objectReference adtcore:uri="{uri}" adtcore:type="{t}" adtcore:name="{n}"/>'
            for uri, t, n in refs
        )
        batch_body = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<adtcore:objectReferences xmlns:adtcore="{ADT_CORE_NS}">'
            f'{batch}'
            f'</adtcore:objectReferences>'
        )

        r2 = self._request_with_csrf_retry(
            'post', f"{self.url}/sap/bc/adt/activation",
            headers=headers,
            data=batch_body,
            params={'method': 'activate'},
        )

        if r2.status_code == 403:
            return self._handle_activation_403(r2, object_name, object_url, batch_body, headers)

        if r2.status_code != 200:
            return {
                'success': False, 'activation_executed': False, 'check_executed': False,
                'generation_executed': False,
                'errors': [{'message': f'HTTP {r2.status_code} - Batch activation failed',
                            'type': 'E', 'object': object_name, 'line': '0', 'href': ''}],
                'warnings': [], 'response': r2.text[:500]
            }

        p2 = self._parse_activation_response(r2, object_name)

        if self.debug_enabled:
            self._debug(f"[DEBUG] activate_object phase 2 result: success={p2['success']}, "
                        f"ioc_refs={len(p2['ioc_refs'])}, errors={len(p2['errors'])}")

        # If phase 2 still returned ioc:inactiveObjects, activation is incomplete
        if p2['ioc_refs']:
            remaining = [n for _, _, n in p2['ioc_refs']]
            p2['success'] = False
            p2['errors'].append({
                'type': 'E',
                'message': (f'Activation incomplete — SAP still reports inactive sub-objects after batch activate: '
                            f'{", ".join(remaining)}. Activate manually in SE24 or Eclipse ADT.'),
                'object': object_name, 'line': '0', 'href': ''
            })

        return p2

    def _handle_activation_403(self, response, object_name, object_url, activation_body, headers):
        """Handle 403 during activation (stale enqueue lock). Clears lock and retries once."""
        error_msg = f'HTTP 403 - Activation failed'
        try:
            text = response.text or ''
            if 'zaten' in text or 'already editing' in text or 'T100KEY-V1' in text:
                user_match = re.search(r'<entry key="T100KEY-V1">([^<]+)</entry>', text)
                if not user_match:
                    user_match = re.search(r"<entry key='T100KEY-V1'>([^<]+)</entry>", text)
                lock_user = user_match.group(1).strip() if user_match else 'another user'
                current_user = self.user.upper() if hasattr(self, 'user') and self.user else ''
                if lock_user.upper() == current_user:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] _handle_activation_403 - same user ({lock_user}) has lock, clearing")
                    if self.clear_enqueue_lock(object_url):
                        self.fetch_csrf_token()
                        retry = self.session.post(
                            f"{self.url}/sap/bc/adt/activation",
                            headers=headers,
                            data=activation_body,
                            params={'method': 'activate'},
                            timeout=self.timeout_default
                        )
                        self._update_cookies(retry)
                        if retry.status_code == 200:
                            return self._parse_activation_response(retry, object_name)
                        error_msg = (f'Object locked by {lock_user} (same user). '
                                     f'Enqueue lock cleared but activation still failed (HTTP {retry.status_code}).')
                    else:
                        error_msg = (f'Object locked by {lock_user} (same user). '
                                     f'Failed to clear enqueue lock. Use SM12 to release lock "EADT_LOCK".')
                else:
                    error_msg = (f'Object locked by {lock_user}. '
                                 f'Please close other SAP sessions or use SM12 to release lock "EADT_LOCK".')
        except Exception:
            pass
        return {
            'success': False, 'activation_executed': False, 'check_executed': False,
            'generation_executed': False,
            'errors': [{'message': error_msg, 'type': 'E', 'object': object_name, 'line': '0', 'href': ''}],
            'warnings': [], 'response': response.text[:500]
        }

    def search_objects(self, query, max_results=100):
        """Search for ABAP objects"""
        headers = self._get_headers('application/xml')

        response = self.session.get(
            f"{self.url}/sap/bc/adt/repository/informationsystem/search",
            headers=headers,
            params={
                'operation': 'quickSearch',
                'query': query,
                'maxResults': max_results
            },
            timeout=self.timeout_short
        )

        if response.status_code == 200:
            return response.text
        else:
            raise SAPADTError(
                f"Search failed",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

    def get_package_contents(self, package_name):
        """Get package contents"""
        headers = self._get_headers('application/vnd.sap.as+xml', 'application/vnd.sap.adt.core.v1+xml')

        response = self._request_with_csrf_retry(
            'post', f"{self.url}/sap/bc/adt/repository/nodestructure",
            headers=headers,
            params={
                'parent_type': 'DEVC/K',
                'parent_name': package_name,
                'withShortDescriptions': 'true'
            },
            data='',
            timeout=self.timeout_short,
        )

        if response.status_code == 200:
            return response.text
        else:
            raise SAPADTError(
                f"Failed to get package contents",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

    def register_object_in_transport(self, object_name, transport, object_type='class'):
        """Pre-register object as an R3TR catch-all entry in the target transport.

        Without an R3TR CLAS/INTF/PROG entry, SAP CTS records each touched
        class-pool include (CLSD, CPUB, CPRI, CPRO, CCDEF, CCIMP, CM0xx) as a
        separate LIMU entry. When SAP activation touches an include NOT already
        owned by any transport, CTS auto-creates a new K+S pair ("Generated
        Request for Change Recording") — one ghost transport per touched
        include. A single push that adds a new method declaration can spawn
        2–3 ghost transports this way.

        This call adds an R3TR <type> <name> catch-all entry so CTS attributes
        every subsequent include change to the caller's transport. Idempotent —
        SAP accepts a duplicate add as a no-op.

        Tries multiple REST endpoint patterns because SAP ADT doesn't document
        this operation consistently across NetWeaver / S/4HANA versions. Returns
        status dict; never raises — the push should proceed even if
        registration fails, with a clear WARN + SE09 fallback instruction.

        Args:
            object_name: ABAP object name (e.g., 'ZSD000_CL_MM_TOOLS')
            transport: K-type workbench transport (e.g., 'IEDK936301')
            object_type: Normalized object type ('class'/'clas'/'interface'/
                         'intf'/'program'/'prog'/'functiongroup'/'fugr')

        Returns:
            dict with keys:
                registered (bool): True if R3TR entry was added (or already present)
                method (str|None): REST path that succeeded
                status_code (int): HTTP status from the last attempt
                error (str): Error text on failure
        """
        type_map = {
            'class': 'CLAS', 'clas': 'CLAS',
            'interface': 'INTF', 'intf': 'INTF',
            'program': 'PROG', 'prog': 'PROG', 'report': 'PROG',
            'functiongroup': 'FUGR', 'fugr': 'FUGR',
        }
        otype = type_map.get((object_type or '').lower())
        if not otype:
            return {'registered': False, 'method': None, 'status_code': 0,
                    'error': f'Unsupported object type for R3TR registration: {object_type}'}
        if not transport:
            return {'registered': False, 'method': None, 'status_code': 0,
                    'error': 'transport is required'}

        name_upper = object_name.upper()
        trkorr = transport.upper()

        if not self.csrf_token:
            self.fetch_csrf_token()

        # SAP CTS standard namespace payload
        xml_body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<tm:root xmlns:tm="http://www.sap.com/cts/adt/tm" '
            'xmlns:adtcore="http://www.sap.com/adt/core">\n'
            f'  <tm:request tm:number="{trkorr}">\n'
            f'    <tm:object tm:pgmid="R3TR" tm:type="{otype}" tm:name="{name_upper}"/>\n'
            '  </tm:request>\n'
            '</tm:root>'
        )

        # Verified endpoint (live-tested on INDEX S/4HANA 2026-04-15):
        #   POST /sap/bc/adt/cts/transportrequests/<TRKORR>
        #   Content-Type: application/xml
        #   Body: <tm:root><tm:request tm:number><tm:object tm:pgmid tm:type tm:name/>
        # Returns 200 on success. Creates an R3TR CLAS entry in the transport's task.
        target_url = f'{self.url}/sap/bc/adt/cts/transportrequests/{trkorr}'

        # Context-scoped CSRF prefetch (critical).
        # Tokens fetched from /sap/bc/adt/discovery are scoped to that context;
        # SAP rejects them on /cts/* with a misleading "CSRF token validation
        # failed" 403. Fetching a fresh token from the target URL binds it to
        # the CTS context.
        try:
            fetch_headers = self._get_headers(accept_type='*/*')
            fetch_headers['X-CSRF-Token'] = 'Fetch'
            fetch_resp = self.session.get(
                target_url, headers=fetch_headers, timeout=self.timeout_short
            )
            ctx_token = fetch_resp.headers.get('X-CSRF-Token')
            if ctx_token and ctx_token.lower() not in ('required', 'fetch'):
                self.csrf_token = ctx_token  # re-use for subsequent CTS calls
        except Exception as e:
            if self.debug_enabled:
                self._debug(f'[DEBUG] register_object_in_transport - CSRF prefetch failed: {str(e)[:150]}')

        try:
            headers = self._get_headers(accept_type='*/*', content_type='application/xml')
            if self.debug_enabled:
                self._debug(f'[DEBUG] register_object_in_transport - POST {target_url}')
            response = self.session.post(
                target_url, data=xml_body, headers=headers, timeout=self.timeout_short
            )
            if response.status_code in (200, 201, 204):
                if self.debug_enabled:
                    self._debug('[DEBUG] register_object_in_transport - success')
                return {'registered': True, 'method': 'transportrequests',
                        'status_code': response.status_code, 'error': ''}
            return {'registered': False, 'method': None,
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}: {(response.text or "")[:200]}'}
        except Exception as e:
            return {'registered': False, 'method': None, 'status_code': 0,
                    'error': f'{type(e).__name__}: {str(e)[:200]}'}

    def get_transport_info(self, object_url, dev_class=None, operation=None):
        """Get transport information for an object"""
        headers = self._get_headers()

        params = {}
        if dev_class:
            params['DEVCLASS'] = dev_class
        if operation:
            params['OPERATION'] = operation

        # Build request URL
        request_url = f"{self.url}{object_url}"
        if not request_url.endswith('/source/main'):
            request_url = request_url.rstrip('/') + '/source/main'

        response = self.session.get(
            request_url,
            headers=headers,
            params=params,
            timeout=self.timeout_short
        )

        # Transport info might be in headers
        transport = response.headers.get('X-sap-adt-transport')
        return transport or "No transport info available"

    def _extract_object_type(self, object_url):
        """Extract ADT object type from URL using centralized registry."""
        from object_types import get_adt_type_from_url
        return get_adt_type_from_url(object_url)

    def _extract_parent_uri(self, object_url):
        """Extract parent URI from object URL"""
        if '/source/main' in object_url:
            return object_url.replace('/source/main', '')
        return object_url.rsplit('/', 1)[0] if '/' in object_url else ''

    def create_object(self, obj_type, name, package_name, description, package_path, responsible=None, transport=None, max_retries=10):
        """Create a new ABAP object (class, interface, or program)

        Note: Automatically retries with different namespaces/media types based on error responses.
        Different SAP versions may require different combinations.
        """


        # Ensure we have CSRF token
        if not self.csrf_token:
            self.fetch_csrf_token()

        responsible_xml = responsible or self.user
        name_upper = name.upper()
        package_upper = package_name.upper()

        # Define creation attempts with different namespace/media type combinations
        # Format: (object_type_key, namespace, media_type, xml_element_name, object_path)
        attempts = []

        if obj_type == 'PROG/P':
            # Program creation attempts - namespace and media types may vary by SAP version
            attempts = [
                ('programs', 'http://www.sap.com/adt/programs/programs',
                 'application/vnd.sap.adt.programs.programs.v2+xml', 'programs', 'programs/programs'),
                ('programs_alt', 'http://www.sap.com/adt/programs',
                 'application/vnd.sap.adt.programs.programs', 'programs', 'programs/programs'),
                ('programs_v2', 'http://www.sap.com/adt/programs',
                 'application/vnd.sap.adt.program.v2+xml', 'programs', 'programs/programs'),
            ]
        elif obj_type == 'PROG/I':
            # Include creation attempts
            attempts = [
                ('includes', 'http://www.sap.com/adt/programs/includes',
                 'application/vnd.sap.adt.programs.includes.v2+xml', 'include', 'programs/includes'),
                ('includes_alt', 'http://www.sap.com/adt/programs/includes',
                 'application/vnd.sap.adt.programs.includes+xml', 'include', 'programs/includes'),
                ('includes_v3', 'http://www.sap.com/adt/programs/includes',
                 'application/vnd.sap.adt.programs.includes.v3+xml', 'include', 'programs/includes'),
            ]
        elif obj_type == 'CLAS/OC':
            attempts = [
                ('class', 'http://www.sap.com/adt/oo/classes',
                 'application/vnd.sap.adt.oo.classes.v4+xml', 'class', 'oo/classes'),
            ]
        elif obj_type == 'INTF/OI':
            attempts = [
                ('interface', 'http://www.sap.com/adt/oo/interfaces',
                 'application/vnd.sap.adt.oo.interfaces.v4+xml', 'interface', 'oo/interfaces'),
            ]
        else:
            raise ValueError(f"Unsupported object type: {obj_type}")

        # Track tried combinations to avoid infinite loops
        tried_combinations = set()
        retry_queue = list(attempts)
        attempt_num = 0

        while retry_queue and attempt_num < max_retries:
            attempt_key, namespace, media_type, xml_element, object_path = retry_queue.pop(0)
            attempt_key_with_media = f"{attempt_key}|{media_type}"

            if attempt_key_with_media in tried_combinations:
                continue
            tried_combinations.add(attempt_key_with_media)
            attempt_num += 1

            # Build XML body
            if obj_type == 'PROG/P':
                creation_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<{xml_element}:abapProgram xmlns:{xml_element}="{namespace}"
                      xmlns:adtcore="http://www.sap.com/adt/core"
                      adtcore:description="{description}"
                      adtcore:name="{name_upper}"
                      adtcore:responsible="{responsible_xml}"
                      adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:name="{package_upper}" adtcore:uri="{package_path}"/>
</{xml_element}:abapProgram>'''
            elif obj_type == 'PROG/I':
                creation_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<{xml_element}:abapInclude xmlns:{xml_element}="{namespace}"
                      xmlns:adtcore="http://www.sap.com/adt/core"
                      adtcore:type="{obj_type}"
                      adtcore:description="{description}"
                      adtcore:name="{name_upper}"
                      adtcore:responsible="{responsible_xml}"
                      adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:name="{package_upper}" adtcore:uri="{package_path}"/>
</{xml_element}:abapInclude>'''
            elif obj_type == 'INTF/OI':
                # Interface
                creation_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<{xml_element}:abapInterface xmlns:{xml_element}="{namespace}"
                            xmlns:adtcore="http://www.sap.com/adt/core"
                            adtcore:type="{obj_type}"
                            adtcore:description="{description}"
                            adtcore:name="{name_upper}"
                            adtcore:responsible="{responsible_xml}"
                            adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:name="{package_upper}" adtcore:uri="{package_path}"/>
</{xml_element}:abapInterface>'''
            else:
                # Class
                creation_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<{xml_element}:abapClass xmlns:{xml_element}="{namespace}"
                            xmlns:adtcore="http://www.sap.com/adt/core"
                            adtcore:type="{obj_type}"
                            adtcore:description="{description}"
                            adtcore:name="{name_upper}"
                            adtcore:responsible="{responsible_xml}"
                            adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:name="{package_upper}" adtcore:uri="{package_path}"/>
</{xml_element}:abapClass>'''

            headers = self._get_headers(media_type, media_type)

            params = {}
            if transport:
                params['corrNr'] = transport

            response = self.session.post(
                f"{self.url}/sap/bc/adt/{object_path}",
                headers=headers,
                data=creation_body.encode('utf-8'),
                params=params,
                timeout=self.timeout_default
            )

            # 403 CSRF: the cached token can be stale server-side. Force-refresh
            # and retry this attempt ONCE with a new token before falling through
            # to the media-type/namespace retry queue.
            if response.status_code == 403 and 'CSRF' in response.text:
                self.fetch_csrf_token(force_refresh=True)
                headers = self._get_headers(media_type, media_type)
                response = self.session.post(
                    f"{self.url}/sap/bc/adt/{object_path}",
                    headers=headers,
                    data=creation_body.encode('utf-8'),
                    params=params,
                    timeout=self.timeout_default
                )

            if response.status_code in [200, 201]:
                # Success
                object_url = response.headers.get('Location', f'/sap/bc/adt/{object_path}/{name.lower()}')
                return {
                    'success': True,
                    'object_url': object_url,
                    'message': f'{xml_element.capitalize()} {name} created successfully'
                }

            # Check for media type error (415) - extract suggested type
            if response.status_code == 415:
                match = re.search(r'Supported Media Types: ([^\s<]+)', response.text)
                if match:
                    suggested_type = match.group(1)
                    new_key = f"{attempt_key}|{suggested_type}"
                    if new_key not in tried_combinations:
                        retry_queue.append((attempt_key, namespace, suggested_type, xml_element, object_path))

            # Check for namespace error (400) - extract suggested namespace
            if response.status_code == 400:
                # Look for namespace pattern in error
                match = re.search(r'\{([^\}]+)\}' + re.escape(xml_element) + r'[:\s]', response.text)
                if not match:
                    match = re.search(r'\{([^\}]+)\}', response.text)
                if match:
                    suggested_ns = match.group(1)
                    new_key = f"{attempt_key}_ns|{media_type}"
                    if new_key not in tried_combinations and suggested_ns != namespace:
                        retry_queue.append((new_key, suggested_ns, media_type, xml_element, object_path))

        # All retries exhausted
        raise SAPADTError(
            f"Failed to create {obj_type} after {attempt_num} attempts",
            status_code=response.status_code,
            response_text=response.text[:500]
        )

    # NOTE: The old syntax_check() method has been removed because the SAP ADT
    # source endpoint does not support POST for syntax checking (returns 405).
    # Use syntax_check_via_activation() instead, which uses the activation
    # endpoint in pre-audit mode to perform syntax checks.

    def get_object_structure(self, object_url, version='active'):
        """Get object structure and metadata"""
        accept_types = [
            'application/vnd.sap.adt.oo.classes.v2+xml',
            'application/vnd.sap.adt.oo.classes.v4+xml',
            'application/vnd.sap.adt.core.v1+xml',
            'application/xml',
            '*/*'
        ]

        params = {'version': version}
        last_error = None

        for accept_type in accept_types:
            headers = self._get_headers(accept_type)
            response = self.session.get(
                f"{self.url}{object_url}",
                headers=headers,
                params=params,
                timeout=self.timeout_short
            )

            if response.status_code == 200:
                return response.text

            if response.status_code in (406, 415):
                last_error = response
                continue

            last_error = response
            break

        status = last_error.status_code if last_error is not None else 'N/A'
        text = last_error.text if last_error is not None else ''
        raise SAPADTError(
            f"Failed to get object structure",
            status_code=status if isinstance(status, int) else None,
            response_text=text[:500] if text else None
        )

    def user_transports(self, user=None, include_targets=False, modifiable_only=False):
        """Get transport requests from Transport Organizer

        Uses the /cts/transportrequests endpoint which returns all
        modifiable and released transports visible to the user.

        Args:
            user: Filter by owner (default: current user)
            include_targets: Include target system information
            modifiable_only: Return only modifiable transports (requestStatus=D)

        Tries multiple Accept headers to support different SAP system versions.
        Falls back through headers on 406 (Not Acceptable) responses.
        """
        # CSRF token dene — AMA transport listesi bir GET'tir; geçici CSRF hatası
        # tüm listeyi abort etmesin (gözlemlendi 2026-06-02: "Failed to obtain CSRF
        # token" → count 0). GET CSRF'siz de çoğunlukla çalışır.
        if not self.csrf_token:
            try:
                self.fetch_csrf_token()
            except Exception as _csrf_exc:
                self._debug(f'[DEBUG] user_transports CSRF prefetch failed (non-fatal): {str(_csrf_exc)[:120]}')

        # Try different Accept headers - different SAP systems support different types
        # Ordered by most common/standard first
        accept_types = [
            'application/vnd.sap.adt.transportorganizer.v1+xml',           # Most common
            'application/vnd.sap.adt.transportorganizer.trrequests.v1+xml', # Some systems
            'application/vnd.sap.adt.transportorganizertree.v1+xml',       # Older systems
            'application/vnd.sap.adt.transportorganizer.v2+xml',           # v2 API
            'application/vnd.sap.adt.transportorganizer.requests.v1+xml',  # Requests variant
            'application/vnd.sap.adt.transportorganizer.requests+xml',     # Requests no version
            'application/vnd.sap.adt.cts.transportrequests.v1+xml',        # CTS namespace
            'application/vnd.sap.adt.cts.transporttree.v1+xml',            # CTS tree variant
            'application/vnd.sap.adt.cts.transportorganizer.v1+xml',       # CTS organizer
            'application/vnd.sap.adt.core.v1+xml',                         # Generic ADT
            'application/xml',                                              # Fallback
            '*/*'                                                          # Last resort
        ]

        params = {}
        if user:
            params['user'] = user
        if include_targets:
            params['targets'] = 'true'
        if modifiable_only:
            # Use requestStatus parameter (not 'status') to filter modifiable transports
            # D = Modifiable, L = Modifiable Protected
            params['requestStatus'] = 'D'

        last_error = None
        for i, accept_type in enumerate(accept_types):
            headers = self._get_headers(accept_type)

            response = self.session.get(
                f"{self.url}/sap/bc/adt/cts/transportrequests",
                headers=headers,
                params=params,
                timeout=self.timeout_short
            )

            if response.status_code == 200:
                if i > 0:  # Log if fallback was used
                    print(f"Note: Used fallback Accept header: {accept_type}")
                return response.text

            last_error = (
                f"Failed to get transport requests "
                f"(Accept: {accept_type}): {response.status_code} - {response.text[:200]}"
            )

            # Log fallback attempts
            if response.status_code == 406 and i < len(accept_types) - 1:
                print(f"Transport endpoint rejected '{accept_type}', trying next header...")

            if response.status_code != 406:  # 406 = Not Acceptable, try next type
                break  # Non-406 error, don't retry

        raise SAPTransportError(last_error or "Failed to get transport requests: All Accept types rejected")

    def user_transports_from_table(self, user=None, status_filter=None, include_released=False):
        """Get transport requests by querying E070 table directly (fallback method)

        This method queries the SAP transport table E070 directly when the ADT endpoint
        doesn't return modifiable transports. This is a last-resort fallback.

        Args:
            user: Filter by owner (default: current user)
            status_filter: Filter by status (D=Modifiable, R=Released, None=All)
            include_released: Include released transports in results (default: False)

        Returns:
            XML string compatible with ADT endpoint format

        Transport Table E070 Fields:
            TRKORR: Transport number
            AS4USER: Owner
            AS4TEXT: Description
            TRFUNCTION: Type (K=Workbench, W=Customizing, etc.)
            TRSTATUS: Status (D=Modifiable, R=Released, N=Released w/o consolidation)
            STRKORR: Parent transport (for tasks)
            AS4DATE: Created date
            AS4TIME: Created time
            TARSYSTEM: Target system
        """

        from datetime import datetime

        # Build SQL query (must be single line for ADT datapreview)
        user_filter = f"AND AS4USER = '{user.upper()}'" if user else f"AND AS4USER = '{self.user}'"

        # Status filter: D=Modifiable, R=Released, O=Released (with consolidation)
        status_conditions = []
        if status_filter:
            if status_filter.upper() == 'D':
                status_conditions.append("TRSTATUS = 'D'")
            elif status_filter.upper() == 'R':
                status_conditions.append("TRSTATUS IN ('R', 'N', 'O')")
        elif include_released:
            status_conditions.append("TRSTATUS IN ('D', 'R', 'N', 'O')")
        else:
            # Default to modifiable only
            status_conditions.append("TRSTATUS = 'D'")

        status_clause = f"AND ({' OR '.join(status_conditions)})" if status_conditions else ""

        # Query E070 table - single line for ADT datapreview
        query = f"SELECT TRKORR, AS4USER, AS4TEXT, TRFUNCTION, TRSTATUS, STRKORR, AS4DATE, AS4TIME, TARSYSTEM FROM E070 WHERE MANDT = '{self.client}' {user_filter} {status_clause} ORDER BY AS4DATE DESC, AS4TIME DESC"

        # Execute SQL query
        url = f'{self.url}/sap/bc/adt/datapreview/freestyle'
        headers = {
            'Authorization': self._get_auth_header(),
            'sap-client': self.client,
            'X-CSRF-Token': self.csrf_token if self.csrf_token else '',
            'Content-Type': 'text/plain',
            'Accept': 'application/vnd.sap.adt.datapreview.table.v1+xml'
        }

        if not self.csrf_token:
            self.fetch_csrf_token()
            headers['X-CSRF-Token'] = self.csrf_token

        response = self.session.post(
            url,
            headers=headers,
            params={'rowNumber': 100},
            data=query,
            timeout=self.timeout_default
        )

        if response.status_code != 200:
            raise SAPADTError(
                f"SQL query on E070 failed",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        # Parse SQL result and convert to ADT-compatible XML format
        root = ET.fromstring(response.text)
        ns = {'dp': 'http://www.sap.com/adt/dataPreview'}

        # Extract data
        columns = root.findall('.//dp:columns', ns)
        if not columns:
            return '<?xml version="1.0" encoding="utf-8"?><tm:root xmlns:tm="http://www.sap.com/cts/adt/tm" xmlns:adtcore="http://www.sap.com/adt/core"></tm:root>'

        # Get column metadata to find field positions
        col_map = {}
        for col in columns:
            meta = col.find('dp:metadata', ns)
            col_name = meta.get('{http://www.sap.com/adt/dataPreview}name') if meta is not None else ''
            data_elements = col.findall('.//dp:data', ns)
            col_map[col_name] = [d.text for d in data_elements]

        # Build XML in ADT format
        ns_tm = 'http://www.sap.com/cts/adt/tm'
        ns_adtcore = 'http://www.sap.com/adt/core'

        xml_parts = ['<?xml version="1.0" encoding="utf-8"?>']
        xml_parts.append(f'<tm:root adtcore:name="{self.user}" xmlns:tm="{ns_tm}" xmlns:adtcore="{ns_adtcore}">')
        xml_parts.append(f'  <tm:workbench tm:category="Workbench">')

        # Group by status
        modifiable_requests = []
        released_requests = []

        num_rows = len(next(iter(col_map.values()), []))
        for i in range(num_rows):
            try:
                trkorr = col_map.get('TRKORR', [''])[i] if i < len(col_map.get('TRKORR', [])) else ''
                as4user = col_map.get('AS4USER', [''])[i] if i < len(col_map.get('AS4USER', [])) else ''
                as4text = col_map.get('AS4TEXT', [''])[i] if i < len(col_map.get('AS4TEXT', [])) else ''
                trfunction = col_map.get('TRFUNCTION', [''])[i] if i < len(col_map.get('TRFUNCTION', [])) else ''
                trstatus = col_map.get('TRSTATUS', [''])[i] if i < len(col_map.get('TRSTATUS', [])) else ''
                tarssystem = col_map.get('TARSYSTEM', [''])[i] if i < len(col_map.get('TARSYSTEM', [])) else ''
                as4date = col_map.get('AS4DATE', [''])[i] if i < len(col_map.get('AS4DATE', [])) else ''
                as4time = col_map.get('AS4TIME', [''])[i] if i < len(col_map.get('AS4TIME', [])) else ''

                if not trkorr or trfunction != 'K':  # Only workbench requests
                    continue

                # Format timestamp
                if as4date and as4time:
                    timestamp = f"{as4date.replace('-', '')}{as4time.replace(':', '')}"
                else:
                    timestamp = ''

                # XML for this request
                request_xml = f'''        <tm:request tm:number="{trkorr}" tm:parent="" tm:owner="{as4user}" tm:desc="{as4text}" tm:type="K" tm:status="{trstatus}" tm:target="{tarssystem}" tm:target_desc="" tm:cts_project="" tm:cts_project_desc="" tm:lastchanged_timestamp="{timestamp}" tm:uri="/sap/bc/adt/cts/transportrequests/{trkorr}">
          <tm:long_desc/>
        </tm:request>'''

                if trstatus == 'D':
                    modifiable_requests.append(request_xml)
                else:
                    released_requests.append(request_xml)
            except (IndexError, KeyError):
                continue

        # Add modifiable section
        if modifiable_requests:
            xml_parts.append('    <tm:modifiable tm:status="Modifiable">')
            xml_parts.extend(modifiable_requests)
            xml_parts.append('    </tm:modifiable>')

        # Add released section if requested
        if include_released and released_requests:
            xml_parts.append('    <tm:released tm:status="Released (From Table)">')
            xml_parts.extend(released_requests)
            xml_parts.append('    </tm:released>')

        xml_parts.append('  </tm:workbench>')
        xml_parts.append('</tm:root>')

        return '\n'.join(xml_parts)

    @staticmethod
    def _xml_escape(text):
        """Escape special characters for XML attribute values."""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))

    @staticmethod
    def _extract_transport_from_location(location):
        """Extract transport number from Location header.

        Location example: /sap/bc/adt/cts/transportrequests/<TRANSPORT>
        Also handles trailing slashes, query strings, and absolute URLs.
        """
        if not location:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(location)
        path = parsed.path.rstrip('/')
        candidate = path.split('/')[-1].upper() if path else ''
        if re.match(r'^[A-Z0-9]{10,}$', candidate):
            return candidate
        match = re.search(r'/transportrequests/([A-Z0-9]{10,})', location, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    def create_transport(self, description, package_name=None, transport_layer=None,
                         request_type='K', task_type='S', target=''):
        """Create new transport request.

        Supports both On-Premise and BTP Cloud Public Edition.

        BTP Cloud notes:
        - Endpoint: POST /sap/bc/adt/cts/transportrequests
        - Content-Type: application/vnd.sap.adt.transportrequests.v1+xml
        - Accept: application/vnd.sap.adt.transportorganizer.v1+xml
        - XML: tm:useraction='newrequest' on <tm:root>, tm:desc on <tm:request>
        - HTTP 406 = SUCCESS on BTP Cloud; transport number is in Location header
        """
        desc_escaped = self._xml_escape(description)
        target_escaped = self._xml_escape(target)

        transport_body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<tm:root xmlns:tm="http://www.sap.com/cts/adt/tm"'
            ' tm:useraction="newrequest">\n'
            f'  <tm:request tm:desc="{desc_escaped}"'
            f' tm:type="{request_type}"'
            f' tm:target="{target_escaped}"'
            ' tm:cts_project="">\n'
            f'    <tm:task tm:desc="{desc_escaped}" tm:type="{task_type}"/>\n'
            '  </tm:request>\n'
            '</tm:root>'
        )

        headers = self._get_headers(
            'application/vnd.sap.adt.transportrequests.v1+xml',
            'application/vnd.sap.adt.transportorganizer.v1+xml'
        )

        response = self._request_with_csrf_retry(
            'post', f"{self.url}/sap/bc/adt/cts/transportrequests",
            headers=headers,
            data=transport_body.encode('utf-8'),
        )

        location = response.headers.get('Location', '')

        if response.status_code in (200, 201):
            trkorr = self._extract_transport_from_location(location)
            if not trkorr:
                match = re.search(r'<tm:number[^>]*>([^<]+)</tm:number>', response.text)
                if match:
                    trkorr = match.group(1)
            if trkorr:
                return {'success': True, 'transport': trkorr,
                        'message': f'Transport {trkorr} created successfully'}
            return {'success': True, 'response': response.text}

        elif response.status_code == 406:
            # BTP Cloud Public Edition: 406 = SUCCESS, transport number in Location header
            trkorr = self._extract_transport_from_location(location)
            if trkorr:
                return {'success': True, 'transport': trkorr,
                        'message': f'Transport {trkorr} created successfully (BTP Cloud)'}
            raise SAPTransportError(
                'Transport creation returned HTTP 406 (BTP Cloud success) but no '
                f'transport number found in Location header: "{location}"',
                status_code=406,
                response_text=response.text[:500]
            )

        else:
            raise SAPTransportError(
                'Failed to create transport',
                status_code=response.status_code,
                response_text=response.text[:500]
            )

    def table_contents(self, table_name, row_number=100, decode=False, sql_query=None, row_limit=None):
        """Get contents of a database table

        Args:
            table_name: Table name
            row_number: Maximum rows to return (primary parameter name)
            decode: Whether to decode response
            sql_query: Optional SQL query
            row_limit: Alias for row_number (for compatibility)
        """
        # Support both row_number and row_limit parameter names
        if row_limit is not None:
            row_number = row_limit

        headers = self._get_headers('application/xml')

        params = {
            'rowNumber': row_number
        }

        if decode:
            params['decode'] = 'true'

        if sql_query:
            params['sqlQuery'] = sql_query

        response = self.session.get(
            f"{self.url}/sap/bc/adt/datapreview/freestyle/{table_name.upper()}",
            headers=headers,
            params=params,
            timeout=self.timeout_default
        )

        if response.status_code == 200:
            return response.text
        else:
            raise SAPADTError(
                f"Failed to get table contents",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

    def run_query(self, sql_query, row_number=100, decode=False):
        """Execute SQL query on SAP database

        IMPORTANT: Query should be plain SELECT without 'UP TO' clause.
        Use row_number parameter to limit results instead.
        """
        # Use correct Accept header for freestyle data preview
        headers = self._get_headers('application/vnd.sap.adt.datapreview.table.v1+xml')
        headers['Content-Type'] = 'text/plain'

        # Send query as plain text (not XML!)
        # Remove 'UP TO X ROWS' if present - use rowNumber parameter instead
        clean_query = sql_query.strip()

        params = {'rowNumber': row_number}
        if decode:
            params['decode'] = 'true'

        response = self._request_with_csrf_retry(
            'post', f"{self.url}/sap/bc/adt/datapreview/freestyle",
            headers=headers,
            data=clean_query.encode('utf-8'),
            params=params,
        )

        if response.status_code == 200:
            return response.text
        else:
            raise SAPADTError(
                f"Failed to run query",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

    def delete_object(self, object_url, lock_handle, transport=None):
        """Delete an ABAP object.

        Bug 18b: INDEX (and other CL4/S4 systems) reject the `X-sap-adt-lockHandle`
        header form with HTTP 423 — the lockHandle must be passed as a URL query
        parameter (mirroring `unlock_object()`). Try the query-param approach first,
        then fall back to the header-based variants for older SAP releases.
        """
        from urllib.parse import quote

        if self.debug_enabled:
            self._debug(f"[DEBUG] delete_object - URL: {object_url}, lock_handle: {lock_handle[:50] if lock_handle else 'None'}..., transport: {transport}")

        has_lock = bool(lock_handle) and lock_handle != 'NO_LOCK_SUPPORT'

        def try_delete(lock_as_param: bool, lock_as_header: bool, corr_as_param: bool):
            headers = self._get_headers()
            params = {}

            if lock_as_header and has_lock:
                headers['X-sap-adt-lockHandle'] = lock_handle
            if lock_as_param and has_lock:
                params['lockHandle'] = quote(lock_handle)
            if corr_as_param and transport:
                params['corrNr'] = transport

            if self.debug_enabled:
                self._debug(
                    f"[DEBUG] delete_object attempt - lock_as_param: {lock_as_param}, "
                    f"lock_as_header: {lock_as_header}, corr_as_param: {corr_as_param}, corrNr: {transport}"
                )

            response = self._request_with_csrf_retry(
                'delete', f"{self.url}{object_url}",
                headers=headers,
                params=params,
                timeout=self.timeout_short,
            )

            if self.debug_enabled:
                self._debug(f"[DEBUG] delete_object response - status: {response.status_code}, text: {response.text[:500]}")

            return response

        # Approach tuple: (lock_as_param, lock_as_header, corr_as_param, description)
        # Query-param lockHandle goes first — matches unlock_object() and works on
        # INDEX (HTTP 423 with header-only form on that system).
        delete_approaches = [
            (True,  False, True,  'lockHandle query + corrNr query'),
            (True,  False, False, 'lockHandle query only'),
            (False, True,  False, 'lock header only (legacy)'),
            (False, False, True,  'corrNr query only'),
            (False, True,  True,  'lock header + corrNr query (legacy)'),
        ]
        if not has_lock:
            # NO_LOCK_SUPPORT or missing lock_handle: don't send any lockHandle variant
            delete_approaches = [(False, False, cp, desc) for (_, _, cp, desc) in delete_approaches]
            delete_approaches.insert(0, (False, False, False, 'no lock, no transport'))
        if not transport:
            delete_approaches = [(lp, lh, cp, desc) for (lp, lh, cp, desc) in delete_approaches if not cp]
        # Deduplicate while preserving order (happens after filtering above)
        seen = set()
        delete_approaches = [a for a in delete_approaches if not (a[:3] in seen or seen.add(a[:3]))]

        if self.debug_enabled:
            self._debug(f"[DEBUG] delete_object - will try {len(delete_approaches)} approaches")

        last_response = None
        for lock_as_param, lock_as_header, corr_as_param, desc in delete_approaches:
            if self.debug_enabled:
                self._debug(f"[DEBUG] delete_object - trying approach: {desc}")
            response = try_delete(lock_as_param, lock_as_header, corr_as_param)
            last_response = response
            if response.status_code in [200, 204]:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] delete_object - success with approach: {desc}")
                return {'success': True, 'message': 'Object deleted successfully'}

        status = last_response.status_code if last_response else 'unknown'
        text = last_response.text if last_response else 'no response'
        if self.debug_enabled:
            self._debug(f"[DEBUG] delete_object - all approaches failed, final status: {status}")

        if lock_handle == 'NO_LOCK_SUPPORT' and status in [400, 403]:
            raise SAPLockError(
                f"Failed to delete object: {status}. "
                "This SAP system requires a lock handle for deletion, but the lock endpoint is not supported.",
                status_code=status,
                response_text=text[:500] if text else None
            )
        raise SAPADTError(
            f"Failed to delete object",
            status_code=status if isinstance(status, int) else None,
            response_text=text[:500] if text else None
        )

    # ===== DDIC Object Creation Methods =====

    def _get_domain_typeinfo(self, domain_name):
        """Read a domain's active type information (datatype, length, decimals).

        Needed for the dtel:dataElement payload — SAP requires these in the DTEL
        body even when bound to a domain (playbook adt-domain-dtel.md §26.2).

        Returns:
            (datatype:str, length:str, decimals:str) — length/decimals as plain
            integers (leading zeros stripped). Falls back to ('CHAR','0','0') if
            the domain cannot be read, so the caller can still attempt create.
        """
        import re
        if not self.csrf_token:
            self.fetch_csrf_token()
        try:
            headers = self._get_headers()
            headers['Accept'] = 'application/vnd.sap.adt.domains.v2+xml, application/*'
            r = self.session.get(
                f"{self.url}/sap/bc/adt/ddic/domains/{domain_name.lower()}",
                headers=headers,
                params={'sap-client': self.client, 'sap-language': self.language},
                timeout=self.timeout_default,
            )
            if r.status_code != 200:
                return ('CHAR', '0', '0')
            txt = r.text
            dt = re.search(r'<doma:datatype>([^<]+)</doma:datatype>', txt)
            ln = re.search(r'<doma:length>([^<]+)</doma:length>', txt)
            dc = re.search(r'<doma:decimals>([^<]+)</doma:decimals>', txt)
            datatype = dt.group(1).strip() if dt else 'CHAR'
            length = str(int(ln.group(1))) if ln else '0'
            decimals = str(int(dc.group(1))) if dc else '0'
            return (datatype, length, decimals)
        except Exception:
            return ('CHAR', '0', '0')

    def create_dataelement(self, name, domain_name, description, package_name,
                          short_label=None, medium_label=None, long_label=None,
                          heading_label=None, transport=None):
        """Create a data element

        Args:
            name: Data element name (e.g., 'ZSD000_E_MODEL')
            domain_name: Domain name (e.g., 'CHAR200')
            description: Description text
            package_name: Package name
            short_label: Short field label (max 10 chars, default: description[:10])
            medium_label: Medium field label (max 20 chars, default: description[:20])
            long_label: Long field label (max 40 chars, default: description[:40])
            heading_label: Heading label (max 55 chars, default: description[:55])
            transport: Transport request number

        Returns:
            dict with success status and object URL
        """
        # Ensure we have CSRF token
        if not self.csrf_token:
            self.fetch_csrf_token()

        # Default labels from description
        short_label = short_label or description[:10]
        medium_label = medium_label or description[:20]
        long_label = long_label or description[:40]
        heading_label = heading_label or description[:55]

        # Resolve underlying domain's data type / length / decimals — required in
        # the dtel:dataElement block (SAP rejects/ignores otherwise → "No domain
        # or data type was defined" on activate). Read the domain's active metadata.
        dom_datatype, dom_length, dom_decimals = self._get_domain_typeinfo(domain_name)

        # Build XML body — playbook adt-domain-dtel.md §26.2 ÇALIŞAN payload.
        # Eski `dtel:wbobj` (http://www.sap.com/wbobj/dictionary/dtel) namespace'i
        # SAP parser tarafından YOK SAYILIYOR → typeName/labels yazılmıyordu.
        # Doğru kök: blue:wbobj + nested dtel:dataElement; TÜM zorunlu adtcore
        # attribute'lar (responsible/abapLanguageVersion/language) dolu olmalı.
        dtel_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<blue:wbobj adtcore:responsible="{self.user}"
            adtcore:masterLanguage="{self.language}"
            adtcore:abapLanguageVersion="standard"
            adtcore:name="{name.upper()}"
            adtcore:type="DTEL/DE"
            adtcore:description="{description}"
            adtcore:language="{self.language}"
            xmlns:blue="http://www.sap.com/wbobj/dictionary/dtel"
            xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
  <dtel:dataElement xmlns:dtel="http://www.sap.com/adt/dictionary/dataelements">
    <dtel:typeKind>domain</dtel:typeKind>
    <dtel:typeName>{domain_name.upper()}</dtel:typeName>
    <dtel:dataType>{dom_datatype}</dtel:dataType>
    <dtel:dataTypeLength>{dom_length}</dtel:dataTypeLength>
    <dtel:dataTypeDecimals>{dom_decimals}</dtel:dataTypeDecimals>
    <dtel:shortFieldLabel>{short_label}</dtel:shortFieldLabel>
    <dtel:shortFieldLength>{len(short_label)}</dtel:shortFieldLength>
    <dtel:shortFieldMaxLength>10</dtel:shortFieldMaxLength>
    <dtel:mediumFieldLabel>{medium_label}</dtel:mediumFieldLabel>
    <dtel:mediumFieldLength>{len(medium_label)}</dtel:mediumFieldLength>
    <dtel:mediumFieldMaxLength>20</dtel:mediumFieldMaxLength>
    <dtel:longFieldLabel>{long_label}</dtel:longFieldLabel>
    <dtel:longFieldLength>{len(long_label)}</dtel:longFieldLength>
    <dtel:longFieldMaxLength>40</dtel:longFieldMaxLength>
    <dtel:headingFieldLabel>{heading_label}</dtel:headingFieldLabel>
    <dtel:headingFieldLength>{len(heading_label)}</dtel:headingFieldLength>
    <dtel:headingFieldMaxLength>55</dtel:headingFieldMaxLength>
    <dtel:searchHelp/>
    <dtel:searchHelpParameter/>
    <dtel:setGetParameter/>
    <dtel:defaultComponentName/>
    <dtel:deactivateInputHistory>false</dtel:deactivateInputHistory>
    <dtel:changeDocument>false</dtel:changeDocument>
    <dtel:leftToRightDirection>false</dtel:leftToRightDirection>
    <dtel:deactivateBIDIFiltering>false</dtel:deactivateBIDIFiltering>
  </dtel:dataElement>
</blue:wbobj>'''

        params = {'sap-language': self.language}
        if transport:
            params['corrNr'] = transport

        def do_request():
            # Rebuild headers inside the closure so CSRF-refresh retries pick up
            # the fresh token (see fetch_csrf_token force_refresh path).
            headers = self._get_headers(
                'application/vnd.sap.adt.dataelements.v2+xml',
                'application/vnd.sap.adt.dataelements.v2+xml'
            )
            return self.session.post(
                f"{self.url}/sap/bc/adt/ddic/dataelements",
                headers=headers,
                data=dtel_xml.encode('utf-8'),
                params=params,
                timeout=self.timeout_default
            )

        response = self._retry_request(do_request, f'Create data element {name}')

        if response.status_code in [200, 201]:
            object_url = response.headers.get('Location', f'/sap/bc/adt/ddic/dataelements/{name.lower()}')
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Data element {name} created successfully'
            }
        if response.status_code == 405 and 'AlreadyExists' in response.text:
            object_url = f'/sap/bc/adt/ddic/dataelements/{name.lower()}'
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Data element {name} already exists'
            }
        raise SAPADTError(
            f"Failed to create data element {name}",
            status_code=response.status_code,
            response_text=response.text,
            endpoint='/sap/bc/adt/ddic/dataelements'
        )

    # Validation Helpers
    def _validate_object_name(self, name, object_type='Object'):
        """Validate object name follows SAP naming conventions

        Args:
            name: Object name to validate
            object_type: Type description for error message

        Raises:
            SAPValidationError: If name is invalid
        """
        if not name:
            raise SAPValidationError(
                f"{object_type} name cannot be empty",
                field='name'
            )

        if not isinstance(name, str):
            raise SAPValidationError(
                f"{object_type} name must be a string",
                field='name',
                value=type(name).__name__
            )

        # Check length (SAP names max 30 chars for most objects)
        if len(name) > 30:
            raise SAPValidationError(
                f"{object_type} name too long (max 30 characters): {len(name)}",
                field='name',
                value=name
            )

        # Check for invalid characters

        if not re.match(r'^[A-Z][A-Z0-9_]*$', name):
            raise SAPValidationError(
                f"{object_type} name must start with letter and contain only A-Z, 0-9, underscore: {name}",
                field='name',
                value=name
            )

    def _validate_package_name(self, package_name):
        """Validate package name exists and is properly formatted

        Args:
            package_name: Package name

        Raises:
            SAPValidationError: If package name is invalid
        """
        if not package_name:
            raise SAPValidationError(
                "Package name is required",
                field='package'
            )

        if len(package_name) > 30:
            raise SAPValidationError(
                f"Package name too long (max 30 characters): {len(package_name)}",
                field='package',
                value=package_name
            )

    def _validate_transport(self, transport):
        """Validate transport request number format

        Args:
            transport: Transport request number

        Raises:
            SAPValidationError: If transport format is invalid
        """
        if transport and not isinstance(transport, str):
            raise SAPValidationError(
                "Transport must be a string",
                field='transport'
            )

    def _validate_datatype(self, datatype, length=None, decimals=None):
        """Validate DDIC datatype parameters

        Args:
            datatype: Data type (CHAR, NUMC, INT4, etc.)
            length: Field length
            decimals: Number of decimal places

        Raises:
            SAPValidationError: If parameters are invalid
        """
        valid_types = ['CHAR', 'NUMC', 'INT4', 'INT8', 'INT1', 'INT2', 'CURR', 'QUAN', 'FLTP', 'DATS', 'TIMS', 'ACCP', 'RAW', 'CLNT', 'LANG', 'LCHR', 'STRG', 'DEC', 'D16D34', 'D34D34S', 'DF16_DEC', 'DF34_DEC']
        datatype_upper = datatype.upper() if datatype else ''

        if datatype_upper not in valid_types:
            raise SAPValidationError(
                f"Invalid datatype: {datatype}. Valid types: {', '.join(valid_types[:10])}...",
                field='datatype',
                value=datatype
            )

        # Type-specific validation
        if datatype_upper in ['CHAR', 'NUMC', 'RAW', 'LCHR']:
            if not length or length <= 0:
                raise SAPValidationError(
                    f"Length must be positive for {datatype}",
                    field='length',
                    value=length
                )
            if length > 1333:
                raise SAPValidationError(
                    f"Length too long for {datatype} (max 1333): {length}",
                    field='length',
                    value=length
                )

        if datatype_upper in ['CURR', 'QUAN', 'DEC']:
            if decimals is not None and decimals < 0:
                raise SAPValidationError(
                    f"Decimals cannot be negative: {decimals}",
                    field='decimals',
                    value=decimals
                )

    def create_domain(self, name, datatype, length, description, package_name,
                     decimals=0, lowercase=False, fixed_values=None, transport=None):
        """Create a domain

        Args:
            name: Domain name (e.g., 'ZSD000_D_MODEL')
            datatype: Data type (e.g., 'CHAR', 'NUMC', 'INT4')
            length: Length (e.g., 200 for CHAR200)
            description: Description text
            package_name: Package name
            decimals: Number of decimal places (default: 0)
            lowercase: Allow lowercase (default: False)
            fixed_values: List of dicts with 'value' and 'text' keys, e.g.:
                         [{'value': 'A', 'text': 'Option A'}, {'value': 'B', 'text': 'Option B'}]
            transport: Transport request number

        Returns:
            dict with success status and object URL

        Raises:
            SAPValidationError: If parameters are invalid
            SAPConnectionError: If connection fails
            SAPADTError: If SAP API returns error
        """
        # Validate inputs
        self._validate_object_name(name, 'Domain')
        self._validate_package_name(package_name)
        self._validate_datatype(datatype, length, decimals)
        self._validate_transport(transport)

        # Ensure we have CSRF token
        if not self.csrf_token:
            self.fetch_csrf_token()

        # Format length and decimals with leading zeros
        length_str = str(length).zfill(6)
        decimals_str = str(decimals).zfill(6)

        # Build fixed values XML
        fix_values_xml = ''
        if fixed_values:
            fix_values_xml = '<doma:fixValues>'
            for idx, fv in enumerate(fixed_values, start=1):
                value = fv.get('value', '')
                text = fv.get('text', value)
                fix_values_xml += f'''<doma:fixValue>
      <doma:position>{str(idx).zfill(4)}</doma:position>
      <doma:low>{value}</doma:low>
      <doma:high/>
      <doma:text>{text}</doma:text>
    </doma:fixValue>'''
            fix_values_xml += '</doma:fixValues>'
        else:
            fix_values_xml = '<doma:fixValues/>'

        # Build XML body
        domain_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<doma:domain adtcore:name="{name.upper()}"
             adtcore:type="DOMA/DD"
             adtcore:description="{description}"
             adtcore:masterLanguage="{self.language}"
             xmlns:doma="http://www.sap.com/dictionary/domain"
             xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
  <doma:content>
    <doma:typeInformation>
      <doma:datatype>{datatype.upper()}</doma:datatype>
      <doma:length>{length_str}</doma:length>
      <doma:decimals>{decimals_str}</doma:decimals>
    </doma:typeInformation>
    <doma:outputInformation>
      <doma:length>{length_str}</doma:length>
      <doma:style>00</doma:style>
      <doma:conversionExit/>
      <doma:signExists>false</doma:signExists>
      <doma:lowercase>{"true" if lowercase else "false"}</doma:lowercase>
      <doma:ampmFormat>false</doma:ampmFormat>
    </doma:outputInformation>
    <doma:valueInformation>
      <doma:valueTableRef/>
      <doma:appendExists>false</doma:appendExists>
      {fix_values_xml}
    </doma:valueInformation>
  </doma:content>
</doma:domain>'''

        params = {}
        if transport:
            params['corrNr'] = transport

        # Use retry logic for the POST request
        def do_request():
            # Rebuild headers inside the closure so CSRF-refresh retries pick up
            # the fresh token.
            headers = self._get_headers(
                'application/vnd.sap.adt.domains.v2+xml',
                'application/vnd.sap.adt.domains.v2+xml'
            )
            return self.session.post(
                f"{self.url}/sap/bc/adt/ddic/domains",
                headers=headers,
                data=domain_xml.encode('utf-8'),
                params=params,
                timeout=self.timeout_default
            )

        response = self._retry_request(do_request, f'Create domain {name}')

        if response.status_code in [200, 201]:
            object_url = response.headers.get('Location', f'/sap/bc/adt/ddic/domains/{name.lower()}')
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Domain {name} created successfully'
            }
        if response.status_code == 405 and 'AlreadyExists' in response.text:
            object_url = f'/sap/bc/adt/ddic/domains/{name.lower()}'
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Domain {name} already exists'
            }
        else:
            raise SAPADTError(
                f"Failed to create domain {name}",
                status_code=response.status_code,
                response_text=response.text,
                endpoint='/sap/bc/adt/ddic/domains'
            )

    def _validate_structure_fields(self, fields):
        """Validate structure field definitions

        Args:
            fields: List of field definitions

        Raises:
            SAPValidationError: If fields are invalid
        """
        if not fields or not isinstance(fields, list):
            raise SAPValidationError(
                "Fields must be a non-empty list",
                field='fields'
            )

        for idx, field in enumerate(fields):
            if 'name' not in field:
                raise SAPValidationError(
                    f"Field at index {idx} missing 'name' attribute",
                    field='fields'
                )
            if 'type' not in field:
                raise SAPValidationError(
                    f"Field '{field.get('name')}' missing 'type' attribute",
                    field='fields'
                )

    def create_structure(self, name, fields, description, package_name, transport=None):
        """Create a structure (INTTAB) using blue source format

        Args:
            name: Structure name (e.g., 'ZSD000_S_CUSTOMER')
            fields: List of field definitions. Each field is a dict with:
                - 'name': Field name
                - 'type': ABAP type (e.g., 'char10', 'numc8', 'ZSD000_E_STATUS' for data elements)
                - 'description': Field description (optional, used for comments)
            description: Structure description text
            package_name: Package name
            transport: Transport request number

        Returns:
            dict with success status and object URL

        Raises:
            SAPValidationError: If parameters are invalid
            SAPConnectionError: If connection fails
            SAPADTError: If SAP API returns error

        Examples:
            # Simple structure with predefined types
            create_structure('ZSD000_S_TEST', [
                {'name': 'FIELD1', 'type': 'char10'},
                {'name': 'FIELD2', 'type': 'numc8'}
            ], 'Test structure', 'ZSD000')

            # Structure with data elements
            create_structure('ZSD000_S_STATUS', [
                {'name': 'STATUS', 'type': 'ZSD000_E_STATUS'}
            ], 'Status info', 'ZSD000')
        """
        # Validate inputs
        self._validate_object_name(name, 'Structure')
        self._validate_package_name(package_name)
        self._validate_structure_fields(fields)
        self._validate_transport(transport)

        # Ensure we have CSRF token
        if not self.csrf_token:
            self.fetch_csrf_token()

        # Build field definitions (ABAP structure syntax)
        field_lines = []
        for field in fields:
            field_name = field.get('name', '')
            field_type = field.get('type', 'char10')
            field_desc = field.get('description', '')

            # Add comment if description provided
            if field_desc:
                field_lines.append(f'  "// {field_desc}')
            field_lines.append(f'  {field_name}: {field_type};')

        fields_source = '\n'.join(field_lines)

        # Build XML with blueSource format
        structure_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<blue:blueSource xmlns:blue="http://www.sap.com/wbobj/blue"
                  xmlns:adtcore="http://www.sap.com/adt/core"
                  adtcore:name="{name.upper()}"
                  adtcore:description="{description}"
                  adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
  <blue:source>structure {name.upper()} {{
{fields_source}
}}</blue:source>
</blue:blueSource>'''

        params = {}
        if transport:
            params['corrNr'] = transport

        # Use retry logic
        def do_request():
            # Rebuild headers inside the closure so CSRF-refresh retries pick up
            # the fresh token.
            headers = self._get_headers(
                'application/vnd.sap.adt.structures.v2+xml',
                'application/vnd.sap.adt.structures.v2+xml'
            )
            return self.session.post(
                f"{self.url}/sap/bc/adt/ddic/structures",
                headers=headers,
                data=structure_xml.encode('utf-8'),
                params=params,
                timeout=self.timeout_default
            )

        response = self._retry_request(do_request, f'Create structure {name}')

        if response.status_code in [200, 201]:
            object_url = response.headers.get('Location', f'/sap/bc/adt/ddic/structures/{name.lower()}')
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Structure {name} created successfully'
            }
        if response.status_code == 405 and 'AlreadyExists' in response.text:
            object_url = f'/sap/bc/adt/ddic/structures/{name.lower()}'
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Structure {name} already exists'
            }
        else:
            raise SAPADTError(
                f"Failed to create structure {name}",
                status_code=response.status_code,
                response_text=response.text,
                endpoint='/sap/bc/adt/ddic/structures'
            )

    def create_table(self, name, description, package_name, fields=None,
                     ref_structure=None, transport=None, table_category='TRANSP',
                     delivery_class='A', data_maintenance='RESTRICTED',
                     include_mandt=True):
        """Create a database table using blue source format with annotations

        Technical Settings (defaults - applied automatically by SAP):
            - Datenart (Data Class): APPL0
            - Größenkategorie (Size Category): 0
            - Pufferung (Buffering): nicht erlaubt (not allowed)
            - Protokollierung (Logging): ausgeschaltet (off)

        Args:
            name: Table name (e.g., 'ZSD000_T_CUSTOMER')
            description: Table description text
            package_name: Package name
            fields: List of field definitions (mutually exclusive with ref_structure)
                Each field is a dict with:
                - 'name': Field name
                - 'type': ABAP type (e.g., 'char10', 'numc8', or data element name)
                - 'key': True if this is a key field (default: False)
                - 'null': True if null allowed (default: False)
                - 'description': Field description (optional, for comments)
                Note: MANDT is auto-added as first key field unless include_mandt=False
            ref_structure: Name of existing structure to reference (optional)
                If provided, fields parameter is ignored
            transport: Transport request number
            table_category: Table type - 'TRANSP' (transparent), 'POOL', 'CLUSTER' (default: 'TRANSP')
            delivery_class: Delivery class (default: 'A')
                - 'A': Application table (master/transaction data)
                - 'C': Customizing table
                - 'L': Temporary data, delivered empty
                - 'G': Customizing table, protected against SAP update
                - 'E': Control table, SAP and customer have separate key areas
                - 'S': System table, maintained only by SAP
                - 'W': System table, contents transportable via own TR objects
            data_maintenance: Data Browser/Table View Editing (default: 'RESTRICTED')
                - 'ALLOWED': Display/Maintenance Allowed (space in SE11)
                - 'RESTRICTED': Display/Maintenance Allowed with Restrictions
                - 'NOT_ALLOWED': Display/Maintenance Not Allowed
                - 'LIMITED': Only Display, No Maintenance
            include_mandt: Auto-add MANDT as first key field (default: True)
                Set to False only for client-independent tables

        Returns:
            dict with success status and object URL

        Examples:
            # Table with direct field definitions (MANDT auto-added)
            create_table('ZSD000_T_CUSTOMER', 'Customer table', 'ZSD000',
                        fields=[
                            {'name': 'ID', 'type': 'char10', 'key': True},
                            {'name': 'NAME', 'type': 'char50'}
                        ],
                        transport='TRXXXXXX')

            # Table referencing existing structure (recommended)
            create_table('ZSD000_T_DATA', 'Data table', 'ZSD000',
                        ref_structure='ZSD000_S_CUSTOMER',
                        transport='TRXXXXXX')
        """
        # Validate inputs
        self._validate_object_name(name, 'Table')
        self._validate_package_name(package_name)
        self._validate_transport(transport)

        # Validate table parameters
        if fields and ref_structure:
            raise SAPValidationError(
                "Cannot specify both 'fields' and 'ref_structure'",
                field='fields'
            )

        if not fields and not ref_structure:
            raise SAPValidationError(
                "Must specify either 'fields' or 'ref_structure'",
                field='fields'
            )

        # Validate table category
        valid_categories = ['TRANSP', 'POOL', 'CLUSTER', 'VIEW']
        if table_category.upper() not in valid_categories:
            raise SAPValidationError(
                f"Invalid table_category '{table_category}'. Valid: {', '.join(valid_categories)}",
                field='table_category',
                value=table_category
            )

        # Validate delivery class
        valid_delivery = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'K', 'L', 'P', 'R', 'S', 'W']
        if delivery_class.upper() not in valid_delivery:
            raise SAPValidationError(
                f"Invalid delivery_class '{delivery_class}'. Valid: {', '.join(valid_delivery)}",
                field='delivery_class',
                value=delivery_class
            )

        # Validate data maintenance
        valid_maintenance = ['ALLOWED', 'RESTRICTED', 'NOT_ALLOWED', 'LIMITED']
        if data_maintenance.upper() not in valid_maintenance:
            raise SAPValidationError(
                f"Invalid data_maintenance '{data_maintenance}'. Valid: {', '.join(valid_maintenance)}",
                field='data_maintenance',
                value=data_maintenance
            )

        # Map table category to annotation format
        category_map = {
            'TRANSP': 'TRANSPARENT',
            'TRANSPARENT': 'TRANSPARENT',
            'POOL': 'POOL',
            'CLUSTER': 'CLUSTER',
            'VIEW': 'VIEW'
        }
        table_category_annotation = category_map.get(table_category.upper(), 'TRANSPARENT')

        # Ensure we have CSRF token
        if not self.csrf_token:
            self.fetch_csrf_token()

        if ref_structure:
            # Validate structure name format
            self._validate_object_name(ref_structure, 'Referenced Structure')
            # Reference mode: use include structure syntax
            fields_source = f'  include {ref_structure.upper()};'
        else:
            # Direct field definitions
            # Auto-add MANDT as first key field if include_mandt=True
            if include_mandt:
                has_mandt = any(f.get('name', '').upper() == 'MANDT' for f in fields)
                if not has_mandt:
                    fields = [{'name': 'MANDT', 'type': 'mandt', 'key': True}] + list(fields)

            field_lines = []
            for field in fields:
                field_name = field.get('name', '')
                field_type = field.get('type', 'char10')
                is_key = field.get('key', False)
                is_null = field.get('null', False)
                field_desc = field.get('description', '')

                # Add comment if description provided
                if field_desc:
                    field_lines.append(f'  "// {field_desc}')

                # Build field definition
                key_part = 'key ' if is_key else ''
                null_part = 'not null' if not is_null else ''
                null_part = f' {null_part}' if null_part else ''

                field_lines.append(f'  {key_part}{field_name}: {field_type}{null_part};')

            fields_source = '\n'.join(field_lines)

        # Build DDL source with annotations
        ddl_source = f'''@EndUserText.label : '{description}'
@AbapCatalog.tableCategory : #{table_category_annotation}
@AbapCatalog.deliveryClass : #{delivery_class.upper()}
@AbapCatalog.dataMaintenance : #{data_maintenance.upper()}
define table {name.lower()} {{
{fields_source}
}}'''

        # Build XML with blueSource format
        # IMPORTANT: adtcore:type="TABL/DT" is required to create a database table
        # Without it, SAP creates a structure (TABL/DS) instead
        table_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<blue:blueSource xmlns:blue="http://www.sap.com/wbobj/blue"
                  xmlns:adtcore="http://www.sap.com/adt/core"
                  adtcore:name="{name.upper()}"
                  adtcore:type="TABL/DT"
                  adtcore:description="{description}"
                  adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
  <blue:source>{ddl_source}</blue:source>
</blue:blueSource>'''

        headers = self._get_headers(
            'application/vnd.sap.adt.tables.v2+xml',
            'application/vnd.sap.adt.tables.v2+xml'
        )

        params = {}
        if transport:
            params['corrNr'] = transport

        def make_request():
            return self.session.post(
                f"{self.url}/sap/bc/adt/ddic/tables",
                headers=headers,
                data=table_xml.encode('utf-8'),
                params=params,
                timeout=self.timeout_default
            )

        response = self._retry_request(make_request, operation=f'create table {name}')

        if response.status_code in [200, 201]:
            object_url = response.headers.get('Location', f'/sap/bc/adt/ddic/tables/{name.lower()}')
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Table {name} created successfully'
            }
        else:
            raise SAPADTError(
                f"Failed to create table {name}",
                status_code=response.status_code,
                response_text=response.text,
                endpoint='/sap/bc/adt/ddic/tables'
            )

    def _validate_cds_source(self, cds_source):
        """Validate CDS source code

        Args:
            cds_source: CDS DDL source code

        Raises:
            SAPValidationError: If CDS source is invalid
        """
        if not cds_source or not isinstance(cds_source, str):
            raise SAPValidationError(
                "CDS source code must be a non-empty string",
                field='cds_source'
            )

        # Check for required CDS keywords (klasik DEFINE VIEW + RAP view entity + projection desteği)
        cds_upper = cds_source.upper()
        # 'select from' (klasik/interface) VEYA 'projection on' (RAP consumption projection)
        if 'SELECT FROM' not in cds_upper and 'PROJECTION ON' not in cds_upper:
            raise SAPValidationError(
                "CDS source must contain 'SELECT FROM' or 'PROJECTION ON' keyword",
                field='cds_source'
            )
        # Klasik 'define view' VEYA RAP 'define [root] view entity'
        if 'DEFINE VIEW' not in cds_upper and 'VIEW ENTITY' not in cds_upper:
            raise SAPValidationError(
                "CDS source must contain 'DEFINE VIEW' or 'DEFINE [ROOT] VIEW ENTITY' keyword",
                field='cds_source'
            )

    def create_cds_view(self, name, cds_source, description, package_name, transport=None):
        """Create a CDS (Core Data Services) view using DDL source

        Args:
            name: CDS view name (e.g., 'ZSD000_C_CUSTOMER')
            cds_source: CDS DDL source code (SQL-like syntax with annotations)
            description: View description text
            package_name: Package name
            transport: Transport request number

        Returns:
            dict with success status and object URL

        Examples:
            Simple CDS view:
            ```python
            cds_source = '''@AbapCatalog.sqlViewName: 'ZSD000_C_CUSTOMER'
            @AccessControl.authorizationCheck: #CHECK

            define view ZSD000_C_CUSTOMER as
            select from zai_t_customer
            {
              key customer_id,
              customer_name,
              status
            }'''
            ```

            CDS view with WHERE clause:
            ```python
            cds_source = '''@AbapCatalog.sqlViewName: 'ZSD000_C_ACTIVE'
            @EndUserText.label: 'Active Customers'

            define view ZSD000_C_ACTIVE as
            select from zai_t_customer
            {
              key customer_id,
              customer_name
            }
            where status = 'A'
            '''
            ```
        """
        # Validate inputs
        self._validate_object_name(name, 'CDS View')
        self._validate_package_name(package_name)
        self._validate_transport(transport)
        self._validate_cds_source(cds_source)

        # Ensure we have CSRF token
        if not self.csrf_token:
            self.fetch_csrf_token()

        # Build XML with DDL source format
        cds_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ddl:ddlSource xmlns:ddl="http://www.sap.com/adt/ddic/ddlsources"
                 xmlns:adtcore="http://www.sap.com/adt/core"
                 adtcore:name="{name.upper()}"
                 adtcore:description="{description}"
                 adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
  <ddl:sourceMainArtifact>
    <ddl:artifactType>ddlSource</ddl:artifactType>
    <ddl:source>{html.escape(cds_source, quote=False)}</ddl:source>
  </ddl:sourceMainArtifact>
</ddl:ddlSource>'''

        params = {}
        if transport:
            params['corrNr'] = transport

        def make_request():
            # Rebuild headers inside the closure so CSRF force-refresh on retry
            # picks up the FRESH token (self.csrf_token). Eskiden headers dış
            # kapsamda 1 kez kuruluyordu → her retry AYNI bayat token'ı yolluyordu
            # → 3x 403 patinaj (spike vakası). Fix 3.
            headers = self._get_headers(
                'application/vnd.sap.adt.ddlSource+xml',
                'application/vnd.sap.adt.ddlSource+xml'
            )
            return self.session.post(
                f"{self.url}/sap/bc/adt/ddic/ddl/sources",
                headers=headers,
                data=cds_xml.encode('utf-8'),
                params=params,
                timeout=self.timeout_default
            )

        response = self._retry_request(make_request, operation=f'create CDS view {name}')

        if response.status_code in [200, 201]:
            object_url = response.headers.get('Location', f'/sap/bc/adt/ddic/ddl/sources/{name.lower()}')
            return {
                'success': True,
                'object_url': object_url,
                'message': f'CDS view {name} created successfully'
            }
        if response.status_code == 405 and 'AlreadyExists' in response.text:
            object_url = f'/sap/bc/adt/ddic/ddl/sources/{name.lower()}'
            return {
                'success': True,
                'object_url': object_url,
                'message': f'CDS view {name} already exists'
            }
        else:
            raise SAPADTError(
                f"Failed to create CDS view {name}",
                status_code=response.status_code,
                response_text=response.text,
                endpoint='/sap/bc/adt/ddic/ddl/sources'
            )

    def get_ddic_object(self, object_type, name):
        """Get DDIC object XML

        Args:
            object_type: Type ('dataelement', 'domain', 'table', 'structure', 'tabletype')
            name: Object name

        Returns:
            XML string
        """
        type_map = {
            'dataelement': ('application/vnd.sap.adt.dataelements.v2+xml', 'dataelements'),
            'domain': ('application/vnd.sap.adt.domains.v2+xml', 'domains'),
            'table': ('application/vnd.sap.adt.tables.v2+xml', 'tables'),
            'structure': ('application/vnd.sap.adt.structures.v2+xml', 'structures'),
            'tabletype': ('application/vnd.sap.adt.tabletype.v1+xml', 'tabletypes')
        }

        if object_type not in type_map:
            raise ValueError(f"Unsupported DDIC object type: {object_type}")

        accept_type, endpoint = type_map[object_type]
        headers = self._get_headers(accept_type)

        response = self.session.get(
            f"{self.url}/sap/bc/adt/ddic/{endpoint}/{name.lower()}",
            headers=headers,
            timeout=self.timeout_short
        )

        if response.status_code == 200:
            return response.text
        else:
            raise SAPADTError(
                f"Failed to get {object_type}",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

    def create_type_group(self, name, types_and_constants, description, package_name, transport=None):
        """Create a Type Group (TYPE)

        Type groups are legacy ABAP constructs for defining reusable types and constants.
        They use the TYPE-POOLS statement.

        Args:
            name: Type group name (e.g., 'ZSD000_TYPES')
            types_and_constants: ABAP source code containing TYPES and CONSTANTS definitions
                               (should NOT include 'type-pool' statement - that's added automatically)
            description: Short description
            package_name: Development class/package
            transport: Transport request (optional)

        Returns:
            dict with success status and object URL

        Example:
            types_consts = '''
types:
  zai_status_type type c length 1.

constants:
  zai_status_active type zai_status_type value 'A',
  zai_status_inactive type zai_status_type value 'I'.
'''
            create_type_group('ZSD000_TYPES', types_consts, 'ZSD000 Type Definitions', 'ZSD000', 'FIDK901433')
        """
        if not transport:
            raise ValueError("Transport request is required for type group creation")

        # Build the ABAP source code
        # Type groups must start with 'type-pool name.'
        source_code = f"type-pool {name.lower()} .\n\n"
        source_code += f"************************************************************************\n"
        source_code += f"* {description}\n"
        source_code += f"************************************************************************\n\n"
        source_code += types_and_constants.strip()

        # Type groups use atypgr:abapTypeGroup namespace format
        # The source code is uploaded separately
        typegroup_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<atypgr:abapTypeGroup xmlns:atypgr="http://www.sap.com/adt/ddic/typegroups"
                       xmlns:adtcore="http://www.sap.com/adt/core"
                       adtcore:name="{name.upper()}"
                       adtcore:description="{description}"
                       adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
</atypgr:abapTypeGroup>'''

        self.fetch_csrf_token()

        headers = self._get_headers(
            accept_type="application/vnd.sap.adt.ddic.typegroups.v2+xml",
            content_type="application/vnd.sap.adt.ddic.typegroups.v2+xml"
        )

        params = {}
        if transport:
            params['corrNr'] = transport

        # Create type group metadata first
        response = self.session.post(
            f"{self.url}/sap/bc/adt/ddic/typegroups",
            headers=headers,
            data=typegroup_xml.encode('utf-8'),
            params=params,
            timeout=self.timeout_default
        )

        if response.status_code not in [200, 201]:
            if response.status_code == 403 and 'already exists' in response.text.lower():
                object_url = f'/sap/bc/adt/ddic/typegroups/{name.lower()}'
                return {
                    'success': True,
                    'object_url': object_url,
                    'message': f'Type group {name} already exists'
                }
            raise SAPADTError(
                f"Failed to create type group {name}",
                status_code=response.status_code,
                response_text=response.text,
                endpoint='/sap/bc/adt/ddic/typegroups'
            )

        # Now upload the source code
        # The URL is constructed from the type group name (lowercase)
        object_url = f'/sap/bc/adt/ddic/typegroups/{name.lower()}'
        source_url = f"{self.url}{object_url}/source/main"

        source_headers = self._get_headers(
            accept_type="text/plain",
            content_type="text/plain"
        )

        source_response = self.session.put(
            source_url,
            headers=source_headers,
            data=source_code.encode('utf-8'),
            timeout=self.timeout_default
        )

        if source_response.status_code not in [200, 201, 204]:
            raise SAPADTError(
                f"Failed to upload source code",
                status_code=source_response.status_code,
                response_text=source_response.text[:500]
            )

        return {
            'success': True,
            'object_url': object_url,
            'message': f'Type group {name} created successfully'
        }

    def create_function_group(self, name, description, package_name, transport=None):
        """Create a Function Group (FUGR)

        Function groups are containers for function modules. A function group must
        exist before creating function modules within it.

        Args:
            name: Function group name (e.g., 'ZSD000_FG_CUSTOMER')
            description: Short description
            package_name: Development class/package
            transport: Transport request (optional)

        Returns:
            dict with success status and object URL

        Example:
            create_function_group('ZSD000_FG_CUSTOMER', 'Customer Function Modules', 'ZSD000', 'TRXXXXXX')
        """
        if not transport:
            raise ValueError("Transport request is required for function group creation")

        fugr_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<group:abapFunctionGroup xmlns:group="http://www.sap.com/adt/functions/groups"
                         xmlns:adtcore="http://www.sap.com/adt/core"
                         adtcore:name="{name.upper()}"
                         adtcore:description="{description}"
                         adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
</group:abapFunctionGroup>'''

        headers = self._get_headers(
            accept_type="application/vnd.sap.adt.functions.groups.v2+xml",
            content_type="application/vnd.sap.adt.functions.groups.v2+xml"
        )

        params = {}
        if transport:
            params['corrNr'] = transport

        # Use CSRF-retry wrapper: a stale/expired CSRF token returns 403 and was
        # the observed root cause of FG/FM creation failures (deferred-trigger C1).
        response = self._request_with_csrf_retry(
            'post',
            f"{self.url}/sap/bc/adt/functions/groups",
            headers=headers,
            data=fugr_xml.encode('utf-8'),
            params=params,
            timeout=self.timeout_default
        )

        if response.status_code in [200, 201]:
            object_url = f'/sap/bc/adt/functions/groups/{name.lower()}'
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Function group {name} created successfully'
            }
        if response.status_code == 405 and 'AlreadyExists' in response.text:
            object_url = f'/sap/bc/adt/functions/groups/{name.lower()}'
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Function group {name} already exists'
            }
        raise SAPADTError(
            f"Failed to create function group {name}",
            status_code=response.status_code,
            response_text=response.text,
            endpoint='/sap/bc/adt/functions/groups'
        )

    def create_function_module(self, name, function_group, description, import_params=None,
                              export_params=None, changing_params=None, tables=None,
                              exceptions=None, transport=None):
        """Create a Function Module shell within a Function Group.

        Notes (verified live on <SYSTEM_ID>, ADR 0005 / C1):
          * The ADT create endpoint accepts ONLY name + description + masterLanguage.
            Adding ``fmodule:processingType`` as a create attribute is rejected with
            HTTP 400 "Unexpected Case in Branch" — so RFC-enabling ('Remote-Enabled
            Module') is NOT a create attribute; it is a one-time SE37 toggle.
          * The interface (IMPORTING/EXPORTING/CHANGING/TABLES/EXCEPTIONS) IS set via
            source push — but as INLINE ABAP clauses after the FUNCTION line, NOT the
            SE37-style *" comment block (which ADT rejects). So the full flow is:
            create shell (here) -> push full source incl. inline signature via
            set_function_module_source() -> activate. (ZSD001_FM_SO_CREATE pattern.)

        Args:
            name: Function module name (e.g., 'ZSD000_GET_CUSTOMER')
            function_group: Parent function group name (must exist)
            description: Short description
            import_params/export_params/changing_params/tables/exceptions: reserved
                (signature is written as inline clauses in the pushed source).
            transport: Transport request (required for Z objects)

        Returns:
            dict with success status and object URL
        """
        if not transport:
            raise ValueError("Transport request is required for function module creation")

        # ADR 0005 D: Z objects must carry masterLanguage so SAP stores the short text
        # under the TR login language (not the EN default).  No processingType here —
        # it is rejected at create time (see docstring); RFC-enable is a SE37 step.
        fm_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<fmodule:abapFunctionModule xmlns:fmodule="http://www.sap.com/adt/functions/fmodules"
                            xmlns:adtcore="http://www.sap.com/adt/core"
                            adtcore:name="{name.upper()}"
                            adtcore:description="{description}"
                            adtcore:masterLanguage="{self.language}">
</fmodule:abapFunctionModule>'''

        headers = self._get_headers(
            accept_type="application/vnd.sap.adt.functions.fmodules.v2+xml",
            content_type="application/vnd.sap.adt.functions.fmodules+xml"
        )

        params = {}
        if transport:
            params['corrNr'] = transport

        # CSRF-retry wrapper: stale CSRF token -> 403 was the FM-create root cause.
        response = self._request_with_csrf_retry(
            'post',
            f"{self.url}/sap/bc/adt/functions/groups/{function_group.lower()}/fmodules",
            headers=headers,
            data=fm_xml.encode('utf-8'),
            params=params,
            timeout=self.timeout_default
        )

        object_url = f'/sap/bc/adt/functions/groups/{function_group.lower()}/fmodules/{name.lower()}'

        if response.status_code in [200, 201]:
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Function module {name} created (shell; push full source incl. '
                           f'inline signature via set_function_module_source, then activate)'
            }
        # Already-exists is reported as 405 (AlreadyExists) on some releases and as
        # 400 ExceptionResourceAlreadyExists on this system — treat both as idempotent.
        already = (
            (response.status_code == 405 and 'AlreadyExists' in response.text) or
            (response.status_code == 400 and 'AlreadyExists' in response.text)
        )
        if already:
            return {
                'success': True,
                'object_url': object_url,
                'message': f'Function module {name} already exists'
            }
        raise SAPADTError(
            f"Failed to create function module {name}",
            status_code=response.status_code,
            response_text=response.text[:500],
            endpoint=f'/sap/bc/adt/functions/groups/{function_group.lower()}/fmodules'
        )

    def set_function_module_source(self, name, function_group, source_code,
                                   transport=None, activate=False):
        """Push the full source of a function module and (optionally) activate it.

        Uses the proven FM push pattern (playbook adt-foundation.md §3.2): a tight
        stateful LOCK -> PUT /source/main -> activate -> UNLOCK in ONE session with a
        single CSRF token.  The generic set_object_source() is NOT used here — its
        ETag pre-fetch + 4 transport-approach retries break the stateful lock and the
        PUT fails with 423 InvalidLockHandle (verified live 2026-06-02).

        Args:
            name: Function module name
            function_group: Parent function group name
            source_code: Full FUNCTION ... ENDFUNCTION source. The interface MUST be
                written as inline ABAP clauses (IMPORTING/EXPORTING/CHANGING/TABLES/
                EXCEPTIONS) directly after the FUNCTION line — NOT as the SE37-style
                *" comment block, which ADT rejects ("Parameter comment blocks are not
                allowed"). The signature is set from these inline clauses on push, so
                no SE37 signature step is needed. (Verified: ZSD001_FM_SO_CREATE.)
                NOTE: RFC-enabling ('Remote-Enabled Module') is a separate one-time
                SE37 toggle — it is NOT an ADT create attribute.
            transport: Transport request
            activate: When True, activate the function module after the push

        Returns:
            dict with success status, object_url and (if activated) activation result
        """
        fg = function_group.lower()
        fm = name.lower()
        fm_url = f'/sap/bc/adt/functions/groups/{fg}/fmodules/{fm}'
        base = f"{self.url}{fm_url}"

        # Stateful session so the lock survives across LOCK -> PUT in the same session.
        prev_sessiontype = self.session.headers.get('X-sap-adt-sessiontype')
        self.session.headers['X-sap-adt-sessiontype'] = 'stateful'
        self.fetch_csrf_token(force_refresh=True)
        csrf = self.csrf_token

        lock_handle = None
        try:
            lock = self.session.post(
                base,
                params={'_action': 'LOCK', 'accessMode': 'MODIFY'},
                headers={'X-CSRF-Token': csrf,
                         'Content-Type': 'application/vnd.sap.as+xml',
                         'Accept': 'application/vnd.sap.adt.lock.v1+xml',
                         'X-sap-adt-corrNr': transport or ''},
                data='', timeout=self.timeout_default)
            if lock.status_code != 200:
                raise SAPADTError(f"FM lock failed for {name}",
                                  status_code=lock.status_code,
                                  response_text=lock.text[:500], endpoint=fm_url)
            lock_handle = next(
                (e.text for e in ET.fromstring(lock.text).iter()
                 if e.tag.endswith('LOCK_HANDLE')), None)
            if not lock_handle:
                raise SAPADTError(f"FM lock returned no handle for {name}",
                                  status_code=lock.status_code,
                                  response_text=lock.text[:500], endpoint=fm_url)

            put = self.session.put(
                base + '/source/main',
                params={'lockHandle': lock_handle, 'corrNr': transport},
                headers={'X-CSRF-Token': csrf,
                         'Content-Type': 'text/plain; charset=utf-8'},
                data=source_code.encode('utf-8'), timeout=self.timeout_default)
            if put.status_code not in (200, 201):
                raise SAPADTError(f"FM source push failed for {name}",
                                  status_code=put.status_code,
                                  response_text=put.text[:500],
                                  endpoint=fm_url + '/source/main')
        finally:
            if lock_handle:
                try:
                    self.session.post(base, params={'_action': 'UNLOCK',
                                                    'lockHandle': lock_handle},
                                      headers={'X-CSRF-Token': csrf},
                                      timeout=self.timeout_short)
                except Exception:
                    pass
            # Restore prior session type.
            if prev_sessiontype is None:
                self.session.headers.pop('X-sap-adt-sessiontype', None)
            else:
                self.session.headers['X-sap-adt-sessiontype'] = prev_sessiontype

        out = {'success': True, 'object_url': fm_url,
               'message': f'Function module {name} source pushed'}

        # Activate via activate_object() — its CSRF-retry handles the fresh-token
        # requirement (the in-session token 403s on the activation endpoint).
        if activate:
            out['activation'] = self.activate_object(name.upper(), fm_url)
            act = out['activation']
            out['success'] = bool(act.get('success', True)) if isinstance(act, dict) else True

        return out

    def where_used(self, object_url):
        """Find where an object is used (Where-Used List)

        Args:
            object_url: Object URL (e.g., '/sap/bc/adt/oo/classes/zcl_my_class')

        Returns:
            list of dicts with 'name', 'type', 'uri', 'description'
        """
        headers = self._get_headers('application/*')
        headers['Content-Type'] = 'application/*'

        # URI goes as query parameter, XML body contains empty affectedObjects
        body = '''<?xml version="1.0" encoding="ASCII"?>
<usagereferences:usageReferenceRequest xmlns:usagereferences="http://www.sap.com/adt/ris/usageReferences">
  <usagereferences:affectedObjects/>
</usagereferences:usageReferenceRequest>'''

        response = self._request_with_csrf_retry(
            'post',
            f"{self.url}/sap/bc/adt/repository/informationsystem/usageReferences",
            headers=headers,
            params={'uri': object_url},
            data=body.encode('utf-8')
        )

        if response.status_code != 200:
            raise SAPADTError(
                "Where-used search failed",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        results = []
        try:
            root = ET.fromstring(response.text)
            # Walk referencedObject elements and extract child adtObject info
            for ref_obj in root.iter():
                ref_tag = ref_obj.tag.split('}')[-1] if '}' in ref_obj.tag else ref_obj.tag
                if ref_tag != 'referencedObject':
                    continue
                ref_attrs = {k.split('}')[-1] if '}' in k else k: v for k, v in ref_obj.attrib.items()}
                ref_uri = ref_attrs.get('uri', '')
                # Find child adtObject (first child, not packageRef)
                for child in ref_obj:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if child_tag != 'adtObject':
                        continue
                    child_attrs = {k.split('}')[-1] if '}' in k else k: v for k, v in child.attrib.items()}
                    name = child_attrs.get('name', '')
                    obj_type = child_attrs.get('type', '')
                    desc = child_attrs.get('description', '')
                    if name and obj_type:
                        results.append({
                            'name': name,
                            'type': obj_type,
                            'uri': ref_uri,
                            'description': desc
                        })
                    break  # Only first adtObject child per referencedObject
        except ET.ParseError:
            pass

        return results

    def pretty_print(self, object_url, source):
        """Format ABAP source code using SAP Pretty Printer

        Args:
            object_url: Object URL for context (unused by API but kept for interface)
            source: ABAP source code to format

        Returns:
            Formatted source code string
        """
        headers = self._get_headers(
            'text/plain',
            'text/plain'
        )
        headers['Content-Type'] = 'text/plain; charset=utf-8'

        response = self._request_with_csrf_retry(
            'post',
            f"{self.url}/sap/bc/adt/abapsource/prettyprinter",
            headers=headers,
            data=source.encode('utf-8')
        )

        if response.status_code != 200:
            raise SAPADTError(
                "Pretty printer failed",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        return response.text

    def run_atc_check(self, object_url, variant='DEFAULT', max_verdicts=100):
        """Run ATC (ABAP Test Cockpit) check - 3-step workflow

        Args:
            object_url: Object URL to check
            variant: ATC check variant name
            max_verdicts: Maximum number of findings to return

        Returns:
            dict with 'findings' list, each containing 'priority', 'message', 'location', 'checkId'
        """
        # Step 1: Create worklist with check variant
        headers1 = self._get_headers('text/plain')
        response1 = self._request_with_csrf_retry(
            'post',
            f"{self.url}/sap/bc/adt/atc/worklists",
            headers=headers1,
            params={'checkVariant': variant}
        )

        if response1.status_code not in [200, 201]:
            raise SAPADTError(
                "ATC worklist creation failed",
                status_code=response1.status_code,
                response_text=response1.text[:500]
            )

        worklist_id = response1.text.strip()
        if not worklist_id:
            raise SAPADTError("ATC worklist creation returned empty ID")

        self._debug(f"ATC worklist created: {worklist_id}")

        # Step 2: Create ATC run with the worklist ID
        run_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<atc:run maximumVerdicts="{max_verdicts}" xmlns:atc="http://www.sap.com/adt/atc">
  <objectSets xmlns:adtcore="http://www.sap.com/adt/core">
    <objectSet kind="inclusive">
      <adtcore:objectReferences>
        <adtcore:objectReference adtcore:uri="{object_url}"/>
      </adtcore:objectReferences>
    </objectSet>
  </objectSets>
</atc:run>'''

        headers2 = self._get_headers(
            'application/xml',
            'application/xml'
        )

        response2 = self._request_with_csrf_retry(
            'post',
            f"{self.url}/sap/bc/adt/atc/runs",
            headers=headers2,
            params={'worklistId': worklist_id},
            data=run_xml.encode('utf-8')
        )

        if response2.status_code not in [200, 201]:
            raise SAPADTError(
                "ATC run creation failed",
                status_code=response2.status_code,
                response_text=response2.text[:500]
            )

        # Extract result worklist ID from run response
        result_worklist_id = worklist_id
        try:
            root = ET.fromstring(response2.text)
            for elem in root.iter():
                wl_id = elem.get('worklistId', '') or elem.get('id', '')
                if wl_id:
                    result_worklist_id = wl_id
                    break
        except ET.ParseError:
            pass

        self._debug(f"ATC run completed, result worklist: {result_worklist_id}")

        # Step 3: Get ATC results from worklist
        headers3 = self._get_headers('application/atc.worklist.v1+xml')
        response3 = self._request_with_csrf_retry(
            'get',
            f"{self.url}/sap/bc/adt/atc/worklists/{result_worklist_id}",
            headers=headers3,
            params={'includeExemptedFindings': 'false'}
        )

        if response3.status_code != 200:
            # Fallback: try with generic application/xml
            headers3b = self._get_headers('application/xml')
            response3 = self._request_with_csrf_retry(
                'get',
                f"{self.url}/sap/bc/adt/atc/worklists/{result_worklist_id}",
                headers=headers3b
            )
            if response3.status_code != 200:
                raise SAPADTError(
                    "ATC results retrieval failed",
                    status_code=response3.status_code,
                    response_text=response3.text[:500]
                )

        # Parse findings - attributes are namespaced, strip namespace prefixes
        findings = []
        try:
            root2 = ET.fromstring(response3.text)
            for finding in root2.iter():
                tag = finding.tag.split('}')[-1] if '}' in finding.tag else finding.tag
                if tag == 'finding':
                    # Strip namespace from attribute keys for reliable access
                    attrs = {k.split('}')[-1] if '}' in k else k: v
                             for k, v in finding.attrib.items()}
                    findings.append({
                        'priority': attrs.get('priority', ''),
                        'message': attrs.get('messageTitle', '') or attrs.get('message', ''),
                        'location': attrs.get('location', '') or attrs.get('uri', ''),
                        'checkId': attrs.get('checkId', '') or attrs.get('checkTitle', '')
                    })
        except ET.ParseError:
            pass

        return {'findings': findings}

    def get_inactive_objects(self):
        """Get list of inactive objects for current user

        Returns:
            list of dicts with 'name', 'type', 'uri', 'user'
        """
        headers = self._get_headers(
            'application/vnd.sap.adt.inactivectsobjects.v1+xml, application/xml;q=0.8'
        )

        response = self._request_with_csrf_retry(
            'get',
            f"{self.url}/sap/bc/adt/activation/inactiveobjects",
            headers=headers
        )

        if response.status_code != 200:
            raise SAPADTError(
                "Failed to get inactive objects",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        results = []
        try:
            root = ET.fromstring(response.text)
            for elem in root.iter():
                name = elem.get('{http://www.sap.com/adt/core}name', '') or elem.get('name', '')
                obj_type = elem.get('{http://www.sap.com/adt/core}type', '') or elem.get('type', '')
                uri = elem.get('{http://www.sap.com/adt/core}uri', '') or elem.get('uri', '')
                user = elem.get('user', '') or elem.get('{http://www.sap.com/adt/core}responsibleUser', '')
                if name and (obj_type or uri):
                    results.append({
                        'name': name,
                        'type': obj_type,
                        'uri': uri,
                        'user': user
                    })
        except ET.ParseError:
            pass

        return results

    def get_system_info(self):
        """Get SAP system information via ADT discovery

        Returns:
            dict with system properties including SID, available services
        """
        info = {
            'connection_url': self.url,
            'client': self.client,
            'user': self.user,
            'language': self.language
        }

        # Extract system ID from session cookies (sap-contextid contains SID)
        import urllib.parse
        for cookie in self.session.cookies:
            if cookie.name == 'sap-contextid':
                decoded = urllib.parse.unquote(cookie.value)
                # Format: SID:ANON:Fiori2Dev_FID_00:...
                parts = decoded.split(':')
                if len(parts) >= 3:
                    sid_part = parts[2]  # e.g. 'Fiori2Dev_FID_00'
                    sid_tokens = sid_part.split('_')
                    if len(sid_tokens) >= 2:
                        info['system_id'] = sid_tokens[-2]

        # Fetch discovery document for available services catalog
        try:
            headers = self._get_headers('application/atomsvc+xml')
            headers['Accept'] = 'application/atomsvc+xml'
            response = self._request_with_csrf_retry(
                'get',
                f"{self.url}/sap/bc/adt/discovery",
                headers=headers
            )
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                services = []
                for elem in root.iter():
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag == 'collection':
                        href = elem.get('href', '')
                        title = ''
                        for child in elem:
                            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            if child_tag == 'title' and child.text:
                                title = child.text
                                break
                        if href:
                            services.append({'href': href, 'title': title})
                info['available_services'] = services
                info['service_count'] = len(services)
        except Exception:
            pass

        return info

    def create_metadata_extension(self, name, source, description, package_name, transport=None):
        """Create a CDS Metadata Extension (DDLX)

        Args:
            name: Metadata extension name
            source: DDLX source code
            description: Description text
            package_name: Package name
            transport: Transport request number

        Returns:
            dict with success status
        """
        self._validate_object_name(name, 'Metadata Extension')
        self._validate_package_name(package_name)
        self._validate_transport(transport)

        if not self.csrf_token:
            self.fetch_csrf_token()

        ddlx_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ddlx:ddlxSource xmlns:ddlx="http://www.sap.com/adt/ddic/ddlxsources"
                xmlns:adtcore="http://www.sap.com/adt/core"
                  adtcore:name="{name.upper()}"
                  adtcore:description="{description}"
                  adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
</ddlx:ddlxSource>'''

        headers = self._get_headers(
            'application/vnd.sap.adt.ddlxSource+xml',
            'application/vnd.sap.adt.ddlxSource+xml'
        )

        params = {}
        if transport:
            params['corrNr'] = transport

        response = self.session.post(
            f"{self.url}/sap/bc/adt/ddic/ddlx/sources",
            headers=headers,
            data=ddlx_xml.encode('utf-8'),
            params=params,
            timeout=self.timeout_default
        )

        if response.status_code not in [200, 201]:
            raise SAPADTError(
                f"Failed to create metadata extension",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        object_url = f'/sap/bc/adt/ddic/ddlx/sources/{name.lower()}'

        # Upload the source (pass transport so SAP registers write under correct CTS entry)
        try:
            self.set_object_source(f"{object_url}/source/main", source, lock_handle=None, transport=transport)
        except Exception as e:
            if self.debug_enabled:
                self._debug(f"[DEBUG] DDLX source upload note: {e}")

        return {
            'success': True,
            'object_url': object_url,
            'message': f'Metadata extension {name} created'
        }

    def create_access_control(self, name, source, description, package_name, transport=None):
        """Create a CDS Access Control (DCL)

        Args:
            name: Access control name
            source: DCL source code
            description: Description text
            package_name: Package name
            transport: Transport request number

        Returns:
            dict with success status
        """
        self._validate_object_name(name, 'Access Control')
        self._validate_package_name(package_name)
        self._validate_transport(transport)

        # force_refresh: cached token bağlanan oturuma ait — yeni CLI process'in
        # cookie'siyle uyuşmaz → 403 "CSRF token validation failed". Taze al.
        self.fetch_csrf_token(force_refresh=True)

        dcl_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<acm:dclSource xmlns:acm="http://www.sap.com/adt/acm/dclsources"
               xmlns:adtcore="http://www.sap.com/adt/core"
               adtcore:name="{name.upper()}"
               adtcore:description="{description}"
               adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
</acm:dclSource>'''

        headers = self._get_headers(
            'application/vnd.sap.adt.dclSource+xml',
            'application/vnd.sap.adt.dclSource+xml'
        )

        params = {}
        if transport:
            params['corrNr'] = transport

        response = self.session.post(
            f"{self.url}/sap/bc/adt/acm/dcl/sources",
            headers=headers,
            data=dcl_xml.encode('utf-8'),
            params=params,
            timeout=self.timeout_default
        )

        if response.status_code not in [200, 201]:
            raise SAPADTError(
                f"Failed to create access control",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        object_url = f'/sap/bc/adt/acm/dcl/sources/{name.lower()}'

        # Upload the source (pass transport so SAP registers write under correct CTS entry)
        try:
            self.set_object_source(f"{object_url}/source/main", source, lock_handle=None, transport=transport)
        except Exception as e:
            if self.debug_enabled:
                self._debug(f"[DEBUG] DCL source upload note: {e}")

        return {
            'success': True,
            'object_url': object_url,
            'message': f'Access control {name} created'
        }

    def create_behavior_definition(self, name, root_entity, implementation_type,
                                    package_name, description='', transport='',
                                    source=None, activate=True):
        """Create an ABAP Behavior Definition (BDEF)

        Args:
            name: Behavior Definition name (e.g., 'ZI_MY_BDEF')
            root_entity: Root Entity name (CDS view entity, e.g., 'ZI_MY_ENTITY')
            implementation_type: Implementation type ('Managed', 'Unmanaged', 'Abstract', 'Projection')
            package_name: Package name
            description: Description text
            transport: Transport request number
            source: BDEF source code (optional)
            activate: Activate after creation

        Returns:
            dict with success status
        """
        self._validate_object_name(name, 'Behavior Definition')
        self._validate_package_name(package_name)

        if not self.csrf_token:
            self.fetch_csrf_token()

        # BDEF, blue/blueSource ailesindendir (adtcore:type="BDEF/BDO"), endpoint
        # /sap/bc/adt/bo/behaviordefinitions, content-type blues.v1+xml.
        # KANITLI reçete: playbook/adt-rap.md §32.6c + create_rap_service.py.
        # ESKİ (bozuk) payload: bdef:behaviorDefinition + yanlış ns + yanlış
        # endpoint (/behaviordefinitions, /bo eksik) → 404, hiç çalışmıyordu.
        from xml.sax.saxutils import escape as _xe
        bdef_base = '/sap/bc/adt/bo/behaviordefinitions'
        bdef_ct = 'application/vnd.sap.adt.blues.v1+xml'
        object_url = f'{bdef_base}/{name.lower()}'

        shell_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<blue:blueSource xmlns:blue="http://www.sap.com/wbobj/blue"\n'
            '                 xmlns:adtcore="http://www.sap.com/adt/core"\n'
            f'                 adtcore:name="{name.upper()}"\n'
            f'                 adtcore:description="{_xe(description or name)}"\n'
            '                 adtcore:type="BDEF/BDO"\n'
            f'                 adtcore:masterLanguage="{self.language}">\n'
            f'  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"\n'
            '                      adtcore:type="DEVC/K"\n'
            f'                      adtcore:name="{package_name.upper()}"/>\n'
            '</blue:blueSource>'
        )

        shell_headers = self._get_headers(bdef_ct, bdef_ct)
        params = {}
        if transport:
            params['corrNr'] = transport

        # CSRF self-healing: bare session.post 403'lerde patinaj yapıyordu (poison
        # cache). _request_with_csrf_retry 403+CSRF'de cache temizle + force-refresh
        # + tek retry yapar (Fix 3).
        response = self._request_with_csrf_retry(
            'post', f"{self.url}{bdef_base}",
            headers=shell_headers,
            data=shell_xml.encode('utf-8'),
            params=params,
        )

        # 'AlreadyExists' (400) → mevcut shell'i kullan, source'u güncelle
        already = response.status_code == 400 and 'AlreadyExists' in response.text
        if response.status_code not in [200, 201] and not already:
            raise SAPADTError(
                f"Failed to create behavior definition",
                status_code=response.status_code,
                response_text=response.text[:500],
                endpoint=bdef_base
            )

        # Upload source via LOCK + PUT (text/plain, NO If-Match) + UNLOCK — SRVD/CDS
        # ile aynı 2-step pattern (create_rap_service.py step_bdef).
        if source:
            lock_handle = self.lock_object(object_url, transport=transport)
            try:
                put_url = f"{self.url}{object_url}/source/main"
                put_params = {'lockHandle': lock_handle}
                if transport:
                    put_params['corrNr'] = transport
                put_headers = self._get_headers()
                put_headers['Content-Type'] = 'text/plain; charset=utf-8'
                put_headers['Accept'] = '*/*'
                pr = self._request_with_csrf_retry(
                    'put', put_url, headers=put_headers, params=put_params,
                    data=source.encode('utf-8'),
                )
                if pr.status_code not in (200, 201, 204):
                    raise SAPADTError(
                        f"Failed to upload BDEF source for {name}",
                        status_code=pr.status_code,
                        response_text=pr.text[:500],
                        endpoint=object_url + '/source/main'
                    )
            finally:
                try:
                    self.unlock_object(object_url, lock_handle)
                except Exception as e:
                    if self.debug_enabled:
                        self._debug(f"[DEBUG] BDEF unlock note: {e}")

        # Activate if requested. NOT: managed BDEF + behavior class RAP circular
        # dependency → genellikle ikisi BİRLİKTE aktive edilmeli (bkz.
        # create_rap_service.py step_bactivate). Tek-BDEF aktivasyonu behavior
        # class henüz yoksa "BEHAVIOR cannot be implemented" verebilir; bu durumda
        # çağıran BDEF+class'ı birlikte aktive etmeli.
        if activate:
            try:
                self.activate_object(name, object_url)
            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] BDEF activation note: {e}")

        return {
            'success': True,
            'object_url': object_url,
            'name': name.upper(),
            'message': f'Behavior definition {name} created'
        }

    def create_behavior_implementation(self, name, behavior_definition,
                                       package_name, description='', transport='',
                                       source=None, activate=True):
        """Create an ABAP Behavior Implementation (BIMP)

        Args:
            name: Behavior Implementation name (e.g., 'ZBP_MY_ENTITY')
            behavior_definition: Behavior Definition name (e.g., 'ZI_MY_BDEF')
            package_name: Package name
            description: Description text
            transport: Transport request number
            source: BIMP source code (optional)
            activate: Activate after creation

        Returns:
            dict with success status
        """
        self._validate_object_name(name, 'Behavior Implementation')
        self._validate_package_name(package_name)

        if not self.csrf_token:
            self.fetch_csrf_token()

        # Build BIMP XML
        bimp_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<bimpl:behaviorImplementation xmlns:bimpl="http://www.sap.com/adt/behaviorImplementations"
                               xmlns:adtcore="http://www.sap.com/adt/core"
                               adtcore:name="{name.upper()}"
                               adtcore:description="{description or name}"
                               adtcore:masterLanguage="{self.language}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package_name.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package_name.upper()}"/>
  <bimpl:behaviorDefinitionRef adtcore:uri="/sap/bc/adt/behaviordefinitions/{behavior_definition.lower()}"
                                adtcore:name="{behavior_definition.upper()}"/>
</bimpl:behaviorImplementation>'''

        headers = self._get_headers(
            'application/vnd.sap.adt.behaviorImplementation+xml',
            'application/vnd.sap.adt.behaviorImplementation+xml'
        )

        params = {}
        if transport:
            params['corrNr'] = transport

        response = self.session.post(
            f"{self.url}/sap/bc/adt/behaviorimplementations",
            headers=headers,
            data=bimp_xml.encode('utf-8'),
            params=params,
            timeout=self.timeout_default
        )

        if response.status_code not in [200, 201]:
            raise SAPADTError(
                f"Failed to create behavior implementation",
                status_code=response.status_code,
                response_text=response.text[:500]
            )

        object_url = f'/sap/bc/adt/behaviorimplementations/{name.lower()}'

        # Upload source if provided
        if source:
            try:
                self.set_object_source(f"{object_url}/source/main", source, lock_handle=None, transport=transport)
            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] BIMP source upload note: {e}")

        # Activate if requested
        if activate:
            try:
                self.activate_object(name, 'bimpl')
            except Exception as e:
                if self.debug_enabled:
                    self._debug(f"[DEBUG] BIMP activation note: {e}")

        return {
            'success': True,
            'object_url': object_url,
            'name': name.upper(),
            'message': f'Behavior implementation {name} created'
        }


# =============================================================================
# Source DRIFT guard (ADR 0016) — repo ↔ canlı SAP senkron
# =============================================================================

# srvd/srvb/bdef object_types.py'de merkezi DEĞİL (create_rap_service.py elle path
# kullanır). get_source_url bunlara ValueError verir → drift guard'ın bu tipleri de
# kapsaması için fallback REST-path map. Kaynak: create_rap_service.py SRVD_BASE +
# check_source_drift._TYPE_TO_ADT_PATH (tek doğruluk burada tutulur, validator kopyalar).
_DRIFT_FALLBACK_PATHS = {
    'srvd': 'ddic/srvd/sources',
    'srvb': 'ddic/srvb/services',
    'bdef': 'bo/behaviordefinitions',
}


def _resolve_source_url(object_name, object_type):
    """Obje için /source/main URL'i çöz; bilinmeyen tip → fallback map; yoksa None.

    Önce object_types.get_source_url (merkezi); ValueError ise srvd/srvb/bdef
    fallback. Hiçbiri yoksa None (çağıran drift kıyasını atlar)."""
    try:
        from object_types import get_source_url
        return get_source_url(object_name, object_type)
    except Exception:
        pass
    seg = _DRIFT_FALLBACK_PATHS.get((object_type or '').lower())
    if seg:
        return f'/sap/bc/adt/{seg}/{object_name.lower()}/source/main'
    return None


def detect_source_drift(object_url, object_name, object_type, client=None):
    """Repo dosyası ile canlı SAP AKTİF source ayrışıyor mu? (ADR 0016 M1)

    Push'tan ÖNCE çağrılır. Canlıdaki aktif source'u çeker (version='active'),
    objenin repo dosyasını bulur, normalize edip kıyaslar. Drift varsa push'u
    HARD-BLOCK etmek için is_drift=True döner (çağıran taraf push'u durdurur).

    Obje canlıda YOKsa (404) → yeni yaratım, drift YOK (GEÇ).
    Repo'da dosya yoksa → kıyas yapılamaz, drift YOK (GEÇ).
    Bağlantı/fetch hatası → GÜVENLİ tarafta drift YOK (push'u bricklememek için;
    asıl koruma push'un kendi hata yolu).

    Args:
        object_url: ADT obje URL'i (örn. /sap/bc/adt/ddic/srvd/sources/zsd001_ui_booking).
                    None ise object_name+object_type'tan türetilir.
        object_name: SAP obje adı (Z*/Y*).
        object_type: ADT obje tipi (srvd, ddls, cds, class, prog, ...).
        client: Mevcut SAPADTClient (yeniden bağlanmamak için). None → yeni yaratılır.

    Returns:
        (is_drift: bool, repo_path: str|None, diff_summary: str)
    """
    from source_drift import detect_drift_with_fetch  # lazy: hafif modül

    def _fetch_active():
        nonlocal client
        if client is None:
            client = SAPADTClient()
        url = object_url or _resolve_source_url(object_name, object_type)
        if not url:
            # tip hiçbir yolla çözülemedi → drift kıyası atlanır (üstte yakalanır)
            raise SAPADTError(f"source URL resolve edilemedi: type={object_type}")
        try:
            return client.get_object_source(url, version='active')
        except SAPObjectNotFoundError:
            return None  # canlıda yok → yeni yaratım

    result = detect_drift_with_fetch(object_name, _fetch_active, object_type=object_type)
    return result["is_drift"], result.get("repo_path"), result.get("diff_summary", "") or result.get("reason", "")


def sync_repo_from_live(object_url, object_name, object_type, client=None, force=False):
    """Pull-before-edit REPO SYNC: canlı aktif source'u repo dosyasına yaz.

    Repo dosyası yoksa yazmaz (yol tahmini yapmaz; yeni obje normal akışla eklenir).
    force=False iken yereldeki commit'lenmemiş değişikliği EZMEZ (FIX-B; write_repo_from_live
    uncommitted-local koruması → blocked_dirty). force=True bilerek canlıya döner.

    Returns:
        dict: {"written": bool, "repo_path": str|None, "reason": str, "blocked_dirty"?: bool}
              veya {"written": False, "reason": "..."} (fetch başarısızsa).
    """
    from source_drift import write_repo_from_live

    if client is None:
        client = SAPADTClient()
    url = object_url or _resolve_source_url(object_name, object_type)
    if not url:
        return {"written": False, "repo_path": None,
                "reason": f"source URL türetilemedi (type={object_type})"}
    try:
        live = client.get_object_source(url, version='active')
    except SAPObjectNotFoundError:
        return {"written": False, "repo_path": None,
                "reason": "canlı obje yok (404) — post-sync atlandı"}
    except Exception as exc:
        return {"written": False, "repo_path": None,
                "reason": f"canlı source çekilemedi ({exc}) — post-sync atlandı"}

    return write_repo_from_live(object_name, live, object_type=object_type, force=force)

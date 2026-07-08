#!/usr/bin/env python3
"""
SAP ADT Credential Setup
Interactive or programmatic setup of .conn_adt file
"""
import sys
import os
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from sap_adt_lib import (
    set_session_credentials,
    clear_session_credentials,
    get_conn_path,
    check_sap_config,
    validate_sap_config
)


def setup_credentials_interactive():
    """
    Interactive setup - prompt user for credentials one by one.
    Sets credentials as session environment variables (no file created).
    """
    print("\n" + "=" * 70)
    print("  SAP ADT Credential Setup (Session Mode)")
    print("=" * 70)
    print("\nPlease provide your SAP ADT connection details:\n")

    sap_url = input("SAP URL (e.g., https://server.com:44300): ").strip()
    if not sap_url:
        print("[ERROR] SAP URL is required")
        return False

    sap_user = input("SAP Username: ").strip()
    if not sap_user:
        print("[ERROR] SAP Username is required")
        return False

    sap_password = input("SAP Password: ").strip()
    if not sap_password:
        print("[ERROR] SAP Password is required")
        return False

    sap_client = input("SAP Client (e.g., 100): ").strip()
    if not sap_client:
        print("[ERROR] SAP Client is required")
        return False

    sap_language = input("SAP Language (default: EN): ").strip() or "EN"

    print("\n" + "-" * 70)
    print("Setting session credentials...")
    print("-" * 70)

    result = set_session_credentials(sap_url, sap_user, sap_password, sap_client, sap_language)

    if result['success']:
        print("\n[OK] Session credentials set successfully")
        print("\nNOTE: Credentials are valid for this session only")
        print("      They are NOT saved to disk and will be cleared when the session ends")
        print("\nYou can now use SAP ADT operations.")
        return True
    else:
        print(f"\n[ERROR] {result['message']}")
        return False


def setup_credentials_from_dict(credentials: dict):
    """
    Programmatic setup - accept credentials as a dictionary.
    This is designed for LLM agent usage.
    Sets credentials as session environment variables (no file created).

    Args:
        credentials: dict with keys:
            - url: SAP server URL
            - user: SAP username
            - password: SAP password
            - client: SAP client number
            - language: (optional) SAP language code, defaults to 'EN'

    Returns:
        dict with keys:
            - success: bool
            - message: str
            - error: str or None

    Example:
        credentials = {
            "url": "https://sap-server.com:44300",
            "user": "DEVELOPER",
            "password": "secret123",
            "client": "100",
            "language": "EN"
        }
        result = setup_credentials_from_dict(credentials)
    """
    required_fields = ['url', 'user', 'password', 'client']
    missing = [f for f in required_fields if f not in credentials or not credentials[f]]

    if missing:
        return {
            'success': False,
            'message': 'Missing required fields',
            'error': f'Missing required fields: {", ".join(missing)}'
        }

    sap_url = credentials['url']
    sap_user = credentials['user']
    sap_password = credentials['password']
    sap_client = credentials['client']
    sap_language = credentials.get('language', 'EN')

    result = set_session_credentials(sap_url, sap_user, sap_password, sap_client, sap_language)

    return {
        'success': result['success'],
        'message': result['message'] if result['success'] else 'Failed to set credentials',
        'error': None if result['success'] else result['message']
    }


def show_current_config():
    """Show current SAP configuration status."""
    print("\n" + "=" * 70)
    print("  Current SAP Configuration")
    print("=" * 70)

    status = check_sap_config()

    print(f"\n.conn_adt location: {status['conn_path']}")
    print(f"File exists: {status['conn_exists']}")
    print(f"Configured: {status['configured']}")

    if status['missing']:
        print(f"\nMissing fields: {', '.join(status['missing'])}")

    if status['placeholders']:
        print(f"Fields with placeholders: {', '.join(status['placeholders'])}")

    if status['configured']:
        print("\n[OK] SAP credentials are configured and ready to use")
    else:
        print("\n[WARNING] SAP credentials need to be configured")


def test_connection():
    """Test current SAP connection."""
    print("\n" + "=" * 70)
    print("  Testing SAP Connection")
    print("=" * 70)

    is_valid, error_msg = validate_sap_config()

    if not is_valid:
        print(error_msg)
        return False

    # Import here to avoid circular dependency
    from sap_client import SAPClient

    try:
        client = SAPClient()
        result = client.check_logon()

        if result:
            print("\n[OK] SAP connection successful!")
            print("You can now use SAP ADT operations.")
            return True
        else:
            print("\n[FAIL] SAP connection failed")
            print("Please check your credentials and try again.")
            return False
    except Exception as e:
        print(f"\n[ERROR] Connection test failed: {e}")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='SAP ADT Credential Setup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive setup
  python setup_credentials.py

  # Show current configuration
  python setup_credentials.py --show

  # Test connection
  python setup_credentials.py --test

  # Setup from JSON (for LLM usage)
  python setup_credentials.py --json '{"url":"https://server.com:44300","user":"ME","password":"pass","client":"100"}'
        """
    )

    parser.add_argument('--show', action='store_true',
                       help='Show current configuration status')
    parser.add_argument('--test', action='store_true',
                       help='Test SAP connection')
    parser.add_argument('--json', type=str,
                       help='Setup from JSON string (for LLM agent usage)')
    parser.add_argument('--cwd', type=str,
                       help='Working directory containing .conn_adt')

    args = parser.parse_args()

    # Set explicit working directory if provided
    if args.cwd:
        from sap_adt_lib import set_explicit_working_dir
        set_explicit_working_dir(args.cwd)

    if args.show:
        show_current_config()
    elif args.test:
        test_connection()
    elif args.json:
        import json
        try:
            credentials = json.loads(args.json)
            result = setup_credentials_from_dict(credentials)

            if result['success']:
                print(f"\n[OK] Credentials saved to: {result['conn_path']}")
                print("\nTesting connection...")
                if test_connection():
                    print("\n[SUCCESS] Setup complete and connection verified!")
            else:
                print(f"\n[ERROR] {result['error']}")
        except json.JSONDecodeError as e:
            print(f"\n[ERROR] Invalid JSON: {e}")
        except Exception as e:
            print(f"\n[ERROR] {e}")
    else:
        # Default: interactive setup
        if setup_credentials_interactive():
            print("\nTesting connection...")
            test_connection()

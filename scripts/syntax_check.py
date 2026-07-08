#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check SAP ABAP object syntax without activating.

Usage:
    python syntax_check.py --name ZCL_MY_CLASS --type class --cwd /path/to/project
    python syntax_check.py --name ZSD000_D_TEST --type domain --cwd /path/to/project
"""
import argparse
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from sap_adt_lib import set_explicit_working_dir, SAPADTClient
from sap_client import SAPClient


def check_ddic_object(client: SAPClient, object_name: str, object_type: str) -> dict:
    """
    Check DDIC object by retrieving metadata and checking activation status.

    DDIC objects don't have a separate syntax check endpoint.
    Instead, we verify the object metadata and check if it's active.
    """
    adt_client = SAPADTClient()

    # Map object types to ADT Accept headers and endpoints
    # Format: {object_type: (accept_header, endpoint_suffix)}
    type_map = {
        'domain': ('application/vnd.sap.adt.domains.v2+xml', 'domains'),
        'doma': ('application/vnd.sap.adt.domains.v2+xml', 'domains'),
        'dataelement': ('application/vnd.sap.adt.dataelements.v2+xml', 'dataelements'),
        'dtel': ('application/vnd.sap.adt.dataelements.v2+xml', 'dataelements'),
        'structure': ('application/vnd.sap.adt.structures.v2+xml', 'structures'),
        'tabl': ('application/vnd.sap.adt.structures.v2+xml', 'structures'),
        'table': ('application/vnd.sap.adt.tables.v2+xml', 'tables'),
        'tabletype': ('application/vnd.sap.adt.tabletype.v1+xml', 'tabletypes'),
        'ttyp': ('application/vnd.sap.adt.tabletype.v1+xml', 'tabletypes'),
    }

    mapping = type_map.get(object_type.lower())
    if not mapping:
        return {
            'valid': False,
            'errors': [{'message': f'Unsupported DDIC type: {object_type}'}]
        }

    accept_type, endpoint = mapping
    object_url = f"/sap/bc/adt/ddic/{endpoint}/{object_name.lower()}"

    print(f"Checking DDIC object: {object_name} (type: {object_type})")

    try:
        # Ensure we have CSRF token for cookies
        if not adt_client.csrf_token:
            adt_client.fetch_csrf_token()

        # Fetch object metadata to verify it exists and is valid
        headers = adt_client._get_headers(accept_type=accept_type)

        # Use requests module directly (SAPADTClient doesn't use session)
        import requests
        response = requests.get(
            f"{adt_client.url}{object_url}",
            headers=headers,
            cookies=adt_client.cookies,
            verify=False,
            timeout=30
        )

        if response.status_code == 404:
            return {
                'valid': False,
                'errors': [{'message': f'Object {object_name} not found'}]
            }

        if response.status_code == 200:
            # Check if object is active
            content = response.text
            is_active = 'version="active"' in content

            if is_active:
                print("[OK] DDIC object exists and is active")
                return {'valid': True, 'errors': [], 'active': True}
            else:
                print("[INFO] DDIC object exists but may not be active")
                return {'valid': True, 'errors': [], 'active': False}
        else:
            return {
                'valid': False,
                'errors': [{'message': f'Failed to check object: HTTP {response.status_code}'}]
            }

    except Exception as e:
        return {
            'valid': False,
            'errors': [{'message': str(e)}]
        }


def main():
    parser = argparse.ArgumentParser(
        description='Check SAP ABAP object syntax without activating'
    )
    parser.add_argument('--name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS, ZSD000_D_TEST)')
    parser.add_argument('--type', default='class',
                       choices=['class', 'clas', 'interface', 'intf', 'program', 'prog',
                               'report', 'include', 'incl', 'functiongroup', 'fugr',
                               'domain', 'doma', 'dataelement', 'dtel',
                               'structure', 'tabl', 'table', 'tabletype', 'ttyp'],
                       help='Object type (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()

        # DDIC objects use different check method
        ddic_types = ['domain', 'doma', 'dataelement', 'dtel', 'structure', 'tabl', 'table', 'tabletype', 'ttyp']
        is_ddic = args.type.lower() in ddic_types

        if is_ddic:
            result = check_ddic_object(client, args.name, args.type)
        else:
            result = client.syntax_check(
                object_name=args.name,
                object_type=args.type
            )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] SYNTAX CHECK FAILED - could NOT check syntax for {args.name}")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result.get('valid'):
        print("[OK] Check passed")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] SYNTAX CHECK FAILED - {args.name} has syntax errors")
        print("=" * 60)
        errors = result.get('errors', [])
        if not errors and result.get('error'):
            print(f"  {result.get('error')}")
        else:
            for error in errors:
                if isinstance(error, dict):
                    line = error.get('line', '')
                    msg = error.get('message', '')
                    if line:
                        print(f"  Line {line}: {msg}")
                    else:
                        print(f"  {msg}")
                else:
                    print(f"  {error}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

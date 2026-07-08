#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check if a SAP package exists.

This script checks if a package exists in the SAP system via ADT.

To create a package, use create_package.py:
    python create_package.py --name ZSD000_T --description "ZSD000 Types" --super-package ZSD000 --transport IEDK934921 --cwd /path

Usage:
    python check_package.py --name ZSD000_T --cwd /path/to/project
"""
import argparse
import json
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
import requests


def check_package_exists(package_name: str) -> dict:
    """Check if a package exists in SAP.

    Args:
        package_name: Name of the package to check

    Returns:
        dict with 'exists', 'status_code', and 'message' keys
    """
    adt = SAPADTClient()

    try:
        adt.fetch_csrf_token()
    except Exception as e:
        return {
            'exists': False,
            'status_code': 0,
            'message': f'Failed to connect to SAP: {str(e)}'
        }

    # Try multiple approaches to check if package exists
    # Method 1: Direct package endpoint with different media types
    url = f"{adt.url}/sap/bc/adt/packages/{package_name.lower()}"

    # Try different Accept headers (application/* works best)
    accept_types = [
        'application/*',
        'application/vnd.sap.adt.packages.package.v2+xml',
        'application/vnd.sap.adt.packages.packageProperties+xml',
    ]

    for accept_type in accept_types:
        headers = adt._get_headers(accept_type)
        response = requests.get(
            url,
            headers=headers,
            cookies=adt.cookies,
            verify=False,
            timeout=30
        )

        if response.status_code == 200:
            return {
                'exists': True,
                'status_code': 200,
                'package': package_name,
                'message': f'Package {package_name} exists'
            }
        elif response.status_code == 404:
            # Package doesn't exist
            continue
        elif response.status_code == 406:
            # 406 might mean "not acceptable" - try next method
            continue

    # Method 2: Try through nodestructure (repository tree)
    try:
        url = f"{adt.url}/sap/bc/adt/repository/nodestructure"
        headers = adt._get_headers('application/vnd.sap.as+xml', 'application/vnd.sap.adt.core.v1+xml')

        params = {
            'parent_type': 'DEVC/K',
            'parent_name': '$ROOT',
            'withShortDescriptions': 'true'
        }

        response = requests.post(
            url,
            headers=headers,
            params=params,
            data='',
            cookies=adt.cookies,
            verify=False,
            timeout=30
        )

        if response.status_code == 200 and package_name in response.text:
            return {
                'exists': True,
                'status_code': 200,
                'package': package_name,
                'message': f'Package {package_name} found in repository tree'
            }
    except Exception as e:
        pass  # Fall through to return not exists

    # Package doesn't exist or we can't verify
    return {
        'exists': False,
        'status_code': 404,
        'package': package_name,
        'message': f'Package {package_name} does not exist (or cannot be verified via ADT)'
    }


def main():
    parser = argparse.ArgumentParser(
        description='Check if a SAP package exists'
    )
    parser.add_argument('--name', required=True,
                       help='Package name (e.g., ZSD000, ZSD000_T)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        result = check_package_exists(args.name)
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] PACKAGE CHECK FAILED - could NOT check package {args.name} in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result['exists']:
            print(f"[OK] Package {result['package']} exists")
        else:
            print(f"[INFO] Package {result['package']} does not exist")
            print("")
            print("To create this package, use create_package.py:")
            print(f"  python create_package.py --name {result['package']} --description \"Description\" --super-package PARENT --transport TR12345 --cwd /path")

    return 0 if result['exists'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

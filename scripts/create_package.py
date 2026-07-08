#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a SAP package via ADT.

This script creates a new SAP package (DEVC) using the ADT REST API.

Usage:
    python create_package.py --name ZSD000_T --description "ZSD000 Types" --super-package ZSD000 --transport IEDK934921 --cwd /path/to/project

Required parameters:
    --name           Package name (e.g., ZSD000_T)
    --description    Package description
    --transport      Transport request number
    --cwd            Working directory containing .conn_adt

Optional parameters:
    --super-package  Parent/super package (default: none - creates root package)
    --sw-component   Software component (default: HOME)
    --transport-layer Transport layer (auto-detected from super-package if not specified)
    --package-type   Package type: development, structure, main (default: development)
    --responsible    Responsible user (default: current user)
"""
import argparse
import json
import sys
import re
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


def get_package_info(adt: SAPADTClient, package_name: str) -> dict:
    """Get package information from SAP.

    Args:
        adt: SAP ADT client
        package_name: Name of the package

    Returns:
        dict with package info or None if not found
    """
    url = f"{adt.url}/sap/bc/adt/packages/{package_name.lower()}"
    headers = adt._get_headers('application/*')

    response = requests.get(url, headers=headers, cookies=adt.cookies, verify=False, timeout=30)

    if response.status_code != 200:
        return None

    text = response.text

    # Extract key info using regex
    swcomp_match = re.search(r'softwareComponent[^>]*pak:name="([^"]*)"', text)
    layer_match = re.search(r'transportLayer[^>]*pak:name="([^"]*)"', text)
    pkgtype_match = re.search(r'pak:packageType="([^"]*)"', text)
    desc_match = re.search(r'adtcore:description="([^"]*)"', text)

    return {
        'name': package_name,
        'description': desc_match.group(1) if desc_match else '',
        'sw_component': swcomp_match.group(1) if swcomp_match else 'HOME',
        'transport_layer': layer_match.group(1) if layer_match else '',
        'package_type': pkgtype_match.group(1) if pkgtype_match else 'development'
    }


def check_package_exists(adt: SAPADTClient, package_name: str) -> bool:
    """Check if a package already exists.

    Args:
        adt: SAP ADT client
        package_name: Name of the package

    Returns:
        True if package exists, False otherwise
    """
    url = f"{adt.url}/sap/bc/adt/packages/{package_name.lower()}"
    headers = adt._get_headers('application/*')

    response = requests.get(url, headers=headers, cookies=adt.cookies, verify=False, timeout=30)
    return response.status_code == 200


def validate_package(adt: SAPADTClient, name: str, description: str,
                     super_package: str, sw_component: str,
                     transport_layer: str, package_type: str) -> dict:
    """Validate package parameters before creation.

    Args:
        adt: SAP ADT client
        name: Package name
        description: Package description
        super_package: Super/parent package name
        sw_component: Software component
        transport_layer: Transport layer
        package_type: Package type (development/structure/main)

    Returns:
        dict with 'valid' (bool), 'severity', and 'message' keys
    """
    url = f"{adt.url}/sap/bc/adt/packages/validation"
    headers = adt._get_headers('application/vnd.sap.as+xml')

    params = {
        'objname': name,
        'objtype': 'DEVC/K',
        'description': description,
        'packagename': super_package or '',
        'packagetype': package_type,
        'swcomp': sw_component,
        'transportLayer': transport_layer or ''
    }

    response = requests.post(url, headers=headers, params=params,
                            cookies=adt.cookies, verify=False, timeout=30)

    # 403 CSRF: disk-cached token can be stale server-side (session killed,
    # app-server restart). Force-refresh and retry once with the new token.
    if response.status_code == 403 and 'CSRF' in response.text:
        adt.fetch_csrf_token(force_refresh=True)
        headers = adt._get_headers('application/vnd.sap.as+xml')
        response = requests.post(url, headers=headers, params=params,
                                cookies=adt.cookies, verify=False, timeout=30)

    if response.status_code != 200:
        # Try to extract error message from XML
        error_match = re.search(r'<message[^>]*>([^<]+)</message>', response.text)
        error_msg = error_match.group(1) if error_match else response.text[:200]
        return {
            'valid': False,
            'severity': 'ERROR',
            'message': f"Validation failed: {error_msg}"
        }

    # Parse validation response
    severity_match = re.search(r'<SEVERITY>([^<]+)</SEVERITY>', response.text)
    text_match = re.search(r'<SHORT_TEXT>([^<]*)</SHORT_TEXT>', response.text)

    severity = severity_match.group(1) if severity_match else 'OK'
    message = text_match.group(1) if text_match and text_match.group(1) else ''

    return {
        'valid': severity != 'ERROR',
        'severity': severity,
        'message': message or 'Validation successful'
    }


def create_package(adt: SAPADTClient, name: str, description: str,
                   super_package: str, sw_component: str,
                   transport_layer: str, package_type: str,
                   transport: str, responsible: str = None) -> dict:
    """Create a new SAP package.

    Args:
        adt: SAP ADT client
        name: Package name
        description: Package description
        super_package: Super/parent package name (empty for root)
        sw_component: Software component (e.g., HOME)
        transport_layer: Transport layer
        package_type: Package type (development/structure/main)
        transport: Transport request number
        responsible: Responsible user (default: current user)

    Returns:
        dict with 'success', 'package', 'location', and 'message' keys
    """
    responsible = (responsible or adt.user).upper()

    # Build XML body
    super_pkg_ref = f'<adtcore:packageRef adtcore:name="{super_package}"/>' if super_package else '<adtcore:packageRef/>'
    super_pkg_elem = f'<pak:superPackage adtcore:name="{super_package}"/>' if super_package else '<pak:superPackage/>'

    xml_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<pak:package xmlns:pak="http://www.sap.com/adt/packages"
xmlns:adtcore="http://www.sap.com/adt/core" adtcore:description="{description}"
adtcore:name="{name}" adtcore:type="DEVC/K" adtcore:version="active" adtcore:responsible="{responsible}">
{super_pkg_ref}
<pak:attributes pak:packageType="{package_type}"/>
{super_pkg_elem}
<pak:applicationComponent/>
<pak:transport>
 <pak:softwareComponent pak:name="{sw_component}"/>
 <pak:transportLayer pak:name="{transport_layer}"/>
</pak:transport>
<pak:translation/>
<pak:useAccesses/>
<pak:packageInterfaces/>
<pak:subPackages/>
</pak:package>'''

    # POST to create package
    url = f"{adt.url}/sap/bc/adt/packages"
    headers = adt._get_headers('application/*')
    headers['Content-Type'] = 'application/*'

    params = {'corrNr': transport}

    response = requests.post(
        url,
        headers=headers,
        params=params,
        data=xml_body.encode('utf-8'),
        cookies=adt.cookies,
        verify=False,
        timeout=60
    )

    # 403 CSRF: force-refresh and retry once — see validate_package() for why.
    if response.status_code == 403 and 'CSRF' in response.text:
        adt.fetch_csrf_token(force_refresh=True)
        headers = adt._get_headers('application/*')
        headers['Content-Type'] = 'application/*'
        response = requests.post(
            url,
            headers=headers,
            params=params,
            data=xml_body.encode('utf-8'),
            cookies=adt.cookies,
            verify=False,
            timeout=60
        )

    if response.status_code == 201:
        location = response.headers.get('location', '')
        return {
            'success': True,
            'package': name,
            'location': location,
            'message': f'Package {name} created successfully'
        }
    else:
        # Extract error message
        error_match = re.search(r'<message[^>]*>([^<]+)</message>', response.text)
        error_msg = error_match.group(1) if error_match else response.text[:500]
        return {
            'success': False,
            'package': name,
            'status_code': response.status_code,
            'message': f'Failed to create package: {error_msg}'
        }


def main():
    parser = argparse.ArgumentParser(
        description='Create a SAP package via ADT',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create a subpackage under ZSD000
  python create_package.py --name ZSD000_T --description "ZSD000 Types" --super-package ZSD000 --transport IEDK934921 --cwd /path

  # Create with explicit settings
  python create_package.py --name ZTEST --description "Test Package" --sw-component HOME --transport-layer ZIED --transport TR123 --cwd /path
'''
    )
    parser.add_argument('--name', required=True,
                        help='Package name (e.g., ZSD000_T)')
    parser.add_argument('--description', required=True,
                        help='Package description')
    parser.add_argument('--transport', required=True,
                        help='Transport request number')
    parser.add_argument('--super-package', default='',
                        help='Parent/super package (optional)')
    parser.add_argument('--sw-component', default='HOME',
                        help='Software component (default: HOME)')
    parser.add_argument('--transport-layer', default='',
                        help='Transport layer (auto-detected from super-package if not specified)')
    parser.add_argument('--package-type', default='development',
                        choices=['development', 'structure', 'main'],
                        help='Package type (default: development)')
    parser.add_argument('--responsible', default=None,
                        help='Responsible user (default: current user)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--skip-validation', action='store_true',
                        help='Skip validation before creation')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    # Initialize client
    adt = SAPADTClient()

    try:
        adt.fetch_csrf_token()
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE PACKAGE FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    # Check if package already exists
    try:
        if check_package_exists(adt, args.name):
            result = {
                'success': False,
                'package': args.name,
                'message': f'Package {args.name} already exists'
            }
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"[FAIL] Package {args.name} already exists")
            return 1
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE PACKAGE FAILED - could NOT check if {args.name} exists in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    # Auto-detect transport layer from super-package if not specified
    sw_component = args.sw_component
    transport_layer = args.transport_layer

    if args.super_package and not transport_layer:
        print(f"[INFO] Auto-detecting transport layer from {args.super_package}...")
        super_info = get_package_info(adt, args.super_package)
        if super_info:
            transport_layer = super_info['transport_layer']
            if not sw_component or sw_component == 'HOME':
                sw_component = super_info['sw_component']
            print(f"[INFO] Using SW Component: {sw_component}, Transport Layer: {transport_layer}")
        else:
            print(f"[WARN] Could not get info from super-package {args.super_package}")

    # Validate before creation
    if not args.skip_validation:
        print(f"[INFO] Validating package parameters...")
        validation = validate_package(
            adt, args.name, args.description, args.super_package,
            sw_component, transport_layer, args.package_type
        )

        if not validation['valid']:
            if args.json:
                print(json.dumps({'success': False, **validation}, indent=2))
            else:
                print(f"[FAIL] Validation failed: {validation['message']}")
            return 1
        print(f"[OK] Validation passed")

    # Create the package
    print(f"[INFO] Creating package {args.name}...")
    try:
        result = create_package(
            adt,
            name=args.name,
            description=args.description,
            super_package=args.super_package,
            sw_component=sw_component,
            transport_layer=transport_layer,
            package_type=args.package_type,
            transport=args.transport,
            responsible=args.responsible
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE PACKAGE FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))

    if result['success']:
        if not args.json:
            print(f"[OK] {result['message']}")
            if result.get('location'):
                print(f"[INFO] Location: {result['location']}")
        return 0
    else:
        if not args.json:
            print("")
            print("=" * 60)
            print(f"[FAIL] CREATE PACKAGE FAILED - {args.name} was NOT created in SAP")
            print("=" * 60)
            print(f"[ERROR] {result['message']}")
            print("")
            print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
            print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
            print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

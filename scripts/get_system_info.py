#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Get SAP system information.

Retrieves system details including SAP version, installed components,
system ID, and other diagnostic information.

Usage:
    python get_system_info.py --cwd /path/to/project
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

from sap_adt_lib import set_explicit_working_dir
from sap_client import SAPClient


def main():
    parser = argparse.ArgumentParser(
        description='Get SAP system information'
    )
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        result = client.get_system_info()
    except Exception as e:
        print("")
        print("=" * 60)
        print("[FAIL] GET SYSTEM INFO FAILED - could NOT retrieve system information")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result is None:
        print("")
        print("=" * 60)
        print("[FAIL] GET SYSTEM INFO FAILED - could NOT retrieve system information")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    print(f"[OK] SAP System Information:")
    print()
    for key, value in result.items():
        if key == 'available_services':
            continue# Print separately below
        print(f"  {key:25}: {value}")

    services = result.get('available_services', [])
    if services:
        print(f"\nAvailable ADT Services ({len(services)}):")
        print("=" * 80)
        for svc in services:
            title = svc.get('title', '')
            href = svc.get('href', '')
            if title:
                print(f"  {title:45} {href}")
            else:
                print(f"  {'(untitled)':45} {href}")
        print("=" * 80)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

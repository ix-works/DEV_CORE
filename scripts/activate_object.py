#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Activate SAP ABAP or DDIC object.

Usage:
    python activate_object.py --name ZCL_MY_CLASS --type class --cwd /path/to/project
    python activate_object.py --name ZSD000_D_TEST --type domain --cwd /path/to/project

Exit codes:
    0 - Success
    1 - Activation failed (syntax errors, etc.)
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
from object_types import list_supported_types, OBJECT_TYPE_ALIASES


def main():
    # Build choices from object_types
    all_types = list_supported_types() + list(OBJECT_TYPE_ALIASES.keys())

    parser = argparse.ArgumentParser(
        description='Activate SAP ABAP or DDIC object'
    )
    parser.add_argument('--name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS, ZSD000_D_TEST)')
    parser.add_argument('--type', default='class',
                       choices=all_types,
                       help='Object type (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        result = client.activate_object(
            object_name=args.name,
            object_type=args.type
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] ACTIVATION FAILED - {args.name} was NOT activated in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] ACTIVATION FAILED - {args.name} was NOT activated in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

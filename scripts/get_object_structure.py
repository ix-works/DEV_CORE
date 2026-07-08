#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Get internal structure of an SAP ABAP object.

Shows the sub-components of an object: class methods, includes,
function module parameters, table fields, etc.

Usage:
    python get_object_structure.py --object-name ZCL_MY_CLASS --object-type class --cwd /path/to/project
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
        description='Get internal structure of an SAP ABAP object'
    )
    parser.add_argument('--object-name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--object-type', default='class',
                       help='Object type: class, interface, program, functiongroup, table, etc. (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        result = client.get_structure(
            object_name=args.object_name,
            object_type=args.object_type
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] GET STRUCTURE FAILED - could NOT retrieve structure for {args.object_name}")
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
        print(f"[FAIL] GET STRUCTURE FAILED - could NOT retrieve structure for {args.object_name}")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    print(f"[OK] Structure of {args.object_name} ({args.object_type}):")
    print()

    components = result.get('components', [])
    if not components:
        print("  No sub-components found")
        return 0

    for comp in components:
        comp_type = comp.get('type', '')
        comp_name = comp.get('name', '?')
        comp_uri = comp.get('uri', '')
        desc = comp.get('description', '')
        desc_str = f" - {desc}" if desc else ""
        print(f"  [{comp_type:12}] {comp_name}{desc_str}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

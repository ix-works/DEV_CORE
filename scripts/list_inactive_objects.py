#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List inactive (not yet activated) SAP ABAP objects.

Shows all objects that have been modified but not yet activated.
Useful before mass activation or to check pending changes.

Usage:
    python list_inactive_objects.py --cwd /path/to/project
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
        description='List inactive (not yet activated) SAP ABAP objects'
    )
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        results = client.list_inactive_objects()
    except Exception as e:
        print("")
        print("=" * 60)
        print("[FAIL] LIST INACTIVE OBJECTS FAILED - could NOT retrieve inactive objects")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if results is None:
        print("")
        print("=" * 60)
        print("[FAIL] LIST INACTIVE OBJECTS FAILED - could NOT retrieve inactive objects")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if not results:
        print(f"[OK] No inactive objects found")
        return 0

    print(f"[OK] Found {len(results)} inactive object(s):")
    print()
    for obj in results:
        obj_type = obj.get('type', 'UNKNOWN')
        obj_name = obj.get('name', '?')
        obj_user = obj.get('user', '')
        user_str = f" (by {obj_user})" if obj_user else ""
        print(f"  [{obj_type:8}] {obj_name}{user_str}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

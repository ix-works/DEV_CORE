#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Delete SAP ABAP object.

WARNING: This operation is irreversible. Use with caution.

Usage:
    python delete_object.py --name ZCL_OLD_CLASS --type class --transport TRXXXXX --cwd /path/to/project

Skip confirmation (for automated scripts):
    python delete_object.py --name ZCL_OLD_CLASS --type class --transport TRXXXXX --yes --cwd /path/to/project
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
        description='Delete SAP ABAP object (WARNING: irreversible operation)'
    )
    parser.add_argument('--name', required=True,
                       help='Object name to delete (e.g., ZCL_OLD_CLASS)')
    parser.add_argument('--type', default='class',
                       choices=['class', 'clas', 'interface', 'intf', 'program', 'prog',
                               'report', 'include', 'incl', 'functiongroup', 'fugr'],
                       help='Object type (default: class)')
    parser.add_argument('--transport', required=True,
                       help='Transport request number (e.g., TRXXXXXX) - REQUIRED for deletion')
    parser.add_argument('--yes', action='store_true',
                       help='Skip confirmation prompt (useful for automated scripts)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    # Print warning
    print("[WARNING] This will DELETE the object from SAP!")
    print(f"  Object: {args.name}")
    print(f"  Type: {args.type}")
    print(f"  Transport: {args.transport}")
    print("")

    if not args.yes:
        try:
            response = input("Type 'yes' to confirm deletion: ")
            if response.lower() != 'yes':
                print("[INFO] Deletion cancelled")
                return 1
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Deletion cancelled")
            return 1

    try:
        client = SAPClient()
        result = client.delete_object(
            object_name=args.name,
            object_type=args.type,
            transport=args.transport,
            confirm=False  # We already confirmed above
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] DELETE FAILED - {args.name} was NOT deleted from SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Object deleted successfully: {args.name}")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] DELETE FAILED - {args.name} was NOT deleted from SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

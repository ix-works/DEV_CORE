#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find where an SAP ABAP object is used (Where-Used List).

Searches for all references to a given object across the SAP system.
Supports classes, interfaces, data elements, tables, CDS views, etc.

Usage:
    python where_used.py --object-name ZCL_MY_CLASS --object-type class --cwd /path/to/project
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from sap_adt_lib import set_explicit_working_dir, SAPObjectNotFoundError
from sap_client import SAPClient


def main():
    parser = argparse.ArgumentParser(
        description='Find where an SAP ABAP object is used (Where-Used List)'
    )
    parser.add_argument('--object-name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--object-type', default='class',
                       help='Object type: class, interface, program, table, dataelement, domain, cds (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        results = client.where_used(
            object_name=args.object_name,
            object_type=args.object_type
        )
    except SAPObjectNotFoundError:
        print("")
        print("=" * 60)
        print(f"[FAIL] OBJECT NOT FOUND - {args.object_name} ({args.object_type}) does not exist in SAP")
        print("=" * 60)
        print("[WHY THIS IS NOT '0 usages'] SAP returns an EMPTY usage list for objects that")
        print("do not exist. 'no consumers' and 'no object' look identical. They are not.")
        print("")
        print("[ACTION REQUIRED] Do NOT report this as 'orphan' or 'safe to delete'.")
        print("[ACTION REQUIRED] Verify the object name/type, or confirm it was already deleted.")
        print("=" * 60)
        return 2
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] WHERE-USED SEARCH FAILED - could NOT search for usages of {args.object_name}")
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
        print(f"[FAIL] WHERE-USED SEARCH FAILED - could NOT search for usages of {args.object_name}")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if not results:
        # Buraya gelindiyse obje VARLIGI dogrulanmistir (where_used gate'i 404'te
        # SAPObjectNotFoundError firlatir) — bu yuzden "0 usages" guvenilir bir iddiadir.
        print(f"[OK] No usages found for: {args.object_name} (object EXISTS, verified)")
        return 0

    print(f"[OK] Found {len(results)} usage(s) of {args.object_name}:")
    print()
    for ref in results:
        obj_type = ref.get('type', 'UNKNOWN')
        obj_name = ref.get('name', '?')
        uri = ref.get('uri', '')
        desc = ref.get('description', '')
        desc_str = f" - {desc}" if desc else ""
        print(f"  [{obj_type:8}] {obj_name}{desc_str}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

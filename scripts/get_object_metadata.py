#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Get SAP ABAP object metadata/structure without full source (token-efficient).

Usage:
    python get_object_metadata.py --name ZCL_MY_CLASS --type class --cwd /path/to/project
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
        description='Get SAP ABAP object metadata/structure (token-efficient, no full source)'
    )
    parser.add_argument('--name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--type', default='class',
                       choices=['class', 'clas', 'interface', 'intf', 'program', 'prog',
                               'report', 'include', 'incl', 'functiongroup', 'fugr'],
                       help='Object type (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        metadata = client.get_object_metadata(
            object_name=args.name,
            object_type=args.type
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] GET METADATA FAILED - could NOT retrieve metadata for {args.name}")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if metadata:
        print(f"[OK] Retrieved metadata for: {args.name}")
        print("\nMetadata preview (first 1000 chars):")
        print("=" * 80)
        print(metadata[:1000])
        if len(metadata) > 1000:
            print(f"\n... ({len(metadata) - 1000} more characters)")
        print("=" * 80)
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] GET METADATA FAILED - could NOT retrieve metadata for {args.name}")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

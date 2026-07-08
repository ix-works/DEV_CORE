#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List SAP package contents in one command."""
import argparse
import sys
import io
from pathlib import Path

# Force UTF-8 output on Windows
def _setup_utf8_output():
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
                if hasattr(sys.stdout, 'buffer'):
                    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'encoding') and sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
                if hasattr(sys.stderr, 'buffer'):
                    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

_setup_utf8_output()

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from sap_adt_lib import set_explicit_working_dir
from sap_client import SAPClient


def main():
    parser = argparse.ArgumentParser(description='List SAP package contents')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    parser.add_argument('--package', required=True, help='Package name (e.g., ZSD000)')
    parser.add_argument('--type', dest='obj_type', help='Filter by ADT type prefix (e.g., CLAS, INTF)')
    parser.add_argument('--max', dest='max_results', type=int, default=500, help='Max results for fallback search')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        objects = client.list_package_contents(args.package)
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] LIST PACKAGE CONTENTS FAILED - could NOT list contents of {args.package}")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if args.obj_type:
        obj_type = args.obj_type.upper()
        objects = [o for o in objects if (o.get('type') or '').startswith(obj_type)]

    if not objects:
        print("No objects found")
        return 1

    print(f"\nFound {len(objects)} object(s) in package {args.package}:")
    for obj in sorted(objects, key=lambda x: x.get('name', '')):
        obj_type = obj.get('type', '')
        desc = f" - {obj.get('description')}" if obj.get('description') else ""
        print(f"  [{obj_type}] {obj.get('name')}{desc}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

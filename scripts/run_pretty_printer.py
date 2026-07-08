#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Format ABAP source code using SAP Pretty Printer.

Applies SAP's server-side code formatting (indentation, casing, etc.)
to ABAP source code. Works with classes, programs, function modules, etc.

Usage:
    python run_pretty_printer.py --object-name ZCL_MY_CLASS --object-type class --cwd /path/to/project
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
        description='Format ABAP source code using SAP Pretty Printer'
    )
    parser.add_argument('--object-name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--object-type', default='class',
                       help='Object type: class, interface, program, include, function (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        result = client.pretty_print(
            object_name=args.object_name,
            object_type=args.object_type
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] PRETTY PRINTER FAILED - {args.object_name} was NOT formatted in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Pretty printer applied to: {args.object_name}")
        if isinstance(result, str):
            print(f"\nFormatted source ({len(result)} chars):")
            print(result)
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] PRETTY PRINTER FAILED - {args.object_name} was NOT formatted in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

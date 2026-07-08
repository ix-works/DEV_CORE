#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create SAP ABAP object (class, interface, program, include, function group).

Usage:
    python create_object.py --name ZCL_MY_CLASS --type class --package ZSD000 --description "My class" --transport TRXXXXX --cwd /path/to/project
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
        description='Create SAP ABAP object (class, interface, program, etc.)'
    )
    parser.add_argument('--name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS, ZIF_MY_INTERFACE)')
    parser.add_argument('--type', default='class',
                       choices=['class', 'clas', 'interface', 'intf', 'program', 'prog',
                               'report', 'include', 'incl', 'functiongroup', 'fugr'],
                       help='Object type (default: class)')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--description', required=True,
                       help='Object description')
    parser.add_argument('--transport',
                       help='Transport request number (e.g., TRXXXXXX)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    if not args.transport:
        print("[FAIL] --transport is required.")
        print("[INFO] You MUST run list_transports.py --modifiable-only and ASK the user which transport to use.")
        print("[INFO] NEVER assume, fabricate, or reuse a transport number from memory.")
        return 1

    try:
        client = SAPClient()
        result = client.create_object(
            object_type=args.type,
            name=args.name,
            package=args.package,
            description=args.description,
            transport=args.transport
        )
    except Exception as e:
        result = None
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE FAILED - object {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user the object was created.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Object created successfully: {args.name}")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE FAILED - object {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user the object was created.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("[HINT] Check transport is valid: run list_transports.py --modifiable-only")
        print("[HINT] Check package exists: run check_package.py --name %s" % args.package)
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

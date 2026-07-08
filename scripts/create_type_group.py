#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create type group in SAP.

Note: Type groups are legacy ABAP constructs for defining reusable types and constants.
They are used with the TYPE-POOLS statement. Keep name short (max 4 chars recommended).

Usage:
    python create_type_group.py --name ZSD000TY --source-file /path/to/types.txt --description "ZSD000 Type Definitions" --package ZSD000 --transport TRXXXXX --cwd /path/to/project

Source file format example (TYPES and CONSTANTS only, no type-pool statement):
    TYPES zai_status_type TYPE c LENGTH 1.
    CONSTANTS zai_status_active TYPE zai_status_type VALUE 'A'.
    CONSTANTS zai_status_inactive TYPE zai_status_type VALUE 'I'.
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
        description='Create type group in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Type group name (e.g., ZSD000TY, ZSD000EM) - max 4 chars recommended')
    parser.add_argument('--source-file', required=True,
                       help='Path to file containing TYPES and CONSTANTS definitions')
    parser.add_argument('--description', required=True,
                       help='Type group description')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
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

    # Validate name length
    if len(args.name) > 4:
        print("[WARNING] Type group names should be max 4 characters for SAP compatibility")

    # Read source file
    source_path = Path(args.source_file)
    if not source_path.exists():
        print(f"[ERROR] Source file not found: {args.source_file}")
        return 1

    with open(source_path, 'r', encoding='utf-8') as f:
        types_and_constants = f.read()

    try:
        client = SAPClient()
        result = client.create_type_group(
            name=args.name,
            types_and_constants=types_and_constants,
            description=args.description,
            package=args.package,
            transport=args.transport
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE TYPE GROUP FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Type group created successfully: {args.name}")
        print(f"[INFO] Remember to activate the type group before use!")
        print(f"[INFO] Use in ABAP with: TYPE-POOLS {args.name}.")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE TYPE GROUP FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create ABAP Behavior Implementation in SAP.

Behavior Implementations (BIMP) contain the actual ABAP code for behavior
defined in Behavior Definitions. They implement validations, determinations,
actions, and draft table handling.

Usage:
    python create_behavior_implementation.py --name ZBP_MY_ENTITY --description "My Behavior Implementation" --package ZSD000 --behavior-definition ZI_MY_BDEF --transport TRXXXXX --cwd /path/to/project
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
        description='Create ABAP Behavior Implementation (BIMP) in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Behavior Implementation name (e.g., ZBP_MY_ENTITY)')
    parser.add_argument('--description', default='',
                       help='Description for the behavior implementation')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000, $TMP for local)')
    parser.add_argument('--transport',
                       help='Transport request number (required for non-local packages)')
    parser.add_argument('--behavior-definition', '--bdef', required=True,
                       help='Behavior Definition name (e.g., ZI_MY_BDEF)')
    parser.add_argument('--source-file',
                       help='Path to BIMP source file (optional, creates empty if not provided)')
    parser.add_argument('--activate', action='store_true', default=True,
                       help='Activate after creation (default: true)')
    parser.add_argument('--no-activate', dest='activate', action='store_false',
                       help='Do not activate after creation')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    # For non-local packages, transport is required
    if args.package != '$TMP' and not args.transport:
        print("[FAIL] --transport is required for non-local packages.")
        print("[INFO] Run list_transports.py --modifiable-only and ASK the user which transport to use.")
        return 1

    # Read source from file if provided
    source = None
    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.exists():
            print(f"[ERROR] Source file not found: {args.source_file}")
            return 1
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

    try:
        client = SAPClient()
        result = client.create_behavior_implementation(
            name=args.name.upper(),
            description=args.description or args.name,
            package=args.package,
            transport=args.transport or '',
            behavior_definition=args.behavior_definition.upper(),
            source=source,
            activate=args.activate
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE BEHAVIOR IMPLEMENTATION FAILED - {args.name} was NOT created")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result and result.get('success'):
        print(f"[OK] Behavior Implementation created successfully: {args.name}")
        if args.activate:
            print(f"[OK] Behavior Implementation activated: {args.name}")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE BEHAVIOR IMPLEMENTATION FAILED - {args.name} was NOT created")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

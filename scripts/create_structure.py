#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create DDIC structure in SAP.

Usage:
    python create_structure.py --name ZSD000_S_CUSTOMER --fields '[{"name":"CUSTOMER_ID","type":"char10"},{"name":"CUSTOMER_NAME","type":"char50"}]' --description "Customer structure" --package ZSD000 --transport TRXXXXX --cwd /path/to/project
"""
import argparse
import sys
import json
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
        description='Create DDIC structure in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Structure name (e.g., ZSD000_S_CUSTOMER)')
    parser.add_argument('--fields', required=True,
                       help='Field definitions as JSON array. Example: \'[{"name":"ID","type":"char10"},{"name":"NAME","type":"char50"}]\'')
    parser.add_argument('--description', required=True,
                       help='Structure description')
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

    # Parse fields JSON
    try:
        fields = json.loads(args.fields)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in --fields: {e}")
        print("[INFO] Example format: '[{\"name\":\"ID\",\"type\":\"char10\"},{\"name\":\"NAME\",\"type\":\"char50\"}]'")
        return 1

    try:
        client = SAPClient()
        result = client.create_structure(
            name=args.name,
            fields=fields,
            description=args.description,
            package=args.package,
            transport=args.transport
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE STRUCTURE FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Structure created successfully: {args.name}")
        print(f"[INFO] Remember to activate the structure before use!")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE STRUCTURE FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

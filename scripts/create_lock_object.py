#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create lock object (ENQU) in SAP.

Note: Lock object names must start with 'E'.

Usage:
    python create_lock_object.py --name EZSD000_CUSTOMER --primary-table ZSD000_T_CUSTOMER --lock-fields '["CUSTOMER_ID"]' --description "Customer lock" --package ZSD000 --transport TRXXXXX --cwd /path/to/project

Note: --lock-fields = JSON STRING-array (["F1","F2"]), dict DEĞİL. Lib field.upper() çağırır.
Note: create AKTİVE ETMEZ → sonra ayrı activate + FM-generate gerekir (bkz playbook/adt-lock-objects.md).
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
        description='Create lock object (ENQU) in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Lock object name (e.g., EZSD000_CUSTOMER) - must start with E')
    parser.add_argument('--primary-table', required=True,
                       help='Primary table to lock (e.g., ZSD000_T_CUSTOMER)')
    parser.add_argument('--lock-fields', required=True,
                       help='Lock field names as JSON array. Example: \'["CUSTOMER_ID","CLIENT"]\'')
    parser.add_argument('--description', required=True,
                       help='Lock object description')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--transport',
                       help='Transport request number (e.g., TRXXXXXX)')
    parser.add_argument('--lock-mode', default='E',
                       choices=['E', 'S', 'X'],
                       help='Lock mode: E=exclusive, S=shared, X=exclusive non-cumulative (default: E)')
    parser.add_argument('--allow-rfc', action='store_true',
                       help='Allow RFC access to the lock')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    if not args.transport:
        print("[FAIL] --transport is required.")
        print("[INFO] You MUST run list_transports.py --modifiable-only and ASK the user which transport to use.")
        print("[INFO] NEVER assume, fabricate, or reuse a transport number from memory.")
        return 1

    # Validate lock object name starts with E
    if not args.name.upper().startswith('E'):
        print("[WARNING] Lock object names typically start with 'E'")

    # Parse lock fields JSON
    try:
        lock_fields = json.loads(args.lock_fields)
        if not isinstance(lock_fields, list):
            print("[ERROR] --lock-fields must be a JSON array")
            return 1
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in --lock-fields: {e}")
        print("[INFO] Example format: '[\"CUSTOMER_ID\",\"CLIENT\"]'")
        return 1

    try:
        client = SAPClient()
        result = client.create_lock_object(
            name=args.name,
            primary_table=args.primary_table,
            description=args.description,
            package=args.package,
            lock_fields=lock_fields,
            transport=args.transport,
            lock_mode=args.lock_mode,
            allow_rfc=args.allow_rfc
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE LOCK OBJECT FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Lock object created successfully: {args.name}")
        print(f"[INFO] Generated functions: ENQUEUE_{args.name.upper()}, DEQUEUE_{args.name.upper()}")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE LOCK OBJECT FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

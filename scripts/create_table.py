#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create database table in SAP.

Usage with reference structure (recommended):
    python create_table.py --name ZSD000_T_CONFIG --description "Config table" --package ZSD000 --ref-structure ZSD000_S_CONFIG --transport TRXXXXX --cwd /path/to/project

Usage with direct fields:
    python create_table.py --name ZSD000_T_CONFIG --description "Config table" --package ZSD000 --fields '[{"name":"CLIENT","type":"mandt","key":true},{"name":"ID","type":"char10","key":true}]' --transport TRXXXXX --cwd /path/to/project
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
        description='Create database table in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Table name (e.g., ZSD000_T_CONFIG)')
    parser.add_argument('--description', required=True,
                       help='Table description')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--transport',
                       help='Transport request number (e.g., TRXXXXXX)')
    parser.add_argument('--ref-structure',
                       help='Reference structure name (recommended, mutually exclusive with --fields)')
    parser.add_argument('--fields',
                       help='Field definitions as JSON array (mutually exclusive with --ref-structure). Example: \'[{"name":"CLIENT","type":"mandt","key":true},{"name":"ID","type":"char10","key":true}]\'')
    parser.add_argument('--table-category', default='TRANSP',
                       choices=['TRANSP', 'POOL', 'CLUSTER', 'VIEW'],
                       help='Table category (default: TRANSP)')
    parser.add_argument('--delivery-class', default='A',
                       choices=['A', 'C', 'L', 'G', 'S', 'W'],
                       help='Delivery class (default: A for application table)')
    parser.add_argument('--data-maintenance', default='ALLOWED',
                       choices=['ALLOWED', 'RESTRICTED', 'NOT_ALLOWED', 'LIMITED'],
                       help='Data maintenance (default: ALLOWED)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    if not args.transport:
        print("[FAIL] --transport is required.")
        print("[INFO] You MUST run list_transports.py --modifiable-only and ASK the user which transport to use.")
        print("[INFO] NEVER assume, fabricate, or reuse a transport number from memory.")
        return 1

    # Validate mutually exclusive options
    if args.ref_structure and args.fields:
        print("[ERROR] --ref-structure and --fields are mutually exclusive")
        return 1
    if not args.ref_structure and not args.fields:
        print("[ERROR] Either --ref-structure or --fields must be specified")
        return 1

    # Parse fields if provided
    fields = None
    if args.fields:
        try:
            fields = json.loads(args.fields)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in --fields: {e}")
            return 1

    try:
        client = SAPClient()
        result = client.create_table(
            name=args.name,
            description=args.description,
            package=args.package,
            transport=args.transport,
            ref_structure=args.ref_structure,
            fields=fields,
            table_category=args.table_category,
            delivery_class=args.delivery_class,
            data_maintenance=args.data_maintenance
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE TABLE FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Table created successfully: {args.name}")
        print(f"[INFO] Remember to activate the table before use!")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE TABLE FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create DDIC domain in SAP.

Usage:
    python create_domain.py --name ZSD000_D_STATUS --datatype CHAR --length 1 --description "Status" --package ZSD000 --transport TRXXXXX --cwd /path/to/project
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
        description='Create DDIC domain in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Domain name (e.g., ZSD000_D_STATUS)')
    parser.add_argument('--datatype', required=True,
                       choices=['CHAR', 'NUMC', 'INT4', 'INT8', 'FLTP', 'DATS', 'TIMS', 'CURR', 'QUAN', 'DEC', 'LCHR'],
                       help='Data type (e.g., CHAR, NUMC, INT4)')
    parser.add_argument('--length', type=int, required=True,
                       help='Field length (e.g., 10)')
    parser.add_argument('--description', required=True,
                       help='Domain description')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--transport',
                       help='Transport request number (e.g., TRXXXXXX)')
    parser.add_argument('--decimals', type=int, default=0,
                       help='Number of decimal places (default: 0)')
    parser.add_argument('--lowercase', action='store_true',
                       help='Allow lowercase letters')
    parser.add_argument('--fixed-values',
                       help='Fixed values as JSON array: \'[{"value":"A","text":"Active"},{"value":"I","text":"Inactive"}]\'')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    if not args.transport:
        print("[FAIL] --transport is required.")
        print("[INFO] You MUST run list_transports.py --modifiable-only and ASK the user which transport to use.")
        print("[INFO] NEVER assume, fabricate, or reuse a transport number from memory.")
        return 1

    # Parse fixed values if provided
    fixed_values = None
    if args.fixed_values:
        try:
            fixed_values = json.loads(args.fixed_values)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in --fixed-values: {e}")
            return 1

    try:
        client = SAPClient()
        result = client.create_domain(
            name=args.name,
            datatype=args.datatype,
            length=args.length,
            description=args.description,
            package=args.package,
            transport=args.transport,
            decimals=args.decimals,
            lowercase=args.lowercase,
            fixed_values=fixed_values
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE DOMAIN FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Domain created successfully: {args.name}")
        print(f"[INFO] Remember to activate the domain before use!")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE DOMAIN FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

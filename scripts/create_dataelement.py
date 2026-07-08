#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create DDIC data element in SAP.

Usage:
    python create_dataelement.py --name ZSD000_E_STATUS --domain ZSD000_D_STATUS --description "Status field" --package ZSD000 --transport TRXXXXX --cwd /path/to/project
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
        description='Create DDIC data element in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Data element name (e.g., ZSD000_E_STATUS)')
    parser.add_argument('--domain', required=True,
                       help='Domain name (e.g., ZSD000_D_STATUS, CHAR10)')
    parser.add_argument('--description', required=True,
                       help='Data element description')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--transport',
                       help='Transport request number (e.g., TRXXXXXX)')
    parser.add_argument('--short-label',
                       help='Short field label (max 10 chars)')
    parser.add_argument('--medium-label',
                       help='Medium field label (max 20 chars)')
    parser.add_argument('--long-label',
                       help='Long field label (max 40 chars)')
    parser.add_argument('--heading-label',
                       help='Heading label (max 55 chars)')
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
        result = client.create_dataelement(
            name=args.name,
            domain_name=args.domain,
            description=args.description,
            package=args.package,
            transport=args.transport,
            short_label=args.short_label,
            medium_label=args.medium_label,
            long_label=args.long_label,
            heading_label=args.heading_label
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE DATA ELEMENT FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Data element created successfully: {args.name}")
        print(f"[INFO] Remember to activate the data element before use!")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE DATA ELEMENT FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

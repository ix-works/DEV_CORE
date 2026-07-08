#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create CDS Metadata Extension (DDLX) in SAP.

Metadata extensions allow adding annotations to CDS views without modifying
the original view definition. Used for UI annotations, search help, etc.

Usage:
    python create_metadata_extension.py --name ZSD000_E_CUSTOMER --source-file /path/to/source.ddlx --description "Customer UI annotations" --package ZSD000 --transport TRXXXXX --cwd /path/to/project
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
        description='Create CDS Metadata Extension (DDLX) in SAP'
    )
    parser.add_argument('--name', required=True,
                       help='Metadata extension name (e.g., ZSD000_E_CUSTOMER)')
    parser.add_argument('--source-file', required=True,
                       help='Path to DDLX source file')
    parser.add_argument('--description', required=True,
                       help='Metadata extension description')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--transport',
                       help='Transport request number')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    if not args.transport:
        print("[FAIL] --transport is required.")
        print("[INFO] You MUST run list_transports.py --modifiable-only and ASK the user which transport to use.")
        print("[INFO] NEVER assume, fabricate, or reuse a transport number from memory.")
        return 1

    # Read source from file
    source_path = Path(args.source_file)
    if not source_path.exists():
        print(f"[ERROR] Source file not found: {args.source_file}")
        return 1

    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        client = SAPClient()
        result = client.create_metadata_extension(
            name=args.name,
            source=source,
            description=args.description,
            package=args.package,
            transport=args.transport
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE METADATA EXTENSION FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result:
        print(f"[OK] Metadata extension created successfully: {args.name}")
        return 0
    else:
        print("")
        print("=" * 60)
        print(f"[FAIL] CREATE METADATA EXTENSION FAILED - {args.name} was NOT created in SAP")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create transport request in SAP.

Usage:
    python create_transport.py --description "New features" --package ZSD000 --cwd /path/to/project
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
        description='Create transport request in SAP'
    )
    parser.add_argument('--description', required=True,
                       help='Transport description (e.g., "New AI features")')
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    client = SAPClient()
    transport_num = client.create_transport(
        description=args.description,
        package_name=args.package
    )

    if transport_num:
        print(f"[OK] Transport created successfully: {transport_num}")
        print(f"[INFO] Use this transport number for subsequent object creation/push operations")
        return 0
    else:
        print("[FAIL] Failed to create transport")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List SAP transport requests for the current user.

Accepts --filter argument to filter transports by description.
"""
import argparse
import sys
import io
from pathlib import Path

# Force UTF-8 output on Windows to avoid encoding errors
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from sap_adt_lib import set_explicit_working_dir
from sap_client import SAPClient
from sap_adt_lib import SAPADTClient
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description='List SAP transport requests')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    parser.add_argument('--filter', help='Filter transports by description text')
    parser.add_argument('--user', help='Username (defaults to current user)')
    parser.add_argument('--modifiable-only', action='store_true',
                       help='Show only modifiable transports')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    # Get transports
    try:
        adt = SAPADTClient()
        result = adt.user_transports(user=args.user, modifiable_only=args.modifiable_only)

        # Parse XML
        root = ET.fromstring(result)
        ns = {'tm': 'http://www.sap.com/cts/adt/tm'}
        ns_uri = 'http://www.sap.com/cts/adt/tm'

        transports = []
        for tr in root.findall('.//tm:request', ns):
            transport_id = tr.get(f'{{{ns_uri}}}number')
            description = tr.get(f'{{{ns_uri}}}desc', '')
            status = tr.get(f'{{{ns_uri}}}status', '')

            if transport_id:
                transports.append({
                    'number': transport_id,
                    'description': description,
                    'status': status
                })
    except Exception as e:
        print("")
        print("=" * 60)
        print("[FAIL] LIST TRANSPORTS FAILED - could NOT retrieve transport list from SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    # Filter if requested
    if args.filter:
        filter_lower = args.filter.lower()
        transports = [t for t in transports if filter_lower in t['description'].lower()]

    if args.modifiable_only:
        transports = [t for t in transports if t['status'] == 'Modifiable' or t['status'] == 'D']

    # Print results
    if transports:
        print(f"\nFound {len(transports)} transport(s):\n")
        for t in transports:
            # Use ASCII symbols instead of emoji to avoid Windows encoding errors
            status_symbol = "[+]" if t['status'] in ['Modifiable', 'D'] else "[ ]"
            print(f"  {status_symbol} {t['number']} - {t['description']} [{t['status']}]")
    else:
        print("No transports found")
        if args.filter:
            print(f"  (filtered by: {args.filter})")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

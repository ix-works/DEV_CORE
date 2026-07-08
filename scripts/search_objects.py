#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search for SAP ABAP objects by pattern.

KNOWN LIMITATION: SAP ADT quickSearch endpoint has issues with specific patterns
combined with object type filters (e.g., "ZSD000*" + type="INTF" returns no results).

Root Cause:
- When both a specific pattern (e.g., "ZSD000*") and an object type filter (e.g., "INTF")
  are provided, SAP's search indexer may apply the type filter BEFORE pattern matching
- This causes the search to fail because it tries to find INTF objects first, then
  applies the ZSD000* pattern, which doesn't match SAP's internal search order

Workaround:
- Use broader patterns like "Z*" instead of "ZSD000*" when using type filters
- Then filter results client-side for your specific prefix
- Example: search_objects.py --query "Z*" --type INTF --max-results 500

Usage:
    python search_objects.py --query "Z*" --max-results 50 --type CLAS --cwd /path/to/project
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
        description='Search for SAP ABAP objects by pattern'
    )
    parser.add_argument('--query', required=True,
                       help='Search query (supports wildcards like ZSD000*)')
    parser.add_argument('--max-results', type=int, default=50,
                       help='Maximum number of results (default: 50)')
    parser.add_argument('--type',
                       help='Filter by ADT type (e.g., CLAS, INTF, PROG)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        results = client.search_objects(
            query=args.query,
            max_results=args.max_results,
            obj_type=args.type
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] SEARCH FAILED - could NOT search for objects in SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    # Print summary
    if results:
        print(f"\nTotal results: {len(results)}")
        for obj in results:
            type_short = obj['type'].split('/')[0] if '/' in obj['type'] else obj['type']
            desc = f" - {obj['description']}" if obj['description'] else ""
            print(f"  [{type_short:4}] {obj['name']}{desc}")
    else:
        print("No results found")
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

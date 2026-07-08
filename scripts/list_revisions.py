#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List object revision history from SAP.

Usage:
    python list_revisions.py --name ZCL_MY_CLASS --type class

With object URL:
    python list_revisions.py --url /sap/bc/adt/oo/classes/zcl_my_class
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
        description='List object revision history from SAP'
    )
    parser.add_argument('--name', help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--type', default='class',
                       choices=['class', 'clas', 'interface', 'intf', 'program', 'prog',
                               'report', 'table', 'tabl', 'view', 'viewd', 'ddic'],
                       help='Object type (default: class)')
    parser.add_argument('--url', help='Full object URL (alternative to name+type)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    parser.add_argument('--limit', type=int, default=20,
                       help='Maximum number of revisions to show (default: 20)')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()

        # Build object URL if not provided
        if args.url:
            object_url = args.url
        elif args.name:
            # Map common type names to ADT object types
            type_map = {
                'class': '/sap/bc/adt/oo/classes',
                'clas': '/sap/bc/adt/oo/classes',
                'interface': '/sap/bc/adt/oo/interfaces',
                'intf': '/sap/bc/adt/oo/interfaces',
                'program': '/sap/bc/adt/programs/programs',
                'prog': '/sap/bc/adt/programs/programs',
                'report': '/sap/bc/adt/programs/programs',
                'table': '/sap/bc/adt/ddic/ddl/sources',
                'tabl': '/sap/bc/adt/ddic/ddl/sources',
                'view': '/sap/bc/adt/ddic/ddlx/sources',
                'viewd': '/sap/bc/adt/ddic/ddlx/sources',
            }

            obj_type = args.type.lower()
            if obj_type not in type_map:
                print(f"[ERROR] Unsupported object type: {args.type}")
                print(f"Supported types: {', '.join(type_map.keys())}")
                return 1

            base_url = type_map[obj_type]
            object_url = f"{base_url}/{args.name.lower()}"
        else:
            print("[ERROR] Either --name or --url is required")
            parser.print_help()
            return 1

        # Get revisions
        revisions = client.adt_client.get_object_revisions(object_url)
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] LIST REVISIONS FAILED - could NOT retrieve revisions for {args.name or args.url}")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if not revisions:
        print(f"[INFO] No revisions found for object: {args.name or args.url}")
        return 0

    # Display revisions
    print(f"\\n{'='*80}")
    print(f"Revision History: {args.name or args.url}")
    print(f"{'='*80}\\n")

    for i, rev in enumerate(revisions[:args.limit], 1):
        print(f"Revision {i}:")
        print(f"  Version:     {rev.get('version', 'N/A')}")
        print(f"  Title:       {rev.get('versionTitle', 'N/A')}")
        print(f"  Author:      {rev.get('author', 'Unknown')}")
        print(f"  Date:        {rev.get('date', 'Unknown')}")
        print(f"  URI:         {rev.get('uri', 'N/A')}")
        print()

    if len(revisions) > args.limit:
        print(f"... and {len(revisions) - args.limit} more revisions")
        print(f"Total: {len(revisions)} revisions")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download SAP ABAP object source code or DDIC definitions.

Usage:
    python download_object.py --name ZCL_MY_CLASS --type class --cwd /path/to/project
    python download_object.py --name ZSD000_E_TEST --type dataelement --cwd /path/to/project
    python download_object.py --name ZSD000_D_TEST --type domain --cwd /path/to/project
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

# DDIC types mapping
DDIC_TYPES = {
    'dataelement': 'dtel',
    'dtel': 'dtel',
    'domain': 'doma',
    'doma': 'doma',
    'table': 'tabl',
    'tabl': 'tabl',
    'structure': 'tabl',  # Structures are stored with tables
    'tabletype': 'ttyp',
    'ttyp': 'ttyp'
}

# Abap source types
ABAP_TYPES = ['class', 'clas', 'interface', 'intf', 'program', 'prog',
              'report', 'include', 'incl', 'functiongroup', 'fugr']


def main():
    parser = argparse.ArgumentParser(
        description='Download SAP ABAP object source code or DDIC definitions'
    )
    parser.add_argument('--name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS, ZSD000_E_TEST)')
    parser.add_argument('--type', default='class',
                       choices=ABAP_TYPES + list(DDIC_TYPES.keys()),
                       help='Object type (default: class)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save to local file (print to stdout only)')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()

        # Determine if this is a DDIC or ABAP type
        if args.type in DDIC_TYPES:
            # DDIC object - use get_ddic_object
            ddic_type = args.type
            # Map short names to full names for the API
            type_map = {
                'dtel': 'dataelement',
                'doma': 'domain',
                'tabl': 'table',
                'ttyp': 'tabletype'
            }
            api_type = type_map.get(ddic_type, ddic_type)

            xml_content = client.get_ddic_object(api_type, args.name)

            if not xml_content:
                print("")
                print("=" * 60)
                print(f"[FAIL] DOWNLOAD FAILED - {args.name} was NOT downloaded from SAP")
                print("=" * 60)
                print("")
                print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
                print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
                print("=" * 60)
                return 1

            if args.no_save:
                print(xml_content)
            else:
                # Save to local file
                folder_name = DDIC_TYPES.get(args.type, args.type)
                target_dir = Path(client.local_base).parent / folder_name
                target_dir.mkdir(parents=True, exist_ok=True)
                file_path = target_dir / f"{args.name.upper()}.xml"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                print(f"[OK] Saved to: {file_path}")

            return 0
        else:
            # ABAP source code object
            source = client.download_object(
                object_name=args.name,
                object_type=args.type,
                save_local=not args.no_save
            )

            if not source:
                print("")
                print("=" * 60)
                print(f"[FAIL] DOWNLOAD FAILED - {args.name} was NOT downloaded from SAP")
                print("=" * 60)
                print("")
                print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
                print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
                print("=" * 60)
                return 1

            if args.no_save:
                print(source)

            return 0
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] DOWNLOAD FAILED - {args.name} was NOT downloaded from SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

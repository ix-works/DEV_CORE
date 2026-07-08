#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download all DDIC objects from a package.

Usage:
    python download_ddic_objects.py --package ZSD000 --cwd /path/to/project
    python download_ddic_objects.py --package ZSD000 --types dtel,doma --cwd /path/to/project
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

# DDIC type mappings
DDIC_TYPE_MAP = {
    'DTEL/DE': ('dataelement', 'dtel'),
    'DOMA/DD': ('domain', 'doma'),
    'TABL/DT': ('table', 'tabl'),
    'TABL/DS': ('structure', 'tabl'),  # Structures saved with tables
    'TTYP/DA': ('tabletype', 'ttyp')
}


def main():
    parser = argparse.ArgumentParser(
        description='Download all DDIC objects from a SAP package'
    )
    parser.add_argument('--package', required=True,
                       help='Package name (e.g., ZSD000)')
    parser.add_argument('--types', default='dtel,doma,tabl,ttyp',
                       help='Comma-separated DDIC types to download (default: dtel,doma,tabl,ttyp)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    parser.add_argument('--dry-run', action='store_true',
                       help='List objects without downloading')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    requested_types = [t.strip().lower() for t in args.types.split(',')]

    try:
        client = SAPClient()
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] DOWNLOAD DDIC OBJECTS FAILED - could NOT connect to SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    print(f"\n{'=' * 70}")
    print(f"  Downloading DDIC objects from package: {args.package}")
    print(f"{'=' * 70}")
    print(f"  Types: {', '.join(requested_types)}")

    # Get package contents
    try:
        objects = client.list_package_contents(args.package)
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] DOWNLOAD DDIC OBJECTS FAILED - could NOT list package {args.package}")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    # Filter DDIC objects
    ddic_objects = []
    for obj in objects:
        obj_type = obj.get('type', '')
        if obj_type in DDIC_TYPE_MAP:
            api_type, folder = DDIC_TYPE_MAP[obj_type]
            if folder in requested_types:
                ddic_objects.append({
                    'name': obj.get('name', ''),
                    'type': obj_type,
                    'api_type': api_type,
                    'folder': folder,
                    'description': obj.get('description', '')
                })

    print(f"\n  Found {len(ddic_objects)} DDIC objects to download:\n")

    # Group by folder for display
    by_folder = {}
    for obj in ddic_objects:
        folder = obj['folder']
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(obj)

    for folder, objs in sorted(by_folder.items()):
        print(f"  {folder.upper()} ({len(objs)}):")
        for obj in objs:
            print(f"    - {obj['name']}: {obj['description']}")
        print()

    if args.dry_run:
        print("  [DRY RUN] No files downloaded.")
        return 0

    # Download each object
    success_count = 0
    error_count = 0

    for obj in ddic_objects:
        try:
            print(f"  Downloading {obj['folder']}/{obj['name']}...", end=' ')

            xml_content = client.get_ddic_object(obj['api_type'], obj['name'])

            # Save to local file
            target_dir = Path(client.local_base).parent / obj['folder']
            target_dir.mkdir(parents=True, exist_ok=True)
            file_path = target_dir / f"{obj['name'].upper()}.xml"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            print(f"[OK]")
            success_count += 1

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            error_count += 1

    print(f"\n{'=' * 70}")
    print(f"  Download complete: {success_count} success, {error_count} errors")
    print(f"{'=' * 70}")

    if error_count > 0:
        print("")
        print("=" * 60)
        print(f"[FAIL] DOWNLOAD DDIC OBJECTS FAILED - {error_count} object(s) were NOT downloaded")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

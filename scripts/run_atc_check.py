#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run ATC (ABAP Test Cockpit) code quality checks.

Executes ATC checks on ABAP objects and reports findings including
errors, warnings, and informational messages with locations.

Usage:
    python run_atc_check.py --object-name ZCL_MY_CLASS --object-type class --cwd /path/to/project
    python run_atc_check.py --object-name ZSD000 --object-type package --variant DEFAULT --cwd /path/to/project
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


def atc_bulgulari(object_name, object_type='class', variant='DEFAULT',
                  max_verdicts=100, client=None):
    """Tek hedefin (obje/paket) ATC ham sonucu — yeniden kullanım girişi (Q371①, 2026-10-12).

    `SAPClient.run_atc_check` ile AYNI yol (get_object_url + lib 3 adımlı worklist akışı),
    iki farkla: ① `max_verdicts` AÇIK geçirilir (SAPClient sarmalayıcısı geçirmez ⇒ lib
    varsayılanı 100'de paket sonucu SESSİZCE kesilebilir) ② hata YUTULMAZ (sarmalayıcı
    istisnayı `None`a çevirir; toplu araç hangi hedefin neden koşamadığını raporlamalı).
    Döner: {'findings': [...], ('worklist_parse_fallback': True)}. `main()` bunu KULLANMAZ —
    tek-obje CLI davranışı değişmedi.
    """
    from object_types import get_object_url
    client = client or SAPClient()
    url = get_object_url(object_name, object_type)
    return client.adt_client.run_atc_check(url, variant=variant, max_verdicts=max_verdicts)


def main():
    parser = argparse.ArgumentParser(
        description='Run ATC (ABAP Test Cockpit) code quality checks'
    )
    parser.add_argument('--object-name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS or package name ZSD000)')
    parser.add_argument('--object-type', default='class',
                       help='Object type: class, interface, program, package (default: class)')
    parser.add_argument('--variant', default='DEFAULT',
                       help='ATC check variant (default: DEFAULT)')
    parser.add_argument('--max-findings', type=int, default=100,
                       help='Maximum findings to display (default: 100)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    try:
        client = SAPClient()
        result = client.run_atc_check(
            object_name=args.object_name,
            object_type=args.object_type,
            variant=args.variant
        )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] ATC CHECK FAILED - could NOT run ATC check on {args.object_name}")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    if result is None:
        print("")
        print("=" * 60)
        print(f"[FAIL] ATC CHECK FAILED - could NOT run ATC check on {args.object_name}")
        print("=" * 60)
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user this operation succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("=" * 60)
        return 1

    findings = result.get('findings', [])
    print(f"[OK] ATC check completed for: {args.object_name}")
    print(f"Variant: {args.variant}")
    print(f"Total findings: {len(findings)}")

    if not findings:
        print("\nNo findings - code is clean!")
        return 0

    # Group by priority
    by_priority = {}
    for f in findings:
        prio = f.get('priority', 'unknown')
        by_priority.setdefault(prio, []).append(f)

    print()
    for prio in sorted(by_priority.keys()):
        items = by_priority[prio]
        prio_label = {'1': 'ERROR', '2': 'WARNING', '3': 'INFO'}.get(str(prio), f'P{prio}')
        print(f"  {prio_label}: {len(items)}")

    print(f"\n{'=' * 90}")
    shown = 0
    for f in findings:
        if shown >= args.max_findings:
            print(f"\n... and {len(findings) - shown} more findings")
            break
        prio = f.get('priority', '?')
        prio_label = {'1': 'ERR', '2': 'WRN', '3': 'INF'}.get(str(prio), f'P{prio}')
        msg = f.get('message', '')
        location = f.get('location', '')
        check_id = f.get('checkId', '')
        print(f"  [{prio_label}] {msg}")
        if location:
            print(f"Location: {location}")
        if check_id:
            print(f"         Check: {check_id}")
        shown += 1

    print(f"{'=' * 90}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

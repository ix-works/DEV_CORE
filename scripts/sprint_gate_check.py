#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sprint Gate Check — Tüm sprint'lerin SAP TADIR vs plan karşılaştırması.

KURAL (LESSONS_LEARNED.md PATTERN #1):
  Sprint X kapanmadan Sprint X+1'e geçiş YASAK. Bu script'in çıktısı:
  - Açık sprint VAR ise: forward işlem exit 1 ile durdurulur
  - Açık sprint YOK: clean ✅ sonraki işe geçilir

KULLANIM:
  python scripts/sprint_gate_check.py                # Tüm sprint status
  python scripts/sprint_gate_check.py --target 5     # Sprint 5'e geçmek için 1-4 kapalı mı?
  python scripts/sprint_gate_check.py --json         # CI/script entegrasyon için

populate_*.py scripts ilk satırda çağırır:
  ensure_sprint_gates_open(target_sprint='3')  # Sprint 3 için 0-1A-1B-2 kapalı mı?
"""
import sys
import urllib3
import io
import re
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    # FIX 2026-05-14: reconfigure (Py 3.11+) ile mevcut stream güncellenir.
    # io.TextIOWrapper kullanmak populate_cds_views.py gibi script'lerden
    # import edildiğinde sys.stdout.buffer'ı ikinci kez sarınca "closed file" verir.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))
from sap_adt_lib import set_explicit_working_dir, SAPADTClient


# ─── SPRINT TANIMLARI ─────────────────────────────────────────────────────────
# Her sprint: TADIR/DD03L query, expected count veya specific name list

SPRINT_DEFINITIONS = {
    '0.1': {
        'name': 'Message Class ZSD015 (54 mesaj)',
        'check_type': 'count_query',
        'sql': "SELECT msgnr FROM t100 WHERE arbgb = 'ZSD015'",
        'expected_min': 54,
    },
    '0.2': {
        'name': 'NR Object ZSD015_VN',
        'check_type': 'count_query',
        'sql': "SELECT object FROM tnro WHERE object = 'ZSD015_VN'",
        'expected_min': 1,
    },
    '0.3': {
        'name': 'NR Object ZSD015_DO',
        'check_type': 'count_query',
        'sql': "SELECT object FROM tnro WHERE object = 'ZSD015_DO'",
        'expected_min': 1,
    },
    '0.4': {
        'name': 'NR Object ZSD015_BN',
        'check_type': 'count_query',
        'sql': "SELECT object FROM tnro WHERE object = 'ZSD015_BN'",
        'expected_min': 1,
    },
    '1A': {
        'name': 'Custom Domain (ZSD015_D_*)',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'DOMA' AND obj_name LIKE 'ZSD015_D_%'",
        'expected_min': 34,
    },
    '1B': {
        'name': 'Custom DTEL (ZSD015_E_*)',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'DTEL' AND obj_name LIKE 'ZSD015_E_%'",
        'expected_min': 50,
    },
    '2A': {
        'name': 'Z Tablolar (ZSD015_T_*)',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'TABL' AND obj_name LIKE 'ZSD015_T_%'",
        'expected_min': 8,
    },
    '2B': {
        'name': 'Standart Tablo Append (LIPS+LIKP)',
        'check_type': 'multi_field',
        'fields': [
            ('LIPS', 'ZZ1_DISPATCH_ORDER_DLI'),
            ('LIPS', 'ZZ1_DISPATCH_ITEM_DLI'),
            ('LIKP', 'ZZ1_BOOKING_NUMBER_DLH'),
            ('LIKP', 'ZZ1_CONTAINER_NUMBER_DLH'),
        ],
        'expected_count': 4,
    },
    '2C': {
        'name': 'Lock Objects (EZSD015_LO_*)',
        'check_type': 'name_list',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'ENQU' AND obj_name LIKE 'EZSD015%'",
        'expected_names': ['EZSD015_LO_DORD', 'EZSD015_LO_BOOK'],
    },
    '3': {
        'name': 'Yaprak CDS (10 obje)',
        'check_type': 'name_list',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'DDLS' AND obj_name LIKE 'ZSD015_DDL_%'",
        'expected_names': [
            'ZSD015_DDL_VOYAGE_DESTINATION',
            'ZSD015_DDL_DISPATCH_SHIP_BAL',
            'ZSD015_DDL_ORDER_DISPATCHES',
            'ZSD015_DDL_DISPATCH_ORDER_BC',
            'ZSD015_DDL_STOCK_LIST',
            'ZSD015_DDL_CONTAINER_TYPES',
            'ZSD015_DDL_SHIPMENT_ITEMS',
            'ZSD015_DDL_SHIPMENT_LIST',
            'ZSD015_DDL_CONTAINER_CUSTOMER',
            'ZSD015_DDL_SHIPPING_TYPES',
            # ZSD015_DDL_ORDER_SA_SCHED ve ZSD015_DDL_ORDER_SCHED_LINES — 2026-05-14
            # iptal: ABAP CDS bu sistemde window function desteklemiyor; aggregate +
            # FIFO ABAP class içinde yapılacak. Standart I_SalesSchedgAgrmtSchedLine
            # + ZSD015_DDL_ORDER_DISPATCHES yeterli.
        ],
    },
    '4': {
        'name': 'Mid-tier CDS + ORDER_ITEMS UNION',
        'check_type': 'name_list',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'DDLS' AND obj_name LIKE 'ZSD015_DDL_%'",
        'expected_names': [
            'ZSD015_DDL_VOYAGE_HEADER',
            'ZSD015_DDL_CONTAINER_SHIPMENT',
            'ZSD015_DDL_ORDER_ITEMS',
            'ZSD015_DDL_ORDER_ITEMS_SO',
            'ZSD015_DDL_ORDER_ITEMS_SA',
            'ZSD015_DDL_BOOKING_CONTAINERS',
            'ZSD015_DDL_DISPATCH_ORDER_IT',
            'ZSD015_DDL_DISPATCH_SHIP_ITM',
        ],
    },
    '5': {
        'name': 'Composite CDS (7 obje)',
        'check_type': 'name_list',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'DDLS' AND obj_name LIKE 'ZSD015_DDL_%'",
        'expected_names': [
            'ZSD015_DDL_BOOKING_DOCCOUNT',
            'ZSD015_DDL_BOOKING_DOCCOUNT2',
            'ZSD015_DDL_DISPATCH_ORDER_ST',
            'ZSD015_DDL_BOOKING_HEADER',
            'ZSD015_DDL_DISPATCH_ORDER_HD',
            'ZSD015_DDL_DISPATCH_ORDER_BK',
            'ZSD015_DDL_CONTAINER_REPORT',
        ],
    },
    '6': {
        'name': 'Z Structures (13 obje)',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'TABL' AND obj_name LIKE 'ZSD015_S_%'",
        'expected_min': 13,
    },
    '7': {
        'name': 'Utility Class ZCL_SD015_GENERAL',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'CLAS' AND obj_name = 'ZCL_SD015_GENERAL'",
        'expected_min': 1,
    },
    '8': {
        'name': 'VOYAGE Program',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'PROG' AND obj_name = 'ZSD015_VOYAGE'",
        'expected_min': 1,
    },
    '9': {
        'name': 'BOOKING Program',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'PROG' AND obj_name = 'ZSD015_BOOKING'",
        'expected_min': 1,
    },
    '10': {
        'name': 'DISPATCH_ORDER Program',
        'check_type': 'count_query',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'PROG' AND obj_name = 'ZSD015_DISPATCH_ORDER'",
        'expected_min': 1,
    },
    '11': {
        'name': 'SHIPMENT + CONTAINER_REPORT Programs',
        'check_type': 'name_list',
        'sql': "SELECT obj_name FROM tadir WHERE pgmid = 'R3TR' AND object = 'PROG' AND obj_name LIKE 'ZSD015_%'",
        'expected_names': ['ZSD015_SHIPMENT', 'ZSD015_CONTAINER_REPORT'],
    },
}

# Sprint sırası (dependency)
SPRINT_ORDER = ['0.1', '0.2', '0.3', '0.4', '1A', '1B', '2A', '2B', '2C', '3', '4', '5', '6', '7', '8', '9', '10', '11']


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def _query_sap(client, sql: str) -> List[str]:
    """SAP'a SQL sorgu, dataPreview:data değerlerini döndür."""
    client._invalidate_csrf_cache()
    fr = client.session.get(
        client.url + '/sap/bc/adt/discovery',
        params={'sap-client':'100','sap-language':'TR'},
        headers={'X-CSRF-Token':'Fetch'}, verify=False, timeout=10
    )
    csrf = fr.headers.get('X-CSRF-Token','')
    sr = client.session.post(
        client.url + '/sap/bc/adt/datapreview/freestyle',
        params={'rowNumber':'1000'},
        headers={'X-CSRF-Token':csrf,
                 'Content-Type':'text/plain',
                 'Accept':'application/xml,application/vnd.sap.adt.datapreview.table.v1+xml'},
        data=sql.encode('utf-8'), verify=False, timeout=30
    )
    if sr.status_code != 200:
        return []
    return [m.group(1) for m in re.finditer(r'<dataPreview:data>([^<]+)</dataPreview:data>', sr.text)]


def check_sprint(client, sprint_id: str) -> Tuple[bool, str, Dict]:
    """Tek sprint için SAP query çalıştır, durum döndür.

    Returns:
        (is_closed, status_message, detail_dict)
    """
    defn = SPRINT_DEFINITIONS.get(sprint_id)
    if not defn:
        return (False, f'Bilinmeyen sprint: {sprint_id}', {})

    ct = defn['check_type']
    if ct == 'count_query':
        rows = _query_sap(client, defn['sql'])
        # totalRows'tan say
        actual = len(rows)
        expected = defn['expected_min']
        is_closed = actual >= expected
        return (is_closed,
                f'{actual}/{expected}',
                {'actual': actual, 'expected': expected, 'rows': rows[:10]})

    elif ct == 'name_list':
        rows = _query_sap(client, defn['sql'])
        existing = set(rows)
        expected = set(defn['expected_names'])
        missing = expected - existing
        is_closed = len(missing) == 0
        return (is_closed,
                f'{len(expected) - len(missing)}/{len(expected)}',
                {'expected': sorted(expected), 'missing': sorted(missing)})

    elif ct == 'multi_field':
        present = 0
        missing = []
        for table, field in defn['fields']:
            sql = f"SELECT fieldname FROM dd03l WHERE tabname = '{table}' AND fieldname = '{field}'"
            rows = _query_sap(client, sql)
            if rows:
                present += 1
            else:
                missing.append(f'{table}.{field}')
        is_closed = present == defn['expected_count']
        return (is_closed,
                f'{present}/{defn["expected_count"]}',
                {'missing': missing})

    return (False, 'Unknown check_type', {})


def gate_check_all(verbose: bool = True) -> Dict[str, dict]:
    """Tüm sprint'leri kontrol et, sonuç dict döndür."""
    client = SAPADTClient()
    results = {}
    if verbose:
        print(f'{"Sprint":8} {"Status":7} {"Count":12} {"İçerik":40}')
        print('-' * 75)
    for sprint_id in SPRINT_ORDER:
        defn = SPRINT_DEFINITIONS[sprint_id]
        is_closed, count_str, detail = check_sprint(client, sprint_id)
        results[sprint_id] = {
            'name': defn['name'],
            'closed': is_closed,
            'count': count_str,
            'detail': detail,
        }
        status_icon = '✅' if is_closed else '❌'
        if verbose:
            print(f'{sprint_id:8} {status_icon:7} {count_str:12} {defn["name"][:40]}')
            if not is_closed and 'missing' in detail and detail['missing']:
                miss_str = ', '.join(list(detail['missing'])[:3])
                more = '' if len(detail['missing']) <= 3 else f' (+{len(detail["missing"])-3})'
                print(f'         eksik: {miss_str}{more}')
    return results


def ensure_sprint_gates_open(target_sprint: str, allow_open_priors: bool = False,
                              raise_on_fail: bool = False) -> bool:
    """populate_*.py scripts'in ilk satırında çağrılır.

    Hedef sprint için önceki sprint'ler kapalı mı?

    Args:
        target_sprint: Hedef sprint ID ('1A', '3', '4' vb.)
        allow_open_priors: True ise sadece uyarı verir, False döner
        raise_on_fail: True ise SystemExit raise eder (CLI mode); False ise False döner

    Returns:
        True (sprint gate'leri OK), False (açık prior var ve raise_on_fail=False)
    """
    if target_sprint not in SPRINT_ORDER:
        raise ValueError(f'Bilinmeyen sprint: {target_sprint}')
    target_idx = SPRINT_ORDER.index(target_sprint)
    prior_sprints = SPRINT_ORDER[:target_idx]

    client = SAPADTClient()
    open_priors = []
    for sid in prior_sprints:
        is_closed, count_str, _ = check_sprint(client, sid)
        if not is_closed:
            open_priors.append((sid, count_str))

    if not open_priors:
        print(f'[OK] Sprint gate: Sprint {target_sprint} için tüm önceki sprint\'ler kapalı')
        return True

    msg = (
        f'\n[FAIL] Sprint Gate ihlali — Sprint {target_sprint}\'e geçmeden önce '
        f'önceki açık sprint\'ler kapatılmalı:\n'
    )
    for sid, count in open_priors:
        msg += f'  ❌ Sprint {sid}: {count} ({SPRINT_DEFINITIONS[sid]["name"]})\n'
    msg += (
        f'\nKural (LESSONS_LEARNED.md PATTERN #1):\n'
        f'  Sprint X kapanmadan Sprint X+1\'e geçiş YASAK.\n'
        f'  Önce yukarıdaki sprint\'leri kapat, sonra hedef sprint\'e geç.\n'
    )

    # Defensive print — stdout kapalıysa stderr'a yönelt
    def _safe_print(s):
        try:
            print(s)
        except (ValueError, OSError):
            sys.stderr.write(s + '\n')

    if allow_open_priors:
        _safe_print(msg)
        _safe_print('[WARN] allow_open_priors=True — gate ihlali kabul edildi, devam.')
        return False
    _safe_print(msg)
    if raise_on_fail:
        raise SystemExit(1)
    return False


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Sprint gate check — SAP TADIR vs plan')
    p.add_argument('--target', help='Hedef sprint ID (ör. 3, 4, 5)')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--allow-open', action='store_true',
                   help='Açık önceki sprint VARSA uyar ama exit 1 yapma')
    args = p.parse_args()

    if args.target:
        ok = ensure_sprint_gates_open(args.target,
                                       allow_open_priors=args.allow_open,
                                       raise_on_fail=False)
        return 0 if ok else 1

    # Tüm sprint'leri rapor
    results = gate_check_all(verbose=not args.json)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r['closed'] for r in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())

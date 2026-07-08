#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Create multiple SAP Z Tables via ADT REST in one batch.

Çözüm referansı: scripts/sap_adt_lib.py create_table() pattern'i + CSV-driven batch.

Pattern özet:
- Endpoint: POST /sap/bc/adt/ddic/tables
- Content-Type: application/vnd.sap.adt.tables.v2+xml
- Body: <blue:blueSource> root + <blue:source> ile DDL annotations + define table block
- adtcore:type="TABL/DT" (DİKKAT: "TABL/DS" → Structure olur)

Kullanım:
    python populate_tables.py \\
        --package ZSD001_CLC \\
        --transport <TRANSPORT> \\
        --csv <source_root>/ZSD001_CLC/table_fields.csv \\
        --cwd <PROJECT_ROOT>

CSV format (UTF-8, header'lı, satır başına bir alan):
    table_name,table_desc,delivery_class,data_maint,field_name,is_key,type,description

    Aynı table_name'li satırlar gruplandırılır → bir tablo olur.
    type sütunu: DTEL adı (`MANDT`, `KUNNR`, `ZSD001_E_VOYNO`) ya da built-in (`char10`, `numc5`).

Örnek satır:
    ZSD001_T_ORDER,Sefer Başlık,A,ALLOWED,MANDT,Y,MANDT,Client
    ZSD001_T_ORDER,Sefer Başlık,A,ALLOWED,ORDER_NO,Y,ZSD001_E_VOYNO,Sefer no
"""

import argparse
import csv
import sys
import io
import urllib3
from pathlib import Path
from collections import OrderedDict
from xml.sax.saxutils import escape as xml_escape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))
from sap_adt_lib import set_explicit_working_dir, SAPADTClient


def build_ddl(table_name: str, description: str, delivery_class: str,
              data_maint: str, fields: list, unit_refs: dict = None) -> str:
    """Build the DDL source for a table (Playbook §28).

    Kritik kurallar:
    - @AbapCatalog.enhancement.category : #NOT_EXTENSIBLE ZORUNLU
    - Key field'lara `not null`, non-key'lere yok
    - Quantity (QUAN) field'lar → @Semantics.quantity.unitOfMeasure : 'TABLE.UNIT_FIELD'
    - Currency (CURR) field'lar → @Semantics.amount.currencyCode : 'TABLE.WAERS_FIELD'
    - Unit field'lar (UNIT/MEINS) → @Semantics.unitOfMeasure : true marker
    - Currency code field'lar (CUKY/WAERS) → @Semantics.currencyCode : true marker

    Args:
        fields: list of dicts: {name, is_key, type, description}
        unit_refs: dict mapping quantity_or_amount_field_name → unit_or_currency_field_name
                   örn: {'volum': 'voleh', 'netwr': 'waers'}
                   Script field tipine göre doğru annotation seçer:
                     - CURR → @Semantics.amount.currencyCode + ref marker'da currencyCode
                     - diğer (QUAN/DEC) → @Semantics.quantity.unitOfMeasure + ref marker'da unitOfMeasure
    """
    table_name = table_name.lower()
    unit_refs = unit_refs or {}

    # Field type lookup (lowercase)
    type_by_name = {f['name'].lower(): f['type'].strip().lower() for f in fields}

    # Reverse map: which fields are unit/currency referenced (need marker annotation)
    # Decide marker type: if quantity_field is CURR → mark ref as currencyCode, else unitOfMeasure
    unit_field_markers = {}  # field_name → marker_type ('currency' or 'unit')
    for qty_field, unit_field in unit_refs.items():
        qty_type = type_by_name.get(qty_field, '').upper()
        if qty_type == 'CURR':
            unit_field_markers[unit_field] = 'currency'
        else:
            unit_field_markers[unit_field] = 'unit'

    field_lines = []
    for f in fields:
        name = f['name'].lower()
        ftype = f['type'].strip().lower()
        is_key = (f['is_key'].strip().upper() == 'Y')

        # Annotation: unit/currency code field marker
        if name in unit_field_markers:
            if unit_field_markers[name] == 'currency':
                field_lines.append('  @Semantics.currencyCode : true')
            else:
                field_lines.append('  @Semantics.unitOfMeasure : true')

        # Annotation: quantity → unit OR amount → currency referansı
        if name in unit_refs:
            ref_field = unit_refs[name]
            qty_type = type_by_name.get(name, '').upper()
            if qty_type == 'CURR':
                # Amount → Currency Code
                field_lines.append(f"  @Semantics.amount.currencyCode : '{table_name}.{ref_field}'")
            else:
                # Quantity → Unit of Measure
                field_lines.append(f"  @Semantics.quantity.unitOfMeasure : '{table_name}.{ref_field}'")

        # Field line — key has not null, non-key doesn't
        key_part = 'key ' if is_key else ''
        not_null_part = ' not null' if is_key else ''
        field_lines.append(f'  {key_part}{name} : {ftype}{not_null_part};')

    fields_src = '\n'.join(field_lines)

    return f'''@EndUserText.label : '{description}'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #{delivery_class.upper()}
@AbapCatalog.dataMaintenance : #{data_maint.upper()}
define table {table_name} {{
{fields_src}
}}'''


def build_xml(table_name: str, description: str, package: str,
              master_lang: str, ddl: str) -> str:
    """Build shell XML for POST — DDL gönderilmez (source/main PUT ayrıca yapılır)."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<blue:blueSource xmlns:blue="http://www.sap.com/wbobj/blue"
                 xmlns:adtcore="http://www.sap.com/adt/core"
                 adtcore:name="{table_name.upper()}"
                 adtcore:type="TABL/DT"
                 adtcore:description="{xml_escape(description)}"
                 adtcore:masterLanguage="{master_lang}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package.upper()}"/>
</blue:blueSource>'''


def table_exists(client: SAPADTClient, name: str) -> bool:
    r = client.session.get(
        client.url + f'/sap/bc/adt/ddic/tables/{name.lower()}',
        verify=False, timeout=10
    )
    return r.status_code == 200


def create_one(client: SAPADTClient, csrf: str, table_name: str,
               description: str, delivery_class: str, data_maint: str,
               fields: list, package: str, transport: str,
               master_lang: str = 'TR',
               unit_refs: dict = None,
               force_recreate: bool = False,
               dry_run: bool = False) -> bool:
    table_name = table_name.upper()
    exists = table_exists(client, table_name) if not dry_run else False

    if exists and not force_recreate:
        print(f'  [SKIP] {table_name} zaten var')
        return True

    ddl = build_ddl(table_name, description, delivery_class, data_maint, fields, unit_refs)
    xml_payload = build_xml(table_name, description, package, master_lang, ddl)

    if dry_run:
        print(f'\n--- DRY-RUN: {table_name} ({len(fields)} fields) ---')
        print(ddl)
        return True

    if force_recreate and exists:
        del_resp = client.session.delete(
            client.url + f'/sap/bc/adt/ddic/tables/{table_name.lower()}',
            params={'corrNr': transport},
            headers={'X-CSRF-Token': csrf, 'Accept': 'application/xml'},
            verify=False, timeout=30
        )
        if del_resp.status_code not in (200, 204):
            print(f'  [WARN] DELETE {table_name} failed: {del_resp.status_code}')

    # Step 1: POST shell create — body içinde DDL var ama bu sistemde SAP body DDL'i ignore ediyor.
    # SAP sadece metadata kullanır (name, package, desc, type) ve default DDL koyar.
    # GERÇEK DDL'i ayrıca /source/main'a PUT etmek gerek (Step 2).
    r = client.session.post(
        client.url + '/sap/bc/adt/ddic/tables',
        params={'corrNr': transport},
        headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'application/vnd.sap.adt.tables.v2+xml; charset=utf-8',
            'Accept': 'application/vnd.sap.adt.tables.v2+xml',
            'sap-client': '100',
            'sap-language': 'TR',
        },
        data=xml_payload.encode('utf-8'),
        verify=False, timeout=60
    )
    if r.status_code not in (200, 201):
        print(f'  [FAIL] {table_name} CREATE status={r.status_code}')
        print(f'         Body: {r.text[:600]}')
        return False

    # Step 2: Manual LOCK + PUT /source/main + UNLOCK
    # Library'nin set_object_source() If-Match gönderiyor (412 mismatch). Manual gidiyoruz.
    object_url = f'/sap/bc/adt/ddic/tables/{table_name.lower()}'

    # LOCK
    lr = client.session.post(
        client.url + object_url,
        params={'_action':'LOCK', 'accessMode':'MODIFY', 'corrNr':transport},
        headers={
            'X-CSRF-Token': csrf,
            'X-sap-adt-sessiontype': 'stateful',
            'Accept': 'application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result',
        },
        verify=False, timeout=15
    )
    import re as _re
    m = _re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lr.text)
    handle = m.group(1) if m else None
    if not handle:
        print(f'  [FAIL] {table_name} LOCK failed: {lr.status_code}')
        return False

    try:
        # PUT source/main — If-Match GÖNDERME!
        pr = client.session.put(
            client.url + object_url + '/source/main',
            params={'corrNr': transport, 'lockHandle': handle},
            headers={
                'X-CSRF-Token': csrf,
                'Content-Type': 'text/plain; charset=utf-8',
                'Accept': '*/*',
            },
            data=ddl.encode('utf-8'),
            verify=False, timeout=60
        )
        if pr.status_code in (200, 201, 204):
            print(f'  [OK]   {table_name}  ({len(fields)} fields, DDL pushed)')
            success = True
        else:
            print(f'  [FAIL] {table_name} PUT source/main status={pr.status_code}')
            print(f'         Body: {pr.text[:600]}')
            success = False
    finally:
        # UNLOCK garantili
        try:
            client.session.post(
                client.url + object_url,
                params={'_action':'UNLOCK', 'lockHandle':handle},
                headers={'X-CSRF-Token':csrf, 'X-sap-adt-sessiontype':'stateful'},
                verify=False, timeout=10
            )
        except Exception:
            pass

    return success


def main():
    parser = argparse.ArgumentParser(
        description='Batch-create SAP Z Tables from CSV'
    )
    parser.add_argument('--package', required=True)
    parser.add_argument('--transport', required=True)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--cwd')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force-recreate', action='store_true')
    parser.add_argument('--only', help='Comma-separated list of table names to process (rest skipped)')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f'[FAIL] CSV bulunamadı: {csv_path}')
        return 1

    only_set = None
    if args.only:
        only_set = {x.strip().upper() for x in args.only.split(',')}

    # Group rows by table_name
    tables = OrderedDict()
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            tname = r.get('table_name', '').strip().upper()
            if not tname:
                continue
            if only_set and tname not in only_set:
                continue
            if tname not in tables:
                tables[tname] = {
                    'description': r.get('table_desc', '').strip(),
                    'delivery_class': r.get('delivery_class', 'A').strip(),
                    'data_maint': r.get('data_maint', 'ALLOWED').strip(),
                    'fields': [],
                    'unit_refs': {},  # quantity_field → unit_field
                }
            fname = r.get('field_name', '').strip()
            unit_field = r.get('unit_field', '').strip()
            tables[tname]['fields'].append({
                'name': fname,
                'is_key': r.get('is_key', 'N').strip(),
                'type': r.get('type', '').strip(),
                'description': r.get('description', '').strip(),
            })
            if unit_field:
                tables[tname]['unit_refs'][fname.lower()] = unit_field.lower()

    print(f'[INFO] CSV → {len(tables)} tablo yüklendi')
    for tname, t in tables.items():
        print(f'  {tname:25} fields={len(t["fields"]):3}  desc={t["description"]}')

    if not tables:
        print('[FAIL] CSV boş veya filtre eşleşmedi')
        return 1

    client = SAPADTClient()

    csrf = ''
    if not args.dry_run:
        client._invalidate_csrf_cache()
        r = client.session.get(
            client.url + '/sap/bc/adt/discovery',
            params={'sap-client': '100', 'sap-language': 'TR'},
            headers={'X-CSRF-Token': 'Fetch'},
            verify=False
        )
        csrf = r.headers.get('X-CSRF-Token', '')
        if not csrf:
            print('[FAIL] CSRF token alınamadı')
            return 1
        print(f'\n[OK] CSRF: {csrf[:24]}...')

    ok = 0
    fail = 0
    print('\n=== Creating tables ===')
    for tname, t in tables.items():
        if create_one(client=client, csrf=csrf, table_name=tname,
                      description=t['description'],
                      delivery_class=t['delivery_class'],
                      data_maint=t['data_maint'],
                      fields=t['fields'],
                      package=args.package, transport=args.transport,
                      unit_refs=t.get('unit_refs', {}),
                      force_recreate=args.force_recreate, dry_run=args.dry_run):
            ok += 1
        else:
            fail += 1

    print(f'\n=== Sonuç: {ok} başarılı, {fail} hatalı ===')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())

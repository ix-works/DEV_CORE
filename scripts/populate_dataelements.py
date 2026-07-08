#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Create multiple SAP Z Data Elements (DTEL) via ADT REST in one batch.

Çözüm referansı: SAP_ADT_PLAYBOOK.md §26.2 (DTEL yaratma pattern'i)

KRİTİK NOTLAR (Playbook §26.5):
- Eski namespace `<dtel:wbobj xmlns:dtel="...wbobj/dictionary/dtel">` SILENT EMPTY döner.
  Mutlaka `<blue:wbobj xmlns:blue="...wbobj/dictionary/dtel">` + nested `<dtel:dataElement>` kullan.
- 3 attribute eksikse labels kayıt olmaz: `responsible`, `abapLanguageVersion`, `language`
- `sap-language=TR` hem query param hem header — ikisinde de gönder
- Update gerekirse: DELETE + tekrar CREATE (PUT bu sistemde broken — playbook'ta sabit)

Kullanım:
    python populate_dataelements.py \\
        --package ZSD001_CLC \\
        --transport <TRANSPORT> \\
        --responsible <SAP_USER> \\
        --csv <source_root>/ZSD001_CLC/dataelements.csv \\
        --cwd <PROJECT_ROOT>

CSV format (UTF-8, header'lı):
    name,type_kind,type_name,datatype,length,decimals,description,short,medium,long,heading

    type_kind = 'domain' veya 'BUILTIN'
    type_name = Domain adı (Z veya SAP standart) — BUILTIN için boş
    datatype  = CHAR / NUMC / DATS / INT2 / INT4 / DEC / QUAN
    length    = numeric (e.g. 10)
    decimals  = numeric (e.g. 0 ya da 3)

    Labels (TR):
      short    = max 10 char (kısa)
      medium   = max 20 char (orta)
      long     = max 40 char (uzun)
      heading  = max 55 char (heading)

Örnek satır:
    ZSD001_E_VOYNO,domain,ZSD001_D_VOYNO,NUMC,10,0,Sefer Numarası,Sefer,Sefer No,Sefer Numarası,Sefer Numarası
    ZSD001_E_DEPDATE,BUILTIN,,DATS,8,0,Planlanan Kalkış Tarihi,Kalkış,Planlı Kalkış,Planlanan Kalkış Tarihi,Planlanan Kalkış Tarihi
"""

import argparse
import csv
import sys
import io
import urllib3
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))
from sap_adt_lib import set_explicit_working_dir, SAPADTClient


def build_xml(name: str, description: str, package: str, responsible: str,
              type_kind: str, type_name: str,
              datatype: str, length: int, decimals: int,
              short: str, medium: str, long: str, heading: str) -> str:
    """Build DTEL XML — sabahki başarılı pattern (Playbook §26.2)."""
    name = name.upper()
    package = package.upper()
    length_str = f'{length:06d}'
    decimals_str = f'{decimals:06d}'

    # Validate label max lengths
    if len(short) > 10:
        print(f'  [WARN] {name}: short label "{short}" > 10 chars (will trim)')
        short = short[:10]
    if len(medium) > 20:
        print(f'  [WARN] {name}: medium label "{medium}" > 20 chars (will trim)')
        medium = medium[:20]
    if len(long) > 40:
        print(f'  [WARN] {name}: long label "{long}" > 40 chars (will trim)')
        long = long[:40]
    if len(heading) > 55:
        print(f'  [WARN] {name}: heading "{heading}" > 55 chars (will trim)')
        heading = heading[:55]

    # type_kind: 'domain' or 'BUILTIN' (case sensitive in SAP)
    if type_kind.lower() == 'builtin':
        type_kind_str = 'BUILTIN'
        type_name_str = ''
    else:
        type_kind_str = 'domain'
        type_name_str = type_name

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<blue:wbobj adtcore:responsible="{responsible}"
            adtcore:masterLanguage="TR"
            adtcore:abapLanguageVersion="standard"
            adtcore:name="{name}"
            adtcore:type="DTEL/DE"
            adtcore:description="{xml_escape(description)}"
            adtcore:language="TR"
            xmlns:blue="http://www.sap.com/wbobj/dictionary/dtel"
            xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package}"/>
  <dtel:dataElement xmlns:dtel="http://www.sap.com/adt/dictionary/dataelements">
    <dtel:typeKind>{type_kind_str}</dtel:typeKind>
    <dtel:typeName>{xml_escape(type_name_str)}</dtel:typeName>
    <dtel:dataType>{datatype}</dtel:dataType>
    <dtel:dataTypeLength>{length_str}</dtel:dataTypeLength>
    <dtel:dataTypeDecimals>{decimals_str}</dtel:dataTypeDecimals>
    <dtel:shortFieldLabel>{xml_escape(short)}</dtel:shortFieldLabel>
    <dtel:shortFieldLength>{len(short)}</dtel:shortFieldLength>
    <dtel:shortFieldMaxLength>10</dtel:shortFieldMaxLength>
    <dtel:mediumFieldLabel>{xml_escape(medium)}</dtel:mediumFieldLabel>
    <dtel:mediumFieldLength>{len(medium)}</dtel:mediumFieldLength>
    <dtel:mediumFieldMaxLength>20</dtel:mediumFieldMaxLength>
    <dtel:longFieldLabel>{xml_escape(long)}</dtel:longFieldLabel>
    <dtel:longFieldLength>{len(long)}</dtel:longFieldLength>
    <dtel:longFieldMaxLength>40</dtel:longFieldMaxLength>
    <dtel:headingFieldLabel>{xml_escape(heading)}</dtel:headingFieldLabel>
    <dtel:headingFieldLength>{len(heading)}</dtel:headingFieldLength>
    <dtel:headingFieldMaxLength>55</dtel:headingFieldMaxLength>
    <dtel:searchHelp/>
    <dtel:searchHelpParameter/>
    <dtel:setGetParameter/>
    <dtel:defaultComponentName/>
    <dtel:deactivateInputHistory>false</dtel:deactivateInputHistory>
    <dtel:changeDocument>false</dtel:changeDocument>
    <dtel:leftToRightDirection>false</dtel:leftToRightDirection>
    <dtel:deactivateBIDIFiltering>false</dtel:deactivateBIDIFiltering>
  </dtel:dataElement>
</blue:wbobj>'''


def dtel_exists(client: SAPADTClient, name: str) -> bool:
    r = client.session.get(
        client.url + f'/sap/bc/adt/ddic/dataelements/{name.lower()}',
        verify=False, timeout=10
    )
    return r.status_code == 200


def create_one(client: SAPADTClient, csrf: str, row: dict,
               package: str, responsible: str, transport: str,
               force_recreate: bool = False, dry_run: bool = False) -> bool:
    name = row['name'].upper()

    exists = dtel_exists(client, name) if not dry_run else False

    if exists and not force_recreate:
        print(f'  [SKIP] {name} zaten var')
        return True

    xml_payload = build_xml(
        name=name, description=row['description'],
        package=package, responsible=responsible,
        type_kind=row['type_kind'], type_name=row['type_name'],
        datatype=row['datatype'], length=row['length'], decimals=row['decimals'],
        short=row['short'], medium=row['medium'], long=row['long'], heading=row['heading'],
    )

    if dry_run:
        print(f'\n--- DRY-RUN XML: {name} ---')
        print(xml_payload[:1500])
        return True

    # DELETE first if force_recreate and exists
    if force_recreate and exists:
        del_resp = client.session.delete(
            client.url + f'/sap/bc/adt/ddic/dataelements/{name.lower()}',
            params={'corrNr': transport},
            headers={'X-CSRF-Token': csrf, 'Accept': 'application/xml'},
            verify=False, timeout=20
        )
        if del_resp.status_code not in (200, 204):
            print(f'  [WARN] DELETE {name} failed: {del_resp.status_code}')

    r = client.session.post(
        client.url + '/sap/bc/adt/ddic/dataelements',
        params={'corrNr': transport, 'sap-language': 'TR'},
        headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'application/vnd.sap.adt.dataelements.v2+xml; charset=utf-8',
            'Accept': 'application/vnd.sap.adt.dataelements.v2+xml',
            'sap-client': '100',
            'sap-language': 'TR',
        },
        data=xml_payload.encode('utf-8'),
        verify=False, timeout=30
    )
    if r.status_code in (200, 201):
        print(f'  [OK]   {name}  ({row["type_kind"]} → {row["type_name"] or row["datatype"]})')
        return True
    else:
        print(f'  [FAIL] {name} status={r.status_code}')
        print(f'         Body: {r.text[:400]}')
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Batch-create SAP Z Data Elements from CSV (Playbook §26.2 pattern)'
    )
    parser.add_argument('--package', required=True, help='Package (e.g. ZSD001_CLC)')
    parser.add_argument('--transport', required=True, help='Transport (e.g. <TRANSPORT>)')
    parser.add_argument('--responsible', default='<SAP_USER>')
    parser.add_argument('--csv', required=True, help='CSV file path')
    parser.add_argument('--cwd', help='Working dir with .conn_adt')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force-recreate', action='store_true',
                        help='DELETE existing DTELs and re-CREATE (Playbook §26.5 pattern)')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f'[FAIL] CSV bulunamadı: {csv_path}')
        return 1

    rows = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = r.get('name', '').strip()
            if not name:
                continue
            rows.append({
                'name': name,
                'type_kind': r.get('type_kind', 'domain').strip(),
                'type_name': r.get('type_name', '').strip(),
                'datatype': r.get('datatype', 'CHAR').strip().upper(),
                'length': int(r.get('length', '10')),
                'decimals': int(r.get('decimals', '0') or '0'),
                'description': r.get('description', '').strip(),
                'short': r.get('short', '').strip(),
                'medium': r.get('medium', '').strip(),
                'long': r.get('long', '').strip(),
                'heading': r.get('heading', '').strip(),
            })

    print(f'[INFO] CSV → {len(rows)} DTEL yüklendi')

    if not rows:
        print('[FAIL] CSV boş')
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
        print(f'[OK] CSRF: {csrf[:24]}...')

    ok = 0
    fail = 0
    for row in rows:
        if create_one(client=client, csrf=csrf, row=row,
                      package=args.package, responsible=args.responsible,
                      transport=args.transport, force_recreate=args.force_recreate,
                      dry_run=args.dry_run):
            ok += 1
        else:
            fail += 1

    print(f'\n=== Sonuç: {ok} başarılı, {fail} hatalı ===')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())

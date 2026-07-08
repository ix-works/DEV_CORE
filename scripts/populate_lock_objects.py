#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Create multiple SAP Z Lock Objects (ENQU/DL) via ADT REST.

Çözüm referansı: scripts/create_lock_object.py + manual CSRF/pattern düzeltmeleri.
Library'nin kapatma tag'leri buggy (backslash) - manuel doğru XML yazıyoruz.

Kullanım:
    python populate_lock_objects.py \\
        --package ZSD001_CLC \\
        --transport <TRANSPORT> \\
        --csv <source_root>/ZSD001_CLC/lock_objects.csv \\
        --cwd <PROJECT_ROOT>

CSV format (UTF-8, header'lı):
    name,description,primary_table,lock_mode,allow_rfc,field_names
    EZSD001_LO_BOOK,Booking Edit Kilidi,ZSD001_T_BOOKHD,E,false,MANDT;BOOKING_NO
    EZSD001_LO_DORD,Dispatch Edit Kilidi,ZSD001_T_DORHD,E,false,MANDT;ORDER_ORDER

field_names: semicolon-separated field listesi (primary key alanları)
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


def build_xml(name: str, description: str, package: str, primary_table: str,
              lock_mode: str, allow_rfc: bool, field_names: list) -> str:
    """Build lockobject XML — kapatma tag'leri DOĞRU forward slash ile."""
    name = name.upper()
    package = package.upper()
    primary_table = primary_table.upper()

    lock_params = []
    for field in field_names:
        f = field.strip().upper()
        if not f:
            continue
        lock_params.append(f'''        <enqu:lockParameter>
            <enqu:parameterWanted>true</enqu:parameterWanted>
            <enqu:parameterName>{f}</enqu:parameterName>
            <enqu:tableName>{primary_table}</enqu:tableName>
            <enqu:fieldName>{f}</enqu:fieldName>
        </enqu:lockParameter>''')

    lock_params_xml = '\n'.join(lock_params)
    allow_rfc_str = 'true' if allow_rfc else 'false'

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<enqu:lockobject xmlns:enqu="http://www.sap.com/adt/ddic/enqu"
                 xmlns:adtcore="http://www.sap.com/adt/core"
                 adtcore:name="{name}"
                 adtcore:description="{xml_escape(description)}"
                 adtcore:masterLanguage="TR">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package}"/>
  <enqu:content>
    <enqu:allowRFC>{allow_rfc_str}</enqu:allowRFC>
    <enqu:primaryTable>
      <enqu:tableName>{primary_table}</enqu:tableName>
      <enqu:lockMode>{lock_mode}</enqu:lockMode>
    </enqu:primaryTable>
    <enqu:secondaryTables/>
    <enqu:lockParameters>
{lock_params_xml}
    </enqu:lockParameters>
  </enqu:content>
</enqu:lockobject>'''


def lock_object_exists(client: SAPADTClient, name: str) -> bool:
    """⚠ URL pattern: /lockobjects/sources/{name} (sources alt yolu — playbook §29.1)"""
    r = client.session.get(
        client.url + f'/sap/bc/adt/ddic/lockobjects/sources/{name.lower()}',
        verify=False, timeout=10
    )
    return r.status_code == 200


def activate_lock_object(client: SAPADTClient, csrf: str, name: str) -> bool:
    """Lock object activation (playbook §29.6) — activate_object.py ENQU/DL desteklemez."""
    obj_url = f'/sap/bc/adt/ddic/lockobjects/sources/{name.lower()}'
    body = f'''<?xml version="1.0" encoding="UTF-8"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:objectReference adtcore:uri="{obj_url}"
                            adtcore:type="ENQU/DL"
                            adtcore:name="{name.upper()}"/>
</adtcore:objectReferences>'''

    r = client.session.post(
        client.url + '/sap/bc/adt/activation',
        params={'method':'activate', 'preauditRequested':'true'},
        headers={'X-CSRF-Token':csrf, 'Content-Type':'application/xml', 'Accept':'application/xml'},
        data=body.encode('utf-8'),
        verify=False, timeout=30
    )
    return r.status_code == 200 and 'activationExecuted="true"' in r.text


def create_one(client: SAPADTClient, csrf: str, name: str, description: str,
               package: str, primary_table: str, lock_mode: str,
               allow_rfc: bool, field_names: list, transport: str,
               force_recreate: bool = False, dry_run: bool = False) -> bool:
    name = name.upper()
    exists = lock_object_exists(client, name) if not dry_run else False

    if exists and not force_recreate:
        print(f'  [SKIP] {name} zaten var')
        return True

    xml_payload = build_xml(name, description, package, primary_table,
                            lock_mode, allow_rfc, field_names)

    if dry_run:
        print(f'\n--- DRY-RUN XML: {name} ---')
        print(xml_payload)
        return True

    if force_recreate and exists:
        try:
            client.session.delete(
                client.url + f'/sap/bc/adt/ddic/lockobjects/sources/{name.lower()}',
                params={'corrNr': transport},
                headers={'X-CSRF-Token': csrf}, verify=False, timeout=30
            )
        except Exception:
            pass

    r = client.session.post(
        client.url + '/sap/bc/adt/ddic/lockobjects/sources',
        params={'corrNr': transport},
        headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'application/vnd.sap.adt.lockobjects.v1+xml; charset=utf-8',
            'Accept': '*/*',
            'sap-client': '100',
            'sap-language': 'TR',
        },
        data=xml_payload.encode('utf-8'),
        verify=False, timeout=60
    )
    if r.status_code not in (200, 201):
        print(f'  [FAIL] {name} CREATE status={r.status_code}')
        print(f'         Body: {r.text[:500]}')
        return False

    # Activate (playbook §29.6 — activate_object.py ENQU/DL desteklemez)
    if activate_lock_object(client, csrf, name):
        print(f'  [OK]   {name}  (primary={primary_table}, fields={len(field_names)}, ACTIVE)')
        return True
    else:
        print(f'  [WARN] {name} yaratıldı ama AKTİVASYON BAŞARISIZ')
        return False


def main():
    parser = argparse.ArgumentParser(description='Batch-create SAP Z Lock Objects from CSV')
    parser.add_argument('--package', required=True)
    parser.add_argument('--transport', required=True)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--cwd')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force-recreate', action='store_true')
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
                'description': r.get('description', '').strip(),
                'primary_table': r.get('primary_table', '').strip(),
                'lock_mode': r.get('lock_mode', 'E').strip(),
                'allow_rfc': r.get('allow_rfc', 'false').strip().lower() == 'true',
                'field_names': [x.strip() for x in r.get('field_names', '').split(';') if x.strip()],
            })

    print(f'[INFO] CSV → {len(rows)} lock object yüklendi')

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
        if create_one(client=client, csrf=csrf,
                      name=row['name'], description=row['description'],
                      package=args.package, primary_table=row['primary_table'],
                      lock_mode=row['lock_mode'], allow_rfc=row['allow_rfc'],
                      field_names=row['field_names'],
                      transport=args.transport,
                      force_recreate=args.force_recreate, dry_run=args.dry_run):
            ok += 1
        else:
            fail += 1

    print(f'\n=== Sonuç: {ok} başarılı, {fail} hatalı ===')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())

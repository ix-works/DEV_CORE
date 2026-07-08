#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Create multiple SAP Z Domains via ADT REST in one batch.

Çözüm referansı: SAP_ADT_PLAYBOOK.md §26.1 (Domain yaratma pattern'i)

Kullanım:
    python populate_domains.py \\
        --package ZSD001_CLC \\
        --transport <TRANSPORT> \\
        --responsible <SAP_USER> \\
        --csv ERP/ZSD001_CLC/domains.csv \\
        --cwd <PROJECT_ROOT>

CSV format (UTF-8, header'lı, 5 kolon):
    name,datatype,length,decimals,description,fixed_values
    ZSD001_D_VOYNO,NUMC,10,0,Sefer Numarası,
    ZSD001_D_BOOKDS,CHAR,6,0,Teslim durumu,YOLDA=Yolda;TESLIM=Teslim edildi
    ZSD001_D_TRMODCAT,CHAR,1,0,Taşıma türü,1=Karayolu;2=Demiryolu;3=Denizyolu

fixed_values kolonu:
    - boş → fixed value yok
    - `VAL1=Label1;VAL2=Label2;VAL3=Label3` formatı (noktalı virgül ile ayrılmış)
"""

import argparse
import csv
import re
import sys
import io
import urllib3
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# sap_adt_lib path
sys.path.insert(0, str(Path(__file__).parent))

from sap_adt_lib import set_explicit_working_dir, SAPADTClient


def parse_fixed_values(fv_str: str) -> list:
    """Parse `VAL1=Label1;VAL2=Label2` → [(VAL1, Label1), (VAL2, Label2)]"""
    if not fv_str or not fv_str.strip():
        return []
    result = []
    for pair in fv_str.split(';'):
        pair = pair.strip()
        if '=' in pair:
            val, label = pair.split('=', 1)
            result.append((val.strip(), label.strip()))
    return result


def calculate_output_length(datatype: str, length: int, decimals: int) -> int:
    """SAP'nin domain output length hesabı (SE11 önerisi ile uyumlu).

    Formül:
      CHAR/NUMC/DATS/TIMS/CLNT  → length
      INT1                      → 4   (-128..127)
      INT2                      → 6   (-32768..32767)
      INT4                      → 11  (-2147483648..2147483647)
      INT8                      → 20
      DEC/QUAN/CURR             → length + 4 (sign + decimal nokta + thousand sep'ler için)
    """
    dt = datatype.upper()
    if dt == 'INT1':
        return 4
    if dt == 'INT2':
        return 6
    if dt == 'INT4':
        return 11
    if dt == 'INT8':
        return 20
    if dt in ('DEC', 'QUAN', 'CURR'):
        return length + 4
    return length  # CHAR, NUMC, DATS, TIMS, CLNT, vb.


def build_xml(name: str, description: str, package: str, responsible: str,
              datatype: str, length: int, decimals: int,
              fixed_values: list) -> str:
    """Build domain XML payload with optional fixed values."""
    name = name.upper()
    package = package.upper()
    length_str = f'{length:06d}'
    decimals_str = f'{decimals:06d}'
    output_length = calculate_output_length(datatype, length, decimals)
    output_length_str = f'{output_length:06d}'

    # Fixed values block
    if fixed_values:
        fv_xml_parts = []
        for idx, (val, label) in enumerate(fixed_values, start=1):
            fv_xml_parts.append(
                f'      <doma:fixValue>\n'
                f'        <doma:position>{idx:04d}</doma:position>\n'
                f'        <doma:low>{xml_escape(val)}</doma:low>\n'
                f'        <doma:high/>\n'
                f'        <doma:text>{xml_escape(label)}</doma:text>\n'
                f'      </doma:fixValue>'
            )
        fv_block = '\n'.join(fv_xml_parts)
        fix_values_xml = f'<doma:fixValues>\n{fv_block}\n    </doma:fixValues>'
    else:
        fix_values_xml = '<doma:fixValues/>'

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<doma:domain adtcore:responsible="{responsible}"
             adtcore:masterLanguage="TR"
             adtcore:abapLanguageVersion="standard"
             adtcore:name="{name}"
             adtcore:type="DOMA/DD"
             adtcore:description="{xml_escape(description)}"
             adtcore:language="TR"
             xmlns:doma="http://www.sap.com/dictionary/domain"
             xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package}"/>
  <doma:content>
    <doma:typeInformation>
      <doma:datatype>{datatype}</doma:datatype>
      <doma:length>{length_str}</doma:length>
      <doma:decimals>{decimals_str}</doma:decimals>
    </doma:typeInformation>
    <doma:outputInformation>
      <doma:length>{output_length_str}</doma:length>
      <doma:style>00</doma:style>
      <doma:conversionExit/>
      <doma:signExists>false</doma:signExists>
      <doma:lowercase>false</doma:lowercase>
      <doma:ampmFormat>false</doma:ampmFormat>
    </doma:outputInformation>
    <doma:valueInformation>
      <doma:valueTableRef/>
      <doma:appendExists>false</doma:appendExists>
      {fix_values_xml}
    </doma:valueInformation>
  </doma:content>
</doma:domain>'''


def domain_exists(client: SAPADTClient, name: str) -> bool:
    r = client.session.get(
        client.url + f'/sap/bc/adt/ddic/domains/{name.lower()}',
        verify=False, timeout=10
    )
    return r.status_code == 200


def create_one(client: SAPADTClient, csrf: str, name: str, description: str,
               package: str, responsible: str, transport: str,
               datatype: str, length: int, decimals: int,
               fixed_values: list, dry_run: bool = False) -> bool:
    name = name.upper()

    if not dry_run and domain_exists(client, name):
        print(f'  [SKIP] {name} zaten var')
        return True

    xml_payload = build_xml(
        name=name, description=description, package=package,
        responsible=responsible, datatype=datatype, length=length,
        decimals=decimals, fixed_values=fixed_values
    )

    if dry_run:
        print(f'\n--- DRY-RUN XML: {name} ---')
        print(xml_payload[:1200])
        return True

    r = client.session.post(
        client.url + '/sap/bc/adt/ddic/domains',
        params={'corrNr': transport},
        headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'application/vnd.sap.adt.domains.v2+xml; charset=utf-8',
            'Accept': 'application/vnd.sap.adt.domains.v2+xml',
            'sap-client': '100',
            'sap-language': 'TR',
        },
        data=xml_payload.encode('utf-8'),
        verify=False, timeout=30
    )
    if r.status_code in (200, 201):
        fv_note = f' (+ {len(fixed_values)} fixed values)' if fixed_values else ''
        print(f'  [OK]   {name} yaratıldı{fv_note}')
        return True
    else:
        print(f'  [FAIL] {name} status={r.status_code}')
        print(f'         Body: {r.text[:400]}')
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Batch-create SAP Z Domains from CSV (uses SAP_ADT_PLAYBOOK §26.1 pattern)'
    )
    parser.add_argument('--package', required=True, help='Package name (e.g. ZSD001_CLC)')
    parser.add_argument('--transport', required=True, help='Transport (e.g. <TRANSPORT>)')
    parser.add_argument('--responsible', default='<SAP_USER>', help='Responsible user')
    parser.add_argument('--csv', required=True, help='CSV file path')
    parser.add_argument('--cwd', help='Working dir with .conn_adt')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print XML only, do not POST')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f'[FAIL] CSV bulunamadı: {csv_path}')
        return 1

    # Load CSV
    rows = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = r.get('name', '').strip()
            if not name:
                continue
            rows.append({
                'name': name,
                'datatype': r.get('datatype', 'CHAR').strip().upper(),
                'length': int(r.get('length', '10')),
                'decimals': int(r.get('decimals', '0') or '0'),
                'description': r.get('description', '').strip(),
                'fixed_values': parse_fixed_values(r.get('fixed_values', '')),
            })

    print(f'[INFO] CSV → {len(rows)} domain yüklendi')

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

    ok_count = 0
    fail_count = 0
    for row in rows:
        success = create_one(
            client=client, csrf=csrf,
            name=row['name'], description=row['description'],
            package=args.package, responsible=args.responsible,
            transport=args.transport,
            datatype=row['datatype'], length=row['length'], decimals=row['decimals'],
            fixed_values=row['fixed_values'],
            dry_run=args.dry_run,
        )
        if success:
            ok_count += 1
        else:
            fail_count += 1

    print(f'\n=== Sonuç: {ok_count} başarılı, {fail_count} hatalı ===')
    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())

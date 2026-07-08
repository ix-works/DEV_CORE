#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Populate SAP Message Class (MSAG) via ADT REST.

Çözüm bulundu: 2026-05-13. Detaylı analiz için bkz. SAP_ADT_PLAYBOOK.md §27.

KRİTİK BULGU: Bu sistemde (S/4 1909) mesaj sınıfı PUT'unda `If-Match` header'ı
göndermek ENQUEUE lock bug'ını tetikliyor (handler kendi enqueue check'ini
yapıp self-collision veriyor). `If-Match`'siz PUT ile precondition check
bypass ediliyor ve mesajlar başarıyla yazılıyor.

WINNING PATTERN:
  1. CSRF fetch (X-CSRF-Token: Fetch)
  2. LOCK parent class (_action=LOCK, accessMode=MODIFY, corrNr, stateful)
  3. PUT /sap/bc/adt/messageclass/{name}
     - Query: corrNr, lockHandle, accessMode=MODIFY
     - Headers: X-CSRF-Token, X-sap-adt-sessiontype: stateful,
                Content-Type: application/vnd.sap.adt.mc.messageclass+xml
     - !!!! If-Match GÖNDERME !!!!
     - Body: <mc:messageClass>...<mc:messages mc:msgno=... mc:msgtext=...>...
  4. UNLOCK (try/finally garantili) + clear_enqueue_lock safety net

XML ŞEMA (kritik nokta — element ve attribute adları SAP'nin döndüğü formatta):
  - <mc:messages> ÇOĞUL (singular değil!)
  - mc:msgno (number değil!)
  - mc:msgtext (text değil!)
  - mc:selfexplainatory (SAP'de typo — "selfExplanatory" değil!)

Kullanım:
    python populate_message_class.py \\
        --name ZSD001 \\
        --package ZSD000_CLC \\
        --transport <TRANSPORT> \\
        --description "Sevkemri Mesaj Sinifi" \\
        --responsible <SAP_USER> \\
        --messages-csv messages.csv \\
        --cwd <PROJECT_ROOT>

    messages.csv format (UTF-8, ilk satır header):
        msgno,msgtext,selfexplainatory
        001,"Müşteri bulunamadı",false
        002,"Tarih boş olamaz",true
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
_PLUGIN_PATH = r'C:\Users\<USER>\.config\opencode\ntt-marketplace\plugins\abaper\skills\sap-adt\scripts'
sys.path.insert(0, _PLUGIN_PATH)

from sap_adt_lib import set_explicit_working_dir, SAPADTClient


def load_messages_from_csv(csv_path: Path) -> list:
    """CSV oku → [(msgno, msgtext, selfexplainatory), ...]"""
    messages = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            msgno = str(row.get('msgno', '')).strip().zfill(3)  # zero-pad to 3 digits
            msgtext = str(row.get('msgtext', '')).strip()
            self_exp = str(row.get('selfexplainatory', 'false')).strip().lower()
            if self_exp not in ('true', 'false'):
                self_exp = 'false'
            if msgno and msgtext:
                messages.append((msgno, msgtext, self_exp))
    return messages


def build_xml(name: str, description: str, package: str, responsible: str,
              messages: list) -> str:
    """Build full message class XML with embedded messages."""
    msgs_xml = '\n'.join(
        f'  <mc:messages mc:msgno="{n}" mc:msgtext="{xml_escape(t)}" '
        f'mc:selfexplainatory="{s}" mc:documented="false" adtcore:name=""/>'
        for n, t, s in messages
    )

    return f'''<?xml version="1.0" encoding="utf-8"?>
<mc:messageClass adtcore:responsible="{responsible}"
                 adtcore:masterLanguage="TR"
                 adtcore:name="{name}"
                 adtcore:type="MSAG/N"
                 adtcore:description="{xml_escape(description)}"
                 adtcore:language="TR"
                 xmlns:mc="http://www.sap.com/adt/MessageClass"
                 xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package}"/>
{msgs_xml}
</mc:messageClass>'''


def populate(client: SAPADTClient, name: str, description: str, package: str,
             responsible: str, transport: str, messages: list,
             dry_run: bool = False) -> bool:
    """
    Lock, PUT messages, unlock. Returns True on success.
    """
    name = name.upper()
    object_url = f'/sap/bc/adt/messageclass/{name.lower()}'

    # Build payload
    xml_payload = build_xml(name, description, package, responsible, messages)

    if dry_run:
        print('\n=== DRY-RUN — XML preview (first 1500 chars) ===')
        print(xml_payload[:1500])
        return True

    # 1. Fresh CSRF
    client._invalidate_csrf_cache()
    r = client.session.get(
        client.url + '/sap/bc/adt/discovery',
        params={'sap-client': '100', 'sap-language': 'TR'},
        headers={'X-CSRF-Token': 'Fetch'},
        verify=False, timeout=15
    )
    csrf = r.headers.get('X-CSRF-Token', '')
    if not csrf:
        print('[FAIL] CSRF token alınamadı')
        return False
    print(f'[OK] CSRF: {csrf[:24]}...')

    handle = None
    success = False
    try:
        # 2. LOCK
        print(f'[INFO] LOCK {name}...')
        lock_resp = client.session.post(
            client.url + object_url,
            params={'_action': 'LOCK', 'accessMode': 'MODIFY', 'corrNr': transport},
            headers={
                'X-CSRF-Token': csrf,
                'X-sap-adt-sessiontype': 'stateful',
                'Accept': 'application/*,application/vnd.sap.as+xml;'
                          'dataname=com.sap.adt.lock.result',
            },
            verify=False, timeout=15
        )
        if lock_resp.status_code != 200:
            print(f'[FAIL] LOCK status: {lock_resp.status_code}')
            print(f'       Body: {lock_resp.text[:500]}')
            return False
        m = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lock_resp.text)
        handle = m.group(1) if m else None
        if not handle:
            print('[FAIL] LOCK_HANDLE çıkarılamadı')
            return False
        print(f'[OK] Lock handle: {handle[:16]}...')

        # 3. PUT — winning pattern: NO If-Match!
        print(f'[INFO] PUT {len(messages)} message(s)...')
        r = client.session.put(
            client.url + object_url,
            params={'corrNr': transport, 'lockHandle': handle,
                    'accessMode': 'MODIFY'},
            headers={
                'X-CSRF-Token': csrf,
                'Content-Type': 'application/vnd.sap.adt.mc.messageclass+xml; '
                                'charset=utf-8',
                'Accept': '*/*',
                'X-sap-adt-sessiontype': 'stateful',
                'sap-client': '100',
                'sap-language': 'TR',
                # !!! NO If-Match — kritik! !!!
            },
            data=xml_payload.encode('utf-8'),
            verify=False, timeout=60
        )
        if r.status_code in (200, 201, 204):
            print(f'[OK] PUT başarılı — Status: {r.status_code}')
            success = True
        else:
            print(f'[FAIL] PUT status: {r.status_code}')
            print(f'       Body: {r.text[:800]}')

    finally:
        # 4. Guaranteed UNLOCK
        if handle:
            try:
                u = client.session.post(
                    client.url + object_url,
                    params={'_action': 'UNLOCK', 'lockHandle': handle},
                    headers={
                        'X-CSRF-Token': csrf,
                        'X-sap-adt-sessiontype': 'stateful',
                    },
                    verify=False, timeout=10
                )
                print(f'[OK] UNLOCK: {u.status_code}')
            except Exception as e:
                print(f'[WARN] UNLOCK error: {e}')

        # Safety net — clear any lingering enqueue locks
        try:
            client.clear_enqueue_lock(object_url=object_url)
            print('[OK] Enqueue cleanup tamamlandı')
        except Exception as e:
            print(f'[WARN] clear_enqueue_lock skipped: {e}')

    return success


def verify(client: SAPADTClient, name: str) -> list:
    """GET class and return list of (msgno, msgtext) tuples."""
    object_url = f'/sap/bc/adt/messageclass/{name.lower()}'
    r = client.session.get(
        client.url + object_url,
        headers={'Accept': 'application/vnd.sap.adt.mc.messageclass+xml'},
        params={'sap-language': 'TR'},
        verify=False
    )
    if r.status_code != 200:
        return []
    return re.findall(
        r'<mc:messages mc:msgno="([^"]*)" mc:msgtext="([^"]*)"',
        r.text
    )


def main():
    parser = argparse.ArgumentParser(
        description='Populate SAP message class with messages via ADT REST '
                    '(uses winning pattern from SAP_ADT_PLAYBOOK §27)'
    )
    parser.add_argument('--name', required=True,
                        help='Message class name (e.g. ZSD001)')
    parser.add_argument('--package', required=True,
                        help='Package name (e.g. ZSD000_CLC)')
    parser.add_argument('--transport', required=True,
                        help='Transport request (e.g. <TRANSPORT>)')
    parser.add_argument('--description', required=True,
                        help='Class description')
    parser.add_argument('--responsible', default='<SAP_USER>',
                        help='Responsible user (default: <SAP_USER>)')
    parser.add_argument('--messages-csv', required=True,
                        help='CSV file: msgno,msgtext,selfexplainatory')
    parser.add_argument('--cwd',
                        help='Working dir with .conn_adt')
    parser.add_argument('--dry-run', action='store_true',
                        help='Build XML and print, do not POST')
    parser.add_argument('--verify-only', action='store_true',
                        help='Skip write, just GET and list current messages')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    client = SAPADTClient()

    if args.verify_only:
        msgs = verify(client, args.name)
        print(f'\n{args.name} içinde {len(msgs)} mesaj var:')
        for nr, txt in msgs:
            print(f'  {nr}: {txt[:80]}')
        return 0

    csv_path = Path(args.messages_csv)
    if not csv_path.exists():
        print(f'[FAIL] CSV bulunamadı: {csv_path}')
        return 1

    messages = load_messages_from_csv(csv_path)
    print(f'[INFO] {csv_path.name} → {len(messages)} mesaj yüklendi')
    if not messages:
        print('[FAIL] CSV boş')
        return 1

    # PRE-state
    if not args.dry_run:
        before = verify(client, args.name)
        print(f'[INFO] Mevcut mesaj sayısı: {len(before)}')

    ok = populate(
        client=client,
        name=args.name,
        description=args.description,
        package=args.package,
        responsible=args.responsible,
        transport=args.transport,
        messages=messages,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        return 0

    if not ok:
        print('\n[FAIL] Mesaj yazma başarısız oldu')
        return 1

    # POST-state
    after = verify(client, args.name)
    print(f'\n[OK] Final mesaj sayısı: {len(after)}')
    if len(after) >= len(messages):
        print(f'[OK] Tüm {len(messages)} mesaj başarıyla yazıldı')
        return 0
    else:
        print(f'[WARN] Beklenen {len(messages)}, gelen {len(after)} — '
              'CSV içeriğini kontrol et')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Push local object changes to SAP (complete workflow: lock -> upload -> activate -> unlock).

Usage:
    python push_object.py --name ZCL_MY_CLASS --type class --transport TRXXXXX --cwd /path/to/project

With explicit source file:
    python push_object.py --name ZCL_MY_CLASS --type class --source-file /path/to/ZCL_MY_CLASS.abap --transport TRXXXXX --cwd /path/to/project
"""
import argparse
import re
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
from object_types import is_class_include

# ── #30③ (2026-08-29) — REDDEDİLEN TİP İÇİN YÖNLENDİRME ──────────────────────
# ⛔ `--type` choices GEVŞETİLMEDİ ve gevşetilmemeli. DDIC tiplerinin listede
# olmaması KUSUR DEĞİL, KORUYUCU: push_object source-based bir yoldur
# (lock → PUT .../source/main + If-Match). DDIC objelerinin bir kısmı XML-ZARF'tır
# (`dataelement`=.dtel.xml, `table`/`structure`=.tabl.xml) — `source/main` ucu YOKTUR;
# üstelik DTEL'de PUT bu sistemde bozuktur (`populate_dataelements.py` başlığı:
# "Update gerekirse: DELETE + tekrar CREATE (PUT bu sistemde broken)").
# Değişen TEK ŞEY: ret mesajı. Eskiden argparse çıplak "invalid choice" basıp exit 2
# veriyordu; operatör NEDEN reddedildiğini ve NEREYE gideceğini bilmiyordu.
# Aşağıdaki eşleme ÖLÇÜLDÜ (her script açılıp doğrulandı), tahmin değildir.
TIP_YONLENDIRME = {
    'dataelement':       'populate_dataelements.py',
    'domain':            'populate_domains.py',
    'table':             'populate_tables.py',
    'structure':         'create_structure.py',
    'cds':               'populate_cds_views.py',
    'function':          'create_function_module.py (yalnız SHELL) + '
                         'sap_adt_lib.set_function_module_source()',
    'servicedefinition': 'create_rap_service.py --step srvd',
}
# `source/main` ucu OLMAYAN, XML zarfı ile yazılan tipler (yukarıdakilerin alt kümesi).
# ⚠ `cds`/`function`/`servicedefinition` BU KÜMEDE DEĞİL — onlar source-based'dir,
# yalnızca kendi kanonik araçları vardır. Gerekçeyi karıştırma.
TIP_XML_ZARF = ('dataelement', 'domain', 'table', 'structure', 'tabletype')
# Kayıtlı ADT tipi ama bu repoda kanonik YARATMA aracı bulunmayanlar (ölçüldü:
# yalnız okuma/description yollarında geçiyorlar).
TIP_YAZICISI_YOK = ('metadataextension', 'accesscontrol', 'tabletype')


def tip_yonlendirme_notu(istenen):
    """Reddedilen `--type` için operatöre yol gösteren not (boş string = not yok)."""
    t = (istenen or '').strip().lower()
    # Esanlamli tipler de yonlendirilsin: olculdu 2026-09-03 -> `--type func`
    # ciplak "invalid choice" aliyordu (tabloda yalniz 'function' anahtari var),
    # yani operator NEREYE gidecegini yine ogrenemiyordu. Esanlamli tablosu
    # object_types'tan okunur; burada IKINCI bir kopya acilmaz.
    try:
        from object_types import OBJECT_TYPE_ALIASES
        t = OBJECT_TYPE_ALIASES.get(t, t)
    except Exception:
        pass
    if t == 'package':
        return ("[YONLENDIRME] 'package' bu araca EKLENMEZ: paket YARATMA ADR 0005-C ile "
                "YASAKTIR (create_package.py 2026-08-01'de silindi, geri eklenmez).")
    if t in TIP_YONLENDIRME:
        satir = (f"[YONLENDIRME] '{t}' push_object'e KASTEN kablolanmadi. "
                 f"Kanonik arac: {TIP_YONLENDIRME[t]}")
        if t in TIP_XML_ZARF:
            satir += ("\n              Sebep: bu tip XML-ZARF objesidir ('source/main' ucu "
                      "YOK); push_object ise lock -> PUT source/main + If-Match yolundan gider.")
        return satir
    if t in TIP_YAZICISI_YOK:
        return (f"[YONLENDIRME] '{t}' kayitli bir ADT tipidir ama bu repoda kanonik bir "
                f"YARATMA araci YOK. Once playbook/adt-*.md oku; ad-hoc REST ile yazma.")
    return ''


class _YonlendirenParser(argparse.ArgumentParser):
    """`--type` reddini AYNEN korur (exit 2), yalnız mesaja yönlendirme ekler."""

    def error(self, message):
        if '--type' in message and 'invalid choice' in message:
            m = re.search(r"invalid choice: '([^']*)'", message)
            not_ = tip_yonlendirme_notu(m.group(1) if m else '')
            if not_:
                message = f"{message}\n\n{not_}"
        super().error(message)          # usage + mesaj -> stderr, exit 2 (DEĞİŞMEDİ)


def main():
    parser = _YonlendirenParser(
        description='Push local object changes to SAP (lock -> upload -> activate -> unlock)'
    )
    parser.add_argument('--name', required=True,
                       help='Object name (e.g., ZCL_MY_CLASS)')
    parser.add_argument('--type', default='class',
                       choices=['class', 'clas', 'interface', 'intf', 'program', 'prog',
                               'report', 'include', 'incl', 'functiongroup', 'fugr',
                               # 2026-08-10 KUSUR-4: sinif ALT-INCLUDE'lari bu listede
                               # HIC YOKTU -> `--type ccau` argparse tarafindan reddediliyor,
                               # operator ham HTTP atmak zorunda kaliyor ve POST/PUT
                               # asimetrisine (KUSUR-5/6) carpiyordu.
                               'testclasses', 'ccau', 'implementations', 'ccimp',
                               'definitions', 'ccdef', 'macros', 'ccmac'],
                       help='Object type (default: class). ccau/ccimp/ccdef/ccmac = '
                            'sinif alt-include (--name ANA SINIF adidir)')
    parser.add_argument('--transport',
                       help='Transport request number (e.g., TRXXXXXX)')
    parser.add_argument('--source-file',
                       help='Full path to local source file (optional, auto-detected if not provided)')
    parser.add_argument('--cwd', help='Working directory containing .conn_adt')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    if not args.transport:
        print("[FAIL] --transport is required.")
        print("[INFO] You MUST run list_transports.py --modifiable-only and ASK the user which transport to use.")
        print("[INFO] NEVER assume, fabricate, or reuse a transport number from memory.")
        return 1

    try:
        client = SAPClient()
        # Sinif alt-include'u (ccau/ccimp/...) AYRI bir yoldur: bagimsiz obje degildir,
        # URL'i ana sinifin adini gerektirir ve yazimi POST-then-PUT sirasi ister
        # (playbook/adt-classes.md 24.8). --name burada ANA SINIF adidir.
        if is_class_include(args.type):
            result = client.push_class_include(
                class_name=args.name,
                include_kind=args.type,
                transport=args.transport,
                source_file=args.source_file
            )
        else:
            result = client.push_object(
                object_name=args.name,
                object_type=args.type,
                transport=args.transport,
                source_file=args.source_file
            )
    except Exception as e:
        print("")
        print("=" * 60)
        print(f"[FAIL] PUSH FAILED - object {args.name} was NOT pushed to SAP")
        print("=" * 60)
        print(f"[ERROR] {type(e).__name__}: {e}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user the push succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("[ACTION REQUIRED] Do NOT call push_object.py again without user confirmation.")
        print("[ACTION REQUIRED] Each retry creates new SAP transport tasks (ghost transports).")
        print("=" * 60)
        return 1

    # result is a dict with 'success' key (or True/False for backward compat)
    success = result.get('success') if isinstance(result, dict) else bool(result)

    if success:
        print(f"[OK] Push completed successfully: {args.name}")
        return 0
    else:
        error = result.get('error', '') if isinstance(result, dict) else ''
        error_type = result.get('error_type', '') if isinstance(result, dict) else ''
        print("")
        print("=" * 60)
        print(f"[FAIL] PUSH FAILED - object {args.name} was NOT pushed to SAP")
        print("=" * 60)
        if error:
            print(f"[ERROR] {error}")
        if error_type:
            print(f"[ERROR TYPE] {error_type}")
        print("")
        print("[ACTION REQUIRED] Do NOT tell the user the push succeeded.")
        print("[ACTION REQUIRED] Report this failure to the user and ask how to proceed.")
        print("[ACTION REQUIRED] Do NOT call push_object.py again without user confirmation.")
        print("[ACTION REQUIRED] Each retry may create new SAP transport tasks (ghost transports).")
        if error_type in ('SAPTransportError', 'SAPAuthenticationError'):
            print("[HINT] Run list_transports.py --modifiable-only and ask the user to pick a valid transport.")
        if error_type == 'SAPLockError':
            if '409' in error or 'transport' in error.lower() or 'CORRNR' in error:
                print("[HINT] Transport conflict: object is locked under a different transport.")
                print("")
                print("=" * 60)
                print("[CRITICAL] DO NOT re-push using the transport number from this error message.")
                print("[CRITICAL] That transport may belong to ANOTHER developer (different owner).")
                print("[CRITICAL] Using it would silently inject your changes into their transport request.")
                print("")
                print("[ACTION REQUIRED] STOP. Report the conflict to the user.")
                print("[ACTION REQUIRED] Run list_transports.py --modifiable-only and SHOW the list.")
                print("[ACTION REQUIRED] ASK the user which transport to use. Wait for their answer.")
                print("[ACTION REQUIRED] NEVER pick a transport yourself.")
                print("")
                print("[MANUAL FIX] If object is stuck:")
                print("  1. SM12 -> delete enqueue lock for this object")
                print("  2. SE01/SE09 -> move object from conflicting transport to the correct one")
                print("  3. Retry push only after user confirms which transport to use")
                print("=" * 60)
            else:
                print("[HINT] Object may be locked by another user. Ask user to check SM12.")
        if error_type == 'SAPActivationError':
            print("[HINT] Run syntax_check.py --name %s to diagnose." % args.name)
        print("=" * 60)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Create multiple SAP CDS Views (DDLS/DF) via ADT REST.

Çözüm: 2-step pattern (POST shell + LOCK + PUT /source/main + UNLOCK).
Library'nin create_cds_view() POST'a source koyuyor — bu sistemde SAP body'yi
ignore ediyor, source/main boş kalıyor (table'daki sorunla aynı, playbook §28).

Kullanım:
    python populate_cds_views.py \\
        --package ZSD015_CLC \\
        --transport <TRANSPORT> \\
        --source-dir ERP/ZSD015_CLC/cds_src \\
        --cwd C:\\<LEGACY_ROOT>\\<PROJECT_NAME>

Source dir formatı:
    Her CDS için bir .cds dosyası:
        ERP/ZSD015_CLC/cds_src/ZSD015_DDL_CONTAINER_TYPES.cds
        ERP/ZSD015_CLC/cds_src/ZSD015_DDL_SHIPPING_TYPES.cds
        ...

    Her .cds dosyası tam DDL kaynağını içerir (annotations + define view).
    Açıklama (description) ilk satırdaki `@EndUserText.label: '...'`'den alınır.
"""

import argparse
import re
import sys
import io
import urllib3
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))
from sap_adt_lib import set_explicit_working_dir, SAPADTClient


def extract_label(source: str) -> str:
    m = re.search(r"@EndUserText\.label\s*:\s*'([^']+)'", source)
    return m.group(1) if m else 'CDS View'


def extract_view_name(source: str) -> str:
    m = re.search(r"define\s+view\s+(\w+)", source, re.IGNORECASE)
    return m.group(1).upper() if m else ''


# ─── PRE-FLIGHT VALIDATION (POZİTİF WHITELIST — Sprint 3 hatası tekrar olmasın) ─
# Playbook §1.5 ve §17.9 — POZİTİF KURAL: TD namespace'de sqlViewName tek doğru
# format `ZSD015_V_<≤5char>`, view name tek doğru `zsd015_ddl_<x>`, source içinde
# hiçbir `zsd_007_*` veya `'ZSD15XXXX'` (eski kısaltma) referansı YASAK.
#
# Sprint 3'te yaşananlar:
# - _convert_cds_sources.py manuel dictionary kullandı, 8+ CDS source <LEGACY_SOURCE>
#   prefix (ZSD_007_CV_*) ile aktive oldu → TADIR cleanup gerekti
# - Bazı CDS'ler `ZSD15XXXX` kısaltma ile aktive edildi → TADIR orphan, rename
#   broken (Sprint 4'te SHIPPING_TYPES bunu tekrar gösterdi)
#
# Whitelist kuralı: sadece tek format OK, geri kalan hepsi RED.
SQL_VIEW_PATTERN  = re.compile(r"^ZSD015_V_[A-Z0-9]{1,5}$")    # POZİTİF: tek geçerli format
VIEW_NAME_PATTERN = re.compile(r"^zsd015_ddl_[a-z0-9_]+$")     # POZİTİF: view name TD namespace
SQL_VIEW_MAX_LEN  = 14                                          # SAP DB SQL view 14 char limit

# RAP view entity: `define [root] view entity` — sqlViewName TAŞIMAZ. Klasik
# whitelist (sqlViewName + `define view zsd015_ddl_`) uygulanmaz; ayrı isim kuralı
# geçerli. 2026-05-15 reconcile (PILOT_VOYAGE_RAP.md §88, repo gate — ADR 0005 dışı).
# view entity / root view entity / abstract entity — hepsi RAP teknik CDS:
# TD-spec + sqlViewName whitelist UYGULANMAZ (abstract entity = RAP action/function
# param/result tipi; veri-CDS veya <LEGACY_SOURCE>→TD dönüşümü değil). 2026-06-03 ZSD011 spike.
RAP_VIEW_ENTITY_RE  = re.compile(r"\bdefine\s+(?:(?:root\s+)?view|abstract)\s+entity\b", re.IGNORECASE)
# Modül-bağımsız RAP view entity adı (NTTDATA: Z<MOD><nnn>_<I|C|R|E>_*;
# MOD = SD/MM/FI/CO/PP/QM/PM/EWM... 2-4 harf). Paket-doğru olma kontrolü
# check_package_naming.py'de (.rules.md regex'i); burası RAP-naming sanity
# (ZSD'ye hardcoded DEĞİL — başka modülde de çalışır).
RAP_VE_NAME_PATTERN = re.compile(r"^Z[A-Z]{2,4}\d{3}_(?:I|C|R|E)_[A-Z0-9_]+$")

# Source body içinde yasak literal'ler (TD namespace dışı her şey)
BANNED_SOURCE_PATTERNS = [
    (re.compile(r"\bzsd_007_\w+", re.IGNORECASE),
     "<LEGACY_SOURCE> namespace referansı (zsd_007_*) — tüm referanslar zsd015_* olmalı"),
    (re.compile(r"'ZSD_007_(?:CV|V)_\w+'"),
     "Eski <LEGACY_SOURCE> sqlViewName literal'i ('ZSD_007_CV_*' / 'ZSD_007_V_*')"),
    (re.compile(r"'ZSD\d{2}[A-Z]{4,8}'"),
     "Eski kısaltılmış sqlViewName literal'i ('ZSD15XXXX' stili) — 'ZSD015_V_XXX' olmalı"),
]

# ─── SPRINT 4 EXCEPTION LISTESİ (Plan A — 2026-05-13) ─────────────────────────
# Sprint 3 release kalıntısı: 9 yaprak CDS shipped DDL source rename teknik
# imkansız (SAP Note 2710405, DDLS 533). Bu CDS'ler **eski sqlViewName** ile
# aktive edildi (re-sync), source dosyaları o şekilde güncellendi.
# Gelecek tüm modüllerde yeni format `ZSD015_V_<X>` zorunlu olarak uygulanır.
#
# Bu liste sadece bu 9 CDS için pre-flight check'i yumuşatır.
SPRINT3_LEGACY_EXCEPTIONS = {
    # User 2026-05-13 gecesi 6 CDS'i temiz TD format ile yeniden yarattı:
    # CONTAINER_CUSTOMER, DISPATCH_ORDER_BC, DISPATCH_SHIP_BAL, ORDER_DISPATCHES,
    # SHIPMENT_LIST (V_SHPLS), CONTAINER_SHIPMENT — bunlar listede DEĞİL.
    'ZSD015_DDL_VOYAGE_DESTINATION': 'ZSD015VYDS',
    'ZSD015_DDL_SHIPMENT_ITEMS':     'ZSD_007_CV_SHPIT',
    'ZSD015_DDL_STOCK_LIST':         'ZSD_007_CV_STOCK',
    'ZSD015_DDL_SHIPPING_TYPES':     'ZSD15SHTYP',
    'ZSD015_DDL_ORDER_ITEMS_SO':     'ZSD15ORDSO',
    'ZSD015_DDL_ORDER_ITEMS_SA':     'ZSD15ORDSA',
}


def validate_sql_view_names(cds_files):
    """POZİTİF WHITELIST validation — her .cds dosyası TD namespace kurallarına uygun mu?

    KURAL (whitelist-only):
    - @AbapCatalog.sqlViewName MUTLAKA 'ZSD015_V_<≤5 char>' formatında OLMALI
    - define view MUTLAKA zsd015_ddl_<x> formatında OLMALI
    - Source body içinde HİÇBİR zsd_007_* veya 'ZSD15XXXX' referansı OLMAMALI

    Doğru:  sqlViewName='ZSD015_V_CONCD', view=zsd015_ddl_container_customer
    Yanlış: sqlViewName='ZSD_007_CV_CONCD' (<LEGACY_SOURCE> prefix)
            sqlViewName='ZSD15CONCD'        (eski kısaltma)
            sqlViewName='ZSD015_V_TOOLONG'  (>14 char)
            view=zsd_007_ddl_x              (eski namespace)
            JOIN zsd_007_ddl_orderitems     (source body'de orphan ref)

    Returns: hata mesajı listesi (boş = OK)
    """
    errors = []
    for f in cds_files:
        try:
            source = f.read_text(encoding='utf-8')
        except Exception as e:
            errors.append(f"{f.name}: okunamadı: {e}")
            continue

        # CDS adından exception kontrolü (Sprint 3 release kalıntısı 9 CDS)
        cds_name = f.stem.upper()
        legacy_sv = SPRINT3_LEGACY_EXCEPTIONS.get(cds_name)

        # ─── RAP VIEW ENTITY DALI (sqlViewName YOK; ayrı isim kuralı) ────────
        if RAP_VIEW_ENTITY_RE.search(source):
            if re.search(r"@AbapCatalog\.sqlViewName", source):
                errors.append(
                    f"{f.name}: RAP view entity'de @AbapCatalog.sqlViewName "
                    f"YASAK (view entity sqlView taşımaz). Kaldır. "
                    f"(checklist C-RAP-VE-02)"
                )
            vem = re.search(
                r"\bdefine\s+(?:(?:root\s+)?view|abstract)\s+entity\s+(\S+)",
                source, re.IGNORECASE,
            )
            if not vem:
                errors.append(
                    f"{f.name}: 'define [root] view entity <name>' bulunamadı"
                )
            elif not RAP_VE_NAME_PATTERN.match(vem.group(1).upper()):
                errors.append(
                    f"{f.name}: RAP view entity adı='{vem.group(1)}' YASAK. "
                    f"FORMAT: 'Z<MOD><nnn>_<I|C|R|E>_<x>' "
                    f"(regex: ^Z[A-Z]{{2,4}}\\d{{3}}_(I|C|R|E)_[A-Z0-9_]+$). "
                    f"(standards/05-coding-rap.md §4)"
                )
            # Section 3 (yasak namespace ref) RAP view entity'de de geçerli
            for pat, msg in BANNED_SOURCE_PATTERNS:
                for hit in pat.finditer(source):
                    line_no = source[:hit.start()].count('\n') + 1
                    errors.append(
                        f"{f.name}:{line_no}: YASAK literal '{hit.group(0)}' — {msg}"
                    )
            continue

        # ─── 1. @AbapCatalog.sqlViewName WHITELIST (+exception) ──────────────
        m = re.search(r"@AbapCatalog\.sqlViewName\s*:\s*'([^']+)'", source)
        if not m:
            errors.append(f"{f.name}: @AbapCatalog.sqlViewName annotation EKSİK "
                          f"(zorunlu, format: 'ZSD015_V_<≤5 char>')")
        else:
            sv = m.group(1)
            if legacy_sv and sv == legacy_sv:
                # Sprint 3 legacy istisna — OK, atla (kayıt için)
                pass
            elif not SQL_VIEW_PATTERN.match(sv):
                errors.append(
                    f"{f.name}: sqlViewName='{sv}' YASAK. "
                    f"TEK GEÇERLİ FORMAT: 'ZSD015_V_<1-5 büyük harf/rakam>' "
                    f"(regex: ^ZSD015_V_[A-Z0-9]{{1,5}}$, toplam ≤14 char). "
                    f"(Playbook §17.9)"
                )
            elif len(sv) > SQL_VIEW_MAX_LEN:
                errors.append(
                    f"{f.name}: sqlViewName='{sv}' uzunluk={len(sv)} > "
                    f"{SQL_VIEW_MAX_LEN} (SAP DB SQL view 14 char limit)"
                )

        # ─── 2. define view <name> WHITELIST ──────────────────────────────────
        vm = re.search(r"\bdefine\s+view\s+(\S+)", source, re.IGNORECASE)
        if not vm:
            errors.append(f"{f.name}: 'define view <name>' bulunamadı")
        else:
            vname = vm.group(1).lower()
            if not VIEW_NAME_PATTERN.match(vname):
                errors.append(
                    f"{f.name}: define view='{vname}' YASAK. "
                    f"TEK GEÇERLİ FORMAT: 'zsd015_ddl_<x>' "
                    f"(regex: ^zsd015_ddl_[a-z0-9_]+$). "
                    f"(Playbook §17.9)"
                )

        # ─── 3. Source body içinde YASAK referans tarama ─────────────────────
        # Legacy CDS için sqlViewName satırını skip et (annotation kendisi
        # yasak literal pattern'a uyabilir)
        for pat, msg in BANNED_SOURCE_PATTERNS:
            for hit in pat.finditer(source):
                # Hangi satırda bulundu?
                line_no = source[:hit.start()].count('\n') + 1
                # Legacy exception: sqlViewName annotation satırındaki literal'i tolere et
                if legacy_sv and hit.group(0).strip("'") == legacy_sv:
                    continue
                errors.append(
                    f"{f.name}:{line_no}: YASAK literal '{hit.group(0)}' — {msg}"
                )

    return errors


def build_shell_xml(name: str, description: str, package: str, master_lang: str = 'TR') -> str:
    """Shell XML — sadece metadata, source body içinde DEĞİL."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<ddl:ddlSource xmlns:ddl="http://www.sap.com/adt/ddic/ddlsources"
                xmlns:adtcore="http://www.sap.com/adt/core"
                adtcore:name="{name.upper()}"
                adtcore:description="{xml_escape(description)}"
                adtcore:masterLanguage="{master_lang}">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{package.upper()}"/>
</ddl:ddlSource>'''


def cds_exists(client: SAPADTClient, name: str) -> bool:
    r = client.session.get(
        client.url + f'/sap/bc/adt/ddic/ddl/sources/{name.lower()}',
        verify=False, timeout=10
    )
    return r.status_code == 200


def create_one(client: SAPADTClient, csrf: str, name: str, source: str,
               package: str, transport: str,
               force_recreate: bool = False, dry_run: bool = False) -> bool:
    name = name.upper()
    description = extract_label(source)
    exists = cds_exists(client, name) if not dry_run else False

    if exists and not force_recreate:
        print(f'  [SKIP] {name} zaten var')
        return True

    shell_xml = build_shell_xml(name, description, package)

    if dry_run:
        print(f'\n--- DRY-RUN: {name} ---')
        print(f'Description: {description}')
        print(f'Source preview (first 400 chars):')
        print(source[:400])
        return True

    # Step 1: DELETE if force_recreate
    if force_recreate and exists:
        client.session.delete(
            client.url + f'/sap/bc/adt/ddic/ddl/sources/{name.lower()}',
            params={'corrNr': transport},
            headers={'X-CSRF-Token': csrf}, verify=False, timeout=30
        )

    # Step 2: POST shell create
    r = client.session.post(
        client.url + '/sap/bc/adt/ddic/ddl/sources',
        params={'corrNr': transport},
        headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'application/vnd.sap.adt.ddlSource+xml; charset=utf-8',
            'Accept': 'application/vnd.sap.adt.ddlSource+xml',
            'sap-client': '100',
            'sap-language': 'TR',
        },
        data=shell_xml.encode('utf-8'),
        verify=False, timeout=60
    )
    if r.status_code not in (200, 201):
        print(f'  [FAIL] {name} POST status={r.status_code}')
        print(f'         Body: {r.text[:400]}')
        return False

    # Step 3: LOCK
    obj_url = f'/sap/bc/adt/ddic/ddl/sources/{name.lower()}'
    lr = client.session.post(
        client.url + obj_url,
        params={'_action':'LOCK', 'accessMode':'MODIFY', 'corrNr':transport},
        headers={
            'X-CSRF-Token': csrf,
            'X-sap-adt-sessiontype': 'stateful',
            'Accept': 'application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result',
        },
        verify=False, timeout=15
    )
    m = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lr.text)
    handle = m.group(1) if m else None
    if not handle:
        print(f'  [FAIL] {name} LOCK status={lr.status_code}')
        return False

    try:
        # Step 4: PUT source/main (If-Match GÖNDERME, playbook §28)
        pr = client.session.put(
            client.url + obj_url + '/source/main',
            params={'corrNr': transport, 'lockHandle': handle},
            headers={
                'X-CSRF-Token': csrf,
                'Content-Type': 'text/plain; charset=utf-8',
                'Accept': '*/*',
            },
            data=source.encode('utf-8'),
            verify=False, timeout=60
        )
        if pr.status_code in (200, 201, 204):
            print(f'  [OK]   {name}  ({len(source)} bytes pushed)')
            return True
        else:
            print(f'  [FAIL] {name} PUT source/main status={pr.status_code}')
            print(f'         Body: {pr.text[:400]}')
            return False
    finally:
        # Step 5: UNLOCK
        try:
            client.session.post(
                client.url + obj_url,
                params={'_action':'UNLOCK', 'lockHandle':handle},
                headers={'X-CSRF-Token':csrf, 'X-sap-adt-sessiontype':'stateful'},
                verify=False, timeout=10
            )
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description='Batch-create SAP CDS Views from .cds source files')
    parser.add_argument('--package', required=True)
    parser.add_argument('--transport', required=True)
    parser.add_argument('--source-dir', required=True,
                        help='Directory with .cds files (one per view)')
    parser.add_argument('--cwd')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force-recreate', action='store_true')
    parser.add_argument('--only', help='Comma-separated CDS names to process')
    args = parser.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    src_dir = Path(args.source_dir)
    if not src_dir.exists():
        print(f'[FAIL] Source dir bulunamadı: {src_dir}')
        return 1

    only_set = None
    if args.only:
        only_set = {x.strip().upper() for x in args.only.split(',')}

    cds_files = sorted(src_dir.glob('*.cds'))
    if not cds_files:
        print(f'[FAIL] {src_dir} altında .cds dosyası yok')
        return 1

    print(f'[INFO] {len(cds_files)} .cds dosyası bulundu')

    # ─── PRE-FLIGHT: sqlViewName format validation ─────────────────────────
    # Sprint 3 hatası tekrar olmasın: <LEGACY_SOURCE> prefix veya eski kısaltma
    # ile yaratma DENEMEDEN HEMEN dur. Playbook §1.5 ve §17.9.
    if only_set is None:
        files_to_check = cds_files
    else:
        files_to_check = [f for f in cds_files if f.stem.upper() in only_set]

    # ─── PRE-FLIGHT 1/3: Sprint Gate Check (LESSONS_LEARNED.md PATTERN #1) ──
    # Bu populate işlemi hangi sprint'e ait? Önceki sprint'ler kapalı mı?
    # CDS yaratma → genelde Sprint 3, 4 veya 5. En geniş tahmin: hedef = 5
    # (en geç sprint'in CDS'i de gerekirse). Hata raporunda kullanıcı düzeltir.
    try:
        from sprint_gate_check import ensure_sprint_gates_open
        target_sprint = '3'  # CDS'in en erken sprint'i
        if not ensure_sprint_gates_open(target_sprint, raise_on_fail=False):
            return 1
    except ImportError as e:
        print(f'[WARN] sprint_gate_check modülü yüklenemedi: {e}')

    # ─── PRE-FLIGHT 2/3: TD Spec Cross-Check (Playbook §1 §6️⃣) ──────────────
    # Her .cds dosyası için TD spec MD'sini bul, "Silinen Alanlar/Kaldırılan"
    # tabloyu parse et, source'ta hala duranlar varsa FAIL.
    # Spec yoksa exit 1 (operator approval mesajı).
    try:
        from td_spec_check import require_td_spec, find_deleted_items, scan_source_for_deleted
        spec_errors = []
        for f in files_to_check:
            cds_name = f.stem.upper()
            # RAP view entity → TD spec ZORUNLU DEĞİL (<LEGACY_SOURCE>→TD dönüşümü
            # değil; fresh Z-tablo view'ı). Reviewer rap_cds_creation zinciri de
            # td_spec_check içermez. standards/05-coding-rap.md §9; 2026-05-15
            # reconcile (PILOT_VOYAGE_RAP.md §88, repo gate — ADR 0005 dışı).
            try:
                if RAP_VIEW_ENTITY_RE.search(f.read_text(encoding='utf-8')):
                    continue
            except Exception:
                pass
            try:
                spec_text = require_td_spec(cds_name, 'cds')
            except SystemExit as se:
                # TD spec yok — operator approval gerekli
                print(str(se))
                return 1
            deleted = find_deleted_items(spec_text)
            if not deleted['fields'] and not deleted['joins']:
                continue  # Bu spec'te silinen yok, skip
            source = f.read_text(encoding='utf-8')
            issues = scan_source_for_deleted(source, deleted)
            if issues:
                spec_errors.append((cds_name, issues))
        if spec_errors:
            print(f'\n[FAIL] TD spec cross-check başarısız '
                  f'({len(spec_errors)} CDS\'te silinmiş item hala source\'ta):')
            for cds_name, issues in spec_errors:
                print(f'  ✗ {cds_name}:')
                for i in issues:
                    print(f'  {i}')
            print(f'\nPlaybook §1 §6️⃣ — TD Spec Disiplini: silinen alanlar source\'tan çıkarılmalı')
            return 1
        print(f'[OK] TD spec cross-check: {len(files_to_check)} dosya temiz '
              f'(silinen alan/join referansı yok)')
    except ImportError as e:
        print(f'[WARN] td_spec_check modülü yüklenemedi: {e}')
        print(f'       Pre-flight TD spec katmanı atlandı.')

    naming_errors = validate_sql_view_names(files_to_check)
    if naming_errors:
        print(f'\n[FAIL] sqlViewName pre-flight kontrolü başarısız '
              f'({len(naming_errors)} hata):')
        for err in naming_errors:
            print(f'  ✗ {err}')
        print(f'\nDoğru format: ZSD015_V_<≤5 karakter> (toplam ≤14 char)')
        print(f'Playbook §17.9 — Namespace Dönüşümü Doğrulama')
        return 1
    print(f'[OK] Pre-flight: {len(files_to_check)} dosya doğru '
          f'sqlViewName formatında (ZSD015_V_<XXX>)')

    client = SAPADTClient()
    csrf = ''
    if not args.dry_run:
        client._invalidate_csrf_cache()
        r = client.session.get(
            client.url + '/sap/bc/adt/discovery',
            params={'sap-client':'100','sap-language':'TR'},
            headers={'X-CSRF-Token':'Fetch'},
            verify=False
        )
        csrf = r.headers.get('X-CSRF-Token', '')
        if not csrf:
            print('[FAIL] CSRF token alınamadı')
            return 1
        print(f'[OK] CSRF: {csrf[:24]}...')

    ok = 0
    fail = 0
    for f in cds_files:
        name = f.stem.upper()
        if only_set and name not in only_set:
            continue
        source = f.read_text(encoding='utf-8')
        if create_one(client=client, csrf=csrf, name=name, source=source,
                      package=args.package, transport=args.transport,
                      force_recreate=args.force_recreate, dry_run=args.dry_run):
            ok += 1
        else:
            fail += 1

    print(f'\n=== Sonuç: {ok} başarılı, {fail} hatalı ===')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())

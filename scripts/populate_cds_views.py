#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production tool: Create multiple SAP CDS Views (DDLS/DF) via ADT REST.

Çözüm: 2-step pattern (POST shell + LOCK + PUT /source/main + UNLOCK).
Library'nin create_cds_view() POST'a source koyuyor — bu sistemde SAP body'yi
ignore ediyor, source/main boş kalıyor (table'daki sorunla aynı, playbook §28).

Kullanım:
    python populate_cds_views.py \\
        --package ZSD<NNN>_CLC \\
        --transport <TR_NO> \\
        --source-dir <source_root>/ZSD<NNN>_CLC/cds_src \\
        --cwd <PROJECT_ROOT>

Source dir formatı:
    Her CDS için bir .cds dosyası:
        <source_root>/ZSD<NNN>_CLC/cds_src/ZSD<NNN>_DDL_CONTAINER_TYPES.cds
        <source_root>/ZSD<NNN>_CLC/cds_src/ZSD<NNN>_DDL_SHIPPING_TYPES.cds
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


# ─── PRE-FLIGHT VALIDATION (POZİTİF WHITELIST — legacy-prefix hatası tekrar olmasın) ─
# Playbook §1.5 ve §17.9 — POZİTİF KURAL: proje namespace'inde sqlViewName tek doğru
# format `<sql_view_prefix><≤5char>`, view name tek doğru `<cds_view_name_prefix><x>`,
# source içinde hiçbir legacy-namespace / eski-kısaltma referansı YASAK.
#
# Tarihsel ders (bu gate'in doğduğu vaka):
# - Elle dictionary'li dönüşüm 8+ CDS source'u LEGACY prefix ile aktive etti →
#   TADIR cleanup gerekti; bazıları kısaltma-sqlViewName ile aktive edildi →
#   TADIR orphan + rename broken (shipped DDL rename teknik imkansız, SAP Note 2710405).
#
# Whitelist kuralı: sadece tek format OK, geri kalan hepsi RED.
#
# ⭐ PREFIX KAYNAĞI — PAKET ADINDAN TÜRETİLİR (2026-08-27; çok-paketli düzeltme)
# Önceki davranış: prefix YALNIZ project.yaml'daki TEK düz string'ti
# (`sql_view_prefix` / `cds_view_name_prefix`). Bir proje deposunda birden çok
# paket yaşadığı için bu, hangi paketin CDS'i doğrulanırsa doğrulansın HERKESE
# tek paketin prefix'ini dayatıyordu → o paket dışındaki her paketin TÜM canlı
# `.cds` dosyaları yapısal olarak FAIL veriyordu (ölçüldü: 11 paket / ~121 dosya).
# Artık prefix `--package` argümanından DETERMİNİSTİK türetilir:
#     ZMOD001_CLC  →  sqlView: "ZMOD001_V_"   ·   view adı: "zmod001_ddl_"
# Kök kalıp `RAP_VE_NAME_PATTERN` ile AYNIDIR (Z<MOD 2-4 harf><3 hane>).
# project.yaml config'i KALKMADI: paket adı kalıba uymuyorsa (ya da paket
# bilinmiyorsa) fallback olarak kullanılır. İkisi de yoksa gate VARSAYMAZ —
# validate anında NET hatayla durur (fail-safe).
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[0]))
from utils.project_config import cfg as _cfg  # noqa: E402

_SQLP = _cfg("sql_view_prefix")          # fallback (örn. "ZMOD001_V_")
_VNP  = _cfg("cds_view_name_prefix")     # fallback (örn. "zmod001_ddl_")
SQL_VIEW_MAX_LEN  = 14                                          # SAP DB SQL view 14 char limit

# Paket adının namespace kökü: ZMOD001_CLC → ZMOD001 (sondaki `_<suffix>` serbest,
# suffix'siz düz paket adı da kabul). `\d{3}` sonrası başka rakam/harf gelirse
# EŞLEŞMEZ → yanlış türetme yerine config fallback'ine düşülür (fail-safe).
_PKG_PREFIX_RE = re.compile(r"^(Z[A-Z]{2,4}\d{3})(?:_|$)")


def _derive_prefixes(package=None):
    """(sql_view_prefix, cds_view_name_prefix) — paket adından türet, olmazsa config.

    ZMOD001_CLC → ("ZMOD001_V_", "zmod001_ddl_")
    Paket None / kalıp dışı (ör. "LEGACY_STUFF") → (config, config) — ikisi de
    None olabilir; o zaman çağıran fail-safe hata döndürür.
    """
    if package:
        m = _PKG_PREFIX_RE.match(str(package).strip().upper())
        if m:
            kok = m.group(1)
            return f"{kok}_V_", f"{kok.lower()}_ddl_"
    return _SQLP, _VNP

# RAP view entity: `define [root] view entity` — sqlViewName TAŞIMAZ. Klasik
# whitelist (sqlViewName + `define view <cds_view_name_prefix>`) uygulanmaz; ayrı isim kuralı
# geçerli. 2026-05-15 reconcile (PILOT_VOYAGE_RAP.md §88, repo gate — ADR 0005 dışı).
# view entity / root view entity / abstract entity — hepsi RAP teknik CDS:
# TD-spec + sqlViewName whitelist UYGULANMAZ (abstract entity = RAP action/function
# param/result tipi; veri-CDS veya legacy→TD dönüşümü değil). 2026-06-03 RAP spike.
RAP_VIEW_ENTITY_RE  = re.compile(r"\bdefine\s+(?:(?:root\s+)?view|abstract)\s+entity\b", re.IGNORECASE)
# Modül-bağımsız RAP view entity adı (NTTDATA: Z<MOD><nnn>_<I|C|R|E>_*;
# MOD = SD/MM/FI/CO/PP/QM/PM/EWM... 2-4 harf). Paket-doğru olma kontrolü
# check_package_naming.py'de (.rules.md regex'i); burası RAP-naming sanity
# (ZSD'ye hardcoded DEĞİL — başka modülde de çalışır).
RAP_VE_NAME_PATTERN = re.compile(r"^Z[A-Z]{2,4}\d{3}_(?:I|C|R|E)_[A-Z0-9_]+$")

# Source body içinde yasak literal'ler — PROJE-CONFIG'ten (legacy namespace projeye
# özgü veridir; core hard-code etmez). project.yaml:
#   cds_banned_literals:
#     - "\\bzsd_007_\\w+"          # legacy namespace referansı
#     - "'ZSD_007_(?:CV|V)_\\w+'"  # legacy sqlViewName literal'i
#     - "'ZSD\\d{2}[A-Z]{4,8}'"    # eski kısaltılmış sqlViewName stili
# Tanımsızsa bu EK tarama atlanır (prefix-whitelist yine zorunludur).
BANNED_SOURCE_PATTERNS = []
for _pat in (_cfg("cds_banned_literals") or []):
    try:
        BANNED_SOURCE_PATTERNS.append(
            (re.compile(_pat, re.IGNORECASE),
             f"proje-config yasak literal'i (cds_banned_literals: {_pat})"))
    except re.error as _e:
        print(f"[UYARI] cds_banned_literals regex derlenemedi: {_pat} ({_e})")

# ─── LEGACY sqlViewName İSTİSNALARI — PROJE-CONFIG'ten ────────────────────────
# Shipped DDL source rename teknik imkansız (SAP Note 2710405, DDLS 533) —
# eski sqlViewName ile aktive kalmış CDS'ler için pre-flight yumuşatması.
# project.yaml:  cds_legacy_sqlview_exceptions: ["ZSD001_DDL_X:ZSD01OLDSV", ...]
# ("VIEWADI:ESKISQLVIEW" çiftleri; yeni modüllerde yeni format zorunlu kalır.)
LEGACY_SQLVIEW_EXCEPTIONS = {}
for _cift in (_cfg("cds_legacy_sqlview_exceptions") or []):
    if ":" in str(_cift):
        _ad, _sv = str(_cift).split(":", 1)
        LEGACY_SQLVIEW_EXCEPTIONS[_ad.strip().upper()] = _sv.strip()


def validate_sql_view_names(cds_files, package=None):
    """POZİTİF WHITELIST validation — her .cds dosyası TD namespace kurallarına uygun mu?

    KURAL (whitelist-only; prefix'ler PAKET ADINDAN türetilir, yoksa project.yaml):
    - @AbapCatalog.sqlViewName MUTLAKA '<sql_view_prefix><≤5 char>' formatında OLMALI
    - define view MUTLAKA <cds_view_name_prefix><x> formatında OLMALI
    - Source body içinde HİÇBİR cds_banned_literals deseni OLMAMALI (legacy ns vb.)

    Args:
        cds_files: doğrulanacak .cds Path'leri
        package:   hedef ABAP paketi (`--package`). Verilirse prefix BUNDAN türetilir
                   (ZMOD001_CLC → 'ZMOD001_V_' / 'zmod001_ddl_') — böylece gate
                   TEK pakete kilitli kalmaz. None ise/kalıp dışıysa project.yaml
                   config'ine düşülür (geriye-uyum: eski çağrı biçimi aynen çalışır).

    Örn. (package=ZMOD001_CLC → ZMOD001_V_ / zmod001_ddl_):
    Doğru:  sqlViewName='ZMOD001_V_CONCD', view=zmod001_ddl_container_customer
    Yanlış: sqlViewName='<legacy-prefix>_CONCD'  (eski namespace)
            sqlViewName='ZMD01CONCD'             (eski kısaltma)
            sqlViewName='ZMOD001_V_TOOLONG'      (>14 char)
            JOIN <legacy>_ddl_orderitems         (source body'de orphan ref)

    Returns: hata mesajı listesi (boş = OK)
    """
    errors = []
    # Prefix: paket adından türet → olmazsa project.yaml config'i (fallback).
    _sqlp, _vnp = _derive_prefixes(package)
    # B-5 fail-safe: ne paket adı çözülebildi ne config var → VARSAYMA, NET hata.
    if not _sqlp or not _vnp:
        return [f"NAMESPACE-GATE ÇÖZÜLEMEDİ (B-5): paket adı={package!r} kalıba "
                f"UYMUYOR (beklenen: 'Z<MOD 2-4 harf><3 hane>_<x>', ör. ZMOD001_CLC) "
                f"VE project.yaml'da `sql_view_prefix` / `cds_view_name_prefix` YOK. "
                f"İkisinden BİRİ gerekli — gate prefix VARSAYMAZ, bu doldurulmadan "
                f"CDS populate REDDEDİLİR."]
    sql_view_pattern  = re.compile(r"^" + re.escape(_sqlp) + r"[A-Z0-9]{1,5}$")
    view_name_pattern = re.compile(r"^" + re.escape(_vnp) + r"[a-z0-9_]+$")
    for f in cds_files:
        try:
            source = f.read_text(encoding='utf-8')
        except Exception as e:
            errors.append(f"{f.name}: okunamadı: {e}")
            continue

        # CDS adından exception kontrolü (config: cds_legacy_sqlview_exceptions)
        cds_name = f.stem.upper()
        legacy_sv = LEGACY_SQLVIEW_EXCEPTIONS.get(cds_name)

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
                          f"(zorunlu, format: '{_sqlp}<≤5 char>')")
        else:
            sv = m.group(1)
            if legacy_sv and sv == legacy_sv:
                # Sprint 3 legacy istisna — OK, atla (kayıt için)
                pass
            elif not sql_view_pattern.match(sv):
                errors.append(
                    f"{f.name}: sqlViewName='{sv}' YASAK. "
                    f"TEK GEÇERLİ FORMAT: '{_sqlp}<1-5 büyük harf/rakam>' "
                    f"(regex: {sql_view_pattern.pattern}, toplam ≤14 char). "
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
            if not view_name_pattern.match(vname):
                errors.append(
                    f"{f.name}: define view='{vname}' YASAK. "
                    f"TEK GEÇERLİ FORMAT: '{_vnp}<x>' "
                    f"(regex: {view_name_pattern.pattern}). "
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
    parser.add_argument('--target-sprint',
                        help='Sprint kapısının hedef sprint ID\'si (ör. 3). '
                             'Verilmezse project.yaml `cds_target_sprint`; '
                             'o da yoksa kapı UYGULANMAZ (core tahmin etmez).')
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
    # Tarihsel hata tekrar olmasın: legacy prefix veya eski kısaltma
    # ile yaratma DENEMEDEN HEMEN dur. Playbook §1.5 ve §17.9.
    if only_set is None:
        files_to_check = cds_files
    else:
        files_to_check = [f for f in cds_files if f.stem.upper() in only_set]

    # ─── PRE-FLIGHT 1/3: Sprint Gate Check (LESSONS_LEARNED.md PATTERN #1) ──
    # Bu populate işlemi hangi sprint'e ait? Önceki sprint'ler kapalı mı?
    #
    # ⛔ ESKIDEN: `target_sprint = '3'` **core'a gömülü tahmindi** (kendi yorumu
    # *"En geniş tahmin"*). Sonuç yapısal yanlış-pozitifti: sprint panosu TEK bir
    # paketin planıdır; başka bir paketin CDS'i yazılırken kapı O PAKETİN açık
    # sprint'lerine bakıp `return 1` ile bloklardı. Ölçüldü 2026-08-19: hedef
    # paketin hiçbir CDS'i bu araçla yazılamıyordu (vaka değil SINIF).
    #
    # ⭐ Hedef sprint artık **proje kaynağından** gelir, core'dan değil:
    #     1) `--target-sprint` (açık parametre, en yüksek öncelik)
    #     2) `project.yaml: cds_target_sprint` (env: `IX_CDS_TARGET_SPRINT`)
    #     3) hiçbiri yoksa → **kapı DEVRE DIŞI** (tahmin YOK, körlemesine blok YOK)
    # Kapı KALDIRILMADI: tanım verildiğinde aynen bloklar (pozitif kontrol).
    target_sprint = args.target_sprint
    if not target_sprint:
        try:
            from utils.project_config import cfg
            v = cfg('cds_target_sprint')
            target_sprint = str(v).strip() if v else None
        except Exception as e:
            print(f'[WARN] proje config okunamadı ({e.__class__.__name__}) — '
                  f'sprint kapısı hedefi belirlenemedi')
            target_sprint = None

    if not target_sprint:
        print('[SKIP] Sprint kapısı: hedef sprint tanımsız — kapı uygulanmadı.'
              ' (Tanımlamak için: --target-sprint <ID> ya da project.yaml'
              ' `cds_target_sprint`)')
    else:
        try:
            from sprint_gate_check import ensure_sprint_gates_open
            if not ensure_sprint_gates_open(target_sprint, raise_on_fail=False):
                return 1
        except ImportError as e:
            print(f'[WARN] sprint_gate_check modülü yüklenemedi: {e}')
        except ValueError as e:
            # Hedef, BU projenin panosunda yok. Eskiden bu ham ValueError ile
            # script'i ÇÖKERTİRDİ; artık görünür SKIP (yanlış panoya ait hedef
            # bir kod hatası değil, konfigürasyon uyumsuzluğudur).
            print(f'[SKIP] Sprint kapısı: {e} — bu projenin panosunda yok, '
                  f'kapı uygulanmadı')

    # ─── PRE-FLIGHT 2/3: TD Spec Cross-Check (Playbook §1 §6️⃣) ──────────────
    # Her .cds dosyası için TD spec MD'sini bul, "Silinen Alanlar/Kaldırılan"
    # tabloyu parse et, source'ta hala duranlar varsa FAIL.
    # Spec yoksa exit 1 (operator approval mesajı).
    try:
        from td_spec_check import require_td_spec, find_deleted_items, scan_source_for_deleted
        spec_errors = []
        for f in files_to_check:
            cds_name = f.stem.upper()
            # RAP view entity → TD spec ZORUNLU DEĞİL (legacy→TD dönüşümü
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

    # Prefix HEDEF PAKETTEN türetilir (tek-paket kilidi kalktı, 2026-08-27)
    _sqlp_main, _vnp_main = _derive_prefixes(args.package)
    naming_errors = validate_sql_view_names(files_to_check, package=args.package)
    if naming_errors:
        print(f'\n[FAIL] sqlViewName pre-flight kontrolü başarısız '
              f'({len(naming_errors)} hata):')
        for err in naming_errors:
            print(f'  ✗ {err}')
        if _sqlp_main:
            print(f'\nDoğru format: {_sqlp_main}<≤5 karakter> (toplam ≤14 char) '
                  f'— paket {args.package} için türetildi')
        print(f'Playbook §17.9 — Namespace Dönüşümü Doğrulama')
        return 1
    print(f'[OK] Pre-flight: {len(files_to_check)} dosya doğru '
          f'sqlViewName formatında ({_sqlp_main}<XXX>)')

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

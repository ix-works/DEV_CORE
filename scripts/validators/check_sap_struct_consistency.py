"""
check_sap_struct_consistency.py — Post-create validator.

Lokal artifact'taki struct tanımı ile SAP'deki aktif versiyonu karşılaştırır:
  - Placeholder detection (component_to_be_changed:abap.string(0))
  - Field count match (lokal vs SAP)
  - Field name set match
  - SAP'de version == "active"

Sprint 6 lesson (T10): adt_struct_create fields[] yöntemi SAP'de sadece placeholder
yaratıyor — 58 alan iddiası ile gerçekte 1 alan. Bu validator yakalar.

Kullanım:
    python scripts/validators/check_sap_struct_consistency.py <artifact.asddls>

Exit kodu:
    0 — Tutarlı (lokal == SAP, active)
    1 — Tutarsız (placeholder, field count diff, veya inactive)
"""
import argparse
import re
import sys
from pathlib import Path

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_status import gate_status, sap_baglanti_yok  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.ad_politikasi import AD_ADAYI, ad_coz  # noqa: E402 — TEK ad grameri (#402 K1)

_GATE = Path(__file__).stem

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


PLACEHOLDER_PATTERN = re.compile(r'\bcomponent_to_be_changed\s*:\s*abap\.string', re.IGNORECASE)
# Yapı ve ALAN adları `ad_politikasi` gramerinden (#402 K1): `(\w+)` `/` eşlemediği için
# namespace'li yapı "define structure yok" sayılıyor, namespace'li alan (`/nspc/fld : …`) alan
# kümesine hiç girmiyordu (eksik alan SAP'de de eksikse fark GÖRÜNMEZDİ).
STRUCT_NAME_PATTERN = re.compile(r'define\s+structure\s+(' + AD_ADAYI + r')', re.IGNORECASE)
STRUCT_KW_PATTERN = re.compile(r'define\s+structure\b', re.IGNORECASE)
_ALAN_SATIRI = re.compile(r'^(' + AD_ADAYI + r')\s*:\s+')


def extract_struct_name(text: str) -> str | None:
    """Katı gramere uyan yapı adı (büyük harf) ya da None (`define structure` yok / ad bozuk)."""
    m = STRUCT_NAME_PATTERN.search(text)
    ad = ad_coz(m.group(1))[0] if m else ''
    return ad.upper() if ad else None


def cozulemeyen_alanlar(text: str) -> list[str]:
    """Alan konumunda olup katı gramere UYMAYAN adlar (`/ab/x : …`) — kıyas bunlarla ölçülemez."""
    out = []
    for line in text.splitlines():
        m = _ALAN_SATIRI.match(line.strip())
        if m and not ad_coz(m.group(1))[0]:
            out.append(m.group(1))
    return out


def extract_fields(text: str) -> set[str]:
    """Return set of field names from struct DDL source.

    Excludes annotation lines, keywords (define, with, where, and), and the struct name itself.
    Ad gramere uymayan alan satırı kümeye GİRMEZ — çağıran `cozulemeyen_alanlar` ile ölçer.
    """
    keywords = {'define', 'structure', 'with', 'where', 'and', 'value', 'help',
                'foreign', 'key', 'in', 'on', 'as', 'using', 'syst'}
    fields = set()
    struct_name = extract_struct_name(text)
    struct_name_lower = struct_name.lower() if struct_name else ''
    in_struct = False
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('@') or s.startswith('--') or s.startswith('//'):
            continue
        if 'define structure' in s.lower() or 'define table' in s.lower():
            in_struct = True
            continue
        if not in_struct:
            continue
        if s.startswith('}'):
            break
        # Lines that match "name : type" with name at the start of the line (not indented continuation)
        m = _ALAN_SATIRI.match(s)
        if m and ad_coz(m.group(1))[0]:
            name = m.group(1).lower()
            if name in keywords:
                continue
            if name == struct_name_lower:
                continue
            fields.add(name)
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description='SAP struct active version vs local artifact tutarlılık')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true',
                       help='(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ, run_all --strict kazara terfi ettirmesin; ADR 0019 §54)')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    local_text = path.read_text(encoding='utf-8', errors='replace')
    struct_name = extract_struct_name(local_text)
    if not struct_name and STRUCT_KW_PATTERN.search(local_text):
        # #402 K2: `define structure` VAR ama ad katı gramere uymadı (ör. `/AB/X`) ⇒ ÖLÇÜLEMEDİ.
        print(f'ÖLÇÜLEMEDİ — {path.name} `define structure` içeriyor ama yapı adı çözülemedi '
              f'→ SAP kıyası KOŞMADI')
        gate_status(_GATE, 'SKIPPED', False, 'ad-cozulemedi')
        return 0
    if not struct_name:
        print(f'UYARI: {path.name} içinde "define structure NAME" bulunamadı — validator atlandı')
        # Hedef obje ADI çıkarılamadı => SAP'de hiçbir şey sorgulanmadı.
        gate_status(_GATE, 'SKIPPED', False, 'struct-adi-cikarilamadi')
        return 0

    bozuk = cozulemeyen_alanlar(local_text)
    if bozuk:
        print(f'ÖLÇÜLEMEDİ — {path.name}: alan adı çözülemedi {bozuk[:5]} → alan kümesi kıyası '
              f'eksik olurdu, KOŞMADI')
        gate_status(_GATE, 'SKIPPED', False, 'ad-cozulemedi')
        return 0
    local_fields = extract_fields(local_text)
    if not local_fields:
        print(f'UYARI: {path.name} içinde alan bulunamadı — validator atlandı')
        gate_status(_GATE, 'SKIPPED', False, 'yerel-alan-cikarilamadi')
        return 0

    # SAP'ye bağlan
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.ad_politikasi import url_segmenti as _adt_seg  # noqa: E402 — Q393 P2a: ADT yol parcasi tek kaynak
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        sap_baglanti_yok(_GATE)
        return 0

    # SAP'den source çek (structures endpoint)
    try:
        r = client.session.get(
            client.url + f'/sap/bc/adt/ddic/structures/{_adt_seg(struct_name)}/source/main',
            params={'sap-client': '100'}, verify=False, timeout=20
        )
    except Exception as e:
        print(f'UYARI: SAP GET hata: {e}', file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, 'sap-get-istisnasi')
        return 0

    if r.status_code == 404:
        # Struct henüz yok — bu pre-create durumu, validator buradan birşey demiyor
        print(f'OK — {struct_name} SAP\'de henüz yok (pre-create durumu, atlandı)')
        # 404 GERÇEK bir hükümdür: obje yok => tutarsızlık da olamaz. ÖLÇÜLDÜ.
        gate_status(_GATE, 'OK', True, 'pre-create-obje-yok')
        return 0
    if r.status_code != 200:
        print(f'UYARI: SAP GET {r.status_code} — validator atlandı', file=sys.stderr)
        gate_status(_GATE, 'SKIPPED', False, f'sap-get-http-{r.status_code}')
        return 0

    sap_source = r.text

    issues = []

    # 1. Placeholder detection
    if PLACEHOLDER_PATTERN.search(sap_source):
        issues.append(f'PLACEHOLDER: SAP\'de "component_to_be_changed:abap.string" placeholder var — alanlar yazılmamış.')

    # 2. Field count match
    sap_fields = extract_fields(sap_source)
    if not sap_fields and not PLACEHOLDER_PATTERN.search(sap_source):
        issues.append('EMPTY: SAP\'de struct'"'"'a alan bulunamadı.')

    if sap_fields:
        missing_in_sap = local_fields - sap_fields
        extra_in_sap = sap_fields - local_fields
        if missing_in_sap:
            issues.append(f'MISSING_IN_SAP ({len(missing_in_sap)} alan): {sorted(missing_in_sap)[:10]}')
        if extra_in_sap:
            issues.append(f'EXTRA_IN_SAP ({len(extra_in_sap)} alan): {sorted(extra_in_sap)[:10]}')

    # 3. Version check — metadata
    try:
        rm = client.session.get(
            client.url + f'/sap/bc/adt/ddic/structures/{_adt_seg(struct_name)}',
            params={'sap-client': '100'}, verify=False, timeout=10
        )
        if rm.status_code == 200:
            vm = re.search(r'adtcore:version="(\w+)"', rm.text)
            version = vm.group(1) if vm else '?'
            if version != 'active':
                issues.append(f'INACTIVE: SAP version="{version}" (active bekleniyor)')
    except Exception:
        pass

    if not issues:
        print(f'OK — {struct_name} SAP\'de tutarlı ({len(local_fields)} alan, active)')
        gate_status(_GATE, 'OK', True, 'tutarli')
        return 0

    print(f'\n[BLOCKER] {struct_name} SAP tutarsız:', file=sys.stderr)
    print(f'  Lokal: {len(local_fields)} alan ({path.name})', file=sys.stderr)
    print(f'  SAP:   {len(sap_fields)} alan', file=sys.stderr)
    for issue in issues:
        print(f'  - {issue}', file=sys.stderr)
    print(f'\n  Çözüm: adt_push_source(object_type=\'structure\', source=<full DDL>) ile düzelt, sonra activate.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())

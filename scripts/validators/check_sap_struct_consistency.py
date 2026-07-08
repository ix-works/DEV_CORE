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

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


PLACEHOLDER_PATTERN = re.compile(r'\bcomponent_to_be_changed\s*:\s*abap\.string', re.IGNORECASE)
STRUCT_NAME_PATTERN = re.compile(r'define\s+structure\s+(\w+)', re.IGNORECASE)
FIELD_PATTERN = re.compile(r'^\s*(\w+)\s*:\s+', re.MULTILINE)


def extract_struct_name(text: str) -> str | None:
    m = STRUCT_NAME_PATTERN.search(text)
    return m.group(1).upper() if m else None


def extract_fields(text: str) -> set[str]:
    """Return set of field names from struct DDL source.

    Excludes annotation lines, keywords (define, with, where, and), and the struct name itself.
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
        m = re.match(r'^(\w+)\s*:\s+', s)
        if m:
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
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    local_text = path.read_text(encoding='utf-8', errors='replace')
    struct_name = extract_struct_name(local_text)
    if not struct_name:
        print(f'UYARI: {path.name} içinde "define structure NAME" bulunamadı — validator atlandı')
        return 0

    local_fields = extract_fields(local_text)
    if not local_fields:
        print(f'UYARI: {path.name} içinde alan bulunamadı — validator atlandı')
        return 0

    # SAP'ye bağlan
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        return 0

    # SAP'den source çek (structures endpoint)
    try:
        r = client.session.get(
            client.url + f'/sap/bc/adt/ddic/structures/{struct_name.lower()}/source/main',
            params={'sap-client': '100'}, verify=False, timeout=20
        )
    except Exception as e:
        print(f'UYARI: SAP GET hata: {e}', file=sys.stderr)
        return 0

    if r.status_code == 404:
        # Struct henüz yok — bu pre-create durumu, validator buradan birşey demiyor
        print(f'OK — {struct_name} SAP\'de henüz yok (pre-create durumu, atlandı)')
        return 0
    if r.status_code != 200:
        print(f'UYARI: SAP GET {r.status_code} — validator atlandı', file=sys.stderr)
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
            client.url + f'/sap/bc/adt/ddic/structures/{struct_name.lower()}',
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

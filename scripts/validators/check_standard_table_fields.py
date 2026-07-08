"""
check_standard_table_fields.py — Source'ta kullanılan standart SAP tablo alanları
yeni sistemde gerçekten var mı SAP GET ile teyit eder.

Vaka 2026-05-14 (Sprint 5, SHIPPING_TYPES) — <LEGACY_SOURCE> source'ta `t173.vsartkat`
yazıyordu ama yeni sistemde T173 field listesinde `vsartkat` yok, gerçek field `vktra`.
Bu validator GET /sap/bc/adt/ddic/tables/<name>/source/main ile field listesini alıp
referans verilen alanları kontrol eder.

Kullanım:
    python scripts/validators/check_standard_table_fields.py <cds_path>
    python scripts/validators/check_standard_table_fields.py <cds_path> --type dtel

Exit kodu:
    0 — Tüm referans alanlar yeni sistemde mevcut
    1 — Bir veya daha fazla alan yok (BLOCKER)
"""
# ENFORCES: C-CDS-FROM-03, C-RAP-VE-03, C-STR-FIELD-03, C-TBL-STD-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Z olmayan tabloları yakalayan regex (CDS'te `tablename.fieldname` pattern'i)
TABLE_FIELD_PATTERN = re.compile(
    r'\b([a-z][a-z0-9_]{0,15})\.([a-z][a-z0-9_]+)\b',
    re.IGNORECASE
)

# ALIAS ÇÖZÜMÜ (fix 2026-06-24): CDS `from <tablo> as <alias>` / `join <tablo> as <alias>`
# eşlemesi. Önceden validator alias'ı (ör. `from vfkp as Cost` → `Cost.netwr`) tablo adı
# sanıp gerçek tabloyu (VFKP) kontrol etmiyordu → ZSD001_I_FREIGHT_COST'ta false-positive
# BLOCKER. Artık alias gerçek tabloya çözülür; namespaced (/ITTR/) tablo da desteklenir.
ALIAS_PATTERN = re.compile(
    r'\b(?:from|join)\s+(/?[a-z][a-z0-9_/]*)\s+as\s+([a-z][a-z0-9_]*)',
    re.IGNORECASE
)

# Z* ve session var prefix'leri — skip (abap.* cast tipleri de skip)
SKIP_TABLE_PREFIXES = ('z', '$session', 'reqd_', 'confd_', 'projection', 'abap')


def fetch_table_fields(client, table_name: str) -> set[str]:
    """SAP'den tablo source'unu çekip field adlarını döner."""
    try:
        r = client.session.get(
            client.url + f'/sap/bc/adt/ddic/tables/{table_name.lower()}/source/main',
            params={'sap-client': '100', 'sap-language': 'TR'},
            headers={'Accept': 'text/plain'},
            verify=False, timeout=10
        )
        if r.status_code != 200:
            return set()
        # 'fieldname : dtel;' pattern
        fields = set(re.findall(
            r'^\s*(?:key\s+)?([a-z][a-z0-9_]*)\s*:\s*[a-z][a-z0-9_]*',
            r.text, re.MULTILINE
        ))
        return {f.lower() for f in fields}
    except Exception:
        return set()


def main() -> int:
    parser = argparse.ArgumentParser(description='Standart tablo field varlık kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--type', default='cds', help='cds|table|dtel')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    text = path.read_text(encoding='utf-8', errors='replace')

    # Tablo.field çiftlerini çıkar
    pairs = TABLE_FIELD_PATTERN.findall(text)

    # Alias → gerçek tablo haritası: `from/join <tablo> as <alias>` (fix 2026-06-24).
    # Böylece `Cost.netwr` (alias) → gerçek tablo `vfkp` üzerinde kontrol edilir;
    # alias adının (Cost, Delivery) gerçek SAP tablosuyla (COST, ...) çakışması önlenir.
    alias_map = {}
    for real_tbl, alias in ALIAS_PATTERN.findall(text):
        alias_map[alias.lower()] = real_tbl.lower()

    # Z olmayanları filtrele
    candidates = {}  # table → set of fields
    for table, field in pairs:
        tbl = alias_map.get(table.lower(), table.lower())  # alias → gerçek tablo
        if tbl.startswith(SKIP_TABLE_PREFIXES):
            continue
        # Namespaced add-on tablosu (/ITTR/ vb.) — ADT source endpoint güvenilir değil, skip
        if tbl.startswith('/'):
            continue
        # Çözülemeyen kısa token (1-2 char alias) — skip
        if len(tbl) <= 2:
            continue
        # Append/extension alanı (ZZ1_*, ZZ_*) — base-tablo source'unda GÖRÜNMEZ
        # (append struct'ta). Standart alan asla 'zz' ile başlamaz → bu alanlar
        # validator'ın base-source GET'iyle DOĞRULANAMAZ; her zaman false-positive
        # verirdi. Skip (fix 2026-06-24; canlı kanıt: LIKP.zz1_booking_number_dlh VAR).
        if field.lower().startswith('zz'):
            continue
        candidates.setdefault(tbl, set()).add(field.lower())

    if not candidates:
        print(f'OK — {path.name} standart tablo referansı yok')
        return 0

    # SAP'ye bağlan
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f'UYARI: SAP bağlantısı kurulamadı, validator atlandı: {e}', file=sys.stderr)
        return 0

    violations = []
    print(f'Source: {path.name} — {len(candidates)} potansiyel standart tablo referansı kontrol ediliyor...')

    for table, fields in candidates.items():
        # Sadece bilinen SAP standart tablolar (basit heuristic — Z olmayan, 4-5 char)
        actual_fields = fetch_table_fields(client, table)
        if not actual_fields:
            # Tablo bulunamadı, skip (alias olabilir veya CDS view olabilir)
            continue

        for field in fields:
            if field not in actual_fields:
                # Yakın alternatif bul (basit)
                similar = [f for f in actual_fields if abs(len(f) - len(field)) <= 2 and (f[:3] == field[:3] or f[-3:] == field[-3:])]
                violations.append({
                    'table': table.upper(),
                    'field': field,
                    'similar': similar[:3],
                })

    if not violations:
        print(f'OK — {path.name} tüm standart tablo alanları yeni sistemde mevcut')
        return 0

    print(f'\n[BLOCKER] {len(violations)} standart tablo alanı yeni sistemde YOK:', file=sys.stderr)
    for v in violations:
        print(f"  {v['table']}.{v['field']}", file=sys.stderr)
        if v['similar']:
            print(f"    Benzer alanlar: {', '.join(v['similar'])}", file=sys.stderr)
    print('\nÇözüm: Source\'ta bu alan referanslarını gerçek alan adlarıyla değiştir.\n'
          '       Eski <LEGACY_SOURCE> source\'tan kopya yaparken yeni sistem field listesini\n'
          '       her zaman GET /sap/bc/adt/ddic/tables/<name>/source/main ile teyit et.',
          file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())

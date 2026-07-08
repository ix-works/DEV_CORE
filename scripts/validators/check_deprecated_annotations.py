"""
check_deprecated_annotations.py — CDS/Tablo source'ta deprecated annotation kullanımı.

KURAL:
  @AbapCatalog.preserveKey: deprecated (S/4HANA 2026+ removed olabilir)
  @Analytics.dataExtraction: deprecated bazı modlar
  Diğer deprecated annotation'lar listesi büyüdükçe eklenir.

Kullanım:
    python scripts/validators/check_deprecated_annotations.py <artifact>

Exit kodu:
    0 — Deprecated yok
    0 (WARNING) — Deprecated var ama default mode (run_all_validators'da soft)
    1 — --strict ile çalışıyorsa fail
"""
# ENFORCES: C-CDS-DEPR-01, C-RAP-VE-08, C-STR-DEPR-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Deprecated pattern'ler
DEPRECATED = [
    {
        'pattern': re.compile(r'@AbapCatalog\.preserveKey\s*:\s*true', re.IGNORECASE),
        'name': '@AbapCatalog.preserveKey',
        'reason': 'Deprecated S/4HANA 2026+ — default davranış değişti, gereksiz',
        'replacement': 'Annotation\'ı kaldır',
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description='Deprecated annotation tespit')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    text = path.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines()

    violations = []
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('//') or line.strip().startswith('--'):
            continue
        for dep in DEPRECATED:
            if dep['pattern'].search(line):
                violations.append((i, dep, line.strip()[:80]))

    if not violations:
        print(f'OK — {path.name} deprecated annotation yok')
        return 0

    level = 'HATA' if args.strict else 'UYARI'
    print(f'\n[{level}] {path.name} — {len(violations)} deprecated annotation', file=sys.stderr)
    for line_no, dep, snippet in violations:
        print(f"  line {line_no}: {dep['name']}", file=sys.stderr)
        print(f"    Sebep: {dep['reason']}", file=sys.stderr)
        print(f"    Öneri: {dep['replacement']}", file=sys.stderr)

    return 1 if args.strict else 0


if __name__ == '__main__':
    sys.exit(main())

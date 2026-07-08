"""
check_window_function_compatibility.py — CDS source'ta window function (OVER PARTITION BY)
kullanımı tespit eder. Bu SAP sistemi (NetWeaver < 7.55) window function'ı desteklemiyor.

Vaka 2026-05-14 (Sprint 3, ORDER_SCHED_LINES) — `sum(...) over (partition by ...)` yazıldı,
aktivasyonda 'Line 3: Syntax error in "over"' hatası. ABAP'a kaydırıldı.

Kullanım:
    python scripts/validators/check_window_function_compatibility.py <cds_path>

Exit kodu:
    0 — Window function yok, güvenli
    1 — Window function tespit edildi (BLOCKER)
"""
# ENFORCES: C-CDS-WIN-01, C-RAP-VE-06  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Window function pattern'leri (case-insensitive)
PATTERNS = [
    re.compile(r'\bover\s*\(\s*partition\s+by\b', re.IGNORECASE),
    re.compile(r'\bover\s*\(\s*order\s+by\b', re.IGNORECASE),
    re.compile(r'\brow_number\s*\(\s*\)\s*over\b', re.IGNORECASE),
    re.compile(r'\brank\s*\(\s*\)\s*over\b', re.IGNORECASE),
    re.compile(r'\bdense_rank\s*\(\s*\)\s*over\b', re.IGNORECASE),
    re.compile(r'\blag\s*\(.*\)\s*over\b', re.IGNORECASE),
    re.compile(r'\blead\s*\(.*\)\s*over\b', re.IGNORECASE),
]


def main() -> int:
    parser = argparse.ArgumentParser(description='CDS window function tespit')
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
        # Yorumları atla
        if line.strip().startswith('//') or line.strip().startswith('--'):
            continue
        for pat in PATTERNS:
            if pat.search(line):
                violations.append((i, line.strip()[:80]))
                break

    if not violations:
        print(f'OK — {path.name} window function kullanımı yok')
        return 0

    print(f'\n[BLOCKER] {path.name} — {len(violations)} window function ihlali', file=sys.stderr)
    for line_no, snippet in violations:
        print(f"  line {line_no}: {snippet}", file=sys.stderr)
    print(
        '\nBu sistem ABAP CDS window function desteklemiyor.\n'
        'Alternatif: FIFO/aggregate logic ABAP class içinde yapılır.\n'
        'Bkz. ERP/SD/ZSD001_CLC/programs/FIFO_ORDER_ALLOCATION.md',
        file=sys.stderr
    )
    return 1


if __name__ == '__main__':
    sys.exit(main())

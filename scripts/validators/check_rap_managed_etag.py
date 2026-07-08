"""
check_rap_managed_etag.py — Managed RAP BDEF'te optimistic locking (etag) ve
lock master eksikliğini SAP'ye yazmadan yakalar.

Kaynak (gap-analysis #16, SAP topluluğu RAP-demo anekdotu):
  Claude managed RAP demo'da LAST_CHANGED_AT / etag alanını eklemeyi unutunca
  uygulama çalışmadı (managed senaryoda kilitleme/concurrency için hayati).

Kural (managed + yazma operasyonu varsa):
  - Root behavior `lock master` tanımlamalı (kilit).            → eksikse BLOCKER
  - `etag master <field>` veya `etag dependent` olmalı (optimistic concurrency).
                                                                 → eksikse BLOCKER
  - İPUCU: etag master alanı CDS root view'da
    `@Semantics.systemDateTime.lastChangedAt: true` olmalı (BDEF dışı; WARNING hatırlatma).

Kapsam dışı (OK): unmanaged (released BAPI/EML), `query`/read-only behavior, .bdef olmayan.

Kullanım:
    python scripts/validators/check_rap_managed_etag.py <bdef_path>

Exit kodu: 0 temiz / 1 BLOCKER
"""
import argparse
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

MANAGED_RE = re.compile(r'\bmanaged\b\s+implementation', re.IGNORECASE)
UNMANAGED_RE = re.compile(r'\bunmanaged\b\s+implementation', re.IGNORECASE)
DEFINE_BEHAVIOR_RE = re.compile(r'\bdefine\s+behavior\s+for\s+(\w+)', re.IGNORECASE)
WRITE_OP_RE = re.compile(r'\b(create|update|delete)\b', re.IGNORECASE)
LOCK_MASTER_RE = re.compile(r'\block\s+master\b', re.IGNORECASE)
LOCK_DEPENDENT_RE = re.compile(r'\block\s+dependent\b', re.IGNORECASE)
ETAG_RE = re.compile(r'\betag\s+(master|dependent)\b', re.IGNORECASE)
LASTCHANGED_SEMANTICS_RE = re.compile(
    r'@Semantics\.systemDateTime\.lastChangedAt', re.IGNORECASE)


def _strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('//'):
            continue
        out.append(line)
    return '\n'.join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Managed RAP BDEF etag/lock master kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    raw = path.read_text(encoding='utf-8', errors='replace')
    text = _strip_comments(raw)

    if not DEFINE_BEHAVIOR_RE.search(text):
        print(f'OK — {path.name} behavior definition değil, kapsam dışı')
        return 0
    if UNMANAGED_RE.search(text) and not MANAGED_RE.search(text):
        print(f'OK — {path.name} unmanaged (released BAPI/EML), etag kapsamı dışı')
        return 0
    if not MANAGED_RE.search(text):
        print(f'OK — {path.name} managed implementation değil, kapsam dışı')
        return 0
    if not WRITE_OP_RE.search(text):
        print(f'OK — {path.name} yazma operasyonu (create/update/delete) yok, '
              f'etag/lock gerekmez')
        return 0

    violations = []
    warnings = []

    if not LOCK_MASTER_RE.search(text):
        # En az bir root 'lock master' olmalı
        violations.append(
            "Root behavior 'lock master' tanımlamıyor — managed senaryoda kilit zorunlu "
            "(child'lar 'lock dependent by _assoc').")

    if not ETAG_RE.search(text):
        violations.append(
            "'etag master <field>' (veya child için 'etag dependent') YOK — optimistic "
            "concurrency için zorunlu. Anekdot: LAST_CHANGED_AT/etag unutulunca managed "
            "RAP çalışmaz. Root'a 'etag master <LastChangedField>;' ekle.")

    if ETAG_RE.search(text) and not LASTCHANGED_SEMANTICS_RE.search(text):
        warnings.append(
            "BDEF'te etag var ama bu dosyada @Semantics.systemDateTime.lastChangedAt "
            "görülmedi — etag-master alanının CDS ROOT view'da "
            "@Semantics.systemDateTime.lastChangedAt:true (+ created/lastChanged admin "
            "alanları) olduğundan emin ol (BDEF dışı kontrol).")

    if not violations:
        msg = f'OK — {path.name} managed RAP etag/lock temiz'
        if warnings:
            print(msg)
            for w in warnings:
                print(f'  [WARNING] {w}')
        else:
            print(msg)
        return 0

    print(f'\n[BLOCKER] {path.name} — {len(violations)} managed-RAP etag/lock ihlali '
          f'(standards/05 §lock; ADR 0006)', file=sys.stderr)
    for v in violations:
        print(f'  [BLOCKER] {v}', file=sys.stderr)
    for w in warnings:
        print(f'  [WARNING] {w}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())

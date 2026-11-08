"""
check_rap_readonly_consumption.py — RAP read-only consumption/interface
katmanı iki klasik aktivasyon hatasını SAP'ye yazmadan yakalar.

Vaka 2026-05-19 (R2 CONTAINER_REPORT, T1/T10 — adt-rap.md §32.6k):
  A) `define view entity` (projeksiyon DEĞİL) gövdesinde join/base
     olarak `Z<MOD><nnn>_C_*` (consumption projection) kullanımı →
     aktivasyon: "Projection Views are not allowed as base object
     for this entity type."
  B) Adı `Z<MOD><nnn>_C_*` + içerik `as projection on` ama paket altında
     bu entity'i referanslayan hiç `.bdef` yok → aktivasyon:
     "Transactional Projection View must be part of a business object."
     (read-only raporda C_ katmanı `as select from` olmalı.)

Kullanım:
    python scripts/validators/check_rap_readonly_consumption.py <cds_path>

Exit kodu:
    0 — Temiz
    0 + `IX-GATE-STATUS … measured=false reason=ad-cozulemedi` — `define view entity` VAR ama
        entity adı çözülemedi (DEV_CORE #402 K2; ör. namespace'li ad) ⇒ ÖLÇÜLEMEDİ, "kapsam
        dışı" DEĞİL. run_review bunu SKIP sayar (bu gate BLOCKER şiddetinde ⇒ verdict BLOCKER).
    1 — İhlal (BLOCKER)

BDEF araması (Kural B): düz `*.bdef` + abapGit `*.bdef.asbdef` (#402 EK-2).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gate_status import gate_status  # noqa: E402  — IX-GATE-STATUS üretici ucu (#402 K2)

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ENTITY_RE = re.compile(
    r'\bdefine\s+(?:root\s+)?view\s+entity\s+(\w+)', re.IGNORECASE)
# Tür anahtar sözcüğü (adsız): ENTITY_RE eşleşmeyip bu eşleşirse ad ÇÖZÜLEMEMİŞTİR (#402 K2).
ENTITY_KW_RE = re.compile(r'\bdefine\s+(?:root\s+)?view\s+entity\b', re.IGNORECASE)
_GATE = Path(__file__).stem
PROJECTION_RE = re.compile(r'\bas\s+projection\s+on\b', re.IGNORECASE)
SELECT_FROM_RE = re.compile(r'\bas\s+select\s+from\b', re.IGNORECASE)
# Modül-bağımsız: Z<MOD><nnn>_C_* (MOD=SD/MM/FI/CO/PP/QM/PM/EWM... 2-4 harf)
C_NAME_RE = re.compile(r'\bZ[A-Z]{2,4}\d{3}_C_\w+', re.IGNORECASE)
C_ENTITY_NAME_RE = re.compile(r'^Z[A-Z]{2,4}\d{3}_C_\w+$', re.IGNORECASE)
JOIN_OR_BASE_RE = re.compile(
    r'\b(?:join|from)\s+(Z[A-Z]{2,4}\d{3}_C_\w+)', re.IGNORECASE)


def _strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('//') or s.startswith('--'):
            continue
        out.append(line)
    return '\n'.join(out)


def _package_root(path: Path) -> Path:
    # .../<source_root>/<MOD>/<PKG>/cds/X.cds → <PKG>
    for parent in path.parents:
        if (parent / '.rules.md').exists():
            return parent
    return path.parent.parent if len(path.parents) >= 2 else path.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description='RAP read-only consumption/interface katman kontrolü')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true',
                       help='(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ, run_all --strict kazara terfi ettirmesin; ADR 0019 §54)')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    raw = path.read_text(encoding='utf-8', errors='replace')
    text = _strip_comments(raw)

    em = ENTITY_RE.search(text)
    if not em:
        if ENTITY_KW_RE.search(text):
            # DEV_CORE #402 (K2): `define view entity` VAR ama ad çözülemedi (ör. namespace'li
            # `/NSPC/...`). Eski hâl "kapsam dışı" + rc 0 idi — Kural A/B hiç koşmadan temiz
            # görünüyordu. ÖLÇÜLEMEDİ = rc 0 + `measured=false` (`_gate_status` sözleşmesi);
            # run_review bunu SKIP sayar ve BLOCKER şiddetiyle verdict'e katar.
            print(f'ÖLÇÜLEMEDİ — {path.name} `define view entity` içeriyor ama entity adı '
                  f'çözülemedi → Kural A/B KOŞMADI; "temiz" anlamına GELMEZ.')
            gate_status(_GATE, 'SKIPPED', False, 'ad-cozulemedi')
            return 0
        print(f'OK — {path.name} view entity değil, kapsam dışı')
        return 0
    entity = em.group(1)
    is_projection = bool(PROJECTION_RE.search(text))
    is_select = bool(SELECT_FROM_RE.search(text))

    violations = []

    # Rule A — düz view entity, base/join'de C_ projection
    if is_select and not is_projection:
        for m in JOIN_OR_BASE_RE.finditer(text):
            violations.append(
                ('A', m.group(1),
                 f"'{m.group(1)}' bir consumption projection (Z<MOD><nnn>_C_); "
                 f"düz 'define view entity' base/join kaynağı OLAMAZ. "
                 f"Interface (Z<MOD><nnn>_I_*) view'a geç."))

    # Rule B — C_ adlı + 'as projection on' ama referanslayan .bdef yok
    if is_projection and C_ENTITY_NAME_RE.match(entity):
        root = _package_root(path)
        has_bdef = False
        # #402 EK-2: abapGit yerleşimi BDEF'i `X.bdef.asbdef` adıyla tutar; yalnız `*.bdef`
        # aransaydı her `_C_` projeksiyonu "referanslayan .bdef yok" diye SAHTE BLOCKER alırdı.
        # Ev deseni: checklist_check (`*.bdef` + `*.asbdef`).
        for bdef in (*root.rglob('*.bdef'), *root.rglob('*.asbdef')):
            try:
                btxt = bdef.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            if re.search(rf'\b{re.escape(entity)}\b', btxt, re.IGNORECASE):
                has_bdef = True
                break
        if not has_bdef:
            violations.append(
                ('B', entity,
                 f"'{entity}' 'as projection on' kullanıyor (transactional "
                 f"projection = BO/BDEF zorunlu) ama paket altında onu "
                 f"referanslayan .bdef yok. Read-only ise 'as select from' "
                 f"düz consumption view entity yap."))

    if not violations:
        print(f'OK — {path.name} RAP read-only consumption/interface temiz')
        return 0

    print(f'\n[BLOCKER] {path.name} — {len(violations)} ihlal '
          f'(adt-rap.md §32.6k)', file=sys.stderr)
    for rule, obj, msg in violations:
        print(f"  [Rule {rule}] {msg}", file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())

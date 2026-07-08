"""
check_reuse_gate.py — CBO brownfield reuse gate (gap-analysis #3).

Yeni bir Z obje (CDS view entity / DDIC) yaratmadan önce, AYNI adın repo'da
başka bir yerde zaten tanımlı olup olmadığını kontrol eder. Amaç: duplicate
obje yaratımını ve "var olanı tekrar üretme" hatasını SAP'ye yazmadan yakalamak.

Kapsam (deterministik, repo-local):
  - CDS/RAP view entity adları: <source_root>/**/*.{cds,asddls,ddls} içinde
    `define [root] view entity <NAME>`.
  - Generic ortak master objeler (ZSD000_I_*) — reuse hatırlatması (ADR 0009).

NOT: Tam DDIC envanteri (domain/dtel/struct) SAP'de yaşar; tam reuse-gate için
canlı `adt_search_objects` gerekir (gelecek: SAP-aware mod). Bu sürüm repo-local
duplicate'i ve ortak-VH reuse'unu yakalar — en sık vakalar.

Severity: WARNING (false-positive riski; coordinator karar verir).

Kullanım:
    python scripts/validators/check_reuse_gate.py <artifact_path>

Exit: 0 temiz / 0 (WARNING stdout) — bu validator BLOCKER üretmez.
"""
# ENFORCES: DE-REUSE-02  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ENTITY_RE = re.compile(
    r'\bdefine\s+(?:root\s+)?view\s+entity\s+(\w+)', re.IGNORECASE)
# Ortak generic master objeler (ADR 0009 — local kopya yaratma, expose+assoc kullan)
GENERIC_MASTERS = (
    'ZSD000_I_BPNAME', 'ZSD000_I_VKORGVH', 'ZSD000_I_SHIPTYPEVH',
    'ZSD000_I_PORTVH',
)
SCAN_GLOBS = ('**/*.cds', '**/*.asddls', '**/*.ddls')


def _repo_root(path: Path) -> Path:
    for parent in path.parents:
        if (parent / 'CLAUDE.md').exists() or (parent / '.git').exists():
            return parent
    # <source_root>/<MOD>/<PKG>/... → 3 üst
    return path.parents[min(3, len(path.parents) - 1)]


def _inventory(repo: Path, exclude: Path) -> dict[str, Path]:
    """Repo'daki tüm CDS view entity adları → tanımlandığı dosya."""
    inv: dict[str, Path] = {}
    erp = repo / SOURCE_ROOT_NAME
    base = erp if erp.exists() else repo
    for pat in SCAN_GLOBS:
        for f in base.glob(pat):
            if f.resolve() == exclude.resolve():
                continue
            try:
                txt = f.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            for m in ENTITY_RE.finditer(txt):
                inv.setdefault(m.group(1).upper(), f)
    return inv


def main() -> int:
    parser = argparse.ArgumentParser(description='CBO reuse gate (repo-local duplicate)')
    parser.add_argument('artifact')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    path = Path(args.artifact)
    if not path.exists():
        print(f'HATA: {path} bulunamadı', file=sys.stderr)
        return 1

    text = path.read_text(encoding='utf-8', errors='replace')
    m = ENTITY_RE.search(text)
    if not m:
        print(f'OK — {path.name} view entity değil, reuse-gate kapsamı dışı')
        return 0
    new_name = m.group(1).upper()

    repo = _repo_root(path)
    inv = _inventory(repo, exclude=path)
    warnings = []

    # 1. Aynı ad repo'da başka dosyada → güçlü duplicate uyarısı
    if new_name in inv:
        warnings.append(
            f"'{new_name}' ZATEN tanımlı: {inv[new_name].relative_to(repo)}. "
            f"Yeniden yaratma yerine mevcut objeyi kullan/incele (duplicate riski).")

    # 1b. SAP CBO envanteri (build_cbo_inventory.py → cbo-inventory.json) → repo'da
    # olmasa bile SAP'de var mı? (tüm obje tipleri, repo-local CDS taramasının ötesi)
    inv_path = repo / 'governance' / 'cbo-inventory.json'
    if inv_path.exists() and new_name not in inv:
        try:
            import json
            sap_objs = json.loads(inv_path.read_text(encoding='utf-8')).get('objects', {})
        except Exception:
            sap_objs = {}
        meta = sap_objs.get(new_name)
        if meta:
            warnings.append(
                f"'{new_name}' SAP'de ZATEN var (cbo-inventory: paket {meta.get('package')}, "
                f"type {meta.get('type')}). Yeniden yaratma — reuse/incele. "
                f"(Envanteri güncelle: python scripts/build_cbo_inventory.py)")

    # 2. Master/VH gibi görünen yeni obje → ortak ZSD000_I_* reuse hatırlatması (ADR 0009)
    if new_name.startswith('ZSD') and ('_I_' in new_name) and any(
            k in new_name for k in ('BPNAME', 'VKORG', 'SHIPTYPE', 'PORT', 'NAME')):
        warnings.append(
            f"'{new_name}' bir master/VH gibi görünüyor — ortak ZSD000_I_* "
            f"({', '.join(GENERIC_MASTERS)}) zaten var mı kontrol et; varsa "
            f"local kopya yaratma, expose+assoc kullan (ADR 0009).")

    if not warnings:
        print(f'OK — {path.name} ({new_name}) repo-local duplicate yok')
        return 0

    print(f'[WARNING] {path.name} — reuse-gate {len(warnings)} uyarı (gap-analysis #3, ADR 0009):')
    for w in warnings:
        print(f'  [WARNING] {w}')
    # WARNING-only validator: exit 0 (reviewer severity'yi WARNING olarak işler)
    return 0


if __name__ == '__main__':
    sys.exit(main())

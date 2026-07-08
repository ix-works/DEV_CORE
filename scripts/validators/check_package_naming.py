"""
check_package_naming.py — Her paketin `.rules.md`'sindeki regex'lere göre dosya adlarını doğrular.

Mantık:
1. `.rules.md` içindeki "Naming" tablosundan obje tipi → regex eşlemesini okur
2. Paket altındaki alt klasörlerdeki dosya adlarını regex'le karşılaştırır
3. Paket root'undaki `.txt` dosyaları muaf (legacy/draft konvansiyonu)
4. Standart `_CLC` paketlerindeki obje klasörleri: cds/, classes/, programs/, structures/, tables/, functions/

Kullanım:
    python scripts/validators/check_package_naming.py
    python scripts/validators/check_package_naming.py --package ZSD001_CLC

Exit kodu:
    0 — Tüm dosya adları paket regex'lerine uyumlu
    1 — Bir veya birden çok ihlal var (liste stderr'de)
"""
# ENFORCES: C-CDS-NAME-01, C-RAP-NAME-01, C-STR-NAME-01, C-TBL-NAME-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import project_root,  SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Obje tipi → klasör adları eşlemesi (.rules.md "Obje Tipi" satırı → klasör)
TYPE_TO_FOLDERS = {
    "program": ["programs"],
    "include": ["programs"],
    "class": ["classes"],
    "interface": ["classes"],
    "function module": ["functions"],
    "function group": ["functions"],
    "cds": ["cds"],
    "cds root view": ["cds"],
    "cds interface view": ["cds"],
    "ddl source": ["cds"],
    "ddl source (cds)": ["cds"],
    "structure": ["structures"],
    "data element": [],  # DDIC objelerinin lokal kopyası nadir
    "domain": [],
    "tablo": ["tables"],
    "table": ["tables"],
    "table type": [],
    "lock object": [],
    "message class": [],
}

# Paket root'undaki dosyalar için muafiyet (legacy/draft konvansiyonu)
ROOT_EXEMPT_EXTENSIONS = {".txt", ".md"}  # spec/draft dosyaları regex'ten muaf

# Klasörler bazında dosya uzantı filtresi
FOLDER_FILE_GLOBS = {
    "cds": ["*.cds"],  # .md spec'leri muaf
    "classes": ["*.abap"],
    "programs": ["*.abap"],
    "structures": ["*.ddls.asddls", "*.abap"],
    "tables": ["*.abap", "*.ddls.asddls"],
    "functions": ["*.abap"],
}


def parse_rules_md(rules_path: Path) -> list[tuple[str, str]]:
    """`.rules.md`'den (obje_tipi, regex) listesini çıkarır."""
    if not rules_path.exists():
        return []

    rules = []
    table_started = False
    text = rules_path.read_text(encoding="utf-8", errors="replace")

    for line in text.splitlines():
        line = line.strip()
        # Naming bölümünü ve tablosunu yakala
        if line.startswith("## Naming"):
            table_started = True
            continue
        if table_started and line.startswith("## "):
            # Yeni section başladı, tabloyu bırak
            break
        if table_started and line.startswith("|") and "|" in line[1:]:
            # Tablo satırı. Regex hücresi `\|` (escape edilmiş pipe) içerebilir —
            # bu bir kolon ayıracı DEĞİL (ör. alternation `(A\|B)`). Split etmeden
            # önce sentinel ile koru, sonra geri yükle (aksi halde regex hücresi
            # parçalanır ve satır sessizce düşer → naming kuralı kaybolur).
            _SENT = "\x00PIPE\x00"
            cells = [c.strip().replace(_SENT, "|")
                     for c in line.replace("\\|", _SENT).split("|")[1:-1]]
            if len(cells) >= 3 and cells[2].startswith("`") and cells[2].endswith("`"):
                obj_type = cells[0].strip().lower()
                regex_str = cells[2].strip("`")
                rules.append((obj_type, regex_str))

    return rules


def validate_package(pkg_dir: Path, verbose: bool = False) -> list[str]:
    """Bir paket için tüm dosya adlarını doğrular, ihlal listesini döner."""
    violations = []
    rules_path = pkg_dir / ".rules.md"
    rules = parse_rules_md(rules_path)

    if not rules:
        violations.append(f"{pkg_dir.name}: .rules.md'den naming kuralı çıkarılamadı")
        return violations

    # Obje tipi → regex sözlüğü (lowercase key)
    type_regex = {t: re.compile(r) for t, r in rules}

    if verbose:
        print(f"\n=== {pkg_dir.name} ===")
        for t, r in rules:
            print(f"  {t} → {r}")

    # Her alt klasör için ilgili obje tipini bul, dosyaları doğrula
    for folder_name, file_globs in FOLDER_FILE_GLOBS.items():
        folder = pkg_dir / folder_name
        if not folder.exists():
            continue

        # Bu klasöre uygun obje tipini bul
        applicable_regexes = []
        for obj_type, regex in type_regex.items():
            for canonical_type, folders in TYPE_TO_FOLDERS.items():
                if canonical_type in obj_type and folder_name in folders:
                    applicable_regexes.append((obj_type, regex))
                    break

        if not applicable_regexes:
            continue  # Bu klasör için regex yok, atla

        # Dosyaları topla
        files = []
        for glob in file_globs:
            files.extend(folder.glob(glob))

        for f in files:
            # Uzantıyı kaldır, basename'i regex'le
            name = f.name
            # SAP ADT multi-part source konvansiyonu: <OBJE>.<kind>[.<sub>].<ext>
            # — obje adı her zaman ilk marker'dan önceki segment.
            #   class pool : .clas.abap / .clas.locals_imp.abap / .clas.testclasses.abap
            #   RAP behavior pool : .ccimp.abap (CCIMP) / .ccdef.abap (CCDEF) /
            #                       .ccmac.abap (CCMAC) — behavior class lokal include'ları
            #   BDEF : .bdef.abap
            #   program : .prog.abap   function module : .func.abap   FUGR : .fugr.abap
            _sap_markers = (".clas.", ".ccimp.", ".ccdef.", ".ccmac.", ".bdef.",
                            ".intf.", ".prog.", ".func.", ".fugr.")
            _hit = next((m for m in _sap_markers if m in name), None)
            if _hit:
                name = name.split(_hit)[0]
            else:
                for ext in (".ddls.asddls", ".abap", ".cds"):
                    if name.endswith(ext):
                        name = name[: -len(ext)]
                        break

            # En az bir regex eşleşmeli
            if not any(rx.match(name) for _, rx in applicable_regexes):
                violations.append(
                    f"{pkg_dir.name}/{folder_name}/{f.name}: "
                    f"hiçbir regex'le eşleşmiyor "
                    f"(denenenler: {', '.join(t for t, _ in applicable_regexes)})"
                )

    return violations


# Tooling scratch dizini artık .tmp/sap_scratch (ERP DIŞI, gitignored) — ZAI default'u
# KALDIRILDI (2026-06-18). <source_root>/ZAI ARTIK YASAK: belirirse bu check onu flag'ler
# (ZAI-resurgence guard). Başka scratch-modül yok → exclude kümesi BOŞ.
SCRATCH_MODULES: set = set()


def find_packages(erp_root: Path) -> list[Path]:
    """<source_root>/<MODULE>/<PKG>/ — modül seviyesi altındaki paketleri döner."""
    if not erp_root.exists():
        return []
    packages = []
    for module_dir in sorted(erp_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("."):
            continue
        if module_dir.name in SCRATCH_MODULES:
            continue
        for pkg in sorted(module_dir.iterdir()):
            if pkg.is_dir() and not pkg.name.startswith("."):
                packages.append(pkg)
    return packages


def find_package_by_name(erp_root: Path, pkg_name: str) -> Path | None:
    """Modülleri tarayarak paketi bulur."""
    for module_dir in erp_root.iterdir():
        if not module_dir.is_dir():
            continue
        candidate = module_dir / pkg_name
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Paket naming kurallarını doğrula")
    parser.add_argument("--source-root", default=SOURCE_ROOT_NAME, help="ERP root dizini")
    parser.add_argument("--package", default=None, help="Sadece bu paketi doğrula")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--strict", action="store_true", help="run_all_validators ile uyum için, no-op")
    args = parser.parse_args()

    _p = Path(args.source_root)
    erp_root = _p if _p.is_absolute() else (project_root() / _p)
    if args.package:
        pkg = find_package_by_name(erp_root, args.package)
        if pkg is None:
            print(f"HATA: {args.package} <source_root>/ altında bulunamadı", file=sys.stderr)
            return 1
        packages = [pkg]
    else:
        packages = find_packages(erp_root)

    all_violations = []
    for pkg in packages:
        if not pkg.exists():
            print(f"UYARI: {pkg} bulunamadı, atlanıyor", file=sys.stderr)
            continue
        violations = validate_package(pkg, verbose=args.verbose)
        all_violations.extend(violations)

    if all_violations:
        print("HATA — Naming ihlalleri:", file=sys.stderr)
        for v in all_violations:
            print(f"  {v}", file=sys.stderr)
        return 1

    print(f"OK — {len(packages)} paket, naming ihlali yok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

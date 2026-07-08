"""
check_object_in_correct_pkg.py — Bir paketin alt klasörlerindeki dosyaların prefix'i
paket adıyla uyumlu mu kontrol eder.

Örnek ihlal: <source_root>/ZSD003_CLC/cds/ZSD010_DDL_FOO.cds (yanlış paket)

Whitelist (.rules.md "Bilinen İstisnalar / Legacy" bölümünden okunur — gelecek):
- ZSD003_CLC: ZCL_ZSD_FITTINGS_* (Gateway namespace)
- ZSD009_CLC: ZFI_I_FITT_* (FI namespace, paket root'unda .txt olarak)

Kullanım:
    python scripts/validators/check_object_in_correct_pkg.py

Exit kodu:
    0 — Tüm dosyalar doğru pakette
    1 — Cross-package sızıntı tespit edildi
"""
# ENFORCES: C-RAP-PKG-01  (ADR 0019 coverage binding)
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Paket bazlı istisnalar (NTTDATA-onaylı veya legacy)
# B10/K12: paket-istisnalari PROJE-CONFIG'ten. project.yaml:
#   package_exceptions: ["ZSD001_CLC:^ZCL_SD001_", "ZSD001_CLC:^ZIF_SD001_"]
from utils.project_config import cfg as _cfg
PACKAGE_EXCEPTIONS: dict = {}
for _e in (_cfg('package_exceptions') or []):
    if ':' in str(_e):
        _pkg, _rx = str(_e).split(':', 1)
        PACKAGE_EXCEPTIONS.setdefault(_pkg.strip(), []).append(_rx.strip())

# Sadece bu klasörlerde obje adı doğrulanır (root'taki .md/.txt'ler ve docs/ muaf)
CHECK_FOLDERS = {"cds", "classes", "programs", "structures", "tables", "functions", "auth"}

# Tooling scratch dizini artık .tmp/sap_scratch (ERP DIŞI, gitignored) — ZAI default'u
# KALDIRILDI (2026-06-18). <source_root>/ZAI ARTIK YASAK: belirirse bu check onu flag'ler
# (ZAI-resurgence guard). Başka scratch-modül yok → exclude kümesi BOŞ.
SCRATCH_MODULES: set = set()


def get_pkg_prefix(pkg_name: str) -> str:
    """ZSD003_CLC → ZSD003"""
    return pkg_name.replace("_CLC", "")


def matches_package(filename: str, pkg_prefix: str, pkg_name: str) -> bool:
    """Dosya adı paket prefix'iyle veya istisna pattern'iyle eşleşiyor mu?"""
    base = filename.split(".")[0].upper()
    if base.startswith(pkg_prefix.upper() + "_") or base == pkg_prefix.upper():
        return True

    # Paket-spesifik istisnalar
    for pattern in PACKAGE_EXCEPTIONS.get(pkg_name, []):
        if re.match(pattern, base):
            return True

    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Obje paket sınır kontrolü")
    parser.add_argument("--source-root", default=SOURCE_ROOT_NAME, help="ERP root dizini")
    parser.add_argument("--strict", action="store_true", help="run_all_validators ile uyum için, no-op")
    args = parser.parse_args()

    erp_root = Path(args.erp_root)
    if not erp_root.exists():
        print(f"HATA: {erp_root} bulunamadı", file=sys.stderr)
        return 1

    violations = []
    # <source_root>/<MODULE>/<PKG>/ pattern'i
    packages = []
    for module_dir in sorted(erp_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("."):
            continue
        if module_dir.name in SCRATCH_MODULES:
            continue
        for pkg in sorted(module_dir.iterdir()):
            if pkg.is_dir() and not pkg.name.startswith("."):
                packages.append((module_dir.name, pkg))

    for module_name, pkg in packages:
        pkg_prefix = get_pkg_prefix(pkg.name)

        for folder_name in CHECK_FOLDERS:
            folder = pkg / folder_name
            if not folder.exists():
                continue

            for f in folder.rglob("*"):
                if not f.is_file():
                    continue
                # Sadece kod/obje uzantılarını kontrol et
                if not f.suffix.lower() in {".abap", ".cds", ".ddls", ".asddls", ".xml"}:
                    continue
                # .ddls.asddls çift uzantı
                if f.name.endswith(".ddls.asddls"):
                    pass

                if not matches_package(f.name, pkg_prefix, pkg.name):
                    violations.append(
                        f"{module_name}/{pkg.name}/{folder_name}/{f.name}: "
                        f"paket prefix'i '{pkg_prefix}' veya istisna pattern'iyle eşleşmiyor"
                    )

    if violations:
        print("HATA — Cross-package sızıntı:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1

    print(f"OK — {len(packages)} paketteki obje dosyaları doğru paket altında.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

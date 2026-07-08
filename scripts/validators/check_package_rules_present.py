"""
check_package_rules_present.py — Her <source_root>/<PKG>/ paketinde `.rules.md` var mı kontrol eder.

Kullanım:
    python scripts/validators/check_package_rules_present.py
    python scripts/validators/check_package_rules_present.py --source-root ERP

Exit kodu:
    0 — Tüm paketlerin .rules.md'si mevcut
    1 — Eksik paket var (liste stderr'de)

LESSONS_LEARNED #4 (Doc ≠ Enforcement) — kural varlığı kod ile zorunlu.
"""
import argparse
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Tooling scratch dizini artık .tmp/sap_scratch (ERP DIŞI, gitignored) — ZAI default'u
# KALDIRILDI (2026-06-18). <source_root>/ZAI ARTIK YASAK: belirirse bu check onu flag'ler
# (ZAI-resurgence guard). Başka scratch-modül yok → exclude kümesi BOŞ.
SCRATCH_MODULES: set = set()


def find_packages(erp_root: Path) -> list[Path]:
    """<source_root>/<MODULE>/<PKG>/ pattern'i — modül seviyesi altındaki paketleri döner."""
    if not erp_root.exists():
        return []
    packages = []
    for module_dir in sorted(erp_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("."):
            continue
        if module_dir.name in SCRATCH_MODULES:
            continue
        # Modül klasörünün içindeki paketleri topla
        for pkg in sorted(module_dir.iterdir()):
            if pkg.is_dir() and not pkg.name.startswith("."):
                packages.append(pkg)
    return packages


def main() -> int:
    parser = argparse.ArgumentParser(description=".rules.md varlık kontrolü")
    parser.add_argument("--source-root", default=SOURCE_ROOT_NAME, help="ERP root dizini (varsayılan: ERP)")
    parser.add_argument("--strict", action="store_true", help="run_all_validators ile uyum için, no-op")
    args = parser.parse_args()

    erp_root = Path(args.erp_root)
    packages = find_packages(erp_root)

    if not packages:
        print(f"UYARI: {erp_root}/ altında paket bulunamadı", file=sys.stderr)
        return 0

    missing = [pkg for pkg in packages if not (pkg / ".rules.md").exists()]

    if missing:
        print("HATA — .rules.md eksik paketler:", file=sys.stderr)
        for pkg in missing:
            print(f"  {pkg}/.rules.md", file=sys.stderr)
        print(
            f"\nÇözüm: python scripts/bootstrap_package.py <paket_adı> --module <MODÜL> "
            f"veya manuel olarak templates/new-package/.rules.md.tmpl'den kopyala.",
            file=sys.stderr,
        )
        return 1

    print(f"OK — {len(packages)} paketin tamamında .rules.md mevcut.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

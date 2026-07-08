"""
bootstrap_package.py — Yeni ERP paketi kurar (templates/new-package/'den).

Kullanım:
    python scripts/bootstrap_package.py ZSD001_CLC --title "Sevkiyat Optimizasyon" --module SD
    python scripts/bootstrap_package.py ZSD001_CLC --title "Demo" --owner <OWNER>

Yapılanlar:
1. ERP/<PKG_FULL>/ yaratır
2. templates/new-package/ içeriğini kopyalar
3. Placeholder'ları doldurur:
   - {PKG} → ZSD001
   - {PKG_FULL} → ZSD001_CLC
   - {TITLE} → "Sevkiyat Optimizasyon"
   - {MODULE} → SD
   - {DATE} → bugünün tarihi
   - {OWNER} → --owner veya git config user.name
4. folders.txt'deki klasörleri yaratır
5. validators/check_package_rules_present.py çalıştırır
6. governance/package-registry.md auto-yeniden üretmeyi önerir

Sonra kullanıcı:
- Transport number ekler (.rules.md)
- SAP'de paket yaratır (SE21)
"""
import argparse
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_git_user() -> str:
    try:
        r = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, check=True
        )
        return r.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def substitute(text: str, mapping: dict) -> str:
    """Placeholder'ları değiştirir: {KEY} → değer."""
    for key, val in mapping.items():
        text = text.replace("{" + key + "}", val)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Yeni ERP paketi bootstrap")
    parser.add_argument("package", help="Paket adı (örn. ZSD001_CLC)")
    parser.add_argument("--title", required=True, help="Paket başlığı")
    parser.add_argument("--module", default="SD", help="SAP modülü (varsayılan: SD)")
    parser.add_argument("--owner", default=None, help="Owner (varsayılan: git user.name)")
    parser.add_argument("--templates-root", default="templates/new-package")
    parser.add_argument("--erp-root", default="ERP")
    args = parser.parse_args()

    pkg_full = args.package
    if not re.match(r"^ZSD\d{3}_CLC$", pkg_full):
        print(
            f"UYARI: Paket adı '{pkg_full}' standart format değil (ZSD<NNN>_CLC). "
            f"ADR 0002'ye bak.",
            file=sys.stderr,
        )

    pkg_short = pkg_full.replace("_CLC", "")
    owner = args.owner or get_git_user()
    today = date.today().isoformat()

    mapping = {
        "PKG": pkg_short,
        "PKG_FULL": pkg_full,
        "TITLE": args.title,
        "MODULE": args.module,
        "DATE": today,
        "OWNER": owner,
    }

    templates_dir = Path(args.templates_root)
    erp_root = Path(args.erp_root)
    module_dir = erp_root / args.module
    pkg_dir = module_dir / pkg_full

    # Modül klasörü mevcut mu? (SD, MM, FI, QM, PM, EWM, CO ve diğerleri)
    if not module_dir.exists():
        print(
            f"HATA: Modül klasörü {module_dir} yok. "
            f"Geçerli modüller: SD, MM, FI, QM, PM, EWM, CO (veya manuel olarak yarat).",
            file=sys.stderr,
        )
        return 1

    if pkg_dir.exists():
        print(f"HATA: {pkg_dir} zaten mevcut, bootstrap iptal.", file=sys.stderr)
        return 1

    if not templates_dir.exists():
        print(f"HATA: {templates_dir} bulunamadı.", file=sys.stderr)
        return 1

    pkg_dir.mkdir(parents=True)
    print(f"OK — Yaratıldı: {pkg_dir}/")

    # 1. Klasörleri yarat (folders.txt'den)
    folders_file = templates_dir / "folders.txt"
    if folders_file.exists():
        for folder in folders_file.read_text(encoding="utf-8").splitlines():
            folder = folder.strip()
            if folder:
                (pkg_dir / folder).mkdir(parents=True, exist_ok=True)
                print(f"  Klasör: {folder}/")

    # 2. Template dosyalarını kopyala + substitute (alt-klasör yapısını korur — ör. ref_docs/README.md.tmpl)
    for tmpl_file in sorted(templates_dir.rglob("*")):
        if not tmpl_file.is_file():
            continue
        if tmpl_file.name == "folders.txt":
            continue

        # Hedef göreli yol: .tmpl uzantısını at, alt-klasörü koru
        rel = tmpl_file.relative_to(templates_dir)
        target = pkg_dir / Path(str(rel).replace(".tmpl", ""))
        target.parent.mkdir(parents=True, exist_ok=True)

        content = tmpl_file.read_text(encoding="utf-8")
        target.write_text(substitute(content, mapping), encoding="utf-8")
        print(f"  Dosya: {target.relative_to(pkg_dir)}")

    print(f"\nBootstrap tamamlandı: {pkg_dir}/")
    print("\nSıradaki adımlar:")
    print("  1. .rules.md'de transport number ve bağımlılık doldur")
    print("  2. SPEC.md'yi gerçek FS/TS bilgisiyle doldur")
    print("  3. SAP'de paketi yarat (SE21)")
    print(f"  4. python scripts/build_package_index.py  # governance/package-registry.md yenile")
    print(f"  5. python scripts/validators/run_all_validators.py  # doğrula")
    return 0


if __name__ == "__main__":
    sys.exit(main())

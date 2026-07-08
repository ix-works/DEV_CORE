"""
build_package_index.py — Tüm <source_root>/<PKG>/.rules.md'leri tarayıp
governance/package-registry.md'yi auto-üretir.

Kullanım:
    python scripts/build_package_index.py
    python scripts/build_package_index.py --dry-run  # üretilecek içeriği göster, yazma

Mantık:
- Her .rules.md'den frontmatter (layer, scope) + "Modül & Amaç" bölümünden bilgi çıkarır
- Tablo formatında governance/package-registry.md üretir
- Mevcut "Aktif Paketler" tablosunu değiştirir, diğer bölümleri korur
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[0]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def extract_field(text: str, label: str) -> str:
    """`.rules.md` body'sinden 'Field: value' satırını çıkarır."""
    pattern = rf"\*\*{re.escape(label)}:?\*\*\s*([^\n]+)"
    m = re.search(pattern, text)
    if m:
        return m.group(1).strip()
    # Alternatif: "- Field: value"
    pattern = rf"-\s*\*\*{re.escape(label)}:?\*\*\s*([^\n]+)"
    m = re.search(pattern, text)
    if m:
        return m.group(1).strip()
    return ""


def extract_frontmatter_status(text: str) -> str:
    """Frontmatter'dan status değerini çıkarır."""
    m = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
    return m.group(1) if m else "unknown"


def collect_packages(erp_root: Path) -> list[dict]:
    """<source_root>/<MODULE>/<PKG>/ — her paketten bilgi topla, modül path'ten alınır."""
    packages = []
    for module_dir in sorted(erp_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("."):
            continue
        module_name = module_dir.name  # SD, MM, FI, ...

        for pkg in sorted(module_dir.iterdir()):
            if not pkg.is_dir() or pkg.name.startswith("."):
                continue
            rules_path = pkg / ".rules.md"
            if not rules_path.exists():
                packages.append(
                    {
                        "name": pkg.name,
                        "module": module_name,
                        "prefix": "?",
                        "module_desc": "?",
                        "owner": "?",
                        "status": "❌ .rules.md yok",
                    }
                )
                continue

            text = rules_path.read_text(encoding="utf-8", errors="replace")
            module_desc = extract_field(text, "Modül")
            owner = extract_field(text, "Owner")
            status_fm = extract_frontmatter_status(text)
            status_body = extract_field(text, "Durum")
            status = status_body or status_fm

            # Prefix tahmin: paket adından
            prefix = pkg.name.replace("_CLC", "") + "_*"

            packages.append(
                {
                    "name": pkg.name,
                    "module": module_name,
                    "prefix": prefix,
                    "module_desc": module_desc,
                    "owner": owner,
                    "status": status,
                }
            )
    return packages


def render_table(packages: list[dict]) -> str:
    """Markdown tablosu üret (modüle göre gruplu)."""
    lines = ["| Modül | Paket | Prefix | Açıklama | Owner | Durum |",
             "|---|---|---|---|---|---|"]
    for p in packages:
        lines.append(
            f"| `{p['module']}` | `{p['name']}` | `{p['prefix']}` | "
            f"{p['module_desc']} | {p['owner']} | {p['status']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="package-registry.md üret")
    parser.add_argument("--source-root", default=SOURCE_ROOT_NAME)
    parser.add_argument("--registry", default="governance/package-registry.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    erp_root = Path(args.erp_root)
    registry_path = Path(args.registry)

    packages = collect_packages(erp_root)
    if not packages:
        print(f"UYARI: {erp_root}/ altında paket yok", file=sys.stderr)
        return 0

    table = render_table(packages)
    today = date.today().isoformat()

    # Mevcut registry'i oku, "## Aktif Paketler" altındaki tabloyu değiştir
    if not registry_path.exists():
        print(f"HATA: {registry_path} mevcut değil — manuel oluştur ya da template'e başvur.", file=sys.stderr)
        return 1

    current = registry_path.read_text(encoding="utf-8")
    # last-updated frontmatter alanını güncelle
    current = re.sub(
        r"^last-updated:.*$", f"last-updated: {today}", current, count=1, flags=re.MULTILINE
    )

    # "## Aktif Paketler" bölümünü değiştir
    pattern = r"(## Aktif Paketler\n\n).*?(\n\n## )"
    replacement = rf"\g<1>{table}\g<2>"
    new_content = re.sub(pattern, replacement, current, flags=re.DOTALL)

    if new_content == current:
        print("UYARI: 'Aktif Paketler' bölümü bulunamadı veya değişiklik gerekmedi.", file=sys.stderr)
    elif args.dry_run:
        print("--- DRY RUN — yazılacak içerik ---")
        print(new_content)
    else:
        registry_path.write_text(new_content, encoding="utf-8")
        print(f"OK — {registry_path} güncellendi ({len(packages)} paket).")

    return 0


if __name__ == "__main__":
    sys.exit(main())

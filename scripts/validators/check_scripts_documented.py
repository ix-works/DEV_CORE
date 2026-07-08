"""
check_scripts_documented.py — `scripts/` altındaki create_*.py / populate_*.py / run_*.py
script'lerinin her birinin playbook/ MD dosyalarından birinde referans verildiğini doğrular.

Mantık (T9 trigger destekli, LESSONS_LEARNED #4):
- `scripts/` altındaki üst seviye `.py` dosyaları taranır
- Prefix filter: create_*.py, populate_*.py, run_*.py (alt klasörler hariç)
- Whitelist: library/helper script'ler doğrulamadan muaf
- Her script ismi (örn. "create_table_type.py") en az bir playbook MD'sinde geçmeli

Kullanım:
    python scripts/validators/check_scripts_documented.py
    python scripts/validators/check_scripts_documented.py --playbook-root playbook

Exit kodu:
    0 — Tüm script'ler dokumante
    1 — Bir veya birden çok script playbook'ta referans verilmemiş
"""
import argparse
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Doğrulamadan muaf script'ler (library, helper, setup)
WHITELIST = {
    "sap_adt_lib.py",
    "sap_client.py",
    "setup_credentials.py",
    "object_types.py",
    "sprint_gate_check.py",  # mevcut kod gate
    "td_spec_check.py",  # mevcut kod gate
    "syntax_check.py",
    "where_used.py",
    "check_package.py",  # not a create/populate/run pattern
    "delete_object.py",
    "download_object.py",
    "download_ddic_objects.py",
    "get_object_metadata.py",
    "get_object_structure.py",
    "get_system_info.py",
    "list_inactive_objects.py",
    "list_package_contents.py",
    "list_revisions.py",
    "list_transports.py",
    "login_saml_sso.py",
    "push_object.py",
    "search_objects.py",
    "activate_object.py",
}

# Sadece bu prefix'lerle başlayan dosyalar zorunlu doc kapsamında
REQUIRED_PREFIXES = ("create_", "populate_", "run_")


def main() -> int:
    parser = argparse.ArgumentParser(description="Script playbook referansı kontrolü")
    parser.add_argument("--scripts-root", default="scripts", help="scripts/ dizini")
    parser.add_argument("--playbook-root", default="playbook", help="playbook/ dizini")
    parser.add_argument("--strict", action="store_true", help="Eksik referansları fail say")
    args = parser.parse_args()

    scripts_dir = Path(args.scripts_root)
    playbook_dir = Path(args.playbook_root)

    if not scripts_dir.exists() or not playbook_dir.exists():
        print(f"HATA: {scripts_dir} veya {playbook_dir} bulunamadı", file=sys.stderr)
        return 1

    # Üst-seviye .py dosyaları (alt klasörler hariç)
    scripts = sorted(
        f.name
        for f in scripts_dir.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name not in WHITELIST
    )

    # Sadece create_/populate_/run_ prefix'leri kontrol kapsamında
    required = [s for s in scripts if s.startswith(REQUIRED_PREFIXES)]

    # Playbook MD'lerini tek string'e topla
    playbook_text = ""
    for md in playbook_dir.rglob("*.md"):
        playbook_text += md.read_text(encoding="utf-8", errors="replace") + "\n"

    undocumented = [s for s in required if s not in playbook_text]

    if undocumented:
        level = "HATA" if args.strict else "UYARI"
        print(f"{level} — Playbook'ta referans verilmemiş script'ler:", file=sys.stderr)
        for s in undocumented:
            print(f"  scripts/{s}", file=sys.stderr)
        print(
            "\nÇözüm: İlgili playbook MD'sine (örn. playbook/adt-<tip>.md) bu script'in "
            "referansını ve pattern özetini ekle (T9 trigger).\n"
            "Bu script'ler henüz icra edilmediyse playbook eklemesi T1/T2 trigger ile gelecek.",
            file=sys.stderr,
        )
        return 1 if args.strict else 0

    print(f"OK — {len(required)} create_/populate_/run_ script playbook'ta referans verilmiş.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

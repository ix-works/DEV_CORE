# -*- coding: utf-8 -*-
"""setup_plugins.py — Bu projenin SAĞLIKLI çalışması için GEREKEN Claude Code
plugin'lerini kurar (idempotent). Klon, proje sahibiyle aynı araç setine sahip olur.

NEDEN: Claude Code plugin'leri makine/kullanıcı düzeyinde kuruludur (repo'da DEĞİL).
Clone, repo'daki kural/hook/MCP/skill'leri alır AMA marketplace plugin'lerini (ui5,
playwright, pyright-lsp…) ALMAZ → bu script onları kurar. Plugin envanteri:
governance/tooling-plugins.md.

Kaynak: `governance/tooling-plugins.md` (proje araç kaydı). CLI: `claude plugin ...`.

Kullanım:
    python scripts/setup_plugins.py            # eksikleri kur
    python scripts/setup_plugins.py --dry-run  # ne kurulacağını göster
    python scripts/setup_plugins.py --list     # mevcut durumu listele
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MARKETPLACE = "claude-plugins-official"
MARKETPLACE_SRC = "https://github.com/anthropics/claude-plugins-official.git"

# Bu projenin işleyişi için GEREKLİ plugin'ler (governance/tooling-plugins.md).
# (plugin_adı, neden-gerekli)
REQUIRED = [
    ("ui5",                 "Freestyle UI5/Fiori: control API doğrulama + linter + manifest (ZORUNLU FE)"),
    ("playwright",          "UI'ı tarayıcıda çalıştır/doğrula (lokal test + layout-sayısal kontrol)"),
    ("pyright-lsp",         "Python script zekası (validator/hook/tool geliştirme diagnostics)"),
    ("code-review",         "Commit/PR öncesi çok-ajanlı kod kalite + bug taraması"),
    ("frontend-design",     "UI5 ekran görsel kalite/iskelet"),
    ("claude-md-management", "CLAUDE.md loader bakımı + oturum öğrenimi"),
    ("skill-creator",       "Project-skill yaratma/iyileştirme (örn. sap-abap-dev)"),
    ("plugin-dev",          "Kendi plugin/skill/hook/command/MCP'lerimizi geliştirme"),
]


def claude_bin() -> str | None:
    return shutil.which("claude")


def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def installed_plugins(claude: str) -> set[str]:
    _, out = run([claude, "plugin", "list"])
    names = set()
    for line in out.splitlines():
        line = line.strip().lstrip("❯> ").strip()  # CLI liste-öneki: '❯' (eski) / '>' (yeni)
        if "@" in line and not line.lower().startswith(("version", "scope", "status", "source")):
            names.add(line.split("@")[0].strip())
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description="Gerekli Claude Code plugin'lerini kur (idempotent)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true", help="Yalnız mevcut durumu göster")
    args = ap.parse_args()

    claude = claude_bin()
    if not claude:
        print("[FAIL] 'claude' CLI PATH'te yok — Claude Code kurulu mu? Plugin kurulumu atlandı.", file=sys.stderr)
        print("       (Manuel: claude plugin install <ad>@%s)" % MARKETPLACE)
        return 1

    have = installed_plugins(claude)
    print(f"[INFO] Marketplace : {MARKETPLACE}")
    print(f"[INFO] Kurulu      : {', '.join(sorted(have)) or '(yok)'}")

    if args.list:
        for name, why in REQUIRED:
            mark = "✔" if name in have else "✗ EKSİK"
            print(f"  {mark:8} {name:22} — {why}")
        return 0

    # Marketplace ekli değilse ekle (idempotent; resmi marketplace genelde hazır)
    _, mout = run([claude, "plugin", "marketplace", "list"])
    if MARKETPLACE not in mout:
        print(f"[>>>] Marketplace ekleniyor: {MARKETPLACE}")
        if not args.dry_run:
            run([claude, "plugin", "marketplace", "add", MARKETPLACE_SRC])

    missing = [(n, w) for n, w in REQUIRED if n not in have]
    if not missing:
        print("[OK] Tüm gerekli plugin'ler zaten kurulu.")
        return 0

    print(f"\n[>>>] Kurulacak {len(missing)} eksik plugin:")
    failed = []
    for name, why in missing:
        spec = f"{name}@{MARKETPLACE}"
        print(f"   - {name}  ({why})")
        if args.dry_run:
            continue
        rc, out = run([claude, "plugin", "install", spec])
        if rc != 0:
            failed.append(name)
            print(f"     [FAIL] {out.strip()[-300:]}")
        else:
            print(f"     [OK] kuruldu")

    print("\n--- ÖZET ---")
    if args.dry_run:
        print(f"  (DRY-RUN) Eksik: {len(missing)}")
    else:
        print(f"  Kuruldu: {len(missing) - len(failed)} · Başarısız: {len(failed)}")
        if failed:
            print(f"  Başarısız: {', '.join(failed)} — manuel: claude plugin install <ad>@{MARKETPLACE}")
        print("  NOT: Plugin'ler yeni Claude oturumunda aktif olur — kurulum sonrası oturumu yeniden başlat.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_project.py — YENİ proje iskeleti ÜRETİCİSİ (ADR 0020; PROJECT_BOOTSTRAP STEP 2).

KOPYALAMAZ, core'daki template'lerden ÜRETİR. Metodoloji projeye girmez —
proje core'a junction'la bakar (junction'ları team_setup.py kurar, STEP 3).

Üretilenler (hedef proje kökünde):
  CLAUDE.md                (claude/CLAUDE.project.template.md'den; --name verilirse doldurulur)
  .claude/settings.json    (claude/settings.template.json'dan)
  scripts/hook_shim.py     (claude/hook_shim.template.py'den — D15)
  project.yaml             (profil + source_root iskeleti — §9.3)
  .gitignore               (SIZINTI KİLİDİ satırları hazır)
  .gitattributes           (CRLF kararı — A3.0/B1 ile aynı)
  .mcp.json                (MCP core'dan yüklenir; D17 env-first)
  <source_root>/ conn/ playbook-local/ standards-local/ scripts/validators-local/  (boş)

Kullanım:  python <CORE>/scripts/init_project.py C:\\IX\\<PROJE> [--name <AD>] [--source-root SOURCE_CODES] [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CORE_ROOT = Path(__file__).resolve().parent.parent  # __file__-türetimli (D24)

GITIGNORE = """\
# ==== SIZINTI KİLİDİ (ADR 0020 — core içeriği proje reposuna GİREMEZ) ====
/core/
.claude/agents/
.claude/skills/
.claude/commands/
# ==== kişisel / runtime ====
.claude/settings.local.json
.claude/active_package
.conn_adt
conn/*.env
CLAUDE.local.md
.tmp/
*.pyc
__pycache__/
node_modules/
sap_adt_debug.log
"""

GITATTRIBUTES = """\
* text=auto
*.sh text eol=lf
*.py text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.pdf binary
*.zip binary
"""

MCP_JSON = """\
{
  "mcpServers": {
    "sap-adt": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_servers.sap_adt.server"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": "${CLAUDE_PROJECT_DIR:-.}/core"
      }
    }
  }
}
"""

PROJECT_YAML = """\
# project.yaml — proje kimliği (PROJECT_BOOTSTRAP STEP 0 kararları; GECIS-PLAN §9.3)
# Core script/validator'ları BU dosyadan okur — hard-code yok (K12).

source_root: {source_root}     # kaynak-kod klasörü adı
sap_profile: __DOLDUR__        # ecc | s4_private | s4_public | btp_abap
release: "__DOLDUR__"          # ecc+s4_private zorunlu (örn. "2025"); public/btp'de kaldır
# db: hana                     # yalnız ecc: hana | anydb
# cleancore_policy: balanced   # yalnız s4_private: strict | balanced | classic
master_language: __DOLDUR__    # örn. TR / EN (ADR 0005-D bu dille uygulanır)

# Davranış/guard config'leri:
frozen_readonly_paths: []      # pre_tool_guard bu köklere YAZMAYI bloklar (örn. eski-dünya arşivi)
# sql_view_prefix: Z<MOD><NNN>_V_   # populate_cds_views namespace-gate'i (B-5)
# package_prefixes: []         # paket-sınır validator'ları
"""


def uret(hedef: Path, icerik: str, force: bool) -> str:
    if hedef.exists() and not force:
        return f"[ATLA] {hedef} (mevcut; --force ile ez)"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(icerik, encoding="utf-8", newline="\n")
    return f"[ OK ] {hedef}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hedef", help="Yeni proje kök dizini (örn. C:\\IX\\XYZ)")
    ap.add_argument("--name", default=None, help="<PROJECT_NAME> placeholder'ını doldur")
    ap.add_argument("--source-root", default="SOURCE_CODES", help="Kaynak-kod klasör adı (K12)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    proje = Path(a.hedef).resolve()
    proje.mkdir(parents=True, exist_ok=True)
    print(f"init_project: core={CORE_ROOT}  →  proje={proje}\n")

    # Template'lerden üret
    tpl = CORE_ROOT / "claude"
    claude_md = (tpl / "CLAUDE.project.template.md").read_text(encoding="utf-8")
    settings = (tpl / "settings.template.json").read_text(encoding="utf-8")
    shim = (tpl / "hook_shim.template.py").read_text(encoding="utf-8")
    if a.name:
        claude_md = claude_md.replace("<PROJECT_NAME>", a.name)
    claude_md = claude_md.replace("<SOURCE_ROOT>", a.source_root)

    sonuc = [
        uret(proje / "CLAUDE.md", claude_md, a.force),
        uret(proje / ".claude" / "settings.json", settings, a.force),
        uret(proje / "scripts" / "hook_shim.py", shim, a.force),
        uret(proje / "project.yaml", PROJECT_YAML.format(source_root=a.source_root), a.force),
        uret(proje / ".gitignore", GITIGNORE, a.force),
        uret(proje / ".gitattributes", GITATTRIBUTES, a.force),
        uret(proje / ".mcp.json", MCP_JSON, a.force),
    ]
    for d in (a.source_root, "conn", "playbook-local", "standards-local",
              "scripts/validators-local", "governance"):
        p = proje / d
        p.mkdir(parents=True, exist_ok=True)
        (p / ".gitkeep").touch()
        sonuc.append(f"[ OK ] {p}\\  (klasör)")

    print("\n".join(sonuc))
    print("\nSONRAKİ ADIMLAR (PROJECT_BOOTSTRAP):")
    print(f"  1. python {CORE_ROOT / 'scripts' / 'team_setup.py'} --project {proje}   (junction'lar + seed)")
    print("  2. .conn_adt + project.yaml __DOLDUR__ alanları  (STEP 4)")
    print("  3. Kabul gate'i (STEP 5): oturum aç → ekran-teyidi + MCP ping + validators")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_project.py — YENİ proje iskeleti ÜRETİCİSİ (ADR 0020; PROJECT_BOOTSTRAP STEP 2).

KOPYALAMAZ, core'daki template'lerden ÜRETİR. Metodoloji projeye girmez —
proje core'a junction'la bakar (junction'ları team_setup.py kurar, STEP 3).

Üretilenler (hedef proje kökünde):
  CLAUDE.md                (claude/CLAUDE.project.template.md'den; --name verilirse doldurulur)
  .claude/settings.json    (claude/settings.template.json'dan)
  scripts/hook_shim.py     (claude/hook_shim.template.py'den — D15)
  project.yaml             (profil + source_root iskeleti — profiles/ + CLAUDE.core.md §2)
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import yasaklar_stamp  # KESİN YASAKLAR fiziksel damga (junction-bağımsız)

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
.claude/rules/
.claude/memory-seed/

# ==== SIRLAR / KİMLİK — asla commit'lenmez ====
# 2026-07-10 template provası: bu satırların ÇOĞU şablonda YOKTU; yalnız TD'de
# birikmişti → yeni açılan her proje bağlantı-yedeğini, CSRF token'ını ve
# proje-lokal kimlik dosyalarını COMMIT EDİYORDU.
.conn_adt
conn/*.env
conn/.conn_adt.bak
.csrf_token.json
# genericize blocklist: müşteri/sistem/kişi adları — ASLA commit'lenmez
.claude/genericize-blocklist.txt
.claude/project.local.yaml

# ==== kişisel / runtime state ====
.claude/settings.local.json
.claude/active_package
.claude/cache/
.claude/projects/
.claude/worktrees/
# makine-lokal davranış baseline (behavior_manifest üretir; commit'lenmez)
.claude/behavior-manifest.json
.claude/.current_session
.claude/.session_fresh.json
.claude/.statusline_vpn_cache
.claude/.mcp_active_system
.claude/.worktype_hinted.json
.claude/.itg_shown.json
**/.statusline_vpn_cache
**/.mcp_active_system
CLAUDE.local.md
.tmp/
scratchpad/
TempScripts/
mcp_servers/**/.cache/
mcp_servers/**/audit.log
sap_adt_debug.log

# ==== derleme / araç artefaktları ====
*.pyc
*.pyo
__pycache__/
.pytest_cache/
node_modules/
UI/node_modules/
.playwright/
.playwright-cli/
.playwright-mcp/
*.proposed.cds

# ==== editör / OS ====
*.swp
*~
~$*
.DS_Store
Thumbs.db
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
# project.yaml — proje kimliği (PROJECT_BOOTSTRAP STEP 0 kararları;
# profil alanları: core/profiles/ + CLAUDE.core.md §2)
# Core script/validator'ları BU dosyadan okur — hard-code yok (K12).

source_root: {source_root}     # kaynak-kod klasörü adı
repo_mode: {repo_mode}         # full=GitHub+korumalar | local=yalnız git-init (kısa proje ÖNERİLEN) | none=git'siz (K13)
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
    ap.add_argument("--repo-mode", default="full", choices=["full", "local", "none"],
                    help="K13: full=GitHub | local=yalnız git-init (kısa proje) | none=git'siz")
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
    # 2026-07-10 template provası: README ve pre-commit ÜRETİLMİYORDU. README her projede
    # elle yazılıyordu; pre-commit ise HİÇ yoktu → yeni proje commit anında sıfır statik
    # kontrolle açılıyordu (merdivende ③ sanılan gate'ler fiilen ⑤ idi).
    readme = (tpl / "README.project.template.md").read_text(encoding="utf-8")
    precommit = (tpl / "git-hooks" / "pre-commit.template").read_text(encoding="utf-8")
    if a.name:
        claude_md = claude_md.replace("<PROJECT_NAME>", a.name)
        readme = readme.replace("<PROJECT_NAME>", a.name)
    claude_md = claude_md.replace("<SOURCE_ROOT>", a.source_root)
    readme = readme.replace("<source_root>", a.source_root)
    # KESİN YASAKLAR fiziksel damgası — kök CLAUDE.md'ye (junction-bağımsız daima yüklü)
    claude_md = yasaklar_stamp.upsert(claude_md, CORE_ROOT)

    sonuc = [
        uret(proje / "CLAUDE.md", claude_md, a.force),
        uret(proje / "README.md", readme, a.force),
        uret(proje / ".claude" / "settings.json", settings, a.force),
        uret(proje / "scripts" / "hook_shim.py", shim, a.force),
        uret(proje / "scripts" / "git-hooks" / "pre-commit", precommit, a.force),
        uret(proje / "project.yaml",
             PROJECT_YAML.format(source_root=a.source_root, repo_mode=a.repo_mode), a.force),
        uret(proje / ".gitignore", GITIGNORE, a.force),
        uret(proje / ".gitattributes", GITATTRIBUTES, a.force),
        uret(proje / ".mcp.json", MCP_JSON, a.force),
    ]

    # Sunucu-tarafı koruma (yalnız repo_mode=full; LITE modlarda anlamsız).
    # Bootstrap provası 2026-07-09: bunlar ÜRETİLMİYORDU → her proje elle kuruyordu,
    # ve CI workflow'u başka bir projeden kopyalanıyordu (private→public sızıntı riski).
    if a.repo_mode == "full":
        wf = (tpl / "workflows" / "guard.template.yml").read_text(encoding="utf-8")
        co = (tpl / "CODEOWNERS.template").read_text(encoding="utf-8")
        if a.name:
            co = co.replace("<PROJECT_NAME>", a.name)
        sonuc.append(uret(proje / ".github" / "workflows" / "guard.yml", wf, a.force))
        sonuc.append(uret(proje / ".github" / "CODEOWNERS", co, a.force))
    for d in (a.source_root, "conn", "playbook-local", "standards-local",
              "scripts/validators-local", "governance"):
        p = proje / d
        p.mkdir(parents=True, exist_ok=True)
        (p / ".gitkeep").touch()
        sonuc.append(f"[ OK ] {p}\\  (klasör)")

    print("\n".join(sonuc))
    print(f"\nSONRAKİ ADIMLAR (PROJECT_BOOTSTRAP — repo_mode={a.repo_mode}):")
    if a.repo_mode == "full":
        print("  0. GitHub'da boş repo aç + clone/remote bağla (STEP 1)")
    elif a.repo_mode == "local":
        print(f"  0. git init (yalnız lokal — remote YOK):  git -C {proje} init  (K13 LITE)")
    else:
        print("  0. (K13 LITE/none) git YOK — sızıntı/push kalemleri kabul-gate'inden düşer;"
              " kalıcılaştırma kullanıcı takdirinde")
    print(f"  1. python {CORE_ROOT / 'scripts' / 'team_setup.py'} --project {proje}   (junction'lar + seed)")
    print("  2. .conn_adt + project.yaml __DOLDUR__ alanları  (STEP 4)")
    print(f"  3. python {CORE_ROOT / 'scripts' / 'behavior_manifest.py'} generate"
          "   (davranış baseline; yoksa ix_doctor K4 FAIL)")
    if a.repo_mode == "full":
        print("  4. .github/CODEOWNERS → <OWNER_TEAM> yerine gerçek GitHub team yaz")
        print("     (team'in repoya EN AZ `write` erişimi olmalı — GitHub şartı)")
        print("  5. STEP 6 ilk push'tan SONRA ruleset'i ACTIVE et:")
        print("       required_approving_review_count=1 + require_code_owner_review=true")
        print("       + required_status_checks=[core-leak, behavior-surface]")
        print("       + bypass_actors=[{OrganizationAdmin, bypass_mode: pull_request}]")
        print("       (tek code-owner varsa bypass ŞART: kendi PR'ını onaylayamaz)")
    print("  6. Kabul gate'i (STEP 5) — ilk commit/push SONRASI koş "
          "(ix_doctor main-ref + ruleset + CI arar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

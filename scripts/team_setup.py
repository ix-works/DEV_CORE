#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""team_setup.py — Geliştirici/proje kurulumu ve onarımı (ADR 0020; canlı-çekirdek modeli).

CORE içinde yaşar; hedef PROJE cwd'den veya --project ile alınır (D24: kökler
__file__-türetimli, sabit sürücü/klasör varsayımı YOK).

Yaptıkları:
  1. Python >= 3.10 + pip install (MCP requirements)
  2. CORE reposunda `core.hooksPath scripts/git-hooks` (D19 — pre-commit gate'leri)
  3. PROJE'de 4 JUNCTION kur/doğrula (admin gerektirmez, mklink /J; D25: tek tek rapor):
       core / .claude\\agents / .claude\\skills / .claude\\commands
  4. Eksik proje-lokal dosyaları template'ten tamamla (settings.json, hook_shim.py)
  5. Claude Code plugin'leri (setup_plugins.py; non-fatal) + seed_memory (--no-seed ile atla)
  6. Smoke: statusline + MCP import
  --repair-junctions      : yalnız junction kur/onar + rapor (session_start'ın önerdiği komut)
  --provision-worktree P  : D16 — worktree'ye junction'lar + izlenmeyen runtime dosyaları
                            (.conn_adt, conn/, settings.local.json → hardlink/kopya)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CORE_ROOT = Path(__file__).resolve().parent.parent          # D24
MIN_PY = (3, 10)
REQ_FILE = CORE_ROOT / "mcp_servers" / "sap_adt" / "requirements.txt"

OK, WARN, FAIL, INFO = "[ OK ]", "[WARN]", "[FAIL]", "[INFO]"


def say(lv: str, msg: str) -> None:
    print(f"{lv} {msg}")


def junction_hedefi(link: Path) -> Path | None:
    """Junction/symlink hedefini döndür; değilse None.
    Windows readlink '\\\\?\\' extended-length öneki döndürür — kıyas için soyulur
    (soyulmazsa sağlam junction 'YANLIŞ hedefe' sanılıp gereksiz yeniden kurulur)."""
    try:
        ham = str(os.readlink(link))
        if ham.startswith("\\\\?\\"):
            ham = ham[4:]
        return Path(ham)
    except (OSError, ValueError):
        return None


def junction_kur(link: Path, hedef: Path) -> bool:
    """mklink /J (admin gerektirmez). True=sağlam."""
    if link.exists():
        mevcut = junction_hedefi(link)
        if mevcut and mevcut.resolve() == hedef.resolve():
            say(OK, f"junction sağlam: {link} → {hedef}")
            return True
        if mevcut:
            say(WARN, f"junction YANLIŞ hedefe: {link} → {mevcut}; yeniden kuruluyor")
            link.rmdir()  # linki kaldırır, HEDEFE DOKUNMAZ (silme-matrisi kanıtlı)
        else:
            say(FAIL, f"{link} junction DEĞİL gerçek klasör — elle incele, DOKUNMADIM")
            return False
    link.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(hedef)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        say(OK, f"junction kuruldu: {link} → {hedef}")
        return True
    say(FAIL, f"mklink başarısız: {(r.stderr or r.stdout).strip()}")
    return False


def junctions(proje: Path) -> bool:
    """4 junction (D25: dördü TEK TEK raporlanır — kopuk agents/skills SESSİZ semptom verir)."""
    plan = [
        (proje / "core",                 CORE_ROOT),
        (proje / ".claude" / "agents",   CORE_ROOT / "claude" / "agents"),
        (proje / ".claude" / "skills",   CORE_ROOT / "claude" / "skills"),
        (proje / ".claude" / "commands", CORE_ROOT / "claude" / "commands"),
    ]
    return all([junction_kur(l, h) for (l, h) in plan])


def dosya_tamamla(proje: Path) -> None:
    """Eksik proje-lokal dosyaları template'ten üret (idempotent — var olanı EZMEZ)."""
    tpl = CORE_ROOT / "claude"
    hedefler = [
        (proje / ".claude" / "settings.json", tpl / "settings.template.json"),
        (proje / "scripts" / "hook_shim.py",  tpl / "hook_shim.template.py"),
    ]
    for hedef, kaynak in hedefler:
        if hedef.exists():
            say(OK, f"mevcut: {hedef.name} (drift denetimi: session_start D7)")
        else:
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kaynak, hedef)
            say(OK, f"template'ten üretildi: {hedef}")


def hookspath_core() -> None:
    """D19: core reposunda versiyonlanan git-hook'ları etkinleştir."""
    gh = CORE_ROOT / "scripts" / "git-hooks"
    if not gh.is_dir():
        say(WARN, "core scripts/git-hooks henüz yok (B11) — hooksPath atlandı")
        return
    r = subprocess.run(["git", "-C", str(CORE_ROOT), "config",
                        "core.hooksPath", "scripts/git-hooks"], capture_output=True, text=True)
    say(OK if r.returncode == 0 else FAIL, f"core.hooksPath=scripts/git-hooks ({CORE_ROOT})")


def provision_worktree(worktree: Path, proje: Path) -> bool:
    """D16: worktree'de junction'lar + git'in getirmediği runtime dosyaları."""
    say(INFO, f"worktree provizyonu: {worktree} (ana proje: {proje})")
    ok = junctions(worktree)
    for rel in (".conn_adt", ".claude/settings.local.json"):
        src, dst = proje / rel, worktree / rel
        if not src.exists():
            say(WARN, f"kaynakta yok, atlandı: {rel}")
            continue
        if dst.exists():
            say(OK, f"zaten var: {rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)  # hardlink: aynı volume, admin istemez
            say(OK, f"hardlink: {rel}")
        except OSError:
            shutil.copyfile(src, dst)
            say(OK, f"kopya (hardlink olmadı): {rel}")
    src_conn, dst_conn = proje / "conn", worktree / "conn"
    if src_conn.is_dir() and not dst_conn.exists():
        shutil.copytree(src_conn, dst_conn)
        say(OK, "conn/ kopyalandı")
    return ok


def npm_clis() -> None:
    """Token-verimli CLI'ler (governance/tooling-plugins.md; makine-düzeyi, repo'da DEĞİL):
    playwright-cli = ADR 0017 ui-smoke gate'i + tarayıcı-doğrulamanın TEMELİ (skill core'da,
    binary global gerekir). NON-FATAL: yoksa playwright-MCP-plugin'ine düşülür."""
    if not shutil.which("npm"):
        say(WARN, "npm YOK — playwright-cli/ast-grep/mmdc/marp atlandı "
                  "(node kur, sonra: npm i -g @playwright/cli @ast-grep/cli)")
        return
    clis = [
        ("playwright-cli", "@playwright/cli@latest", "token-verimli tarayıcı doğrulama (ADR 0017 ui-smoke)"),
        ("ast-grep", "@ast-grep/cli@latest", "yapısal kod arama/refactor (AST)"),
        ("mmdc", "@mermaid-js/mermaid-cli@latest", "Mermaid → SVG/PNG (FS/TS/KD)"),
        ("marp", "@marp-team/marp-cli@latest", "Markdown → slayt (PDF/PPTX)"),
    ]
    for binary, pkg, desc in clis:
        if shutil.which(binary):
            say(OK, f"{binary} kurulu ({desc})")
            continue
        r = subprocess.run(["npm", "install", "-g", pkg], capture_output=True, text=True)
        say(OK if r.returncode == 0 else WARN,
            f"{binary} {'kuruldu' if r.returncode == 0 else 'KURULAMADI (opsiyonel): ' + (r.stderr or '')[:120]}")


def alt_arac(proje: Path, ad: str, non_fatal_msg: str) -> None:
    """core scripts/<ad> aracını proje cwd'siyle koş (non-fatal)."""
    script = CORE_ROOT / "scripts" / ad
    if not script.exists():
        return
    r = subprocess.run([sys.executable, str(script)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=proje)
    say(OK if r.returncode == 0 else WARN,
        f"{ad} (exit {r.returncode}) {(r.stdout or '').strip().splitlines()[-1][:70] if (r.stdout or '').strip() else non_fatal_msg}")


def smoke(proje: Path) -> None:
    st = CORE_ROOT / "scripts" / "statusline.py"
    try:
        r = subprocess.run([sys.executable, str(st)], input="{}", capture_output=True,
                           text=True, cwd=proje, timeout=30)
        say(OK if r.returncode == 0 else WARN, f"statusline smoke (exit {r.returncode})")
    except subprocess.TimeoutExpired:
        say(WARN, "statusline smoke timeout")
    env = dict(os.environ, PYTHONPATH=str(CORE_ROOT), CLAUDE_PROJECT_DIR=str(proje))
    r = subprocess.run([sys.executable, "-c",
                        "import mcp_servers.sap_adt.server; print('import-ok')"],
                       capture_output=True, text=True, cwd=proje, env=env, timeout=60)
    say(OK if "import-ok" in (r.stdout or "") else WARN,
        f"MCP server import smoke ({((r.stdout or r.stderr) or '').strip()[:60]})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=".", help="Proje kökü (default: cwd)")
    ap.add_argument("--repair-junctions", action="store_true")
    ap.add_argument("--provision-worktree", metavar="PATH")
    ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--no-seed", action="store_true")
    ap.add_argument("--no-plugins", action="store_true")
    ap.add_argument("--no-smoke", action="store_true")
    a = ap.parse_args()

    proje = Path(a.project).resolve()
    print(f"team_setup — core = {CORE_ROOT}\n            proje = {proje}\n")

    if a.provision_worktree:
        return 0 if provision_worktree(Path(a.provision_worktree).resolve(), proje) else 1
    if a.repair_junctions:
        return 0 if junctions(proje) else 1

    if sys.version_info < MIN_PY:
        say(FAIL, f"Python {MIN_PY[0]}.{MIN_PY[1]}+ gerekli"); return 1
    say(OK, f"Python {sys.version.split()[0]}")

    if not a.no_install and REQ_FILE.exists():
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                            str(REQ_FILE)], capture_output=True, text=True)
        say(OK if r.returncode == 0 else WARN, "pip install (MCP requirements)")

    if not junctions(proje):
        say(FAIL, "junction kurulumu TAMAMLANAMADI — yukarıdaki satırlara bak")
        return 1
    dosya_tamamla(proje)
    hookspath_core()

    if not a.no_plugins:
        alt_arac(proje, "setup_plugins.py", "plugin kurulumu (claude CLI gerekli)")
        npm_clis()  # playwright-cli + ast-grep + mmdc + marp (non-fatal)
    if not a.no_seed:
        alt_arac(proje, "seed_memory.py", "memory tohumu")

    if not (proje / ".conn_adt").exists():
        say(WARN, ".conn_adt YOK — SAP için doldurulmalı (PROJECT_BOOTSTRAP STEP 4)")
    if not a.no_smoke:
        smoke(proje)
    say(OK, "team_setup TAMAM — kabul gate'i: oturum aç → ekran-teyidi + MCP ping + validators")
    return 0


if __name__ == "__main__":
    sys.exit(main())

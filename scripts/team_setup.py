#!/usr/bin/env python3
"""Team Setup — <PROJECT_NAME> repo yeni katılan veya güncellenen geliştirici için.

Tek komutla:
  1. Python versiyonu kontrol et (>= 3.10)
  2. Mevcut repo durumunu kontrol et (clean / kirli)
  3. git pull (varsa upstream)
  4. pip install -r mcp_servers/sap_adt/requirements.txt
  5. .claude/active_package wizard (ilk kez veya değişiklik)
  6. .conn_adt template kontrolü (yoksa uyar)
  7. Statusline smoke test
  8. MCP server smoke test (ping tool)
  9. Özet rapor

Çalıştırma (repo kök dizininde):
  python scripts/team_setup.py

Flags:
  --no-pull      git pull yapma
  --no-install   pip install yapma
  --no-smoke     smoke test yapma
  --pkg <name>   active_package'i bu değere set et (wizard'ı atla)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Force UTF-8 on Windows so Türkçe karakterler hata vermez
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
MIN_PY = (3, 10)
REQ_FILE = REPO_ROOT / "mcp_servers" / "sap_adt" / "requirements.txt"
ACTIVE_PKG_FILE = REPO_ROOT / ".claude" / "active_package"
CONN_FILE = REPO_ROOT / ".conn_adt"
STATUSLINE = REPO_ROOT / "scripts" / "statusline.py"


# ---------------- helpers ----------------

class Step:
    OK = "[ OK ]"
    WARN = "[WARN]"
    FAIL = "[FAIL]"
    INFO = "[INFO]"
    ACTION = "[>>>]"


def say(level: str, msg: str) -> None:
    print(f"{level} {msg}", flush=True)


def run(cmd: list[str], cwd: Path | None = None, check: bool = False, capture: bool = False):
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        check=check,
        capture_output=capture,
        text=True,
    )


# ---------------- steps ----------------

def check_python() -> bool:
    say(Step.INFO, f"Python: {sys.version.split()[0]}  ({sys.executable})")
    if sys.version_info < MIN_PY:
        say(Step.FAIL, f"Python {MIN_PY[0]}.{MIN_PY[1]}+ gerekli. Yükselt ve tekrar dene.")
        return False
    say(Step.OK, "Python versiyonu yeterli")
    return True


def check_git_status() -> bool:
    r = run(["git", "status", "--porcelain"], capture=True)
    if r.returncode != 0:
        say(Step.FAIL, "git çalışmıyor veya bu klasör repo değil")
        return False
    dirty = r.stdout.strip()
    if dirty:
        say(Step.WARN, "Repo'da commit edilmemiş değişiklikler var:")
        for line in dirty.splitlines()[:8]:
            print(f"        {line}")
        say(Step.WARN, "Devam edebilirsin ama pull conflict'e yol açabilir. Önce commit/stash öner.")
    else:
        say(Step.OK, "Repo temiz")
    return True


def git_pull() -> bool:
    say(Step.ACTION, "git pull çalışıyor...")
    r = run(["git", "pull", "--ff-only"], capture=True)
    if r.returncode != 0:
        say(Step.FAIL, f"git pull başarısız: {r.stderr.strip()}")
        say(Step.INFO, "Çözüm: önce kendi değişikliklerini commit/stash et veya rebase yap.")
        return False
    out = (r.stdout + r.stderr).strip()
    for line in out.splitlines()[-5:]:
        print(f"        {line}")
    say(Step.OK, "git pull tamam")
    return True


def pip_install() -> bool:
    if not REQ_FILE.exists():
        say(Step.FAIL, f"requirements bulunamadı: {REQ_FILE}")
        return False
    say(Step.ACTION, f"pip install -r {REQ_FILE.relative_to(REPO_ROOT)} ...")
    r = run([sys.executable, "-m", "pip", "install", "-q", "-r", str(REQ_FILE)], capture=True)
    if r.returncode != 0:
        say(Step.FAIL, "pip install başarısız:")
        print(r.stderr)
        return False
    say(Step.OK, "MCP SDK ve bağımlılıklar yüklü")
    return True


def npm_install_clis() -> bool:
    # Token-verimli CLI'ler (governance/tooling-plugins.md): playwright-cli (tarayıcı doğrulama;
    # skill repo'da .claude/skills/, binary global gerekir) + ast-grep (yapısal kod arama/refactor,
    # AST). NON-FATAL: yoksa playwright MCP / Grep'e düşülür, setup'ı bloklamaz.
    if not shutil.which("npm"):
        say(Step.WARN, "npm yok — playwright-cli + ast-grep atlandı (sonra: npm i -g @playwright/cli @ast-grep/cli)")
        return True
    clis = [
        ("playwright-cli", "@playwright/cli@latest", "token-verimli tarayıcı doğrulama"),
        ("ast-grep", "@ast-grep/cli@latest", "yapısal kod arama/refactor (AST)"),
        ("mmdc", "@mermaid-js/mermaid-cli@latest", "Mermaid diyagram → SVG/PNG (FS/TS/KD)"),
        ("marp", "@marp-team/marp-cli@latest", "Markdown → eğitim slaytı (PDF/PPTX)"),
    ]
    for binary, pkg, desc in clis:
        if shutil.which(binary):
            say(Step.OK, f"{binary} zaten kurulu ({desc})")
            continue
        say(Step.ACTION, f"npm i -g {pkg} ({desc}) ...")
        r = run(["npm", "install", "-g", pkg], capture=True)
        if r.returncode != 0:
            say(Step.WARN, f"{binary} kurulamadı (opsiyonel):")
            print((r.stderr or "")[:200])
        else:
            say(Step.OK, f"{binary} kuruldu")
    return True


def setup_active_package(forced_pkg: str | None) -> bool:
    ACTIVE_PKG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if forced_pkg:
        ACTIVE_PKG_FILE.write_text(forced_pkg + "\n", encoding="utf-8")
        say(Step.OK, f"Aktif paket: {forced_pkg}")
        return True
    if ACTIVE_PKG_FILE.exists():
        cur = ACTIVE_PKG_FILE.read_text(encoding="utf-8").strip()
        say(Step.OK, f"Aktif paket zaten ayarlı: {cur}")
        say(Step.INFO, "Değiştirmek için: --pkg <name> ile tekrar çalıştır")
        return True
    # Wizard
    print()
    print("    Hangi pakette çalışıyorsun? (örn: ZSD001_CLC, ZMM004_CLC)")
    print("    Boş bırakırsan otomatik tespit edilir (en son düzenlenen SESSION_NOTES'tan).")
    try:
        ans = input("    Paket adı: ").strip()
    except EOFError:
        ans = ""
    if ans:
        ACTIVE_PKG_FILE.write_text(ans + "\n", encoding="utf-8")
        say(Step.OK, f"Aktif paket: {ans}")
    else:
        say(Step.INFO, "Otomatik tespit aktif (active_package dosyası yaratılmadı)")
    return True


def check_conn_file() -> bool:
    if CONN_FILE.exists():
        say(Step.OK, ".conn_adt mevcut (SAP credentials)")
        return True
    say(Step.WARN, ".conn_adt yok — SAP'a bağlanamazsın")
    say(Step.INFO, "Şu içerikle bir tane yarat (kendi credentials'larınla):")
    print("""
        ADT_SAP_URL=https://<SYSTEM_ID>:8000
        ADT_SAP_USER=<kendi-user>
        ADT_SAP_PASSWORD=<kendi-password>
        ADT_SAP_CLIENT=100
        ADT_SAP_LANGUAGE=TR
    """)
    say(Step.INFO, "Sonra bu script'i tekrar çalıştır.")
    return True  # warning, not fatal


def smoke_statusline() -> bool:
    if not STATUSLINE.exists():
        say(Step.FAIL, f"statusline.py bulunamadı: {STATUSLINE}")
        return False
    say(Step.ACTION, "Statusline smoke test...")
    payload = json.dumps({"workspace": {"current_dir": str(REPO_ROOT)}})
    r = subprocess.run(
        [sys.executable, str(STATUSLINE)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if r.returncode != 0:
        say(Step.FAIL, f"statusline.py exit {r.returncode}: {r.stderr.strip()}")
        return False
    line = r.stdout.strip()
    say(Step.OK, f"Statusline: {line}")
    return True


def smoke_mcp() -> bool:
    say(Step.ACTION, "MCP server smoke test (ping)...")
    smoke_mod = "mcp_servers.sap_adt.tests.smoke"
    r = subprocess.run(
        [sys.executable, "-m", smoke_mod],
        capture_output=True,
        text=True,
        timeout=20,
        cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        say(Step.FAIL, f"MCP smoke fail (exit {r.returncode})")
        if r.stderr:
            print(r.stderr[-500:])
        return False
    last_lines = [ln for ln in r.stdout.strip().splitlines() if ln.strip()]
    for ln in last_lines[-3:]:
        print(f"        {ln}")
    say(Step.OK, "MCP server ayakta, ping başarılı")
    return True


def setup_plugins_step() -> None:
    """Projenin gerektirdiği Claude Code plugin'lerini kur (idempotent, non-fatal)."""
    script = REPO_ROOT / "scripts" / "setup_plugins.py"
    if not script.exists():
        return
    say(Step.INFO, "Gerekli Claude Code plugin'leri (ui5/playwright/pyright-lsp…)...")
    r = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    for ln in (r.stdout or "").strip().splitlines():
        if any(k in ln for k in ("Kurulu", "Kurulacak", "ÖZET", "Kuruldu", "[OK]", "[FAIL]", "Başarısız", "NOT:")):
            print(f"        {ln.strip()}")
    if r.returncode == 0:
        say(Step.OK, "Gerekli plugin'ler kurulu/kuruldu")
    else:
        say(Step.WARN, "Bazı plugin'ler kurulamadı — yukarıyı oku (claude CLI gerekli); kritik FE/UI işinde tamamla")


def seed_memory_step() -> None:
    """Feedback memory tohumunu bu makineye seed et (merge-safe, non-fatal)."""
    seed_script = REPO_ROOT / "scripts" / "seed_memory.py"
    if not seed_script.exists():
        return
    say(Step.INFO, "Memory tohumu (feedback çalışma-disiplini kuralları)...")
    r = subprocess.run(
        [sys.executable, str(seed_script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    for ln in (r.stdout or "").strip().splitlines():
        if any(k in ln for k in ("ÖZET", "Eklendi", "Atlandı", "Ezildi", "MEMORY.md", "[OK]", "[WARN]", "[FAIL]")):
            print(f"        {ln.strip()}")
    if r.returncode == 0:
        say(Step.OK, "Memory tohumu işlendi (yeni oturumda kurallar yüklenir)")
    else:
        say(Step.WARN, "Memory tohumu atlandı (seed klasörü/erişim) — kritik değil")


def show_next_steps(ok: bool) -> None:
    print()
    print("=" * 60)
    if ok:
        print("  KURULUM TAMAM")
        print("=" * 60)
        print()
        print("  Son adımlar:")
        print("    1. Claude Code panelini TAMAMEN kapat ve yeniden aç")
        print("       (sadece Reload Window MCP'yi yeniden bağlamayabilir)")
        print("    2. Alt çubukta statusline görünür (paket | sprint | VPN | branch)")
        print("    3. Terminal: 'claude mcp list' — 'sap-adt: ✓ Connected' görmen lazım")
        print("    4. Claude'da '/mcp' yaz veya tool isteği yap (örn: 'adt_get ile ZSD001_D_DEMDT')")
        print()
        print("  Sorun olursa: python scripts/team_setup.py --no-pull --no-install")
    else:
        print("  KURULUM TAMAMLANMADI")
        print("=" * 60)
        print("  Yukarıdaki [FAIL] satırlarını oku, sebebi düzeltip tekrar dene.")
    print()


# ---------------- main ----------------

def main() -> int:
    ap = argparse.ArgumentParser(description="<PROJECT_NAME> team setup")
    ap.add_argument("--no-pull", action="store_true", help="git pull yapma")
    ap.add_argument("--no-install", action="store_true", help="pip install yapma")
    ap.add_argument("--no-smoke", action="store_true", help="smoke test yapma")
    ap.add_argument("--pkg", help="active_package değeri (wizard atlanır)")
    args = ap.parse_args()

    print()
    print("=" * 60)
    print("  <PROJECT_NAME> — Team Setup")
    print("=" * 60)
    print(f"  Repo: {REPO_ROOT}")
    print()

    steps_ok = True

    if not check_python():
        steps_ok = False
        show_next_steps(steps_ok)
        return 1

    if not check_git_status():
        steps_ok = False

    if not args.no_pull and steps_ok:
        if not git_pull():
            steps_ok = False

    if not args.no_install and steps_ok:
        if not pip_install():
            steps_ok = False
        npm_install_clis()  # non-fatal — playwright-cli + ast-grep

    if steps_ok:
        setup_active_package(args.pkg)
        check_conn_file()
        setup_plugins_step()  # gerekli Claude Code plugin'leri (idempotent, non-fatal)
        seed_memory_step()    # feedback memory tohumu (merge-safe, non-fatal)

    if not args.no_smoke and steps_ok:
        if not smoke_statusline():
            steps_ok = False
        if not smoke_mcp():
            steps_ok = False

    show_next_steps(steps_ok)
    return 0 if steps_ok else 2


if __name__ == "__main__":
    sys.exit(main())

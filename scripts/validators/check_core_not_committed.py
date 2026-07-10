# -*- coding: utf-8 -*-
"""check_core_not_committed — CORE içeriği proje reposuna SIZMASIN (R1; §11 F1'in git-katmanı).

Kontroller (proje reposunda):
  1. git index'te core-path YOK: `git ls-files core/ .claude/agents .claude/skills
     .claude/commands` boş olmalı (sızıntı = FAIL).
  2. .gitignore SIZINTI-KİLİDİ satırları mevcut: /core/ + .claude/{agents,skills,commands}/
     (eksik satır = FAIL — kilit olmadan bir sonraki commit sızdırır).
  3. `git status` untracked'ta core-path görünmüyor (ignore fiilen çalışıyor kanıtı).

Kasıtlı-kirli senaryoda test edilmelidir (sürekli-PASS tuzağı — GATE-2/C7).
Exit: 0=temiz · 1=sızıntı/kilit-eksiği.
"""
import os
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
# `.claude/rules/` 2026-07-10'da eklendi (L1b). Junction'lanan her tip bu iki listede
# OLMAK ZORUNDA — yoksa core içeriği proje reposuna sessizce commit'lenir.
KILIT_SATIRLARI = ["/core/", ".claude/agents/", ".claude/skills/", ".claude/commands/",
                   ".claude/rules/"]
IZLENEN_YOLLAR = ["core", ".claude/agents", ".claude/skills", ".claude/commands",
                  ".claude/rules"]


def _git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(PROJ), *args], capture_output=True, text=True)
    return r.returncode, (r.stdout or "")


def main() -> int:
    if not (PROJ / ".git").exists():
        print("[SKIP] git reposu değil (prova-dizin olabilir) — kontrol atlandı")
        return 0
    sorun: list[str] = []

    # 1) index sızıntısı
    rc, out = _git("ls-files", "--", *IZLENEN_YOLLAR)
    sizanlar = [l for l in out.splitlines() if l.strip()]
    if sizanlar:
        sorun.append(f"INDEX SIZINTISI: {len(sizanlar)} core dosyası commit'li/staged! İlkleri: "
                     + ", ".join(sizanlar[:5])
                     + " → `git rm -r --cached <yol>` + .gitignore kontrolü + LİDER'e bildir (R1)")

    # 2) .gitignore kilidi
    gi = PROJ / ".gitignore"
    icerik = gi.read_text(encoding="utf-8", errors="ignore") if gi.exists() else ""
    eksik = [s for s in KILIT_SATIRLARI if s not in icerik]
    if eksik:
        sorun.append("GITIGNORE KİLİDİ EKSİK: " + ", ".join(eksik)
                     + " → satırları ekle (init_project şablonunda hazır)")

    # 3) untracked görünürlüğü (ignore fiilen çalışıyor mu)
    rc, out = _git("status", "--porcelain")
    gorunen = [l for l in out.splitlines()
               if l.startswith("??") and any(
                   l[3:].startswith(y + "/") or l[3:].rstrip("/") == y for y in IZLENEN_YOLLAR)]
    if gorunen:
        sorun.append("UNTRACKED'TA CORE GÖRÜNÜYOR (ignore çalışmıyor): "
                     + ", ".join(g[3:] for g in gorunen[:4]))

    if sorun:
        print("[FAIL] check_core_not_committed:")
        for s in sorun:
            print("   ⛔ " + s)
        return 1
    print("[OK] core-sızıntı kilidi sağlam (index temiz + gitignore tam + ignore fiilen çalışıyor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

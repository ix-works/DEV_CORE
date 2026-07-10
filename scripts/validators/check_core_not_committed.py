# -*- coding: utf-8 -*-
"""check_core_not_committed — CORE içeriği proje reposuna SIZMASIN (R1; §11 F1'in git-katmanı).

Kontroller (proje reposunda):
  1. git index'te core-path YOK: `git ls-files core/ .claude/agents .claude/skills
     .claude/commands` boş olmalı (sızıntı = FAIL).
  2. .gitignore SIZINTI-KİLİDİ satırları mevcut: /core/ + .claude/{agents,skills,commands}/
     (eksik satır = FAIL — kilit olmadan bir sonraki commit sızdırır).
  3. `git status` untracked'ta core-path görünmüyor (ignore fiilen çalışıyor kanıtı).
  4. SIR KİLİDİ: `.conn_adt` · `.csrf_token.json` · `.claude/project.local.yaml` hem
     .gitignore'da satır olarak VAR hem de git index'inde YOK.

NEDEN 4 (K3, 2026-07-10): bu üç dosya AYLARCA commit'lendi ve hiçbir katman uyarmadı.
Bu gate .gitignore'u zaten okuyordu ama yalnız core-sızıntısını biliyordu; sır kalıplarını
hiç bilmiyordu. Push'lanmış bir sır GERİ ALINAMAZ (ifşa olmuştur) ve sızma SESSİZDİR —
yeni bir gate değil, var olan kilidin eksik dişi. Satır kontrolü TEK BAŞINA yetmez: dosya
zaten tracked ise .gitignore hiçbir şey yapmaz, o yüzden index de kontrol edilir.

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

# Sır/kimlik dosyaları (K3). Satır eşleşmesi TAM SATIR ile yapılır: `.conn_adt` alt-dizgesi
# `conn/.conn_adt.bak` içinde de geçer → alt-dizge kontrolü yanlış güvence verirdi.
SIR_SATIRLARI = [".conn_adt", ".csrf_token.json", ".claude/project.local.yaml"]
SIR_YOLLARI = [".conn_adt", ".csrf_token.json", ".claude/project.local.yaml",
               "conn/.conn_adt.bak"]


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

    # 4) SIR kilidi — satır VAR mı (tam satır) + index'te YOK mu
    satirlar = {s.strip() for s in icerik.splitlines() if s.strip() and not s.startswith("#")}
    eksik_sir = [s for s in SIR_SATIRLARI if s not in satirlar]
    if eksik_sir:
        sorun.append("SIR KİLİDİ EKSİK (.gitignore): " + ", ".join(eksik_sir)
                     + " → satırları ekle; push'lanmış sır GERİ ALINAMAZ (K3)")

    rc, out = _git("ls-files", "--", *SIR_YOLLARI)
    sizan_sir = [l for l in out.splitlines() if l.strip()]
    if sizan_sir:
        sorun.append("SIR COMMIT'Lİ/STAGED: " + ", ".join(sizan_sir[:4])
                     + " → `git rm --cached <yol>` + kimlik bilgisini DEĞİŞTİR (ifşa varsay)")

    if sorun:
        print("[FAIL] check_core_not_committed:")
        for s in sorun:
            print("   ⛔ " + s)
        return 1
    print("[OK] core-sızıntı kilidi sağlam (index temiz + gitignore tam + ignore fiilen çalışıyor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

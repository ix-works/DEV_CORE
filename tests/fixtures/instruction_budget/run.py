#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixture — check_instruction_budget (C-BUD-01) P/N doğrulaması.

P: temiz sentetik ağaç → 0 bulgu, exit 0 (--strict dahil).
N: şişkin (>200 soyulmuş satır) + blok-tekrarlı ağaç → WARN'lar; default exit 0 (warn-first
   sözleşmesi), --strict exit 1. Ayrıca frontmatter/yorum SOYMA kanıtı: ham 210 satır ama
   soyulunca 190 kalan dosya bulgu ÜRETMEZ (üst-harness semantiği).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
V = REPO / "scripts" / "validators" / "check_instruction_budget.py"
SONUC: list[tuple[bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((kosul, f"{ad}{(' -> ' + detay) if detay else ''}"))


def kos(kok: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(V), "--root", str(kok), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="bud_fix_"))

    # --- P: temiz ağaç
    p = tmp / "temiz"
    (p / "claude" / "rules").mkdir(parents=True)
    (p / "CLAUDE.md").write_text("# proje\n" + "\n".join(f"- kural {i}" for i in range(40)) + "\n",
                                 encoding="utf-8")
    (p / "claude" / "rules" / "a.md").write_text("---\npaths:\n  - '**/*.abap'\n---\n# a\n- x\n",
                                                 encoding="utf-8")
    rc, out = kos(p)
    kontrol("P1 temiz -> 0 bulgu + [OK]", rc == 0 and "[OK]" in out and "[WARN]" not in out)
    rc, out = kos(p, "--strict")
    kontrol("P2 temiz --strict -> exit 0", rc == 0, f"exit={rc}")

    # --- P3 SOYMA: ham 210+ satır ama frontmatter+yorum soyulunca ~190 → bulgu YOK
    s = tmp / "soyma"
    s.mkdir()
    fm = "---\n" + "\n".join(f"meta{i}: x" for i in range(12)) + "\n---\n"
    yorum = "<!--\n" + "\n".join(f"bakim notu {i}" for i in range(10)) + "\n-->\n"
    govde = "\n".join(f"- kural {i}" for i in range(188)) + "\n"
    (s / "CLAUDE.md").write_text(fm + yorum + govde, encoding="utf-8")
    ham = len((fm + yorum + govde).splitlines())
    rc, out = kos(s)
    kontrol(f"P3 ham {ham}>200 ama soyulmus<200 -> bulgu YOK (soyma dogru)",
            rc == 0 and "[WARN]" not in out)

    # --- N: şişkin + blok-tekrarlı
    n = tmp / "sisik"
    (n / "claude" / "rules").mkdir(parents=True)
    blok = "\n".join(f"tekrar-blok satiri {i}" for i in range(6))
    uzun = "\n".join(f"- madde {i}" for i in range(230))
    (n / "CLAUDE.core.md").write_text(uzun + "\n\n" + blok + "\n\nara\n\n" + blok + "\n",
                                      encoding="utf-8")
    rc, out = kos(n)
    kontrol("N1 tavan asimi WARN", "> 200" in out and "[WARN]" in out)
    kontrol("N2 blok-tekrari WARN", "TEKRARI" in out)
    kontrol("N3 default exit 0 (warn-first sozlesmesi)", rc == 0, f"exit={rc}")
    rc, out = kos(n, "--strict")
    kontrol("N4 --strict -> exit 1", rc == 1, f"exit={rc}")

    ok = sum(1 for k, _ in SONUC if k)
    for k, m in SONUC:
        print(("  [OK] " if k else "  [FAIL] ") + m)
    print(f"\n{ok}/{len(SONUC)} OK   (sandbox: {tmp.name})")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())

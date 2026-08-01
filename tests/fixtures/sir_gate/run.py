#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sir_gate fixture — core_precommit 5. kontrol (SIR DOSYASI).

NEDEN VAR (2026-08-01 bug-avi, CANLI ihlal):
`scripts/.conn_adt` DEV_CORE'da ILK cekirdek commit'inden beri (f85e3fd, 2026-07-08)
PUBLIC repoda TAKIPLIYDI ve hicbir katman gormedi:
  - `check_core_not_committed.py` bu sinifi korur ama PROJE repolarinda kosar; core'un
    KENDISINI denetleyen yoktu (core-ci'da adim yok, pre-commit'te kontrol yoktu),
  - ustelik o validator'un pathspec'i JOKERSIZDI (`.conn_adt`) -> yalniz KOKU esliyordu:
        git ls-files -- .conn_adt      -> bos   ("temiz" der)
        git ls-files -- "*.conn_adt"   -> scripts/.conn_adt
O dosyanin degerleri placeholder'di (sizinti-desenimizle 0 eslesme) — kimlik sizmadi.
Ama kanal aciktI: `create_conn_file()` cwd'ye `.conn_adt` YAZAR, yani herhangi bir alt
dizinde GERCEK bir baglanti dosyasi olusup commit'lenebilirdi. Public'e giden sir GERI
ALINAMAZ (K3).

Senaryolar (hepsi ayri, sentetik git repolarinda; ana repolara DOKUNULMAZ):
  S1 kokte  .conn_adt staged            -> BLOK (exit 1)
  S2 derin  alt/derin/.conn_adt staged  -> BLOK  (asil vaka: derinlik)
  S3 turev  .conn_adt.bak staged        -> BLOK
  S4 .csrf_token.json staged            -> BLOK
  S5 sir cikarilinca                    -> SERBEST (exit 0)
  S6 SABLON claude/conn_adt.template    -> SERBEST (deger tasimaz; FP olmamali)
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# parents: [0]=sir_gate [1]=fixtures [2]=tests [3]=REPO KOKU. parents[2] yazmak
# `tests/scripts/...` verir -> dosya yok -> python exit 2 -> fixture "6/6 FAIL" der ve
# sebebi kod sanilir. (Ilk kurulumda tam bu oldu; var-mi kontrolu bu yuzden eklendi.)
GATE = Path(__file__).resolve().parents[3] / "scripts" / "git-hooks" / "core_precommit.py"
if not GATE.exists():  # sessiz yanlis-sonuc yerine gurultulu hata
    raise SystemExit(f"[fixture-hatasi] gate bulunamadi: {GATE}")


def _repo() -> Path:
    d = Path(tempfile.mkdtemp(prefix="sir_gate_"))
    subprocess.run(["git", "init", "-q", "."], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    return d


def _kos(d: Path) -> int:
    # ⚠ ORTAM İZOLASYONU ZORUNLU: miras alınan `CLAUDE_PROJECT_DIR` gate'e BAŞKA bir repoyu
    # çözdürür ve fixture sessizce anlamsızlaşır (ilk kurulumda tam bu oldu: 6/6 "FAIL",
    # sebebi kod değil harness'tı). Aynı ders `run_ozel`'de de kodlu.
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDE_PROJECT_DIR" and not k.startswith("IX_")}
    env["IX_GENERICIZE_BLOCKLIST"] = "ZZZ_SENTETIK_ESLESMEZ"
    p = subprocess.run([sys.executable, str(GATE)], cwd=d, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode


def _yaz(d: Path, rel: str, icerik: str = "ADT_SAP_URL=https://x\nADT_SAP_PASSWORD=gizli\n") -> None:
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(icerik, encoding="utf-8")


def main() -> int:
    sonuc: list[tuple[str, bool, str]] = []

    def vaka(ad: str, rel: str, beklenen: int, icerik: str | None = None) -> None:
        d = _repo()
        (d / "normal.md").write_text("# normal\n", encoding="utf-8")
        if icerik is None:
            _yaz(d, rel)
        else:
            _yaz(d, rel, icerik)
        subprocess.run(["git", "add", "-A"], cwd=d, check=True)
        rc = _kos(d)
        sonuc.append((ad, rc == beklenen, f"exit={rc} beklenen={beklenen}"))

    vaka("S1 kokte .conn_adt -> BLOK", ".conn_adt", 1)
    vaka("S2 DERIN alt/derin/.conn_adt -> BLOK", "alt/derin/.conn_adt", 1)
    vaka("S3 turev .conn_adt.bak -> BLOK", "conn/.conn_adt.bak", 1)
    vaka("S4 .csrf_token.json -> BLOK", "alt/.csrf_token.json", 1)
    vaka("S6 SABLON conn_adt.template -> SERBEST (FP yok)",
         "claude/conn_adt.template", 0,
         icerik="# sablon: yalniz alan adlari, DEGER YOK\nADT_SAP_URL=\nADT_SAP_PASSWORD=\n")

    # S5 — sir cikarilinca serbest (ayni repoda once BLOK, sonra SERBEST)
    d = _repo()
    (d / "normal.md").write_text("# normal\n", encoding="utf-8")
    _yaz(d, "alt/derin/.conn_adt")
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    rc_once = _kos(d)
    subprocess.run(["git", "rm", "-q", "--cached", "alt/derin/.conn_adt"], cwd=d, check=True)
    rc_sonra = _kos(d)
    sonuc.append(("S5 sir cikarilinca SERBEST", rc_once == 1 and rc_sonra == 0,
                  f"once={rc_once} sonra={rc_sonra}"))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())

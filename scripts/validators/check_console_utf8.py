#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — non-ASCII basan her script konsol kodlamasını UTF-8'e sabitliyor mu?

NEDEN: Windows konsolu/pipe'ı `cp1252`'dir. Türkçe basan script `UnicodeEncodeError` ile
ÇÖKER → `exit 1`. Bir validator/test için bu, gerçek FAIL'den ayırt edilemez:
  - negatif test hiçbir şey kanıtlamaz (çökme "FAIL" sanılır)
  - CI'da sahte FAIL / yerelde sahte PASS
2026-07-09'da üç script arka arkaya bu yüzden çöktü; repo'daki 94 script zaten doğru
yapıyordu. Konvansiyon vardı, ENFORCEMENT yoktu → bu validator.

ENFORCES: C-ENC-01 (non-ASCII basan script UTF-8 konsol koruması taşımalı)
Onarım:   `from utils.console import utf8_konsol; utf8_konsol()`
          veya `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

def core_kok(argv: list[str] | None = None) -> Path:
    """Taranacak CORE kökü — öncelik: `--kok <yol>` → env `IX_CORE_ROOT` → `__file__` türevi.

    ⛔ K2 (2026-08-20): kök yalnız `Path(__file__).resolve().parents[2]` idi ⇒ gate
    HİÇBİR sentetik ağaca yöneltilemiyordu. Sonucu "izole edilemez" değil, ÖLÇÜLEMEZdi:
    dedektörün gerçekten yakalayıp yakalamadığını kanıtlamanın tek yolu canlı core'a
    kasten bozuk bir script koymaktı (kimse yapmaz) ⇒ gate fiilen KANITSIZ duruyordu.

    ⚠ `project_root()` BİLEREK kullanılmaz (CORE-01'in tersi görünse de doğrusu budur):
    bu gate CORE'un KENDİ script'lerini ölçer, projenin değil. Projeye çevirmek gate'i
    sessizce boşaltırdı (projede `scripts/` ya yok ya da bambaşka bir ağaç).
    Varsayılan davranış AYNEN korunur — argüman/env verilmezse eski kök çözülür.
    """
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    if "--kok" in argv:
        i = argv.index("--kok")
        if i + 1 < len(argv):
            return Path(argv[i + 1]).resolve()
    env = os.environ.get("IX_CORE_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


CORE = core_kok()

# Çıktı üreten çağrılar
_BASAR = re.compile(r"\bprint\s*\(|sys\.(stdout|stderr)\.write\s*\(")
# Kabul edilen korumalar
_KORUMA = re.compile(r"reconfigure\s*\(\s*encoding|utf8_konsol\s*\(|TextIOWrapper\s*\(|"
                     r"PYTHONIOENCODING")

# Bu dosyalar çıktı basmaz ya da saf kütüphanedir; taranır ama non-ASCII+print yoksa geçer.
ATLA_DIZIN = {"__pycache__", "TempScripts", "tests"}


def main() -> int:
    kok = core_kok()          # her cagrida TAZE (bayat modul-global degil)
    riskli: list[str] = []
    toplam = 0
    for f in sorted((kok / "scripts").rglob("*.py")):
        if any(p in ATLA_DIZIN for p in f.parts):
            continue
        try:
            s = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if not _BASAR.search(s):
            continue
        if not any(ord(c) > 127 for c in s):
            continue
        toplam += 1
        if not _KORUMA.search(s):
            riskli.append(f.relative_to(kok).as_posix())

    if riskli:
        print(f"  [FAIL] {len(riskli)}/{toplam} script non-ASCII basıyor ama UTF-8 konsol "
              f"koruması YOK → Windows cp1252'de ÇÖKER (exit 1, sahte FAIL):")
        for r in riskli:
            print(f"         - {r}")
        print("         Onarım: `from utils.console import utf8_konsol; utf8_konsol()`")
        print("         veya    `sys.stdout.reconfigure(encoding=\"utf-8\", errors=\"replace\")`")
        return 1
    print(f"  [OK] non-ASCII basan {toplam} script'in tamamı UTF-8 konsol korumalı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""abaplint_failopen fixture — "OLCEMEDIM = TEMIZ" SINIFI (check_abaplint.py).

NEDEN VAR (2026-08-14, canli vaka):
`check_abaplint.py` yalnizca ISSUE_RE'ye uyan satirlari sayiyordu; eslesen satir yoksa
KOSULSUZ `OK — ... abaplint temiz (tuned)` + exit 0 donuyordu. `returncode`a hic bakilmiyordu.
Sonuc: AYNI BOZUK dosya icin bir kosumda exit 0 "temiz", ikinci kosumda exit 1 parser_error
alindi (npx soguk-baslatma / fetch gurultusu ilk kosumda ayristirilabilir cikti uretmemisti).
⇒ Gate'in yesili KANIT TASIMIYORDU ve verdict deterministik degildi.

Kardes sinif: `dogrulama_kosamadi` fixture'i (ucuncu deger "KOSAMADI" sessizce olumluya
katlaniyor). Burada da ucuncu deger var: **temiz · bulgu var · OLCUM YAPILAMADI**.

POLITIKA: "temiz" verdict'i yalniz abaplint'in KENDI ozet satiri gorulunce verilir:
    abaplint: <N> issue(s) found, <M> file(s) analyzed      (M >= 1)
Ozet yoksa / M=0 ise / N ayristirdigimiz satir sayisiyla tutmuyorsa -> FAIL (exit 1).

OLCULEN GERCEK CIKTI BICIMI (abaplint 2.120.5, 2026-08-14):
  temiz -> stdout 'abaplint: 0 issue(s) found, 1 file(s) analyzed'                      rc=0
  bozuk -> stdout '<dosya>[42, 3] - ... (parser_error) [E]' + ozet satiri               rc=1

⚠ KONTROL GRUBU BU TESTIN OMURGASI:
  S1 (gercekten temiz -> exit 0) ve S2 (gercek bulgu -> exit 1) satirlari, kilidin
  ASIRI-SIKI olmadigini kanitlar. Silinirlerse test "her seye FAIL de" seviyesine duser
  ve gercek isi bloklar.

⚠ KONTROL GRUBU TUZAGI (bu fixture yazilirken YASANDI, tekrar dusmeyelim):
  Ilk kurulumda kiyaslanan ESKI surum kopyasi repo disina konmustu; `CONFIG` yolu
  `Path(__file__).parents[1]` ile cozuldugu icin config BULUNAMIYOR, script her senaryoda
  "SKIP — config yok" deyip 0 donuyordu. Yani "eski surum yesil veriyordu" tablosu tamamen
  sahteydi (S2 dahil hepsi 0). Modulu yukledikten sonra CONFIG ELLE PINLENIR.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

HEDEF = REPO / "scripts" / "validators" / "check_abaplint.py"
CONFIG = REPO / "scripts" / "abaplint" / "abaplint.json"

# Gercek bir .clas.abap'a ihtiyac var (detect() class'i tanisin). Fixture kendi ornegini tasir:
# repo icerigine bagimli olmasin (baska paket silinirse test cokmesin).
ORNEK_CLAS = """CLASS zcl_lint_fixture DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    METHODS run.
ENDCLASS.

CLASS zcl_lint_fixture IMPLEMENTATION.
  METHOD run.
    DATA(lv_x) = 1.
  ENDMETHOD.
ENDCLASS.
"""

OZET_TEMIZ = "abaplint: 0 issue(s) found, 1 file(s) analyzed\n"
BULGU_SATIRI = ('src\\zcl_lint_fixture.clas.abap[42, 3] - Statement does not exist, '
                '"ENDMETHOD" (parser_error) [E]\n')
OZET_BIR = "abaplint: 1 issue(s) found, 1 file(s) analyzed\n"

# (ad, stdout, stderr, returncode, beklenen_exit, neden_onemli)
SENARYOLAR = [
    ("S1 gercekten temiz", OZET_TEMIZ, "", 0, 0,
     "KONTROL GRUBU: kilit asiri-siki degil, gercek temiz hala yesil"),
    ("S2 gercek bulgu", BULGU_SATIRI + OZET_BIR, "", 1, 1,
     "KONTROL GRUBU: gercek bulgu hala yakalaniyor (regresyon yok)"),
    ("S3 BOS cikti", "", "", 1, 1,
     "FAIL-OPEN: npx soguk-baslatma/ag hatasi -> eskiden 'temiz'"),
    ("S4 npx gurultusu, ozet YOK", "npm warn exec\n", "ERR fetch failed\n", 1, 1,
     "FAIL-OPEN: pin fetch edilemedi -> eskiden 'temiz'"),
    ("S5 ozet var ama 0 dosya analiz edildi",
     "abaplint: 0 issue(s) found, 0 file(s) analyzed\n", "", 0, 1,
     "lint kostu ama HICBIR dosyaya bakmadi (src/ yerlesimi bozuk) -> eskiden 'temiz'"),
    ("S6 sayi uyusmazligi (ISSUE_RE desync)",
     "abaplint: 3 issue(s) found, 1 file(s) analyzed\n", "", 1, 1,
     "3 bulgu var ama 0'ini ayristirabildik -> bulgular sessizce kaybolurdu"),
    ("S7 upstream cikti bicimi degisti",
     "abaplint >> 2 problems in 1 file\n", "", 1, 1,
     "abaplint bicim degistirirse gate SESSIZ YESILE dusmemeli"),
]

SONUC: list[tuple[str, bool, str]] = []


def _sonuc(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def _yukle():
    spec = importlib.util.spec_from_file_location("_fixture_check_abaplint", HEDEF)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[fixture-hatasi] modul yuklenemedi: {HEDEF}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # ⛔ CONFIG'i ELLE PINLE — yukaridaki "kontrol grubu tuzagi" notuna bak.
    mod.CONFIG = CONFIG
    if not mod.CONFIG.exists():
        raise SystemExit(f"[fixture-hatasi] abaplint config yok: {mod.CONFIG}")
    return mod


def _kostur(mod, artefakt: Path, out: str, err: str, rc: int) -> tuple[int, str]:
    """subprocess.run'i stub'la; abaplint HIC calistirilmaz (offline-guvenli, hizli)."""
    def sahte_run(*_a, **_k):
        return types.SimpleNamespace(stdout=out, stderr=err, returncode=rc)

    gercek = subprocess.run
    eski_argv = sys.argv
    subprocess.run = sahte_run          # type: ignore[assignment]
    mod.subprocess.run = sahte_run
    sys.argv = ["check_abaplint.py", str(artefakt)]
    so, se = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
            kod = mod.main()
    finally:
        subprocess.run = gercek         # type: ignore[assignment]
        mod.subprocess.run = gercek
        sys.argv = eski_argv
    return kod, so.getvalue() + se.getvalue()


def main() -> int:
    import tempfile

    mod = _yukle()
    with tempfile.TemporaryDirectory() as td:
        artefakt = Path(td) / "zcl_lint_fixture.clas.abap"
        artefakt.write_text(ORNEK_CLAS, encoding="utf-8")

        for ad, out, err, rc, bekl, neden in SENARYOLAR:
            kod, metin = _kostur(mod, artefakt, out, err, rc)
            ok = (kod == bekl)
            _sonuc(f"{ad} -> exit {bekl}", ok,
                   f"alinan={kod} beklenen={bekl} | {neden} | cikti={metin[:200]!r}")

        # Ek: "temiz" verdict'i KANIT TASIMALI — ozet sayilari ciktida gorunsun.
        kod, metin = _kostur(mod, artefakt, OZET_TEMIZ, "", 0)
        _sonuc("temiz verdict'i ozet kanitini BASIYOR",
               kod == 0 and "file(s) analyzed" in metin,
               f"exit={kod} cikti={metin[:200]!r}")

        # Ek: FAIL dallari ham ciktiyi gostermeli (teshis edilemez bir FAIL ise yaramaz).
        kod, metin = _kostur(mod, artefakt, "npm warn exec\n", "", 1)
        _sonuc("FAIL dali HAM CIKTIYI raporluyor",
               kod == 1 and "npm warn exec" in metin,
               f"exit={kod} cikti={metin[:200]!r}")

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad}")
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print(f"         -> {detay}")
    print(f"\n{gecen}/{len(SONUC)} OK")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())

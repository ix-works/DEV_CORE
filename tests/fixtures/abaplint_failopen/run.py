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
import re
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

# (ad, stdout, stderr, returncode, beklenen_exit, beklenen_status, beklenen_measured, neden_onemli)
#
# ⚠ `beklenen_measured` NEDEN ESKI TABLODA YOKTU (2026-08-29 eklendi):
# Eski tablo yalnizca EXIT KODUNU olcuyordu. Ama S1 (gercek temiz) ile asagidaki
# K1/K2/K3 SKIP senaryolarinin HEPSI `exit 0` doner ⇒ exit kodu bu ikisini AYIRT
# EDEMEZ. Yani eski korpus, "olcemedim"i "temiz"den ayiran davranisi HIC olcemezdi;
# ayrimi tasiyan tek kanal `IX-GATE-STATUS` satiridir ve capayi ORAYA koymak gerekir.
SENARYOLAR = [
    ("S1 gercekten temiz", OZET_TEMIZ, "", 0, 0, "OK", "true",
     "KONTROL GRUBU: kilit asiri-siki degil, gercek temiz hala yesil"),
    ("S2 gercek bulgu", BULGU_SATIRI + OZET_BIR, "", 1, 1, "FINDING", "true",
     "KONTROL GRUBU: gercek bulgu hala yakalaniyor (regresyon yok)"),
    ("S3 BOS cikti", "", "", 1, 1, "FAIL", "false",
     "FAIL-OPEN: npx soguk-baslatma/ag hatasi -> eskiden 'temiz'"),
    ("S4 npx gurultusu, ozet YOK", "npm warn exec\n", "ERR fetch failed\n", 1, 1, "FAIL", "false",
     "FAIL-OPEN: pin fetch edilemedi -> eskiden 'temiz'"),
    ("S5 ozet var ama 0 dosya analiz edildi",
     "abaplint: 0 issue(s) found, 0 file(s) analyzed\n", "", 0, 1, "FAIL", "false",
     "lint kostu ama HICBIR dosyaya bakmadi (src/ yerlesimi bozuk) -> eskiden 'temiz'"),
    ("S6 sayi uyusmazligi (ISSUE_RE desync)",
     "abaplint: 3 issue(s) found, 1 file(s) analyzed\n", "", 1, 1, "FAIL", "false",
     "3 bulgu var ama 0'ini ayristirabildik -> bulgular sessizce kaybolurdu"),
    ("S7 upstream cikti bicimi degisti",
     "abaplint >> 2 problems in 1 file\n", "", 1, 1, "FAIL", "false",
     "abaplint bicim degistirirse gate SESSIZ YESILE dusmemeli"),
]

# Makinece okunur durum satirinin capasi. Satir-basi DEMIRLI (`re.M`): bu markoru
# TARIF eden yorum/docstring metni BEYAN sayilmasin (kardes ders: ENFORCES_RE capasi).
DURUM_RE = re.compile(
    r"^IX-GATE-STATUS: gate=check_abaplint status=(\S+) measured=(true|false) reason=(\S+)",
    re.M)

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


def _kostur(mod, artefakt: Path, out: str, err: str, rc: int,
            patlat: BaseException | None = None) -> tuple[int, str]:
    """subprocess.run'i stub'la; abaplint HIC calistirilmaz (offline-guvenli, hizli).

    `patlat` verilirse stub o istisnayi atar -> gercek offline/npx-yok yolu (`except
    Exception` dali) kosar. Bu dal STUB'LI korpusta bugune dek HIC olculmemisti:
    stub daima basarili donuyordu, dolayisiyla "tool-unavailable" SKIP yolu ve onun
    `exit 0`'i test disindaydi. Kaydin (#5) tam olarak sikayet ettigi yol o.
    """
    def sahte_run(*_a, **_k):
        if patlat is not None:
            raise patlat
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

        for ad, out, err, rc, bekl, bekl_st, bekl_ms, neden in SENARYOLAR:
            kod, metin = _kostur(mod, artefakt, out, err, rc)
            ok = (kod == bekl)
            _sonuc(f"{ad} -> exit {bekl}", ok,
                   f"alinan={kod} beklenen={bekl} | {neden} | cikti={metin[:200]!r}")
            # AYNI kosumun makinece okunur beyani da dogru olmali (exit kodu + beyan
            # birbirini yalanlarsa tuketici hangisine inanacagini bilemez).
            m = DURUM_RE.search(metin)
            _sonuc(f"{ad} -> IX-GATE-STATUS status={bekl_st} measured={bekl_ms}",
                   bool(m) and m.group(1) == bekl_st and m.group(2) == bekl_ms,
                   f"beyan={m.groups() if m else None} beklenen=({bekl_st},{bekl_ms}) | cikti={metin[:200]!r}")

        # Ek: "temiz" verdict'i KANIT TASIMALI — ozet sayilari ciktida gorunsun.
        kod, metin = _kostur(mod, artefakt, OZET_TEMIZ, "", 0)
        _sonuc("temiz verdict'i ozet kanitini BASIYOR",
               kod == 0 and "file(s) analyzed" in metin,
               f"exit={kod} cikti={metin[:200]!r}")

        # ⭐ #69 — "temiz" verdict'i KAPSAMINI da BEYAN etmeli.
        # Capa `check_syntax` + "DERLEME KANITI DEGILDIR": "(tuned)" kelimesi TEK BASINA
        # yetmez (eski surumde de vardi ve yine yanlis okundu). Bu satir silinirse kayit
        # #69 sessizce geri acilir.
        _sonuc("temiz verdict'i KAPSAM BEYANI tasiyor (#69)",
               kod == 0 and "check_syntax" in metin and "DERLEME KANITI" in metin.upper(),
               f"exit={kod} cikti={metin[:400]!r}")

        # Ek: FAIL dallari ham ciktiyi gostermeli (teshis edilemez bir FAIL ise yaramaz).
        kod, metin = _kostur(mod, artefakt, "npm warn exec\n", "", 1)
        _sonuc("FAIL dali HAM CIKTIYI raporluyor",
               kod == 1 and "npm warn exec" in metin,
               f"exit={kod} cikti={metin[:200]!r}")

        # ────────────────────────────────────────────────────────────────────────
        # ⭐ #5 ①/③ — UC SKIP YOLU: hepsi `exit 0` doner (BILINCLI: offline zincir
        # kirilmasin) ama HICBIRI "temiz" DEGILDIR. Ayrimi tasiyan tek sey durum
        # satiridir. Bu uc senaryo, exit-kodu-tabanli bir tuketicinin (bugunku
        # `run_review.py`) neyi goremedigini korpusta GORUNUR kilar.
        # ────────────────────────────────────────────────────────────────────────
        # K1 — config yok
        gercek_cfg = mod.CONFIG
        mod.CONFIG = Path(td) / "olmayan" / "abaplint.json"
        kod, metin = _kostur(mod, artefakt, OZET_TEMIZ, "", 0)
        mod.CONFIG = gercek_cfg
        m = DURUM_RE.search(metin)
        _sonuc("K1 config YOK -> exit 0 AMA measured=false reason=config-missing",
               kod == 0 and bool(m) and m.group(2) == "false" and m.group(3) == "config-missing",
               f"exit={kod} beyan={m.groups() if m else None} cikti={metin[:200]!r}")

        # K2 — desteklenmeyen obje tipi (FM/FUGR). Kaydin (2026-08-17) CANLI vakasi buydu:
        # `ZSD000_FM_SCREEN_GEN` icin gate SKIP+exit 0 dedi, ajan bunu "gecti" sanmadi ama
        # MAKINE ayirt edemiyordu. Capa `unsupported-object-type`: "lintlenecek sey yok"
        # DEGIL, "bu yerlesimi henuz kurmuyoruz" (abapGit fugr yerlesimiyle OLCULEBILIR).
        fm_artefakt = Path(td) / "zsd000_fm_probe.fugr.abap"
        fm_artefakt.write_text("FUNCTION zsd000_fm_probe.\nENDFUNCTION.\n", encoding="utf-8")
        kod, metin = _kostur(mod, fm_artefakt, OZET_TEMIZ, "", 0)
        m = DURUM_RE.search(metin)
        _sonuc("K2 FM/FUGR -> exit 0 AMA measured=false reason=unsupported-object-type",
               kod == 0 and bool(m) and m.group(2) == "false"
               and m.group(3) == "unsupported-object-type",
               f"exit={kod} beyan={m.groups() if m else None} cikti={metin[:200]!r}")

        # K3 — npx/offline: `subprocess.run` PATLAR (stub'li korpusta ilk kez olculuyor).
        kod, metin = _kostur(mod, artefakt, "", "", 0,
                             patlat=FileNotFoundError("npx bulunamadi"))
        m = DURUM_RE.search(metin)
        _sonuc("K3 npx YOK (istisna) -> exit 0 AMA measured=false reason=tool-unavailable",
               kod == 0 and bool(m) and m.group(2) == "false" and m.group(3) == "tool-unavailable",
               f"exit={kod} beyan={m.groups() if m else None} cikti={metin[:200]!r}")

        # KONTROL GRUBU (bu blogun omurgasi): ayni `exit 0`, ama S1'de measured=TRUE.
        # Bu satir olmadan yukaridaki uclu "her seye measured=false de" ile de gecerdi.
        kod_t, metin_t = _kostur(mod, artefakt, OZET_TEMIZ, "", 0)
        m_t = DURUM_RE.search(metin_t)
        _sonuc("KONTROL GRUBU: ayni exit 0'da gercek temiz measured=true",
               kod_t == 0 and bool(m_t) and m_t.group(2) == "true" and m_t.group(3) == "clean",
               f"exit={kod_t} beyan={m_t.groups() if m_t else None}")

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad}")
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print(f"         -> {detay}")
    print(f"\n{gecen}/{len(SONUC)} OK")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())

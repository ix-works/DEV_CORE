#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ix_doctor KABLOLAMA KONTROLU — korunan tool kumesi ELLE TUTULMAZ, KODDAN TURETILIR.

NEDEN BU KORPUS VAR (infra-findings 2026-08-22 "M11", duzeltildi 2026-08-29)
---------------------------------------------------------------------------
`ix_doctor._kablolama_kontrol()` "guard'in kodda korudugu her tool, PreToolUse
matcher'iyla ona yonleniyor mu?" sorusunu sorar. Ama BEKLENEN KUME elle tutulan bir
tuple'di:

    _GUARD_KORUDUGU_TOOLLAR = ("Bash","PowerShell","Edit","Write","MultiEdit","NotebookEdit")

Ayni olgu iki yerde yasarsa biri bayatlar -- ve BAYATLAMISTI. Olculdu (2026-08-29):
`pre_tool_guard` bugun 16 tool adini isliyor, elle liste 6'sini tasiyordu ⇒ 10 MCP
tool'u (`mcp__sap-adt__adt_push_source`, `...adt_activate`, `...adt_post_shell` ...)
bu kontrolde HIC denetlenmiyordu. Kontrol yine de "guard'in korudugu 6 tool'un
TAMAMI matcher'da" diye PASS basiyordu: cumle DOGRU, PAYDA yanlis. Sessiz kapsam kaybi.

⛔ BU KORPUSUN OLCTUGU SEY "yeni yetenek" DEGIL, PAYDANIN CANLILIGI:
  · S1  turetme calisiyor ve payda ELLE LISTEDEN GENIS (>6) -- ölü/dar kume degil
  · S2  ⭐ REGRESYON CAPASI: matcher TAM OLARAK eski elle listeyi kapsiyorsa
        (MCP yok) kontrol FAIL vermeli. ESKI KOD BURADA PASS DERDI. Bu senaryo,
        M11'in tarif ettigi sessiz kapsam kaybinin birebir sekli.
  · S3  KONTROL GRUBU: matcher gercekten hepsini kapsiyorsa PASS (asiri-siki degil)
  · S4  ⛔ OLCULEMEDI != TEMIZ: turetme kirilirsa BOS kume ile "hepsi kapsandi"
        denmez; FAIL + gerekce doner. (Bos kume donseydi kontrol "0 tool'un tamami
        matcher'da" diyerek SESSIZCE yesile duserdi = olu gate.)

⛔ IZOLASYON: gercek proje `.claude/settings.json` DOKUNULMAZ. Her senaryo kendi
gecici PROJE kokunu kurar ve `CLAUDE_PROJECT_DIR` ile oraya isaret eder.

KOSUM:  python tests/fixtures/ix_doctor_kablolama/run.py
        ... --mutasyon-elle-liste   (kume KODDAN degil ESKI elle listeden gelir -> S2 duser)
        ... --mutasyon-bos-sessiz   (turetme hatasi sessizce PASS'a duser  -> S4 duser)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)
"""
from __future__ import annotations

import importlib.util
import json
import re
import os
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
DOCTOR = REPO / "scripts" / "ix_doctor.py"

# Fix oncesi elle tutulan kume (regresyon capasi -- SILINEMEZ: S2'nin anlami budur).
ESKI_ELLE_LISTE = ("Bash", "PowerShell", "Edit", "Write", "MultiEdit", "NotebookEdit")

CAPA_TURETME = "    kume = adlar.get(\"pre_tool_guard\", set())\n"
CAPA_BOS = "    if turetme_hatasi:\n"

MUTLAR = {
    # Fix'in SOKUMU: kume yine ELLE listeden gelir -> MCP tool'lari denetlenmez (S2 duser).
    "--mutasyon-elle-liste": (
        CAPA_TURETME,
        "    kume = {\"Bash\", \"PowerShell\", \"Edit\", \"Write\", \"MultiEdit\", "
        "\"NotebookEdit\"}  # MUTASYON: elle liste\n"),
    # AYRI DEGISMEZ: turetme HATASI sessizce yutulur -> bos kume ile PASS (S4 duser).
    # ⛔ Ustteki mutasyon bunu KAPSAMAZ: biri "kume dogru kaynaktan mi", oteki
    # "kaynak KIRILDIGINDA dogru sey mi oluyor" sorusunu olcer.
    "--mutasyon-bos-sessiz": (CAPA_BOS, "    if False:\n"),
}

SONUC: list[tuple[str, bool, str]] = []


def ekle(ad: str, kosul, aciklama: str = "") -> None:
    SONUC.append((ad, bool(kosul), aciklama))


def _modul(kaynak: str | None, tdp: Path):
    """ix_doctor'u (gerekirse mutasyonlu kopyasini) yukle.

    ⛔ Kopya, GERCEK `scripts/` agacinin ICINE konur: `_guard_korudugu_toollar()`
    kardes `validators/` dizinini `Path(__file__).parent/"validators"` ile bulur.
    Baska bir yere koysaydik olculen sey "fix" degil KURULUM HATASI olurdu
    (KURULAMADI != KACTI).
    """
    if kaynak is None:
        yol = DOCTOR
    else:
        yol = DOCTOR.parent / "_ix_doctor_mutant_fixture.py"
        yol.write_text(kaynak, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"_ixd_{yol.stem}", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, (yol if kaynak is not None else None)


def _proje(tdp: Path, ad: str, matcher_bloklari: list) -> Path:
    kok = tdp / ad
    (kok / ".claude").mkdir(parents=True, exist_ok=True)
    (kok / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {"PreToolUse": matcher_bloklari}}, indent=2),
        encoding="utf-8")
    return kok


def _kanca():
    return [{"type": "command", "command": "python",
             "args": ["scripts/hook_shim.py", "pre_tool_guard"]}]


def _kos(mod, kok: Path):
    """`_kablolama_kontrol` PROJ'u modul-duzeyinde okur -> PROJ'u pinle."""
    eski = mod.PROJ
    mod.PROJ = kok
    try:
        return mod._kablolama_kontrol()
    finally:
        mod.PROJ = eski


def main() -> int:
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))
    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    kaynak = None
    if secili:
        ham = DOCTOR.read_text(encoding="utf-8")
        eski, yeni = MUTLAR[secili[0]]
        if eski not in ham:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        kaynak = ham.replace(eski, yeni, 1)

    tmp = Path(tempfile.mkdtemp(prefix="ixd_kablolama_"))
    mod, gecici_modul = _modul(kaynak, tmp)
    try:
        korunan, onekler, hata = mod._guard_korudugu_toollar()

        # === S1 TURETME CANLI + PAYDA ELLE LISTEDEN GENIS ====================
        # ⛔ ERISILEBILIRLIK CENGELI: turetme bos/dar donerse kontrol "hepsi kapsandi"
        # der ve OLU bir gate olur. Payda > 6 olmasi, kumenin gercekten KODDAN
        # geldiginin kanitidir (elle liste tam 6 idi).
        ekle("S1 kume KODDAN turetiliyor + payda eski elle listeden GENIS",
             not hata and len(korunan) > len(ESKI_ELLE_LISTE)
             and set(ESKI_ELLE_LISTE) <= korunan,
             f"payda={len(korunan)} (eski elle liste={len(ESKI_ELLE_LISTE)}) hata={hata!r}")

        # === S2 ⭐ REGRESYON: eski elle listeyi kapsayan matcher YETMEZ ========
        # Matcher TAM OLARAK eski 6 tool'u yonlendiriyor; MCP tool'lari yonlendirmiyor.
        # ESKI KOD: "6/6 kapsandi" -> PASS. YENI KOD: MCP tool'lari DELIK -> FAIL.
        kok = _proje(tmp, "s2", [{"matcher": "|".join(ESKI_ELLE_LISTE), "hooks": _kanca()}])
        r = _kos(mod, kok)
        durum = [d for d, _ in r]
        metin = " ".join(m for _, m in r)
        ekle("S2 REGRESYON: matcher yalniz eski 6 tool'u yonlendirir -> FAIL + MCP tool'lari adiyla",
             mod.FAIL in durum and "DELİK" in metin and "mcp__sap-adt__" in metin,
             f"durum={durum} metin={metin[:220]!r}")

        # === S3 KONTROL GRUBU: gercekten tam kapsayan matcher -> PASS =========
        # ⛔ SILINEMEZ: S2 tek basina "her seye FAIL de" mutasyonuyla da gecerdi.
        kok = _proje(tmp, "s3", [
            {"matcher": "Bash|PowerShell|mcp__sap-adt__.*", "hooks": _kanca()},
            {"matcher": "Edit|Write|MultiEdit", "hooks": _kanca()},
            {"matcher": "NotebookEdit", "hooks": _kanca()}])
        r = _kos(mod, kok)
        durum = [d for d, _ in r]
        metin = " ".join(m for _, m in r)
        ekle("S3 KONTROL GRUBU: tam kapsayan matcher -> PASS + PAYDA ciktida",
             mod.FAIL not in durum and f"{len(korunan)} tool" in metin,
             f"durum={durum} metin={metin[:220]!r}")

        # === S4 ⛔ OLCULEMEDI != TEMIZ =======================================
        # Turetme kirilirsa (kardes modul yok/bozuk) kontrol PASS DEMEMELI.
        eski_fn = mod._guard_korudugu_toollar
        mod._guard_korudugu_toollar = lambda: (set(), [], "turetme modulu yuklenemedi (sentetik)")
        try:
            kok = _proje(tmp, "s4", [{"matcher": ".*", "hooks": _kanca()}])
            r = _kos(mod, kok)
        finally:
            mod._guard_korudugu_toollar = eski_fn
        durum = [d for d, _ in r]
        metin = " ".join(m for _, m in r)
        ekle("S4 turetme kirik -> FAIL + 'ÖLÇÜLEMEDİ' (matcher '.*' olsa BILE PASS DEGIL)",
             mod.FAIL in durum and "ÖLÇÜLEMEDİ" in metin,
             f"durum={durum} metin={metin[:220]!r}")

        # === S5 ELLE LISTE KAYNAKTA ARTIK YOK (capa) =========================
        # ⛔ Ikinci gercek geri gelirse bu satir kirmizi yanar.
        # ⛔ CAPA SATIR-BASI DEMIRLI OLMALI: ilk yazimda duz `in` testiydi ve KENDI
        # duzeltmemizin ACIKLAMA YORUMUNA takildi (yorum, kaldirilan satiri ALINTILIYOR).
        # Bu evde olculmus sinifin AYNASI: "bir markoru TARIF eden metin, o markoru
        # BEYAN etmis sayilamaz" -- tersi de dogru: bir atamayi ANLATAN yorum, o atama
        # DEGILDIR. Yoksa gerekceyi yazmak fixture'i kirmizi yakardi (yanlis tesvik).
        ham = DOCTOR.read_text(encoding="utf-8")
        ekle("S5 `_GUARD_KORUDUGU_TOOLLAR` ATAMASI (satir basi) kaynakta YOK — ikinci gercek geri gelmesin",
             re.search(r"^_GUARD_KORUDUGU_TOOLLAR\s*=", ham, re.M) is None,
             "elle tutulan kume = ikinci gercek (olculmus curume sinifi)")
    finally:
        if gecici_modul is not None and gecici_modul.exists():
            gecici_modul.unlink()

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print(f"         -> {detay}")
    print(f"\nix_doctor_kablolama: {gecen}/{len(SONUC)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
        return 0 if gecen < len(SONUC) else 1
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())

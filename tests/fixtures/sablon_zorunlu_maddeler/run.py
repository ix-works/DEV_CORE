#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SABLON KUSURLARI: her yeni paket/brif yanlisi MIRAS ALIYORDU.

A) `templates/new-package/.rules.md.tmpl` — DTEL/Domain oneki YANLISTI
   Sablon `{PKG}_DE_*`/`{PKG}_DTEL_*` ve `{PKG}_DOM_*` yaziyordu. Kurumsal standart
   (`standards/01-naming.md` §4.4.5) ise Data Element = **E** (`ZMM001_E_AMOUNT`),
   Domain = **D** (`ZSD001_D_AMOUNT`) diyor; canli sistemde `_DOM_`/`_DE_` onekli
   TEK BIR OBJE YOK (olculdu 2026-08-17).
   ⭐ SINIF KANITI: ayni duzeltme UC AYRI pakette ELLE yapildi (2026-05-15 · 2026-08-05 ·
   2026-08-17). Uc turda uc kez elle duzeltmek, duzeltmenin YANLIS KATMANDA yapildiginin
   kanitidir — kok sablondaydi ve her yeni paket onu miras aliyordu.
   ⚠ Kural dosyasi validator'un GIRDISIDIR: yanlis oldugunda standarda uygun ad yazan
   gelistirici VALIDATOR HATASI alir; ya kural bukulur ya ad bozulur.

B) `claude/templates/spawn-brief.md` §9 + `brifing-lint` — "ENGELLENIRSEN" maddesi YOKTU
   VAKA: `isolation:"worktree"` ile acilan infra ajaninin worktree'si YANLIS repoda
   olustu; charter'i canli agaca yazmayi yasakladigi icin YAZACAK YERI YOKTU. Yasaga
   uydu, bekledi, HABER VERMEDI -> **26 dk olculebilir cikti SIFIR**. Watchdog
   "heartbeat taze" diyordu (canlilik olcer, ILERLEME olcmez). Kusur ajanda degil BRIFTEYDI.

   ⭐ LINT EKSENI OLCULEREK DARALTILDI (587 gercek brif, transcript korpusu):
     · ham "madde var mi?"                -> **%86,7** atesler ⇒ KULLANILAMAZ (uyari korlugu)
     · DAR (baska-agac + yazma isi)       -> **%18,4** kapsam / **%16,0** atesleme
       ⇒ KB-01'in olculmus gurultu tabaniyla (%13,9) ayni bant; mevcut GOREV ekseni %25,0.

  A1-A2  sablon <-> STANDART esligi (E/D) + eski onekler geri gelmemis
  A3     3. BAGLAM: sablonun diger DDIC satirlari standartla tutarli
  A4-A5  ACIK KARAR notu: `Class` satirinin 2. bicimi (`ZCL_{PKG}_*`) hicbir
         otoriteye uymuyor ve YER-TUTUCU YOK (`PKG_NOZ`) diye duzeltilemiyor ->
         celiski hic degilse BELGELENMIS olmali + not DAYANAGINI tasimali
  B1-B2  lint DAR eksen: baska-agac+yazma & madde YOK -> atesler / madde VAR -> susar
  B3-B4  ⭐ FP CAPALARI: yalniz-okuma isi ateslemez · kisa brif muaf
  B5     sablon §9 zorunlu maddeyi TASIYOR
  B6     mevcut GOREV/KANIT-KURAL ekseni BOZULMADI (regresyon)
  M1-M3  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/sablon_zorunlu_maddeler/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import re
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
TMPL = CORE / "templates" / "new-package" / ".rules.md.tmpl"
STD = CORE / "standards" / "01-naming.md"
BRIEF = CORE / "claude" / "templates" / "spawn-brief.md"
LINT = CORE / "scripts" / "hooks" / "watchdog_launch.py"


def _std_ddic_onekleri() -> dict[str, str]:
    """`standards/01-naming.md` §4.4.5 tablosundan {obje: onek} — TEK OTORITE.

    ⚠ Onekler burada KOPYALANMAZ, standarttan OKUNUR: ikinci kopya bayatlar ve
    korpus standardi degil kendi ezberini dogrular hale gelir.
    """
    metin = STD.read_text(encoding="utf-8")
    i = metin.find("#### 4.4.5")
    if i < 0:
        return {}
    blok = metin[i:i + 2500]
    out = {}
    for satir in blok.splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*Z or Y\s*\|\s*`([A-Z]+)`\s*\|", satir)
        if m:
            out[m.group(1).strip()] = m.group(2)
    return out


def _tmpl_regex(obje: str, src: str) -> str | None:
    for satir in src.splitlines():
        m = re.match(r"\|\s*" + re.escape(obje) + r"\s*\|\s*`([^`]+)`", satir)
        if m:
            return m.group(1)
    return None


def _tmpl_satir(obje: str, src: str) -> str | None:
    """Sablondaki naming tablosunun `| <obje> | ... |` satirini AYNEN dondurur.

    ⚠ `_tmpl_regex` yalnizca 2. hucredeki ILK backtick grubunu verir; bir hucre
    iki bicim tasiyorsa (`{PKG}_CL_*` veya `ZCL_{PKG}_*`) ikincisini GORMEZ.
    Capa dosyanin TAMAMINDA aranirsa da olmaz: ayni dize aciklama notunun
    tarihsel alintilarinda da gecer (olculdu 2026-08-29: dosyada 3, satirda 1)
    ⇒ satir duzelse bile not capayi diri tutar, senaryo KENDINI EMEKLIYE
    AYIRAMAZ. Bu yuzden kapsam SATIRDIR.
    """
    for satir in src.splitlines():
        if re.match(r"\|\s*" + re.escape(obje) + r"\s*\|", satir):
            return satir
    return None


def _lint_yukle(src: str):
    """watchdog_launch'i TAZE namespace'e yukler (mutasyon icin)."""
    mod = types.ModuleType("watchdog_launch_x")
    mod.__file__ = str(LINT)
    exec(compile(src, str(LINT), "exec"), mod.__dict__)
    return mod


def _payload(prompt: str) -> dict:
    return {"tool_input": {"prompt": prompt}}


# --- Gercek sekilden turetilmis brifingler (adlar jenerik) -------------------
_DOLGU = ("GOREV: bilesen uzerinde calis. KANIT KURAL: tahmin yasak, olcerek ilerle. "
          "Cikti formati: rapor. Arac kilavuzu: repo araclari. " * 6)
BRIF_YAZMA_ENGELSIZ = ("GOREV: worktree C:/IX/_wt/ornek icinde fix uygula ve commit et. "
                       "KANIT KURAL: olc. " + _DOLGU)
BRIF_YAZMA_ENGELLI = (BRIF_YAZMA_ENGELSIZ +
                      " ENGELLENIRSEN: yazacak yerin yoksa TAHMIN ETME, DERHAL "
                      "SendMessage(to:'main') ile bildir.")
BRIF_SALT_OKUMA = ("GOREV: worktree icindeki kodu OKU ve bulgulari rapor et. "
                   "KANIT KURAL: olc. Hicbir sey degistirme. " + _DOLGU)
BRIF_KISA = "GOREV: test echo. worktree fix uygula."


def senaryolar(mod) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    tmpl = TMPL.read_text(encoding="utf-8")
    std = _std_ddic_onekleri()

    # --- A1: sablon <-> STANDART esligi (E/D) ------------------------------
    beklenen = {"Data Element": std.get("Data Element"), "Domain": std.get("Domain")}
    gercek = {o: _tmpl_regex(o, tmpl) for o in beklenen}
    uyum = all(
        beklenen[o] and gercek[o] and re.search(r"_" + beklenen[o] + r"_", gercek[o])
        for o in beklenen)
    ekle("A1 sablon DTEL/Domain oneki STANDARTLA (§4.4.5) esit: E / D",
         uyum, "standart=%s sablon=%s" % (beklenen, gercek))

    # --- A2: eski YANLIS onekler geri gelmemis -----------------------------
    kotu = [k for k in ("_DE_", "_DTEL_", "_DOM_")
            if re.search(r"\|\s*(Data Element|Domain)\s*\|[^|]*" + k, tmpl)]
    ekle("A2 eski yanlis onekler (_DE_/_DTEL_/_DOM_) naming satirinda YOK",
         not kotu, "bulunan=%s" % kotu)

    # --- A3: 3. BAGLAM — diger DDIC satirlari da standartla tutarli --------
    # (Sablon degistirilirken komsu satirin bozulmadiginin capasi.)
    komsu = {"Structure": "S", "Table": "T", "Table Type": "TT"}
    sapan = [o for o, p in komsu.items()
             if not (_tmpl_regex(o, tmpl) or "").count("_" + p + "_")]
    ekle("A3 3.baglam: Structure/Table/TableType onekleri bozulmadi",
         not sapan, "sapan=%s" % sapan)

    # --- A4: ⭐ CELISKI KENDINI BELGELEMELI (2026-08-29) --------------------
    # Sablonun `Class` satirinin 2. bicimi (`ZCL_{PKG}_*`) UC otoritenin
    # HICBIRINE uymuyor: standart §4.4.3 `ZCL_<PKG#>_*` (paket adinin Z'siz
    # hali) diyor, canli artefakt `ZCL_<Z'siz>_*` kullaniyor, sablonun bicimi
    # ise bugune dek 0 dosyada gecmis. Duzeltilemiyor cunku `{PKG}`nin Z'siz
    # hali icin `bootstrap_package.py`de yer-tutucu (`PKG_NOZ`) YOK.
    # Celiskiyi SESSIZCE tasimak, her yeni paketin uc kaynaktan hangisine
    # uyacagini TAHMIN etmesi demektir (A1/A2'nin kapattigi sinifin ta kendisi).
    # ⚠ Bu capa KENDINI EMEKLIYE AYIRIR: yer-tutucu eklenip satir
    # `ZCL_{PKG_NOZ}_*` olarak hizalanirsa not ZORUNLU OLMAKTAN CIKAR. Yani
    # dogru fix'i BLOKLAMAZ, yalniz sessiz birakilmasini bloklar.
    # ⓘ 2026-08-29 REPOINT: bu capa `Message Class` ekseninde dogmustu; o eksen
    # (`{PKG}` -> `{PKG}_MSG`, kullanici karari) KAPANDI ve senaryolar kendini
    # emekliye ayirdi — ama MUTASYONLAR ayrilamadi (M4 [YAMA TUTMADI] /
    # M5 [KACTI] ⇒ suit exit 1). Capa hala ACIK olan `Class` eksenine tasindi.
    cls_satir = _tmpl_satir("Class", tmpl) or ""
    uyumsuz = "ZCL_{PKG}_*" in cls_satir
    # ⚠ Capa eksen ADINI da tasir: bambaska bir konudaki artik bir "AÇIK KARAR"
    # basligi bu eksenin belgelenmis oldugu ANLAMINA GELMEZ.
    notu_var = "AÇIK KARAR — `Class`" in tmpl
    ekle("A4 ⭐sablon<->standart `Class` (2.bicim) celiskisi BELGELENMIS "
         "(hizalanirsa not zorunlu degil)",
         (not uyumsuz) or notu_var,
         "satir=%r uyumsuz=%s not_var=%s" % (cls_satir[:90], uyumsuz, notu_var))

    # --- A5: not BOS BIR MARKER OLMAMALI — dayanagini tasimali -------------
    # "Marker koy gec" refleksine karsi: not, kararin iki ENGELINI de adiyla
    # anmali, yoksa sonraki okuyan yine tahmin eder.
    if uyumsuz:
        dayanak = all(x in tmpl for x in
                      ("standards/01-naming.md", "bootstrap_package.py", "PKG_NOZ"))
        ekle("A5 AÇIK KARAR notu dayanagini tasiyor (standart + yer-tutucu sinirini anar)",
             dayanak, "eksik=%s" % [x for x in ("standards/01-naming.md",
                                                "bootstrap_package.py", "PKG_NOZ")
                                    if x not in tmpl])
    else:
        ekle("A5 AÇIK KARAR notu dayanagini tasiyor (satir hizali -> gerekmiyor)", True)

    # --- B1: DAR eksen atesler --------------------------------------------
    n = mod._brifing_lint(_payload(BRIF_YAZMA_ENGELSIZ)) or ""
    ekle("B1 baska-agac + yazma + madde YOK -> lint UYARIR",
         "ENGELLENIRSEN" in n, "not=%r" % n[:110])

    # --- B2: madde VARSA susar (ayirt edici ikiz) -------------------------
    n2 = mod._brifing_lint(_payload(BRIF_YAZMA_ENGELLI)) or ""
    ekle("B2 ayni brif + madde VAR -> bu eksen SUSAR",
         "ENGELLENIRSEN" not in n2, "not=%r" % n2[:110])

    # --- B3: ⭐ FP CAPASI — salt-okuma isi ateslemez ----------------------
    n3 = mod._brifing_lint(_payload(BRIF_SALT_OKUMA)) or ""
    ekle("B3 FP capasi: yalniz-OKUMA isi bu ekseni atesleMEZ",
         "ENGELLENIRSEN" not in n3, "not=%r" % n3[:110])

    # --- B4: FP CAPASI — kisa/mekanik brif muaf ---------------------------
    n4 = mod._brifing_lint(_payload(BRIF_KISA))
    ekle("B4 FP capasi: <400 karakter brif MUAF (hicbir not yok)",
         n4 is None, "not=%r" % (n4 or "")[:80])

    # --- B5: sablon zorunlu maddeyi tasiyor -------------------------------
    b = BRIEF.read_text(encoding="utf-8")
    ekle("B5 spawn-brief.md §9 zorunlu maddeyi TASIYOR",
         "ENGELLENİRSEN" in b and "SendMessage" in b and "26 dakika" in b,
         "uzunluk=%d" % len(b))

    # --- B6: REGRESYON — mevcut GOREV/KANIT-KURAL ekseni bozulmadi --------
    n5 = mod._brifing_lint(_payload("x" * 500)) or ""
    ekle("B6 regresyon: sablonsuz brifte GOREV/KANIT KURAL ekseni HALA uyarir",
         "R2 sablon izleri eksik" in n5, "not=%r" % n5[:110])

    return out


MUTASYONLAR = [
    ("M1 sablonda eski oneki geri getir (_DOM_)",
     "tmpl",
     lambda s: s.replace("| Domain | `{PKG}_D_*` | `^{PKG}_D_[A-Z0-9_]+$` |",
                         "| Domain | `{PKG}_DOM_*` | `^{PKG}_DOM_[A-Z0-9_]+$` |")),
    ("M2 lint'in ENGELLENIRSEN eksenini sok",
     "lint",
     lambda s: s.replace("        if yer and yazma and not engel:",
                         "        if False:")),
    ("M3 ekseni GENISLET (yazma sarti kalksin -> salt-okumada da atesler)",
     "lint",
     lambda s: s.replace("        if yer and yazma and not engel:",
                         "        if yer and not engel:")),
    # A4'un degismezi: celiski VARKEN notu SIL -> korpus KIRMIZI olmali.
    # (Yoksa "not koydum" iddiasi olculemez ve ilk temizlikte sessizce kaybolur.)
    ("M4 AÇIK KARAR notunun basligini sil (celiski yine sessiz kalir)",
     "tmpl",
     lambda s: s.replace("AÇIK KARAR — `Class`", "eski not")),
    # A5'in AYRI degismezi: baslik dursun ama DAYANAK kaybolsun (bos marker).
    # ⚠ Iki gecisin IKISI de silinir — A5 `in` ile bakar, tek gecis kalsaydi
    # mutasyon KACARDI. Yan etki bilincli: not icindeki `ZCL_{PKG_NOZ}_*`
    # ornegi `ZCL_{PKG}_*`e doner; A4'un capasi SATIR kapsamli oldugu icin
    # (bkz. `_tmpl_satir`) bu sahte bir `uyumsuz` uretmez.
    ("M5 not dursun ama yer-tutucu sinirini anan dayanagi sil (bos marker)",
     "tmpl",
     lambda s: s.replace("PKG_NOZ", "PKG")),
]


def main() -> int:
    print("=" * 78)
    print("sablon_zorunlu_maddeler — sablon kusuru = her yeni paket/brif miras alir")
    print("=" * 78)

    ham_lint = LINT.read_text(encoding="utf-8")
    ham_tmpl = TMPL.read_text(encoding="utf-8")

    mod = _lint_yukle(ham_lint)
    sonuc = senaryolar(mod)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    for ad, hedef, mut in MUTASYONLAR:
        ham = ham_tmpl if hedef == "tmpl" else ham_lint
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            if hedef == "tmpl":
                TMPL.write_text(bozuk, encoding="utf-8")
                try:
                    m_res = senaryolar(mod)
                finally:
                    TMPL.write_text(ham_tmpl, encoding="utf-8")   # HER halukarda geri al
            else:
                m_res = senaryolar(_lint_yukle(bozuk))
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # Sablon dosyasi geri alindi mi (mutasyon kalintisi = SESSIZ BOZULMA)
    print("\n--- kalinti kontrolu ---")
    geri = TMPL.read_text(encoding="utf-8") == ham_tmpl
    print("  [%s] sablon dosyasi mutasyondan SONRA geri alindi" % ("OK" if geri else "KALINTI"))

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik or not geri:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        if not geri:
            print("FAIL — sablon dosyasinda MUTASYON KALINTISI kaldi")
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

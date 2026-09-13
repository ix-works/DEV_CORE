#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI ODATA REFS KAPSAMI (Q284) — dosya VAR ama binding GORULMUYOR => yine "TEMIZ" demesin.

=== OLCULMUS KUSUR ===
`scripts/check_ui_odata_refs.py` yedi desenin hepsini CIFT tirnakla ariyordu. Gercek bir
rapor app'inde iki entity yolu da gorunmuyordu:
  XML  rows="{ path: '/ZSD001_C_SUM', parameters: {...} }"      (tek tirnak)
  JS   var ENTITY = "/ZSD001_C_DETAIL"; ... bindRows({ path: sPath })   (degisken)
Sonuc: `=== read/binding -> entity set ===` bolumu BOS, hukum `TEMIZ` + exit 0.
Olculdu 2026-09-13 (19 app'lik gercek korpus, canli $metadata): 7/19 app bu durumdaydi.
Kardes kayit Q232 ("0 DOSYA taradim" = TEMIZ) — ayni yanlis-guven ekseni, bir kat asagida.

=== FP SINIRI (olculdu, vektorlerle civili) ===
Genel `"/[A-Z]..."` literal kurali REDDEDILDI: 512 adayin 67'si JSON-model yolu
(`setProperty("/Busy")`), 37'si baska servisin seti. => V5 bu literallerin KIRMIZI
URETMEDIGINI, yalniz beyan satirinda SAYILDIGINI civiler.
Degisken yolu KIRMIZI degil UYARI'dir (korpusta 2/16 aday baska servisin setiydi) => V3.

  V1  ⭐ AYIRT EDICI  tek tirnakli XML path   -> [OK] entity satiri (once: bolum BOS)
  V1b ⭐ AYIRT EDICI  degisken yolu           -> [OK] degisken satiri (once: gorunmez)
  V1c FP capasi       vaka seklinde app'te gercek kusur YOK -> hukum TEMIZ + exit 0
  V1d beyan           degiskenli Filter SAYILIR + view {Prop} + kapsam disi dosyalar yazilir
  V2  ⭐ POZ.KONTROL  tek tirnakli YANLIS ad  -> exit 1 + ENTITY SET YOK (once: TEMIZ/0)
  V3  ⭐ SINIR        degisken yolu metadata'da yok -> [?] UYARI, exit 0 (KIRMIZI DEGIL)
  V4  ⭐ AYIRT EDICI  0 entity referansi      -> hukum "TEMIZ DEGIL: entity OLCULMEDI", exit 0
  V5  FP capasi       JSON-model "/Ad" literalleri -> KIRMIZI yok, "4 diger" diye sayilir
  V6  KONTROL GRUBU   yalniz cift tirnak app  -> TEMIZ + exit 0 (eski kodla AYNI hukum)
  V6b KONTROL GRUBU   cift tirnakli yanlis ad -> exit 1 (eski kodla AYNI hukum)
  V7  3. BAGLAM       JS tek tirnak read/callFunction/Filter/$select (korpusta 0 isabet)
  V8  3. BAGLAM       fragment/ + entitySet='X' + const/let bildirimi
  V9  SINIR           dengesiz tirnak '/Ad" referans SAYILMAZ (geri-referans)
  V10 ⭐ AYIRT EDICI  0 property referansi    -> "TEMIZ DEGIL: property OLCULMEDI"
  M1..M4             fix'i sok -> korpus KIRMIZI olmali

TAMAMEN CEVRIMDISI: arac BELLEKTE calistirilir, `load_conn`/`fetch_metadata` sentetik
$metadata dondurecek sekilde yamanir (yama main() CAGRISINDAN once yapilir; main global
adlari cagri aninda cozer). Gercek giris noktasi `main()` + argparse aynen kosar.

Kosum: python tests/fixtures/ui_odata_refs_kapsami/run.py          (exit 0 = PASS)
Kipler: --mutasyon-tirnak · --mutasyon-degisken · --mutasyon-bos-eksen · --mutasyon-uyari-kirmizi
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
ARAC = REPO / "scripts" / "check_ui_odata_refs.py"

# ⛔ BILINMEYEN KIP SESSIZCE YESIL GECMESIN (negatif_test_harness sozlesmesi).
GECERLI_KIP = {"--mutasyon-tirnak", "--mutasyon-degisken", "--mutasyon-bos-eksen",
               "--mutasyon-uyari-kirmizi"}
for _a in sys.argv[1:]:
    if _a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {_a!r} — gecerli: {sorted(GECERLI_KIP)}")
        sys.exit(2)
KIP = set(sys.argv[1:])

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def dur(neden: str) -> None:
    """SAYI RAPORLAMADAN durus — `KURULAMADI` != `KACTI`."""
    print(f"[DURDU] KURULAMADI: {neden}")
    sys.exit(2)


# ══════════════════════════════════════════════════════════════════════════════
# MUTASYON — BUGUNKU kaynaktan turetilir (pinli SHA YOK). Her capa TAM 1 kez
# bulunmali; bulunamazsa KURULAMADI (sessiz kacak yok).
# ══════════════════════════════════════════════════════════════════════════════
TIRNAK_SINIFI = "([\"\\'])"        # kaynaktaki metin: (["\'])
TIRNAK_DESEN_SATIRLARI = ("RE_CALLFN = ", "RE_READ = ", "RE_PATH = ", "RE_ENTITYSET = ",
                          "RE_FILTER = ", "RE_ORDERBY = ", "RE_SELECT = ")


def _tek_degistir(metin: str, eski: str, yeni: str, kip: str) -> str:
    if metin.count(eski) != 1:
        dur(f"{kip}: capa {metin.count(eski)} kez bulundu (1 bekleniyor) — mutasyon BAYATLADI")
    return metin.replace(eski, yeni)


def _mut_tirnak(metin: str) -> str:
    """Yedi kontrol desenini eski CIFT-TIRNAK-ONLY haline dondur (kusurun birebir eski hali)."""
    satirlar = metin.split("\n")
    for onek in TIRNAK_DESEN_SATIRLARI:
        idx = [i for i, s in enumerate(satirlar) if s.startswith(onek)]
        if len(idx) != 1 or TIRNAK_SINIFI not in satirlar[idx[0]]:
            dur(f"--mutasyon-tirnak: {onek!r} satiri {len(idx)} kez / tirnak sinifi yok — BAYATLADI")
        satirlar[idx[0]] = satirlar[idx[0]].replace(TIRNAK_SINIFI, '(")') + "  # MUTASYON"
    return "\n".join(satirlar)


MUTASYONLAR = {
    "--mutasyon-tirnak": _mut_tirnak,
    # degisken yolu ekseni hic taranmasin
    "--mutasyon-degisken": lambda m: _tek_degistir(
        m, "        for m in RE_DEGISKEN.finditer(txt):",
        "        for m in []:  # MUTASYON", "--mutasyon-degisken"),
    # 0 referansli eksen yine "TEMIZ" desin
    "--mutasyon-bos-eksen": lambda m: _tek_degistir(
        m, '    olculmeyen = [e for e, n in (("entity", n_entity), ("property", len(props))) if n == 0]',
        "    olculmeyen = []  # MUTASYON", "--mutasyon-bos-eksen"),
    # FP SINIRI: degisken yolu uyarisi KIRMIZIYA terfi etsin (baska servisin seti alarm uretir)
    "--mutasyon-uyari-kirmizi": lambda m: _tek_degistir(
        m, "                uyari += 1\n",
        "                uyari += 1; red += 1  # MUTASYON\n", "--mutasyon-uyari-kirmizi"),
}


def kaynak() -> str:
    if not ARAC.is_file():
        dur(f"arac yok: {ARAC}")
    metin = ARAC.read_text(encoding="utf-8")
    for kip in sorted(KIP):
        metin = MUTASYONLAR[kip](metin)
    return metin


KAYNAK = kaynak()

MD_XML = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="1.0" xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx">
 <edmx:DataServices><Schema Namespace="ZSD001_UI_O2">
  <EntityType Name="SumType"><Key><PropertyRef Name="Alan1"/></Key>
   <Property Name="Alan1" Type="Edm.String"/><Property Name="Alan2" Type="Edm.String"/>
  </EntityType>
  <EntityContainer Name="C" m:IsDefaultEntityContainer="true">
   <EntitySet Name="ZSD001_C_SUM" EntityType="ZSD001_UI_O2.SumType"/>
   <EntitySet Name="ZSD001_C_DETAIL" EntityType="ZSD001_UI_O2.SumType"/>
   <EntitySet Name="ZSD001_I_VH" EntityType="ZSD001_UI_O2.SumType"/>
   <FunctionImport Name="DoAction" ReturnType="ZSD001_UI_O2.SumType" m:HttpMethod="POST">
    <Parameter Name="P1" Type="Edm.String" Mode="In"/>
   </FunctionImport>
  </EntityContainer>
 </Schema></edmx:DataServices>
</edmx:Edmx>
"""

TMP = tempfile.TemporaryDirectory(prefix="ui_odata_refs_")
KOK = Path(TMP.name)


def app(ad: str, dosyalar: dict[str, str]) -> Path:
    kok = KOK / ad
    for rel, icerik in dosyalar.items():
        p = kok / "webapp" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(icerik, encoding="utf-8", newline="\n")
    return kok


def kos(app_yolu: Path) -> tuple[int, str]:
    """Araci BELLEKTE calistir; ag yerine sentetik $metadata. (rc, stdout)."""
    mod = types.ModuleType("_ui_odata_refs")
    mod.__file__ = str(ARAC)
    try:
        exec(compile(KAYNAK, str(ARAC), "exec"), mod.__dict__)
    except Exception as exc:                      # kurulum hatasi != kacan mutasyon
        dur(f"arac yuklenemedi: {exc!r}")
    mod.load_conn = lambda cwd: {}
    mod.fetch_metadata = lambda cfg, service: MD_XML
    tampon = io.StringIO()
    eski_argv = sys.argv
    sys.argv = ["check_ui_odata_refs.py", "--app", str(app_yolu), "--service", "ZSD001_UI_O2"]
    try:
        with contextlib.redirect_stdout(tampon):
            mod.main()
        rc = -1                                   # main exit'siz dondu = sozlesme disi
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as exc:                      # COKTU != FAIL: gorunur detayla dus
        return -9, tampon.getvalue() + f"\nCOKTU: {exc!r}"
    finally:
        sys.argv = eski_argv
    return rc, tampon.getvalue()


def hukum(cikti: str) -> str:
    satirlar = [s for s in cikti.strip().splitlines() if s.strip()]
    return satirlar[-1] if satirlar else ""


CTRL_BASI = 'sap.ui.define(["sap/ui/model/Filter"], function (Filter) {\n  "use strict";\n'
CTRL_SONU = "});\n"

# ── V1: VAKANIN SEKLI ────────────────────────────────────────────────────────
rc1, c1 = kos(app("vaka", {
    "view/List.view.xml":
        '<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns:table="sap.ui.table">\n'
        "  <table:Table id=\"tbl\" rows=\"{ path: '/ZSD001_C_SUM', parameters: { countMode: 'Inline' } }\"/>\n"
        "</mvc:View>\n",
    "controller/List.controller.js": CTRL_BASI +
        '  var ENTITY_SUMMARY = "/ZSD001_C_SUM";\n'
        '  var ENTITY_DETAIL = "/ZSD001_C_DETAIL";\n'
        "  function rangeToFilter(sProp, oR) {\n"
        '    return new Filter(sProp, "EQ", oR.value1);\n'
        "  }\n"
        "  return {\n"
        "    apply: function (bDetail) {\n"
        "      var sPath = bDetail ? ENTITY_DETAIL : ENTITY_SUMMARY;\n"
        '      this.byId("tbl").bindRows({ path: sPath, filters: [new Filter("Alan1", "EQ", "x"), rangeToFilter("Alan2", {})] });\n'
        "    }\n"
        "  };\n" + CTRL_SONU,
}))
kontrol("V1 ⭐ tek tirnakli XML path entity ekseninde GORUNUR (once: bolum BOS)",
        "  [OK] ZSD001_C_SUM\n" in c1, f"rc={rc1} cikti={c1[:300]!r}")
kontrol("V1b ⭐ degiskene atanmis yol GORUNUR (once: hicbir desene uymuyordu)",
        "  [OK] ZSD001_C_DETAIL [controller/List.controller.js]" in c1, f"cikti={c1[:400]!r}")
kontrol("V1c FP capasi: gercek kusuru olmayan vaka-sekilli app -> TEMIZ + exit 0",
        rc1 == 0 and hukum(c1).startswith("TEMIZ ("), f"rc={rc1} hukum={hukum(c1)!r}")
kontrol("V1d beyan: degiskenli Filter SAYILIR + view {Prop} + kapsam disi dosyalar yazilir",
        "1 degiskenli new Filter(<degisken>, ...)" in c1
        and "view/fragment {Prop} binding'leri" in c1
        and "DISINDAKI dosyalar" in c1, f"cikti={c1[-500:]!r}")

# ── V2: POZITIF KONTROL — tek tirnakli YANLIS ad ──────────────────────────────
rc2, c2 = kos(app("tek_tirnak_yanlis", {
    "view/Main.view.xml":
        "<mvc:View xmlns:mvc=\"sap.ui.core.mvc\"><Table rows=\"{ path: '/ZSD001_C_YANLIS' }\"/></mvc:View>\n",
    "controller/Main.controller.js": CTRL_BASI + '  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU,
}))
kontrol("V2 ⭐ POZ.KONTROL: tek tirnakli yanlis entity -> exit 1 + ENTITY SET YOK (once: TEMIZ/0)",
        rc2 == 1 and "[X] ENTITY SET YOK: ZSD001_C_YANLIS [view/Main.view.xml]" in c2,
        f"rc={rc2} cikti={c2[:300]!r}")

# ── V3: SINIR — degisken yolu metadata'da yok -> UYARI, KIRMIZI DEGIL ─────────
rc3, c3 = kos(app("degisken_yok", {
    "controller/Main.controller.js": CTRL_BASI +
        '  var ENTITY_OTHER_MODEL = "/ZSD001_C_YOK";\n'
        '  this.getModel().read("/ZSD001_C_SUM");\n'
        '  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU,
}))
kontrol("V3 ⭐ SINIR: metadata'da olmayan degisken yolu [?] UYARI + exit 0 (KIRMIZI DEGIL — "
        "korpusta 2/16 aday baska servisin setiydi)",
        rc3 == 0 and "[?] UYARI ZSD001_C_YOK" in c3
        and hukum(c3).startswith("KIRMIZI YOK — 1 UYARI"),
        f"rc={rc3} hukum={hukum(c3)!r}")

# ── V4: 0 entity referansi -> TEMIZ DEGIL ────────────────────────────────────
rc4, c4 = kos(app("entitysiz", {
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel().callFunction("/DoAction", {\n'
        '    method: "POST",\n'
        "    urlParameters: { P1: 1 }\n"
        "  });\n"
        '  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU,
}))
kontrol("V4 ⭐ 0 entity referansi -> hukum 'TEMIZ DEGIL: entity ekseni OLCULMEDI' + exit 0 "
        "(once: TEMIZ)",
        rc4 == 0 and "0 binding tarandi — entity ekseni OLCULMEDI" in c4
        and hukum(c4).startswith("KIRMIZI YOK — TEMIZ DEGIL: entity ekseni OLCULMEDI"),
        f"rc={rc4} hukum={hukum(c4)!r}")

# ── V5: FP CAPASI — JSON-model literalleri KIRMIZI URETMEZ ───────────────────
rc5, c5 = kos(app("json_literal", {
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel().read("/ZSD001_C_SUM");\n'
        '  var f = new Filter("Alan1", "EQ", 1);\n'
        '  oJson.setProperty("/Busy", true);\n'
        '  var c = this._m.getProperty("/Customer");\n'
        '  var a = [{ ctl: "/TractorCtl" }];\n'
        '  oV.setProperty(sPath + "/MatnrEtkin", 1);\n' + CTRL_SONU,
}))
kontrol("V5 FP capasi: 4 JSON-model '/Ad' literali -> KIRMIZI/UYARI yok, beyanda SAYILIR, TEMIZ",
        rc5 == 0 and "[X]" not in c5 and "[?]" not in c5
        and "4 diger '/Ad' literali" in c5 and hukum(c5).startswith("TEMIZ ("),
        f"rc={rc5} hukum={hukum(c5)!r} cikti={c5[-400:]!r}")

# ── V6: KONTROL GRUBU — yalniz cift tirnak (eski kodla AYNI hukum) ────────────
rc6, c6 = kos(app("cift_tirnak", {
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel().read("/ZSD001_C_SUM");\n'
        '  oTable.bindItems({ path: "/ZSD001_C_DETAIL" });\n'
        '  this.getModel().callFunction("/DoAction", {\n'
        "    urlParameters: { P1: 1 }\n"
        "  });\n"
        '  var f = new Filter("Alan1", "EQ", 1);\n'
        '  var o = { "$orderby": "Alan2 desc" };\n' + CTRL_SONU,
}))
kontrol("V6 KONTROL GRUBU: cift tirnakli temiz app -> TEMIZ + exit 0",
        rc6 == 0 and hukum(c6).startswith("TEMIZ (") and "[OK] DoAction" in c6,
        f"rc={rc6} hukum={hukum(c6)!r}")

rc6b, c6b = kos(app("cift_tirnak_yanlis", {
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel().read("/ZSD001_NOPE");\n'
        '  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU,
}))
kontrol("V6b KONTROL GRUBU: cift tirnakli yanlis ad -> exit 1 + ENTITY SET YOK",
        rc6b == 1 and "[X] ENTITY SET YOK: ZSD001_NOPE" in c6b, f"rc={rc6b} cikti={c6b[:300]!r}")

# ── V7: 3. BAGLAM — JS tek tirnak (korpusta 0 isabet sozdizimi) ──────────────
rc7, c7 = kos(app("js_tek_tirnak", {
    "controller/Main.controller.js": CTRL_BASI +
        "  oModel.read('/ZSD001_C_SUM', {});\n"
        "  oModel.callFunction('/DoAction', {\n"
        "    method: 'POST',\n"
        "    urlParameters: { P9: 1 }\n"
        "  });\n"
        "  var f = new Filter('AlanYok', 'EQ', 1);\n"
        "  var o = { '$select': 'Alan1,SecimYok' };\n" + CTRL_SONU,
}))
kontrol("V7 3.BAGLAM: JS tek tirnak read/callFunction/Filter/$select -> dort eksen de olculur",
        rc7 == 1 and "  [OK] ZSD001_C_SUM\n" in c7
        and "[!] DoAction: gecersiz param ['P9']" in c7
        and "[X] property YOK: AlanYok" in c7 and "[X] property YOK: SecimYok" in c7,
        f"rc={rc7} cikti={c7[:600]!r}")

# ── V8: 3. BAGLAM — fragment/ + entitySet='X' + const/let ────────────────────
rc8, c8 = kos(app("fragment_const", {
    "fragment/VH.fragment.xml":
        '<core:FragmentDefinition xmlns:core="sap.ui.core">'
        "<SelectDialog entitySet='ZSD001_I_VH'/></core:FragmentDefinition>\n",
    "controller/Main.controller.js": CTRL_BASI +
        "  const SET_A = '/ZSD001_C_SUM';\n"
        '  let SET_B = "/ZSD001_I_VH",\n'
        "      x = 1;\n"
        '  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU,
}))
kontrol("V8 3.BAGLAM: fragment entitySet='X' + const/let degisken yollari olculur -> TEMIZ",
        rc8 == 0 and "  [OK] ZSD001_I_VH\n" in c8
        and "[OK] ZSD001_C_SUM [controller/Main.controller.js]" in c8
        and "[OK] ZSD001_I_VH [controller/Main.controller.js]" in c8
        and hukum(c8).startswith("TEMIZ ("),
        f"rc={rc8} cikti={c8[:600]!r}")

# ── V9: SINIR — dengesiz tirnak referans sayilmaz ────────────────────────────
rc9, c9 = kos(app("dengesiz_tirnak", {
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel().read("/ZSD001_C_SUM");\n'
        "  var s = '/ZSD001_C_DENGESIZ\";\n"
        '  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU,
}))
kontrol("V9 SINIR: acilis/kapanis tirnagi farkli '/Ad\" -> referans SAYILMAZ (geri-referans)",
        rc9 == 0 and "ZSD001_C_DENGESIZ" not in c9, f"rc={rc9} cikti={c9[:400]!r}")

# ── V10: 0 property referansi -> TEMIZ DEGIL ─────────────────────────────────
rc10, c10 = kos(app("propertysiz", {
    "controller/Main.controller.js": CTRL_BASI + '  this.getModel().read("/ZSD001_C_SUM");\n' + CTRL_SONU,
}))
kontrol("V10 ⭐ 0 property referansi -> 'TEMIZ DEGIL: property ekseni OLCULMEDI' + exit 0 "
        "(once: '[OK] hepsi metadata'da' — bos kume icin 'hepsi')",
        rc10 == 0 and "0 property tarandi — property ekseni OLCULMEDI" in c10
        and "hepsi metadata'da" not in c10
        and hukum(c10).startswith("KIRMIZI YOK — TEMIZ DEGIL: property ekseni OLCULMEDI"),
        f"rc={rc10} hukum={hukum(c10)!r}")


# ══════════════════════════════════════════════════════════════════════════════
print()
gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f" -- {detay}" if (detay and not ok) else ""))
mod = f"  (kip: {' '.join(sorted(KIP))})" if KIP else ""
print(f"\n{gecen}/{len(SONUC)} OK{mod}")
TMP.cleanup()
sys.exit(0 if gecen == len(SONUC) else 1)

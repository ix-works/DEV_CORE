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

=== Q299 — COK SERVIS (olculdu 2026-09-13, canli: coklu dataSource'lu 6 app'te 27 KIRMIZI) ===
  W1  ⭐ AYIRT EDICI  bes alici bicimi (getModel('m') · this._yardimci() · oX = getModel('m') ·
                     oDlg.setModel + bindAggregation) + {m>/X} -> IKINCI servise karsi [OK]
  W1b beyan           model haritasi satiri; JSON model haritaya GIRMEZ
  W2  ⭐ POZ.KONTROL  ikincide de olmayan ad -> KIRMIZI (servis etiketli)
  W2b ⭐ GEVSETME SINIRI yalniz ANA'da olan ad ikinci modelden okunuyor -> KIRMIZI (birlesim YOK)
  W3  ⭐ SINIR        cozulemeyen alici + callback govdesindeki Filter -> ANA servise karsi (eski
                     davranis, gevsetme YOK) + sayisi beyan edilir
  W4  SINIR           bozuk manifest -> harita bos, eski davranis, not gorunur
  W5  ⭐              ikincil $metadata alinamadi + KIRMIZI yok -> exit 2 + [--] OLCULEMEDI
  W5b                 ... + ANA'da gercek KIRMIZI -> exit 1 (KIRMIZI yutulmaz)
  W6  KONTROL GRUBU   tek servisli manifest -> TEMIZ
  W7  ⭐ YENI EKSEN   isimli OData binding tek kaynak -> ikincide yoksa KIRMIZI; {ui>/..} sayilmaz
=== Q300 — $metadata ALINAMAZSA OLCEMEDIM (exit 2), KIRMIZI (1) DEGIL ===
  N1..N7             ConnectionError · HTTP 404 · EDMX olmayan 200 · .conn_adt yok · zaman asimi
                     kwarg'i (GERCEK fetch_metadata) · ReadTimeout · eksik conn anahtari

TAMAMEN CEVRIMDISI: arac BELLEKTE calistirilir, `load_conn`/`fetch_metadata` sentetik
$metadata dondurecek sekilde yamanir (yama main() CAGRISINDAN once yapilir; main global
adlari cagri aninda cozer). Gercek giris noktasi `main()` + argparse aynen kosar.
N-vektorlerinde `fetch_metadata` YAMANMAZ; yalniz `requests.Session` sahtedir.

Kosum: python tests/fixtures/ui_odata_refs_kapsami/run.py          (exit 0 = PASS)
Kipler: --mutasyon-tirnak · --mutasyon-degisken · --mutasyon-bos-eksen · --mutasyon-uyari-kirmizi ·
        --mutasyon-harita · --mutasyon-alici · --mutasyon-birlesim · --mutasyon-isimli ·
        --mutasyon-kismi-yesil · --mutasyon-olcemedim · --mutasyon-edmx · --mutasyon-conn ·
        --mutasyon-timeout
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

import requests

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
ARAC = REPO / "scripts" / "check_ui_odata_refs.py"

# ⛔ BILINMEYEN KIP SESSIZCE YESIL GECMESIN (negatif_test_harness sozlesmesi).
GECERLI_KIP = {"--mutasyon-tirnak", "--mutasyon-degisken", "--mutasyon-bos-eksen",
               "--mutasyon-uyari-kirmizi",
               # Q299
               "--mutasyon-harita", "--mutasyon-alici", "--mutasyon-birlesim", "--mutasyon-isimli",
               "--mutasyon-kismi-yesil",
               # Q300
               "--mutasyon-olcemedim", "--mutasyon-edmx", "--mutasyon-conn", "--mutasyon-timeout"}
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
    # Q299: manifest model haritasi hic okunmasin (kusurun birebir eski hali)
    "--mutasyon-harita": lambda m: _tek_degistir(
        m, "    harita, harita_notu = model_haritasi(a.app)\n",
        '    harita, harita_notu = {}, ""  # MUTASYON\n', "--mutasyon-harita"),
    # Q299: alici ifadesi hic cozulmesin (harita var ama referans modele BAGLANMIYOR)
    "--mutasyon-alici": lambda m: _tek_degistir(
        m, "def _coz(ifade, txt, konum, derinlik=0):\n",
        "def _coz(ifade, txt, konum, derinlik=0):\n    return None  # MUTASYON\n", "--mutasyon-alici"),
    # Q299 GEVSETME SINIRI: ikincil referans iki servisin BIRLESIMINE karsi olculsun
    "--mutasyon-birlesim": lambda m: _tek_degistir(
        m, "        es, fis = meta[s][0], meta[s][1]\n",
        "        es, fis = meta[s][0] | meta[service][0], {**meta[service][1], **meta[s][1]}  # MUTASYON\n",
        "--mutasyon-birlesim"),
    # Q299: isimli OData binding'i ({m>/X}) olculmesin
    "--mutasyon-isimli": lambda m: _tek_degistir(
        m, '    reads |= {(harita[mdl], ad, sh) for mdl, ad, sh in ek["isimli"] if mdl in harita}\n',
        "    pass  # MUTASYON\n", "--mutasyon-isimli"),
    # Q299: ikincil servis olculemediyse yine exit 0 (sessiz kismi yesil)
    "--mutasyon-kismi-yesil": lambda m: _tek_degistir(
        m, "    sys.exit(1 if red else (2 if olculemedi else 0))\n",
        "    sys.exit(1 if red else 0)  # MUTASYON\n", "--mutasyon-kismi-yesil"),
    # Q300: ag/HTTP istisnasi yakalanmasin (traceback = exit 1)
    "--mutasyon-olcemedim": lambda m: _tek_degistir(
        m, "    except (requests.RequestException, KeyError) as exc:\n",
        "    except ZeroDivisionError as exc:  # MUTASYON\n", "--mutasyon-olcemedim"),
    # Q300: EDMX olmayan 200 govdesi olcum sayilsin
    "--mutasyon-edmx": lambda m: _tek_degistir(
        m, '    if "<edmx:Edmx" not in (md or ""):\n',
        "    if False:  # MUTASYON\n", "--mutasyon-edmx"),
    # Q300: .conn_adt okunamazsa traceback
    "--mutasyon-conn": lambda m: _tek_degistir(
        m, "    except (OSError, UnicodeDecodeError) as exc:\n",
        "    except ZeroDivisionError as exc:  # MUTASYON\n", "--mutasyon-conn"),
    # Q300: zaman asimi dusurulsun (asili sunucuda suresiz bekleme)
    "--mutasyon-timeout": lambda m: _tek_degistir(
        m, ", timeout=ZAMAN_ASIMI)", ")  # MUTASYON", "--mutasyon-timeout"),
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


def kos(app_yolu: Path, md: dict | None = None, conn=None, session=None) -> tuple[int, str]:
    """Araci BELLEKTE calistir; ag yerine sentetik $metadata. (rc, stdout).

    md      None -> her servis icin MD_XML · dict -> servis basina govde YA DA istisna
    conn    dict -> load_conn onu dondurur · callable -> load_conn'un yerine gecer
    session verilirse `fetch_metadata` YAMANMAZ: gercek fonksiyon sahte `requests.Session`la kosar
    """
    mod = types.ModuleType("_ui_odata_refs")
    mod.__file__ = str(ARAC)
    try:
        exec(compile(KAYNAK, str(ARAC), "exec"), mod.__dict__)
    except Exception as exc:                      # kurulum hatasi != kacan mutasyon
        dur(f"arac yuklenemedi: {exc!r}")
    mod.load_conn = conn if callable(conn) else (lambda cwd, _c=dict(conn or {}): _c)
    if session is not None:
        mod.requests = types.SimpleNamespace(Session=session, HTTPError=requests.HTTPError,
                                             RequestException=requests.RequestException)
    elif md is None:
        mod.fetch_metadata = lambda cfg, service: MD_XML
    else:
        def _fm(cfg, service, _md=md):
            v = _md[service]
            if isinstance(v, BaseException):
                raise v
            return v
        mod.fetch_metadata = _fm
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
# Q299 — COK SERVIS. Manifest'te ikinci bir OData dataSource'u + ona bagli `drv` modeli.
# ══════════════════════════════════════════════════════════════════════════════
IKINCI = "ZSD001_UI_IKINCI_O2"
MD_IKINCI = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="1.0" xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx">
 <edmx:DataServices><Schema Namespace="ZSD001_UI_IKINCI_O2">
  <EntityType Name="BType"><Key><PropertyRef Name="BAlan"/></Key>
   <Property Name="BAlan" Type="Edm.String"/>
  </EntityType>
  <EntityContainer Name="C" m:IsDefaultEntityContainer="true">
   <EntitySet Name="B_SET" EntityType="ZSD001_UI_IKINCI_O2.BType"/>
   <EntitySet Name="B_SET2" EntityType="ZSD001_UI_IKINCI_O2.BType"/>
   <FunctionImport Name="B_FN" ReturnType="ZSD001_UI_IKINCI_O2.BType" m:HttpMethod="GET">
    <Parameter Name="BP" Type="Edm.String" Mode="In"/>
   </FunctionImport>
  </EntityContainer>
 </Schema></edmx:DataServices>
</edmx:Edmx>
"""
MANIFEST_COK = """{
  "sap.app": { "id": "ornek.app", "dataSources": {
    "mainService":   { "uri": "/sap/opu/odata/sap/ZSD001_UI_O2/", "type": "OData" },
    "ikinciService": { "uri": "/sap/opu/odata/sap/ZSD001_UI_IKINCI_O2/", "type": "OData" },
    "yerelVeri":     { "uri": "model/veri.json", "type": "JSON" } } },
  "sap.ui5": { "models": {
    "i18n": { "type": "sap.ui.model.resource.ResourceModel" },
    "":     { "dataSource": "mainService" },
    "drv":  { "dataSource": "ikinciService" },
    "ui":   { "type": "sap.ui.model.json.JSONModel" },
    "yrl":  { "dataSource": "yerelVeri" } } }
}
"""
IKI_MD = {"ZSD001_UI_O2": MD_XML, IKINCI: MD_IKINCI}


def kos_cok(app_yolu: Path, md: dict | None = None, **kw) -> tuple[int, str]:
    return kos(app_yolu, md=IKI_MD if md is None else md, **kw)


# ── W1: VAKANIN SEKLI — bes alici bicimi + isimli binding, hepsi ikinci serviste ──
rcw1, cw1 = kos_cok(app("cok_servis", {
    "manifest.json": MANIFEST_COK,
    "controller/Main.controller.js": CTRL_BASI +
        '  var SET_B = "/B_SET2";\n'
        "  return {\n"
        '    _b: function () { return this.getOwnerComponent().getModel("drv"); },\n'
        "    a: function () {\n"
        '      this.getOwnerComponent().getModel("drv").read("/B_SET", {\n'
        '        filters: [new Filter("BAlan", "EQ", "x")]\n'
        "      });\n"
        "      this._b().read(SET_B);\n"
        '      this._b().read("/B_SET2", { urlParameters: { "$select": "BAlan" } });\n'
        '      var oB = this.getModel("drv");\n'
        '      oB.callFunction("/B_FN", {\n'
        "        urlParameters: { BP: 1 }\n"
        "      });\n"
        '      oDlg.setModel(this.getModel("drv"));\n'
        '      oDlg.bindAggregation("items", { path: "/B_SET" });\n'
        '      this.getModel().read("/ZSD001_C_SUM", { filters: [new Filter("Alan1", "EQ", 1)] });\n'
        '      this.getModel("ui").setProperty("/Busy", true);\n'
        "    }\n"
        "  };\n" + CTRL_SONU,
    "fragment/Secici.fragment.xml":
        '<core:FragmentDefinition xmlns:core="sap.ui.core" xmlns:table="sap.ui.table">'
        "<table:Table rows=\"{drv>/B_SET}\"/><table:Table rows=\"{ path: 'drv>/B_SET2' }\"/>"
        '<Text text="{ui>/Busy}"/></core:FragmentDefinition>\n',
}))
kontrol("W1 ⭐ AYIRT EDICI: getModel('drv').read · this._b().read · oB=getModel('drv') · "
        "oDlg.setModel+bindAggregation · {drv>/X} -> IKINCI servise karsi [OK], TEMIZ + exit 0 "
        "(once: ana serviste aranip KIRMIZI)",
        rcw1 == 0 and hukum(cw1).startswith("TEMIZ (") and "[X]" not in cw1
        and f"  [OK] B_SET (servis {IKINCI})\n" in cw1
        and f"  [OK] B_SET2 (servis {IKINCI})\n" in cw1
        and f"  [OK] B_FN (servis {IKINCI})\n" in cw1
        and f"[OK] B_SET2 [controller/Main.controller.js] (servis {IKINCI})" in cw1
        and f"Servis {IKINCI} (model 'drv'):" in cw1
        and "  [OK] ZSD001_C_SUM\n" in cw1,
        f"rc={rcw1} cikti={cw1[:1500]!r}")
kontrol("W1b beyan: model haritasi ciktida (JSON model 'yrl'/'ui' haritaya GIRMEZ)",
        f"Model haritasi (manifest): 'drv' -> {IKINCI} · modeli statik cozulemeyen 0 referans" in cw1
        and "'yrl'" not in cw1, f"cikti={cw1[:500]!r}")

# ── W2: POZITIF KONTROL — ikinci servise eslenen referans ORADA da yoksa KIRMIZI ──
rcw2, cw2 = kos_cok(app("cok_servis_yanlis", {
    "manifest.json": MANIFEST_COK,
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getOwnerComponent().getModel("drv").read("/B_YOK");\n'
        '  this.getOwnerComponent().getModel("drv").read("/ZSD001_C_SUM");\n'
        '  this.getOwnerComponent().getModel("drv").read("/B_SET", { filters: [new Filter("Alan1", "EQ", 1)] });\n'
        '  this.getModel().read("/ZSD001_C_SUM", { filters: [new Filter("Alan1", "EQ", 1)] });\n' + CTRL_SONU,
}))
kontrol("W2 ⭐ POZ.KONTROL: ikincide olmayan ad -> exit 1 + ENTITY SET YOK (servis etiketiyle)",
        rcw2 == 1 and f"[X] ENTITY SET YOK: B_YOK [controller/Main.controller.js] (servis {IKINCI})" in cw2,
        f"rc={rcw2} cikti={cw2[:900]!r}")
kontrol("W2b ⭐ GEVSETME SINIRI: yalniz ANA'da olan ad ikinci modelden okunuyorsa KIRMIZI "
        "(iki servisin BIRLESIMINE karsi olculmez)",
        f"[X] ENTITY SET YOK: ZSD001_C_SUM [controller/Main.controller.js] (servis {IKINCI})" in cw2
        and f"[X] property YOK: Alan1 (servis {IKINCI})" in cw2
        and "  [OK] ZSD001_C_SUM\n" in cw2,
        f"cikti={cw2[:900]!r}")

# ── W3: SINIR — modeli statik cozulemeyen referans BUGUNKU gibi ANA servise karsi ──
rcw3, cw3 = kos_cok(app("cok_servis_cozulemez", {
    "manifest.json": MANIFEST_COK,
    "controller/Main.controller.js": CTRL_BASI +
        '  oBilinmez.read("/B_SET");\n'
        '  this.getModel("drv").read("/B_SET2", {\n'
        "    success: function () { var f = new Filter(\"BAlan\", \"EQ\", 1); }\n"
        "  });\n"
        '  this.getModel().read("/ZSD001_C_SUM", { filters: [new Filter("Alan1", "EQ", 1)] });\n' + CTRL_SONU,
}))
kontrol("W3 ⭐ SINIR (gevsetme YOK): cozulemeyen alici -> ANA servise karsi KIRMIZI (etiketsiz); "
        "callback govdesindeki Filter cagriya ATFEDILMEZ; sayi beyan edilir",
        rcw3 == 1 and "[X] ENTITY SET YOK: B_SET [controller/Main.controller.js]\n" in cw3
        and "[X] property YOK: BAlan\n" in cw3
        and f"  [OK] B_SET2 (servis {IKINCI})\n" in cw3
        and "modeli statik cozulemeyen 2 referans ANA servise karsi olculdu" in cw3,
        f"rc={rcw3} cikti={cw3[:1200]!r}")

# ── W4: SINIR — manifest okunamazsa harita BOS, davranis ESKISI ───────────────
rcw4, cw4 = kos_cok(app("cok_servis_bozuk_manifest", {
    "manifest.json": "{ bozuk json",
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel("drv").read("/B_SET", { filters: [new Filter("Alan1", "EQ", 1)] });\n' + CTRL_SONU,
}))
kontrol("W4 SINIR: bozuk manifest -> 'Model haritasi: manifest.json okunamadi' + ANA servise karsi KIRMIZI",
        rcw4 == 1 and "Model haritasi: manifest.json okunamadi (JSONDecodeError)" in cw4
        and "[X] ENTITY SET YOK: B_SET [controller/Main.controller.js]\n" in cw4,
        f"rc={rcw4} cikti={cw4[:700]!r}")

# ── W5: ikincil servisin $metadata'si ALINAMAZSA — sessiz OK/[?] YOK ──────────
_W5 = {
    "manifest.json": MANIFEST_COK,
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel("drv").read("/B_SET");\n'
        '  this.getModel().read("/ZSD001_C_SUM", { filters: [new Filter("Alan1", "EQ", 1)] });\n' + CTRL_SONU,
}
_MD_KOPUK = {"ZSD001_UI_O2": MD_XML, IKINCI: requests.ConnectionError("baglanti koptu")}
rcw5, cw5 = kos_cok(app("cok_servis_kopuk", _W5), md=_MD_KOPUK)
kontrol("W5 ⭐ ikincil $metadata alinamadi + KIRMIZI yok -> exit 2 + gorunur OLCULEMEDI "
        "(sessiz OK/[?] YOK)",
        rcw5 == 2 and f"[FAIL] OLCEMEDIM: servis {IKINCI} (model 'drv') $metadata alinamadi (ConnectionError)" in cw5
        and f"  [--] OLCULEMEDI: B_SET [controller/Main.controller.js] (servis {IKINCI})" in cw5
        and "[OK] B_SET" not in cw5 and hukum(cw5).startswith("OLCEMEDIM (kismi)"),
        f"rc={rcw5} cikti={cw5[:1200]!r}")
_W5b = dict(_W5)
_W5b["controller/Main.controller.js"] = _W5["controller/Main.controller.js"].replace(
    CTRL_SONU, '  this.getModel().read("/ZSD001_NOPE");\n' + CTRL_SONU)
rcw5b, cw5b = kos_cok(app("cok_servis_kopuk_kirmizi", _W5b), md=_MD_KOPUK)
kontrol("W5b ikincil alinamadi + ANA'da gercek KIRMIZI -> exit 1 (KIRMIZI yutulmaz) + OLCULEMEDI sayisi hukumde",
        rcw5b == 1 and hukum(cw5b).startswith("1 KIRMIZI uyumsuzluk · 1 referans OLCULEMEDI"),
        f"rc={rcw5b} hukum={hukum(cw5b)!r}")

# ── W7: YENI EKSEN — isimli OData binding TEK kaynak ({drv>/X} · path: 'drv>/X') ──
rcw7, cw7 = kos_cok(app("isimli_binding", {
    "manifest.json": MANIFEST_COK,
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel().read("/ZSD001_C_SUM", { filters: [new Filter("Alan1", "EQ", 1)] });\n' + CTRL_SONU,
    "view/Secici.view.xml":
        '<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns:table="sap.ui.table">'
        "<table:Table rows=\"{drv>/B_YOK2}\"/><table:Table rows=\"{ path: 'drv>/B_SET' }\"/>"
        "<Text text=\"{ui>/Busy}\"/><table:Table rows=\"{ path: 'ui>/Satirlar' }\"/></mvc:View>\n",
}))
kontrol("W7 ⭐ YENI EKSEN (sikilastirma): isimli OData binding ikinci servise karsi olculur — yoksa KIRMIZI; "
        "JSON model binding'i ({ui>/..}) SAYILMAZ",
        rcw7 == 1 and f"[X] ENTITY SET YOK: B_YOK2 [view/Secici.view.xml] (servis {IKINCI})" in cw7
        and f"  [OK] B_SET (servis {IKINCI})\n" in cw7
        and "Satirlar" not in cw7 and "Busy" not in cw7,
        f"rc={rcw7} cikti={cw7[:900]!r}")

# ── W6: KONTROL GRUBU — tek dataSource'lu manifest: hukum V6 ile ayni ─────────
rcw6, cw6 = kos(app("tek_servis_manifest", {
    "manifest.json": '{"sap.app": {"dataSources": {"mainService": {"uri": "/sap/opu/odata/sap/ZSD001_UI_O2/"}}},'
                     ' "sap.ui5": {"models": {"": {"dataSource": "mainService"}}}}',
    "controller/Main.controller.js": CTRL_BASI +
        '  this.getModel().read("/ZSD001_C_SUM");\n  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU,
}))
kontrol("W6 KONTROL GRUBU: tek servisli manifest -> TEMIZ + 'ikincil OData modeli yok'",
        rcw6 == 0 and hukum(cw6).startswith("TEMIZ (")
        and "ikincil OData modeli yok — tum referanslar ANA servise karsi olculdu" in cw6,
        f"rc={rcw6} cikti={cw6[:600]!r}")


# ══════════════════════════════════════════════════════════════════════════════
# Q300 — $metadata ALINAMAZSA: KIRMIZI (1) degil OLCEMEDIM (2). GERCEK `fetch_metadata`
# kosar; yalniz `requests.Session` sahtedir (ag YOK).
# ══════════════════════════════════════════════════════════════════════════════
CFG = {"ADT_SAP_URL": "https://ornek.invalid:44300", "ADT_SAP_USER": "u", "ADT_SAP_PASSWORD": "p"}


class _Yanit:
    def __init__(self, kod: int, govde: str):
        self.status_code, self.text = kod, govde

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Hata", response=self)


def oturum(davranis, kayit: list | None = None):
    class _Oturum:
        def get(self, url, **kw):
            if kayit is not None:
                kayit.append(kw)
            if isinstance(davranis, BaseException):
                raise davranis
            return davranis
    return _Oturum


_N_APP = {"controller/Main.controller.js": CTRL_BASI +
          '  this.getModel().read("/ZSD001_C_SUM");\n  var f = new Filter("Alan1", "EQ", 1);\n' + CTRL_SONU}

rcn1, cn1 = kos(app("ag_kopuk", _N_APP), conn=CFG,
                session=oturum(requests.ConnectionError("Failed to resolve host")))
kontrol("N1 ⭐ AYIRT EDICI: ConnectionError -> exit 2 + '[FAIL] OLCEMEDIM' (once: traceback + exit 1 = KIRMIZI kodu)",
        rcn1 == 2 and "[FAIL] OLCEMEDIM: $metadata alinamadi (ConnectionError)" in cn1 and "COKTU" not in cn1,
        f"rc={rcn1} cikti={cn1[-400:]!r}")

rcn2, cn2 = kos(app("ag_404", _N_APP), conn=CFG, session=oturum(_Yanit(404, "<html>yok</html>")))
kontrol("N2 HTTP 404 (servis adi yanlis/yayinlanmamis) -> exit 2 + 'HTTPError 404' (once: traceback + exit 1)",
        rcn2 == 2 and "$metadata alinamadi (HTTPError 404)" in cn2, f"rc={rcn2} cikti={cn2[-400:]!r}")

rcn3, cn3 = kos(app("ag_html", _N_APP), conn=CFG, session=oturum(_Yanit(200, "<html>giris</html>")))
kontrol("N3 200 + EDMX olmayan govde -> exit 2 (once: her referans 'YOK' = sahte KIRMIZI, exit 1)",
        rcn3 == 2 and "yanit EDMX degil" in cn3 and "[X]" not in cn3, f"rc={rcn3} cikti={cn3[-400:]!r}")


def _conn_yok(cwd):
    raise FileNotFoundError(2, "No such file", ".conn_adt")


rcn4, cn4 = kos(app("conn_yok", _N_APP), conn=_conn_yok)
kontrol("N4 .conn_adt okunamadi -> exit 2 + OLCEMEDIM (once: FileNotFoundError traceback + exit 1)",
        rcn4 == 2 and "[FAIL] OLCEMEDIM: .conn_adt okunamadi (FileNotFoundError)" in cn4,
        f"rc={rcn4} cikti={cn4[-400:]!r}")

_kayit: list = []
rcn5, cn5 = kos(app("ag_zaman_asimi", _N_APP), conn=CFG, session=oturum(_Yanit(200, MD_XML), _kayit))
kontrol("N5 ⭐ GERCEK fetch_metadata zaman asimi TASIR (asili sunucuda suresiz bekleme yok) + 200 EDMX -> TEMIZ",
        rcn5 == 0 and bool(_kayit) and _kayit[0].get("timeout") not in (None, 0)
        and hukum(cn5).startswith("TEMIZ ("), f"rc={rcn5} kayit={_kayit!r}")

rcn6, cn6 = kos(app("ag_asim", _N_APP), conn=CFG,
                session=oturum(requests.exceptions.ReadTimeout("read timed out")))
kontrol("N6 ReadTimeout -> exit 2 + 'ReadTimeout' (zaman asimi da OLCEMEDIM)",
        rcn6 == 2 and "$metadata alinamadi (ReadTimeout)" in cn6, f"rc={rcn6} cikti={cn6[-400:]!r}")

rcn7, cn7 = kos(app("conn_eksik_anahtar", _N_APP), conn={}, session=oturum(_Yanit(200, MD_XML)))
kontrol("N7 .conn_adt'de zorunlu anahtar eksik (KeyError) -> exit 2",
        rcn7 == 2 and "$metadata alinamadi (KeyError)" in cn7, f"rc={rcn7} cikti={cn7[-400:]!r}")


# ══════════════════════════════════════════════════════════════════════════════
print()
gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f" -- {detay}" if (detay and not ok) else ""))
mod = f"  (kip: {' '.join(sorted(KIP))})" if KIP else ""
print(f"\n{gecen}/{len(SONUC)} OK{mod}")
TMP.cleanup()
sys.exit(0 if gecen == len(SONUC) else 1)

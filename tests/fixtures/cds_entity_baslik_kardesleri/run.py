#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cds_entity_baslik_kardesleri — CDS entity BASLIK deseninin iki kardes yuzeyi (#410).

NEDEN VAR (DEV_CORE #410, 2026-11-08 kardes taramasi)
  Kaynak kapisi (`sap_adt_lib._validate_cds_source`) ve `populate_cds_views.RAP_BASLIK_DESENI`
  `define [root] custom entity`yi tanimaya basladi. Ayni baslik deseni iki yerde daha yasiyor:
  K1 `scripts/validators/check_sap_active_version.py::infer_from_artifact`
     `define\\s+(?:abstract|custom)\\s+entity` -> `root` onekini TANIMIYORDU: `define root
     custom entity` / `define root abstract entity` artefaktinda ad cozulemiyordu (Q240'tan
     beri "ad cozulemedi" SKIP = olcum yok; daha once None -> sahte BLOCKER).
  K2 `scripts/gen_field_table.py::_body` `view entity|abstract entity` -> custom entity'de
     ad '?' ve govde aramasi 0'dan basliyordu (baslik annotation'indaki `{` govde sanilir).
  Sinir (bilerek): gen_field_table ELEMAN satirini `NAME [as ALIAS]` deseniyle okur;
  tipli eleman (`Id : abap.char(10);`) abstract'ta da custom'da da alan URETMEZ (ayri konu).
  K3 (#412 duzeltme 3) `gen_field_table._strip_comments` yalniz `/* */` + `//` atiyordu:
     `--` satir yorumundaki eski baslik ad oluyor, `-- yorum`lu alan satiri alan listesini
     bosaltiyordu. Artik ortak `sap_adt_lib.cds_kod_metni(..., string_icerigini_koru=True)`.

VEKTORLER
  V1 root custom entity -> (ad, ddls)          V2 custom entity -> (ad, ddls)
  V3 root abstract entity -> (ad, ddls)        V4 duz abstract (FP capasi, 2026-06-29)
  V5 root view entity (FP capasi)              V6 yorumdaki root custom entity ad VERMEZ
  G1 custom entity: ad + govde                 G2 root custom + baslik annotation'inda `{`
  G3 view entity projection (FP capasi)
  (parse_cds uctan uca — ad + [(alan, etiket)])
  G4 `--` yorumundaki eski baslik ad VERMEZ    G5 `-- yorum`lu alan satirlari alan uretir
  G6 etiket string'indeki `--` KORUNUR         G7 `//` kontrol grubu (G4+G5'in `//` esi)
  G8 etiket string'indeki `//` KORUNUR

KIPLER (BEYAN) — dusen kume ilanla AYNI -> exit 1 · farkli -> exit 2 SAPMA · capa != 1 /
yukleme hatasi -> exit 3 KURULAMADI.
  --mutasyon-asv-rootsuz    infer deseninden `root` oneki kalkar          -> V1, V3
  --mutasyon-gft-customsuz  _body deseninden custom kalkar                 -> G1, G2
  --mutasyon-ortak-tiresiz  ortak ayiklayicinin `--` dali kapanir          -> G4, G5
  --mutasyon-gft-string-sil gft string icerigini de atar (koru=False)      -> G6, G8
  --mutasyon-gft-naif-tire  gft string'e kor `--` on-gecisi (re.sub)       -> G6
  --mutasyon-taban          3353fca iki dosya (git show; sig klonda exit 2 DOGRULANAMADI)
SAP GEREKTIRMEZ (yalniz saf fonksiyonlar; modul kaynagi bellekte exec edilir).
"""
from __future__ import annotations

import atexit
import io
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
ASV = KOK / "scripts" / "validators" / "check_sap_active_version.py"
GFT = KOK / "scripts" / "gen_field_table.py"
SAL = KOK / "scripts" / "sap_adt_lib.py"
if not ASV.is_file() or not GFT.is_file() or not SAL.is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")
TABAN_SHA = "3353fca"

GECERLI_KIP = ("--mutasyon-asv-rootsuz", "--mutasyon-gft-customsuz", "--mutasyon-ortak-tiresiz",
               "--mutasyon-gft-string-sil", "--mutasyon-gft-naif-tire", "--mutasyon-taban")
KIPLER = [a for a in sys.argv[1:] if a.startswith("--")]
if len(KIPLER) > 1 or (KIPLER and KIPLER[0] not in GECERLI_KIP):
    print(f"[KULLANIM] gecerli kipler: {', '.join(GECERLI_KIP)} (en fazla bir tane)")
    sys.exit(2)
KIP = KIPLER[0] if KIPLER else ""

MUTASYONLAR = {
    "--mutasyon-asv-rootsuz": (ASV, (r"define\s+(?:root\s+)?(?:abstract|custom)\s+entity\s+",
                                     r"define\s+(?:abstract|custom)\s+entity\s+")),
    "--mutasyon-gft-customsuz": (GFT, (r"abstract\s+entity|custom\s+entity)\s+(\w+)",
                                       r"abstract\s+entity)\s+(\w+)")),
    "--mutasyon-ortak-tiresiz": (SAL, ("        elif metin.startswith('//', i) or "
                                       "metin.startswith('--', i):\n",
                                       "        elif metin.startswith('//', i):\n")),
    "--mutasyon-gft-string-sil": (GFT, ("    return cds_kod_metni(text, string_icerigini_koru=True)\n",
                                        "    return cds_kod_metni(text)\n")),
    "--mutasyon-gft-naif-tire": (GFT, ("    return cds_kod_metni(text, string_icerigini_koru=True)\n",
                                       '    return cds_kod_metni(re.sub(r"--[^\\n]*", "", text), '
                                       "string_icerigini_koru=True)\n")),
}
BEKLENEN_DUSEN = {
    "--mutasyon-asv-rootsuz": {"V1", "V3"},
    "--mutasyon-gft-customsuz": {"G1", "G2"},
    "--mutasyon-ortak-tiresiz": {"G4", "G5"},
    "--mutasyon-gft-string-sil": {"G6", "G8"},
    "--mutasyon-gft-naif-tire": {"G6"},
    "--mutasyon-taban": {"V1", "V3", "G1", "G2", "G4", "G5", "G8"},
}


def _kaynak(yol: Path) -> str:
    metin = yol.read_text(encoding="utf-8")
    if KIP == "--mutasyon-taban":
        goreli = yol.relative_to(KOK).as_posix()
        r = subprocess.run(["git", "-C", str(KOK), "show", f"{TABAN_SHA}:{goreli}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"[DOGRULANAMADI] git show {TABAN_SHA}:{goreli} -> {r.stderr.strip()[:120]}")
            sys.exit(2)
        return r.stdout
    if KIP in MUTASYONLAR and MUTASYONLAR[KIP][0] == yol:
        capa, yerine = MUTASYONLAR[KIP][1]
        n = metin.count(capa)
        if n != 1:
            print(f"[KURULAMADI] {KIP}: capa {n} kez bulundu (1 bekleniyordu)")
            sys.exit(3)
        return metin.replace(capa, yerine)
    return metin


def _yukle(yol: Path, ad: str):
    """Kaynagi (istege bagli mutasyonla) taze namespace'te calistir. `__file__` GERCEK yol:
    modulun kendi sys.path/import satirlari gercek agaci gorur."""
    src = _kaynak(yol)
    mod = types.ModuleType(ad)
    mod.__file__ = str(yol)
    yedek = sys.stdout, sys.stderr
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    try:
        exec(compile(src, str(yol), "exec"), mod.__dict__)
    except Exception as exc:                                   # noqa: BLE001
        sys.stdout, sys.stderr = yedek
        print(f"[KURULAMADI] {ad} yuklenemedi: {type(exc).__name__}: {exc}")
        sys.exit(3)
    finally:
        sys.stdout, sys.stderr = yedek
    return mod


asv = _yukle(ASV, "asv_olcum")
if KIP == "--mutasyon-ortak-tiresiz":
    # gft `from sap_adt_lib import cds_kod_metni` yapar -> mutasyonlu modul sys.modules'e
    # ONCEDEN konur; asagidaki kimlik kontrolu gft'nin onu gercekten aldigini ispatlar.
    sys.modules["sap_adt_lib"] = _yukle(SAL, "sap_adt_lib")
gft = _yukle(GFT, "gft_olcum")
if KIP == "--mutasyon-ortak-tiresiz" and \
        getattr(gft, "cds_kod_metni", None) is not sys.modules["sap_adt_lib"].cds_kod_metni:
    print("[KURULAMADI] gft mutasyonlu cds_kod_metni'yi almadi (sys.modules onbellegi)")
    sys.exit(3)
print(f"### kip: {KIP or '(duzeltilmis moduller)'}")
SONUC: list[tuple[str, bool, str]] = []
KUM = Path(tempfile.mkdtemp(prefix="cdsbaslik_"))
atexit.register(shutil.rmtree, KUM, True)


def infer(metin: str):
    p = KUM / "ornek.cds"
    p.write_text(metin, encoding="utf-8")
    try:
        return asv.infer_from_artifact(p)
    except Exception as exc:                                   # noqa: BLE001
        return ("COKTU", f"{type(exc).__name__}: {exc}")


V = [
    ("V1 root custom entity -> (ad, ddls)",
     "@ObjectModel.query.implementedBy: 'ABAP:ZCL_SD001_ORNEK_Q'\n"
     "define root custom entity ZSD001_I_ORNEK_CR\n{ key Id : abap.char(10); }\n",
     ("ZSD001_I_ORNEK_CR", "ddls")),
    ("V2 custom entity + with parameters -> (ad, ddls)",
     "define custom entity ZSD001_I_ORNEK_CP with parameters p_a : abap.char(1)\n"
     "{ key Id : abap.char(10); }\n", ("ZSD001_I_ORNEK_CP", "ddls")),
    ("V3 root abstract entity -> (ad, ddls)",
     "define root abstract entity ZSD001_I_ORNEK_AR\n{ a : abap.char(1); }\n",
     ("ZSD001_I_ORNEK_AR", "ddls")),
    ("V4 FP CAPASI duz abstract entity -> (ad, ddls)",
     "define abstract entity ZSD001_I_ORNEK_A\n{ a : abap.char(1); }\n",
     ("ZSD001_I_ORNEK_A", "ddls")),
    ("V5 FP CAPASI root view entity -> (ad, ddls)",
     "define root view entity ZSD001_I_ORNEK_V as select from zsd001_t_ornek { key a }\n",
     ("ZSD001_I_ORNEK_V", "ddls")),
    ("V6 yorumdaki `define root custom entity` ad VERMEZ (gercek baslik view entity)",
     "// define root custom entity ZSD001_I_YORUM\n"
     "define view entity ZSD001_I_ORNEK_Y as select from zsd001_t_ornek { key a }\n",
     ("ZSD001_I_ORNEK_Y", "ddls")),
]
for ad, metin, beklenen in V:
    gorulen = infer(metin)
    SONUC.append((ad, tuple(gorulen) == beklenen, f"gorulen={gorulen}"))

G = [
    ("G1 custom entity: ad + govde",
     "define custom entity ZSD001_I_ORNEK_CE\n{\n  key Id : abap.char(10);\n}\n",
     "ZSD001_I_ORNEK_CE", "key Id : abap.char(10);"),
    ("G2 root custom entity, baslik annotation'inda `{` govde sanilmaz",
     "@ObjectModel.usageType: { serviceQuality: #X, sizeCategory: #S }\n"
     "define root custom entity ZSD001_I_ORNEK_CR\n{\n  key Id : abap.char(10);\n}\n",
     "ZSD001_I_ORNEK_CR", "key Id : abap.char(10);"),
    ("G3 FP CAPASI view entity projection",
     "define root view entity ZSD001_C_ORNEK as projection on ZSD001_I_ORNEK\n{\n  key Id\n}\n",
     "ZSD001_C_ORNEK", "key Id"),
]
for ad, metin, beklenen_ad, beklenen_govde in G:
    try:
        n, _proj, govde = gft._body(gft._strip_comments(metin))
        ok = n == beklenen_ad and govde.strip() == beklenen_govde
        detay = f"ad={n!r} govde={govde.strip()[:60]!r}"
    except Exception as exc:                                   # noqa: BLE001
        ok, detay = False, f"COKTU {type(exc).__name__}: {exc}"
    SONUC.append((ad, ok, detay))

# parse_cds uctan uca (dosyadan): `--` yorum ekseni + string'e duyarlilik (#412 duzeltme 3).
# Etiket satirlari literal basinda bolunur (fixture dizgesinde kacisa bitisik annotation
# GENERICIZE-LEAK e-posta sanilir).
_GOVDE_T000 = " as select from t000 {\n"
P = [
    ("G4 `--` yorumundaki eski baslik ad VERMEZ",
     "-- define view entity ZSD001_I_ESKI as select from x {\n"
     "define view entity ZSD001_I_GERCEK" + _GOVDE_T000 + "  key Client,\n  Text\n}\n",
     ("ZSD001_I_GERCEK", [("Client", None), ("Text", None)])),
    ("G5 `-- yorum`lu alan satirlari alan uretir",
     "define view entity ZSD001_I_ALAN" + _GOVDE_T000 +
     "  key Client, -- istemci\n  Text -- metin\n}\n",
     ("ZSD001_I_ALAN", [("Client", None), ("Text", None)])),
    ("G6 etiket string'indeki `--` KORUNUR",
     "define view entity ZSD001_I_ETIKET" + _GOVDE_T000 +
     "  @EndUserText.label: 'Miktar -- toplam'\n"
     "  key Client\n}\n",
     ("ZSD001_I_ETIKET", [("Client", "Miktar -- toplam")])),
    ("G7 KONTROL `//` yorumu (G4+G5'in `//` esi)",
     "// define view entity ZSD001_I_ESKI as select from x {\n"
     "define view entity ZSD001_I_GERCEK" + _GOVDE_T000 +
     "  key Client, // istemci\n  Text // metin\n}\n",
     ("ZSD001_I_GERCEK", [("Client", None), ("Text", None)])),
    ("G8 etiket string'indeki `//` KORUNUR",
     "define view entity ZSD001_I_ETIKET" + _GOVDE_T000 +
     "  @EndUserText.label: 'Web // adres'\n"
     "  key Client\n}\n",
     ("ZSD001_I_ETIKET", [("Client", "Web // adres")])),
]
for ad, metin, beklenen in P:
    p = KUM / "alan.cds"
    p.write_bytes(metin.encode("utf-8"))
    try:
        n, _proj, alanlar = gft.parse_cds(str(p))
        gorulen = (n, [(a["name"], a["label"]) for a in alanlar])
        ok, detay = gorulen == beklenen, f"gorulen={gorulen}"
    except Exception as exc:                                   # noqa: BLE001
        ok, detay = False, f"COKTU {type(exc).__name__}: {exc}"
    SONUC.append((ad, ok, detay))

basarisiz = [s for s in SONUC if not s[1]]
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"  -> {detay}"))
print(f"\nSONUC: {len(SONUC) - len(basarisiz)}/{len(SONUC)} PASS")
if KIP == "":
    sys.exit(1 if basarisiz else 0)
dusen = {s[0].split()[0] for s in basarisiz}
ilan = BEKLENEN_DUSEN[KIP]
if dusen and dusen == ilan:
    print(f"[DUSTU] {KIP}: dusen kume ilanla AYNI: {', '.join(sorted(dusen))}")
    sys.exit(1)
print(f"[SAPMA] {KIP}: ilan edilmeyen dusen={sorted(dusen - ilan)} · "
      f"ilan edilip dusmeyen={sorted(ilan - dusen)}")
sys.exit(2)

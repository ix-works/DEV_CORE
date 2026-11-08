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
     bosaltiyordu. Artik ortak `utils.cds_metin.cds_kod_metni(..., string_icerigini_koru=True)`.

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
  (gercek alt surec, gft `__main__` olarak — #412 duzeltme 4 bagimlilik eksenleri)
  G9  `requests`/`urllib3`/`dotenv` import'u ENGELLI ortamda gft acilir, tabloyu basar (rc 0)
  G10 sahte `.conn_adt`'li proje dizininde gft `ADT_*` ortam degiskeni YUKLEMEZ,
      `sap_adt_lib` import edilmez

KIPLER (BEYAN) — dusen kume ilanla AYNI -> exit 1 · farkli -> exit 2 SAPMA · capa != 1 /
yukleme hatasi -> exit 3 KURULAMADI.
  --mutasyon-asv-rootsuz    infer deseninden `root` oneki kalkar          -> V1, V3
  --mutasyon-gft-customsuz  _body deseninden custom kalkar                 -> G1, G2
  --mutasyon-ortak-tiresiz  ortak ayiklayicinin (`utils/cds_metin.py`) `--` dali kapanir -> G4, G5
  --mutasyon-gft-string-sil gft string icerigini de atar (koru=False)      -> G6, G8
  --mutasyon-gft-naif-tire  gft string'e kor `--` on-gecisi (re.sub)       -> G6
  --mutasyon-gft-sapadtlib  gft ayiklayiciyi yine `sap_adt_lib`'den alir  -> G9, G10
  --mutasyon-taban          3353fca iki dosya (git show; sig klonda exit 2 DOGRULANAMADI).
                            Taban gft ortak modulu (`utils.cds_metin` / `sap_adt_lib`) import
                            ediyorsa o modul de AYNI SHA'dan on-yuklenir (TABAN_SHA ileri
                            cekilince agac karismasin — bug-gate O-2).
Yamali/taban ortak modul `sys.modules`'e ONCEDEN konur; gft'nin onu aldigi KIMLIKLE dogrulanir.
SAP GEREKTIRMEZ (saf fonksiyonlar bellekte exec edilir; G9/G10 yerel alt surec, ag yok).
"""
from __future__ import annotations

import atexit
import io
import json
import os
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
CDSM = KOK / "scripts" / "utils" / "cds_metin.py"
if not all(p.is_file() for p in (ASV, GFT, SAL, CDSM)):
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")
TABAN_SHA = "3353fca"
# Taban gft'nin import edebilecegi ortak moduller (isaret, modul adi, yol) — SIRA onemli:
# sap_adt_lib@SHA de utils.cds_metin'i import ediyor olabilir.
ORTAK = (("from utils.cds_metin import", "utils.cds_metin", CDSM),
         ("from sap_adt_lib import", "sap_adt_lib", SAL))

GECERLI_KIP = ("--mutasyon-asv-rootsuz", "--mutasyon-gft-customsuz", "--mutasyon-ortak-tiresiz",
               "--mutasyon-gft-string-sil", "--mutasyon-gft-naif-tire", "--mutasyon-gft-sapadtlib",
               "--mutasyon-taban")
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
    "--mutasyon-ortak-tiresiz": (CDSM, ("        elif metin.startswith('//', i) or "
                                       "metin.startswith('--', i):\n",
                                       "        elif metin.startswith('//', i):\n")),
    "--mutasyon-gft-string-sil": (GFT, ("    return cds_kod_metni(text, string_icerigini_koru=True)\n",
                                        "    return cds_kod_metni(text)\n")),
    "--mutasyon-gft-naif-tire": (GFT, ("    return cds_kod_metni(text, string_icerigini_koru=True)\n",
                                       '    return cds_kod_metni(re.sub(r"--[^\\n]*", "", text), '
                                       "string_icerigini_koru=True)\n")),
    "--mutasyon-gft-sapadtlib": (GFT, ("from utils.cds_metin import cds_kod_metni",
                                       "from sap_adt_lib import cds_kod_metni")),
}
BEKLENEN_DUSEN = {
    "--mutasyon-asv-rootsuz": {"V1", "V3"},
    "--mutasyon-gft-customsuz": {"G1", "G2"},
    "--mutasyon-ortak-tiresiz": {"G4", "G5"},
    "--mutasyon-gft-string-sil": {"G6", "G8"},
    "--mutasyon-gft-naif-tire": {"G6"},
    "--mutasyon-gft-sapadtlib": {"G9", "G10"},
    "--mutasyon-taban": {"V1", "V3", "G1", "G2", "G4", "G5", "G8"},
}
KUM = Path(tempfile.mkdtemp(prefix="cdsbaslik_"))
atexit.register(shutil.rmtree, KUM, True)


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


def _yukle(yol: Path, ad: str, src: str | None = None):
    """Kaynagi (istege bagli mutasyonla) taze namespace'te calistir. `__file__` GERCEK yol:
    modulun kendi sys.path/import satirlari gercek agaci gorur."""
    if src is None:
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
GFT_SRC = _kaynak(GFT)
# On-yuklenen ortak moduller: [(modul adi, kum kaynak yolu, gercek yol)] — G9/G10 alt sureci
# de AYNI kaynaklari on-yukler (bellek ici olcumle ayni agac).
ON_YUKLE: list[tuple[str, str, str]] = []
ON_MOD: dict = {}          # ad -> on-yuklenen modul NESNESI (kimlik kontrolu buna karsi)


def _on_yukle(ad: str, gercek: Path, src: str) -> None:
    kum = KUM / f"on_{ad.replace('.', '_')}.py"
    kum.write_text(src, encoding="utf-8")
    ON_MOD[ad] = _yukle(gercek, ad, src)
    sys.modules[ad] = ON_MOD[ad]
    ON_YUKLE.append((ad, str(kum), str(gercek)))


_CM, _SA = ORTAK[0][0], ORTAK[1][0]
if KIP == "--mutasyon-ortak-tiresiz":
    # gft `from utils.cds_metin import cds_kod_metni` yapar -> mutasyonlu modul ONCEDEN konur.
    _on_yukle("utils.cds_metin", CDSM, _kaynak(CDSM))
elif KIP == "--mutasyon-taban":
    _sal_src = _kaynak(SAL) if _SA in GFT_SRC else ""
    if _CM in GFT_SRC or _CM in _sal_src:
        _on_yukle("utils.cds_metin", CDSM, _kaynak(CDSM))
    if _sal_src:
        _on_yukle("sap_adt_lib", SAL, _sal_src)
gft = _yukle(GFT, "gft_olcum", GFT_SRC)
_hedef = "utils.cds_metin" if _CM in GFT_SRC else ("sap_adt_lib" if _SA in GFT_SRC else "")
if _hedef in ON_MOD and getattr(gft, "cds_kod_metni", None) is not ON_MOD[_hedef].cds_kod_metni:
    print(f"[KURULAMADI] gft on-yuklenen {_hedef}.cds_kod_metni'yi ALMADI (sys.modules onbellegi)")
    sys.exit(3)
print(f"### kip: {KIP or '(duzeltilmis moduller)'}"
      + (f"  on-yuklenen: {[a for a, _k, _g in ON_YUKLE]}" if ON_YUKLE else ""))
SONUC: list[tuple[str, bool, str]] = []


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

# G9/G10 — gercek alt surec: gft `__main__` olarak (#412 duzeltme 4). Kaynak = bellek ici
# olcumle AYNI (`GFT_SRC`: canli / yamali / taban), `__file__` gercek yol; ON_YUKLE'deki ortak
# moduller alt surecte de once yuklenir. Proje dizininde SAHTE `.conn_adt` var (ornek.invalid;
# ag cagrisi yapilmaz) -> yuklenirse `ADT_*` ortamda belirir.
BOOT = r'''
import json, os, sys, types
kip, src_yol, gercek, cds, on = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5])
if kip == "engelli":
    for _m in ("requests", "urllib3", "dotenv"):
        sys.modules[_m] = None
sys.path.insert(0, os.path.dirname(gercek))
once = {k for k in os.environ if k.startswith("ADT_")}
rc = 0
try:
    for ad, kum, gyol in on:
        m = types.ModuleType(ad)
        m.__file__ = gyol
        sys.modules[ad] = m
        exec(compile(open(kum, encoding="utf-8").read(), gyol, "exec"), m.__dict__)
    sys.argv = [gercek, cds]
    exec(compile(open(src_yol, encoding="utf-8").read(), gercek, "exec"),
         {"__name__": "__main__", "__file__": gercek})
except SystemExit as e:
    rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
except BaseException as e:
    print("HATA %s: %s" % (type(e).__name__, e), file=sys.stderr)
    rc = 99
yeni = sorted({k for k in os.environ if k.startswith("ADT_")} - once)
print("##SONUC " + json.dumps({"rc": rc, "adt": yeni,
                              "sap_adt_lib": sys.modules.get("sap_adt_lib") is not None}))
'''
PROJE = KUM / "proje"
PROJE.mkdir()
(PROJE / ".conn_adt").write_text(
    "ADT_SAP_URL=https://ornek.invalid\nADT_SAP_USER=TESTUSER\nADT_SAP_PASSWORD=x\n"
    "ADT_SAP_CLIENT=100\n", encoding="utf-8")
(KUM / "boot.py").write_text(BOOT, encoding="utf-8")
(KUM / "gft_kaynak.py").write_text(GFT_SRC, encoding="utf-8")
(PROJE / "alan.cds").write_bytes(("define view entity ZSD001_I_ALAN" + _GOVDE_T000 +
                                  "  key Client,\n  Text\n}\n").encode("utf-8"))
_ENV = {k: v for k, v in os.environ.items() if not k.startswith("ADT_")}
_ENV.update({"CLAUDE_PROJECT_DIR": str(PROJE), "PYTHONIOENCODING": "utf-8"})


def alt_surec(kip: str) -> tuple[dict, str]:
    r = subprocess.run([sys.executable, str(KUM / "boot.py"), kip, str(KUM / "gft_kaynak.py"),
                        str(GFT), str(PROJE / "alan.cds"), json.dumps(ON_YUKLE)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(PROJE), env=_ENV, timeout=120)
    satir = [s for s in r.stdout.splitlines() if s.startswith("##SONUC ")]
    if r.returncode != 0 or len(satir) != 1:
        print(f"[KURULAMADI] alt surec rc={r.returncode} ozet={len(satir)}: {r.stderr.strip()[:200]}")
        sys.exit(3)
    return json.loads(satir[0][8:]), r.stdout + r.stderr


s9, cikti9 = alt_surec("engelli")
SONUC.append(("G9 requests/urllib3/dotenv ENGELLI ortamda gft acilir ve tabloyu basar",
              s9["rc"] == 0 and "Alan Tablosu" in cikti9 and "Client" in cikti9,
              f"sonuc={s9} cikti={cikti9.strip()[-160:]!r}"))
s10, cikti10 = alt_surec("normal")
SONUC.append(("G10 sahte .conn_adt'li dizinde ADT_* YUKLENMEZ, sap_adt_lib import EDILMEZ",
              s10["rc"] == 0 and s10["adt"] == [] and not s10["sap_adt_lib"]
              and "Alan Tablosu" in cikti10,
              f"sonuc={s10}"))

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

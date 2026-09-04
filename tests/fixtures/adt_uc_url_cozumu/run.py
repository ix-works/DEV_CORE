#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adt_uc_url_cozumu fixture — ADT uc URL'i: `/source/main` NEREYE eklenir, NEREYE eklenmez.

NEDEN VAR (Q217 = Q229 + Q221 = Q228; hepsi TEK SINIF: *generic URL tablosu ile ozel
yolun ayrismasi*):

  (1) `get_object_source()` her URL'e KOSULSUZ `/source/main` ekliyordu. Sinif alt-include
      uclari (`/oo/classes/<CLS>/includes/<seg>`) ise KAYNAK UCUNUN KENDISIDIR -> ek
      404 verir. CANLI OLCUM 2026-09-03 (DEV, salt-GET, kontrol gruplu):
         ciplak include ucu                     -> HTTP 200 (154609 bayt)
         ayni uc + /source/main                 -> HTTP 404 (26 bayt)
         KONTROL GRUBU ayni sinifin ana kaynagi -> HTTP 200
      Kural depoda ZATEN yaziliydi (`object_types.get_class_include_url` docstring'i:
      *"sonuna /source/main EKLENMEZ ... ekleyen 404 alir"*); KOD UYMUYORDU.
  (2) Ayni 404'un IKINCI zarari: hata mesaji obje adini `url.split('/')[-2]` ile
      uretiyordu -> include URL'inde bu **'source'** kelimesine denk geliyor ve mesaj
      VAR OLMAYAN bir obje ILAN ediyordu (`Object not found: source`). Yanlis teshis
      ("canlida yok") bir kat daha kolaylasiyordu.
  (3) `OBJECT_TYPES['function'].url_path = 'functions/modules'` ADT'de OLMAYAN bir adres
      uretiyordu. CANLI OLCUM (ayni tur):
         /sap/bc/adt/functions/modules/<fm>                           -> HTTP 404
         /sap/bc/adt/functions/groups/<fg>/fmodules/<fm>              -> HTTP 406 (obje VAR)
         /sap/bc/adt/functions/groups/<fg>/fmodules/<fm>/source/main  -> HTTP 200 (27721 bayt)
      `url_path`i duzeltmek COZUM DEGIL: dogru uc FONKSIYON GRUBUNU icerir ve grup adi
      FM adindan TURETILEMEZ (ayni turda olculdu: FM adi ile FG adi ortak on-ek disinda
      ORTUSMUYOR, FG ancak canli ARAMA ile cozuldu). Bu yuzden fix bir ADRES TAMIRI
      degil, FAIL-CLOSED KAPI'dir: yanlis adres uretmektense yonlendiren `ValueError`.

BU FIXTURE'IN OLCTUGU DEGISMEZLER:
  1. Sinif alt-include ucuna `/source/main` EKLENMEZ; klasik program include'una
     (`/programs/includes/<INCL>`) EKLENIR.                       [A1 · A2 AYIRT EDICI]
  2. Muafiyet DARDIR: taninmayan bir include segmenti ek ALIR.                   [A5]
  3. Segment listesi TEK KAYNAKTAN (`CLASS_INCLUDE_TYPES`) okunur — ikinci literal yok. [A6]
  4. Davranis: `get_object_source()` include icin ciplak uctan, sinif icin
     `/source/main`den okur (sahte oturumun KAYDETTIGI URL ile olculur).      [A7 · A8]
  5. 404 mesaji var olmayan obje adi ILAN ETMEZ (mutasyonda olculdu: fix ONCESI **her**
     404 "Object not found: source" diyordu, kusur include'lardan genisti); istisna
     SOZLESMESI (tip/kod/endpoint) ise DEGISMEDI.                 [A9 · A10 · A11 FP]
  6. `func`/`function` generic URL'e girerse ANLASILIR RET (sessiz 404 degil).  [B1-B3]
  7. Komsu tipler BOZULMADI ve `func` girdisinin diger alanlari (adt_type / uzanti /
     yerel dizin) KORUNDU — girdi silinmedi, yalniz URL uretimi kapatildi.  [B4 · B5]
  8. Q228 TUKETICI KANITI: ATC yolu ayni tabloyu tuketir -> artik yanlis adres
     URETMIYOR, kapiya carpiyor.                                              [B7]
  9. 3. BAGLAM (gorev-DISI, AYRI SUREC): CLI `push_object.py --type func` yonlendirme
     verir; `object_types.py` demosu `url_path=None` ile COKMEZ.          [C1 · C2]

SILINMEZ CAPALAR (hepsi MUTASYONDA DA GECER — "asiri-genelleme olmadi"nin tek kaniti
budur; yardimci fonksiyona bakan bir capa mutasyonda duser ve capa OLMAKTAN CIKAR):
A2 (klasik program include'u ek ALIR) · A3a-c (siradan tipler) · A4 (cift ek yok) ·
A5 (taninmayan segment ek ALIR) · A8 · A11 · B4 · B5 · B6 · C2. Bunlar kalkarsa fix
asiri-genellesir ve "okunamayan obje" sinifi TERS yonden geri gelir.

SAP GEREKTIRMEZ: HTTP katmani sahtelenir; olculen sey URL KURULUSUDUR. (Canli teyit
ayri bir kanit satiridir, bu korpusun yerine GECMEZ.)

MUTASYON: python tests/fixtures/adt_uc_url_cozumu/run.py --mutasyon  -> fix ONCESI surum
          (taban `e3484a1` = kusurun CANLI oldugu SHA; DAL ADI / `main` / `HEAD` VERME:
           hareketli ref merge sonrasi "fix SONRASI"na kayar ve korpus sessizce bosalir).
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Kurulum teshisi STDOUT SWAP'indan ONCE yakalanmali (class_include_push D2/4 dersi):
# `yukle()` import penceresinde stdout/stderr'i atilabilir tampona cevirir; oradan
# basilan sebep DISARIDAN GORULMEZ ve `KURULAMADI(rc=2): <bos>` kalir.
_GERCEK_ERR = sys.stderr

KOK = Path(__file__).resolve().parents[3]
if not (KOK / "scripts" / "object_types.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


ap = argparse.ArgumentParser(add_help=True)
ap.add_argument("--mutasyon", action="store_true", help="fix ONCESI surumu yukle")
ap.add_argument("--ref", default="e3484a1",
                help="mutasyon tabani: kusurun CANLI oldugu SHA (dal adi VERME)")
ARG = ap.parse_args()

KUM = Path(tempfile.mkdtemp(prefix="adturl_"))
_eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
(KUM / ".conn_adt").write_text(
    "ADT_SAP_URL=https://ornek.invalid\nADT_SAP_USER=TESTUSER\n"
    "ADT_SAP_PASSWORD=x\nADT_SAP_CLIENT=100\nADT_SAP_TIER=DEV\n", encoding="utf-8")
os.chdir(KUM)
sys.path.insert(0, str(KOK / "scripts"))

MUTASYONLU_DOSYALAR = ("scripts/object_types.py", "scripts/sap_adt_lib.py",
                       "scripts/push_object.py")


def _temizle() -> None:
    try:
        os.chdir(_eski_cwd)
    except Exception:
        pass
    shutil.rmtree(KUM, ignore_errors=True)


def git_show(rel: str) -> str:
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{ARG.ref}:{rel}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"[DOGRULANAMADI] git show {ARG.ref}:{rel} -> {r.stderr.strip()[:200]}",
              file=_GERCEK_ERR, flush=True)
        print("  Tipik sebep: SIG KLON (CI `actions/checkout` fetch-depth 1) — pinli "
              "taban SHA'nin blob'u o klonda YOK.", file=_GERCEK_ERR, flush=True)
        _temizle()
        sys.exit(2)
    return r.stdout


def yukle(rel: str, ad: str):
    """Modulu yukle. Mutasyonda kaynak git'ten gelir (calisma agacina DOKUNULMAZ)."""
    yedek_out, yedek_err = sys.stdout, sys.stderr
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    try:
        if ARG.mutasyon:
            p = KUM / f"{ad}_taban.py"
            p.write_text(git_show(rel), encoding="utf-8")
            spec = importlib.util.spec_from_file_location(ad, p)
            m = importlib.util.module_from_spec(spec)      # type: ignore[arg-type]
            sys.modules[ad] = m
            spec.loader.exec_module(m)                     # type: ignore[union-attr]
            return m
        return importlib.import_module(ad)
    finally:
        sys.stdout, sys.stderr = yedek_out, yedek_err


OT = yukle("scripts/object_types.py", "object_types")
L = yukle("scripts/sap_adt_lib.py", "sap_adt_lib")

if ARG.mutasyon:
    print(f"### MUTASYON MODU — object_types/sap_adt_lib/push_object @ {ARG.ref} (fix ONCESI)\n")

# ── OZ-DENETIM: taban gercekten "fix ONCESI" mi? ─────────────────────────────
if ARG.mutasyon:
    _yetenek_var = hasattr(OT, "ensure_source_url")
    try:
        OT.get_object_url("ZSD001_FM_ORNEK", "func")
        _kapi_var = False                      # URL uretti -> kapi YOK (beklenen taban)
    except Exception:
        _kapi_var = True
    if _yetenek_var or _kapi_var:
        print(f"[DOGRULANAMADI] MUTASYON TABANI GECERSIZ: '{ARG.ref}' fix-ONCESI surum DEGIL "
              f"(ensure_source_url var mi={_yetenek_var}, func kapisi var mi={_kapi_var}).")
        print("  Tipik sebep: --ref bir DAL adi ve fix merge edildi -> taban 'fix SONRASI'na kaydi.")
        print("  Cozum: kusurun CANLI oldugu SHA'yi ver -> --ref e3484a1")
        _temizle()
        sys.exit(2)
    print("### taban oz-denetimi OK — bu ref'te ne ensure_source_url ne de func kapisi VAR\n")


def _es(cagri, *a, **k):
    """(deger, hata) — mutasyonda metot HIC olmayabilir: COKME degil OLCUM."""
    try:
        return cagri(*a, **k), None
    except Exception as exc:                                # noqa: BLE001
        return None, exc


def _uret(ad: str, *a, **k):
    fn = getattr(OT, ad, None)
    if fn is None:
        return None, AttributeError(f"{ad} YOK (fix oncesi)")
    return _es(fn, *a, **k)


INC = "/sap/bc/adt/oo/classes/zcl_ornek/includes/testclasses"
CLS = "/sap/bc/adt/oo/classes/zcl_ornek"
PRG_INC = "/sap/bc/adt/programs/includes/zincl_ornek"

# ── A1: sinif alt-include ucuna EK YOK (dort segmentin dordu de) ─────────────
_a1_detay, _a1 = [], True
for _kind, _seg in (("ccau", "testclasses"), ("ccimp", "implementations"),
                    ("ccdef", "definitions"), ("ccmac", "macros")):
    u = f"/sap/bc/adt/oo/classes/zcl_ornek/includes/{_seg}"
    v, e = _uret("ensure_source_url", u)
    ok = (v == u)
    _a1 = _a1 and ok
    _a1_detay.append(f"{_kind}->{'AYNI' if ok else (repr(v) if e is None else type(e).__name__)}")
kontrol("A1 sinif alt-include ucuna `/source/main` EKLENMEZ (4/4 segment)",
        _a1, " ".join(_a1_detay))

# ⚠ A2-A5 FP CAPALARI, `ensure_source_url` UZERINDEN DEGIL `get_object_source`
# DAVRANISI uzerinden olculur (ilk yazimda yardimci fonksiyona bakiyorlardi; o zaman
# mutasyonda "fonksiyon YOK" diye DUSUYORLARDI ve boylece FP CAPASI OLMAKTAN CIKIP
# ayirt ediciye donusuyorlardi — "asiri-genelleme olmadi" iddiasini HIC olcmuyorlardi).
# Davranis yuzeyi HER IKI SURUMDE de vardir: bu vektorler mutasyonda da GECMELIDIR.
# (Olcum kurulumu asagida: `oku()` sahte oturumun ISTEDIGI url'i dondurur.)
_FP_CAPALARI: list[tuple[str, str, str]] = [
    ("A2", PRG_INC, "klasik program include'u (`/programs/includes/<X>`)"),
    ("A3a", CLS, "siradan sinif"),
    ("A3b", "/sap/bc/adt/ddic/ddl/sources/zsd001_i_ornek", "cds/ddls"),
    ("A3c", "/sap/bc/adt/ddic/tables/zsd001_t_ornek", "table"),
    ("A5", "/sap/bc/adt/oo/classes/zcl_ornek/includes/beklenmeyen",
     "*taninmayan* include segmenti (muafiyet tahminle genisletilmez)"),
]

# ── A6 TEK KAYNAK: segment listesi CLASS_INCLUDE_TYPES'tan okunur ──────────
_a6, _a6d = False, "ensure_source_url YOK"
if hasattr(OT, "ensure_source_url") and hasattr(OT, "CLASS_INCLUDE_TYPES"):
    _yeni = "/sap/bc/adt/oo/classes/zcl_ornek/includes/sonradaneklenen"
    _once, _ = _es(OT.ensure_source_url, _yeni)
    OT.CLASS_INCLUDE_TYPES["sonradaneklenen"] = {
        "segment": "sonradaneklenen", "abap_include": "CCXX",
        "file_extension": ".ccxx.abap", "description": "test", "olculdu": False}
    try:
        _sonra, _ = _es(OT.ensure_source_url, _yeni)
    finally:
        OT.CLASS_INCLUDE_TYPES.pop("sonradaneklenen", None)
    _a6 = (_once == _yeni + "/source/main") and (_sonra == _yeni)
    _a6d = f"tablo ONCESI={_once!r} SONRASI={_sonra!r}"
kontrol("A6 *TEK KAYNAK*: segmentler CLASS_INCLUDE_TYPES'tan okunur (ikinci literal yok)",
        _a6, _a6d)


# ── DAVRANIS OLCUMU: sahte HTTP oturumu ISTENEN URL'i kaydeder ──────────────
class SahteYanit:
    def __init__(self, kod=200, metin="ABAP KAYNAK\n"):
        self.status_code = kod
        self.text = metin
        self.headers = {}
        self.cookies = {}


class SahteOturum:
    def __init__(self, kod=200):
        self.kod = kod
        self.istenen: list[str] = []

    def get(self, url, **kw):
        self.istenen.append(url)
        return SahteYanit(self.kod, "ABAP KAYNAK\n" if self.kod == 200 else "Not Found")


def istemci(oturum):
    c = object.__new__(L.SAPADTClient)
    c.url = ""
    c.timeout_short = 5
    c.timeout_default = 5
    c.debug_enabled = False
    c.csrf_token = "TOKEN"
    c._get_headers = lambda *a, **k: {}
    c.session = oturum
    return c


def oku(url, kod=200):
    """(sonuc, deger, istenen_url) — sonuc: 'ok' | 'hata'."""
    o = SahteOturum(kod)
    c = istemci(o)
    try:
        return "ok", c.get_object_source(url), (o.istenen[-1] if o.istenen else "")
    except Exception as exc:                                # noqa: BLE001
        return "hata", exc, (o.istenen[-1] if o.istenen else "")


# ── A2-A5 FP CAPALARI: siradan/klasik uclar YINE `/source/main`den okunur ──
for _id, _url, _aciklama in _FP_CAPALARI:
    _s, _d, _u = oku(_url)
    kontrol(f"{_id} *FP*: {_aciklama} EK ALIR (davranis yuzeyi — mutasyonda da GECMELI)",
            _s == "ok" and _u == _url + "/source/main", f"istenen={_u!r}")

# ── A4 FP: zaten kaynak ucu ise CIFT eklenmez ──────────────────────────────
_s, _d, _u = oku(CLS + "/source/main")
kontrol("A4 *FP*: zaten `/source/main` ile biten URL'e ikinci ek YOK",
        _s == "ok" and _u == CLS + "/source/main", f"istenen={_u!r}")

# ── A7 get_object_source include'u CIPLAK uctan okur ───────────────────────
_s, _d, _u = oku(INC)
kontrol("A7 *DAVRANIS*: `get_object_source(<include>)` istegi `/source/main` TASIMAZ",
        _s == "ok" and _u == INC, f"sonuc={_s} istenen={_u!r}")

# ── A8 FP: siradan sinif YINE /source/main'den okunur ──────────────────────
_s, _d, _u = oku(CLS)
kontrol("A8 *FP*: `get_object_source(<class>)` istegi `/source/main` TASIR",
        _s == "ok" and _u == CLS + "/source/main", f"sonuc={_s} istenen={_u!r}")

# ── A9 404 mesaji var olmayan obje adi ILAN ETMEZ ──────────────────────────
_s, _d, _u = oku(INC, kod=404)
_msg = str(_d)
kontrol("A9 404 mesaji 'source'/'includes' diye VAR OLMAYAN obje ILAN ETMEZ",
        _s == "hata" and "not found: source" not in _msg.lower()
        and "not found: includes" not in _msg.lower() and "zcl_ornek" in _msg.lower(),
        f"mesaj={_msg[:120]!r}")

# ── A10 AYIRT EDICI (olcumle ortaya cikti): uydurma ad include'a OZGU DEGILDI ──
# Mutasyon kosumu gosterdi ki fix ONCESI **her** 404 mesaji "Object not found: source"
# diyordu (`split('/')[-2]` siradan objede de 'source'a denk geliyor) -> yani kusur
# include'lardan cok daha genisti; kayitlarda bu yon YOKTU.
_s, _d, _u = oku(CLS, kod=404)
kontrol("A10 siradan objede de 404 mesaji GERCEK obje adini soyluyor ('zcl_ornek')",
        _s == "hata" and "zcl_ornek" in str(_d).lower(), f"mesaj={str(_d)[:120]!r}")

# ── A11 FP CAPASI: istisna SOZLESMESI (tip/kod/endpoint) DEGISMEDI ─────────
_s, _d, _u = oku(CLS, kod=404)
kontrol("A11 *FP*: 404 istisna sozlesmesi ayni (SAPObjectNotFoundError · 404 · endpoint=URL)",
        _s == "hata" and type(_d).__name__ == "SAPObjectNotFoundError"
        and getattr(_d, "status_code", None) == 404
        and getattr(_d, "endpoint", None) == CLS + "/source/main",
        f"tip={type(_d).__name__} kod={getattr(_d, 'status_code', None)} "
        f"endpoint={getattr(_d, 'endpoint', None)!r}")

# ── B1 func generic URL'e girerse ANLASILIR RET ────────────────────────────
_b1, _b1d = True, []
for t in ("func", "function", "FUNC"):
    v, e = _es(OT.get_object_url, "ZSD001_FM_ORNEK", t)
    ok = isinstance(e, ValueError)
    _b1 = _b1 and ok
    _b1d.append(f"{t}->{type(e).__name__ if e else repr(v)}")
kontrol("B1 `func`/`function` generic URL'i: sessiz yanlis adres YOK, ValueError VAR",
        _b1, " ".join(_b1d))

# ── B2: ret mesaji KANONIK yolu ve kanonik ARACI soyluyor ─────────────────
_v, _e = _es(OT.get_object_url, "ZSD001_FM_ORNEK", "func")
_m = str(_e or "")
kontrol("B2 ret mesaji kanonik ucu (`fmodules`) ve kanonik araci "
        "(`set_function_module_source`) soyluyor",
        ("fmodules" in _m and "set_function_module_source" in _m), f"mesaj={_m[:140]!r}")

# ── B3: get_source_url de ayni kapiya carpar ──────────────────────────────
_v, _e = _es(OT.get_source_url, "ZSD001_FM_ORNEK", "func")
kontrol("B3 `get_source_url(..., 'func')` de reddediyor (ikinci giris noktasi acik kalmiyor)",
        isinstance(_e, ValueError), f"{type(_e).__name__ if _e else repr(_v)}")

# ── B4 FP: komsu tiplerin URL'i BIREBIR ayni ──────────────────────────────
_beklenen = {
    ("ZSD001_FG_ORNEK", "fugr"): "/sap/bc/adt/functions/groups/zsd001_fg_ornek",
    ("ZCL_ORNEK", "class"): "/sap/bc/adt/oo/classes/zcl_ornek",
    ("ZSD001_I_ORNEK", "ddls"): "/sap/bc/adt/ddic/ddl/sources/zsd001_i_ornek",
    ("ZSD001_T_ORNEK", "table"): "/sap/bc/adt/ddic/tables/zsd001_t_ornek",
    ("ZSD001_P_ORNEK", "prog"): "/sap/bc/adt/programs/programs/zsd001_p_ornek",
    ("ZSD001_INCL", "include"): "/sap/bc/adt/programs/includes/zsd001_incl",
}
_b4 = [(k[1], _es(OT.get_object_url, k[0], k[1])[0] == v) for k, v in _beklenen.items()]
kontrol("B4 *FP*: alti komsu tipin URL'i BIREBIR degismedi (fugr dahil)",
        all(o for _, o in _b4), f"{_b4}")

# ── B5 FP: `func` girdisi SILINMEDI — diger alanlar korunuyor ─────────────
_b5 = (_es(OT.get_adt_type, "func")[0] == "FUNC/FF"
       and _es(OT.get_file_extension, "func")[0] == ".func.abap"
       and _es(OT.get_local_subdir, "func")[0] == "fugr"
       and "function" in (_es(OT.list_supported_types)[0] or []))
kontrol("B5 *FP*: `function` girdisi KALDI (adt_type / uzanti / yerel dizin / tip listesi)",
        _b5, f"adt_type={_es(OT.get_adt_type, 'func')[0]}")

# ── B6: ters-arama `url_path=None` ile COKMUYOR ───────────────────────────
_v, _e = _es(OT.get_adt_type_from_url,
             "/sap/bc/adt/functions/groups/zsd001_fg/fmodules/zsd001_fm/source/main")
kontrol("B6 `get_adt_type_from_url` bos `url_path` tararken COKMUYOR",
        _e is None, f"deger={_v!r} hata={_e!r}")

# ── B7 Q228 TUKETICI KANITI: ATC yolu ayni tabloyu tuketir ────────────────
_b7, _b7d = False, ""
try:
    SC = yukle("scripts/sap_client.py", "sap_client")

    class _SahteAdt:
        def __init__(self):
            self.cagrilan: list[str] = []

        def run_atc_check(self, url, **kw):
            self.cagrilan.append(url)
            return {"findings": []}

    _stub = _SahteAdt()
    _sc = object.__new__(SC.SAPClient)
    _sc.adt_client = _stub
    _tampon = io.StringIO()
    _yedek = sys.stdout
    sys.stdout = _tampon
    try:
        _sonuc = _sc.run_atc_check("ZSD001_FM_ORNEK", "func")
    except Exception as exc:                                # noqa: BLE001
        _sonuc = f"EXC:{type(exc).__name__}"
    finally:
        sys.stdout = _yedek
    _cikti = _tampon.getvalue()
    _b7 = (not _stub.cagrilan) and ("fmodules" in _cikti or "fmodules" in str(_sonuc))
    _b7d = (f"ATC'ye giden url={_stub.cagrilan!r} "
            f"cikti={' '.join(_cikti.split())[-110:]!r}")
except Exception as exc:                                    # noqa: BLE001
    _b7, _b7d = False, f"sap_client yuklenemedi: {type(exc).__name__}: {exc}"
kontrol("B7 *Q228*: ATC yolu ayni tabloyu tuketir -> artik YANLIS ADRES uretmiyor, "
        "kapiya carpiyor", _b7, _b7d)

# ── B8: `supports_generic_url()` beyani ───────────────────────────────────
_b8 = (_uret("supports_generic_url", "class")[0] is True
       and _uret("supports_generic_url", "func")[0] is False)
kontrol("B8 `supports_generic_url()`: class=True · func=False (cagiran ONCEDEN sorabilir)",
        _b8, f"class={_uret('supports_generic_url', 'class')[0]} "
             f"func={_uret('supports_generic_url', 'func')[0]}")

# ── 3. BAGLAM (gorev-DISI): AYRI SUREC + GERCEK CLI giris noktasi ─────────
# Kum agacina scripts/ kopyalanir; mutasyonda uc dosya git'ten gelenlerle DEGISTIRILIR.
# Boylece CLI vektoru de mutasyonda AYIRT EDICI olur (alt surec calisma agacini kosarsa
# mutasyonda sahte-YESIL verirdi).
_KUM_SCRIPTS = KUM / "scripts"
_cli_kuruldu = True
try:
    shutil.copytree(KOK / "scripts", _KUM_SCRIPTS,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if ARG.mutasyon:
        for rel in MUTASYONLU_DOSYALAR:
            (KUM / rel).write_text(git_show(rel), encoding="utf-8")
except Exception as exc:                                    # noqa: BLE001
    _cli_kuruldu = False
    print(f"[DOGRULANAMADI] kum scripts/ kurulamadi: {exc}", file=_GERCEK_ERR, flush=True)


def _cli(*args):
    r = subprocess.run([sys.executable, *args], cwd=str(KUM), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=180)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


if _cli_kuruldu:
    _rc, _out = _cli(str(_KUM_SCRIPTS / "push_object.py"), "--name", "ZSD001_FM_ORNEK",
                     "--type", "func", "--transport", "TRXXXXXX", "--cwd", str(KUM))
    kontrol("C1 *3.BAGLAM* (ayri surec, gercek CLI): `--type func` -> rc=2 + YONLENDIRME",
            _rc == 2 and "YONLENDIRME" in _out,
            f"rc={_rc} cikti={' '.join(_out.split())[-140:]!r}")

    _rc2, _out2 = _cli(str(_KUM_SCRIPTS / "object_types.py"))
    kontrol("C2 3.BAGLAM: `object_types.py` demosu `url_path=None` ile COKMUYOR (rc=0)",
            _rc2 == 0 and "Function Module" in _out2,
            f"rc={_rc2} cikti_son={' '.join(_out2.split())[-80:]!r}")
else:
    kontrol("C1 *3.BAGLAM* (ayri surec, gercek CLI)", False, "kum kurulamadi")
    kontrol("C2 3.BAGLAM: object_types.py demosu", False, "kum kurulamadi")

# ── RAPOR ────────────────────────────────────────────────────────────────
print("=" * 78)
print("adt_uc_url_cozumu — ADT uc URL'i: `/source/main` NEREYE eklenir/eklenmez")
print("=" * 78)
_gecen = 0
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if detay:
        print(f"         {detay}")
    _gecen += 1 if ok else 0
print("-" * 78)
print(f"SONUC: {_gecen}/{len(SONUC)}")
_temizle()
sys.exit(0 if _gecen == len(SONUC) else 1)

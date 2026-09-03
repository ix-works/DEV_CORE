# -*- coding: utf-8 -*-
"""TRANSPORT: GOREV(S) -> UST ISTEK(K) CEVRIMI **UC YAZMA YOLUNDA DA** kosar mi?

SINIF (Q219 + Q207 + Q220 + Q215 — dordu TEK KOK, `infra-findings`):
SAP kilit yanitindaki `CORRNR` **daima K-tipi IS TALEBI**dir. Araca S-tipi **gorev**
numarasi verilirse uyusmazlik DAIMA olur. Bu evde ayni hata **dort kez** tur yakti.
Cevrimi yapan tek yol `push_object` idi:

  | yol                          | gorev->istek cevrimi | uyusmazlikta            |
  |------------------------------|----------------------|-------------------------|
  | `SAPClient.push_object`      | VAR (`_find_existing_transport`) | Bug-11 auto-retry |
  | `SAPClient.push_class_include` | **YOKTU** -> Q207   | sert duser (SAPLockError)|
  | `SAPADTClient.set_function_module_source` | **YOKTU** -> Q215 | `CTS_WBO_API 020` |

Ayrica ayni yanlis degismez IKI dosyada METIN olarak yaziliydi (Q219: `sap_adt_lib`
docstring'i + `sap_client` kod yorumu) — *"S-tipi vermek guvenlidir, nasilsa eslesir"*
diye okunuyordu. Metin de bu korpusta olculur (C bolumu): kusur davranista degil
BELGEDEYDI, ama bedeli ayniydi.

⚠ **NE OLCULMEZ (durustluk siniri):** bu korpus HTTP katmanini SAHTELESTIRIR. Olctugu
sey *"kodumuz LOCK yanitindaki CORRNR'i otorite aliyor ve gorev->istek cevirisini
yapiyor mu"*dur — SAP'nin gercekten bu degerleri dondurdugu DEGIL. Canli olcumler
kayitlarda: `CTS_WBO_API 020` (S ile 500 / K ile 200, kontrol deneyli, 2026-08-30) ve
`populate_tables` 9/9 vs 9/9 (2026-08-19).

⚠ **GEVSETME CAPALARI OMURGADIR** (A4 · B3 · B4): fix iki yerde bir KURTARMA acar
(dun sert dusen yol bugun yuruyor). A4 *"cozum bulunamazsa HALA sert duser ve
auto-retry EKLENMEDI"*, B3 *"YABANCI transport'ta PUT HIC ATILMAZ"*, B4 *"bos CORRNR
hata DEGIL"* — bu ucu silinirse korpus gevsemeyi olcmez olur.

Kosum   : python tests/fixtures/transport_gorev_istek_cevrimi/run.py            -> 23/23
MUTASYON: python tests/fixtures/transport_gorev_istek_cevrimi/run.py --mutasyon  -> 10/23
          (13 ayirt edici FAIL; gecen 10'un TAMAMI FP capasi / gevsetme capasi /
           envanter capasi — yani "iki surumde de dogru olmasi gereken" iddialar.)
          (taban = `e3484a1`; ⛔ DAL ADI / `main` / `HEAD` VERME — hareketli ref fix
           merge edilince "fix SONRASI"na kayar ve korpus SESSIZCE bosalir.)
"""
from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Tesihs akisi: `yukle()` import-aninda stdout'u SARMALAR; kurulum hatalari o tampona
# giderse `KURULAMADI(rc=2): <bos>` gorunur (ariza VAR, sebep YOK). Gercek stderr saklanir.
_GERCEK_ERR = sys.stderr

KOK = Path(__file__).resolve().parents[3]
SONUC: list[tuple[str, bool, str]] = []

TR_ISTEK = "AB1K900029"      # K-tipi WORKBENCH REQUEST  (araca verilmesi gereken)
TR_GOREV = "AB1K918735"      # S-tipi TASK               (siklikla yanlislikla verilen)
TR_YABANCI = "AB1K900777"    # baska gelistiricinin istegi


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


ap = argparse.ArgumentParser(add_help=True)
ap.add_argument("--mutasyon", action="store_true", help="fix ONCESI surumu yukle")
ap.add_argument("--ref", default="e3484a1",
                help="mutasyon tabani: kusurun CANLI oldugu SHA (dal adi VERME)")
ARG = ap.parse_args()

KUM = Path(tempfile.mkdtemp(prefix="trkorr_"))
_eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
(KUM / ".conn_adt").write_text(
    "ADT_SAP_URL=https://ornek.invalid\nADT_SAP_USER=TESTUSER\n"
    "ADT_SAP_PASSWORD=x\nADT_SAP_CLIENT=100\nADT_SAP_TIER=DEV\n", encoding="utf-8")
os.chdir(KUM)
sys.path.insert(0, str(KOK / "scripts"))


def git_show(rel: str) -> str:
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{ARG.ref}:{rel}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"[DOGRULANAMADI] git show {ARG.ref}:{rel} -> {r.stderr.strip()[:200]}",
              file=_GERCEK_ERR, flush=True)
        print("  Tipik sebep: SIG KLON (CI `actions/checkout` fetch-depth 1) — pinli "
              "taban SHA'nin blob'u o klonda YOK. Mutasyon kipi YERELDE kosulur.",
              file=_GERCEK_ERR, flush=True)
        sys.exit(2)
    return r.stdout


def kaynak(rel: str) -> str:
    """Modulle AYNI YERDEN oku. Diskten okuyan statik capa mutasyonda sahte-PASS verir."""
    return git_show(rel) if ARG.mutasyon else (KOK / rel).read_text(encoding="utf-8")


def yukle(rel: str, ad: str):
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


L = yukle("scripts/sap_adt_lib.py", "sap_adt_lib")
C = yukle("scripts/sap_client.py", "sap_client")

if ARG.mutasyon:
    print(f"### MUTASYON MODU — sap_client/sap_adt_lib @ {ARG.ref} (fix ONCESI)\n")


# ── OZ-DENETIM: taban gercekten "fix ONCESI" mi? ─────────────────────────────
#   Hareketli ref = olcum aletinin SESSIZ bosalmasi. Sayi raporlamadan exit 2.
if ARG.mutasyon:
    _sc = git_show("scripts/sap_client.py")
    _sl = git_show("scripts/sap_adt_lib.py")
    _bozuk = []
    if "_find_existing_transport(class_name" in _sc:
        _bozuk.append("push_class_include ZATEN cevrimi yapiyor")
    if "etkin_transport" in _sl:
        _bozuk.append("set_function_module_source ZATEN CORRNR okuyor")
    if _bozuk:
        print(f"[DOGRULANAMADI] MUTASYON TABANI GECERSIZ: '{ARG.ref}' fix-ONCESI surum "
              f"DEGIL ({'; '.join(_bozuk)}).")
        print("  Tipik sebep: --ref bir DAL adi/HEAD ve fix merge edildi.")
        print("  Cozum: kusurun CANLI oldugu SHA'yi ver -> --ref e3484a1")
        os.chdir(_eski_cwd)
        shutil.rmtree(KUM, ignore_errors=True)
        sys.exit(2)
    print("### taban oz-denetimi OK — bu ref'te cevrim GERCEKTEN yok\n")


# =============================================================================
# A — `SAPClient.push_class_include` (Q207 / Q220)
# =============================================================================
DP_NS = "http://www.sap.com/adt/dataPreview"


def dp_govde(sutunlar: dict) -> str:
    """Gercek datapreview sekli: her sutun `dp:metadata@name` + `dp:data` listesi."""
    bloklar = ""
    for ad, degerler in sutunlar.items():
        veri = "".join(f"<dp:data>{d}</dp:data>" for d in degerler)
        bloklar += f'<dp:columns><dp:metadata dp:name="{ad}"/>{veri}</dp:columns>'
    return f'<?xml version="1.0"?><dp:tableData xmlns:dp="{DP_NS}">{bloklar}</dp:tableData>'


# E071 satiri: obje S-tipi GOREV'de kayitli, o gorevin ust istegi (STRKORR) K-tipi.
E071_GOREV_ALTINDA = dp_govde({
    "TRKORR": [TR_GOREV], "STRKORR": [TR_ISTEK], "AS4USER": ["TESTUSER"],
    "PGMID": ["R3TR"], "OBJECT": ["CLAS"]})
# Adaylarin HEPSI baska kullanicinin -> `foreign_only` (bilincli politika, DOKUNULMADI)
E071_YABANCI = dp_govde({
    "TRKORR": [TR_YABANCI], "STRKORR": [""], "AS4USER": ["OTHERUSER"],
    "PGMID": ["R3TR"], "OBJECT": ["CLAS"]})


class SahteAdtSinif:
    """SAP'nin OLCULEN kilit davranisi: CORRNR daima K-tipi ISTEK; farkliysa SAPLockError."""

    def __init__(self, corrnr=TR_ISTEK, sorgu_xml=E071_GOREV_ALTINDA):
        self.user = "TESTUSER"
        self.corrnr = corrnr
        self.sorgu_xml = sorgu_xml
        self.lock_cagrilari: list = []
        self.sorgu_sayisi = 0
        self.push_transport = None
        self._last_lock_effective_transport = None
        self._last_lock_is_link_up = ""

    def run_query(self, q, row_number=50):
        self.sorgu_sayisi += 1
        return self.sorgu_xml

    def lock_object(self, url, transport=None):
        self.lock_cagrilari.append(transport)
        self._last_lock_effective_transport = self.corrnr or transport
        if transport and self.corrnr and transport.upper() != self.corrnr.upper():
            raise L.SAPLockError(
                f"SAP assigned transport {self.corrnr} but {transport} was requested.")
        return "LOCK1"

    def push_class_include(self, cls, kind, src, lock_handle=None, transport=None):
        self.push_transport = transport
        return {"created": False, "verified": True}

    def unlock_object(self, url, handle):
        return True

    def activate_object(self, name, url):
        return {"success": True}


KAYNAK_DOSYA = KUM / "ZCL_ORNEK.ccau.abap"
KAYNAK_DOSYA.write_text("CLASS ltc_x DEFINITION FOR TESTING.\nENDCLASS.\n", encoding="utf-8")


def include_push(adt, transport):
    """(sonuc-dict, stdout) — GERCEK `SAPClient.push_class_include` govdesi kosar."""
    c = object.__new__(C.SAPClient)
    c.adt_client = adt
    c.debug_enabled = False
    c.local_base = KUM / "classes"
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        r = c.push_class_include("ZCL_ORNEK", "ccau", transport=transport,
                                 source_file=str(KAYNAK_DOSYA))
    return r, tampon.getvalue()


# A1/A2 AYIRT EDICI — kusurun ta kendisi
adt = SahteAdtSinif()
r, cikti = include_push(adt, TR_GOREV)
kontrol("A1 AYIRT EDICI: S-tipi GOREV numarasiyla alt-include push'u GECIYOR "
        "(eskiden ayni numara ana sinifta geciyor, burada TRANSPORT MISMATCH ile duruyordu)",
        r.get("success") is True and adt.lock_cagrilari == [TR_ISTEK],
        f"success={r.get('success')} error={str(r.get('error'))[:120]!r} "
        f"lock_cagrilari={adt.lock_cagrilari}")

kontrol("A2 AYIRT EDICI: cevrim GERCEKTEN kostu — E071 sorgusu atildi ve cikti "
        "'using it instead of' ile hangi numaraya gecildigini SOYLUYOR",
        adt.sorgu_sayisi == 1 and "using it instead of" in cikti,
        f"sorgu={adt.sorgu_sayisi} cikti={cikti.strip()[-220:]!r}")

kontrol("A3 AYIRT EDICI: PUT/push'a giden transport da COZULMUS istek (ham gorev DEGIL)",
        adt.push_transport == TR_ISTEK, f"push_transport={adt.push_transport!r}")

# A4 POZITIF KONTROL / GEVSETME CAPASI — cozum bulunamazsa HALA sert duser
adt_y = SahteAdtSinif(corrnr=TR_YABANCI, sorgu_xml=E071_YABANCI)
r_y, cikti_y = include_push(adt_y, TR_GOREV)
kontrol("A4 GEVSETME CAPASI: adaylar BASKA kullanicinin (foreign_only) -> cevrim YAPILMAZ, "
        "istenen numara korunur ve yol ESKISI GIBI SERT DUSER (auto-retry EKLENMEDI)",
        r_y.get("success") is False and r_y.get("error_type") == "SAPLockError"
        and adt_y.lock_cagrilari == [TR_GOREV],
        f"success={r_y.get('success')} tip={r_y.get('error_type')} "
        f"lock_cagrilari={adt_y.lock_cagrilari} [tek cagri = retry YOK]")

# A5 FP CAPASI — dogru numara verildiginde davranis DEGISMEDI, gurultu EKLENMEDI
adt_k = SahteAdtSinif()
r_k, cikti_k = include_push(adt_k, TR_ISTEK)
kontrol("A5 FP CAPASI: K-tipi ISTEK verildiginde push gecer ve 'using it instead of' "
        "gurultusu BASILMAZ (dogru girdi cezalandirilmaz)",
        r_k.get("success") is True and adt_k.lock_cagrilari == [TR_ISTEK]
        and "using it instead of" not in cikti_k,
        f"success={r_k.get('success')} lock={adt_k.lock_cagrilari}")

# A6 FP CAPASI — transport YOK: sorgu hic atilmaz, akis kirilmaz
adt_n = SahteAdtSinif(corrnr=None)
r_n, _ = include_push(adt_n, None)
kontrol("A6 FP CAPASI: transport=None -> E071 sorgusu HIC atilmaz, push yine gecer",
        r_n.get("success") is True and adt_n.sorgu_sayisi == 0,
        f"success={r_n.get('success')} sorgu={adt_n.sorgu_sayisi}")


# =============================================================================
# B — `SAPADTClient.set_function_module_source` (Q215)
# =============================================================================
class SahteYanit:
    def __init__(self, text="", status_code=200):
        self.text, self.status_code = text, status_code
        self.headers, self.cookies = {}, {}


def lock_xml(corrnr=None, is_link_up=None, handle="LOCK-H1"):
    parcalar = [f"<LOCK_HANDLE>{handle}</LOCK_HANDLE>"]
    if corrnr is not None:
        parcalar.append(f"<CORRNR>{corrnr}</CORRNR>")
    if is_link_up is not None:
        parcalar.append(f"<IS_LINK_UP>{is_link_up}</IS_LINK_UP>")
    return ('<asx:abap xmlns:asx="http://www.sap.com/abapxml"><asx:values><DATA>'
            + "".join(parcalar) + "</DATA></asx:values></asx:abap>")


class SahteOturumFM:
    def __init__(self, kilit_govde, kilit_kod=200, put_kod=200):
        self.headers: dict = {}
        self._kilit, self._kilit_kod, self._put_kod = kilit_govde, kilit_kod, put_kod
        self.iz: list[str] = []
        self.put_params: dict = {}

    def post(self, url, params=None, headers=None, data=None, timeout=None):
        eylem = (params or {}).get("_action")
        self.iz.append(f"POST:{eylem}")
        if eylem == "LOCK":
            return SahteYanit(self._kilit, self._kilit_kod)
        return SahteYanit("", 200)

    def put(self, url, params=None, headers=None, data=None, timeout=None):
        self.iz.append("PUT")
        self.put_params = dict(params or {})
        return SahteYanit("", self._put_kod)


def fm_push(oturum, transport):
    """(sonuc, deger, stdout, istemci) — GERCEK `set_function_module_source` govdesi."""
    c = object.__new__(L.SAPADTClient)
    c.url = ""
    c.session = oturum
    c.timeout_default, c.timeout_short = 5, 5
    c.debug_enabled = False
    c.csrf_token = "TOKEN"
    c.fetch_csrf_token = lambda force_refresh=False: "TOKEN"
    c.activate_object = lambda ad, url: {"success": True}
    tampon = io.StringIO()
    try:
        with redirect_stdout(tampon):
            return "ok", c.set_function_module_source(
                "ZSD001_FM_ORNEK", "ZSD001_FG_ORNEK", "FUNCTION x.\nENDFUNCTION.\n",
                transport=transport), tampon.getvalue(), c
    except Exception as exc:                                    # noqa: BLE001
        return "hata", exc, tampon.getvalue(), c


# B1/B2 AYIRT EDICI — LOCK yanitindaki CORRNR otorite mi?
ot = SahteOturumFM(lock_xml(corrnr=TR_ISTEK, is_link_up=""))
s, d, cikti, ist = fm_push(ot, TR_GOREV)
kontrol("B1 AYIRT EDICI: S-tipi GOREV verilse de PUT `corrNr` = LOCK yanitindaki CORRNR "
        "(K-tipi ISTEK) — eskiden verilen gorev gidiyor ve CTS_WBO_API 020 aliniyordu",
        s == "ok" and ot.put_params.get("corrNr") == TR_ISTEK,
        f"sonuc={s} put_params={ot.put_params} deger={str(d)[:120]}")

# ⚠ CAPA DIZELERI CIKTININ GERCEK YAZIMINDAN alinir: uretim metni TURKCE aksanli
#   ("KABUL EDİLMEDİ" / "DOĞRULANMADI"). ASCII yazilirsa negatif capa DAIMA gecer
#   (yalanci anchor), pozitif capa DAIMA duser. Aksan tasimayan alt-dizge secildi.
IZ_KABUL_ED = "TRANSPORT KABUL ED"          # "İSTENEN TRANSPORT KABUL EDİLMEDİ"
IZ_ISTEK_VER = "STEK verilir"               # "Araca İSTEK verilir."
IZ_DOGRULANMADI = "RULANMADI"               # "DOĞRULANMADI"

kontrol("B2 AYIRT EDICI: uyusmazlik SESSIZ degil — 'ISTENEN TRANSPORT KABUL EDILMEDI' + "
        "'araca ISTEK verilir' teshisi basiliyor",
        IZ_KABUL_ED in cikti and IZ_ISTEK_VER in cikti,
        f"cikti={cikti.strip()[:260]!r}")

kontrol("B3 AYIRT EDICI (3. TUKETICI): son-kilit durum sozlesmesi de dolduruluyor "
        "(`_last_lock_effective_transport`) — bu yol o alani HIC yazmiyordu",
        getattr(ist, "_last_lock_effective_transport", None) == TR_ISTEK
        and getattr(ist, "_last_lock_corrnr", None) == TR_ISTEK,
        f"effective={getattr(ist, '_last_lock_effective_transport', None)!r} "
        f"corrnr={getattr(ist, '_last_lock_corrnr', None)!r}")

# B4 GEVSETME CAPASI / POZITIF KONTROL — YABANCI transport'ta PUT HIC ATILMAZ
ot_y = SahteOturumFM(lock_xml(corrnr=TR_YABANCI, is_link_up="X"))
s_y, d_y, cikti_y, _ = fm_push(ot_y, TR_ISTEK)
kontrol("B4 GEVSETME CAPASI: CORRNR farkli VE IS_LINK_UP='X' (baska gelistiricinin "
        "transport'u) -> PUT HIC ATILMAZ, 409 ile durur, kilit BIRAKILIR",
        s_y == "hata" and "FOREIGN" in str(d_y) and getattr(d_y, "status_code", None) == 409
        and "PUT" not in ot_y.iz and "POST:UNLOCK" in ot_y.iz,
        f"sonuc={s_y} iz={ot_y.iz} deger={str(d_y)[:160]!r}")

# B5 FP CAPASI — BOS CORRNR HATA DEGIL (2026-08-09 karari: DDLS/DTEL/DOMA aileleri)
ot_b = SahteOturumFM(lock_xml(corrnr=None, is_link_up=None))
s_b, d_b, cikti_b, _ = fm_push(ot_b, TR_ISTEK)
kontrol("B5 FP CAPASI: CORRNR YOK -> hata YOK, istenen transport'la PUT edilir "
        "(kor kontrol uc obje ailesini kirardi — 2026-08-09 karari)",
        s_b == "ok" and ot_b.put_params.get("corrNr") == TR_ISTEK,
        f"sonuc={s_b} put_params={ot_b.put_params}")

kontrol("B5b AYIRT EDICI: ama SESSIZ de degil — 'CORRNR YOK / DOGRULANMADI' izi birakiliyor",
        "CORRNR YOK" in cikti_b and IZ_DOGRULANMADI in cikti_b,
        f"cikti={cikti_b.strip()[:200]!r}")

# B6 FP CAPASI — dogru numara: davranis ayni, gurultu YOK
ot_k = SahteOturumFM(lock_xml(corrnr=TR_ISTEK, is_link_up=""))
s_k, d_k, cikti_k, _ = fm_push(ot_k, TR_ISTEK)
kontrol("B6 FP CAPASI: CORRNR == istenen -> PUT ayni numarayla, 'KABUL EDILMEDI' "
        "gurultusu BASILMAZ",
        s_k == "ok" and ot_k.put_params.get("corrNr") == TR_ISTEK
        and IZ_KABUL_ED not in cikti_k,
        f"sonuc={s_k} cikti={cikti_k.strip()[:160]!r}")

# B7 FP CAPASI — kilit basarisizligi eski davranisini korudu
ot_f = SahteOturumFM("<err/>", kilit_kod=500)
s_f, d_f, _, _ = fm_push(ot_f, TR_ISTEK)
kontrol("B7 FP CAPASI: LOCK 500 -> 'FM lock failed' hatasi, PUT atilmaz (eski davranis)",
        s_f == "hata" and "lock failed" in str(d_f) and "PUT" not in ot_f.iz,
        f"sonuc={s_f} iz={ot_f.iz} deger={str(d_f)[:120]!r}")


# =============================================================================
# C — Q219: AYNI YANLIS DEGISMEZIN IKI METIN KOPYASI
#     (kusur davranista degil BELGEDEYDI; okuyan *"S vermek guvenli"* saniyordu)
# =============================================================================
_SL_SRC = kaynak("scripts/sap_adt_lib.py")
_SC_SRC = kaynak("scripts/sap_client.py")

kontrol("C1 AYIRT EDICI (kopya 1/2, docstring): 'CORRNR daima eslesir' iddiasi KALKTI ve "
        "yerine 'S-tipi GOREV DAIMA uyusmazlik verir' yaziyor",
        "which always matches" not in _SL_SRC and "ALWAYS mismatches" in _SL_SRC,
        f"eski_ibare={'which always matches' in _SL_SRC} "
        f"yeni_ibare={'ALWAYS mismatches' in _SL_SRC}")

kontrol("C2 AYIRT EDICI (kopya 2/2, kod yorumu): `sap_client` artik 'etkin transport "
        "istenenle daima ayni olur' DEMIYOR; esitligin bir DONUSUMUN sonucu oldugunu soyluyor",
        "should always equal the requested transport" not in _SC_SRC
        and "araca" in _SC_SRC and "STEK (K) verilir" in _SC_SRC,
        f"eski_ibare={'should always equal the requested transport' in _SC_SRC}")


# =============================================================================
# D — AST CAPALARI: metin degil YAPI (kablolama gercekten var mi)
# =============================================================================
#   ⚠ YORUM METNI SAYILMAZ: `ast.get_source_segment` yorumlari da getirir, o yuzden
#     capalar DUGUM uzerinden kurulur (bu turda D3 once metinle yazildi ve kendi
#     aciklama yorumumdaki "lock_object" gecislerini CAGRI sandi -> sahte-KIRMIZI).
def govde_dugumu(src: str, ad: str, sinif: str | None = None):
    agac = ast.parse(src)
    kapsam = agac
    if sinif:
        for d in ast.walk(agac):
            if isinstance(d, ast.ClassDef) and d.name == sinif:
                kapsam = d
                break
        else:
            return None
    for d in ast.walk(kapsam):
        if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)) and d.name == ad:
            return d
    return None


def cagri_adlari(dugum) -> list[str]:
    if dugum is None:
        return []
    adlar = []
    for n in ast.walk(dugum):
        if isinstance(n, ast.Call):
            adlar.append(getattr(n.func, "attr", None) or getattr(n.func, "id", "") or "")
    return adlar


def sabit_argumanli_cagri(dugum, ad: str, sabit: str) -> bool:
    """`<...>.<ad>(..., '<sabit>')` bicimli GERCEK bir cagri var mi (yorum DEGIL)."""
    if dugum is None:
        return False
    for n in ast.walk(dugum):
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == ad:
            for a in n.args:
                if isinstance(a, ast.Constant) and a.value == sabit:
                    return True
    return False


_fm = govde_dugumu(_SL_SRC, "set_function_module_source", "SAPADTClient")
kontrol("D1 AST: `set_function_module_source` LOCK yanitindan CORRNR **ve** IS_LINK_UP "
        "okuyan GERCEK cagrilar iceriyor (yorumdaki gecisler sayilmaz)",
        sabit_argumanli_cagri(_fm, "_extract_lock_xml_field", "CORRNR")
        and sabit_argumanli_cagri(_fm, "_extract_lock_xml_field", "IS_LINK_UP"),
        f"dugum={_fm is not None} "
        f"corrnr={sabit_argumanli_cagri(_fm, '_extract_lock_xml_field', 'CORRNR')} "
        f"linkup={sabit_argumanli_cagri(_fm, '_extract_lock_xml_field', 'IS_LINK_UP')}")

_inc = govde_dugumu(_SC_SRC, "push_class_include", "SAPClient")
_inc_cagrilar = cagri_adlari(_inc)
kontrol("D2 AST: `SAPClient.push_class_include` `_find_existing_transport` CAGIRIYOR "
        "(ana sinif yoluyla SIMETRI)",
        "_find_existing_transport" in _inc_cagrilar,
        f"dugum={_inc is not None} cagrilar={sorted(set(_inc_cagrilar))[:12]}")

# D3 GEVSETME CAPASI (AST): include yoluna Bug-11 auto-retry TASINMADI — bilincli asimetri.
#    Kaldirilirsa bu satir duser ve karar YENIDEN alinmis olur (sessiz gevsetme YOK).
_lock_sayisi = _inc_cagrilar.count("lock_object")
_lock_handler = any(
    isinstance(h, ast.ExceptHandler) and h.type is not None
    and "LockError" in ast.dump(h.type)
    for h in ast.walk(_inc)) if _inc is not None else False
kontrol("D3 GEVSETME CAPASI (AST): include yolunda `SAPLockError` yakalayip YENIDEN "
        "kilitleyen auto-retry YOK — `lock_object` cagrisi TEK (kurtarma ana yolda kalir)",
        _inc is not None and _lock_sayisi == 1 and not _lock_handler,
        f"lock_object_cagrisi={_lock_sayisi} lock_hatasi_yakalayan_handler={_lock_handler}")


# =============================================================================
# E — 3. BAGLAM (gorev-DISI): SINIF ENVANTERI + kanonik desenin diger uyeleri
# =============================================================================
# ⚠ Bu bolum CALISMA AGACINI okur (mutasyonda da bugunku agac) — bilincli: burada
#   olculen sey "fix kondu mu" degil, SINIFIN GERI KALANININ BEYAN EDILDIGI.
# ⚠ ENVANTER DARALDI 2026-09-04 (6 -> 4) — Q235 turu iki uyeyi TASFIYE etti:
#   `scripts/workflows/_clean_recreate.py` ve `scripts/workflows/_full_cycle_v2.py`
#   `attic/adhoc-fosil/workflows/` altina emekli edildi (cagirani YOK'tu; kusur
#   `<PROJECT_ROOT>` yer tutucusuydu). Bu satir CI'da FAIL vererek degisimi YAKALADI
#   — capa amacina gore calisti: kume daralinca da duser, genisleyince de.
#   Kuyruk kaydi `Q255` bu daralmayi yansitacak sekilde guncellendi.
HAM_KILIT_ACIK = {
    "scripts/create_rap_service.py",
    "scripts/populate_cds_views.py",
    "scripts/populate_message_class.py",
    "scripts/push_bo_atomic.py",
}
_ham = {}
for _py in sorted((KOK / "scripts").rglob("*.py")):
    _rel = _py.relative_to(KOK).as_posix()
    try:
        _txt = _py.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    if "'_action': 'LOCK'" in _txt or '"_action": "LOCK"' in _txt \
            or '"_action":"LOCK"' in _txt or "'_action':'LOCK'" in _txt:
        _ham[_rel] = "CORRNR" in _txt
_acik = {r for r, okur in _ham.items() if not okur}
kontrol("E1 3.BAGLAM/ENVANTER: ham `_action=LOCK` atan ve CORRNR OKUMAYAN dosyalar "
        "TAM OLARAK beyan edilen kume (yeni bir yazma yolu eklenirse bu satir duser)",
        _acik == HAM_KILIT_ACIK,
        f"olculen={sorted(_acik)} beklenen={sorted(HAM_KILIT_ACIK)} "
        f"[fark={sorted(_acik ^ HAM_KILIT_ACIK)}]")

_pt = (KOK / "scripts" / "push_textpool.py").read_text(encoding="utf-8", errors="replace")
_sd = (KOK / "scripts" / "sap_set_object_description.py").read_text(
    encoding="utf-8", errors="replace")
kontrol("E2 3.BAGLAM: kanonik desen bu turdan ONCE de iki bagimsiz yazma yolunda kabluydu "
        "(`push_textpool` + `sap_set_object_description` -> `_last_lock_effective_transport`) "
        "— FM helper'i o supurmenin ATLADIGI uyeydi",
        "_last_lock_effective_transport" in _pt and "_last_lock_effective_transport" in _sd)

_dc = (KOK / "scripts" / "deploy_common_package.py").read_text(encoding="utf-8", errors="replace")
kontrol("E3 3.BAGLAM (KABLOLAMA): `deploy_common_package.py` transport'u HAM gecirir "
        "(cagiran degismedi) — kusuru mirasla aliyordu, duzeltme helper'da oldugu icin "
        "cagirana dokunmadan kapandi",
        "set_function_module_source(name, fg, src, transport=tr" in _dc,
        f"cagri_satiri={'set_function_module_source' in _dc}")

# E4 DURUSTLUK CAPASI: playbook'un ANLATTIGI sey kodun YAPTIGI seyle ayni mi?
#   ⚠ E1-E3'ten farkli olarak bu dosya BU TURDA degisti -> `kaynak()` ile MODULLE AYNI
#     YERDEN okunur; diskten okunsaydi mutasyonda sahte-PASS verirdi.
_pb = kaynak("playbook/adt-fugr-functions.md")
kontrol("E4 DURUSTLUK: playbook §2b artik PUT'un `corrNr`'ini LOCK yanitindaki CORRNR "
        "olarak tarif ediyor (kod ile dokuman AYNI seyi soyluyor)",
        "LOCK yanıtındaki CORRNR" in _pb and "GÖREV (S) değil" in _pb,
        f"corrNr_otoritesi={'LOCK yanıtındaki CORRNR' in _pb}")


os.chdir(_eski_cwd)
shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

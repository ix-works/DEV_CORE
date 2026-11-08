#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""q393_namespace_ad_politikasi — müşteri namespace'i (`/<NS>/`) tek ad politikası (Q393, Issue #397 P1).

NEDEN VAR (2026-11-08)
  ADR 0005-A'nın "müşteri adı" kararı Z/Y önekine sabitti ve on bir dosyada ayrı ayrı yazılıydı:
  projede müşteriye kayıtlı bir namespace'teki HER nesne MCP guardrail'inde `ADR_0005_A` ile
  reddediliyordu. Parti 1: karar tek modüle (`scripts/utils/ad_politikasi.py`) taşındı; kayıtlı
  namespace'ler `project.yaml` → `customer_namespaces` listesinden okunur (fail-closed).

VEKTÖRLER (taban `b0bcfac` = düzeltme öncesi; K bölümü ayırt ediciliği ölçer)
  Y*  yapılandırma: Y1 yok/boş → () · Y2 satır içi + blok liste · Y3 küçük harf normalize ·
      Y4 skaler → hata + kapalı · Y5 geçersiz öğe (eğik çizgisiz / 9+ karakter / `#NS#` / `-`)
      → hata ve TÜM liste kapalı · Y6 env `IX_CUSTOMER_NAMESPACES` OKUNMAZ · Y7 okunamayan yaml → ()
  G*  MCP guardrail: G1 ⭐ kayıtlı NS kabul (tablo/sınıf/kilit nesnesi) · G2 ⭐ kayıtsız `/SCWM/` red
      + mesaj kayıtsızlığı söyler · G3 `/NSPC/` (boş gövde) red · G4 `\\n` sonlu ad red · G5 `E/NSPC/X`
      (enqu) red · G6 geçersiz yapılandırmada NS red + hata mesajda · G7 `reject_standard_delete` aynı
      karar · G8 ⭐ KONTROL: yapılandırma YOKKEN 135 (ad × tip) kararının hepsi tabanla AYNI ·
      G9 ⭐ KONTROL: yapılandırma VARKEN `/`'suz adlarda karar tabanla AYNI · G10 kilit E+Z/Y korunur
  L*  sap_adt_lib: L1 validate_object_name NS sınıf kabul / kayıtsız red / `CL` öneksiz red ·
      L2 validate_package_name NS kabul / kayıtsız red · L3 `_validate_object_name` NS kabul,
      küçük harf red · L4 ⭐ KONTROL: yapılandırmasız üç doğrulayıcı tabanla AYNI
  F*  FUGR: F1 önek/ana program biçimi · F2 `fugr_include_ad_alani_hatasi` NS kabul + Z aynı ·
      F3 ⭐ grup kanıtı NS grupta `FUGR/F name==grup` (canlı biçim) kabul · F4 ⭐ Z grupta FUGR/F
      KANIT DEĞİL (eski kural) · F5 kayıtsız NS grupta FUGR/F red · F6 NS grupta başka ad red ·
      F7 NS grupta `contextRefCount=2` red · F8 MCP `_fugr_include_guardrail` NS önek kuralı
  S*  sap_set_object_description kapısı: S1 NS kabul (kapı geçer) · S2 kayıtsız NS rc 2 · S3 Z kabul
  K*  taban: K1 ⭐ taban guardrail `/NSPC/X`'i yapılandırmayla da REDDEDİYORDU · K2 taban grup kanıtı
      NS FUGR/F gövdesini reddediyordu · K3 taban validate_object_name NS'i reddediyordu

KULLANIM
  python tests/fixtures/q393_namespace_ad_politikasi/run.py
  python tests/fixtures/q393_namespace_ad_politikasi/run.py --mutasyon-<kip>   (MUTASYONLAR)
  Mutasyon exit: 1 = ilan edilen küme TAM düştü · 2 = sapma · 3 = çapa ≠ 1 / derlenmedi / sayı yok.
"""
from __future__ import annotations

import io
import os
import re
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

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
TABAN_SHA = "b0bcfac"
_GIT_KOK = Path(os.environ.get("Q393_GIT_KOK") or REPO)
_KUM = Path(tempfile.mkdtemp(prefix="q393_"))
for _p in (REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))
os.environ.pop("IX_CUSTOMER_NAMESPACES", None)

try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp = types.ModuleType("mcp")
    _srv = types.ModuleType("mcp.server")
    _fast = types.ModuleType("mcp.server.fastmcp")

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            return lambda fn: fn

    _fast.FastMCP = _FastMCP                       # type: ignore[attr-defined]
    _srv.fastmcp = _fast                           # type: ignore[attr-defined]
    _mcp.server = _srv                             # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

S: list = []
_TUT: list = []
NL = chr(10)
_SAYAC = [0]


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


def _sessiz(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        try:
            return fn(*a, **k), None
        except BaseException as exc:                  # noqa: BLE001 — istisna ÖLÇÜLÜR
            return None, exc
    finally:
        _TUT.append(atik)
        sys.stdout, sys.stderr = eski


def proje(yaml_metni: str | None) -> Path:
    """Yeni proje kökü (her biri AYRI yol: `_yaml_lite` yola göre önbelleklidir)."""
    _SAYAC[0] += 1
    d = _KUM / f"p{_SAYAC[0]}"
    d.mkdir(parents=True)
    if yaml_metni is not None:
        (d / "project.yaml").write_bytes(yaml_metni.encode("utf-8"))
    os.environ["CLAUDE_PROJECT_DIR"] = str(d)
    return d


YAML_NS = "sap_profile: s4_private\ncustomer_namespaces: [\"/NSPC/\"]\n"
YAML_YOK = "sap_profile: s4_private\n"


def _imp(ad):
    import importlib
    m, exc = _sessiz(importlib.import_module, ad)
    if m is None:
        raise SystemExit(f"[fixture-hatasi] {ad} import edilemedi: {exc!r}")
    return m


def _red(fn, *a, **k) -> bool:
    _, exc = _sessiz(fn, *a, **k)
    return exc is not None and type(exc).__name__ in ("SAPValidationError", "GuardrailViolation")


def _kabul(fn, *a, **k) -> bool:
    _, exc = _sessiz(fn, *a, **k)
    return exc is None


def _hata_metni(fn, *a, **k) -> str:
    _, exc = _sessiz(fn, *a, **k)
    return str(exc) if exc is not None else ""


AD_KORPUS = ["ZFOO", "zfoo", "Y_X", "YX", "Z", "ZFOO" + NL, "MARA", "EZSD001_L", "ezsd001_l", "EZ",
             "ESD", "/SCWM/X", "/NSPC/X", "/NSPC/", "", "ZCL_X", "ZCLX", "ZSD001_CL_X", "X_CL", "ZA-B",
             "Z/X", "Z$X", "ZFOO ", " ZFOO", "E/NSPC/X", "/NSPC/E_LOCK", "LZFG1TOP"]
TIPLER = [None, "enqu", "class", "tabl", "lock"]


# ── Y: yapılandırma ──────────────────────────────────────────────────────────
def bolum_y(A):
    r1 = proje(None)
    r1b = proje(YAML_YOK)
    r1c = proje("customer_namespaces: []\n")
    ekle("Y1 yapilandirma yok/bos -> () ve hata yok (bugunku davranis)",
         A.namespace_yapilandirmasi(r1) == ((), []) and A.namespace_yapilandirmasi(r1b) == ((), [])
         and A.namespace_yapilandirmasi(r1c) == ((), []),
         [A.namespace_yapilandirmasi(x) for x in (r1, r1b, r1c)])
    r2 = proje("customer_namespaces: [\"/NSPC/\", '/AB_1/']\n")
    r2b = proje("customer_namespaces:\n  - \"/NSPC/\"   # aciklama\n  - /AB_1/\n")
    ekle("Y2 satir ici + blok liste okunur (#391 ayristiricisi)",
         A.namespace_yapilandirmasi(r2) == (("/NSPC/", "/AB_1/"), [])
         and A.namespace_yapilandirmasi(r2b) == (("/NSPC/", "/AB_1/"), []),
         [A.namespace_yapilandirmasi(r2), A.namespace_yapilandirmasi(r2b)])
    r3 = proje("customer_namespaces: [/nspc/]\n")
    ekle("Y3 kucuk harf buyuge normalize", A.namespace_yapilandirmasi(r3) == (("/NSPC/",), []),
         A.namespace_yapilandirmasi(r3))
    r4 = proje("customer_namespaces: /NSPC/\n")
    ns4, h4 = A.namespace_yapilandirmasi(r4)
    ekle("Y4 skaler deger -> hata + namespace KAPALI", ns4 == () and h4 and "LİSTE" in h4[0], h4)
    hatali = []
    for oge in ("NSPC", "/NSPC", "/TOOLONGNS/", "#NSPC#", "/NS-X/", "//"):
        r = proje(f"customer_namespaces: [\"/OK/\", \"{oge}\"]\n")
        ns, h = A.namespace_yapilandirmasi(r)
        if ns != () or not any(oge in x for x in h) or not any("KAPALI" in x for x in h):
            hatali.append((oge, ns, h))
    ekle("Y5 gecersiz oge -> hata adla raporlanir ve GECERLI '/OK/' dahil TUM liste kapali",
         not hatali, hatali)
    r6 = proje(YAML_YOK)
    os.environ["IX_CUSTOMER_NAMESPACES"] = "/NSPC/"
    try:
        ns6 = A.namespace_yapilandirmasi(r6)
    finally:
        os.environ.pop("IX_CUSTOMER_NAMESPACES", None)
    ekle("Y6 env IX_CUSTOMER_NAMESPACES OKUNMAZ (izin listesi env ile genisletilemez)",
         ns6 == ((), []), ns6)
    r7 = proje(None)
    (r7 / "project.yaml").mkdir()          # okunamayan yol (dizin)
    ns7 = A.namespace_yapilandirmasi(r7)
    ekle("Y7 okunamayan project.yaml -> () (fail-closed)", ns7[0] == (), ns7)


# ── G: MCP guardrail ─────────────────────────────────────────────────────────
def bolum_g(G, TG):
    proje(YAML_NS)
    ns = G._is_customer_namespace
    ekle("G1 ⭐ kayitli NS kabul: tablo / sinif / kilit nesnesi (E'siz ve E'li)",
         _kabul(G.require_customer_namespace, "/NSPC/SD001_T01", object_type="tabl")
         and _kabul(G.require_customer_namespace, "/NSPC/CL_SD001_X", object_type="clas")
         and ns("/NSPC/E_LOCK", "enqu") and ns("/NSPC/LOCKX", "enqu") and ns("/nspc/x"), "")
    m2 = _hata_metni(G.require_customer_namespace, "/SCWM/X", object_type="tabl")
    ekle("G2 ⭐ kayitsiz SAP namespace'i red + mesaj kayitsizligi soyler",
         "ADR_0005_A" in m2 and "/SCWM/" in m2 and "bildirilmemi" in m2, m2[-160:])
    ekle("G3 '/NSPC/' (namespace sonrasi bos) red", not ns("/NSPC/") and not ns("/NSPC/", "enqu"), "")
    ekle("G4 satir sonlu NS adi red (\\Z)", not ns("/NSPC/X" + NL) and ns("/NSPC/X"), "")
    ekle("G5 'E/NSPC/X' (enqu) tanınmaz -> red", not ns("E/NSPC/X", "enqu"), "")
    proje("customer_namespaces: [\"/NSPC/\", \"NSPC2\"]\n")
    m6 = _hata_metni(G.require_customer_namespace, "/NSPC/X")
    ekle("G6 gecersiz yapilandirmada NS red + hata metinde (sessiz dusme yok)",
         "ADR_0005_A" in m6 and "NSPC2" in m6 and "KAPALI" in m6, m6[-200:])
    proje(YAML_NS)
    ekle("G7 reject_standard_delete ayni karar (NS kabul, /SCWM/ red, Z kabul)",
         _kabul(G.reject_standard_delete, "/NSPC/X", "tabl")
         and _red(G.reject_standard_delete, "/SCWM/X", "tabl")
         and _kabul(G.reject_standard_delete, "ZFOO", None), "")
    proje(YAML_YOK)
    fark = [(a, t, ns(a, t), TG._is_customer_namespace(a, t)) for a in AD_KORPUS for t in TIPLER
            if ns(a, t) != TG._is_customer_namespace(a, t)]
    ekle(f"G8 ⭐ KONTROL: yapilandirma yokken {len(AD_KORPUS) * len(TIPLER)} (ad x tip) karari tabanla AYNI",
         not fark, fark[:6])
    proje(YAML_NS)
    fark9 = [(a, t) for a in AD_KORPUS for t in TIPLER
             if not a.startswith("/") and ns(a, t) != TG._is_customer_namespace(a, t)]
    ekle("G9 ⭐ KONTROL: yapilandirma varken '/'suz adlarda karar tabanla AYNI", not fark9, fark9[:6])
    ekle("G10 kilit E+Z/Y korunur: EZSD001_L enqu kabul, class red",
         ns("EZSD001_L", "enqu") and not ns("EZSD001_L", "class"), "")


# ── L: sap_adt_lib ───────────────────────────────────────────────────────────
def bolum_l(L, TL):
    proje(YAML_NS)
    L._explicit_working_dir = None
    ekle("L1 validate_object_name: NS sinif kabul · kayitsiz /SCWM/ red · CL_ oneksiz red · NS program kabul",
         _kabul(L.validate_object_name, "/NSPC/CL_SD001_X", "class")
         and _red(L.validate_object_name, "/SCWM/CL_X", "class")
         and _red(L.validate_object_name, "/NSPC/CLX", "class")
         and _kabul(L.validate_object_name, "/NSPC/SD001_P01", "program")
         and _red(L.validate_object_name, "/NSPC/", "program"), "")
    ekle("L2 validate_package_name: NS paket kabul · kayitsiz red · kucuk harf red",
         _kabul(L.validate_package_name, "/NSPC/SD001")
         and _red(L.validate_package_name, "/SCWM/SD001")
         and _red(L.validate_package_name, "/nspc/sd001"), "")
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    ekle("L3 _validate_object_name: NS kabul · kucuk harf NS red · kayitsiz red",
         _kabul(c._validate_object_name, "/NSPC/SD001_T01", "Table")
         and _red(c._validate_object_name, "/nspc/sd001_t01", "Table")
         and _red(c._validate_object_name, "/SCWM/T01", "Table"), "")
    proje(YAML_YOK)
    tc = TL.SAPADTClient.__new__(TL.SAPADTClient)
    fark = []
    for a in AD_KORPUS + ["/NSPC/CL_X", "$TMP", "ZSD001_CLC", "/NSPC/SD001"]:
        for t in ("class", "program"):
            if _red(L.validate_object_name, a, t) != _red(TL.validate_object_name, a, t):
                fark.append(("obj", a, t))
        if _red(L.validate_package_name, a) != _red(TL.validate_package_name, a):
            fark.append(("pkg", a))
        if _red(c._validate_object_name, a, "Table") != _red(tc._validate_object_name, a, "Table"):
            fark.append(("cli", a))
    ekle("L4 ⭐ KONTROL: yapilandirmasiz uc dogrulayici tabanla AYNI (kabul/red)", not fark, fark[:6])


# ── F: fonksiyon grubu ──────────────────────────────────────────────────────
def _meta(ref_type, ref_name, ref_uri, sayac="1", ikinci=""):
    return ('<?xml version="1.0" encoding="utf-8"?><include:abapInclude include:contextRefCount="'
            + sayac + '" adtcore:name="X" adtcore:type="PROG/I" '
            'xmlns:include="http://www.sap.com/adt/programs/includes" '
            'xmlns:adtcore="http://www.sap.com/adt/core">'
            '<include:contextRef adtcore:uri="' + ref_uri + '" adtcore:type="' + ref_type
            + '" adtcore:name="' + ref_name + '"/>' + ikinci + '</include:abapInclude>')


def bolum_f(A, O, ATOM):
    proje(YAML_NS)
    ekle("F1 onek/ana program: ZFG1->LZFG1/SAPLZFG1 · /NSPC/FG1->/NSPC/LFG1 /NSPC/SAPLFG1",
         A.fugr_include_oneki("ZFG1") == "LZFG1" and A.fugr_ana_program("ZFG1") == "SAPLZFG1"
         and A.fugr_include_oneki("/nspc/fg1") == "/NSPC/LFG1"
         and A.fugr_ana_program("/NSPC/FG1") == "/NSPC/SAPLFG1", "")
    h = O.fugr_include_ad_alani_hatasi
    ekle("F2 ad alani: NS grup + /NSPC/LFG1TOP kabul · LFG1TOP red · Z grup ayni · /SCWM/ grup red",
         h("/NSPC/FG1", "/NSPC/LFG1TOP") is None and h("/NSPC/FG1", "LFG1TOP")
         and h("ZFG1", "LZFG1TOP") is None and h("ZFG1", "LZFG2TOP") and h("/SCWM/FG1", "/SCWM/LFG1TOP"),
         [h("/NSPC/FG1", "/NSPC/LFG1TOP"), h("/NSPC/FG1", "LFG1TOP")])
    xml_canli = (BURASI / "canli" / "ns_progs_include_meta.xml").read_text(encoding="utf-8")
    k = O.fugr_include_grup_kaniti
    ok3, s3 = k(xml_canli, "/NSPC/FG1")
    ok3b, _ = k(xml_canli, " /nspc/fg1 ")
    ekle("F3 ⭐ NS grup kaniti: canli bicim contextRef FUGR/F name==grup -> True", ok3 and ok3b, s3)
    z_ff = _meta("FUGR/F", "ZFG1", "/sap/bc/adt/functions/groups/zfg1/source/main")
    z_fi = _meta("FUGR/I", "SAPLZFG1", "/sap/bc/adt/functions/groups/zfg1/source/main")
    ekle("F4 ⭐ Z grupta FUGR/F KANIT DEGIL (eski kural), FUGR/I SAPLZFG1 kanit",
         k(z_ff, "ZFG1")[0] is False and k(z_fi, "ZFG1")[0] is True, [k(z_ff, "ZFG1"), k(z_fi, "ZFG1")])
    proje(YAML_YOK)
    ekle("F5 kayitsiz NS grupta FUGR/F red (musteri_adi_mi sarti)", k(xml_canli, "/NSPC/FG1")[0] is False,
         k(xml_canli, "/NSPC/FG1"))
    proje(YAML_NS)
    ekle("F6 NS grupta baska grup adi red", k(xml_canli, "/NSPC/FG2")[0] is False, "")
    iki = _meta("FUGR/F", "/NSPC/FG1", "/sap/bc/adt/functions/groups/%2fnspc%2ffg1/source/main", sayac="2")
    ns_fi = _meta("FUGR/I", "/NSPC/SAPLFG1", "/sap/bc/adt/functions/groups/%2fnspc%2ffg1/source/main")
    ekle("F7 NS grupta contextRefCount=2 red; FUGR/I /NSPC/SAPLFG1 (ana program bicimi) kabul",
         k(iki, "/NSPC/FG1")[0] is False and k(ns_fi, "/NSPC/FG1")[0] is True, "")
    g = ATOM._fugr_include_guardrail
    ekle("F8 MCP _fugr_include_guardrail: NS grup + /NSPC/LFG1TOP kabul · LFG1TOP red · Z ayni",
         _kabul(g, "/NSPC/LFG1TOP", "fugr_include", "/NSPC/FG1")
         and _red(g, "LFG1TOP", "fugr_include", "/NSPC/FG1")
         and _kabul(g, "LZFG1TOP", "fugr_include", "ZFG1")
         and _red(g, "LZFG2TOP", "fugr_include", "ZFG1"), "")


# ── S: sap_set_object_description kapısı (ağsız: kapı geçerse URL adımında durdurulur) ──
class _Gecti(Exception):
    pass


def bolum_s(SD):
    def kos(ad, tip="class"):
        def dur(*a, **k):
            raise _Gecti()
        eski_url, eski_argv = SD._main_url, sys.argv
        SD._main_url = dur
        sys.argv = ["sap_set_object_description.py", ad, "--type", tip, "--desc", "x", "--dry-run"]
        try:
            r, exc = _sessiz(SD.main)
        finally:
            SD._main_url, sys.argv = eski_url, eski_argv
        return "GECTI" if isinstance(exc, _Gecti) else r
    proje(YAML_NS)
    ekle("S1 NS adi kapidan gecer", kos("/NSPC/CL_X") == "GECTI", kos("/NSPC/CL_X"))
    ekle("S2 kayitsiz NS rc 2", kos("/SCWM/CL_X") == 2, kos("/SCWM/CL_X"))
    ekle("S3 Z adi gecer, standart ad rc 2", kos("ZCL_X") == "GECTI" and kos("CL_X") == 2, "")


# ── K: taban (ayırt edicilik) ───────────────────────────────────────────────
def _taban_modul(yol, ad):
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:{yol}"], capture_output=True)
    if g.returncode != 0:
        raise RuntimeError(f"taban okunamadi {yol}: {g.stderr.decode('utf-8', 'replace')[:120]}")
    mod = types.ModuleType(ad)
    mod.__file__ = str(REPO / yol)
    _, exc = _sessiz(lambda: exec(compile(g.stdout.decode("utf-8"), mod.__file__, "exec"), mod.__dict__))
    if exc is not None:
        raise RuntimeError(f"taban derlenemedi {yol}: {exc!r}")
    return mod


def bolum_k(TG, TO, TL):
    xml_canli = (BURASI / "canli" / "ns_progs_include_meta.xml").read_text(encoding="utf-8")
    proje(YAML_NS)
    ekle("K1 ⭐ taban guardrail '/NSPC/X'i yapilandirma VARKEN de reddediyordu",
         TG._is_customer_namespace("/NSPC/X", "tabl") is False, "")
    ekle("K2 ⭐ taban grup kaniti NS canli govdesini reddediyordu", TO.fugr_include_grup_kaniti(
        xml_canli, "/NSPC/FG1")[0] is False, "")
    ekle("K3 ⭐ taban validate_object_name/package NS'i reddediyordu",
         _red(TL.validate_object_name, "/NSPC/CL_SD001_X", "class") and _red(TL.validate_package_name, "/NSPC/SD001"), "")


def main() -> int:
    A = _imp("utils.ad_politikasi")
    G = _imp("mcp_servers.sap_adt.guardrails")
    L = _imp("sap_adt_lib")
    O = _imp("object_types")
    ATOM = _imp("mcp_servers.sap_adt.tools.atom")
    SD = _imp("sap_set_object_description")
    try:
        TG = _taban_modul("mcp_servers/sap_adt/guardrails.py", "guardrails_taban")
        TO = _taban_modul("scripts/object_types.py", "object_types_taban")
        TL = _taban_modul("scripts/sap_adt_lib.py", "sap_adt_lib_taban")
    except Exception as exc:                           # noqa: BLE001
        print(f"[fixture-hatasi] taban kurulamadi: {exc}")
        return 3
    for fn, a in ((bolum_y, (A,)), (bolum_g, (G, TG)), (bolum_l, (L, TL)), (bolum_f, (A, O, ATOM)),
                  (bolum_s, (SD,)), (bolum_k, (TG, TO, TL))):
        try:
            fn(*a)
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle(f"[BOLUM-COKTU] {fn.__name__}", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_KUM, ignore_errors=True)
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYONLAR: kip -> (dosya, çapa, yerine, düşmesi İLAN edilen vektör kümesi)
_AP = "scripts/utils/ad_politikasi.py"
Z = chr(92) + "Z"
MUTASYONLAR = {
    "--mutasyon-ns-kapali": (_AP, "    if ns not in kayitli:\n        return False\n",
                             "    return False\n",
                             {"G1", "G4", "G7", "L1", "L2", "L3", "F2", "F3", "F8", "S1"}),
    "--mutasyon-ns-dolar": (_AP, 'r"[A-Z0-9_]+' + Z + '", ad, re.IGNORECASE)',
                            'r"[A-Z0-9_]+$", ad, re.IGNORECASE)', {"G4"}),
    "--mutasyon-ns-bos-govde": (_AP, 'r"[A-Z0-9_]+' + Z + '", ad, re.IGNORECASE)',
                                'r"[A-Z0-9_]*' + Z + '", ad, re.IGNORECASE)', {"G3", "L1"}),
    "--mutasyon-yapi-kismi": (_AP, "    if hatalar:\n        return (), hatalar + [",
                              "    if False:\n        return (), hatalar + [", {"Y5", "G6"}),
    "--mutasyon-env-okunur": (_AP, "        ham = _yaml_lite(str(yol)).get(ANAHTAR)\n",
                              "        _e = __import__('os').environ.get('IX_' + ANAHTAR.upper())\n"
                              "        ham = _e.split(',') if _e else _yaml_lite(str(yol)).get(ANAHTAR)\n",
                              {"Y6"}),
    "--mutasyon-kayitsiz-kabul": (_AP, "    if ns not in kayitli:\n        return False\n", "",
                                  {"G2", "G6", "G7", "G8", "L1", "L2", "L3", "L4", "F2", "F5", "S2"}),
    "--mutasyon-ff-z-grupta": ("scripts/object_types.py",
                               "    if _ap.ad_namespace(g) and _ap.musteri_adi_mi(g):\n",
                               "    if True:\n", {"F4", "F5"}),
    "--mutasyon-ff-kayit-sarti": ("scripts/object_types.py",
                                  "    if _ap.ad_namespace(g) and _ap.musteri_adi_mi(g):\n",
                                  "    if _ap.ad_namespace(g):\n", {"F5"}),
    "--mutasyon-onek-eski": (_AP, '    return ns + "L" + g[len(ns):] if ns else "L" + g\n',
                             '    return "L" + g\n', {"F1", "F2", "F8"}),
    "--mutasyon-guardrail-eski": ("mcp_servers/sap_adt/guardrails.py",
                                  "    return _ad.musteri_adi_mi(name, object_type)\n",
                                  "    return bool(re.match(r'^[ZY][A-Z0-9_]*" + Z + "', name or '', re.I)) or bool("
                                  "object_type and object_type.lower() in _LOCK_TYPES and "
                                  "re.match(r'^E[ZY][A-Z0-9_]*" + Z + "', name or '', re.I))\n",
                                  {"G1", "G4", "G7", "F8"}),
    "--mutasyon-paket-ns-yok": ("scripts/sap_adt_lib.py",
                                "    if package_upper.startswith('/'):\n",
                                "    if False:\n", {"L2"}),
    "--mutasyon-kilit-zy-yok": (_AP, "    if object_type and object_type.lower() in KILIT_TIPLERI and _KILIT_ZY.match(ad):\n",
                                "    if False:\n", {"G8", "G9", "G10"}),
    "--mutasyon-harf-duyarli": (_AP, '_ZY = re.compile(r"^[ZY][A-Z0-9_]*' + Z + '", re.IGNORECASE)',
                                '_ZY = re.compile(r"^[ZY][A-Z0-9_]*' + Z + '")', {"G8", "G9"}),
}
KIPLER = sorted(MUTASYONLAR)


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="q393_kum_"))
    try:
        for alt in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / alt, kok / alt,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kok / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        env = dict(os.environ)
        env["Q393_GIT_KOK"] = str(_GIT_KOK)
        r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, cwd=str(kok), env=env)
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    sys.exit(main())

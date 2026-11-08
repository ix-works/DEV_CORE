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

import ast
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


def proje(yaml_metni: str | None, baglanti: bool = True) -> Path:
    """Yeni proje kökü (her biri AYRI yol: `_yaml_lite` yola göre önbelleklidir).
    `baglanti=True`: dizine sahte `.conn_adt` yazılır (bug-gate-2 F3: bağlantı dosyası
    çözülemeyen süreçte namespace kabulü KAPALI ⇒ kabul vektörleri gerçek bir bağlantı ister)."""
    _SAYAC[0] += 1
    d = _KUM / f"p{_SAYAC[0]}"
    d.mkdir(parents=True)
    if yaml_metni is not None:
        (d / "project.yaml").write_bytes(yaml_metni.encode("utf-8"))
    if baglanti:
        _sahte_baglanti(d)
    os.environ["CLAUDE_PROJECT_DIR"] = str(d)
    _baglanti(d)
    return d


def nsy(A, r):
    """`namespace_yapilandirmasi(r)` — bağlantıyı önce r'ye sabitler (açık kök = bağlantı dizini)."""
    _baglanti(r)
    return A.namespace_yapilandirmasi(r)


def _baglanti(d, explicit=None):
    """sap_adt_lib'in ÇÖZDÜĞÜ bağlantıyı sabitle (P2a/F2: namespace kökü = bağlantı dizini).
    Ortamın kendi `.conn_adt`'si (worktree provizyonu) ölçüme SIZMASIN diye her projede yeniden."""
    lib = sys.modules.get("sap_adt_lib")
    if lib is not None:
        lib._explicit_working_dir = Path(explicit).resolve() if explicit else None
        lib.conn_path = Path(d) / ".conn_adt"


def _sahte_baglanti(d):
    (Path(d) / ".conn_adt").write_bytes(b"ADT_SAP_URL=https://sahte.invalid\nADT_SAP_CLIENT=000\n")


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
         nsy(A, r1) == ((), []) and nsy(A, r1b) == ((), []) and nsy(A, r1c) == ((), []),
         [nsy(A, x) for x in (r1, r1b, r1c)])
    r2 = proje("customer_namespaces: [\"/NSPC/\", '/AB_1/']\n")
    r2b = proje("customer_namespaces:\n  - \"/NSPC/\"   # aciklama\n  - /AB_1/\n")
    ekle("Y2 satir ici + blok liste okunur (#391 ayristiricisi)",
         nsy(A, r2) == (("/NSPC/", "/AB_1/"), []) and nsy(A, r2b) == (("/NSPC/", "/AB_1/"), []),
         [nsy(A, r2), nsy(A, r2b)])
    r3 = proje("customer_namespaces: [/nspc/]\n")
    ekle("Y3 kucuk harf buyuge normalize", A.namespace_yapilandirmasi(r3) == (("/NSPC/",), []),
         A.namespace_yapilandirmasi(r3))
    r4 = proje("customer_namespaces: /NSPC/\n")
    ns4, h4 = A.namespace_yapilandirmasi(r4)
    ekle("Y4 skaler deger -> hata + namespace KAPALI", ns4 == () and h4 and "LİSTE" in h4[0], h4)
    hatali = []
    for oge in ("NSPC", "/NSPC", "/TOOLONGNS/", "#NSPC#", "/NS-X/", "//"):
        r = proje(f"customer_namespaces: [\"/OKNS/\", \"{oge}\"]\n")
        ns, h = A.namespace_yapilandirmasi(r)
        if ns != () or not any(oge in x for x in h) or not any("KAPALI" in x for x in h):
            hatali.append((oge, ns, h))
    ekle("Y5 gecersiz oge -> hata adla raporlanir ve GECERLI '/OKNS/' dahil TUM liste kapali",
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


# ── R: namespace kökü = BAĞLANTI dizini (bug-gate F2) + yapılandırma sertleştirmeleri ──
def bolum_r(A, G, L, O):
    xml_canli = (BURASI / "canli" / "ns_progs_include_meta.xml").read_text(encoding="utf-8")
    # R1 (i): CLAUDE_PROJECT_DIR=X (.conn_adt YOK, liste /SCWM/ + /NSPC/) · bağlantı cwd P'den
    x = proje("customer_namespaces: [\"/SCWM/\", \"/NSPC/\"]\n", baglanti=False)
    pdir = _KUM / f"p{_SAYAC[0]}_baglanti"
    pdir.mkdir()
    (pdir / "project.yaml").write_bytes(YAML_YOK.encode("utf-8"))
    _sahte_baglanti(pdir)
    eski_cwd = os.getcwd()
    try:
        os.chdir(pdir)
        cozulen = L.find_conn_file()                  # GERÇEK çözücü: X'te yok → cwd P
    finally:
        os.chdir(eski_cwd)
    L.conn_path = cozulen
    on_kosul = Path(cozulen).resolve() == (pdir / ".conn_adt").resolve()
    ekle("R1 ⭐ CLAUDE_PROJECT_DIR=<.conn_adt'siz, listeli dizin> + baglanti baska projede -> "
         "liste BAGLANTININ projesinden: /SCWM/ ve /NSPC/ RED",
         on_kosul and not G._is_customer_namespace("/SCWM/CL_X", "class")
         and not G._is_customer_namespace("/NSPC/X", "tabl")
         and _red(G.require_customer_namespace, "/SCWM/CL_X", object_type="clas"),
         [str(cozulen), G._is_customer_namespace("/SCWM/CL_X", "class")])
    # R2 (ii): CLAUDE_PROJECT_DIR=A (liste /NSPC/) · --cwd B (bağlantı B, liste YOK)
    a = proje(YAML_NS)
    b = _KUM / f"p{_SAYAC[0]}_cwd"
    b.mkdir()
    (b / "project.yaml").write_bytes(YAML_YOK.encode("utf-8"))
    _sahte_baglanti(b)
    _baglanti(b, explicit=b)
    ekle("R2 ⭐ --cwd B (baglanti B, liste yok) + CLAUDE_PROJECT_DIR=A (liste /NSPC/) -> "
         "guardrail / validate_object_name / grup kaniti B'yi okur: RED",
         not G._is_customer_namespace("/NSPC/X", "tabl")
         and _red(L.validate_object_name, "/NSPC/CL_SD001_X", "class")
         and O.fugr_include_grup_kaniti(xml_canli, "/NSPC/FG1")[0] is False,
         [G._is_customer_namespace("/NSPC/X", "tabl"), O.fugr_include_grup_kaniti(xml_canli, "/NSPC/FG1")])
    (b / "project.yaml").write_bytes(YAML_NS.encode("utf-8"))
    os.utime(b / "project.yaml", ns=(1, 2_000_000_000_000_000_000))
    ekle("R3 KONTROL: B'nin listesi /NSPC/ olunca ayni uc kabul (okunan gercekten B)",
         G._is_customer_namespace("/NSPC/X", "tabl")
         and _kabul(L.validate_object_name, "/NSPC/CL_SD001_X", "class")
         and O.fugr_include_grup_kaniti(xml_canli, "/NSPC/FG1")[0] is True, "")
    # R4: açık root bağlantı dizininden farklı -> kabul KAPALI + gerekçe
    ns4, h4 = A.namespace_yapilandirmasi(a)
    ekle("R4 ⭐ acik root (A) baglanti dizininden (B) farkli -> namespace KAPALI + hata metni",
         ns4 == () and h4 and "farkl" in h4[0] and not A.musteri_adi_mi("/NSPC/X", root=a)
         and "farkl" in A.red_gerekcesi("/NSPC/X", root=a), [ns4, h4])
    _baglanti(a)
    # R5 (F5): aynı süreçte dosya değişince yeniden okunur
    r5 = proje(YAML_NS)
    once = A.musteri_adi_mi("/NSPC/X")
    (r5 / "project.yaml").write_bytes(YAML_YOK.encode("utf-8"))
    os.utime(r5 / "project.yaml", ns=(1, 2_000_000_000_000_000_000))
    ekle("R5 ⭐ namespace silinince ayni surecte RED (mtime anahtarli onbellek; /mcp beklemez)",
         once is True and A.musteri_adi_mi("/NSPC/X") is False, [once])
    r6 = proje("customer_namespaces: [\"/NSPC/\"]\nsap_profile: s4_private\ncustomer_namespaces: [\"/SCWM/\"]\n")
    ns6, h6 = A.namespace_yapilandirmasi(r6)
    ekle("R6 mukerrer customer_namespaces anahtari -> hata + KAPALI", ns6 == () and h6 and "2 kez" in h6[0],
         [ns6, h6])
    r7 = proje("customer_namespaces: [\"/OKNS/\", \"/___/\"]\n")
    ns7, h7 = A.namespace_yapilandirmasi(r7)
    r7b = proje("customer_namespaces: [\"/A__/\"]\n")
    ekle("R7 '/___/' (harfsiz/rakamsiz) oge RED + liste kapali · '/A__/' gecerli",
         ns7 == () and any("/___/" in x for x in h7) and A.namespace_yapilandirmasi(r7b) == (("/A__/",), []),
         [ns7, h7])
    # R7c — DEV_CORE #402 tek gramer {3,8}: 2 karakterli oge RED + TUM liste kapali (gorunur hata);
    # KONTROL: 3 karakterli '/NSP/' kabul (SAP: namespace '/' dahil 5-10 · abaplint {3,8} · TRNSPACE)
    r7c = proje("customer_namespaces: [\"/NSP/\", \"/AB/\"]\n")
    ns7c, h7c = A.namespace_yapilandirmasi(r7c)
    r7d = proje("customer_namespaces: [\"/NSP/\"]\n")
    ekle("R7c 2 karakterli '/AB/' oge RED + liste kapali · KONTROL '/NSP/' gecerli + /NSP/X musteri",
         ns7c == () and any("/AB/" in x for x in h7c) and any("KAPALI" in x for x in h7c)
         and A.namespace_yapilandirmasi(r7d) == (("/NSP/",), []) and A.musteri_adi_mi("/NSP/X")
         and not A.musteri_adi_mi("/AB/X", namespaces=["/AB/"]),
         [ns7c, h7c])
    r8 = proje("customer_namespaces: [\"/OKNS/\", \"/\u017fPC/\"]\n")
    ns8, h8 = A.namespace_yapilandirmasi(r8)
    ekle("R8 ASCII olmayan oge ('/\u017fPC/' -> upper '/SPC/') RED + liste kapali", ns8 == () and h8, [ns8, h8])
    proje(YAML_NS)
    ekle("R9 namespace govdesinde Unicode harf RED ('\u0131' '\u017f' '\u212a' '\u0130'), ASCII kabul",
         not any(A.musteri_adi_mi("/NSPC/X" + ch) for ch in ("\u0131", "\u017f", "\u212a", "\u0130"))
         and A.musteri_adi_mi("/NSPC/XK") and not G._is_customer_namespace("/NSPC/X\u0131", "tabl"), "")
    # R10 (F3): tam olarak TEK FUGR/* baglam
    iki_ff = _meta("FUGR/F", "/NSPC/FG1", "/sap/bc/adt/functions/groups/%2fnspc%2ffg1/source/main",
                   ikinci='<include:contextRef adtcore:uri="/sap/bc/adt/functions/groups/%2fnspc%2ffg2/'
                          'source/main" adtcore:type="FUGR/F" adtcore:name="/NSPC/FG2"/>')
    karisik = _meta("FUGR/I", "/NSPC/SAPLFG1", "/sap/bc/adt/functions/groups/%2fnspc%2ffg1/source/main",
                    ikinci='<include:contextRef adtcore:uri="/sap/bc/adt/functions/groups/%2fnspc%2ffg2/'
                           'source/main" adtcore:type="FUGR/F" adtcore:name="/NSPC/FG2"/>')
    z_karisik = _meta("FUGR/I", "SAPLZFG1", "/sap/bc/adt/functions/groups/zfg1/source/main",
                      ikinci='<include:contextRef adtcore:uri="/sap/bc/adt/functions/groups/zfg1/'
                             'source/main" adtcore:type="FUGR/F" adtcore:name="ZFG1"/>')
    k = O.fugr_include_grup_kaniti
    ekle("R10 ⭐ birden cok FUGR/* contextRef (iki FUGR/F · FUGR/I+FUGR/F, Z dahil) -> RED (iki grup "
         "birden kanitlanmaz)",
         k(iki_ff, "/NSPC/FG1")[0] is False and k(iki_ff, "/NSPC/FG2")[0] is False
         and k(karisik, "/NSPC/FG1")[0] is False and k(karisik, "/NSPC/FG2")[0] is False
         and k(z_karisik, "ZFG1")[0] is False,
         [k(iki_ff, "/NSPC/FG1"), k(karisik, "/NSPC/FG2"), k(z_karisik, "ZFG1")])
    # R11 (bug-gate-2 F3): .conn_adt YOK + kimlik env'den (ADT_SAP_URL) + CLAUDE_PROJECT_DIR=<listeli dizin>
    x11 = proje("customer_namespaces: [\"/SCWM/\", \"/NSPC/\"]\n", baglanti=False)
    _baglanti(x11, explicit=x11)
    L.conn_path = L.find_conn_file()                  # GERÇEK çözücü: açık dizin, dosya YOK
    on_kosul11 = not Path(L.conn_path).exists() and os.environ.get("CLAUDE_PROJECT_DIR") == str(x11)
    eski_url = os.environ.get("ADT_SAP_URL")
    os.environ["ADT_SAP_URL"] = "https://sahte.invalid"
    try:
        ns11, h11 = A.namespace_yapilandirmasi()
        sonuc11 = (A.musteri_adi_mi("/SCWM/X_TABLE"), A.musteri_adi_mi("/NSPC/X"),
                   G._is_customer_namespace("/SCWM/X_TABLE", "tabl"), A.musteri_adi_mi("ZSD001_T01"),
                   A.musteri_adi_mi("EZSD001_L", "enqu"), G._is_customer_namespace("ZSD001_T01", "tabl"))
        gerekce11 = A.red_gerekcesi("/SCWM/X_TABLE")
    finally:
        if eski_url is None:
            os.environ.pop("ADT_SAP_URL", None)
        else:
            os.environ["ADT_SAP_URL"] = eski_url
    ekle("R11 ⭐ .conn_adt cozulemedi + env ADT_SAP_URL + CLAUDE_PROJECT_DIR=<listesi /SCWM/ /NSPC/> -> "
         "namespace KAPALI (/SCWM/ /NSPC/ RED, gerekce 'cozulemedi') · Z/Y + EZ kilit AYNEN kabul",
         on_kosul11 and ns11 == () and h11 and "çözülemedi" in h11[0]
         and sonuc11 == (False, False, False, True, True, True) and "çözülemedi" in gerekce11,
         [on_kosul11, ns11, h11, sonuc11, gerekce11])
    _baglanti(x11)


# ── U: ADT URL yol parçası (Parti 2a) ───────────────────────────────────────
_URL_ISARET = ("/sap/bc/adt", "_BASE}", "uri=", "_path}", "_url}")
_ICF_SEGMENT = "/sap/bc/ui5_ui5/"     # BSP ICF yolu: ayrı sınıf, changelog'da bilinen sınır (kapsam dışı)


def _url_dosyalari():
    """KODDAN türetilir (bug-gate-2 F2): `scripts/` + `mcp_servers/` altında `/sap/bc/adt/`
    geçen her .py (attic · tests · __pycache__ hariç). Elle liste yazılmaz — yeni bir URL
    dosyası eklendiğinde tarama ona KENDİLİĞİNDEN uzanır. (Seçim tablosu `run_fixture_tests`
    P2a satırları elle tutulur; kaçan dosya yalnız seçili koşumda atlanır, tam süit/CI yakalar.)"""
    out = []
    for kok in ("scripts", "mcp_servers"):
        for p in sorted((REPO / kok).rglob("*.py")):
            rel = p.relative_to(REPO).as_posix()
            if any(f"/{x}/" in f"/{rel}" for x in ("attic", "tests", "__pycache__")):
                continue
            if "/sap/bc/adt/" in p.read_bytes().decode("utf-8", "replace"):
                out.append(rel)
    return out


def _lower_cagrisi(c) -> bool:
    return (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "lower"
            and not c.args)


def _url_kalintilari(dosyalar):
    """AST: URL f-string'inde `{X.lower()}` ya da AYNI kapsamda `ad = X.lower()` atanmış bir adın
    `{ad}` kullanımı (ad listesi elle yazılmaz — kapsam başına türetilir). ICF yolu hariç."""
    kalan = []
    for yol in dosyalar:
        ham = (REPO / yol).read_bytes().decode("utf-8")
        satirlar = ham.splitlines(keepends=True)
        agac = ast.parse(ham)
        kapsamlar = [agac] + [n for n in ast.walk(agac) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for kap in kapsamlar:
            icerik = [n for st in kap.body for n in ast.walk(st)]
            lower_adlar = {t.id for n in icerik if isinstance(n, ast.Assign) and _lower_cagrisi(n.value)
                           for t in n.targets if isinstance(t, ast.Name)}
            for n in icerik:
                if not isinstance(n, ast.JoinedStr):
                    continue
                seg = "".join(satirlar[n.lineno - 1:n.end_lineno])
                if not any(i in seg for i in _URL_ISARET) or _ICF_SEGMENT in seg:
                    continue
                for v in n.values:
                    c = v.value if isinstance(v, ast.FormattedValue) else None
                    if _lower_cagrisi(c) or (isinstance(c, ast.Name) and c.id in lower_adlar):
                        kalan.append(f"{yol}:{c.lineno}")
    return sorted(set(kalan))


def _kurucular(m):
    """(etiket, çağrı) — modül `m`'nin saf XML/URL kurucuları; `ad`/`pkg` parametreli."""
    yield "dtel", lambda ad, pkg: m["populate_dataelements"].build_xml(
        ad, "aciklama", pkg, "SAP_USER_A", "domain", "ZD", "CHAR", 10, 0, "k", "o", "u", "b")
    yield "doma", lambda ad, pkg: m["populate_domains"].build_xml(ad, "aciklama", pkg, "SAP_USER_A", "CHAR", 10, 0, [])
    yield "enqu", lambda ad, pkg: m["populate_lock_objects"].build_xml(ad, "aciklama", pkg, "ZT", "E", False, ["F1"])
    yield "msag", lambda ad, pkg: m["populate_message_class"].build_xml(ad, "aciklama", pkg, "SAP_USER_A", [])
    yield "tabl", lambda ad, pkg: m["populate_tables"].build_xml(ad, "aciklama", pkg, "TR", "")
    yield "ddls", lambda ad, pkg: m["populate_cds_views"].build_shell_xml(ad, "aciklama", pkg)
    yield "srvd", lambda ad, pkg: m["create_rap_service"].srvd_shell_xml(ad, "aciklama", pkg)
    yield "srvb", lambda ad, pkg: m["create_rap_service"].srvb_xml(ad, ad + "_D", pkg)
    yield "publ", lambda ad, pkg: m["create_rap_service"].publish_xml(ad)
    yield "bdef", lambda ad, pkg: m["create_rap_service"].bdef_shell_xml(ad, "aciklama", pkg)
    yield "bcls", lambda ad, pkg: m["create_rap_service"].bclass_shell_xml(ad, "aciklama", pkg)


def bolum_u(A, O, TO, KUR, TKUR):
    seg = A.url_segmenti
    z = [a for a in AD_KORPUS + ["ZSD001_T01", "ZCL_SD001_ORDER", "Y1_X", "lzfg1top", "SAPLZFG1"]
         if a and re.fullmatch(r"[A-Za-z0-9_]+", a)]
    ekle(f"U1 ⭐ KONTROL: {len(z)} Z/Y/ad-karakterli adda url_segmenti == eski .lower() (bayt bayt)",
         all(seg(a) == a.lower() for a in z), [(a, seg(a)) for a in z if seg(a) != a.lower()][:4])
    ekle("U2 NS ad kodlanir: /NSPC/X -> %2Fnspc%2Fx · /nspc/cl_x -> %2Fnspc%2Fcl_x",
         seg("/NSPC/X") == "%2Fnspc%2Fx" and seg("/nspc/cl_x") == "%2Fnspc%2Fcl_x", seg("/NSPC/X"))
    cift = [seg("%2fnspc%2fx"), seg("%2Fnspc%2Fx"), seg(seg("/NSPC/X")), seg(seg(seg("/NSPC/X")))]
    ekle("U3 ⭐ zaten kodlanmis ad CIFT kodlanmaz (%252f YOK, idempotent)",
         all(c == "%2Fnspc%2Fx" for c in cift) and not any("%25" in c for c in cift), cift)
    ekle("U4 url_parcasindan_ad ters donusum: %2fnspc%2ffg1 / %2Fnspc%2Ffg1 -> /NSPC/FG1 · zfg1 -> ZFG1",
         A.url_parcasindan_ad("%2fnspc%2ffg1") == "/NSPC/FG1" == A.url_parcasindan_ad(seg("/NSPC/FG1"))
         and A.url_parcasindan_ad("zfg1") == "ZFG1", "")
    ns_meta = _meta("FUGR/F", "/NSPC/FG1", "/sap/bc/adt/functions/groups/%2fnspc%2ffg1/source/main")
    z_meta = _meta("FUGR/I", "SAPLZFG1", "/sap/bc/adt/functions/groups/zfg1/source/main")
    ekle("U5 ⭐ include_fugr_baglami NS grubu COZULMUS doner (/NSPC/FG1) · Z grup tabanla AYNI",
         O.include_fugr_baglami(ns_meta) == "/NSPC/FG1"
         and O.include_fugr_baglami(z_meta) == TO.include_fugr_baglami(z_meta) == "ZFG1",
         [O.include_fugr_baglami(ns_meta), O.include_fugr_baglami(z_meta)])
    fark, ns_hata = [], []
    for (et, fn), (_, tfn) in zip(_kurucular(KUR), _kurucular(TKUR)):
        yeni, e1 = _sessiz(fn, "ZSD001_X", "ZSD001_PKG")
        eski, e2 = _sessiz(tfn, "ZSD001_X", "ZSD001_PKG")
        if e1 or e2 or yeni != eski:
            fark.append((et, repr(e1)[:60], repr(e2)[:60]))
        nsx, e3 = _sessiz(fn, "/NSPC/X", "/NSPC/SD001")
        urls = [t for t in re.split("[\"' <>]", nsx or "") if "/sap/bc/adt/" in t]
        if (e3 or not urls or not any("%2fnspc%2f" in u.lower() for u in urls)
                or any("/nspc/" in u.lower() for u in urls) or any("%25" in u for u in urls)):
            ns_hata.append((et, repr(e3)[:60], urls[:2]))
    ekle("U6 ⭐ KONTROL: 11 XML/URL kurucusu Z adinda tabanla BAYT BAYT AYNI", not fark, fark[:4])
    ekle("U7 ⭐ ayni 11 kurucu NS adinda %2F kodlu (ham '/nspc/' yol parcasi YOK, %25 YOK)",
         not ns_hata, ns_hata[:4])
    dosyalar = _url_dosyalari()
    kalan = _url_kalintilari(dosyalar)
    ekle(f"U8 ⭐ koddan turetilen {len(dosyalar)} URL dosyasinda (/sap/bc/adt/ gecen .py) URL f-string'inde "
         f"`.lower()` / lower'lanmis ad kalintisi YOK (AST, ICF haric)",
         len(dosyalar) >= 30 and "scripts/push_bo_atomic.py" in dosyalar and not kalan,
         [len(dosyalar), kalan[:6]])


def bolum_d(PD, CD, TPD):
    sutun = "name,type_kind,type_name,datatype,length,decimals,description,short,medium,long,heading\n"
    def csv(ad):
        y = _KUM / f"dtel_{_SAYAC[0]}.csv"
        y.write_bytes((sutun + f"{ad},domain,ZD,CHAR,10,0,aciklama,k,o,u,b\n").encode("utf-8"))
        return y
    proje(YAML_NS)
    yol = csv("/NSPC/SD001_D01")
    rows, exc = _sessiz(PD.load_dataelements_from_csv, yol)
    b1 = []
    CD._dosyayi_denetle(yol, b1)
    ekle("D1 ⭐ DTEL CSV: kayitli NS adi populate + validator'dan GECER",
         exc is None and rows and rows[0]["name"] == "/NSPC/SD001_D01"
         and not [x for x in b1 if "R1" in x[2]], [repr(exc)[:120], b1[:2]])
    proje(YAML_YOK)
    yol = csv("/NSPC/SD001_D01")
    _, exc2 = _sessiz(PD.load_dataelements_from_csv, yol)
    b2 = []
    CD._dosyayi_denetle(yol, b2)
    ekle("D2 kayitsiz NS adi populate RED (gerekce metinde) + validator R1",
         exc2 is not None and "bildirilmemi" in str(exc2) and [x for x in b2 if "R1" in x[2]],
         [repr(exc2)[:160], b2[:2]])
    yol = csv("MARA_X")
    _, exc3 = _sessiz(PD.load_dataelements_from_csv, yol)
    _, exc4 = _sessiz(TPD.load_dataelements_from_csv, yol)
    yol5 = csv("ZSD001_D01")
    r5, exc5 = _sessiz(PD.load_dataelements_from_csv, yol5)
    ekle("D3 KONTROL: standart ad iki surumde de RED · Z adi gecer",
         exc3 is not None and exc4 is not None and exc5 is None and r5, [repr(exc5)[:100]])


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


def _taban_disi_modul(yol, ad):
    """Paket olmayan dizindeki betiği (validators/) dosyadan yükle — GÜNCEL sürüm."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(ad, str(REPO / yol))
    mod = importlib.util.module_from_spec(spec)
    _, exc = _sessiz(spec.loader.exec_module, mod)
    if exc is not None:
        raise SystemExit(f"[fixture-hatasi] {yol} yuklenemedi: {exc!r}")
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
    ns_meta = _meta("FUGR/F", "/NSPC/FG1", "/sap/bc/adt/functions/groups/%2fnspc%2ffg1/source/main")
    ekle("K4 ⭐ taban include_fugr_baglami NS grubunu KODLU donduruyordu (%2FNSPC%2FFG1)",
         TO.include_fugr_baglami(ns_meta) == "%2FNSPC%2FFG1", TO.include_fugr_baglami(ns_meta))


def main() -> int:
    A = _imp("utils.ad_politikasi")
    G = _imp("mcp_servers.sap_adt.guardrails")
    L = _imp("sap_adt_lib")
    O = _imp("object_types")
    ATOM = _imp("mcp_servers.sap_adt.tools.atom")
    SD = _imp("sap_set_object_description")
    _KURUCU_MOD = ("populate_dataelements", "populate_domains", "populate_lock_objects",
                   "populate_message_class", "populate_tables", "populate_cds_views", "create_rap_service")
    KUR = {ad: _imp(ad) for ad in _KURUCU_MOD}
    CD = _taban_disi_modul("scripts/validators/check_dtel_creation_labels.py", "check_dtel_creation_labels")
    try:
        TG = _taban_modul("mcp_servers/sap_adt/guardrails.py", "guardrails_taban")
        TO = _taban_modul("scripts/object_types.py", "object_types_taban")
        TL = _taban_modul("scripts/sap_adt_lib.py", "sap_adt_lib_taban")
        TKUR = {ad: _taban_modul(f"scripts/{ad}.py", ad + "_taban") for ad in _KURUCU_MOD}
    except Exception as exc:                           # noqa: BLE001
        print(f"[fixture-hatasi] taban kurulamadi: {exc}")
        return 3
    for fn, a in ((bolum_y, (A,)), (bolum_g, (G, TG)), (bolum_l, (L, TL)), (bolum_f, (A, O, ATOM)),
                  (bolum_s, (SD,)), (bolum_r, (A, G, L, O)), (bolum_u, (A, O, TO, KUR, TKUR)),
                  (bolum_d, (KUR["populate_dataelements"], CD, TKUR["populate_dataelements"])),
                  (bolum_k, (TG, TO, TL))):
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
_KOK_ILK = "    baglanti = _baglanti_dizini()\n"
_KOK_KAPALI_KALAN = "        return None, (f\"{ANAHTAR}: bağlantı dosyası"
_KOK_KAPALI_CAPA = _KOK_ILK + "    if baglanti is None:\n" + _KOK_KAPALI_KALAN
_KOK_GERI_DUS = ("    if baglanti is None:\n        from utils.project_config import project_root\n"
                 "        return (Path(root) if root else project_root()), None\n    if False:\n")
MUTASYONLAR = {
    "--mutasyon-ns-kapali": (_AP, "    if ns not in kayitli:\n        return False\n",
                             "    return False\n",
                             {"G1", "G4", "G7", "L1", "L2", "L3", "F2", "F3", "F8", "S1",
                              "R3", "R5", "R9", "D1"}),
    "--mutasyon-ns-dolar": (_AP, 'r"[A-Z0-9_]+' + Z + '", ad, re.IGNORECASE | re.ASCII)',
                            'r"[A-Z0-9_]+$", ad, re.IGNORECASE | re.ASCII)', {"G4"}),
    "--mutasyon-ns-bos-govde": (_AP, 'r"[A-Z0-9_]+' + Z + '", ad, re.IGNORECASE | re.ASCII)',
                                'r"[A-Z0-9_]*' + Z + '", ad, re.IGNORECASE | re.ASCII)', {"G3", "L1"}),
    "--mutasyon-yapi-kismi": (_AP, "    if hatalar:\n        return (), hatalar + [",
                              "    if False:\n        return (), hatalar + [", {"Y5", "G6", "R7", "R8"}),
    "--mutasyon-env-okunur": (_AP, "        ham = veri.get(ANAHTAR)\n",
                              "        _e = __import__('os').environ.get('IX_' + ANAHTAR.upper())\n"
                              "        ham = _e.split(',') if _e else veri.get(ANAHTAR)\n",
                              {"Y6"}),
    "--mutasyon-kayitsiz-kabul": (_AP, "    if ns not in kayitli:\n        return False\n", "",
                                  {"G2", "G6", "G7", "G8", "L1", "L2", "L3", "L4", "F2", "F5", "S2",
                                   "R1", "R2", "R4", "R5", "D2", "R11"}),
    "--mutasyon-ff-z-grupta": ("scripts/object_types.py",
                               "    if _ap.ad_namespace(g) and _ap.musteri_adi_mi(g, root=root):\n",
                               "    if True:\n", {"F4", "F5", "R2"}),
    "--mutasyon-ff-kayit-sarti": ("scripts/object_types.py",
                                  "    if _ap.ad_namespace(g) and _ap.musteri_adi_mi(g, root=root):\n",
                                  "    if _ap.ad_namespace(g):\n", {"F5", "R2"}),
    "--mutasyon-onek-eski": (_AP, '    return ns + "L" + g[len(ns):] if ns else "L" + g\n',
                             '    return "L" + g\n', {"F1", "F2", "F8"}),
    "--mutasyon-guardrail-eski": ("mcp_servers/sap_adt/guardrails.py",
                                  "    return _ad.musteri_adi_mi(name, object_type)\n",
                                  "    return bool(re.match(r'^[ZY][A-Z0-9_]*" + Z + "', name or '', re.I)) or bool("
                                  "object_type and object_type.lower() in _LOCK_TYPES and "
                                  "re.match(r'^E[ZY][A-Z0-9_]*" + Z + "', name or '', re.I))\n",
                                  {"G1", "G4", "G7", "F8", "R3"}),
    "--mutasyon-paket-ns-yok": ("scripts/sap_adt_lib.py",
                                "    if package_upper.startswith('/'):\n",
                                "    if False:\n", {"L2"}),
    "--mutasyon-kilit-zy-yok": (_AP, "    if object_type and object_type.lower() in KILIT_TIPLERI and _KILIT_ZY.match(ad):\n",
                                "    if False:\n", {"G8", "G9", "G10", "R11"}),
    "--mutasyon-harf-duyarli": (_AP, '_ZY = re.compile(r"^[ZY][A-Z0-9_]*' + Z + '", re.IGNORECASE)',
                                '_ZY = re.compile(r"^[ZY][A-Z0-9_]*' + Z + '")', {"G8", "G9"}),
    # ── P2a/bug-gate F2-F5 + öneri ──
    # eski (P1) davranis: bağlantı hiç okunmaz, kök = root / project_root()
    "--mutasyon-kok-proje": (_AP, _KOK_KAPALI_CAPA,
                             "    baglanti = None\n" + _KOK_GERI_DUS + _KOK_KAPALI_KALAN,
                             {"R1", "R2", "R4", "R11"}),
    "--mutasyon-kok-ayrisma": (_AP, "    if root and Path(root).resolve() != baglanti:\n",
                               "    if False:\n", {"R4"}),
    # bug-gate-2 F3: bağlantı dosyası çözülemezse root / project_root()'a DÜŞ (beadd6e davranışı)
    "--mutasyon-baglantisiz-kok": (_AP, _KOK_KAPALI_CAPA, _KOK_ILK + _KOK_GERI_DUS + _KOK_KAPALI_KALAN,
                                   {"R11"}),
    "--mutasyon-onbellek-kalici": (_AP, "    if kayit is not None and kayit[0] == anahtar:\n",
                                   "    if kayit is not None:\n", {"R3", "R5"}),
    "--mutasyon-mukerrer-anahtar": (_AP, "    if tekrar > 1:\n", "    if False:\n", {"R6"}),
    "--mutasyon-ns-harfsiz": (_AP, "(?=[A-Z0-9_]*[A-Z0-9])", "", {"R7"}),
    # DEV_CORE #402: tek gramer {3,8} — eski {1,8}'e dönüş 2 karakterli ögeyi yeniden kabul eder
    "--mutasyon-ns-uzunluk": (_AP, 'NS_GOVDE = r"[A-Za-z0-9_]{3,8}"', 'NS_GOVDE = r"[A-Za-z0-9_]{1,8}"',
                              {"R7c"}),
    "--mutasyon-ns-ascii-oge": (_AP, "        if not str(oge).isascii() or not _NS_BICIM.match(s):\n",
                                "        if not _NS_BICIM.match(s):\n", {"R8"}),
    "--mutasyon-ns-unicode": (_AP, ", ad, re.IGNORECASE | re.ASCII)", ", ad, re.IGNORECASE)", {"R9"}),
    "--mutasyon-coklu-yalniz-fi": ("scripts/object_types.py",
                                   "for r in reflar if r['type'].startswith('FUGR')})",
                                   "for r in reflar if r['type'] == 'FUGR/I'})", {"R10"}),
    "--mutasyon-url-lower": (_AP, '    return _quote(_unquote(str(ad)).lower(), safe="")\n',
                             '    return str(ad).lower()\n', {"U2", "U3", "U7"}),
    "--mutasyon-url-cift": (_AP, '    return _quote(_unquote(str(ad)).lower(), safe="")\n',
                            '    return _quote(str(ad).lower(), safe="")\n', {"U3"}),
    "--mutasyon-baglam-kodlu": ("scripts/object_types.py",
                                "            return url_parcasindan_ad(parcalar[i + 1])",
                                "            return parcalar[i + 1].upper()", {"U5"}),
    "--mutasyon-kurucu-geri": ("scripts/populate_dataelements.py",
                               '<adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{_adt_seg(package)}"',
                               '<adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{package.lower()}"',
                               {"U7", "U8"}),
    "--mutasyon-url-kalinti": ("scripts/populate_tables.py",
                               "    url = client.url + f'/sap/bc/adt/ddic/tables/{_adt_seg(table_name)}/source/main'\n",
                               "    url = client.url + f'/sap/bc/adt/ddic/tables/{table_name.lower()}/source/main'\n",
                               {"U8"}),
    "--mutasyon-atama-kalinti": ("scripts/push_textpool.py", "    prog_l = _adt_seg(prog)\n",
                                 "    prog_l = prog.lower()\n", {"U8"}),
    # bug-gate-2 F2: elle listede OLMAYAN dosya (push_bo_atomic) — koddan türetilen liste yakalar
    "--mutasyon-bo-atomic-lower": ("scripts/push_bo_atomic.py", "    n = _adt_seg(name)\n",
                                   "    n = name.lower()\n", {"U8"}),
    "--mutasyon-dtel-zy": ("scripts/populate_dataelements.py",
                           "            if not _ap.musteri_adi_mi(ad.upper(), root=_gewd()):\n",
                           "            if not ad.upper().startswith(('Z', 'Y')):\n", {"D1"}),
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcp_salt_okur_araclar fixture — Q363①: adt_get_method · adt_revisions · adt_pretty_print.

NEDEN VAR (2026-10-12)
  Üç salt-okur MCP aracı eklendi. Sözleşme:
    · Üçü de SAP'ye YAZMAZ (kilit/PUT/aktivasyon/transport çağrısı YOK — AST ile ölçülür).
    · Her dönüş `scope` (KAPSAM BEYANI) taşır; "bulunamadı" ≠ "yok".
    · `profil_tool` ile kaydolur: geçerli profilde `tools/list`'te VAR, profil çözülemezse YOK
      (fail-closed). CI'da `mcp` paketi olmadığı için kayıt SAHTE FastMCP ile ölçülür.
    · `adt_pretty_print` docstring'i canlı ölçümün KAPSAMINI söyler (sınıf+FM, tek koşum;
      kilit/transport ölçülmedi).

KULLANIM
  python tests/fixtures/mcp_salt_okur_araclar/run.py
  python tests/fixtures/mcp_salt_okur_araclar/run.py --mutasyon
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
_TMP = tempfile.mkdtemp(prefix="mcp_salt_okur_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

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
YENI = ("adt_get_method", "adt_revisions", "adt_pretty_print")
YAZMA_CAGRILARI = {"lock_object", "unlock_object", "set_object_source", "set_include_source",
                   "activate_object", "push_object", "delete_object", "create_object",
                   "require_writable_tier"}

KAYNAK = "\n".join([
    "CLASS zsd001_cl_ornek DEFINITION PUBLIC.",
    "  PUBLIC SECTION.",
    "    METHODS calis.",
    "    METHODS hesapla IMPORTING iv TYPE i.",
    "    INTERFACES zif_sd001_ornek.",
    "ENDCLASS.",
    "CLASS zsd001_cl_ornek IMPLEMENTATION.",
    "* METHOD calis.  yorum satiri, sayilmaz",
    "  METHOD calis.",
    "    \" METHOD hesapla. satir-ici yorum",
    "    WRITE 'x'.",
    "  ENDMETHOD.",
    "  method HESAPLA.",
    "    DATA(lv) = iv.",
    "  endmethod.",
    "  METHOD zif_sd001_ornek~yap.",
    "    RETURN.",
    "  ENDMETHOD.",
    "ENDCLASS.",
])


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:260]))


def _sessiz(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        try:
            return fn(*a, **k), None
        except Exception as exc:                      # noqa: BLE001 — istisna ÖLÇÜLÜR
            return None, exc
    finally:
        _TUT.append(atik)
        sys.stdout, sys.stderr = eski


def _imp(ad):
    import importlib
    m, exc = _sessiz(importlib.import_module, ad)
    if m is None:
        raise SystemExit(f"[fixture-hatasi] {ad} import edilemedi: {exc!r}")
    return m


def bolum_g(Q, A):
    cik = Q._metot_cikar
    b = cik(KAYNAK, "calis")
    ekle("G1 ⭐ METHOD calis bulunur (sutun-1 `*` yorumu ve METHODS tanimi SAYILMAZ)",
         len(b) == 1 and b[0][0] == 9 and b[0][1] == 12 and "WRITE 'x'." in b[0][2], b)
    b = cik(KAYNAK, "Hesapla")
    ekle("G2 harf-durumundan bagimsiz (`method HESAPLA.` .. `endmethod.`) + satir-ici yorum sayilmaz",
         len(b) == 1 and b[0][0] == 13 and b[0][1] == 15, b)
    b = cik(KAYNAK, "zif_sd001_ornek~yap")
    ekle("G3 arayuz metodu `zif~m` bicimi", len(b) == 1 and b[0][0] == 16, b)
    ekle("G4 CRLF kaynak ayni sonucu verir", cik(KAYNAK.replace("\n", "\r\n"), "calis")[0][:2] == (9, 12), "")
    ekle("G5 kapanmamis blok -> son=None", cik("  METHOD calis.\n  WRITE 1.\n", "calis")[0][1] is None, "")
    b = cik("  METHOD calis.\n    WRITE 1. \" ENDMETHOD. yorumda\n* ENDMETHOD.\n    WRITE 2.\n  ENDMETHOD.\n", "calis")
    ekle("G5b yorumdaki ENDMETHOD blogu erken KAPATMAZ (satir-ici + sutun-1)",
         len(b) == 1 and b[0][:2] == (1, 5) and "WRITE 2." in b[0][2], b)

    def mcp(kaynak, metot, oku=None):
        A._read_source_object = oku or (lambda n, s, t: {"ok": True, "exists": True, "name": n.upper(),
                                                           "type": t, "source": kaynak, "client_log": ""})
        r, exc = _sessiz(Q.adt_get_method, class_name="ZSD001_CL_ORNEK", method_name=metot)
        return r if r is not None else {"_istisna": repr(exc)}

    r = mcp(KAYNAK, "calis")
    ekle("G6 ⭐ MCP bulundu -> ok + found + satirlar + scope", r.get("ok") is True and r.get("found") is True
         and r.get("start_line") == 9 and "ARANMAZ" in (r.get("scope") or ""), r)
    r = mcp(KAYNAK, "yok_boyle")
    ekle("G7 ⭐ MCP bulunamadi -> ok + found False + scope ('metot yok' DEMEZ)",
         r.get("ok") is True and r.get("found") is False and "DEGILDIR" in (r.get("scope") or ""), r)
    r = mcp(KAYNAK + "\nCLASS lcl IMPLEMENTATION.\n  METHOD calis.\n  ENDMETHOD.\nENDCLASS.", "calis")
    ekle("G8 iki ayri blok -> ok False + belirsiz (hangisi oldugu uydurulmaz)",
         r.get("ok") is False and r.get("error") == "belirsiz" and len(r.get("matches") or []) == 2, r)
    r = mcp("  METHOD calis.\n  WRITE 1.\n", "calis")
    ekle("G9 kapanmamis -> ok False + kapanmamis", r.get("ok") is False and r.get("error") == "kapanmamis", r)
    r = mcp("", "calis", oku=lambda n, s, t: {"ok": True, "exists": False, "name": n, "type": t})
    ekle("G10 sinif YOK -> alt katman sonucu AYNEN (+scope), found uydurulmaz",
         r.get("exists") is False and "found" not in r and r.get("scope"), r)

    # ── DEV_CORE Issue #362 (2026-10-27): blok SINIRI — tek satır · satır ortası · belirsiz ──
    # Eski kod (367eda1) tek satırda `[(1, 4, 'METHOD a. x = 1. ENDMETHOD.|METHOD b.|…')]`
    # döndürüyordu: SONRAKİ metodun gövdesi `found:true` ile. Sınır artık ilk deyimdir.
    tek = "METHOD a. x = 1. ENDMETHOD.\nMETHOD b.\n  y = 2.\nENDMETHOD."
    b = cik(tek, "a")
    ekle("G11 ⭐ tek satirlik METHOD a. .. ENDMETHOD. -> blok YALNIZ o satir",
         b == [(1, 1, "METHOD a. x = 1. ENDMETHOD.")], b)
    b = cik(tek, "b")
    ekle("G11b tek satirdan sonraki cok satirli metot dogru bulunur", b and b[0][:2] == (2, 4), b)
    b = cik("METHOD a. ENDMETHOD.\nMETHOD b.\nENDMETHOD.", "a")
    ekle("G12 bos tek satir `METHOD a. ENDMETHOD.` -> (1,1)", b == [(1, 1, "METHOD a. ENDMETHOD.")], b)
    b = cik("METHOD b.\n  y = 2.\nENDMETHOD.\n  METHOD a. ENDMETHOD.", "a")
    ekle("G13 tek satir SON metot -> (4,4) (kapanmamis DEGIL)",
         b == [(4, 4, "  METHOD a. ENDMETHOD.")], b)
    b = cik("METHOD a.\n  x = 1.\nENDMETHOD.\nMETHOD b.\nENDMETHOD.", "a")
    ekle("G14 cok satirli kontrol -> (1,3)", b and b[0][:2] == (1, 3) and len(b) == 1, b)
    b = cik("METHOD a.\n  x = 1. ENDMETHOD.\nMETHOD b.\n  y = 2.\nENDMETHOD.", "a")
    ekle("G15 ⭐ satir ORTASINDAKI `ENDMETHOD.` bitistir -> (1,2), b'nin govdesi YOK",
         b and b[0][:2] == (1, 2) and "METHOD b" not in b[0][2], b)
    b = cik("METHOD a. ENDMETHOD. METHOD b. ENDMETHOD.", "a")
    ekle("G16 ayni satirda METHOD/ENDMETHOD karisik -> SINIR_BELIRSIZ",
         len(b) == 1 and b[0][1] == Q._SINIR_BELIRSIZ, b)
    b = cik("METHOD a.\n  x = 1.\nMETHOD b.\n  y = 2.\nENDMETHOD.", "a")
    ekle("G17 ENDMETHOD'dan once METHOD -> SINIR_BELIRSIZ (eskisi (1,5) yanlis govde)",
         len(b) == 1 and b[0][1] == Q._SINIR_BELIRSIZ, b)
    b = cik("METHOD a.\n  lv = 'x. ENDMETHOD.'.\n  lv2 = |y. ENDMETHOD.|.\n"
            "  lv3 = `z. ENDMETHOD.`.\nENDMETHOD.", "a")
    ekle("G18 tek satirlik literal icindeki ENDMETHOD bitis SAYILMAZ (' ` |)",
         b and b[0][:2] == (1, 5), b)
    b = cik("METHOD a.\n* x. ENDMETHOD.\n  WRITE 1.\nENDMETHOD.", "a")
    ekle("G19 sutun-1 `*` yorumundaki `. ENDMETHOD.` bitis SAYILMAZ", b and b[0][:2] == (1, 4), b)
    b = cik("METHOD a.\n  WRITE 1. \" bitti. ENDMETHOD. degil\n  WRITE 2.\nENDMETHOD.", "a")
    ekle("G20 `\"` satir-ici yorumdaki `. ENDMETHOD.` bitis SAYILMAZ", b and b[0][:2] == (1, 4), b)
    r = mcp(tek, "a")
    ekle("G21 ⭐ MCP tek satir -> found + start=end=1 + govde YALNIZ a",
         r.get("ok") is True and r.get("found") is True and r.get("start_line") == 1
         and r.get("end_line") == 1 and r.get("source") == "METHOD a. x = 1. ENDMETHOD.", r)
    r = mcp("METHOD a. ENDMETHOD. METHOD b. ENDMETHOD.", "a")
    ekle("G22 ⭐ MCP sinir belirsiz -> ok False + sinir_belirsiz + govde DONMEZ",
         r.get("ok") is False and r.get("error") == "sinir_belirsiz" and r.get("found") is None
         and "source" not in r, r)
    ekle("G23 KAPSAM metni tek satir + sinir_belirsiz + cok satirli sablon SINIRINI soyler",
         all(s in Q._METOT_KAPSAM for s in ("tek satirlik", "sinir_belirsiz", "cok satirli string")),
         Q._METOT_KAPSAM)

    # ── bug-gate #378 düzeltme turu (2026-10-27) ──
    # F1: `|…|` şablonunda `\` kaçışı atlanmazsa `\|` şablonu erken "kapatır", içindeki
    # ENDMETHOD bitiş sanılır → kesik gövde (eski regex burada doğruydu: (1,4)).
    b = cik(ESKI_PIPE, "a")
    ekle("G24 ⭐ `|x\\|. ENDMETHOD. |` sablon kacisi -> bitis SABLON ICINDE DEGIL (1,4)",
         b and b[0][:2] == (1, 4) and len(b) == 1, b)
    # F3: deyim başındaki `method` TANIMLAYICISI METHOD deyimi değildir (eski kod doğruydu).
    for ad, kaynak, beklenen in (
            ("G25 `method = 'GET'.` atamasi", "METHOD a.\n  method = 'GET'.\n  x = 1.\nENDMETHOD.", (1, 4)),
            ("G26 cok satirli cagrida `method = …` parametresi",
             "METHOD a.\n  lo->call(\n    method = if_http_request=>co_request_method_post ).\nENDMETHOD.",
             (1, 4)),
            ("G27 `x = 1.method = 2.` (bosluksuz nokta)", "METHOD a.\n  x = 1.method = 2.\nENDMETHOD.", (1, 3)),
            ("G28 AMDP `select t.method from …`",
             "METHOD a BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT.\n"
             "  select t.method from ztab as t;\nENDMETHOD.", (1, 3)),
            ("G29 `endmethod = 1.` tanimlayicisi bitis DEGIL",
             "METHOD a.\n  endmethod = 1.\n  x = 2.\nENDMETHOD.", (1, 4))):
        b = cik(kaynak, "a")
        ekle(ad + " -> deyim SAYILMAZ %s" % (beklenen,), b and b[0][:2] == beklenen and len(b) == 1, b)
    b = cik("METHOD a.\n  x = 1.\nMETHOD b BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT.\n"
            "ENDMETHOD.", "a")
    ekle("G30 daraltma AMDP `METHOD b BY …` deyimini KORUR -> SINIR_BELIRSIZ",
         len(b) == 1 and b[0][1] == Q._SINIR_BELIRSIZ, b)


# `\|` ABAP şablon kaçışı (tek ters eğik çizgi; chr(92) — Bash/heredoc kaçış kaybına bağışık)
ESKI_PIPE = ("METHOD a.\n  r = |x" + chr(92) + "|. ENDMETHOD. |.\n  z = 2.\nENDMETHOD.\n"
             "METHOD b.\nENDMETHOD.")


def bolum_f(SC):
    """`sap_client._push_method_includes` YAZMA yolu (Issue #362 kardeşi): belirsiz sınırda
    kilit ALINMAZ, PUT YAPILMAZ; tek satırlık metotta PUT edilen gövde YALNIZ o metottur."""
    class _Adt:
        _last_lock_effective_transport = None

        def __init__(self):
            self.kilit, self.put = [], []

        def lock_object(self, url, transport=None):
            self.kilit.append(url)
            return "KILIT-1"

        def set_include_source(self, url, govde, kilit, transport):
            self.put.append((url, govde))

        def unlock_object(self, url, kilit):
            return True

    def kos(kaynak, metotlar):
        ist = object.__new__(SC.SAPClient)
        ist.adt_client = _Adt()
        ist.debug_enabled = False
        r, exc = _sessiz(ist._push_method_includes, "/sap/bc/adt/oo/classes/zsd001_cl_ornek",
                         "ZSD001_CL_ORNEK", kaynak, metotlar, "<TRANSPORT>")
        return (r if exc is None else repr(exc)), ist.adt_client

    tek = "METHOD a. x = 1. ENDMETHOD.\nMETHOD b.\n  y = 2.\nENDMETHOD."
    r, adt = kos(tek, ["A"])
    ekle("F1 ⭐ tek satirlik metot -> 1 PUT, govde YALNIZ a (b'nin govdesi YAZILMAZ)",
         r is True and len(adt.put) == 1 and adt.put[0][1] == "METHOD a. x = 1. ENDMETHOD.\n"
         and adt.put[0][0].endswith("/includes/implementations/A"), (r, adt.put))
    r, adt = kos("METHOD a. ENDMETHOD. METHOD b. ENDMETHOD.", ["A"])
    ekle("F2 ⭐ ayni satirda karisik sinir -> kilit 0 + PUT 0 + False",
         r is False and not adt.kilit and not adt.put, (r, adt.kilit, adt.put))
    r, adt = kos("METHOD a.\n  x = 1.\nMETHOD b.\n  y = 2.\nENDMETHOD.", ["A"])
    ekle("F3 ⭐ ENDMETHOD'dan once METHOD -> kilit 0 + PUT 0 (eskisi a+b'yi PUT ediyordu)",
         r is False and not adt.kilit and not adt.put, (r, adt.kilit, adt.put))
    r, adt = kos("METHOD a.\n  x = 1.\nENDMETHOD.\nMETHOD b.\nENDMETHOD.", ["A", "B"])
    ekle("F4 cok satirli kontrol -> iki PUT, govdeler dogru (FP capasi)",
         r is True and [p[1] for p in adt.put] == ["METHOD a.\n  x = 1.\nENDMETHOD.\n",
                                                   "METHOD b.\nENDMETHOD.\n"], (r, adt.put))
    r, adt = kos("METHOD a.\n  x = 1.\n", ["A"])
    ekle("F5 kapanmamis blok -> kilit 0 + PUT 0", r is False and not adt.kilit and not adt.put,
         (r, adt.kilit, adt.put))
    r, adt = kos(ESKI_PIPE, ["A"])
    beklenen = "\n".join(ESKI_PIPE.split("\n")[:4]) + "\n"
    ekle("F6 ⭐ sablon kacisli metot -> PUT edilen govde TAM blok (kesik govde YAZILMAZ)",
         r is True and len(adt.put) == 1 and adt.put[0][1] == beklenen, (r, adt.put))


def bolum_r(Q, L):
    class _Adt:
        def __init__(self, sonuc):
            self.sonuc = sonuc
            self.url = None

        def get_object_revisions(self, url):
            self.url = url
            if isinstance(self.sonuc, Exception):
                raise self.sonuc
            return self.sonuc

    def mcp(sonuc, limit=20):
        adt = _Adt(sonuc)
        Q._get_client = lambda: types.SimpleNamespace(adt_client=adt)
        r, exc = _sessiz(Q.adt_revisions, name="ZSD001_CL_ORNEK", object_type="class", limit=limit)
        return (r if r is not None else {"_istisna": repr(exc)}), adt

    revs = [{"version": str(i), "author": "SAP_USER_A"} for i in range(5)]
    r, adt = mcp(revs, limit=3)
    ekle("R1 ⭐ count TAMAMI + revisions limit kadar + truncated + scope",
         r.get("ok") is True and r.get("count") == 5 and len(r.get("revisions")) == 3
         and r.get("truncated") is True and r.get("scope")
         and adt.url == "/sap/bc/adt/oo/classes/zsd001_cl_ornek", r)
    r, _ = mcp([])
    ekle("R2 bos feed -> ok + count 0 + truncated False", r.get("ok") is True and r.get("count") == 0
         and r.get("truncated") is False, r)
    r, _ = mcp(L.SAPObjectNotFoundError("yok", status_code=404))
    ekle("R3 obje yok -> ok False + not_found (count BASILMAZ)",
         r.get("ok") is False and r.get("error") == "not_found" and "count" not in r, r)
    r, _ = mcp(L.SAPADTError("feed okunamadi", status_code=500))
    ekle("R4 ⭐ okunamadi -> ok False + sap_error ('surum yok' DEGIL, count BASILMAZ)",
         r.get("ok") is False and r.get("error") == "sap_error" and "count" not in r, r)


def bolum_p(Q):
    def mcp(donus):
        Q._get_client = lambda: types.SimpleNamespace(pretty_print=lambda n, t: donus)
        r, exc = _sessiz(Q.adt_pretty_print, name="ZSD001_CL_ORNEK", object_type="class")
        return r if r is not None else {"_istisna": repr(exc)}

    r = mcp("CLASS X.\nENDCLASS.")
    ekle("P1 bicimli metin doner + written False + scope", r.get("ok") is True
         and r.get("formatted_source") == "CLASS X.\nENDCLASS." and r.get("written") is False
         and "YAZILMAZ" in (r.get("scope") or ""), r)
    r = mcp(None)
    ekle("P2 alt katman None -> ok False + pretty_print_failed + 'DEGISMEDI'",
         r.get("ok") is False and r.get("error") == "pretty_print_failed"
         and "DEĞİŞMEDİ" in (r.get("message") or ""), r)
    dok = Q.adt_pretty_print.__doc__ or ""
    ekle("P3 docstring canli olcumun KAPSAMINI soyler (sinif + FM, tek kosum, kilit/transport olculmedi)",
         "canlı ölçümle doğrulandı" in dok and "sınıf + FM" in dok and "ÖLÇÜLMEDİ" in dok, dok[:200])


def bolum_v(Q, A, SC, gercek_oku):
    """KAPSAM BEYANI'nın SÜRÜM iddiası ↔ GERÇEK istek (bug-gate 2026-10-14, B-2).

    Eski metin "aktif surum" / "AKTIF kaynagi" diyordu; oysa iki yol da `version` parametresiz
    GET yapar ⇒ SAP en güncel sürümü (bekleyen inaktif varsa O) döner. Vektör isteği YAKALAR
    ve metni ona bağlar: GET'e `version` eklenirse V1a/V2a düşer ⇒ metin de güncellenmek zorunda.
    """
    istekler = []

    class _Oturum:
        def get(self, url, **kw):
            istekler.append((url, kw))
            return types.SimpleNamespace(status_code=200, text=KAYNAK)
    ist = types.SimpleNamespace(adt_client=types.SimpleNamespace(url="https://sap.example.test",
                                                                 session=_Oturum()))
    eski = (A._get_client, A._read_source_object)
    try:
        A._get_client = lambda: ist
        A._read_source_object = gercek_oku
        r, exc = _sessiz(Q.adt_get_method, class_name="ZSD001_CL_ORNEK", method_name="calis")
    finally:
        A._get_client, A._read_source_object = eski
    r = r or {"_istisna": repr(exc)}
    url, kw = istekler[-1] if istekler else ("", {})
    ekle("V1a adt_get_method GERCEK okuma: GET'te `version` YOK (url + params)",
         len(istekler) == 1 and "version" not in url and "version" not in (kw.get("params") or {}),
         istekler)
    sc = r.get("scope") or ""
    ekle("V1b ⭐ adt_get_method scope: EN GUNCEL surum, 'inaktif surum varsa O okunur' (aktif DEGIL)",
         r.get("found") is True and "inaktif surum varsa" in sc and "O okunur" in sc
         and "aktif surum DEGIL" in sc and "inaktif surum ARANMAZ" not in sc, sc)

    cagri = []

    class _Adt:
        def get_object_source(self, url, *a, **kw):
            cagri.append((url, a, kw))
            return KAYNAK

        def pretty_print(self, url, kaynak):
            return kaynak.upper()
    gercek_ist = object.__new__(SC.SAPClient)
    gercek_ist.adt_client = _Adt()
    gercek_ist.debug_enabled = False
    eski_q = Q._get_client
    try:
        Q._get_client = lambda: gercek_ist
        r, exc = _sessiz(Q.adt_pretty_print, name="ZSD001_CL_ORNEK", object_type="class")
    finally:
        Q._get_client = eski_q
    r = r or {"_istisna": repr(exc)}
    a_ = cagri[-1] if cagri else ("", (), {})
    ekle("V2a adt_pretty_print GERCEK SAPClient.pretty_print: get_object_source `version` VERMEZ",
         len(cagri) == 1 and not a_[1] and a_[2].get("version") is None, cagri)
    sc = r.get("scope") or ""
    ekle("V2b ⭐ adt_pretty_print scope: 'inaktif surum varsa O okunur', 'AKTIF kaynagi' iddiasi YOK",
         r.get("ok") is True and "inaktif surum varsa" in sc and "O okunur" in sc
         and "AKTIF kaynagi" not in sc and "YAZILMAZ" in sc, sc)


def bolum_y():
    yol = REPO / "mcp_servers" / "sap_adt" / "tools" / "query.py"
    agac = ast.parse(yol.read_text(encoding="utf-8"))
    fnler = {n.name: n for n in agac.body if isinstance(n, ast.FunctionDef)}
    kotu = {}
    for ad in YENI + ("_metot_cikar",):
        fn = fnler.get(ad)
        if fn is None:
            kotu[ad] = "TANIM YOK"
            continue
        cagri = {(c.func.attr if isinstance(c.func, ast.Attribute) else getattr(c.func, "id", ""))
                 for c in ast.walk(fn) if isinstance(c, ast.Call)}
        if cagri & YAZMA_CAGRILARI:
            kotu[ad] = sorted(cagri & YAZMA_CAGRILARI)
    ekle("Y1 ⭐ uc aracin govdesinde YAZMA/kilit/aktivasyon cagrisi YOK (AST)", not kotu, kotu)
    from mcp_servers.sap_adt.guardrails import SALT_OKUR_ARACLAR
    ekle("Y2 uc arac SALT_OKUR_ARACLAR listesinde", set(YENI) <= SALT_OKUR_ARACLAR, "")


KAYIT = r'''
import sys, types
sys.path[:0] = [r"{kok}", r"{kok}/scripts", r"{kok}/scripts/utils"]
kayitli = []
class _F:
    def __init__(self, *a, **k): pass
    def tool(self, *a, **k):
        def d(fn):
            kayitli.append(fn.__name__)
            return fn
        return d
m = types.ModuleType("mcp"); s = types.ModuleType("mcp.server"); f = types.ModuleType("mcp.server.fastmcp")
f.FastMCP = _F; s.fastmcp = f; m.server = s
sys.modules["mcp"] = m; sys.modules["mcp.server"] = s; sys.modules["mcp.server.fastmcp"] = f
import io
_e = sys.stderr; sys.stderr = io.StringIO()
import mcp_servers.sap_adt.tools.query
sys.stderr = _e
print("KAYITLI=" + ",".join(sorted(kayitli)))
'''


def _kayit(profil):
    kum = Path(tempfile.mkdtemp(prefix="mcp_kayit_"))
    try:
        if profil:
            (kum / "project.yaml").write_text(
                f"sap_profile: {profil}\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(kum)
        r = subprocess.run([sys.executable, "-c", KAYIT.format(kok=str(REPO))], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120, cwd=str(kum), env=env)
        m = re.search(r"^KAYITLI=(.*)$", r.stdout, re.M)
        return (set(filter(None, m.group(1).split(","))) if m else None), r.stdout[-300:] + r.stderr[-300:]
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def bolum_k():
    k1, d1 = _kayit("s4_private")
    k2, d2 = _kayit("btp_abap")
    k3, d3 = _kayit(None)
    ekle("K1 ⭐ s4_private: uc arac tools/list'te (profil_tool kaydi)", k1 is not None and set(YENI) <= k1,
         d1 if k1 is None else sorted(set(YENI) - k1))
    ekle("K2 btp_abap: uc arac kayitli (available_on=all)", k2 is not None and set(YENI) <= k2,
         d2 if k2 is None else sorted(set(YENI) - k2))
    ekle("K3 ⭐ profil cozulemez -> uc arac KAYITSIZ (fail-closed)", k3 is not None and not (set(YENI) & k3),
         d3 if k3 is None else sorted(set(YENI) & k3))


def main() -> int:
    L = _imp("sap_adt_lib")
    Q = _imp("mcp_servers.sap_adt.tools.query")
    A = _imp("mcp_servers.sap_adt.tools.atom")
    SC = _imp("sap_client")
    eski = (A._read_source_object, Q._get_client)
    for fn, a in ((bolum_g, (Q, A)), (bolum_r, (Q, L)), (bolum_p, (Q,)),
                  (bolum_v, (Q, A, SC, eski[0])), (bolum_f, (SC,)), (bolum_y, ()), (bolum_k, ())):
        try:
            fn(*a)
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle(f"[BOLUM COKTU] {fn.__name__}", False, f"{type(exc).__name__}: {exc}")
    A._read_source_object, Q._get_client = eski
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


# 5. eleman (varsa) = düşmesi BEKLENEN vektör önekleri; rc != 0 tek başına yakalama kanıtı DEĞİL.
_BLOK = "scripts/utils/abap_metot_blok.py"
MUTASYONLAR = [
    # Issue #362 (2026-10-27): M1/M6 çapası query.py'den ortak modüle taşındı (sınır tek kaynakta).
    ("M1 METHOD deseni satir basina capali degil (yorum satiri sayilir)", _BLOK,
     'METOT_BAS = re.compile(r"^\\s*METHOD', 'METOT_BAS = re.compile(r"^.*?METHOD', ("G1 ",)),
    ("M6 `\"` satir-ici yorum kesilmez (yorumdaki ENDMETHOD blogu erken kapatir)", _BLOK,
     "        if c == '\"':\n            break\n", "        if False:\n            break\n",
     ("G20",)),
    ("M10 tek satirlik blok dali kapali (eski davranisa yakin)", _BLOK,
     '            if ek == ["ENDMETHOD"]:\n', "            if False:\n",
     ("G11 ", "G12", "G13", "G21", "F1 ")),
    ("M11 deyim yalniz satir basinda (satir ortasi ENDMETHOD kacirilir)", _BLOK,
     '_DEYIM = re.compile(r"(?:^|\\.)\\s*', '_DEYIM = re.compile(r"^\\s*', ("G11 ", "G15")),
    ("M12 tek satirlik literal ayiklanmaz", _BLOK,
     "        if c in \"'`|\":\n", "        if False:\n", ("G18",)),
    ("M13 sutun-1 `*` yorumu ayiklanmaz", _BLOK,
     '    if satir.startswith("*"):\n        return ""\n', '    if False:\n        return ""\n',
     ("G19",)),
    ("M14 sap_client fallback sinir-belirsiz atlamasi kalkar (yanlis blok PUT edilir)",
     "scripts/sap_client.py",
     "            if _son is None or _son == SINIR_BELIRSIZ:\n", "            if False:\n",
     ("F2 ", "F3 ", "F5 ")),
    ("M15 adt_get_method sinir_belirsiz dali kalkar (found:true + yanlis govde)",
     "mcp_servers/sap_adt/tools/query.py",
     "    if belirsiz is not None:\n", "    if False:\n", ("G22",)),
    # bug-gate #378 düzeltme turu (2026-10-27): F1 kaçış · F3 deyim biçimi (iki katman ayrı)
    ("M16 `|` sablonunda `\\` kacisi atlanmaz (F1 geri)", _BLOK,
     '                j += 2 if (c == "|" and satir[j] == "' + chr(92) * 2 + '") else 1\n',
     "                j += 1\n", ("G24", "F6 ")),
    ("M17 METHOD deyim bicimi daraltmasi geri (`method = …` deyim sayilir)", _BLOK,
     r'|(METHOD)(?=\s+[A-Za-z0-9_/~]+\s*(?:\.|\s+BY\b)))"', r'|(METHOD)(?=[\s.]|$))"',
     ("G25", "G26", "G27", "G28")),
    ("M18 ENDMETHOD deyim bicimi daraltmasi geri (`endmethod = 1.` bitis sayilir)", _BLOK,
     r'(?:(ENDMETHOD)(?=\s*\.)"', r'(?:(ENDMETHOD)(?=[\s.]|$)"', ("G29",)),
    ("M2 coklu blok ilki secilir (belirsizlik gizlenir)", "mcp_servers/sap_adt/tools/query.py",
     "    if len(bloklar) > 1:\n        return {\"ok\": False, \"error\": \"belirsiz\"",
     "    if False:\n        return {\"ok\": False, \"error\": \"belirsiz\""),
    ("M3 revisions count kirpilmis listeden", "mcp_servers/sap_adt/tools/query.py",
     '"count": len(revs),', '"count": len(revs[:max(0, int(limit))]),'),
    ("M4 pretty_print tier kapisina baglanir (salt-okur sinif bozulur)", "mcp_servers/sap_adt/tools/query.py",
     "    client = _get_client()\n    try:\n        with _capture() as buf:\n            bicimli = client.pretty_print(",
     "    from mcp_servers.sap_adt.guardrails import require_writable_tier\n"
     "    require_writable_tier('DEV')\n"
     "    client = _get_client()\n    try:\n        with _capture() as buf:\n            bicimli = client.pretty_print("),
    ("M5 arac profil_tool ile kaydolmaz", "mcp_servers/sap_adt/tools/query.py",
     "@profil_tool()\ndef adt_revisions(", "def adt_revisions("),
    # B-2 (bug-gate 2026-10-14): KAPSAM metni eski yanlış sürüm iddiasına geri
    ("M7 metot scope'u eski 'aktif surum' iddiasina geri", "mcp_servers/sap_adt/tools/query.py",
     "    \"Sinifin ANA kaynagi (`source/main`, \" + _SURUM_NOTU + \") METINSEL taranir",
     "    \"Sinifin ANA kaynagi (`source/main`, aktif surum; inaktif surum ARANMAZ) METINSEL taranir"),
    ("M8 bicim scope'u eski 'AKTIF kaynagi' iddiasina geri", "mcp_servers/sap_adt/tools/query.py",
     "    \"Objenin kaynagi okunur (\" + _SURUM_NOTU + \"), \"\n",
     "    \"Objenin AKTIF kaynagi okunur, \"\n"),
    ("M9 okuma GET'ine version=active eklenir (metin bayatlar)", "mcp_servers/sap_adt/tools/atom.py",
     "            r = adt.session.get(url, headers={\"Accept\": \"text/plain\"}, verify=False, timeout=60)\n",
     "            r = adt.session.get(url, headers={\"Accept\": \"text/plain\"}, verify=False, timeout=60,\n"
     "                                params={\"version\": \"active\"})\n"),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="mcp_salt_okur_kum_"))
    kotu = []
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        hedef.mkdir(parents=True)
        shutil.copy2(Path(__file__), hedef / "run.py")

        def _kos():
            return subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=300, cwd=str(kok))
        # KUM TABANI: mutasyonsuz kopya tam yeşil olmalı (yoksa hiçbir "yakalandı" anlamlı değil)
        r = _kos()
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        print(f"--> [KUM TABANI] rc={r.returncode} {m.group(0) if m else '-'}")
        if r.returncode or not m:
            print("[KURULAMADI] kum tabani yesil degil:\n" + r.stdout[-800:] + r.stderr[-400:])
            return 3
        for ad, yol, eski, yeni, *bek in MUTASYONLAR:
            beklenen = bek[0] if bek else ()
            dosya = kok / yol
            asil = dosya.read_bytes().decode("utf-8")
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez")
                kotu.append(ad)
                continue
            dosya.write_bytes(asil.replace(eski, yeni, 1).encode("utf-8"))
            try:
                r = _kos()
            finally:
                dosya.write_bytes(asil.encode("utf-8"))
            m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
            dusen = [x.strip()[len("[FAIL] "):] for x in r.stdout.splitlines()
                     if x.strip().startswith("[FAIL]")]
            eksik = [b for b in beklenen if not any(d.startswith(b) for d in dusen)]
            durum = ("COKTU" if not m else
                     ("YAKALANDI" if r.returncode and not eksik else
                      (f"KACTI(beklenen dusmedi: {eksik})" if r.returncode else "KACTI")))
            if durum != "YAKALANDI":
                kotu.append(ad)
            print(f"--> [{ad}] rc={r.returncode} {m.group(0) if m else '-'} -> {durum}")
            for s in [x.strip() for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")][:3]:
                print(f"      {s[:150]}")
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    print(f"\nMUTASYON OZETI: {len(MUTASYONLAR) - len(kotu)}/{len(MUTASYONLAR)} yakalandi")
    return 1 if kotu else 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    sys.exit(main())

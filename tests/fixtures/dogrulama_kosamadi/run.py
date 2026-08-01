#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dogrulama_kosamadi fixture — "DOGRULAMA KOSAMADI = DOGRULANDI" SINIFI.

NEDEN VAR (2026-08-01 adversarial bug-avi, 5 kayit / TEK kok):
Bir dogrulamanin UC olasi sonucu vardir: **ok · fail · KOSAMADI**. Bes ayri yerde ucuncu
deger sessizce BIRINCIYE (olumluya) katlaniyordu:

  R1 adt_delete      readback patlayinca            -> delete_verified: TRUE
  R2 adt_push_source readback kosamayinca           -> success:true, KOSAN durumdan ayirt EDILEMEZ
  R3 where_used/ATC  `except ET.ParseError: pass`   -> [] = "tuketicisi yok" / "kod temiz"
  R4 csrf()          `raise SystemExit`             -> tool'un `except Exception`ina TAKILMAZ
  R5 package_contents paket-ucu patlayinca          -> AD-DESENLI arama fallback'i = BASKA
                                                       paketlerin objeleri, isaretsiz
Ortak kok: "kanit uretemedim" ile "kanit olumlu" AYNI cikti. Sonuclar geri alinamaz
(silme, yazim, orphan-sweep, ADR 0005-A yeniden-yaratma).

POLITIKA: ucuncu deger ACIKCA yazilir (None / ok:false-belirsiz / package_verified:false)
ve ASLA olumluya katlanmaz.

⚠ KONTROL GRUBU BU TESTIN OMURGASI: her kayitta "temiz vaka ESKISI GIBI GECER" satiri
vardir (404 -> delete_verified TRUE · readback tuttu -> True · gecerli-bos XML -> []
"tuketicisi yok" · gecerli token -> published · nodestructure -> package_verified TRUE).
O satirlar SILINIRSE test asiri-siki olur ve gercek isi bloklar.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(p))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(REPO))

# ── MCP SDK KOPRUSU (test-harness'i, uretim kodu DEGIL) ──────────────────────────
# `atom.py`/`query.py` -> `_app.py` -> `from mcp.server.fastmcp import FastMCP`. Olculen
# sey MCP tool KATMANININ DAVRANISI (calisma-zamani) -> AST ile okunamaz, import sart.
# CI'da SDK yok; yalniz EKSIKSE bu import'u karsilayan asgari sahte modul kurulur
# (gercek SDK varsa DOKUNULMAZ). Sinir: kopru FastMCP'yi TEST ETMEZ; onu MCP import-smoke
# yakalar. Desen: tests/fixtures/adtget_yokluk_kaniti/run.py (core#82).
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    import types as _t
    _mcp, _srv, _fast = (_t.ModuleType("mcp"), _t.ModuleType("mcp.server"),
                         _t.ModuleType("mcp.server.fastmcp"))

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _dek(fn):
                return fn
            return _dek

    _fast.FastMCP = _FastMCP                                 # type: ignore[attr-defined]
    _srv.fastmcp = _fast                                     # type: ignore[attr-defined]
    _mcp.server = _srv                                       # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

try:
    from mcp_servers.sap_adt.tools import atom, query
    from sap_adt_lib import SAPADTClient, SAPADTError
    from sap_client import SAPClient
except Exception as exc:                                    # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")


SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def _hata(sinif, mesaj, kod=None):
    e = sinif(mesaj)
    if kod is not None:
        setattr(e, "status_code", kod)
    return e


# =============================================================================
# R1 — adt_delete: silme-sonrasi varlik readback (True/False/None)
# =============================================================================
class _R1Client:
    """GERCEK `SAPClient.get_object_metadata` govdesini kullanir (istisna-yutma DAHIL)."""

    def __init__(self, md_hata, md_deger=None):
        self._md_hata, self._md_deger = md_hata, md_deger

        class _Adt:
            def __init__(_s):
                _s.url, _s.client = "https://sap.test", "100"

            def get_object_structure(_s, url, version="active"):
                if md_hata is not None:
                    raise md_hata
                return md_deger
        self.adt_client = _Adt()

    def get_object_metadata(self, name, object_type="class"):
        return SAPClient.get_object_metadata(self, name, object_type=object_type)

    def delete_object(self, object_name, object_type, transport=None, confirm=False):
        return True


def r1_delete():
    vakalar = [
        # (ad, metadata-hatasi, metadata-degeri, beklenen delete_verified, beklenen ok)
        ("R1 KONTROL gercek 404 -> delete_verified TRUE (korunmali)",
         _hata(SAPADTError, "Failed to get object structure", 404), None, True, True),
        ("R1 KONTROL obje HALA VAR -> delete_verified FALSE + ok FALSE",
         None, "<xml>hala burada</xml>", False, False),
        ("R1 BOZUK HTTP 500 -> delete_verified None (TRUE DEGIL)",
         _hata(SAPADTError, "Internal Server Error", 500), None, None, True),
        ("R1 BOZUK 403 logon -> delete_verified None",
         _hata(SAPADTError, "Forbidden - logon failed", 403), None, None, True),
        ("R1 BOZUK baglanti kopuk -> delete_verified None",
         _hata(ConnectionError, "Max retries exceeded / getaddrinfo failed"), None, None, True),
    ]
    eski, eski_tier = atom._get_client, atom.get_active_tier
    try:
        atom.get_active_tier = lambda: "DEV"
        for ad, mh, mv, bekl_dv, bekl_ok in vakalar:
            atom._get_client = lambda _mh=mh, _mv=mv: _R1Client(_mh, _mv)
            r = atom.adt_delete(name="ZTEST_OBJ", object_type="class", transport="TRK900001")
            ok = (r.get("delete_verified") is bekl_dv) and (r.get("ok") is bekl_ok)
            kontrol(ad, ok, f"ok={r.get('ok')} delete_verified={r.get('delete_verified')!r} "
                            f"sebep={str(r.get('delete_reason', '-'))[:60]}")
    finally:
        atom._get_client, atom.get_active_tier = eski, eski_tier


# =============================================================================
# R2 — adt_push_source: aktivasyon-sonrasi readback (True/False/None)
#      GERCEK `SAPClient.push_object` govdesi kosar (test mantigi YENIDEN UYGULANMAZ).
# =============================================================================
class _R2Adt:
    def __init__(self, aktif_kaynak, kaynak_hatasi=None):
        self.url, self.client, self.user = "https://sap.test", "100", "TESTUSER"
        self._aktif, self._hata = aktif_kaynak, kaynak_hatasi
        self._last_lock_effective_transport = "TRK900001"
        self._last_lock_is_link_up = ""

    def get_transport_info(self, url):
        return "TRK900001"

    def is_object_locked(self, url):
        return {"locked": False}

    def fetch_source_etag(self, url):
        return "etag123"

    def lock_object(self, url, transport=None):
        return "LOCK1"

    def set_object_source(self, url, src, lock, transport, etag=None):
        return True

    def unlock_object(self, url, lock):
        return True

    def activate_object(self, name, url):
        return {"success": True}

    def get_object_source(self, url, return_etag=False, version=None):
        if self._hata is not None:
            raise self._hata
        return self._aktif


class _R2Client:
    def __init__(self, adt):
        self.adt_client, self.debug_enabled = adt, False
        self.local_base = Path(".")

    def _find_existing_transport(self, name, otype, transport):
        return transport

    def push_object(self, object_name, object_type="class", transport=None, source_file=None):
        return SAPClient.push_object(self, object_name=object_name, object_type=object_type,
                                     transport=transport, source_file=source_file)


def r2_push():
    kaynak = "define view entity ZTEST as select from t { key a }"
    vakalar = [
        ("R2 KONTROL readback TUTTU -> readback_verified TRUE + ok TRUE",
         kaynak, None, True, True),
        ("R2 KONTROL sadece BICIM farki -> hala TRUE (pretty-print asiri-sikilasma capasi)",
         "define view entity ZTEST as select from t {   key a }", None, True, True),
        ("R2 BOZUK ICERIK farki -> readback_verified FALSE + ok FALSE (2026-07-28 regresyonu)",
         "define view entity ZTEST as select from t { key BASKA_ALAN }", None, False, False),
        ("R2 BOZUK readback KOSAMADI -> readback_verified None AMA ok TRUE (asiri-siki degil)",
         None, _hata(SAPADTError, "Internal Server Error", 500), None, True),
    ]
    eski, eski_tier = atom._get_client, atom.get_active_tier
    try:
        atom.get_active_tier = lambda: "DEV"
        for ad, aktif, hata, bekl_rb, bekl_ok in vakalar:
            atom._get_client = lambda _a=aktif, _h=hata: _R2Client(_R2Adt(_a, _h))
            r = atom.adt_push_source(name="ZTEST_CDS", object_type="ddls", source=kaynak,
                                     transport="TRK900001", skip_reviewer=True)
            ok = (r.get("readback_verified") is bekl_rb) and (r.get("ok") is bekl_ok)
            if bekl_rb is None:
                ok = ok and bool(r.get("readback_notice"))
            kontrol(ad, ok, f"ok={r.get('ok')} readback_verified={r.get('readback_verified')!r} "
                            f"notice={'VAR' if r.get('readback_notice') else 'yok'}")
    finally:
        atom._get_client, atom.get_active_tier = eski, eski_tier


# =============================================================================
# R3 — ParseError: where_used / ATC / inactive  (bos liste = "temiz" DEGIL)
# =============================================================================
class _R3Adt:
    """GERCEK `SAPADTClient.where_used` / `run_atc_check` / `get_inactive_objects` govdeleri."""

    def __init__(self, govdeler):
        self.url = "https://sap.test"
        self._govdeler = list(govdeler)
        self._debug_kayit = []

    def _get_headers(self, accept, ctype=None):
        return {}

    def _debug(self, msg):
        self._debug_kayit.append(msg)

    def _request_with_csrf_retry(self, method, url, **kw):
        class _Cevap:
            def __init__(_s, metin, kod=200):
                _s.text, _s.status_code = metin, kod
        return _Cevap(self._govdeler.pop(0))

    where_used = SAPADTClient.where_used
    run_atc_check = SAPADTClient.run_atc_check
    get_inactive_objects = SAPADTClient.get_inactive_objects


WU_DOLU = ('<?xml version="1.0"?><usageReferences xmlns:adtcore="http://www.sap.com/adt/core">'
           '<referencedObject uri="/sap/bc/adt/oo/classes/zcl_x">'
           '<adtObject name="ZCL_X" type="CLAS/OC" description="tuketici"/>'
           '</referencedObject></usageReferences>')
WU_BOS = '<?xml version="1.0"?><usageReferences/>'
BOZUK = '<?xml version="1.0"?><usageReferences><referencedObject '   # kapanmamis


def r3_parse():
    # --- where_used ---
    a = _R3Adt([WU_DOLU])
    kontrol("R3 KONTROL where_used dolu XML -> 1 referans", len(a.where_used("/u")) == 1)
    a = _R3Adt([WU_BOS])
    kontrol("R3 KONTROL where_used GECERLI-BOS -> [] ('tuketicisi yok' MESRU)",
            a.where_used("/u") == [])
    a = _R3Adt([BOZUK])
    try:
        r = a.where_used("/u")
        kontrol("R3 BOZUK where_used ayristirilamaz -> HATA (bos liste DEGIL)", False,
                f"istisna atilmadi, donen={r!r}")
    except SAPADTError as e:
        kontrol("R3 BOZUK where_used ayristirilamaz -> HATA (bos liste DEGIL)", True, str(e)[:70])

    # --- ATC (3 istek: worklist / run / sonuc) ---
    atc_dolu = ('<atc:worklist xmlns:atc="http://www.sap.com/adt/atc">'
                '<finding priority="1" messageTitle="Prio1 bulgu" checkId="X"/></atc:worklist>')
    atc_bos = '<atc:worklist xmlns:atc="http://www.sap.com/adt/atc"/>'
    run_ok = '<atc:run xmlns:atc="http://www.sap.com/adt/atc" worklistId="WL1"/>'

    a = _R3Adt(["WL1", run_ok, atc_dolu])
    kontrol("R3 KONTROL ATC dolu -> 1 bulgu", len(a.run_atc_check("/u")["findings"]) == 1)
    a = _R3Adt(["WL1", run_ok, atc_bos])
    res = a.run_atc_check("/u")
    kontrol("R3 KONTROL ATC gercekten temiz -> 0 bulgu + fallback isareti YOK",
            res["findings"] == [] and not res.get("worklist_parse_fallback"))
    a = _R3Adt(["WL1", run_ok, BOZUK])
    try:
        a.run_atc_check("/u")
        kontrol("R3 BOZUK ATC sonucu ayristirilamaz -> HATA ('temiz' DEGIL)", False,
                "istisna atilmadi")
    except SAPADTError as e:
        kontrol("R3 BOZUK ATC sonucu ayristirilamaz -> HATA ('temiz' DEGIL)", True, str(e)[:60])
    a = _R3Adt(["WL1", BOZUK, atc_bos])
    res = a.run_atc_check("/u")
    kontrol("R3 BOZUK ATC run-yaniti ayristirilamaz -> worklist_parse_fallback ISARETI",
            res.get("worklist_parse_fallback") is True, f"res={res}")

    # --- inactive objects (gun-sonu/commit gate'inin besledigi uc) ---
    io_dolu = ('<ioc xmlns:adtcore="http://www.sap.com/adt/core">'
               '<entry adtcore:name="ZCL_Y" adtcore:type="CLAS/OC" adtcore:uri="/u"/></ioc>')
    a = _R3Adt([io_dolu])
    kontrol("R3 KONTROL inactive dolu -> 1 kayit", len(a.get_inactive_objects()) == 1)
    a = _R3Adt([BOZUK])
    try:
        a.get_inactive_objects()
        kontrol("R3 BOZUK inactive ayristirilamaz -> HATA ('bekleyen yok' DEGIL)", False,
                "istisna atilmadi")
    except SAPADTError:
        kontrol("R3 BOZUK inactive ayristirilamaz -> HATA ('bekleyen yok' DEGIL)", True)

    # --- MCP tool katmani: hata yapilandirilmis cikmali, count:0 DEGIL ---
    class _WuClient:
        def __init__(self, adt):
            self.adt_client = adt

        def object_exists(self, name, otype):
            return True

    eski = query._get_client
    try:
        query._get_client = lambda: _WuClient(_R3Adt([BOZUK]))
        r = query.adt_where_used(name="ZCL_X", object_type="class")
        kontrol("R3 KABLOLAMA adt_where_used bozuk XML -> ok:false + 'count' ANAHTARI YOK",
                r.get("ok") is False and "count" not in r,
                f"ok={r.get('ok')} count={r.get('count', 'YOK')} error={r.get('error')}")
        query._get_client = lambda: _WuClient(_R3Adt([WU_BOS]))
        r = query.adt_where_used(name="ZCL_X", object_type="class")
        kontrol("R3 KONTROL adt_where_used gercekten-bos -> ok:true + count:0 (korunmali)",
                r.get("ok") is True and r.get("count") == 0, f"{r.get('ok')}/{r.get('count')}")
    finally:
        query._get_client = eski

    # --- 3. BAGLAM: CLI sarmalayici (sap_client.list_inactive_objects) None dondurur ---
    class _CliClient:
        def __init__(self, adt):
            self.adt_client = adt

        def list_inactive_objects(self):
            return SAPClient.list_inactive_objects(self)

    c = _CliClient(_R3Adt([BOZUK]))
    with contextlib.redirect_stdout(io.StringIO()):
        v = c.list_inactive_objects()
    kontrol("R3 3.BAGLAM CLI sarmalayici: bozuk XML -> None ([] DEGIL)", v is None, f"donen={v!r}")


# =============================================================================
# R4 — SystemExit sizintisi: CLI idiomu kutuphane yolunda tool'u sessizce oldururdu
# =============================================================================
class _R4Session:
    def __init__(self, token):
        self._token = token

    def get(self, url, **kw):
        class _C:
            pass
        c = _C()
        c.headers = {"X-CSRF-Token": self._token} if self._token else {}
        c.status_code = 200 if self._token else 403
        c.text = "" if self._token else "logon failed"
        return c

    def post(self, url, **kw):
        class _C:
            status_code, text = 200, "<ok/>"
        return _C()


class _R4Adt:
    def __init__(self, token):
        self.url, self.client = "https://sap.test", "100"
        self.session = _R4Session(token)

    def _invalidate_csrf_cache(self):
        return None


class _R4Client:
    def __init__(self, token):
        self.adt_client = _R4Adt(token)


def r4_systemexit():
    eski, eski_tier = atom._get_client, atom.get_active_tier
    try:
        atom.get_active_tier = lambda: "DEV"
        atom._get_client = lambda: _R4Client("TOK123")
        r = atom.adt_publish_service(name="ZTEST_UI_O2")
        kontrol("R4 KONTROL CSRF alindi -> published TRUE (calisan yol bozulmadi)",
                r.get("ok") is True and r.get("published") is True,
                f"{r.get('ok')}/{r.get('status_code')}")

        atom._get_client = lambda: _R4Client("")
        try:
            r = atom.adt_publish_service(name="ZTEST_UI_O2")
            kontrol("R4 BOZUK CSRF yok -> tool YAPILANDIRILMIS ok:false donmeli (SystemExit kacmamali)",
                    isinstance(r, dict) and r.get("ok") is False, f"donen={str(r)[:90]}")
        except BaseException as exc:                       # noqa: BLE001 — olculen sey TAM BU
            kontrol("R4 BOZUK CSRF yok -> tool YAPILANDIRILMIS ok:false donmeli (SystemExit kacmamali)",
                    False, f"{type(exc).__name__} KACTI: {exc}")
    finally:
        atom._get_client, atom.get_active_tier = eski, eski_tier

    # --- 3. BAGLAM (statik, gorev-disi kapsam): mcp_servers'in scripts/'ten import ettigi
    # HICBIR fonksiyon SystemExit/sys.exit ATMAMALI. Sinif-kurali; yeni sizinti eklenirse
    # bu satir kirilir (vaka-ozel yama degil).
    hedefler: dict[str, set[str]] = {}
    for py in (REPO / "mcp_servers").rglob("*.py"):
        try:
            agac = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for d in ast.walk(agac):
            if isinstance(d, ast.ImportFrom) and d.module:
                kok = d.module.split(".")[0]
                if (REPO / "scripts" / f"{kok}.py").is_file():
                    hedefler.setdefault(kok, set()).update(a.name for a in d.names)

    sizintilar = []
    for modul, adlar in sorted(hedefler.items()):
        agac = ast.parse((REPO / "scripts" / f"{modul}.py").read_text(encoding="utf-8",
                                                                     errors="replace"))
        for fn in ast.walk(agac):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name not in adlar:
                continue
            for d in ast.walk(fn):
                if isinstance(d, ast.Raise) and isinstance(d.exc, ast.Call) \
                        and getattr(d.exc.func, "id", "") == "SystemExit":
                    sizintilar.append(f"{modul}.{fn.name}:{d.lineno} raise SystemExit")
                if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "exit" \
                        and getattr(getattr(d.func, "value", None), "id", "") == "sys":
                    sizintilar.append(f"{modul}.{fn.name}:{d.lineno} sys.exit()")
    kontrol("R4 3.BAGLAM statik: MCP'nin import ettigi fonksiyonlarda SystemExit YOK",
            not sizintilar,
            f"taranan modul={sorted(hedefler)} sizinti={sizintilar}")


# =============================================================================
# R5 — package_contents: paket-uyeligi DOGRULANDI mi?
# =============================================================================
NODE_XML = ('<asx:abap xmlns:asx="http://www.sap.com/abapxml">'
            '<SEU_ADT_REPOSITORY_OBJ_NODE><OBJECT_TYPE>CLAS/OC</OBJECT_TYPE>'
            '<OBJECT_NAME>ZSD001_CL_GERCEK</OBJECT_NAME><DESCRIPTION>d</DESCRIPTION>'
            '</SEU_ADT_REPOSITORY_OBJ_NODE></asx:abap>')


class _R5Client:
    """GERCEK `SAPClient.list_package_contents` govdesi (fallback dali dahil)."""

    def __init__(self, node_calisiyor):
        self._node = node_calisiyor
        self.debug_enabled = False

        class _Adt:
            def get_package_contents(_s, pkg):
                if not node_calisiyor:
                    raise Exception("HTTP 500 nodestructure (S_ADT_RES yok)")
                return NODE_XML
        self.adt_client = _Adt()

    def search_objects(self, pattern, max_results=500, debug_context=None):
        # Gercek dunyadaki yayilim: paket adindan turetilen GENIS joker ('ZS*') BASKA
        # paketlerin objelerini getirir; eskiden bu, gercek paket icerigiyle ayni kaba giriyordu.
        if pattern.startswith("ZSD001_CLC"):
            return [{"name": "ZSD001_CLC_X", "type": "CLAS/OC", "uri": "/u", "description": ""}]
        return [{"name": "ZSD000_CL_BASKA_PAKET", "type": "CLAS/OC", "uri": "/u2",
                 "description": "BASKA PAKETIN OBJESI"}]

    def list_package_contents(self, pkg):
        return SAPClient.list_package_contents(self, pkg)


def r5_paket():
    eski = query._get_client
    try:
        query._get_client = lambda: _R5Client(True)
        r = query.adt_package_contents(package="ZSD001_CLC")
        kontrol("R5 KONTROL nodestructure calisti -> package_verified TRUE + uyari YOK",
                r.get("ok") is True and r.get("package_verified") is True and "warning" not in r,
                f"verified={r.get('package_verified')} count={r.get('count')}")

        query._get_client = lambda: _R5Client(False)
        r = query.adt_package_contents(package="ZSD001_CLC")
        yabanci = [o["name"] for o in r.get("objects", []) if "ZSD000" in o.get("name", "")]
        kontrol("R5 BOZUK fallback -> package_verified FALSE + uyari (yabanci obje ISARETLI)",
                r.get("package_verified") is False and bool(r.get("warning")) and bool(yabanci),
                f"verified={r.get('package_verified')} yabanci={yabanci}")

        # KABLOLAMA: adt_grep_source ayni sinyali TUKETMELI (eskiden log'u bile yutuyordu).
        eski_get = atom.adt_get
        try:
            atom.adt_get = lambda name, object_type="class", include_source=True: {
                "ok": True, "exists": True, "source": "DATA lv_x TYPE string."}
            query._get_client = lambda: _R5Client(False)
            g = query.adt_grep_source(pattern="lv_x", package="ZSD001_CLC")
            kontrol("R5 KABLOLAMA adt_grep_source fallback kapsaminda -> scope_verified FALSE + uyari",
                    g.get("scope_verified") is False and bool(g.get("scope_warning")),
                    f"scope_verified={g.get('scope_verified')} taranan={g.get('scanned_objects')}")
            query._get_client = lambda: _R5Client(True)
            g = query.adt_grep_source(pattern="lv_x", package="ZSD001_CLC")
            kontrol("R5 KONTROL grep gercek paket-ucu -> scope_verified TRUE + uyari YOK",
                    g.get("scope_verified") is True and "scope_warning" not in g,
                    f"scope_verified={g.get('scope_verified')}")
        finally:
            atom.adt_get = eski_get
    finally:
        query._get_client = eski


# =============================================================================
# 3. BAGLAM (gorev-disi tool): adt_lock_check ayni sinifin 6. ornegiydi
# =============================================================================
def ucuncu_baglam_lock():
    eski = query._get_client
    try:
        query._get_client = lambda: _R1Client(_hata(SAPADTError, "Internal Server Error", 500))
        r = query.adt_lock_check(name="ZCL_X", object_type="class")
        kontrol("3.BAGLAM adt_lock_check HTTP 500 -> ok:false (exists:false + locked:false DEGIL)",
                r.get("ok") is False and r.get("locked") is not False,
                f"ok={r.get('ok')} exists={r.get('exists', 'YOK')} locked={r.get('locked', 'YOK')}")
        query._get_client = lambda: _R1Client(
            _hata(SAPADTError, "Failed to get object structure", 404))
        r = query.adt_lock_check(name="ZCL_X", object_type="class")
        kontrol("3.BAGLAM KONTROL adt_lock_check gercek 404 -> exists:false + locked:false (korunmali)",
                r.get("ok") is True and r.get("exists") is False and r.get("locked") is False,
                f"ok={r.get('ok')} exists={r.get('exists')}")
        query._get_client = lambda: _R1Client(None, "<xml>var</xml>")
        r = query.adt_lock_check(name="ZCL_X", object_type="class")
        kontrol("3.BAGLAM KONTROL adt_lock_check obje VAR -> exists:true", r.get("exists") is True)
    finally:
        query._get_client = eski


# =============================================================================
# SINIFLANDIRICI birim vektorleri (tek kaynak: _bos_sonuc_sinifi)
# =============================================================================
def siniflandirici():
    vek = [
        ("[ERROR] [404] Object ZTEST not found", "yok"),
        ("", "yok"),
        ("Fetching dtel: ZTEST\n", "yok"),
        ("[ERROR] [500] Internal Server Error", "belirsiz"),
        ("[ERROR] [403] Forbidden - logon failed", "belirsiz"),
        ("[ERROR] Read timed out", "belirsiz"),
        ("[ERROR] Max retries exceeded", "ulasilamadi"),
        ("[ERROR] NameResolutionError", "ulasilamadi"),
        ("[ERROR] [404] not found; [500] baska hata", "belirsiz"),   # karisikta muhafazakar
    ]
    sapan = [f"{m!r}->{atom._bos_sonuc_sinifi(m)} (bekl {b})"
             for m, b in vek if atom._bos_sonuc_sinifi(m) != b]
    kontrol(f"SINIFLANDIRICI _bos_sonuc_sinifi ({len(vek)} vektor)", not sapan, "; ".join(sapan))


def main() -> int:
    # ⚠ ÇÖKME ≠ FAIL: mutasyon-testinde (fix'ler geri alinmis kod) bir bolum AttributeError
    # ile patlarsa fixture SESSIZCE olur ve "olcum yapildi" sanilir. Her bolum izole edilir;
    # patlayan bolum ADIYLA FAIL yazilir (kanit uretilemedi = basarisiz).
    for bolum in (siniflandirici, r1_delete, r2_push, r3_parse,
                  r4_systemexit, r5_paket, ucuncu_baglam_lock):
        try:
            bolum()
        except BaseException as exc:                        # noqa: BLE001
            kontrol(f"[BOLUM COKTU] {bolum.__name__}", False,
                    f"{type(exc).__name__}: {str(exc)[:160]}")

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad}")
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print(f"         -> {detay}")
    print(f"\n{gecen}/{len(SONUC)} OK")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())

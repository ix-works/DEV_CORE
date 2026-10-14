#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checkrun_sozdizimi fixture — Q360: SALT-OKUR sözdizimi denetimi (ADT checkrun).

NEDEN VAR (2026-10-12)
  MCP `adt_syntax_check` aktivasyon ucuna `preauditRequested` ile POST ediyordu ve temiz
  bekleyen sürümü AKTİVE ediyordu (PATTERN #20). Salt-okur kanal `POST /sap/bc/adt/checkruns
  ?reporters=abapCheckRun` canlıda ölçüldü (DEV, 4 tip: sınıf · FM · tablo · CDS):
    · `version="inactive"` aktivasyon ön denetimiyle AYNI kök hatayı verir.
    · `version="active"` hatalı inaktif sürümü GÖRMEZ (0 mesaj) ⇒ varsayılan inactive.
    · ⛔ İnaktif sürümü olmayan tablo: `status="notProcessed"` + 0 mesaj ⇒ "temiz" DEĞİL.
  `canli/` gövdeleri o ölçümün genericize kopyasıdır (ad/kimlik `ZSD001_*`).

SÖZLEŞME (⚠ RİSK bloğu = kabul ölçütü)
  · Belirsiz/ayrıştırılamayan yanıt = OLCULEMEDI, asla "temiz" değil.
  · Her dönüşte KAPSAM BEYANI: sürüm + reporter + bakılmayanlar.
  · `sap_client.py` push ön-kontrolü (aktivasyon yolu) DEĞİŞMEDİ (AST + metin çapası).
  · MCP bağlantısı TEK sabitte (`_SOZDIZIMI_KAYNAGI`) — geri dönüş "aktivasyon".

KULLANIM
  python tests/fixtures/checkrun_sozdizimi/run.py
  python tests/fixtures/checkrun_sozdizimi/run.py --mutasyon
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
CANLI = BURASI / "canli"
TABAN_SHA = "6b6c11d"
_GIT_KOK = Path(os.environ.get("CHECKRUN_GIT_KOK") or REPO)
_TMP = tempfile.mkdtemp(prefix="checkrun_")
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
SINIF = "/sap/bc/adt/oo/classes/zsd001_cl_ornek"
FM = "/sap/bc/adt/functions/groups/zsd001_fg_ornek/fmodules/zsd001_fm_ornek"
TABLO = "/sap/bc/adt/ddic/tables/zsd001_t_ornek"
CDS = "/sap/bc/adt/ddic/ddl/sources/zsd001_i_ornek"


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


def _oku(ad):
    return (CANLI / ad).read_text(encoding="utf-8")


def bolum_a(L):
    """Ayrıştırıcı — canlı gövdeler."""
    ay = L.checkrun_ayristir
    r = ay(_oku("cls_hatali_inactive.resp.xml"), SINIF)
    h = (r["hatalar"] or [{}])[0]
    ekle("A1 ⭐ sinif hatali inaktif -> hatali + satir/kolon (21,25) + metin",
         r["hukum"] == "hatali" and h.get("line") == 21 and h.get("column") == 25
         and "is unknown" in h.get("message", ""), r)
    r = ay(_oku("cls_temiz_inactive.resp.xml"), SINIF)
    ekle("A2 sinif temiz (processed, 0 mesaj) -> temiz", r["hukum"] == "temiz" and not r["hatalar"], r)
    r = ay(_oku("tab_temiz_inactive.resp.xml"), TABLO)
    ekle("A3 ⭐⛔ SAHTE-YESIL: tablo notProcessed + 0 mesaj -> OLCULEMEDI (temiz DEGIL)",
         r["hukum"] == "OLCULEMEDI" and "notProcessed" in r["sebep"] and r["status"] == "notProcessed", r)
    r = ay(_oku("tab_hatali_inactive.resp.xml"), TABLO)
    h = (r["hatalar"] or [{}])[0]
    ekle("A4 tablo hatali -> hatali + t100 DT/963 + satir 10",
         r["hukum"] == "hatali" and h.get("t100") == "DT/963" and h.get("line") == 10, r)
    r1 = ay(_oku("fm_hatali_inactive.resp.xml"), FM)
    r2 = ay(_oku("cds_hatali_inactive.resp.xml"), CDS)
    ekle("A5 FM + CDS hatali -> hatali (4 tipin hepsi ayristirilir)",
         r1["hukum"] == "hatali" and r2["hukum"] == "hatali"
         and r2["hatalar"][0].get("t100") == "SDDL_PARSER_MSG/010", (r1["hukum"], r2["hukum"]))
    r = ay(_oku("cls_hatali_active.resp.xml"), SINIF, version="active")
    ekle("A6 KAPSAM: active surum 0 mesaj -> temiz AMA kapsam.version='active' basilir",
         r["hukum"] == "temiz" and r["kapsam"]["version"] == "active"
         and r["kapsam"]["reporter"] == "abapCheckRun", r["kapsam"])
    ekle("A7 KAPSAM BEYANI bakilmayanlari adlandirir (ATC/Unit/aktivasyon DEGIL)",
         all(k in r["kapsam"]["bakilan"] for k in ("ATC", "ABAP Unit", "aktivasyon")), r["kapsam"])
    cls = _oku("cls_hatali_inactive.resp.xml")
    belirsiz = {
        "bos": ("", None),
        "bozuk_xml": (cls[:200], None),
        "rapor_yok": ('<chkrun:checkRunReports xmlns:chkrun="http://www.sap.com/adt/checkrun"/>', None),
        "baska_reporter": (cls.replace('chkrun:reporter="abapCheckRun"', 'chkrun:reporter="tools.x"'), None),
        "taninmayan_tip": (cls.replace('chkrun:type="E"', 'chkrun:type="Q"'), None),
        "baska_obje": (cls, "/sap/bc/adt/oo/classes/zsd001_cl_baska"),
    }
    sonuc = {k: ay(g, u or SINIF)["hukum"] for k, (g, u) in belirsiz.items()}
    ekle("A8 ⭐ belirsiz 6 vaka (bos/bozuk/rapor yok/baska reporter/taninmayan tip/baska obje) -> OLCULEMEDI",
         set(sonuc.values()) == {"OLCULEMEDI"}, sonuc)


def bolum_b(L):
    """İstek — gövde birebir canlı + uç/parametre/başlık."""
    govde = L.checkrun_govdesi(SINIF)
    ekle("B1 ⭐ istek govdesi canlida OLCULEN biçimle BIREBIR (version=inactive varsayilan)",
         govde == _oku("cls_hatali_inactive.req.xml"), govde)
    ekle("B2 /source/main ile verilen URI kok URI'ye indirgenir",
         L.checkrun_govdesi(SINIF + "/source/main") == govde, "")
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.url, c.client, c.user, c.password = "http://sahte.invalid", "001", "SAP_USER_A", "x"
    c._auth_provider, c.csrf_token, c.debug_enabled = None, None, False
    istek = {}

    class _Y:
        status_code, text, headers = 200, _oku("cls_hatali_inactive.resp.xml"), {}

    def _rq(method, url, headers=None, data=None, params=None, **kw):
        istek.update(method=method, url=url, headers=dict(headers or {}), data=data, params=dict(params or {}))
        return _Y()
    c._request_with_csrf_retry = _rq
    r, exc = _sessiz(c.check_run, SINIF)
    hd = istek.get("headers", {})
    ekle("B3 ⭐ check_run: POST /checkruns + reporters=abapCheckRun + Content-Type/Accept canli bicim",
         istek.get("method") == "post" and istek.get("url", "").endswith("/sap/bc/adt/checkruns")
         and istek.get("params") == {"reporters": "abapCheckRun"}
         and hd.get("Content-Type") == "application/vnd.sap.adt.checkobjects+xml"
         and hd.get("Accept") == "application/vnd.sap.adt.checkmessages+xml"
         and (r or {}).get("hukum") == "hatali", f"{istek.get('url')} {istek.get('params')} {hd} exc={exc!r}")
    ekle("B4 check_run ACTIVATION ucuna GITMEZ (salt-okur)", "/activation" not in istek.get("url", ""), "")

    def _patlar(*a, **k):
        raise ConnectionError("sahte ag hatasi")
    c._request_with_csrf_retry = _patlar
    r, exc = _sessiz(c.check_run, SINIF)
    ekle("B5 ag istisnasi -> OLCULEMEDI (istisna firlatmaz, temiz DEMEZ)",
         exc is None and r["hukum"] == "OLCULEMEDI" and r["sebep"].startswith("istisna:"), r)

    # B7 (bug-gate 2026-10-14): çağrı yerindeki HEDEF BAĞLAMASI. B3'ün gövdesi zaten SINIF'ı
    # raporladığı için `checkrun_ayristir(r.text, None, …)` mutantı B3'ü GEÇİYORDU. Burada başka
    # bir obje denetlenir ama SAP SINIF'ın raporunu döner ⇒ hedef bağlıysa OLCULEMEDI.
    baska = "/sap/bc/adt/oo/classes/zsd001_cl_baska"
    c._request_with_csrf_retry = _rq
    r, exc = _sessiz(c.check_run, baska)
    ekle("B7 ⭐ check_run baska obje icin cagrilip SINIF raporu gelirse -> OLCULEMEDI/obje_raporlanmadi "
         "(beklenen URI cagri yerinde baglanir)",
         exc is None and r["hukum"] == "OLCULEMEDI" and r["sebep"] == "obje_raporlanmadi"
         and r["http_status"] == 200, r if r else repr(exc))

    class _Y500:
        status_code, text, headers = 500, "<html>hata</html>", {}
    c._request_with_csrf_retry = lambda *a, **k: _Y500()
    r, exc = _sessiz(c.check_run, SINIF)
    ekle("B6 HTTP 500 -> OLCULEMEDI + sebep http_500 (govde ayristirilmaz) + http_status",
         r["hukum"] == "OLCULEMEDI" and r["sebep"] == "http_500" and r["http_status"] == 500, r)


def bolum_m(Q, CONN):
    """MCP — `adt_syntax_check` checkrun'a bağlı, guard'lar korunmuş."""
    CONN.get_active_tier = lambda: "DEV"
    gonderilen = []

    class _Adt:
        def __init__(self, govde):
            self.govde = govde

        def check_run(self, url, version="inactive"):
            gonderilen.append((url, version))
            import sap_adt_lib as L
            return L.checkrun_ayristir(self.govde, url, version)

        def syntax_check_via_activation(self, *a, **k):
            raise AssertionError("aktivasyon yolu CAGRILMAMALI")

    class _Ist:
        def __init__(self, govde):
            self.adt_client = _Adt(govde)

        def syntax_check(self, *a, **k):
            raise AssertionError("aktivasyon yolu CAGRILMAMALI")

    def mcp(govde, ad="ZSD001_CL_ORNEK", tip="class"):
        Q._get_client = lambda: _Ist(govde)
        r, exc = _sessiz(Q.adt_syntax_check, name=ad, object_type=tip)
        return r if r is not None else {"_istisna": repr(exc)}

    ekle("M0 varsayilan kaynak 'checkrun'", Q._SOZDIZIMI_KAYNAGI == "checkrun", Q._SOZDIZIMI_KAYNAGI)
    r = mcp(_oku("cls_hatali_inactive.resp.xml"))
    ekle("M1 ⭐ MCP hatali -> ok True + valid False + source checkrun + scope.version inactive",
         r.get("ok") is True and r.get("valid") is False and r.get("source") == "checkrun"
         and (r.get("scope") or {}).get("version") == "inactive" and gonderilen[-1][1] == "inactive", r)
    r = mcp(_oku("cls_temiz_inactive.resp.xml"))
    ekle("M2 MCP temiz -> ok True + valid True", r.get("ok") is True and r.get("valid") is True, r)
    r = mcp(_oku("tab_temiz_inactive.resp.xml"), "ZSD001_T_ORNEK", "table")
    ekle("M3 ⭐⛔ MCP notProcessed -> ok False + sozdizimi_belirsiz + valid None (temiz DEGIL)",
         r.get("ok") is False and r.get("error") == "sozdizimi_belirsiz" and r.get("valid") is None
         and "notProcessed" in (r.get("valid_reason") or ""), r)
    CONN.get_active_tier = lambda: "PRD"
    r = mcp(_oku("cls_temiz_inactive.resp.xml"))
    ekle("M4 tier guard KORUNDU (PRD -> ADR_0010_TIER)", r.get("code") == "ADR_0010_TIER", r)
    CONN.get_active_tier = lambda: "DEV"
    r = mcp(_oku("cls_temiz_inactive.resp.xml"), "CL_GUI_ALV_GRID")
    ekle("M5 namespace guard KORUNDU (standart obje -> ADR_0005_A)", r.get("code") == "ADR_0005_A", r)
    ozet = ((Q.adt_syntax_check.__doc__ or "").strip().splitlines() or [""])[0]
    ekle("M6 docstring ozet satiri SALT-OKUR checkrun + geri donus YAN ETKILI der",
         "SALT-OKUR" in ozet and "YAN ETK" in ozet, ozet)


def bolum_s():
    """`sap_client` push ön-kontrolü aktivasyon yolunda KALDI (kayıt önlemi)."""
    yol = REPO / "scripts" / "sap_client.py"
    metin = yol.read_text(encoding="utf-8")
    agac = ast.parse(metin)
    sx = next((f for f in ast.walk(agac) if isinstance(f, ast.FunctionDef) and f.name == "syntax_check"), None)
    cagrilar = {n.func.attr for n in ast.walk(sx) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)} if sx else set()
    ekle("S1 ⭐ sap_client.syntax_check HALA syntax_check_via_activation cagiriyor, check_run DEGIL",
         "syntax_check_via_activation" in cagrilar and "check_run" not in cagrilar, sorted(cagrilar)[:12])
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:scripts/sap_client.py"],
                       capture_output=True)
    if g.returncode != 0:
        ekle("S2 KONTROL taban sap_client okunamadi (OLCULEMEDI)", False, "")
        return
    taban = g.stdout.decode("utf-8")

    def _gov(src):
        a = ast.parse(src)
        f = next(f for f in ast.walk(a) if isinstance(f, ast.FunctionDef) and f.name == "syntax_check")
        return ast.dump(f)
    ekle("S2 ⭐ sap_client.syntax_check govdesi taban 6b6c11d ile AST-BIREBIR",
         _gov(metin) == _gov(taban), "")


def main() -> int:
    L = _imp("sap_adt_lib")
    Q = _imp("mcp_servers.sap_adt.tools.query")
    CONN = _imp("mcp_servers.sap_adt._conn")
    eski = (CONN.get_active_tier, Q._get_client)
    for fn, a in ((bolum_a, (L,)), (bolum_b, (L,)), (bolum_m, (Q, CONN)), (bolum_s, ())):
        try:
            fn(*a)
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle(f"[BOLUM COKTU] {fn.__name__}", False, f"{type(exc).__name__}: {exc}")
    CONN.get_active_tier, Q._get_client = eski
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


MUTASYONLAR = [
    ("M1 notProcessed temiz sayilir", "scripts/sap_adt_lib.py",
     "        if durum != 'processed':\n", "        if False:\n"),
    ("M2 varsayilan surum active", "scripts/sap_adt_lib.py",
     "def checkrun_govdesi(object_uri, version='inactive'):", "def checkrun_govdesi(object_uri, version='active'):"),
    ("M3 bos govde temiz sayilir", "scripts/sap_adt_lib.py",
     "        sonuc['sebep'] = 'bos_govde'\n        return sonuc\n",
     "        sonuc['sebep'] = 'bos_govde'\n        sonuc['hukum'] = 'temiz'\n        return sonuc\n"),
    ("M4 taninmayan tip sessizce uyari sayilir", "scripts/sap_adt_lib.py",
     "            if tip not in CHECKRUN_BILINEN_TIPLER:\n", "            if False:\n"),
    ("M5 MCP aktivasyon yoluna geri baglanir", "mcp_servers/sap_adt/tools/query.py",
     '_SOZDIZIMI_KAYNAGI = "checkrun"\n', '_SOZDIZIMI_KAYNAGI = "aktivasyon"\n'),
    ("M6 baska objenin raporu kabul edilir", "scripts/sap_adt_lib.py",
     "        if not bizim:\n            sonuc['sebep'] = 'obje_raporlanmadi'\n",
     "        if False:\n            sonuc['sebep'] = 'obje_raporlanmadi'\n"),
    ("M7 HTTP 2xx-disi ayristiriciya yollanir", "scripts/sap_adt_lib.py",
     "        if kod != 200:\n            sonuc = checkrun_ayristir('', object_url, version)\n",
     "        if False:\n            sonuc = checkrun_ayristir('', object_url, version)\n"),
    ("M8 check_run cagri yerinde hedef URI baglanmaz (None)", "scripts/sap_adt_lib.py",
     "        sonuc = checkrun_ayristir(r.text, object_url, version)\n",
     "        sonuc = checkrun_ayristir(r.text, None, version)\n"),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="checkrun_kum_"))
    kotu = []
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        env = dict(os.environ)
        env["CHECKRUN_GIT_KOK"] = str(REPO)
        for ad, yol, eski, yeni in MUTASYONLAR:
            dosya = kok / yol
            asil = dosya.read_bytes().decode("utf-8")
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez")
                kotu.append(ad)
                continue
            dosya.write_bytes(asil.replace(eski, yeni, 1).encode("utf-8"))
            try:
                r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=300,
                                   cwd=str(kok), env=env)
            finally:
                dosya.write_bytes(asil.encode("utf-8"))
            m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
            durum = "COKTU" if not m else ("YAKALANDI" if r.returncode else "KACTI")
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

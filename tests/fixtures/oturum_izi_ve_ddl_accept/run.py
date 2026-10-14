#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oturum_izi_ve_ddl_accept fixture — Q364 (2026-10-12): ② oturum izi + kilitli akış oturum
sürekliliği · ① tablo DDL GET biçim kilidi.

NEDEN VAR
  ② Hipotez: uzun MCP sürecinde yeni objede 400 → oturum (`sap-contextid`) bayatlığı; çare
    olarak `new_session()` önerilir. AMA kilit ve CSRF OTURUMA BAĞLIDIR: kilit → PUT → bırakma
    ortasında oturum yenilenirse kilit sahipsiz kalır, PUT 423 ile düşer. Bu tur YALNIZ ÖLÇÜM:
    `ADT_SESSION_TRACE=1` (stderr, maskeli) eklendi; `new_session()` davranışı DEĞİŞMEDİ.
    Bu fixture iki şeyi kilitler:
      · O — GERÇEK lib kodu (lock_object → set_object_source → unlock_object) yerel sahte HTTP
        sunucuya karşı koşar; üç adım da AYNI oturum çerezini taşır. Ortaya `new_session()`
        sokan mutasyon FAIL olur.
      · T — iz: kapalıyken HİÇ satır yok + kanca eklenmez; açıkken her yanıtta tek satır, ham
        çerez değeri / kilit tutamacı / transport ASLA görünmez.
  ① Tablo/yapı DDL kaynağı: `GET /sap/bc/adt/ddic/{tables|structures}/<ad>/source/main` +
    `Accept: text/plain` (dış kaynakta on-prem'de çalışan biçimle aynı). Kod zaten bu biçimde;
    D bölümü biçimi kilitler (Accept değişirse FAIL).

  Uzun oturumda 400'ün kendisi (② canlı ayağı) bu fixture'ın KAPSAMINDA DEĞİL — SAP bağlantısı
  gerektirir; DOĞRULANAMADI olarak raporlanır.

KULLANIM
  python tests/fixtures/oturum_izi_ve_ddl_accept/run.py
  python tests/fixtures/oturum_izi_ve_ddl_accept/run.py --mutasyon
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
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
_TMP = tempfile.mkdtemp(prefix="oturum_izi_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
os.environ.pop("ADT_SESSION_TRACE", None)
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
URL = "/sap/bc/adt/oo/classes/zsd001_cl_ornek"
TRANSPORT = "NPLK900001"
KILIT = "LHGIZLI0001"


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:400]))


def _yakala(fn, *a, **k):
    """stdout+stderr yakala; istisna ÖLÇÜLÜR (çökme != FAIL)."""
    eski = (sys.stdout, sys.stderr)
    out, err = io.StringIO(), io.StringIO()
    sys.stdout, sys.stderr = out, err
    try:
        try:
            return fn(*a, **k), None, out.getvalue(), err.getvalue()
        except Exception as exc:                      # noqa: BLE001
            return None, exc, out.getvalue(), err.getvalue()
    finally:
        sys.stdout, sys.stderr = eski


# ─────────────────────────────────────────────────────────────────────────────
# Sahte SAP: çerezsiz gelen her isteğe YENİ oturum verir; her isteğin oturumunu kaydeder.
# ─────────────────────────────────────────────────────────────────────────────
class _Sunucu(BaseHTTPRequestHandler):
    sayac = 0
    olaylar: list = []

    def _oturum(self):
        m = re.search(r"sap-contextid=([^;\s]+)", self.headers.get("Cookie") or "")
        return m.group(1) if m else None

    def _c(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)
        yol, _, sorgu = self.path.partition("?")
        ctx = self._oturum()
        yeni = None
        if ctx is None:
            _Sunucu.sayac += 1
            yeni = "CTXDEGER%04dGIZLI" % _Sunucu.sayac
        govde = b""
        if self.command == "POST" and "_action=LOCK" in sorgu:
            adim = "LOCK"
            govde = ('<?xml version="1.0" encoding="utf-8"?><asx:abap xmlns:asx="http://www.sap.com/abapxml" '
                     'version="1.0"><asx:values><DATA><LOCK_HANDLE>%s</LOCK_HANDLE><CORRNR>%s</CORRNR>'
                     '<CORRUSER/><CORRTEXT/><IS_LOCAL/><IS_LINK_UP/><MODIFICATION_SUPPORT/></DATA>'
                     '</asx:values></asx:abap>' % (KILIT, TRANSPORT)).encode()
        elif self.command == "POST" and "_action=UNLOCK" in sorgu:
            adim = "UNLOCK"
        elif self.command == "PUT":
            adim = "PUT"
        else:
            adim = "%s %s" % (self.command, yol)
        _Sunucu.olaylar.append({"adim": adim, "ctx": ctx, "yeni": yeni, "sorgu": sorgu})
        self.send_response(200)
        if yeni:
            self.send_header("Set-Cookie", "sap-contextid=%s; path=/" % yeni)
            self.send_header("Set-Cookie", "SAP_SESSIONID_NPL_100=SID%sGIZLI; path=/" % yeni)
        self.send_header("x-csrf-token", "SAHTE")
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        if govde:
            self.wfile.write(govde)

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _c

    def log_message(self, *a):
        pass


def _istemci(L, kok):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c._auth_provider = None
    c.user, c.password = "SAP_USER_A", "x"
    c.client, c.language = "100", "TR"
    c.csrf_token = "SAHTE"
    c.cookies = None
    c.debug_enabled = False
    c.timeout_short = c.timeout_default = 5
    c.url = kok
    c.session = c._build_session()
    return c


def _akis(L, kok):
    """GERÇEK lib: lock → PUT → unlock. Dönüş: (olaylar, stderr, hata)."""
    _Sunucu.olaylar, _Sunucu.sayac = [], 0
    c = _istemci(L, kok)

    def _kos():
        h = c.lock_object(URL, transport=TRANSPORT)
        c.set_object_source(URL, "CLASS zsd001_cl_ornek DEFINITION.\nENDCLASS.\n", h,
                            transport=TRANSPORT, etag="ETAG-1")
        return c.unlock_object(URL, h)

    r, exc, out, err = _yakala(_kos)
    return list(_Sunucu.olaylar), out + err, exc, r, c


def bolum_o_t(L):
    srv = HTTPServer(("127.0.0.1", 0), _Sunucu)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    kok = "http://127.0.0.1:%d" % srv.server_address[1]
    try:
        # ── O: oturum sürekliliği (iz KAPALI) ──────────────────────────────────
        os.environ.pop("ADT_SESSION_TRACE", None)
        ol, cikti, exc, r, c = _akis(L, kok)
        adimlar = [o["adim"] for o in ol]
        ekle("O0 akis kostu: LOCK, PUT, UNLOCK sirayla sunucuya ulasti (cokme yok)",
             exc is None and {"LOCK", "PUT", "UNLOCK"} <= set(adimlar)
             and adimlar.index("LOCK") < adimlar.index("PUT") < adimlar.index("UNLOCK"),
             f"exc={exc!r} adimlar={adimlar}")
        yeni_oturum = [o for o in ol if o["yeni"]]
        kilitten_sonra = ol[[o["adim"] for o in ol].index("LOCK"):] if "LOCK" in adimlar else []
        ctx_kume = {o["ctx"] or o["yeni"] for o in kilitten_sonra}
        ekle("O1 ⭐ kilit -> PUT -> birakma TEK oturum (sunucu tek oturum acti, tum adimlar ayni cerez)",
             len(yeni_oturum) == 1 and len(ctx_kume) == 1,
             f"acilan_oturum={len(yeni_oturum)} kilit_sonrasi_oturumlar={len(ctx_kume)} adimlar={adimlar}")
        ekle("O2 KONTROL: unlock dogru (True) + kilit tutamaci PUT ve UNLOCK sorgusunda",
             r is True and all(KILIT in o["sorgu"] for o in ol if o["adim"] in ("PUT", "UNLOCK")),
             f"donus={r!r}")
        ekle("O3 iz KAPALI: hic [ADT-OTURUM] satiri yok + kanca EKLENMEDI (davranis eskisi)",
             L.OTURUM_IZI_ONEKI not in cikti and not c.session.hooks.get("response"),
             f"kanca={c.session.hooks.get('response')}")

        # ── T: iz AÇIK ───────────────────────────────────────────────────────
        os.environ["ADT_SESSION_TRACE"] = "1"
        try:
            ol2, cikti2, exc2, r2, c2 = _akis(L, kok)
        finally:
            os.environ.pop("ADT_SESSION_TRACE", None)
        satirlar = [s for s in cikti2.splitlines() if s.startswith(L.OTURUM_IZI_ONEKI)]
        ekle("T1 iz ACIK: her yaniT icin TEK satir (satir sayisi = istek sayisi)",
             exc2 is None and len(satirlar) == len(ol2) and len(ol2) >= 3,
             f"satir={len(satirlar)} istek={len(ol2)} exc={exc2!r}")
        sizan = [s for s in satirlar if "GIZLI" in s or TRANSPORT in s or KILIT in s]
        ekle("T2 ⭐ ham cerez / kilit tutamaci / transport iz satirinda YOK (yalniz sha8)",
             satirlar and not sizan, sizan[:2])
        ozet = [re.search(r"istek-cerez=(\S+)", s).group(1) for s in satirlar]
        nesil = {re.search(r"nesil=(\d+)", s).group(1) for s in satirlar}
        ekle("T3 iz oturumu gosterir: tek nesil + ilk istek '-' ve sonrakiler AYNI ozet",
             len(nesil) == 1 and ozet[0] == "-" and len(set(ozet[1:])) == 1
             and re.fullmatch(r"(SAP_SESSIONID_NPL_100=[0-9a-f]{8},)?sap-contextid=[0-9a-f]{8}",
                              ozet[1] or "") is not None,
             f"nesil={nesil} ozet={ozet}")
        ekle("T4 KONTROL: iz ACIKKEN de akis ayni (tek oturum, unlock True)",
             r2 is True and len({o["ctx"] or o["yeni"] for o in ol2}) == 1, f"donus={r2!r}")
        # new_session nesli artırır — iz bunu görünür kılar (davranış DEĞİŞMEDİ, yalnız sayaç)
        os.environ["ADT_SESSION_TRACE"] = "1"
        try:
            _, _, _, _ = _yakala(c2.new_session)
            _, _, out3, err3 = _yakala(c2.session.get, kok + "/sap/bc/adt/discovery", timeout=5)
        finally:
            os.environ.pop("ADT_SESSION_TRACE", None)
        ekle("T5 new_session sonrasi iz nesil=2 + istek cerezsiz ('-') -> oturum yenilenmesi IZDE gorunur",
             re.search(r"nesil=2 GET /sap/bc/adt/discovery -> 200 istek-cerez=- ", out3 + err3) is not None,
             (out3 + err3).strip()[:200])
        # kanca hatası isteği bozmaz
        kanca = L._oturum_izi_kancasi(1)
        bozuk = types.SimpleNamespace(request=None, cookies=[], status_code=200)
        r5, exc5, _, _ = _yakala(kanca, bozuk)
        ekle("T6 bozuk yanit nesnesinde kanca istisna ATMAZ ve yaniti geri verir",
             exc5 is None and r5 is bozuk, f"exc={exc5!r}")
    finally:
        srv.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# D — tablo/yapı DDL GET biçimi (Q364①)
# ─────────────────────────────────────────────────────────────────────────────
class _Yanit:
    def __init__(self, kod, metin):
        self.status_code, self.text = kod, metin


class _Oturum:
    def __init__(self):
        self.istekler = []

    def get(self, url, headers=None, **kw):
        self.istekler.append((url, dict(headers or {})))
        return _Yanit(200, "@EndUserText.label : 'Ornek'\ndefine table zsd001_t_ornek {\n  key mandt : mandt not null;\n}\n")


class _Adt:
    def __init__(self, oturum):
        self.url, self.session = "https://sap.example.test:44300", oturum


class _Istemci:
    def __init__(self):
        self.session = _Oturum()
        self.adt_client = _Adt(self.session)

    def get_ddic_object(self, *a, **k):
        raise AssertionError("XML yoluna dusuldu")


def bolum_d():
    import importlib
    atom, exc = None, None
    eski = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = io.StringIO()
    try:
        atom = importlib.import_module("mcp_servers.sap_adt.tools.atom")
    except Exception as e:                            # noqa: BLE001
        exc = e
    finally:
        sys.stdout, sys.stderr = eski
    if atom is None:
        ekle("D0 atom import", False, repr(exc))
        return
    for tip, seg in (("table", "ddic/tables"), ("structure", "ddic/structures")):
        c = _Istemci()
        atom._get_client = lambda _c=c: _c
        atom._record_active_binding = lambda _c=None: None
        r, exc, _, _ = _yakala(atom.adt_get, name="ZSD001_T_ORNEK", object_type=tip, include_source=True)
        url, bas = (c.session.istekler[0] if c.session.istekler else ("", {}))
        ekle(f"D1 {tip}: GET .../{seg}/zsd001_t_ornek/source/main (kucuk harf ad)",
             url.endswith(f"/sap/bc/adt/{seg}/zsd001_t_ornek/source/main"), url or f"istek yok exc={exc!r}")
        ekle(f"D2 ⭐ {tip}: Accept TAM OLARAK 'text/plain' (dis kaynakta calisan bicim)",
             bas.get("Accept") == "text/plain", bas)
        ekle(f"D3 {tip}: duz DDL dondu (XML zarfi degil)",
             isinstance(r, dict) and r.get("exists") is True
             and "define table" in (r.get("source") or ""), {k: r.get(k) for k in ("ok", "exists", "error")}
             if isinstance(r, dict) else exc)


def main() -> int:
    import importlib
    L = None
    eski = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = io.StringIO()
    try:
        L = importlib.import_module("sap_adt_lib")
    finally:
        sys.stdout, sys.stderr = eski
    for ad, fn in (("O/T", lambda: bolum_o_t(L)), ("D", bolum_d)):
        try:
            fn()
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle(f"[BOLUM {ad} COKTU]", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print("  [KAPSAM] O/T: yerel sahte HTTP (127.0.0.1), GERCEK lib lock/PUT/unlock; uzun-oturum 400 "
          "canli ayagi OLCULMEDI (SAP yok). D: adt_get table/structure GET bicimi (sahte oturum).")
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


MUTASYONLAR = [
    ("M1 ⭐ RISK: kilit ile PUT arasina new_session() sokulur", "scripts/sap_adt_lib.py",
     "        # Ensure /source/main suffix\n",
     "        self.new_session()\n        # Ensure /source/main suffix\n"),
    ("M2 iz maskesi kaldirilir (ham cerez degeri basilir)", "scripts/sap_adt_lib.py",
     "hashlib.sha256(deger.encode('utf-8', 'replace')).hexdigest()[:8]", "deger"),
    ("M3 iz varsayilan ACIK", "scripts/sap_adt_lib.py",
     "if os.getenv('ADT_SESSION_TRACE', '').strip().lower() in ('1', 'true', 'yes', 'on'):",
     "if True:"),
    ("M4 iz sorgu dizesini (kilit tutamaci/transport) atmaz", "scripts/sap_adt_lib.py",
     "yol = (istek.path_url or '').split('?', 1)[0]", "yol = (istek.path_url or '')"),
    ("M5 iz nesil sayaci artmaz", "scripts/sap_adt_lib.py",
     "self._oturum_nesli = getattr(self, '_oturum_nesli', 0) + 1",
     "self._oturum_nesli = 1"),
    ("M6 DDL GET Accept degisir", "mcp_servers/sap_adt/tools/atom.py",
     'r = adt.session.get(url, headers={"Accept": "text/plain"}, verify=False, timeout=60)',
     'r = adt.session.get(url, headers={"Accept": "application/vnd.sap.adt.tables.v2+xml"}, verify=False, timeout=60)'),
]


def _mutasyon() -> int:
    kok = Path(tempfile.mkdtemp(prefix="oturum_izi_kum_"))
    kotu = []
    try:
        for d in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        hedef.mkdir(parents=True)
        shutil.copy2(Path(__file__), hedef / "run.py")
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
                                   text=True, encoding="utf-8", errors="replace", timeout=300, cwd=str(kok))
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

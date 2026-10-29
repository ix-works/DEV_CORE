#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adt_oturum_kapatma fixture — T-ADT-OTURUM-LOGOFF (2026-10-29): stateful ADT oturumu
süreç sonunda / istemci toplanınca / `new_session()` öncesinde best-effort KAPATILIR.

NEDEN VAR
  İstemci `x-sap-adt-sessiontype: stateful` oturum açıyor ama hiçbir yerde kapatmıyordu:
  süreç bitince ya da `new_session()` eski çerez kavanozunu atınca SAP tarafında oturum
  zaman aşımına kadar sahipsiz yaşıyordu. Kapatma yöntemi CANLI ölçüldü (lib yorumu):
  `GET /sap/public/bc/icf/logoff` güvenlik oturumu + bağlamı bitirir; aynı çerezle
  `x-sap-adt-sessiontype: stateless` bağlamı düşürür; `?sap-sessioncmd=close` etkisiz.
  ⛔ Kapatmanın bir DEV'deki "400 Session not found" vakasını çözdüğü İDDİA EDİLMEZ.

  GERÇEK lib kodu yerel sahte SAP'ye (127.0.0.1) karşı koşar. Sahte sunucu SAP'nin ölçülen
  davranışını modeller: çerezsiz stateful istek → yeni bağlam + güvenlik oturumu · logoff →
  ikisi de kapanır · stateless başlık → bağlam kapanır · kapalı bağlamla istek → 400.
  Ölçüt (canlı probla AYNI): eski çerezlerle jar DIŞINDAN yeniden oynatılan istek 400 mü.

  K0 KONTROL: kapatma yokken yeniden oynatma 200 (ölçüt ayırt edici)
  K1 new_session eski oturumu kapatır, yeni oturum çalışır
  K2 istemci toplanınca (del + gc) oturum kapanır
  K3 süreç normal çıkınca (atexit) oturum kapanır · K3k KONTROL: sonlandırıcı ayrılırsa kapanmaz
  K4 hiç istek yapılmamış istemci kapanırken AĞ ÇAĞRISI YOK (çevrimdışı fixture'lar korunur)
  K5 ICF logoff 404 → bağlam düşürme geri düşüşü
  K6 sunucu erişilemez → istisna YOK, stderr TEK satır, süre sınırlı, new_session düşmez
  K7 SAML: paylaşılan güvenlik oturumuna ICF logoff GİTMEZ, yalnız bağlam düşer
  K8 hiçbir çıktıda çerez/parola değeri yok · K9 iz açıkken kapatma isteği izde görünür
  K10 ÜÇÜNCÜ BAĞLAM: GERÇEK giriş noktası `run_sql_query.py` alt süreçte koşar (SAPClient →
      `run_query` POST); çıkışta logoff sunucuya ulaşır, sorgu çıktısı bozulmaz

KAPSAM DIŞI (ÖLÇÜLMEDİ burada): canlı SAP (lib yorumundaki ölçüm ayrı, elle) · uzun ömürlü
MCP sürecinin zorla öldürülmesi (TerminateProcess/SIGKILL'de hiçbir Python kodu koşmaz).

KULLANIM
  python tests/fixtures/adt_oturum_kapatma/run.py
  python tests/fixtures/adt_oturum_kapatma/run.py --mutasyon-new-session-kapatmaz
  (kipler: GECERLI_KIP; her kip lib'in KUM KOPYASINI bozar, gerçek kaynak DEĞİŞMEZ)
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import gc
import io
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

# kip: (anchor, yerine, beklenen düşen vektörler)
MUTASYONLAR = {
    "--mutasyon-new-session-kapatmaz": (
        "            _oturumu_kapat(old, self.url, saml, 'new_session')\n",
        "            pass\n", {"K1"}),
    "--mutasyon-sonlandirici-yok": (
        "weakref.finalize(self, _sonlandirici_kapat, self._oturum_kutusu)",
        "weakref.finalize(self, lambda _k: None, self._oturum_kutusu)", {"K2", "K3"}),
    "--mutasyon-saml-ayrimi-yok": (
        "            if not saml:\n                y = _gonder(ICF_LOGOFF_YOLU",
        "            if True:\n                y = _gonder(ICF_LOGOFF_YOLU", {"K7"}),
    "--mutasyon-geri-dusus-yok": (
        "if sonuc != 'icf-logoff' and baglam_var:",
        "if False and baglam_var:", {"K5"}),
    "--mutasyon-istisna-yutulmaz": (
        "    except Exception as hata:   # ağ hatası",
        "    except ZeroDivisionError as hata:   # ağ hatası", {"K6"}),
    "--mutasyon-oturumsuz-ag": (
        "        if not any(_KAPATMA_GEREKEN_CEREZ_RE.match(a) for a in adlar):\n"
        "            return 'oturum-yok'\n",
        "        if False:\n            return 'oturum-yok'\n", {"K4"}),
}
GECERLI_KIP = set(MUTASYONLAR)

KIP = None
COCUK = None
_argv = sys.argv[1:]
if _argv and _argv[0] == "--cocuk":                 # K3 alt süreci (iç kullanım)
    COCUK = _argv[1:]
else:
    for _a in _argv:
        if _a in GECERLI_KIP:
            KIP = _a
        else:
            print(f"[KULLANIM] bilinmeyen kip: {_a} (gecerli: {sorted(GECERLI_KIP)})")
            raise SystemExit(2)

PAROLA = "PAROLAGIZLI"
SAML_SID = "SAMLORTAKGIZLI"
A = "/sap/bc/adt/compatibility/graph"
LOGOFF = "/sap/public/bc/icf/logoff"


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSİZCE kalır."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


# ── ortam: proje dizini kum; lib dizini (mutasyonda kum kopyası) ──────────────────────
if COCUK is None:
    _TMP = Path(tempfile.mkdtemp(prefix="oturum_kapatma_"))
    (_TMP / "project.yaml").write_text(
        "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
    os.environ["CLAUDE_PROJECT_DIR"] = str(_TMP)
    for _k in ("ADT_SESSION_TRACE", "ADT_SAML_COOKIES_FILE", "ADT_BTP_AUTH_TYPE",
               "ADT_BTP_SERVICE_KEY_PATH", "ADT_SAP_DEBUG", "SAP_ADT_DEBUG"):
        os.environ.pop(_k, None)
    LIB_DIZIN = REPO / "scripts"
    if KIP:
        anchor, yeni, _ = MUTASYONLAR[KIP]
        _kum = _TMP / "kum_scripts"
        shutil.copytree(REPO / "scripts", _kum, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        _hedef = _kum / "sap_adt_lib.py"
        _metin = _hedef.read_bytes().decode("utf-8")
        if _metin.count(anchor) != 1:
            print(f"[KURULAMADI] {KIP}: capa {_metin.count(anchor)} kez bulundu (1 bekleniyordu)")
            _sil(_TMP)
            raise SystemExit(3)
        _hedef.write_bytes(_metin.replace(anchor, yeni, 1).encode("utf-8"))
        LIB_DIZIN = _kum
    os.environ["OTURUM_KAPATMA_LIB"] = str(LIB_DIZIN)
else:
    LIB_DIZIN = Path(os.environ["OTURUM_KAPATMA_LIB"])

for _p in (REPO / "scripts" / "utils", REPO / "scripts", LIB_DIZIN):
    sys.path.insert(0, str(_p))

_eski = (sys.stdout, sys.stderr)
sys.stdout = sys.stderr = io.StringIO()
try:
    import requests  # noqa: E402
    import sap_adt_lib as L  # noqa: E402
finally:
    sys.stdout, sys.stderr = _eski


def _istemci(kok, **k):
    if "auth_provider" in k:
        return L.SAPADTClient(url=kok, user="SAP_USER_A", password=PAROLA, client="100",
                              language="TR", auth_provider=k["auth_provider"])
    return L.SAPADTClient(url=kok, user="SAP_USER_A", password=PAROLA, client="100",
                          language="TR", auth_type="basic")


def _get(c, kok):
    return c.session.get(kok + A, headers=c._get_headers(accept_type="application/xml"), timeout=5)


def _cerez_dizesi(c):
    return "; ".join("%s=%s" % (k.name, k.value) for k in c.session.cookies)


# ── K3 alt süreci: istemci kur, GET, bağlam adını bas, NORMAL çık (atexit koşar) ─────
if COCUK is not None:
    kok_c, ayir = COCUK[0], COCUK[1] == "1"
    c = _istemci(kok_c)
    r = _get(c, kok_c)
    if ayir:
        c._oturum_sonlandirici.detach()
    ctx = next((k.value for k in c.session.cookies if k.name == "sap-contextid"), "-")
    print("COCUK_GET=%d CTX=%s" % (r.status_code, ctx))
    sys.stdout.flush()
    sys.exit(0)


# ── Sahte SAP ──────────────────────────────────────────────────────────────────────
class _Sunucu(BaseHTTPRequestHandler):
    kip = "normal"
    sayac = 0
    baglam: dict = {}
    guvenlik: dict = {}
    olaylar: list = []
    kilit = threading.Lock()

    def _cerez(self, ad):
        m = re.search(r"(?:^|;\s*)%s=([^;\s]*)" % re.escape(ad), self.headers.get("Cookie") or "")
        return m.group(1) if m else None

    def _c(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)
        yol = self.path.split("?", 1)[0]
        ctx = self._cerez("sap-contextid") or None
        sid = self._cerez("SAP_SESSIONID_NPL_100") or None
        tip = (self.headers.get("x-sap-adt-sessiontype") or "").lower()
        set_c, kod, govde = [], 200, b""
        with _Sunucu.kilit:
            if yol == LOGOFF:
                if _Sunucu.kip == "icf404":
                    kod, govde = 404, b"<html><title>404 Not Found</title></html>"
                else:
                    if ctx in _Sunucu.baglam:
                        _Sunucu.baglam[ctx] = "kapali"
                    if sid in _Sunucu.guvenlik:
                        _Sunucu.guvenlik[sid] = "kapali"
                    set_c.append("SAP_SESSIONID_NPL_100=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT")
            elif ctx and _Sunucu.baglam.get(ctx) == "kapali":
                kod, govde = 400, b"<html><title>400 Session Timed Out</title></html>"
            elif ctx and tip == "stateless":
                _Sunucu.baglam[ctx] = "kapali"
                set_c.append("sap-contextid=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT")
            elif not ctx and tip == "stateful":
                _Sunucu.sayac += 1
                ctx_yeni = "CTX%04dGIZLI" % _Sunucu.sayac
                _Sunucu.baglam[ctx_yeni] = "acik"
                set_c.append("sap-contextid=%s; path=/" % ctx_yeni)
                if not sid:
                    sid_yeni = "SID%04dGIZLI" % _Sunucu.sayac
                    _Sunucu.guvenlik[sid_yeni] = "acik"
                    set_c.append("SAP_SESSIONID_NPL_100=%s; path=/" % sid_yeni)
            _Sunucu.olaylar.append({"m": self.command, "yol": yol, "ctx": ctx, "sid": sid,
                                    "tip": tip, "kod": kod})
        if yol == "/sap/bc/adt/datapreview/freestyle" and kod == 200:
            govde = (b'<?xml version="1.0" encoding="utf-8"?><dataPreview:tableData '
                     b'xmlns:dataPreview="http://www.sap.com/adt/dataPreview">'
                     b'<dataPreview:totalRows>1</dataPreview:totalRows>'
                     b'<dataPreview:queryExecutionTime>1.5</dataPreview:queryExecutionTime>'
                     b'<dataPreview:columns><dataPreview:metadata dataPreview:name="MANDT"/>'
                     b'<dataPreview:dataSet><dataPreview:data>100</dataPreview:data>'
                     b'</dataPreview:dataSet></dataPreview:columns></dataPreview:tableData>')
        self.send_response(kod)
        for s in set_c:
            self.send_header("Set-Cookie", s)
        self.send_header("x-csrf-token", "SAHTETOKEN")
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        if govde:
            self.wfile.write(govde)

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _c

    def log_message(self, *a):
        pass


def _sifirla(kip="normal"):
    with _Sunucu.kilit:
        _Sunucu.kip = kip
        _Sunucu.olaylar = []
        _Sunucu.baglam = {}
        _Sunucu.guvenlik = {}


S: list = []
CIKTILAR: list = []


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
        CIKTILAR.append(out.getvalue() + err.getvalue())


def _oynat(kok, cerez):
    """Eski çerezlerle jar DIŞINDAN yeniden oynatma (canlı probla aynı ölçüt)."""
    r = requests.get(kok + A, headers={"Cookie": cerez, "x-sap-adt-sessiontype": "stateful",
                                       "Accept": "application/xml"}, timeout=5)
    return r.status_code


def _yollar():
    return [o["yol"] for o in _Sunucu.olaylar]


def bolumler(kok):
    # K0 KONTROL — kapatma yokken yeniden oynatma 200
    _sifirla()
    c = _istemci(kok)
    r = _get(c, kok)
    cerez = _cerez_dizesi(c)
    ekle("K0 KONTROL: kapatma yokken eski cerezle yeniden oynatma 200 (olcut ayirt edici)",
         r.status_code == 200 and "sap-contextid" in cerez and _oynat(kok, cerez) == 200,
         f"get={r.status_code} oynatma_yollari={_yollar()}")
    c._oturum_sonlandirici.detach()

    # K1 — new_session eski oturumu kapatır
    _sifirla()
    c = _istemci(kok)
    _get(c, kok)
    eski = _cerez_dizesi(c)
    _, exc, _, _ = _yakala(c.new_session)
    st_eski = _oynat(kok, eski)
    r2 = _get(c, kok)
    ctx_yeni = next((k.value for k in c.session.cookies if k.name == "sap-contextid"), None)
    ekle("K1 ⭐ new_session: eski oturuma ICF logoff gitti + eski cerez 400 + yeni oturum 200",
         exc is None and LOGOFF in _yollar() and st_eski == 400 and r2.status_code == 200
         and ctx_yeni and ctx_yeni not in eski,
         f"exc={exc!r} yollar={_yollar()} eski_oynatma={st_eski} yeni_get={r2.status_code}")
    c._oturum_sonlandirici.detach()

    # K2 — istemci toplanınca
    _sifirla()
    c = _istemci(kok)
    _get(c, kok)
    eski = _cerez_dizesi(c)
    kutu = c._oturum_kutusu
    del c
    gc.collect()
    ekle("K2 ⭐ istemci toplaninca (del+gc) oturum kapanir (sonuc=icf-logoff, eski cerez 400)",
         kutu.get("son") == "icf-logoff" and _oynat(kok, eski) == 400,
         f"son={kutu.get('son')} yollar={_yollar()}")

    # K3 — süreç normal çıkışı (atexit); K3k kontrol: sonlandırıcı ayrılmış
    for ayir, ad in (("0", "K3 ⭐ surec normal cikinca (atexit) oturum kapanir"),
                     ("1", "K3k KONTROL: sonlandirici ayrilirsa surec cikisinda logoff GITMEZ")):
        _sifirla()
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--cocuk", kok, ayir],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60, env=os.environ.copy())
        CIKTILAR.append(p.stderr)          # stdout = harness'in kendi CTX satiri (lib ciktisi degil)
        m = re.search(r"COCUK_GET=(\d+) CTX=(\S+)", p.stdout)
        ctx = m.group(2) if m else None
        logoff_ctx = [o for o in _Sunucu.olaylar if o["yol"] == LOGOFF and o["ctx"] == ctx]
        if ayir == "0":
            ekle(ad, p.returncode == 0 and m and m.group(1) == "200" and len(logoff_ctx) == 1
                 and _Sunucu.baglam.get(ctx) == "kapali",
                 f"rc={p.returncode} out={p.stdout.strip()[:80]} yollar={_yollar()} err={p.stderr[-200:]}")
        else:
            ekle(ad, p.returncode == 0 and m and not logoff_ctx and _Sunucu.baglam.get(ctx) == "acik",
                 f"rc={p.returncode} yollar={_yollar()}")

    # K4 — oturum yoksa ağ çağrısı yok
    _sifirla()
    c = _istemci(kok)
    kutu = c._oturum_kutusu
    _, exc, _, err = _yakala(c._oturum_sonlandirici)
    ekle("K4 hic istek yapmamis istemci kapanirken sunucuya 0 istek (sonuc=oturum-yok)",
         exc is None and not _Sunucu.olaylar and kutu.get("son") == "oturum-yok" and not err,
         f"son={kutu.get('son')} yollar={_yollar()} err={err[:120]}")

    # K5 — ICF logoff 404 → bağlam düşürme
    _sifirla("icf404")
    c = _istemci(kok)
    _get(c, kok)
    eski = _cerez_dizesi(c)
    kutu = c._oturum_kutusu
    _, exc, _, err = _yakala(c._oturum_sonlandirici)
    stateless = [o for o in _Sunucu.olaylar if o["yol"] == A and o["tip"] == "stateless"]
    ekle("K5 ⭐ ICF logoff 404 -> stateless baglam dusurme (sonuc=baglam-dusuruldu, eski cerez 400)",
         exc is None and kutu.get("son") == "baglam-dusuruldu" and len(stateless) == 1
         and _oynat(kok, eski) == 400,
         f"son={kutu.get('son')} yollar={[(o['yol'], o['kod'], o['tip']) for o in _Sunucu.olaylar]}")

    # K6 — erişilemez sunucu
    so = socket.socket()
    so.bind(("127.0.0.1", 0))
    kapali = "http://127.0.0.1:%d" % so.getsockname()[1]
    so.close()
    c = _istemci(kapali)
    c.session.cookies.set("sap-contextid", "CTXERISILEMEZGIZLI")
    c.session.cookies.set("SAP_SESSIONID_NPL_100", "SIDERISILEMEZGIZLI")
    t0 = time.perf_counter()
    r6, exc6, out6, err6 = _yakala(L._oturumu_kapat, c.session, kapali, False, "test")
    sure = time.perf_counter() - t0
    satir = [s for s in err6.splitlines() if s.strip()]
    ekle("K6 ⭐ erisilemez sunucu: istisna YOK + sonuc basarisiz + stderr TEK satir + sure < 20 s",
         exc6 is None and str(r6).startswith("basarisiz:") and len(satir) == 1
         and satir[0].startswith(L.OTURUM_IZI_ONEKI) and "kapatilamadi" in satir[0] and sure < 20,
         f"sonuc={r6!r} exc={exc6!r} satir={satir} sure={sure:.1f}")
    _, exc6b, _, _ = _yakala(c.new_session)
    ekle("K6b erisilemez sunucuda new_session istisna atmaz (yeni oturum kurulur)",
         exc6b is None and c.session is not None, f"exc={exc6b!r}")
    c._oturum_sonlandirici.detach()

    # K7 — SAML
    _sifirla()
    _Sunucu.guvenlik[SAML_SID] = "acik"
    saml = types.SimpleNamespace(
        auth_type="saml", is_valid=lambda: True, refresh_credentials=lambda: None,
        get_auth_headers=lambda: {}, get_sap_session_id=lambda: SAML_SID,
        session_cookies=[{"name": "SAP_SESSIONID_NPL_100", "value": SAML_SID,
                          "domain": "127.0.0.1", "path": "/", "secure": False}])
    c = _istemci(kok, auth_provider=saml)
    r7 = _get(c, kok)
    eski = _cerez_dizesi(c)
    kutu = c._oturum_kutusu
    _, exc, _, _ = _yakala(c._oturum_sonlandirici)
    ekle("K7 ⭐ SAML: ICF logoff GITMEZ, paylasilan guvenlik oturumu ACIK kalir, yalniz baglam duser",
         exc is None and r7.status_code == 200 and kutu.get("saml") is True
         and LOGOFF not in _yollar() and _Sunucu.guvenlik.get(SAML_SID) == "acik"
         and kutu.get("son") == "baglam-dusuruldu" and _oynat(kok, eski) == 400,
         f"son={kutu.get('son')} yollar={_yollar()} saml_sid={_Sunucu.guvenlik.get(SAML_SID)}")

    # K9 — iz açıkken kapatma isteği izde (maskeli)
    _sifirla()
    os.environ["ADT_SESSION_TRACE"] = "1"
    try:
        c = _istemci(kok)
        _, _, o9a, e9a = _yakala(_get, c, kok)
        _, _, o9, e9 = _yakala(c._oturum_sonlandirici)
    finally:
        os.environ.pop("ADT_SESSION_TRACE", None)
    ekle("K9 iz ACIKKEN logoff istegi izde tek satir (GET /sap/public/bc/icf/logoff -> 200)",
         re.search(r"GET /sap/public/bc/icf/logoff -> 200 ", o9 + e9) is not None,
         (o9 + e9).strip()[:200])

    # K10 — ÜÇÜNCÜ BAĞLAM: gerçek giriş noktası run_sql_query.py (alt süreç)
    _sifirla()
    proje = _TMP / "proje_k10"
    proje.mkdir(exist_ok=True)
    (proje / ".conn_adt").write_text(
        "ADT_SAP_URL=%s\nADT_SAP_USER=SAP_USER_A\nADT_SAP_PASSWORD=%s\nADT_SAP_CLIENT=100\n"
        "ADT_SAP_LANGUAGE=TR\n" % (kok, PAROLA), encoding="utf-8")
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    for k in list(env):
        if k.startswith("ADT_SAP_") or k.startswith("SAP_ADT_"):
            env.pop(k)
    env.update({"ADT_SAP_URL": kok, "ADT_SAP_USER": "SAP_USER_A", "ADT_SAP_PASSWORD": PAROLA,
                "ADT_SAP_CLIENT": "100", "ADT_SAP_LANGUAGE": "TR"})
    p = subprocess.run([sys.executable, str(LIB_DIZIN / "run_sql_query.py"), "--cwd", str(proje),
                        "--query", "SELECT MANDT FROM T000", "--max-rows", "1"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120, env=env, cwd=str(proje))
    CIKTILAR.append(p.stdout + p.stderr)
    post = [o for o in _Sunucu.olaylar if o["yol"].endswith("/datapreview/freestyle")]
    logoff = [o for o in _Sunucu.olaylar if o["yol"] == LOGOFF]
    ekle("K10 ⭐ 3.BAGLAM run_sql_query.py: sorgu 200 + cikista ICF logoff ayni baglamla + rc 0",
         p.returncode == 0 and "Total rows: 1" in p.stdout and post and post[-1]["kod"] == 200
         and len(logoff) == 1 and logoff[0]["ctx"] and logoff[0]["ctx"] == post[-1]["ctx"],
         f"rc={p.returncode} yollar={[(o['m'], o['yol'], o['kod']) for o in _Sunucu.olaylar]} "
         f"out={p.stdout[-160:]!r} err={p.stderr[-200:]!r}")


def main() -> int:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Sunucu)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    kok = "http://127.0.0.1:%d" % srv.server_address[1]
    try:
        try:
            bolumler(kok)
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle("[BOLUM COKTU]", False, f"{type(exc).__name__}: {exc}")
        sizan = [c for c in CIKTILAR if "GIZLI" in c]
        ekle("K8 ⭐ hicbir yakalanan cikti cerez/parola degeri tasimiyor ('GIZLI' yok)",
             not sizan and len(CIKTILAR) >= 8, f"sizan={[s[:120] for s in sizan[:2]]}")
    finally:
        srv.shutdown()
        _sil(_TMP)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print("  [KAPSAM] yerel sahte SAP (127.0.0.1), GERCEK lib (_build_session/new_session/"
          "weakref.finalize/_oturumu_kapat) + run_sql_query.py alt sureci. OLCULMEDI: canli SAP "
          "(lib yorumundaki olcum elle), MCP surecinin zorla oldurulmesi.")
    print(f"\n{n}/{len(S)} OK")
    if KIP:
        dusen = {ad.split()[0] for ad, ok, _ in S if not ok}
        beklenen = MUTASYONLAR[KIP][2]
        print(f"[MUTASYON] {KIP} ilan edilen dusus: {sorted(beklenen)} · gercek: {sorted(dusen)}")
        if not dusen:
            return 0                                   # KACTI (skor tabanla ayni)
        return 1 if beklenen & dusen else 2            # 2 = SAPMA: yanlis vektor dustu
    return 0 if n == len(S) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""classrun_tek_post — yan etkili classrun POST'u sunucuya BIR KEZ ulasir (DEV_CORE Issue #325).

NEDEN VAR (2026-10-18, yerel sahte sunucuda olculdu, core 998e739):
  `SAPClient.run_classrun` yan etkili bir classrun'u (ör. mail gonderen deneme sinifi) IKI
  katmanda tekrar POST ediyordu ve `playbook/howto-pdf-ads-xdp.md`deki "tek POST" kuralini
  cekirdegin kendi aracinda ciğniyordu:
    200 normal → 1 · 200 + sinifin KENDI ciktisinda 'does not implement' → 2 (ok:False)
    500 → 2 · 502/503/504 → 4 · okuma zaman asimi → 4
  ① `run_classrun` kosulu "200 disi HER yanit VEYA govdede gevsek alt metin" → new_session + 2. POST.
  ② `_build_session`'in oturum geneli Retry'i (POST dahil, 429/502/503/504 + okuma tekrari)
     → urllib3 ayni POST'u 3 kez daha gonderir; `run_classrun` kodunda gorunmez.

DUZELTME (sozlesme):
  · Tekrar YALNIZ ilk POST'un hic islenmedigi KESIN oldugunda: (a) baglanti kurulamadi
    (tek-post adapter'i connect-only Retry) (b) 200 + TAM imza
    `does not implement if_oo_adt_classrun~main` (bayat oturum → reset → 1 kez daha; 2026-07-31).
  · Belirsiz sonuc (5xx, okuma zaman asimi, yanit beklerken kopan baglanti) → POST TEKRARLANMAZ,
    `islenmis_olabilir: True` + `uyari`. Kesin islenmedi → `islenmis_olabilir: False`, uyari YOK.
  · Oturum geneli Retry DEGISMEDI (K1/K2 kontrol: classrun disi yol 504'te HALA 4 POST).

⛔ SILINMEZ CAPALAR:
  · V3 / V4 — bayat-oturum dali KORUNUR (200 + tam imza → 2 POST, reset gercekten olur).
    "Tekrari tumden sok" diyen fix gecemesin.
  · V11 — baglanti reddinde tekrar KORUNUR (3 red + 1 basari → sunucuya 1 POST, ok True).
  · K1 / K2 — oturum geneli Retry'a dokunulmadi (diger GET/PUT/POST'lar onu istiyor).
  · V12 — kesin islenmedi → `islenmis_olabilir: False` + uyari YOK (uyari yorgunlugu freni).

KULLANIM (repo kokunden):
  python tests/fixtures/classrun_tek_post/run.py               # vektorler
  python tests/fixtures/classrun_tek_post/run.py --mutasyon    # kopya agacta mutasyonlar
  python tests/fixtures/classrun_tek_post/run.py --taban <ref> # eski-kod karsitligi (git show)
SAP GEREKTIRMEZ: 127.0.0.1'de sahte HTTP sunucusu; GERCEK `SAPADTClient._build_session` /
`new_session` / `_request_with_csrf_retry` / `tek_post_onekini_bagla` ve GERCEK
`SAPClient.run_classrun` + MCP `atom.adt_classrun` kosar. Istemci `__new__` ile kurulur,
auth/CSRF yardimcilari sabitlenir (`.conn_adt` OKUNMAZ, canli SAP'ye dusulmez).
"""
from __future__ import annotations

import http.server
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

sys.dont_write_bytecode = True
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts" / "sap_client.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

# URETIM DOSYALARI — `--taban` bunlari eski surumle degistirir.
URETIM = ["scripts/sap_client.py", "scripts/sap_adt_lib.py"]

TO = 0.3        # istemci zaman asimi (sn)
YAVAS = 0.9     # "yavas" yanitin bekleme suresi (> TO)
SINIF = "ZCL_DEMO"
YOL = "/sap/bc/adt/oo/classrun/zcl_demo"
IMZA = "Class does not implement if_oo_adt_classrun~main!"      # SAP'nin bayat-oturum metni
GEVSEK = "done. check: ZCL_Y does not implement ZIF_Z"          # sinifin KENDI konsol ciktisi

# ─────────────────────────────────────────────────────────────────────────────
# ORTAM (import-ani yan etkileri gecici koke; MCP paketi yoksa saplama)
# ─────────────────────────────────────────────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix="classrun_tek_post_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
Path(_TMP, "project.yaml").write_text(
    "sap_profile: s4_private\nrelease: '2025'\nsource_root: SOURCE_CODES\n", encoding="utf-8")
os.chdir(_TMP)
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

_TUTUCULAR: list = []


def _sessiz_import(ad):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        import importlib
        return importlib.import_module(ad)
    finally:
        _TUTUCULAR.append((sys.stdout, sys.stderr, atik))
        sys.stdout, sys.stderr = eski


def _yakala(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    tampon = io.StringIO()
    sys.stdout = sys.stderr = tampon
    try:
        return fn(*a, **k), tampon.getvalue()
    finally:
        sys.stdout, sys.stderr = eski


S: list = []


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:260]))


def bolum(ad):
    def dek(fn):
        def sar(*a, **k):
            try:
                fn(*a, **k)
            except Exception as exc:                   # cokme != FAIL: olculur ve FAIL yazilir
                ekle(f"[BOLUM COKTU] {ad}", False, f"{type(exc).__name__}: {exc}")
        return sar
    return dek


# ─────────────────────────────────────────────────────────────────────────────
# Sahte sunucu: yol basina plan; ULASAN POST'lari sayar
#   plan ogesi: (kod, govde) · (kod, govde, {baslik}) · ("yavas", _) · ("kopar", _)
# ─────────────────────────────────────────────────────────────────────────────
class Sunucu:
    def __init__(self):
        self.plan: dict = {}
        self.n: dict = {}
        self.kilit = threading.Lock()
        d = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                ln = int(self.headers.get("Content-Length") or 0)
                if ln:
                    self.rfile.read(ln)
                with d.kilit:
                    d.n[self.path] = d.n.get(self.path, 0) + 1
                    liste = d.plan.get(self.path) or [(200, "ok")]
                    oge = liste.pop(0) if len(liste) > 1 else liste[0]
                kod, govde = oge[0], oge[1]
                basliklar = oge[2] if len(oge) > 2 else {}
                if kod == "kopar":                    # istek ALINDI, yanit yazilmadan baglanti kapanir
                    self.close_connection = True
                    return
                if kod == "yavas":
                    time.sleep(YAVAS)
                    kod, govde = 200, "gec"
                b = govde.encode("utf-8")
                try:
                    self.send_response(kod)
                    for k, v in basliklar.items():
                        self.send_header(k, v)
                    self.send_header("Content-Length", str(len(b)))
                    self.end_headers()
                    self.wfile.write(b)
                except Exception:
                    pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.srv.daemon_threads = True
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.05},
                         daemon=True).start()

    def kapat(self):
        try:
            self.srv.shutdown()
            self.srv.server_close()
        except Exception:
            pass


def istemci(L, SC, url, teshis_sayac=None):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.url = url
    c.client = "000"
    c.language = "EN"
    c._auth_provider = None
    c._get_auth_headers = lambda: {}
    c.debug_enabled = False
    c.timeout_default = TO
    c.csrf_token = "T"
    c._update_cookies = lambda r: None
    c._invalidate_csrf_cache = lambda: None

    def _csrf(force_refresh=False):
        c.csrf_token = "T"
    c.fetch_csrf_token = _csrf
    c._get_headers = lambda accept_type=None, content_type=None: {
        "Accept": accept_type or "x", "X-CSRF-Token": "T"}
    c.session = c._build_session()
    s = SC.SAPClient.__new__(SC.SAPClient)
    s.adt_client = c
    s.debug_enabled = False

    def _teshis(name):
        if teshis_sayac is not None:
            teshis_sayac.append(name)
        return {"structurally_valid": True, "active_source_bytes": 1}
    s._diagnose_classrun_binding = _teshis
    return s


def kos(L, SC, plan, teshis_sayac=None):
    """run_classrun'i plan'a karsi kos → (ulasan POST, sonuc, cikti, istemci)."""
    sv = Sunucu()
    sv.plan[YOL] = list(plan)
    s = istemci(L, SC, sv.url, teshis_sayac)
    try:
        r, cikti = _yakala(s.run_classrun, SINIF)
    finally:
        time.sleep(0.15)
        sv.kapat()
    return sv.n.get(YOL, 0), (r if isinstance(r, dict) else {}), cikti, s


def belirsiz_mi(r, cikti):
    return (r.get("ok") is False and r.get("islenmis_olabilir") is True
            and "ISLENMIS" in str(r.get("uyari") or "") and "BELIRSIZ" in cikti)


# ─────────────────────────────────────────────────────────────────────────────
# V — run_classrun vektorleri
# ─────────────────────────────────────────────────────────────────────────────
@bolum("V run_classrun")
def bolum_v(L, SC):
    n, r, c, _ = kos(L, SC, [(200, "HELLO")])
    ekle("V1 KONTROL 200 normal -> 1 POST, ok True, islenmis_olabilir/uyari YOK",
         n == 1 and r.get("ok") is True and "islenmis_olabilir" not in r and "uyari" not in r,
         f"POST={n} ok={r.get('ok')} keys={sorted(r)}")

    n, r, c, _ = kos(L, SC, [(200, GEVSEK)])
    ekle("V2 200 + sinifin KENDI ciktisinda gevsek 'does not implement' -> 1 POST, ok True, cikti korunur",
         n == 1 and r.get("ok") is True and r.get("output") == GEVSEK,
         f"POST={n} ok={r.get('ok')} output={r.get('output')!r}")

    sayac: list = []
    n, r, c, s = kos(L, SC, [(200, IMZA), (200, "HELLO")], sayac)
    nesil = getattr(s.adt_client, "_oturum_nesli", None)
    ekle("V3 ⭐ 200 + TAM imza (bayat oturum) -> reset + 2. POST MESRU: 2 POST, ok True, oturum yenilendi",
         n == 2 and r.get("ok") is True and r.get("output") == "HELLO" and nesil == 2,
         f"POST={n} ok={r.get('ok')} oturum_nesli={nesil}")

    sayac = []
    n, r, c, _ = kos(L, SC, [(200, IMZA), (200, IMZA)], sayac)
    ekle("V4 200 + TAM imza iki kez -> 2 POST, teshis kosar, islenmis_olabilir False, uyari YOK",
         n == 2 and r.get("ok") is False and r.get("error") == "classrun_unexpected"
         and len(sayac) == 1 and r.get("islenmis_olabilir") is False and "uyari" not in r
         and "BELIRSIZ" not in c,
         f"POST={n} error={r.get('error')} teshis={len(sayac)} islenmis={r.get('islenmis_olabilir')}")

    for etiket, kod in (("V5", 500), ("V6", 502), ("V7", 503), ("V8", 504)):
        n, r, c, _ = kos(L, SC, [(kod, "gw")])
        ekle(f"{etiket} {kod} -> 1 POST, durum kodu korunur, islenmis_olabilir True + uyari",
             n == 1 and r.get("status") == kod and belirsiz_mi(r, c),
             f"POST={n} status={r.get('status')} islenmis={r.get('islenmis_olabilir')} "
             f"uyari={'VAR' if r.get('uyari') else 'YOK'}")

    n, r, c, _ = kos(L, SC, [(503, "gw", {"Retry-After": "0"})])
    ekle("V9 503 + Retry-After basligi -> 1 POST (Retry-After tekrar ETTIRMEZ)",
         n == 1 and r.get("status") == 503 and belirsiz_mi(r, c),
         f"POST={n} status={r.get('status')}")

    n, r, c, _ = kos(L, SC, [("yavas", "")])
    ekle("V10 okuma zaman asimi -> 1 POST, islenmis_olabilir True + uyari",
         n == 1 and belirsiz_mi(r, c),
         f"POST={n} islenmis={r.get('islenmis_olabilir')} err={str(r.get('error'))[:80]!r}")

    n, r, c, _ = kos(L, SC, [("kopar", "")])
    ekle("V13 istek alindi, yanit yazilmadan baglanti koptu -> 1 POST, islenmis_olabilir True",
         n == 1 and belirsiz_mi(r, c),
         f"POST={n} islenmis={r.get('islenmis_olabilir')} err={str(r.get('error'))[:80]!r}")

    sayac = []
    n, r, c, _ = kos(L, SC, [(500, GEVSEK)], sayac)
    ekle("V14 500 + gevsek metin -> teshis KOSMAZ (tam imza yok), 1 POST, belirsiz",
         n == 1 and not sayac and r.get("error") not in ("classrun_unexpected", "classrun_class_not_active")
         and belirsiz_mi(r, c),
         f"POST={n} teshis={len(sayac)} error={r.get('error')}")

    n, r, c, _ = kos(L, SC, [(200, IMZA), (504, "gw")])
    ekle("V15 200 + TAM imza, sonra 504 -> 2 POST (reset sonrasi da tek-post), belirsiz",
         n == 2 and r.get("status") == 504 and belirsiz_mi(r, c),
         f"POST={n} status={r.get('status')}")


# ─────────────────────────────────────────────────────────────────────────────
# B — baglanti kurulamadi: urllib3 `_new_conn` sahte red (istek sunucuya HIC gitmez)
# ─────────────────────────────────────────────────────────────────────────────
@bolum("B baglanti reddi")
def bolum_b(L, SC):
    import urllib3.connection as UC
    from urllib3.exceptions import NewConnectionError
    asil = UC.HTTPConnection._new_conn
    deneme = {"n": 0, "red": 0}

    def sahte(self):
        deneme["n"] += 1
        if deneme["n"] <= deneme["red"]:
            raise NewConnectionError(self, "sahte baglanti reddi")
        return asil(self)

    UC.HTTPConnection._new_conn = sahte
    try:
        deneme.update(n=0, red=3)
        n, r, c, _ = kos(L, SC, [(200, "HELLO")])
        ekle("V11 ⭐ KONTROL baglanti 3 kez reddedildi, 4. acildi -> tekrar MESRU: sunucuya 1 POST, ok True",
             n == 1 and r.get("ok") is True and deneme["n"] == 4,
             f"POST={n} ok={r.get('ok')} baglanti_denemesi={deneme['n']}")

        deneme.update(n=0, red=99)
        n, r, c, _ = kos(L, SC, [(200, "HELLO")])
        ekle("V12 baglanti hep reddedildi -> 0 POST, islenmis_olabilir False, uyari YOK",
             n == 0 and r.get("ok") is False and r.get("islenmis_olabilir") is False
             and "uyari" not in r and "BELIRSIZ" not in c and deneme["n"] == 4,
             f"POST={n} islenmis={r.get('islenmis_olabilir')} denemeler={deneme['n']} "
             f"err={str(r.get('error'))[:60]!r}")
    finally:
        UC.HTTPConnection._new_conn = asil


# ─────────────────────────────────────────────────────────────────────────────
# K — kontrol grubu: oturum geneli Retry DEGISMEDI
# ─────────────────────────────────────────────────────────────────────────────
@bolum("K oturum geneli Retry")
def bolum_k(L, SC):
    import requests
    sv = Sunucu()
    yol = "/sap/bc/adt/activation"
    sv.plan[yol] = [(504, "gw")]
    sv.plan[YOL] = [(200, "HELLO")]
    s = istemci(L, SC, sv.url)
    try:
        _yakala(s.run_classrun, SINIF)       # classrun once kossun: oneki baglasin
        try:
            s.adt_client.session.post(sv.url + yol, timeout=5)
            sonuc = "yanit"
        except requests.exceptions.RetryError:
            sonuc = "RetryError"
        time.sleep(0.15)
        ekle("K1 KONTROL classrun disi yol (/activation) ayni oturumda 504 -> HALA 4 POST (kalibrasyon)",
             sv.n.get(yol, 0) == 4 and sonuc == "RetryError",
             f"POST={sv.n.get(yol, 0)} sonuc={sonuc}")
        genel = s.adt_client.session.get_adapter(sv.url + yol)
        fl = tuple(getattr(genel.max_retries, "status_forcelist", ()) or ())
        ekle("K2 KONTROL oturum geneli status_forcelist (429,502,503,504) + POST dahil DEGISMEDI",
             fl == (429, 502, 503, 504) and "POST" in (genel.max_retries.allowed_methods or ()),
             f"forcelist={fl}")
        cr = s.adt_client.session.get_adapter(sv.url + YOL)
        ekle("K3 classrun oneki AYRI adapter'da (connect-only: read=False, status_forcelist bos)",
             cr is not genel and cr.max_retries.read is False
             and not tuple(cr.max_retries.status_forcelist or ()),
             f"ayri={cr is not genel} read={getattr(cr.max_retries, 'read', '?')}")
    finally:
        sv.kapat()


# ─────────────────────────────────────────────────────────────────────────────
# M — MCP `adt_classrun` (ucuncu baglam: gercek giris noktasi)
# ─────────────────────────────────────────────────────────────────────────────
@bolum("M MCP adt_classrun")
def bolum_m(L, SC, ATOM):
    eski = (ATOM._get_client, ATOM.get_active_tier)
    try:
        ATOM.get_active_tier = lambda: "DEV"
        for etiket, plan, beklenen in (("M1", [(504, "gw")], 1), ("M2", [(200, "HELLO")], 1)):
            sv = Sunucu()
            sv.plan[YOL] = list(plan)
            s = istemci(L, SC, sv.url)
            ATOM._get_client = lambda _s=s: _s
            try:
                r, _ = _yakala(ATOM.adt_classrun, SINIF)
            finally:
                time.sleep(0.15)
                sv.kapat()
            n = sv.n.get(YOL, 0)
            if etiket == "M1":
                ekle("M1 ⭐ MCP adt_classrun 504 -> 1 POST + islenmis_olabilir True + client_log'da uyari",
                     n == beklenen and isinstance(r, dict) and r.get("islenmis_olabilir") is True
                     and "BELIRSIZ" in str(r.get("client_log") or ""),
                     f"POST={n} islenmis={r.get('islenmis_olabilir') if isinstance(r, dict) else r}")
            else:
                ekle("M2 KONTROL MCP adt_classrun 200 -> 1 POST, ok True, uyari YOK",
                     n == beklenen and isinstance(r, dict) and r.get("ok") is True and "uyari" not in r,
                     f"POST={n} ok={r.get('ok') if isinstance(r, dict) else r}")
    finally:
        ATOM._get_client, ATOM.get_active_tier = eski


def main() -> int:
    try:
        L = _sessiz_import("sap_adt_lib")
        SC = _sessiz_import("sap_client")
    except Exception as exc:
        ekle("[BOLUM COKTU] lib/sap_client import", False, f"{type(exc).__name__}: {exc}")
        L = SC = None
    if SC is not None:
        bolum_v(L, SC)
        bolum_b(L, SC)
        bolum_k(L, SC)
        try:
            ATOM = _sessiz_import("mcp_servers.sap_adt.tools.atom")
            bolum_m(L, SC, ATOM)
        except Exception as exc:
            ekle("[BOLUM COKTU] atom import", False, f"{type(exc).__name__}: {exc}")
    gecen = sum(1 for _, ok, _ in S if ok)
    for ad, ok, detay in S:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(S)} OK")
    return 0 if gecen == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON + TABAN (kopya agacta; gercek dosyalara/git'e DOKUNMAZ)
# Capa parcasi TAM 1 kez gecmezse KURULAMADI (KACTI degil).
# Her mutasyon DUSMESI GEREKEN vektoru ilan eder; yalniz rc != 0 YETMEZ.
# ─────────────────────────────────────────────────────────────────────────────
MUTASYONLAR = [
    ("MU1 reset kosulu eski genis hal (200 disi her yanit VEYA gevsek alt metin)", "scripts/sap_client.py",
     "            if r.status_code == 200 and CLASSRUN_BAYAT_IMZA in body.lower():\n",
     "            if r.status_code != 200 or 'does not implement' in body.lower():\n",
     ("V2", "V5")),
    ("MU2 ok hesabi gevsek alt metin", "scripts/sap_client.py",
     "ok = r.status_code == 200 and CLASSRUN_BAYAT_IMZA not in body.lower()",
     "ok = r.status_code == 200 and 'does not implement' not in body.lower()",
     ("V2",)),
    ("MU3 teshis dali gevsek alt metin", "scripts/sap_client.py",
     "if not ok and CLASSRUN_BAYAT_IMZA in body.lower():",
     "if not ok and 'does not implement' in body.lower():",
     ("V14",)),
    ("MU4 tek-post adapter baglama sokuldu", "scripts/sap_client.py",
     "            self.adt_client.tek_post_onekini_bagla(url)\n",
     "            pass\n",
     ("V6", "V10", "V13")),
    ("MU5 reset sonrasi yeniden baglama yok (yalniz ilk POST'ta bagla)", "scripts/sap_client.py",
     "            self.adt_client.tek_post_onekini_bagla(url)\n",
     "            if not durum.get('bagli'):\n"
     "                self.adt_client.tek_post_onekini_bagla(url)\n"
     "                durum['bagli'] = True\n",
     ("V15",)),
    ("MU6 adapter okuma tekrari acildi (read + POST)", "scripts/sap_adt_lib.py",
     "                read=False,\n",
     "                read=3, allowed_methods=('POST',),\n",
     ("V10", "V13")),
    # Durum tekrarini UC katman birlikte kapatir (status=0 · bos status_forcelist · POST'suz
    # allowed_methods). Tek katmani acan mutasyon KACAR (olculdu: yalniz forcelist+POST → 1 POST,
    # status=0 sayaci ilk 5xx'te tukenir); mutasyon bu yuzden katmanlarin HEPSINI keser.
    ("MU7 adapter durum tekrari acildi (status sayaci + 5xx + POST)", "scripts/sap_adt_lib.py",
     "                status=0,\n                other=0,\n                redirect=0,\n"
     "                status_forcelist=(),\n",
     "                status=3,\n                other=0,\n                redirect=0,\n"
     "                status_forcelist=(502, 503, 504), allowed_methods=('POST',),\n",
     ("V6", "V7", "V8")),
    ("MU8 adapter baglanti tekrari kapatildi", "scripts/sap_adt_lib.py",
     "                connect=3,\n",
     "                connect=0,\n",
     ("V11",)),
    ("MU9 yanit sonrasi islenmis isareti sokuldu", "scripts/sap_client.py",
     "                durum['islenmis_olabilir'] = True\n            return yanit\n",
     "                pass\n            return yanit\n",
     ("V5", "V6")),
    ("MU10 istisna dalinda islenmis isareti sokuldu", "scripts/sap_client.py",
     "            if durum.get('ucusta') and not classrun_istek_gitmedi(e):\n",
     "            if False:\n",
     ("V10", "V13")),
    ("MU11 siniflandirici: baglanti hatasi disini da 'gitmedi' say", "scripts/sap_client.py",
     "    if not isinstance(exc, requests.exceptions.ConnectionError):\n        return False\n",
     "    if not isinstance(exc, requests.exceptions.ConnectionError):\n        return True\n",
     ("V10",)),
    ("MU12 siniflandirici: baglanti reddini de 'gitmis olabilir' say", "scripts/sap_client.py",
     "        if isinstance(cur, ConnectTimeoutError):\n            return True\n",
     "        if isinstance(cur, ConnectTimeoutError):\n            return False\n",
     ("V12",)),
    ("MU13 uyari metni sokuldu", "scripts/sap_client.py",
     "                    print(f\"[UYARI] {sonuc['uyari']}\")\n",
     "                    pass\n",
     ("V5", "M1")),
]


def _kopya_agac() -> Path:
    kok = Path(tempfile.mkdtemp(prefix="classrun_tek_post_kum_"))
    for d in ("scripts", "mcp_servers"):
        shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hedef = kok / "tests" / "fixtures" / BURASI.name
    hedef.mkdir(parents=True)
    shutil.copy2(Path(__file__), hedef / "run.py")
    return kok


def _kos(kok: Path):
    r = subprocess.run([sys.executable, "-B", str(kok / "tests" / "fixtures" / BURASI.name / "run.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600, cwd=str(kok))
    m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
    return r.returncode, (m.group(0) if m else None), r.stdout


def _sil(kok: Path):
    def _yazilabilir(fn, yol, _exc):
        try:
            os.chmod(yol, 0o700)
            fn(yol)
        except OSError:
            pass
    shutil.rmtree(kok, onerror=_yazilabilir)
    if kok.exists():
        print(f"  [UYARI] kum dizini silinemedi: {kok}")


def _dusenler(cikti: str) -> set:
    return {m.group(1) for m in re.finditer(r"^\s*\[FAIL\] (\S+)", cikti, re.M)}


def _mutasyon() -> int:
    kok = _kopya_agac()
    kotu = []
    try:
        for ad, yol, eski, yeni, ilan in MUTASYONLAR:
            dosya = kok / yol
            asil = dosya.read_bytes().decode("utf-8")
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez bulundu (1 olmali)")
                kotu.append(ad)
                continue
            dosya.write_bytes(asil.replace(eski, yeni, 1).encode("utf-8"))
            try:
                rc, ozet, cikti = _kos(kok)
            finally:
                dosya.write_bytes(asil.encode("utf-8"))
            dusen = _dusenler(cikti)
            eksik = [v for v in ilan if v not in dusen]
            if ozet is None:
                durum = "⛔ COKTU (olcum yok)"
                kotu.append(ad)
            elif rc and not eksik:
                durum = "YAKALANDI"
            elif rc:
                durum = f"⛔ ILAN EDILEN VEKTOR DUSMEDI {eksik}"
                kotu.append(ad)
            else:
                durum = "⛔ KACTI"
                kotu.append(ad)
            print(f"--> [{ad}] rc={rc} {ozet} dusen={sorted(dusen)} ilan={list(ilan)} -> {durum}")
        # kum tabani: mutasyonlar geri alindiktan sonra kopya agac yesil olmali
        rc, ozet, cikti = _kos(kok)
        print(f"--> [KUM TABANI] rc={rc} {ozet}")
        if rc or ozet is None:
            kotu.append("KUM TABANI")
    finally:
        _sil(kok)
    print(f"\nMUTASYON OZETI: {len(MUTASYONLAR) - len([k for k in kotu if k != 'KUM TABANI'])}"
          f"/{len(MUTASYONLAR)} yakalandi")
    if kotu:
        print("  YAKALANAMAYAN/KURULAMAYAN: " + ", ".join(kotu))
    return 1 if kotu else 0


def _taban(ref: str) -> int:
    kok = _kopya_agac()
    try:
        for yol in URETIM:
            r = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{yol}"], capture_output=True)
            if r.returncode != 0:
                print(f"[fixture-hatasi] git show {ref}:{yol} basarisiz: {r.stderr[:200]!r}")
                return 2
            (kok / yol).write_bytes(r.stdout)
        rc, ozet, cikti = _kos(kok)
        print(f"### TABAN {ref} (uretim dosyalari eski surum) rc={rc} {ozet}")
        print(cikti)
        return 0 if (ozet is not None and rc != 0) else 1
    finally:
        _sil(kok)


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    if "--taban" in sys.argv:
        sys.exit(_taban(sys.argv[sys.argv.index("--taban") + 1]))
    sys.exit(main())

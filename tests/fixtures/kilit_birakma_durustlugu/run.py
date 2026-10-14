#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kilit_birakma_durustlugu fixture — Q359 + Q358: "kilit bırakılamadı" GÖRÜNÜR olmalı.

NEDEN VAR (2026-10-12)
  Q359: `sap_adt_lib.unlock_object` üç unlock stratejisi de düşse `return True` dönüyordu
  ("kilit zaman aşımıyla düşer"). Çağıranlar ya dönüşü hiç okumuyor ya da okuduğu dal
  ÖLÜYDÜ (hep True). Sızan kilit sonraki push'ta 409/423 / hayalet görev olarak, alakasız
  bir hata gibi geri dönüyordu. Dış kaynakta (aynı motorun türevi) bu satır hayalet
  transport kök nedeni olarak belgelenmiş.
  Q358: `populate_cds_views` UNLOCK yanıtını `except: pass` ile yutuyor, kodu okumuyordu.

SÖZLEŞME (⚠ RİSK bloğu = kabul ölçütü)
  · Tüm stratejiler düşerse `unlock_object` → False; istisna YOK.
  · Çağıran: yazma sonucu (`success`) DEĞİŞMEZ, `lock_released=False` + uyarı; YENİDEN
    DENEME YOK (çift kilit / 423 riski). Uyarı SM12'de kilidi SİLMEYİ ÖNERMEZ (ADR 0005-C).
  · Mutlu yol (ilk strateji 200) çıktısı ESKİSİYLE BİREBİR (kontrol grubu: pinli taban
    `6b6c11d` sap_client'ı aynı sahte istemciyle koşulur, sonuç+log kıyaslanır).

BÖLÜMLER
  A  lib `unlock_object` GERÇEK kod + YEREL sahte HTTP sunucu (127.0.0.1; SAP yok)
  B  `SAPClient.push_object` (sahte ADT) — False → success aynı, lock_released False,
     uyarı, tek unlock çağrısı · True → taban sürümle birebir
  C  MCP `adt_push_source` üst seviye `lock_released` + `lock_notice` (ok değişmez)
  D  `populate_cds_views.create_one` UNLOCK 500/istisna → uyarı + liste; 200 → sessiz
  E  sınıf değişmezi (AST): 4 üretim dosyasında (`URETIM[:4]`) `unlock_object(...)` dönüşü
     ATILMAZ (ifade-deyimi olarak çağrılmaz) + ADR 0005-C metin taraması (SM12 sil/bırak
     önerisi 0; taranan küme KODDAN türetilir) + E3 SM12 anan her satır bir KONTROL fiili taşır
     + E4 öneri deseni birimi (eşanlamlı fiil yakalanır, durum satırı geçer).
     ⚠ E2/E3 SATIR bazlıdır: SM12'siz sonraki satırdaki fiili yalnız tüm çıktıyı tarayan
     davranış vektörü görür (A8/B2/C1/F5) — sınır reçete B71'de.
  F  betik DAVRANIŞI (2026-10-14 bug-gate): push_textpool / sap_set_object_description
     unlock False → uyarı basılır, sonuç aynı · push_object 409 [MANUAL FIX] silme önermez

KULLANIM
  python tests/fixtures/kilit_birakma_durustlugu/run.py               # taban
  python tests/fixtures/kilit_birakma_durustlugu/run.py --mutasyon    # her mutasyon FAIL vermeli
"""
from __future__ import annotations

import ast
import contextlib
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
TABAN_SHA = "6b6c11d"   # Q359 öncesi (PINLI — hareketli ref DEĞİL)
# mutasyon kumunda git YOK: taban `git show` GERÇEK repodan okunur
_GIT_KOK = Path(os.environ.get("KILIT_FIXTURE_GIT_KOK") or REPO)

_TMP = tempfile.mkdtemp(prefix="kilit_birakma_")
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
_TUTUCULAR: list = []


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:260]))


def bolum(ad):
    def dek(fn):
        def sar(*a, **k):
            try:
                fn(*a, **k)
            except Exception as exc:                   # çökme != FAIL: ölçülür
                ekle(f"[BOLUM COKTU] {ad}", False, f"{type(exc).__name__}: {exc}")
        return sar
    return dek


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


def _metinden_modul(src: str, yol: Path, ad: str):
    """Kaynak METNİNİ gerçek `__file__` ile exec et (taban sürümü için)."""
    mod = types.ModuleType(ad)
    mod.__file__ = str(yol)
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        exec(compile(src, str(yol), "exec"), mod.__dict__)
    finally:
        _TUTUCULAR.append(atik)
        sys.stdout, sys.stderr = eski
    return mod


# ADR 0005-C: kilit SİLME / BIRAKMA önerisi kalıpları (uyarı metninde 0 olmalı)
# 2026-10-14 (bug-gate B-1): `delete enqueue lock` ("the" olmadan) eski desenden KAÇIYORDU
# (`push_object.py` [MANUAL FIX] metni) ⇒ `(delete|remove) (the )?(enqueue )?lock`.
# ⛔ Çıplak `clear` BİLEREK yok: "Failed to clear enqueue lock" bir DURUM bildirimidir (lib),
#    öneri değil ⇒ `(?<!to )clear …` (geri-bakış o yazımı dışarıda tutar; E2 + E4 çiviler).
# 2026-10-14 (re-gate Ö1): eşanlamlı silme fiili + KONTROL fiili AYNI satırda ikisi birden
# kaçıyordu (K1 "SM12 -> clear the enqueue lock …, then check" · K2 "SM12 -> unlock …" ·
# K3 "SM12'den kilidi kaldır, sonra kontrol et") ⇒ üç ek kol. ⛔ Çıplak `unlock` EKLENMEZ:
#    push_textpool "[UNLOCK] FAILED" bir durum satırıdır (F1 tüm logu bu desenle tarar).
# Kardeş (aynı tur): üretim metni iyelik ekli yazar ("bu objenin kilidini KONTROL ET") ⇒
# "kilidini sil/kaldır" eski `kilidi sil` kolundan da kaçıyordu → `kilid[iı]n[iı] …` (K6).
_ONERI_RE = re.compile(
    r"(release (the )?(enqueue )?lock|(delete|remove) (the )?(enqueue )?lock|delete the enqueue|"
    r"SM12\s*(→|->)\s*(release|delete)|use SM12 to|kilidi sil|kilidi bırak\b|kilidi birak\b|"
    r"(?<!to )clear (the )?(enqueue )?lock|SM12\s*(→|->)\s*(clear|unlock|remove|drop)|"
    r"kilid[iı] (kaldır|kaldir|temizle)|kilid[iı]n[iı] (sil|bırak\b|birak\b|kaldır|kaldir|temizle))",
    re.IGNORECASE)
# E3 (pozitif değişmez): SM12'yi anan her üretim satırı bir KONTROL fiili taşır — silme
# önermeyen ama ne yapılacağını da söylemeyen metin ("SM12/SE10 sonrası dene") yön verir.
_KONTROL_RE = re.compile(r"(kontrol|check|\bbak\b|do[gğ]rula)", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# A — lib unlock_object (GERÇEK kod, yerel sahte HTTP)
# ─────────────────────────────────────────────────────────────────────────────
class _Kolu(BaseHTTPRequestHandler):
    plan: dict = {}          # (METOD, yol-öneki) -> kod
    olaylar: list = []

    def _c(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)       # gövde TÜKETİLİR (urllib3 bağlantı-retry'si sahte tekrar üretmesin)
        yol = self.path.split("?")[0]
        kod = 599
        for (m, onek), k in _Kolu.plan.items():
            if m == self.command and yol.startswith(onek):
                kod = k
                break
        _Kolu.olaylar.append((self.command, yol, kod))
        self.send_response(kod)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = do_POST = do_PUT = do_DELETE = _c

    def log_message(self, *a):
        pass


def _lib_istemci(L, kok):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c._auth_provider = None
    c.user, c.password = "SAP_USER_A", "x"
    c.client, c.language = "000", "TR"
    c.csrf_token = "SAHTE"
    c.cookies = None
    c.debug_enabled = False
    c.timeout_short = c.timeout_default = 5
    c.url = kok
    c.session = c._build_session()
    return c


@bolum("A lib unlock_object")
def bolum_a(L):
    srv = HTTPServer(("127.0.0.1", 0), _Kolu)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    kok = "http://127.0.0.1:%d" % srv.server_address[1]
    URL = "/sap/bc/adt/oo/classes/zsd001_cl_ornek"
    try:
        def kos(plan):
            _Kolu.plan, _Kolu.olaylar = plan, []
            c = _lib_istemci(L, kok)
            r, log = _yakala(c.unlock_object, URL, "LH-1")
            return r, list(_Kolu.olaylar), log

        r, ol, _ = kos({("POST", URL): 500, ("DELETE", "/sap/bc/adt/locks"): 500,
                        ("DELETE", "/sap/bc/adt/core/objectlock"): 500})
        ekle("A1 ⭐ uc strateji de 500 -> dönüş False (eskiden True)",
             r is False and len(ol) == 3, f"donus={r!r} istek={ol}")
        r, ol, _ = kos({("POST", URL): 200})
        ekle("A2 KONTROL ilk strateji 200 -> True + TEK istek",
             r is True and len(ol) == 1, f"donus={r!r} istek={ol}")
        r, ol, _ = kos({("POST", URL): 500, ("DELETE", "/sap/bc/adt/locks"): 404,
                        ("DELETE", "/sap/bc/adt/core/objectlock"): 204})
        ekle("A3 KONTROL 500 -> 404 -> 204 (ucuncu strateji tuttu) -> True",
             r is True and len(ol) == 3, f"donus={r!r} istek={ol}")
        r, ol, _ = kos({})
        ekle("A4 sunucu her uca 599 -> False (bilinmeyen kod 'birakildi' SAYILMAZ)",
             r is False, f"donus={r!r}")
        c = _lib_istemci(L, kok)
        _Kolu.olaylar = []
        r = c.unlock_object(URL, None)
        ekle("A5 KONTROL kilit yok (None) -> True + istek YOK", r is True and not _Kolu.olaylar,
             f"donus={r!r} istek={_Kolu.olaylar}")
        # _release_lock_after_failure: False'ta "Lock released" YALANI basılmamalı
        _Kolu.plan = {}
        c = _lib_istemci(L, kok)
        _, log = _yakala(c._release_lock_after_failure, URL, "LH-1", "[OK] Lock released to prevent ghost transport.")
        ekle("A6 _release_lock_after_failure False -> '[OK] Lock released' BASILMAZ + uyari imzasi",
             "Lock released" not in log and L.KILIT_BIRAKILAMADI_IMZA in log, log.strip()[:200])
        _Kolu.plan = {("POST", URL): 200}
        c = _lib_istemci(L, kok)
        _, log = _yakala(c._release_lock_after_failure, URL, "LH-1", "[OK] Lock released to prevent ghost transport.")
        ekle("A7 KONTROL _release_lock_after_failure True -> eski OK metni aynen",
             log.strip() == "[OK] Lock released to prevent ghost transport.", log.strip()[:200])
        uy = L.kilit_birakilamadi_uyarisi("ZSD001_CL_ORNEK")
        ekle("A8 ADR 0005-C uyari metni: 'KONTROL ET' VAR, sil/birak ONERISI YOK",
             "KONTROL ET" in uy and not _ONERI_RE.search(uy), uy[:200])
    finally:
        srv.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# B — sap_client.push_object (sahte ADT)
# ─────────────────────────────────────────────────────────────────────────────
AD = "ZSD001_CL_ORNEK"
KAYNAK = "CLASS zsd001_cl_ornek DEFINITION PUBLIC.\nENDCLASS.\nCLASS zsd001_cl_ornek IMPLEMENTATION.\nENDCLASS.\n"


def _sahte_adt(L, unlock_donus):
    class _SahteAdt(L.SAPADTClient):
        def __init__(self):                        # noqa: D401 — gerçek __init__ bağlantı arar
            self.url = "https://sap.example.test:44300"
            self.user = "SAP_USER_A"
            self.debug_enabled = False
            self._last_lock_effective_transport = "SAHK900001"
            self._last_lock_is_link_up = ""
            self.unlock_sayisi = 0

        def get_transport_info(self, url):
            return "SAHK900001"

        def is_object_locked(self, url):
            return {"locked": False}

        def register_object_in_transport(self, name, transport, object_type):
            return {"registered": True, "method": "sahte"}

        def fetch_source_etag(self, url):
            return "etag-sahte"

        def lock_object(self, url, transport=None, **kw):
            return "LOCK1"

        def set_object_source(self, url, src, lock, transport, etag=None):
            return True

        def unlock_object(self, url, lock):
            self.unlock_sayisi += 1
            return unlock_donus

        def activate_object(self, name, url):
            return {"success": True}

        def get_object_source(self, url, return_etag=False, version=None):
            return KAYNAK
    return _SahteAdt()


def _istemci(L, SC, unlock_donus):
    ist = object.__new__(SC.SAPClient)
    ist.adt_client = _sahte_adt(L, unlock_donus)
    ist.debug_enabled = False
    ist.local_base = Path(_TMP)
    ist._find_existing_transport = lambda name, otype, transport: transport
    ist.syntax_check = lambda *a, **k: {"valid": True, "errors": [], "warnings": []}
    return ist


def _dosya():
    p = Path(_TMP) / f"{AD}.clas.abap"
    p.write_bytes(KAYNAK.encode("utf-8"))
    return str(p)


def _push(L, SC, unlock_donus):
    ist = _istemci(L, SC, unlock_donus)
    r, log = _yakala(ist.push_object, AD, object_type="class", transport="SAHK900001",
                     source_file=_dosya())
    return r, log, ist.adt_client


@bolum("B sap_client.push_object")
def bolum_b(L, SC):
    r, log, adt = _push(L, SC, False)
    ekle("B1 ⭐ unlock False -> success AYNEN True + lock_released False",
         r.get("success") is True and r.get("lock_released") is False,
         f"success={r.get('success')} lock_released={r.get('lock_released')}")
    ekle("B2 ⭐ unlock False -> uyari imzasi logda + SM12 sil/birak ONERISI YOK",
         L.KILIT_BIRAKILAMADI_IMZA in log and not _ONERI_RE.search(log),
         [s for s in log.splitlines() if "KILIT" in s][:1])
    ekle("B3 ⭐ unlock False -> YENIDEN DENEME YOK (tek unlock cagrisi)",
         adt.unlock_sayisi == 1, f"unlock_sayisi={adt.unlock_sayisi}")
    r2, log2, adt2 = _push(L, SC, True)
    ekle("B4 KONTROL unlock True -> lock_released True + uyari YOK + tek unlock",
         r2.get("success") is True and r2.get("lock_released") is True
         and L.KILIT_BIRAKILAMADI_IMZA not in log2 and adt2.unlock_sayisi == 1,
         f"lock_released={r2.get('lock_released')} unlock_sayisi={adt2.unlock_sayisi}")
    # kontrol grubu: pinli TABAN sap_client ile aynı sahte istemci -> sonuç + log BİREBİR
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:scripts/sap_client.py"],
                       capture_output=True)
    if g.returncode != 0:
        ekle("B5 KONTROL GRUBU taban sap_client okunamadi (OLCULEMEDI)", False,
             g.stderr.decode("utf-8", "replace")[:160])
        return
    TSC = _metinden_modul(g.stdout.decode("utf-8"), REPO / "scripts" / "sap_client.py",
                          "sap_client_taban")
    r3, log3, _ = _push(L, TSC, True)
    ekle("B5 ⭐ KONTROL GRUBU mutlu yol: yeni == taban (sonuc sozlugu + log BIREBIR)",
         r2 == r3 and log2 == log3,
         f"sonuc_esit={r2 == r3} log_esit={log2 == log3}")
    # B7: yükleme patlarsa iki unlock yolu koşar (upload-hata dalı + finally) — bu 2 çağrı
    # TABANDA da 2'dir (önceden var olan davranış). False dönünce finally'nin 2-deneme
    # döngüsü YENİDEN DENEMEMELİ ⇒ toplam yine 2 (3 olursa yeni bir retry eklenmiş demektir).
    def _patlayan(ist):
        def _p(*a, **k):
            raise RuntimeError("sahte upload hatasi")
        ist.adt_client.set_object_source = _p
        return ist

    ist = _patlayan(_istemci(L, SC, False))
    r7, log7 = _yakala(ist.push_object, AD, object_type="class", transport="SAHK900001",
                       source_file=_dosya())
    ist_t = _patlayan(_istemci(L, TSC, True))
    _yakala(ist_t.push_object, AD, object_type="class", transport="SAHK900001", source_file=_dosya())
    ekle("B7 ⭐ upload hatasi + unlock False -> unlock cagrisi TABANLA AYNI (2), ek retry YOK "
         "+ lock_released False",
         ist.adt_client.unlock_sayisi == ist_t.adt_client.unlock_sayisi == 2
         and r7.get("lock_released") is False and r7.get("success") is False,
         f"yeni={ist.adt_client.unlock_sayisi} taban={ist_t.adt_client.unlock_sayisi} "
         f"lock_released={r7.get('lock_released')}")
    # sap_client icinde HAM unlock cagrisi kalmadi: hepsi _kilit_birak'tan gecer
    agac = ast.parse((REPO / "scripts" / "sap_client.py").read_text(encoding="utf-8"))
    ham, sarmalayici = [], 0
    for fn in ast.walk(agac):
        if isinstance(fn, ast.FunctionDef):
            for n in ast.walk(fn):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                    if n.func.attr == "unlock_object" and fn.name != "_kilit_birak":
                        ham.append(f"{fn.name}:{n.lineno}")
                    if n.func.attr == "_kilit_birak":
                        sarmalayici += 1
    ekle("B6 sap_client: ham unlock cagrisi 0, _kilit_birak cagrisi 9",
         not ham and sarmalayici == 9, f"ham={ham} sarmalayici={sarmalayici}")


# ─────────────────────────────────────────────────────────────────────────────
# C — MCP adt_push_source
# ─────────────────────────────────────────────────────────────────────────────
@bolum("C MCP adt_push_source")
def bolum_c(L, SC, ATOM):
    eski = (ATOM._get_client, ATOM.get_active_tier)
    try:
        ATOM.get_active_tier = lambda: "DEV"

        def mcp(donus):
            ist = _istemci(L, SC, donus)
            ATOM._get_client = lambda _i=ist: _i
            return ATOM.adt_push_source(name=AD, object_type="class", source=KAYNAK,
                                        transport="SAHK900001", skip_reviewer=True)
        r = mcp(False)
        ekle("C1 ⭐ MCP unlock False -> ok AYNEN True + ust seviye lock_released False + lock_notice",
             r.get("ok") is True and r.get("lock_released") is False
             and "KONTROL ET" in str(r.get("lock_notice") or "")
             and not _ONERI_RE.search(str(r.get("lock_notice") or "")),
             f"ok={r.get('ok')} lock_released={r.get('lock_released')}")
        r = mcp(True)
        ekle("C2 KONTROL MCP unlock True -> ust seviyede lock_released/lock_notice YOK",
             r.get("ok") is True and "lock_released" not in r and "lock_notice" not in r,
             f"anahtarlar={sorted(k for k in r if k.startswith('lock'))}")
    finally:
        ATOM._get_client, ATOM.get_active_tier = eski


# ─────────────────────────────────────────────────────────────────────────────
# D — populate_cds_views.create_one (Q358)
# ─────────────────────────────────────────────────────────────────────────────
class _Y:
    def __init__(self, kod, metin=""):
        self.status_code, self.text = kod, metin


class _CdsOturum:
    def __init__(self, unlock):
        self.unlock = unlock          # int kod ya da Exception
        self.unlock_sayisi = 0

    def get(self, url, **kw):
        return _Y(404)

    def post(self, url, params=None, **kw):
        a = (params or {}).get("_action")
        if a == "LOCK":
            return _Y(200, "<LOCK_HANDLE>LH-CDS</LOCK_HANDLE>")
        if a == "UNLOCK":
            self.unlock_sayisi += 1
            if isinstance(self.unlock, Exception):
                raise self.unlock
            return _Y(self.unlock)
        return _Y(201)

    def put(self, url, **kw):
        return _Y(200)


@bolum("D populate_cds_views Q358")
def bolum_d():
    env = {"IX_SQL_VIEW_PREFIX": "ZMOD001_V_", "IX_CDS_VIEW_NAME_PREFIX": "zmod001_ddl_"}
    eski = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        src = (REPO / "scripts" / "populate_cds_views.py").read_text(encoding="utf-8")
        P = _metinden_modul(src, REPO / "scripts" / "populate_cds_views.py", "pcv_q358")
    finally:
        for k, v in eski.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    cds = "@EndUserText.label: 'Ornek'\ndefine view entity ZMOD001_I_ORNEK as select from t000 { mandt }\n"

    def kos(unlock):
        P.KILIDI_ACIK_KALMIS_OLABILIR.clear()
        c = types.SimpleNamespace(url="https://sap.example.test", session=_CdsOturum(unlock))
        r, log = _yakala(P.create_one, client=c, csrf="SAHTE", name="ZMOD001_I_ORNEK", source=cds,
                         package="ZMOD001", transport="SAHK900001")
        return r, log, list(P.KILIDI_ACIK_KALMIS_OLABILIR), c.session.unlock_sayisi

    r, log, liste, n = kos(500)
    ekle("D1 ⭐ UNLOCK 500 -> sonuc AYNEN olusturuldu + uyari + listede + tek UNLOCK",
         r == P.SONUC_OLUSTURULDU and "UNLOCK yanıtı: 500" in log and liste == ["ZMOD001_I_ORNEK"]
         and n == 1, f"r={r} liste={liste} n={n}")
    r, log, liste, n = kos(ConnectionError("sahte kopma"))
    ekle("D2 ⭐ UNLOCK istisna -> sonuc AYNEN + uyari (eskiden except: pass SESSIZ)",
         r == P.SONUC_OLUSTURULDU and "istisna:ConnectionError" in log and liste == ["ZMOD001_I_ORNEK"],
         f"r={r} liste={liste}")
    r, log, liste, n = kos(200)
    ekle("D3 KONTROL UNLOCK 200 -> sonuc olusturuldu + uyari YOK + liste bos",
         r == P.SONUC_OLUSTURULDU and "UNLOCK" not in log and not liste, f"r={r} liste={liste}")
    ekle("D4 Q358 uyari metni ADR 0005-C: sil/birak onerisi YOK",
         not _ONERI_RE.search(kos(500)[1]), "")


# ─────────────────────────────────────────────────────────────────────────────
# E — sınıf değişmezi (AST) + metin taraması
# ─────────────────────────────────────────────────────────────────────────────
# ⚠ İlk 4 eleman E1'in (AST) kümesidir — sıra korunur, yeni dosyalar SONA eklenir.
URETIM = ("scripts/sap_adt_lib.py", "scripts/sap_client.py", "scripts/push_textpool.py",
          "scripts/sap_set_object_description.py", "scripts/populate_cds_views.py",
          "mcp_servers/sap_adt/tools/atom.py", "scripts/push_object.py",
          "mcp_servers/sap_adt/tools/query.py", "scripts/hooks/post_tool_failure.py")


def _sm12_dosyalari():
    """E2/E3 taranan küme KODDAN türetilir: `scripts/` + `mcp_servers/` altında "SM12" geçen
    her .py (elle yazılan liste bayatlar) ∪ URETIM (listedeki dosya YOKSA FAIL — sessiz düşmez)."""
    bulunan = set()
    for kok in ("scripts", "mcp_servers"):
        for d, alt, dosyalar in os.walk(REPO / kok):
            alt[:] = [a for a in alt if a != "__pycache__"]
            for f in dosyalar:
                if f.endswith(".py"):
                    p = Path(d) / f
                    if "SM12" in p.read_text(encoding="utf-8", errors="replace"):
                        bulunan.add(p.relative_to(REPO).as_posix())
    return sorted(bulunan | set(URETIM))


@bolum("E sinif degismezi")
def bolum_e():
    atilan, toplam = [], 0
    for rel in URETIM[:4]:
        agac = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        for n in ast.walk(agac):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and n.func.attr == "unlock_object":
                toplam += 1
        for n in ast.walk(agac):
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) \
                    and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "unlock_object":
                atilan.append(f"{rel}:{n.lineno}")
    ekle("E1 ⭐ unlock_object donusu ATILAN cagri 0 (4 dosya, sinif tamamı)",
         toplam >= 8 and not atilan, f"toplam={toplam} atilan={atilan}")
    kume = _sm12_dosyalari()
    eksik = [rel for rel in kume if not (REPO / rel).is_file()]
    bulgu, fiilsiz, satir = [], [], 0
    for rel in kume:
        if rel in eksik:
            continue
        for i, s in enumerate((REPO / rel).read_text(encoding="utf-8").split("\n"), 1):
            if "SM12" not in s or s.lstrip().startswith("#"):
                continue
            satir += 1
            if _ONERI_RE.search(s):
                bulgu.append(f"{rel}:{i}")
            if not _KONTROL_RE.search(s):
                fiilsiz.append(f"{rel}:{i}")
    # KAPSAM: kaç dosya / kaç satır tarandı detayda basılır (0 bulgu ≠ bakılmadı)
    ekle("E2 ADR 0005-C: uretim metninde SM12 sil/birak ONERISI 0 (kume koddan + URETIM)",
         not bulgu and not eksik and "scripts/push_object.py" in kume and satir >= 15,
         f"dosya={len(kume)} satir={satir} eksik={eksik} bulgu={bulgu[:6]}")
    ekle("E3 SM12 anan her uretim satiri KONTROL fiili tasir (yonsuz 'SM12 sonrasi dene' YOK)",
         not fiilsiz and satir >= 15, f"fiilsiz={fiilsiz[:6]}")
    # E4 (re-gate Ö1): desen birimi — eşanlamlı silme fiili yakalanır, DURUM satırları geçer.
    # Negatifler ÜRETİMDEKİ GERÇEK yazımdır (genişletmeyi çivileyen geçmeli vakalar).
    oneriler = ("SM12 -> clear the enqueue lock for this object, then check",
                "SM12 -> unlock the object, then check",
                "SM12'den kilidi kaldır, sonra kontrol et",
                "SM12'de bu objenin kilidini sil, sonra kontrol et")
    durumlar = ("Failed to clear enqueue lock. SM12'de \"EADT_LOCK\" kilidini KONTROL ET",
                "[UNLOCK] FAILED", "SM12'de bu objenin kilidini KONTROL ET; silme/birakma karari")
    kacan = [o for o in oneriler if not _ONERI_RE.search(o)]
    yanlis = [d for d in durumlar if _ONERI_RE.search(d)]
    ekle("E4 _ONERI_RE: es anlamli silme fiili (clear/unlock/kaldir/kilidini sil) YAKALANIR, "
         "durum satiri ('Failed to clear', '[UNLOCK] FAILED') GECER",
         not kacan and not yanlis, f"kacan={kacan} yanlis={yanlis}")
    # E5: kardeş fixture `istek_sahibi_metni` aynı deseni KOPYA taşır (Fix metnini tüm gövdesiyle
    # tarayan tek vektör) ⇒ kopya kayması burada ölçülür (AST: derleme argümanı + bayrak).
    kardes = REPO / "tests" / "fixtures" / "istek_sahibi_metni" / "run.py"
    kdesen, kbayrak = None, None
    if kardes.is_file():
        for n in ast.walk(ast.parse(kardes.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_ONERI_RE"
                                                 for t in n.targets) and isinstance(n.value, ast.Call):
                kdesen = ast.literal_eval(n.value.args[0])
                kbayrak = ast.unparse(n.value.args[1]) if len(n.value.args) > 1 else None
    ekle("E5 kardes istek_sahibi_metni _ONERI_RE bu desenle BIREBIR ayni (kopya kaymasi yok)",
         kdesen == _ONERI_RE.pattern and kbayrak == "re.IGNORECASE",
         f"kardes_var={kardes.is_file()} ayni={kdesen == _ONERI_RE.pattern} bayrak={kbayrak}")


# ─────────────────────────────────────────────────────────────────────────────
# F — betik çağıranlarının DAVRANIŞI (bug-gate 2026-10-14: AST/metin vektörü bu üç
#     mutantı göremiyordu — `is False`→`is None` · uyarı `print` etkisiz · metin geri)
# ─────────────────────────────────────────────────────────────────────────────
class _PtAdt:
    """push_textpool için sahte ADT: GET/PUT 200, readback dolu, unlock dönüşü ayarlı."""

    def __init__(self, unlock_donus):
        self.url = "https://sap.example.test"
        self._last_lock_effective_transport = None
        self.unlock_donus, self.unlock_sayisi = unlock_donus, 0

    def fetch_csrf_token(self, force_refresh=False):
        return "SAHTE"

    def _get_headers(self, accept_type=None, content_type=None):
        return {}

    def _request_with_csrf_retry(self, method, url, headers=None, params=None, data=None, timeout=None):
        return types.SimpleNamespace(status_code=200, headers={"ETag": "e1"},
                                     text="@MaxLength:10\r\nB00=Baslik")

    def lock_object(self, url, access_mode=None, transport=None):
        return "LH-PT"

    def unlock_object(self, url, handle):
        self.unlock_sayisi += 1
        return self.unlock_donus


class _DescAdt:
    """sap_set_object_description._lock_put_unlock için sahte ADT."""

    def __init__(self, unlock_donus):
        self._last_lock_effective_transport = None
        self.timeout_default = 5
        self.unlock_donus, self.unlock_sayisi = unlock_donus, 0
        self.session = types.SimpleNamespace(
            put=lambda *a, **k: types.SimpleNamespace(status_code=200, text=""))

    def lock_object(self, url, access_mode=None, transport=None):
        return "LH-D"

    def _get_headers(self, *a, **k):
        return {}

    def unlock_object(self, url, handle):
        self.unlock_sayisi += 1
        return self.unlock_donus


def _argv_ile(argv, fn):
    eski = sys.argv
    sys.argv = argv

    def _sarili():
        try:
            return fn()
        except SystemExit as exc:          # argparse çıkışı fixture'ı ÖLDÜRMESİN: kodu ölçülür
            return f"SystemExit:{exc.code}"
    try:
        return _yakala(_sarili)
    finally:
        sys.argv = eski


@bolum("F betik davranisi")
def bolum_f(L):
    PT = _sessiz_import("push_textpool")
    sym = Path(_TMP) / "ZSD001_P_ORNEK.symbols.txt"
    sym.write_bytes(b"@MaxLength:10\nB00=Baslik\n")
    argv = ["push_textpool.py", "--program", "ZSD001_P_ORNEK", "--transport", "SAHK900001",
            "--symbols-file", str(sym), "--no-activate"]

    def pt(donus):
        adt = _PtAdt(donus)
        PT.SAPClient = lambda _a=adt: types.SimpleNamespace(adt_client=_a)
        rc, log = _argv_ile(argv, PT.main)
        return rc, log, adt
    rc, log, adt = pt(False)
    ekle("F1 ⭐ push_textpool unlock False -> '[UNLOCK] FAILED' + uyari imzasi, rc AYNEN 0, tek unlock",
         rc == 0 and "[UNLOCK] FAILED" in log and L.KILIT_BIRAKILAMADI_IMZA in log
         and "[UNLOCK] done" not in log and adt.unlock_sayisi == 1 and not _ONERI_RE.search(log),
         f"rc={rc} unlock={adt.unlock_sayisi} imza={L.KILIT_BIRAKILAMADI_IMZA in log}")
    rc, log, adt = pt(True)
    ekle("F2 KONTROL push_textpool unlock True -> '[UNLOCK] done', imza YOK, rc 0",
         rc == 0 and "[UNLOCK] done" in log and L.KILIT_BIRAKILAMADI_IMZA not in log
         and adt.unlock_sayisi == 1, f"rc={rc}")

    SD = _sessiz_import("sap_set_object_description")
    url = "/sap/bc/adt/oo/classes/zsd001_cl_ornek"

    def sd(donus):
        adt = _DescAdt(donus)
        r, log = _yakala(SD._lock_put_unlock, adt, url, "https://sap.example.test" + url,
                         "application/xml", b"<x/>", "etag-1", "SAHK900001")
        return r, log, adt
    r, log, adt = sd(False)
    ekle("F3 ⭐ set_object_description unlock False -> sonuc AYNEN (200) + uyari imzasi + obje adi",
         r == (200, "", "SAHK900001") and L.KILIT_BIRAKILAMADI_IMZA in log
         and "ZSD001_CL_ORNEK" in log and adt.unlock_sayisi == 1, f"r={r} log={log.strip()[:120]}")
    r, log, adt = sd(True)
    ekle("F4 KONTROL set_object_description unlock True -> sonuc ayni + imza YOK",
         r == (200, "", "SAHK900001") and L.KILIT_BIRAKILAMADI_IMZA not in log, f"r={r}")

    PO = _sessiz_import("push_object")
    sonuc = {"success": False, "error_type": "SAPLockError",
             "error": "[409] Object locked under transport (CORRNR SAHK900002)"}
    PO.SAPClient = lambda: types.SimpleNamespace(push_object=lambda **k: sonuc)
    rc, log = _argv_ile(["push_object.py", "--name", "ZSD001_CL_ORNEK", "--type", "class",
                         "--transport", "SAHK900001"], PO.main)
    sm12 = [s for s in log.splitlines() if "SM12" in s]
    ekle("F5 ⭐ push_object 409 SAPLockError [MANUAL FIX] -> SM12 KONTROL ET, silme ONERISI YOK, rc 1",
         rc == 1 and "[MANUAL FIX]" in log and sm12 and all(_KONTROL_RE.search(s) for s in sm12)
         and not _ONERI_RE.search(log), f"rc={rc} sm12={sm12[:2]}")


def main() -> int:
    try:
        L = _sessiz_import("sap_adt_lib")
        SC = _sessiz_import("sap_client")
    except Exception as exc:
        ekle("[BOLUM COKTU] import", False, f"{type(exc).__name__}: {exc}")
        L = SC = None
    if L is not None:
        bolum_a(L)
        bolum_b(L, SC)
        try:
            ATOM = _sessiz_import("mcp_servers.sap_adt.tools.atom")
            bolum_c(L, SC, ATOM)
        except Exception as exc:
            ekle("[BOLUM COKTU] atom import", False, f"{type(exc).__name__}: {exc}")
    bolum_d()
    bolum_e()
    if L is not None:
        bolum_f(L)
    gecen = sum(1 for _, ok, _ in S if ok)
    for ad, ok, detay in S:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(S)} OK")
    return 0 if gecen == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON (kopya ağaçta; gerçek dosyalara DOKUNMAZ). Parça TAM 1 kez geçmezse KURULAMADI.
# ─────────────────────────────────────────────────────────────────────────────
MUTASYONLAR = [
    ("M1 ⭐ RISK-c: unlock_object son satiri 'return True'ya geri", "scripts/sap_adt_lib.py",
     "lock NOT released\")\n        return False", "lock NOT released\")\n        return True"),
    ("M2 sap_client _kilit_birak donusu okumuyor", "scripts/sap_client.py",
     "        if ok is False:\n            from sap_adt_lib import kilit_birakilamadi_uyarisi",
     "        if False:\n            from sap_adt_lib import kilit_birakilamadi_uyarisi"),
    ("M3 finally dalinda False'ta YENIDEN DENEME (break kaldirildi)", "scripts/sap_client.py",
     "                            print(f\"          [OK] Object unlocked\")\n                        break",
     "                            print(f\"          [OK] Object unlocked\")\n                            break"),
    ("M4 MCP ust seviye lock_released tasinmiyor", "mcp_servers/sap_adt/tools/atom.py",
     "result.get(\"lock_released\") is False:", "False:"),
    ("M5 Q358 UNLOCK yaniti yine yutuluyor", "scripts/populate_cds_views.py",
     "        if _unlock_kod not in (200, 204):", "        if False:"),
    ("M6 _release_lock_after_failure donusu okumuyor (eski yalan OK)", "scripts/sap_adt_lib.py",
     "                if self.unlock_object(object_url, actual_handle) is False:",
     "                if self.unlock_object(object_url, actual_handle) is None:"),
    ("M7 uyari metnine SM12 birakma onerisi geri", "scripts/sap_adt_lib.py",
     "f\"SM12'de bu objenin kilidini KONTROL ET; silme/birakma karari kullanicidadir \"",
     "f\"use SM12 to release the lock. KONTROL ET \""),
    # bug-gate 2026-10-14: aşağıdaki üçü eski 23 vektörün TAMAMINDAN kaçıyordu (23/23 kalıyordu)
    ("M8 push_textpool False dali olu (is None)", "scripts/push_textpool.py",
     "            if ok_unlock is False:\n", "            if ok_unlock is None:\n"),
    ("M9 set_object_description uyarisi basilmiyor", "scripts/sap_set_object_description.py",
     "                print(kilit_birakilamadi_uyarisi(url.rstrip(",
     "                str(kilit_birakilamadi_uyarisi(url.rstrip("),
    ("M10 push_object [MANUAL FIX] SM12 silme onerisi geri", "scripts/push_object.py",
     "                print(\"  1. SM12 -> CHECK the enqueue lock for this object \"\n"
     "                      \"(KONTROL ET; silme karari kullanicida, ADR 0005-C)\")\n",
     "                print(\"  1. SM12 -> delete enqueue lock for this object\")\n"),
    ("M11 hook hatirlatmasi yonsuz SM12 metnine geri", "scripts/hooks/post_tool_failure.py",
     "lock conflict → SM12'de kilidi KONTROL ET \"\n"
     "    \"(silme kararı kullanıcıda, ADR 0005-C) / SE10'da istek durumuna bak.\\n\"",
     "lock conflict → SM12/SE10 sonrası dene.\\n\""),
    # re-gate Ö1 (2026-10-14): 5. eleman = DÜŞMESİ İLAN EDİLEN vektörler; hepsi FAIL vermezse
    # mutant "YANLIS VEKTOR" sayılır (rc≠0 tek başına yetmez — başka bir vektör düşmüş olabilir).
    ("K1 SM12 -> clear the enqueue lock ..., then check (ayni satir)", "scripts/push_object.py",
     "                print(\"  1. SM12 -> CHECK the enqueue lock for this object \"\n",
     "                print(\"  1. SM12 -> clear the enqueue lock for this object, then check \"\n",
     ("E2", "F5")),
    ("K2 SM12 -> unlock ..., then check (lib uyari metni)", "scripts/sap_adt_lib.py",
     "f\"SM12'de bu objenin kilidini KONTROL ET; silme/birakma karari kullanicidadir \"",
     "f\"SM12 -> unlock the object, then KONTROL ET \"",
     ("A8", "B2", "E2")),       # C1 DEĞİL: MCP lock_notice atom.py'nin kendi metnidir (ölçüldü)
    ("K3 hook: SM12'den kilidi kaldir, sonra kontrol et", "scripts/hooks/post_tool_failure.py",
     "lock conflict → SM12'de kilidi KONTROL ET \"\n"
     "    \"(silme kararı kullanıcıda, ADR 0005-C) / SE10'da istek durumuna bak.\\n\"",
     "lock conflict → SM12'den kilidi kaldır, sonra kontrol et / SE10'da istek durumuna bak.\\n\"",
     ("E2",)),
    ("K4 push_object: silme fiili SM12'siz SONRAKI satirda", "scripts/push_object.py",
     "                      \"(KONTROL ET; silme karari kullanicida, ADR 0005-C)\")\n",
     "                      \"(KONTROL ET), then clear the enqueue lock\")\n",
     ("F5",)),
    ("K4b lib uyari: silme fiili SM12'siz SONRAKI satirda", "scripts/sap_adt_lib.py",
     "            f\"(ADR 0005-C). Bir sonraki push 409/423 verirse sebep bu olabilir.\")",
     "            f\"(ADR 0005-C), then clear the enqueue lock.\")",
     ("A8", "B2")),             # E2 DEĞİL: satırda SM12 yok — tüm uyarıyı okuyan A8/B2 yakalar
    # ⛔ K5 (hook: silme fiili SM12'siz SONRAKI satırda) BURADA YOK — ölçüldü 2026-10-14: 30/30
    #    KAÇTI. Hook metnini tüm çıktısıyla okuyan davranış vektörü yok, E2 satır bazlı ⇒ SINIR
    #    (reçete B71). Listeye konursa --mutasyon kalıcı kırmızı olur; desen icat edilmedi.
    ("K6 kardes: iyelik ekli 'kilidini sil' (lib uyari metni)", "scripts/sap_adt_lib.py",
     "f\"SM12'de bu objenin kilidini KONTROL ET; silme/birakma karari kullanicidadir \"",
     "f\"SM12'de bu objenin kilidini sil, sonra KONTROL ET \"",
     ("A8", "B2", "E2")),
    ("K7 kardes fixture deseni daralir (kopya kaymasi)", "tests/fixtures/istek_sahibi_metni/run.py",
     "    r\"kilid[iı] (kaldır|kaldir|temizle)|kilid[iı]n[iı] (sil|bırak\\b|birak\\b|kaldır|kaldir|temizle))\",\n",
     "    r\"kilid[iı] (kaldır|kaldir|temizle))\",\n",
     ("E5",)),
]


def _kopya_agac() -> Path:
    kok = Path(tempfile.mkdtemp(prefix="kilit_birakma_kum_"))
    for d in ("scripts", "mcp_servers"):
        shutil.copytree(REPO / d, kok / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hedef = kok / "tests" / "fixtures" / BURASI.name
    hedef.mkdir(parents=True)
    shutil.copy2(Path(__file__), hedef / "run.py")
    # E5 kardeş fixture'ın desenini okur ⇒ kumda da bulunmalı (yoksa her mutant sahte-YAKALANDI)
    kardes = kok / "tests" / "fixtures" / "istek_sahibi_metni"
    kardes.mkdir(parents=True)
    shutil.copy2(REPO / "tests" / "fixtures" / "istek_sahibi_metni" / "run.py", kardes / "run.py")
    return kok


def _kos(kok: Path):
    env = dict(os.environ)
    env["KILIT_FIXTURE_GIT_KOK"] = str(REPO)
    r = subprocess.run([sys.executable, str(kok / "tests" / "fixtures" / BURASI.name / "run.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600, cwd=str(kok), env=env)
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


def _mutasyon() -> int:
    kok = _kopya_agac()
    kotu = []
    try:
        # KUM TABANI: mutasyonsuz kum yeşil değilse her mutant rc≠0 verir (sahte-YAKALANDI).
        rc0, ozet0, cikti0 = _kos(kok)
        if rc0 or ozet0 is None:
            print(f"  [KURULAMADI] kum tabani kirmizi: rc={rc0} {ozet0}")
            for s in [s.strip() for s in cikti0.splitlines() if s.strip().startswith("[FAIL]")][:6]:
                print(f"      {s[:150]}")
            return 1
        print(f"--> [KUM TABANI] rc=0 {ozet0}")
        for ad, yol, eski, yeni, *ilan in MUTASYONLAR:
            ilan = tuple(ilan[0]) if ilan else ()
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
            dusen = [s.strip() for s in cikti.splitlines() if s.strip().startswith("[FAIL]")]
            dusmeyen = [v for v in ilan
                        if not any(s.startswith(f"[FAIL] {v} ") for s in dusen)]
            if ozet is None:
                durum = "COKTU (olcum yok)"
                kotu.append(ad)
            elif rc and dusmeyen:
                durum = f"YANLIS VEKTOR (ilan edilen dusmedi: {', '.join(dusmeyen)})"
                kotu.append(ad)
            elif rc:
                durum = "YAKALANDI" + (f" [{'+'.join(ilan)}]" if ilan else "")
            else:
                durum = "KACTI"
                kotu.append(ad)
            print(f"--> [{ad}] rc={rc} {ozet} -> {durum}")
            for s in dusen[:4]:
                print(f"      {s[:150]}")
    finally:
        _sil(kok)
    print(f"\nMUTASYON OZETI: {len(MUTASYONLAR) - len(kotu)}/{len(MUTASYONLAR)} yakalandi")
    if kotu:
        print("  YAKALANAMAYAN/KURULAMAYAN: " + ", ".join(kotu))
    return 1 if kotu else 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    sys.exit(main())

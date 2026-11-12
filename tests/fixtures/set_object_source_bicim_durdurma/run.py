#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""set_object_source_bicim_durdurma fixture — DEV_CORE Issue #423.

NEDEN VAR (2026-11-12)
  `set_object_source` dört transport biçimini sırayla dener. Eskiden 2xx ve 423-NO_LOCK
  dışındaki HER yanıt bir sonraki biçime düşüyor, yalnız SONUNCUNUN yanıtı raporlanıyordu.
  Ölçülen vaka (tüketici, on-prem, global sınıf): biçim 1-2 → 400 `OO_SOURCE_BASED 011`
  (kayıt-anı tarama reddi = içerik), biçim 3-4 → kendi kilidimize çarpan 409
  `CTS_WBO_API 019`; araç yalnız 409'u bastı ve teşhis üç tur kilit yönünde yürüdü.

SÖZLEŞME
  · Sonraki biçime YALNIZ transport-biçimi reddinde geçilir: "Parameter … could not be found"
    · 409 · 412 (412 dalı DEĞİŞMEDİ). 400/404/423/500 … → TEK PUT + o yanıt raporlanır.
  · Hata metni TÜM denemelerin `biçim -> kod -> öz` listesini taşır (DENEMELER bloğu).
  · Son biçimdeki "Parameter … could not be found" artık sahte `True` DEĞİL, hata.
  · 423-NO_LOCK dalı (SAPLockError) ve 423 teşhisi (put_423_diagnosis) AYNEN.
  · push_object.py (GERÇEK `main()`): 409-dışı hata alan deneme varsa "ÖNCE O YANITA BAK";
    409 gövdesinde V3/V4 = bu push'un transport'u + oturum kullanıcısıysa "ANOTHER developer"
    BASILMAZ; biri farklı/okunamazsa eski uyarı AYNEN basılır (muhafazakâr kontrol grubu).

KATMANLAR (SAP yok)
  L  lib `set_object_source` GERÇEK kod + GERÇEK `_build_session`/`_request_with_csrf_retry`;
     PUT/GET yerel sahte HTTP sunucusuna (127.0.0.1) gider (desen: retry_500_govde).
  P  `push_object.main()` → GERÇEK `SAPClient.push_object` → GERÇEK `set_object_source` →
     aynı sahte sunucu. Yalnız kilit/ETag/aktivasyon/okuma çağrıları sahte (konu dışı).

KULLANIM
  python tests/fixtures/set_object_source_bicim_durdurma/run.py
  python tests/fixtures/set_object_source_bicim_durdurma/run.py --mutasyon
  python tests/fixtures/set_object_source_bicim_durdurma/run.py --taban   # pinli taban 8565c9d (bilgi)
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
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
TABAN_SHA = "8565c9d"   # Issue #423 öncesi (PINLI — hareketli ref verme)
_GIT_KOK = Path(os.environ.get("BICIM_DURDURMA_GIT_KOK") or REPO)
_TMP = tempfile.mkdtemp(prefix="bicim_durdurma_")
os.environ["CLAUDE_PROJECT_DIR"] = _TMP
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

S: list = []
_TUT: list = []
K = "SAHK900001"            # bu push'un transport'u (placeholder)
KULLANICI = "SAP_USER_A"    # oturum kullanıcısı (placeholder)
URL = "/sap/bc/adt/oo/classes/zsd001_cl_ornek"
AD = "ZSD001_CL_ORNEK"


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


def exc_xml(t100_id, t100_no, metin, v1="", v3="", v4=""):
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<exc:exception xmlns:exc="http://www.sap.com/abapxml/types/decorated">'
            '<type id="ExceptionSahte"/>'
            f'<message lang="EN">{metin}</message>'
            f'<localizedMessage lang="EN">{metin}</localizedMessage>'
            '<properties>'
            f'<entry key="T100KEY-ID">{t100_id}</entry><entry key="T100KEY-NO">{t100_no}</entry>'
            f'<entry key="T100KEY-V1">{v1}</entry><entry key="T100KEY-V3">{v3}</entry>'
            f'<entry key="T100KEY-V4">{v4}</entry>'
            '</properties></exc:exception>')


G400 = exc_xml("OO_SOURCE_BASED", "011", "Error during save. Changes not stored.")
G409 = exc_xml("CTS_WBO_API", "019", "Object is locked in request", v1="LIMU CLSD ZSD001_CL_ORNEK",
               v3=K, v4=KULLANICI)
GPARAM = "Parameter corrNr could not be found"


def g409_uzun(v3, v4):
    """PR #427 F1: GERÇEKÇİ uzunlukta `CTS_WBO_API 019` 409 gövdesi — ADT `exc:exception` biçimi
    (`hata_sebebi_ve_maskeleme` EXC_GOVDE deseni: communicationframework ad alanı + namespace +
    type + message + localizedMessage + properties). Bug-gate ölçümü: ~719 kr, V3 ~618., V4 ~660.
    ⇒ V3/V4 500. karakterin ÖTESİNDE. Kısa G409 (V3/V4 ~400.) gerçekte oluşmayan rejimdi."""
    return ('<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/abapxml/'
            'types/communicationframework"><namespace id="com.sap.adt"/>'
            '<type id="ExceptionResourceLockConflict"/>'
            f'<message lang="EN">Object LIMU CLSD ZSD001_CL_ORNEK is locked in request {v3} of user {v4}'
            '</message>'
            f'<localizedMessage lang="TR">Nesne LIMU CLSD ZSD001_CL_ORNEK {v4} kullanicisinin {v3} '
            'talebinde kilitli; nesne yalniz bu talep icinde degistirilebilir</localizedMessage><properties>'
            '<entry key="T100KEY-ID">CTS_WBO_API</entry><entry key="T100KEY-NO">019</entry>'
            '<entry key="T100KEY-V1">LIMU CLSD ZSD001_CL_ORNEK</entry><entry key="T100KEY-V2"></entry>'
            f'<entry key="T100KEY-V3">{v3}</entry><entry key="T100KEY-V4">{v4}</entry>'
            '</properties></exc:exception>')


# ── sahte SAP (127.0.0.1) ─────────────────────────────────────────────────────
class _Kolu(BaseHTTPRequestHandler):
    karar = None        # fn(sira, headers, params) -> (kod, govde)
    post_karar = None   # fn(yol) -> (kod, govde) | None  (None = 200 <ok/>; PR #427 F1 kilit 409)
    putlar: list = []
    get_etag = "ETAG-INAKTIF"

    def _govdeyi_tuket(self):
        # ⚠ okunmazsa bağlantı kirli kalır, urllib3 PUT'u TEKRAR edebilir (retry_500_govde dersi)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
        except Exception:
            pass

    def _yaz(self, kod, govde, ek=None):
        b = govde.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(b)))
        for k, v in (ek or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def do_PUT(self):
        self._govdeyi_tuket()
        u = urlparse(self.path)
        p = {k: v[0] for k, v in parse_qs(u.query).items()}
        h = {k: v for k, v in self.headers.items()}
        _Kolu.putlar.append({"corrNr": p.get("corrNr"), "hdr": h.get("X-sap-adt-transport"),
                             "ifmatch": h.get("If-Match"), "lockHandle": p.get("lockHandle")})
        kod, govde = _Kolu.karar(len(_Kolu.putlar), h, p)
        self._yaz(kod, govde)

    def do_GET(self):
        self._yaz(200, "x", {"ETag": _Kolu.get_etag})

    def do_POST(self):
        self._govdeyi_tuket()
        k = _Kolu.post_karar(urlparse(self.path).path) if _Kolu.post_karar else None
        if k:
            self._yaz(*k)
            return
        self._yaz(200, "<ok/>")

    def log_message(self, *a):
        pass


_SUNUCU = HTTPServer(("127.0.0.1", 0), _Kolu)
threading.Thread(target=_SUNUCU.serve_forever, daemon=True).start()
TABAN_URL = f"http://127.0.0.1:{_SUNUCU.server_address[1]}"


def senaryo(karar, post=None):
    _Kolu.karar = karar
    _Kolu.post_karar = post
    _Kolu.putlar = []


def kilit_post_409(govde):
    """Gerçek `lock_object` 1. stratejisi (`/sap/bc/adt/locks`) 409 + verilen gövde alır."""
    return lambda yol: (409, govde) if yol.endswith("/sap/bc/adt/locks") else None


def _yakala(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    t = io.StringIO()
    sys.stdout = sys.stderr = t
    try:
        try:
            return fn(*a, **k), None, t.getvalue()
        except BaseException as exc:                  # noqa: BLE001 — istisna ÖLÇÜLÜR
            return None, exc, t.getvalue()
    finally:
        sys.stdout, sys.stderr = eski


def _sessiz_import(ad):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        import importlib
        return importlib.import_module(ad)
    finally:
        _TUT.append(atik)
        sys.stdout, sys.stderr = eski


def istemci_kur(L, nesne=None):
    """GERÇEK oturum + GERÇEK `_request_with_csrf_retry`; yalnız auth/header/çerez izole."""
    c = nesne if nesne is not None else L.SAPADTClient.__new__(L.SAPADTClient)
    c._auth_provider = None
    c.client, c.language = "100", "EN"
    c._get_auth_headers = lambda: {}
    c.session = c._build_session()
    c.url = TABAN_URL
    c.user = KULLANICI
    c.debug_enabled = False
    c.csrf_token = "TOKEN"
    c.timeout_default = c.timeout_short = 10
    c._get_headers = lambda *a, **k: {}
    c._update_cookies = lambda r: None
    c._last_lock_modification_support = None
    return c


def sabit(*seri):
    """PUT sırası → (kod, gövde); son eleman tekrar eder."""
    return lambda i, h, p: seri[min(i, len(seri)) - 1]


# ── L: lib ────────────────────────────────────────────────────────────────────
def bolum_l(L):
    def kos(karar, lh="LH-1", etag="ETAG-1", tr=K):
        senaryo(karar)
        c = istemci_kur(L)
        r, exc, log = _yakala(c.set_object_source, URL, "REPORT x.", lh, tr, etag)
        return r, exc, log, list(_Kolu.putlar)

    # L1 — Issue senaryosu: 400, 400, 409, 409
    r, exc, log, pt = kos(sabit((400, G400), (400, G400), (409, G409), (409, G409)))
    m = str(exc or "")
    ekle("L1 ⭐ Issue: biçim1 400 OO_SOURCE_BASED 011 -> TEK PUT, hata 400 + gövde özü, 409 YOK",
         len(pt) == 1 and type(exc).__name__ == "SAPADTError" and getattr(exc, "status_code", None) == 400
         and "OO_SOURCE_BASED/011" in m and "CTS_WBO_API" not in m and "DENEMELER (1)" in m,
         f"put={len(pt)} exc={type(exc).__name__} kod={getattr(exc, 'status_code', None)} m={m[:200]!r}")
    ekle("L1b durma mesajı 'DURDU' + 'DENENMEDI' der; ilk PUT corrNr query'li (sıra değişmedi)",
         "DURDU" in m and "DENENMEDI" in m and pt and pt[0]["corrNr"] == K and pt[0]["hdr"] is None,
         f"m={m[:160]!r} put={pt[:1]}")
    ekle("L1c istisna `denemeler` özniteliği taşır (sap_client -> push_object kanalı)",
         getattr(exc, "denemeler", None) == [("corrNr query parameter only", 400,
                                              "OO_SOURCE_BASED/011: Error during save. Changes not stored.")],
         f"denemeler={getattr(exc, 'denemeler', None)}")

    # L2 — "Parameter … could not be found" -> sonraki biçim
    r, exc, log, pt = kos(lambda i, h, p: (400, GPARAM) if "corrNr" in p else (200, ""))
    ekle("L2 ⭐ biçim1 'Parameter corrNr could not be found' -> biçim2'ye GEÇER (header yedeği 3. PUT 200)",
         r is True and exc is None and len(pt) == 3 and pt[1]["hdr"] == K and pt[2]["corrNr"] is None,
         f"r={r} exc={exc!r} put={[(x['hdr'], x['corrNr']) for x in pt]}")

    # L3 — kontrol grubu: 200
    r, exc, log, pt = kos(sabit((200, "")))
    ekle("L3 KONTROL 200@biçim1 -> True, TEK PUT, DENEMELER basılmaz",
         r is True and exc is None and len(pt) == 1 and "DENEMELER" not in log,
         f"r={r} put={len(pt)}")

    # L4 — 412 dalı DEĞİŞMEDİ: 412 -> inaktif ETag GET -> retry 200
    _Kolu.get_etag = "ETAG-INAKTIF"
    r, exc, log, pt = kos(sabit((412, "etag"), (200, "")))
    ekle("L4 412 dalı AYNEN: inaktif ETag ile tekrar PUT -> True (2 PUT, 2.si If-Match yeni ETag)",
         r is True and len(pt) == 2 and pt[1]["ifmatch"] == "ETAG-INAKTIF" and pt[1]["corrNr"] == K,
         f"r={r} exc={exc!r} put={[(x['ifmatch'], x['corrNr']) for x in pt]}")
    r, exc, log, pt = kos(sabit((412, "etag"), (412, "etag"), (200, "")))
    ekle("L4b 412 + tekrar 412 -> sonraki BİÇİME geçer (dal davranışı korunur) -> True",
         r is True and len(pt) == 3 and pt[2]["hdr"] == K,
         f"r={r} exc={exc!r} put={[(x['hdr'], x['corrNr'], x['ifmatch']) for x in pt]}")

    # L5 — 409 her biçimde -> 4 PUT (transport_yaklasim_sirasi T3 ile aynı sözleşme) + 4'lü liste
    r, exc, log, pt = kos(sabit((409, G409)))
    m = str(exc or "")
    ekle("L5 ⭐ 409 her biçimde -> 4 PUT + DENEMELER (4) listesi (biçim -> kod -> öz)",
         len(pt) == 4 and getattr(exc, "status_code", None) == 409 and "DENEMELER (4)" in m
         and m.count("-> 409 -> CTS_WBO_API/019") == 4 and "after 4 attempts" in m,
         f"put={len(pt)} m={m[:220]!r}")

    # L6 — 409 sonra 400 -> 2. biçimde DURUR, liste ikisini de taşır
    r, exc, log, pt = kos(sabit((409, G409), (400, G400)))
    m = str(exc or "")
    ekle("L6 ⭐ 409@1 + 400@2 -> 2 PUT'ta DURUR, liste [409, 400] (② tüm denemeler)",
         len(pt) == 2 and getattr(exc, "status_code", None) == 400 and "DENEMELER (2)" in m
         and "1. corrNr query parameter only -> 409" in m and "2. both header and parameter -> 400" in m,
         f"put={len(pt)} m={m[:260]!r}")

    # L7 — 500 / 404 -> durur
    for kod in (500, 404):
        r, exc, log, pt = kos(sabit((kod, exc_xml("SADT", "001", f"sahte {kod}"))))
        ekle(f"L7-{kod} {kod}@biçim1 -> TEK PUT + {kod} raporlanır",
             len(pt) == 1 and getattr(exc, "status_code", None) == kod,
             f"put={len(pt)} kod={getattr(exc, 'status_code', None)}")

    # L8 — 423 (gerçek handle) -> durur + §12.7 teşhisi aynen
    r, exc, log, pt = kos(sabit((423, "invalid lock handle")))
    m = str(exc or "")
    ekle("L8 423@biçim1 -> TEK PUT + '423 TEŞHİSİ' hem hatada hem stdout'ta (teşhis korunur)",
         len(pt) == 1 and getattr(exc, "status_code", None) == 423 and "423 TEŞHİSİ" in m
         and "FROM e071" in log, f"put={len(pt)} m={m[-160:]!r}")

    # L9 — 423 + NO_LOCK_SUPPORT dalı DEĞİŞMEDİ
    r, exc, log, pt = kos(sabit((423, "invalid lockHandle")), lh="NO_LOCK_SUPPORT")
    ekle("L9 423 + NO_LOCK_SUPPORT -> SAPLockError (dal AYNEN), TEK PUT",
         type(exc).__name__ == "SAPLockError" and len(pt) == 1, f"exc={type(exc).__name__} put={len(pt)}")

    # L10 — her biçimde "Parameter…" -> eskiden sahte True; artık hata
    r, exc, log, pt = kos(sabit((400, GPARAM)))
    ekle("L10 ⭐ son biçimde de 'Parameter … could not be found' -> HATA (eskiden sahte True)",
         r is None and getattr(exc, "status_code", None) == 400 and len(pt) == 4
         and "after 4 attempts" in str(exc), f"r={r} exc={exc!r} put={len(pt)}")

    # L11 — PR #427 F3: 412 → inaktif ETag tekrarı 400 (içerik reddi) → DURUR, tekrarın yanıtı raporlanır.
    # c2a1039'da karar ilk 412'ye bakıyordu ⇒ biçim-2'ye düşüp 3. PUT atılıyordu.
    _Kolu.get_etag = "ETAG-INAKTIF"
    r, exc, log, pt = kos(sabit((412, "etag"), (400, G400)))
    m = str(exc or "")
    ekle("L11 ⭐ 412 -> tekrar 400 -> 2 PUT'ta DURUR, istisna 400 + OO_SOURCE_BASED (tekrarın yanıtı)",
         len(pt) == 2 and getattr(exc, "status_code", None) == 400 and "OO_SOURCE_BASED/011" in m
         and "DENEMELER (2)" in m and "412 sonrasi inaktif ETag tekrari] -> 400" in m
         and "Response (400)" in m, f"put={len(pt)} kod={getattr(exc, 'status_code', None)} m={m[:240]!r}")

    # L12 — PR #427 F1: GERÇEK lock_object 409 dalı, gerçekçi uzun gövde (V3/V4 > 500. karakter)
    govde = g409_uzun(K, KULLANICI)
    on_kosul = len(govde) > 500 and govde.index("T100KEY-V3") > 500 and govde.index("T100KEY-V4") > 500
    senaryo(sabit((200, "")), post=kilit_post_409(govde))
    c = istemci_kur(L)
    r, exc, log = _yakala(c.lock_object, URL, transport=K)
    t1 = getattr(exc, "t100_degiskenleri", None) or {}
    ekle("L12 ⭐ gerçek lock_object 409 (gövde %d kr, V3@%d V4@%d): response_text 500'e kesik AMA "
         "t100_degiskenleri V3/V4'ü TAM gövdeden taşır" % (len(govde), govde.index("T100KEY-V3"),
                                                          govde.index("T100KEY-V4")),
         on_kosul and type(exc).__name__ == "SAPLockError" and getattr(exc, "status_code", None) == 409
         and len(getattr(exc, "response_text", "") or "") == 500
         and "T100KEY-V3" not in (exc.response_text or "")
         and t1.get("T100KEY-V3") == K and t1.get("T100KEY-V4") == KULLANICI
         and t1.get("T100KEY-ID") == "CTS_WBO_API",
         f"on_kosul={on_kosul} exc={type(exc).__name__} t100={t1}")


# ── P: push_object.main() gerçek giriş noktası ────────────────────────────────
def bolum_p(L, SC, PO):
    kaynak = Path(_TMP) / f"{AD}.clas.abap"
    kaynak.write_bytes(b"CLASS zsd001_cl_ornek DEFINITION.\nENDCLASS.\n")

    def kos(karar, kilit_hatasi=None, post=None, sonuc=False):
        """`post` verilirse GERÇEK `lock_object` koşar (sahte sunucu POST yanıtıyla, PR #427 F1).
        `sonuc=True` → `push_object.main()` yerine `SAPClient.push_object` sonuç SÖZLÜĞÜ döner (F7)."""
        senaryo(karar, post=post)

        class _A(L.SAPADTClient):
            def __init__(self):
                istemci_kur(L, self)
                self._last_lock_effective_transport = K
                self._last_lock_is_link_up = ""
                self._last_lock_istek_sahibi = None

            def is_object_locked(self, url):
                return {"locked": False}

            def register_object_in_transport(self, *a, **k):
                return {"registered": True, "method": "sahte"}

            def fetch_source_etag(self, url):
                return "ETAG-1"

            def lock_object(self, url, transport=None, **kw):
                if post is not None:
                    return L.SAPADTClient.lock_object(self, url, transport=transport, **kw)
                if kilit_hatasi is not None:
                    self._last_lock_effective_transport = None
                    raise kilit_hatasi
                return "LH-1"

            def unlock_object(self, url, h):
                return True

            def activate_object(self, *a, **k):
                return {"success": True}

            def get_object_source(self, *a, **k):
                return "CLASS zsd001_cl_ornek DEFINITION.\nENDCLASS.\n"

            def find_ghost_transports(self, *a, **k):
                return []

        ist = object.__new__(SC.SAPClient)
        ist.adt_client = _A()
        ist.debug_enabled = False
        ist.local_base = Path(_TMP)
        ist._find_existing_transport = lambda n, t, tr: tr
        ist.syntax_check = lambda *a, **k: {"valid": True}
        if sonuc:
            res, exc, log = _yakala(ist.push_object, object_name=AD, object_type="class",
                                    transport=K, source_file=str(kaynak))
            return res, exc, log, list(_Kolu.putlar)
        eski_sc, eski_argv = PO.SAPClient, sys.argv
        PO.SAPClient = lambda *a, **k: ist
        sys.argv = ["push_object.py", "--name", AD, "--type", "class", "--transport", K,
                    "--source-file", str(kaynak)]
        try:
            rc, exc, log = _yakala(PO.main)
        finally:
            PO.SAPClient, sys.argv = eski_sc, eski_argv
        return rc, exc, log, list(_Kolu.putlar)

    BASKA = "ANOTHER developer"
    # P1 — Issue senaryosu uçtan uca
    rc, exc, log, pt = kos(sabit((400, G400), (400, G400), (409, G409), (409, G409)))
    print(f"  [BILGI] P1 (Issue senaryosu) 'ANOTHER developer' basildi mi: "
          f"{'EVET' if BASKA in log else 'HAYIR'} · PUT sayisi {len(pt)} · "
          f"409 ciktida: {'EVET' if 'CTS_WBO_API' in log else 'HAYIR'}")
    ekle("P1 ⭐ push_object.main: Issue senaryosu -> rc 1, TEK PUT, çıktıda 400 OO_SOURCE_BASED, 409 YOK",
         rc == 1 and exc is None and len(pt) == 1 and "OO_SOURCE_BASED" in log
         and "CTS_WBO_API" not in log and BASKA not in log,
         f"rc={rc} exc={exc!r} put={len(pt)}")

    # P2 — kilit 409, gövde V3/V4 = bu push + bu kullanıcı -> "başka geliştirici" BASILMAZ
    def kilit409(v3, v4):
        return L.SAPLockError("Object is locked under transport unknown (target was %s)." % K,
                              status_code=409,
                              response_text=exc_xml("CTS_WBO_API", "019", "locked", v3=v3, v4=v4))
    rc, exc, log, pt = kos(sabit((200, "")), kilit_hatasi=kilit409(K, KULLANICI))
    ekle("P2 ⭐ kilit 409 + V3/V4 kendi transport'umuz+kullanıcımız -> 'ANOTHER developer' YOK, "
         "'KENDI kilidimizle' VAR, kullanıcı adı basılmaz",
         rc == 1 and BASKA not in log and "KENDI kilidimizle" in log and KULLANICI not in log,
         f"rc={rc} cikti={[s for s in log.splitlines() if 'HINT' in s or 'CRITICAL' in s][:3]}")
    rc, exc, log, pt = kos(sabit((200, "")), kilit_hatasi=kilit409("SAHK900099", "SAP_USER_B"))
    ekle("P2b KONTROL: V3/V4 başka transport+kullanıcı -> eski uyarı AYNEN ('ANOTHER developer' VAR)",
         rc == 1 and BASKA in log and "KENDI kilidimizle" not in log, f"rc={rc}")
    rc, exc, log, pt = kos(sabit((200, "")), kilit_hatasi=kilit409(K, "SAP_USER_B"))
    ekle("P2c KONTROL: transport bizim ama kullanıcı FARKLI -> eski uyarı AYNEN (muhafazakâr)",
         rc == 1 and BASKA in log and "KENDI kilidimizle" not in log, f"rc={rc}")
    rc, exc, log, pt = kos(sabit((200, "")), kilit_hatasi=L.SAPLockError(
        "Object is locked under transport unknown.", status_code=409, response_text="<bozuk"))
    ekle("P2d KONTROL: gövdede V3/V4 YOK -> eski uyarı AYNEN (okunamayan = 'kendimiz' sayılmaz)",
         rc == 1 and BASKA in log and "KENDI kilidimizle" not in log, f"rc={rc}")

    # P3 — 409 sonra 400: ikinci biçimde durur, liste çıktıda
    rc, exc, log, pt = kos(sabit((409, G409), (400, G400)))
    ekle("P3 409@1 + 400@2 -> çıktıda DENEMELER listesi (2) + 400 özü; son yanıt 409 DEĞİL ⇒ "
         "'ONCE O YANITA BAK' basılmaz",
         rc == 1 and len(pt) == 2 and "OO_SOURCE_BASED/011" in log and "DENEMELER (2)" in log
         and "ONCE O YANITA BAK" not in log,
         f"rc={rc} put={len(pt)}")
    _Kolu.get_etag = "ETAG-1"   # 412 retry ETag değişmez -> retry yapılmaz, dal sonraki biçime düşer
    rc, exc, log, pt = kos(sabit((412, exc_xml("SADT_RESOURCE", "043", "etag uyusmuyor")), (409, G409)))
    ekle("P4 ⭐ 412@1 (409-DIŞI) sonra 409'lar -> 'ONCE O YANITA BAK' + 412 özü çıktıda",
         rc == 1 and "ONCE O YANITA BAK" in log and "SADT_RESOURCE/043" in log,
         f"rc={rc} put={len(pt)} hint={[s for s in log.splitlines() if 'ONCE' in s][:1]}")
    rc, exc, log, pt = kos(sabit((409, G409)))
    ekle("P4b KONTROL: yalnız 409'lar -> 'ONCE O YANITA BAK' BASILMAZ",
         rc == 1 and "ONCE O YANITA BAK" not in log and len(pt) == 4, f"rc={rc} put={len(pt)}")
    _Kolu.get_etag = "ETAG-INAKTIF"

    # ── PR #427 F1: GERÇEK uzunlukta gövde (V3/V4 > 500. kr) + GERÇEK kilit/PUT yolu ──
    ust = g409_uzun(K, KULLANICI)
    yab = g409_uzun("SAHK900099", "SAP_USER_B")

    def hint(log_):
        return [s for s in log_.splitlines() if "HINT" in s or "CRITICAL" in s][:3]

    rc, exc, log, pt = kos(sabit((200, "")), post=kilit_post_409(ust))
    ekle("P5 ⭐ GERÇEK lock_object 409, uzun gövde, V3/V4 kendimiz -> 'KENDI kilidimizle', "
         "'ANOTHER developer' YOK, kullanıcı adı basılmaz, PUT yok",
         rc == 1 and "KENDI kilidimizle" in log and BASKA not in log and KULLANICI not in log
         and len(pt) == 0, f"rc={rc} put={len(pt)} {hint(log)}")
    rc, exc, log, pt = kos(sabit((200, "")), post=kilit_post_409(yab))
    ekle("P5b KONTROL: GERÇEK lock_object 409, uzun gövde, başka istek+kullanıcı -> 'ANOTHER developer' VAR",
         rc == 1 and BASKA in log and "KENDI kilidimizle" not in log, f"rc={rc} {hint(log)}")
    # PUT 409 (SAPADTError) da aynı 409 kararından geçer — eskiden bu dala hiç girmiyordu.
    rc, exc, log, pt = kos(sabit((409, ust)))
    # (PUT hata metni `error` TAM gövdeyi taşır — maskesiz `error` önceden var, F7 kapsamı dışı.)
    ekle("P6 ⭐ PUT 409 her biçimde (SAPADTError), uzun gövde kendimiz -> 'KENDI kilidimizle', "
         "'ANOTHER developer' YOK",
         rc == 1 and len(pt) == 4 and "KENDI kilidimizle" in log and BASKA not in log
         and "[ERROR TYPE] SAPADTError" in log, f"rc={rc} put={len(pt)} {hint(log)}")
    rc, exc, log, pt = kos(sabit((409, yab)))
    ekle("P6b ⭐ PUT 409 her biçimde, başka istek+kullanıcı -> 'ANOTHER developer' + 'NEVER pick' VAR "
         "(eskiden PUT 409'da HİÇ basılmıyordu)",
         rc == 1 and BASKA in log and "NEVER pick a transport" in log and "KENDI kilidimizle" not in log,
         f"rc={rc} {hint(log)}")
    rc, exc, log, pt = kos(sabit((400, G400)))
    ekle("P6c KONTROL: PUT 400 (409-dışı) -> 409 dalı YOK ('ANOTHER developer' ve 'KENDI' basılmaz)",
         rc == 1 and BASKA not in log and "KENDI kilidimizle" not in log, f"rc={rc} {hint(log)}")

    # ── PR #427 F7: sonuç sözlüğü (MCP `"result": result`e AYNEN girer) kimlik maskeli ──
    res, exc, log, pt = kos(sabit((200, "")), post=kilit_post_409(ust), sonuc=True)
    res = res if isinstance(res, dict) else {}
    ert = str(res.get("error_response_text") or "")
    t1 = res.get("error_t100") or {}
    ekle("P7a ⭐ error_response_text: oturum kullanıcısı maskeli (<KULLANICI>), ham ad YOK",
         bool(ert) and KULLANICI not in ert and "<KULLANICI>" in ert,
         f"exc={exc!r} ert={ert[:160]!r}")
    ekle("P7b ⭐ error_t100: V4 (kilit sahibi = oturum kullanıcısı) maskeli, V3 transport AYNEN",
         t1.get("T100KEY-V4") == "<KULLANICI>" and t1.get("T100KEY-V3") == K, f"t100={t1}")
    res, exc, log, pt = kos(sabit((200, "")), post=kilit_post_409(yab), sonuc=True)
    res = res if isinstance(res, dict) else {}
    t1 = res.get("error_t100") or {}
    ekle("P7c KONTROL: başka kullanıcı (oturum kullanıcısı değil) maskelenmez — istisna yolu kuralıyla aynı",
         t1.get("T100KEY-V4") == "SAP_USER_B", f"t100={t1}")


def main() -> int:
    L = _sessiz_import("sap_adt_lib")
    SC = _sessiz_import("sap_client")
    PO = _sessiz_import("push_object")
    bolum_l(L)
    bolum_p(L, SC, PO)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    _SUNUCU.shutdown()
    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if n == len(S) else 1


# (ad, dosya, eski, yeni, DÜŞMESİ İLAN EDİLEN vektör önekleri)
MUTASYONLAR = [
    ("M1 eski dongu: her hata sonraki bicime duser", "scripts/sap_adt_lib.py",
     "if transport_bicim_reddi_mi(response.status_code, response.text) and not _son:",
     "if not _son:", {"L1", "L1b", "L6", "L7-500", "L8", "P1", "P3"}),
    ("M2 DENEMELER listesi hata metnine girmez", "scripts/sap_adt_lib.py",
     'f"{_bas}\\nDENEMELER ({len(denemeler)}):\\n{_liste}\\n"', 'f"{_bas}\\n"',
     {"L1", "L5", "L6"}),
    ("M3 son bicimde Parameter -> dongu biter (sahte True yolu)", "scripts/sap_adt_lib.py",
     "and not _son:\n", ":\n", {"L10"}),
    ("M4 push_object kendi-kilit suzgeci kapali", "scripts/push_object.py",
     "if ('409' in error or _put_409) and kendi_kilidimiz_mi(", "if False and kendi_kilidimiz_mi(",
     {"P2", "P5", "P6"}),
    ("M5 push_object ONCE-O-YANITA-BAK kapali", "scripts/push_object.py",
     "if _farkli and str(_denemeler[-1][1]) == '409':", "if False:", {"P4"}),
    ("M5b ipucu son yanit 409 olmasa da basilir", "scripts/push_object.py",
     "if _farkli and str(_denemeler[-1][1]) == '409':",
     "if _farkli and any(str(d[1]) == '409' for d in _denemeler):", {"P3"}),
    ("M6 sap_client hata ayrintisi aktarilmaz", "scripts/sap_client.py",
     "        den = getattr(exc, 'denemeler', None)\n", "        return\n", {"P2", "P4"}),
    # ── PR #427 (bug-gate düzeltme turu) ──
    ("M7 F3: 412 tekrarinin yaniti karara girmez (c2a1039)", "scripts/sap_adt_lib.py",
     "                            response = retry_resp\n", "", {"L11"}),
    ("M8 F1: V3/V4 kesik (500) govdeden okunur", "scripts/sap_adt_lib.py",
     "response_text=response_text[:500],\n"
     "                                       t100_degiskenleri=t100_degiskenleri_oku(response_text))",
     "response_text=response_text[:500])", {"L12", "P5"}),
    ("M9a F7: error_response_text maskesiz", "scripts/sap_client.py",
     "result['error_response_text'] = kimlik_maskele(str(govde), parola=parola,\n"
     "                                                           kullanici=kullanici)",
     "result['error_response_text'] = str(govde)", {"P7a"}),
    ("M9b F7: error_t100 maskesiz", "scripts/sap_client.py",
     "{k: kimlik_maskele(str(v), parola=parola, kullanici=kullanici)", "{k: str(v)", {"P7b"}),
    ("M10 F1: PUT 409 kendi-kilit/CRITICAL dalina girmez", "scripts/push_object.py",
     "_put_409 = bool(_denemeler) and str(_denemeler[-1][1]) == '409'", "_put_409 = False",
     {"P6", "P6b"}),
]


def _kum_kos(kok, env):
    hedef = kok / "tests" / "fixtures" / BURASI.name / "run.py"
    r = subprocess.run([sys.executable, str(hedef)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, cwd=str(kok), env=env)
    m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
    dusen = {re.match(r"\s*\[FAIL\] (\S+)", s).group(1)
             for s in r.stdout.splitlines() if re.match(r"\s*\[FAIL\] \S+", s)}
    return r, m, dusen


def _kum_kur():
    kok = Path(tempfile.mkdtemp(prefix="bicim_durdurma_kum_"))
    shutil.copytree(REPO / "scripts", kok / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hedef = kok / "tests" / "fixtures" / BURASI.name
    hedef.mkdir(parents=True)
    shutil.copy2(Path(__file__), hedef / "run.py")
    env = dict(os.environ)
    env["BICIM_DURDURMA_GIT_KOK"] = str(REPO)
    env.pop("CLAUDE_PROJECT_DIR", None)
    return kok, env


def _mutasyon() -> int:
    kok, env = _kum_kur()
    kotu = []
    try:
        r, m, dusen = _kum_kos(kok, env)
        taban_ok = bool(m) and r.returncode == 0
        print(f"--> [KUM TABANI] rc={r.returncode} {m.group(0) if m else '-'} -> "
              f"{'YESIL' if taban_ok else 'KIRMIZI'}")
        if not taban_ok:
            print(r.stdout[-1500:])
            return 1
        for ad, yol, eski, yeni, ilan in MUTASYONLAR:
            dosya = kok / yol
            asil = dosya.read_bytes().decode("utf-8")
            if asil.count(eski) != 1:
                print(f"  [KURULAMADI] {ad} -> parca {asil.count(eski)} kez")
                kotu.append(ad)
                continue
            dosya.write_bytes(asil.replace(eski, yeni, 1).encode("utf-8"))
            try:
                r, m, dusen = _kum_kos(kok, env)
            finally:
                dosya.write_bytes(asil.encode("utf-8"))
            if not m:
                durum = "COKTU"
            elif ilan <= dusen:
                durum = "YAKALANDI"
            else:
                durum = "KACTI"
            if durum != "YAKALANDI":
                kotu.append(ad)
            print(f"--> [{ad}] rc={r.returncode} {m.group(0) if m else '-'} -> {durum} "
                  f"(ilan={sorted(ilan)} dusen={sorted(dusen)})")
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    print(f"\nMUTASYON OZETI: {len(MUTASYONLAR) - len(kotu)}/{len(MUTASYONLAR)} yakalandi")
    return 1 if kotu else 0


def _taban() -> int:
    """BİLGİ (gate değil): pinli taban `8565c9d`'nin üç dosyasıyla koş — hangi vektör düşüyor,
    eski kodda P1'de 'ANOTHER developer' basılıyor muydu. Beklenen: L1/L5/L6/L10/P1/P2/P4 düşer;
    PR #427 vektörlerinden L11/L12/P5/P6/P6b/P7a/P7b de (taban bu alanları hiç üretmez)."""
    kok, env = _kum_kur()
    try:
        for rel in ("scripts/sap_adt_lib.py", "scripts/sap_client.py", "scripts/push_object.py"):
            g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:{rel}"],
                               capture_output=True)
            if g.returncode != 0:
                print(f"[DOGRULANAMADI] taban okunamadi: {rel}")
                return 2
            (kok / rel).write_bytes(g.stdout)
        r, m, dusen = _kum_kos(kok, env)
        print(r.stdout)
        print(f"--> [TABAN {TABAN_SHA}] rc={r.returncode} {m.group(0) if m else '-'} "
              f"dusen={sorted(dusen)}")
        return 0
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    if "--taban" in sys.argv:
        sys.exit(_taban())
    sys.exit(main())

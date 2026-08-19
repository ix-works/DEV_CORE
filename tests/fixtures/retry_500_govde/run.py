#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""retry_500_govde fixture — SAP'nin 500 GÖVDESİ çağırana ULAŞMALI.

NEDEN VAR (2026-08-19; ölçülmüş iki vaka 18.08.2026)
  `SAPADTClient._build_session()` her isteğe `Retry(status_forcelist=(429,500,502,503,504))`
  mount ediyordu. SAP anlamlı bir hata gövdesiyle 500 döndüğünde adapter onu 3 kez tekrarlıyor
  ve **gövdeyi atıyor**: çağırana `MaxRetryError('too many 500 error responses')` gidiyor,
  SAP'nin anlattığı sebep (`CTS_WBO_API 019/020` — "obje şu kullanıcının şu talebinde bloke")
  KAYBOLUYOR. İki FM push'unda kök sebep ancak retry sökülüp (`max_retries=0`) ham cevap
  okunarak bulundu; bir ajan bu yüzden "kaynak limiti" hipotezine saptı.

  ⛔ Buradaki 500 GEÇİCİ DEĞİL, SAP'nin *kalıcı* reddi (transport kilidi). Tekrar denemek
  çözmez, yalnız TEŞHİSİ SİLER. Fix: `status_forcelist`'ten yalnız **500** çıkarıldı.

İKİ DEĞİŞMEZ, İKİ ÇAPA
  (1) YENİ: 500 tekrar EDİLMEZ, cevap+gövde çağırana döner    → A1..A6 (mutasyonda düşer)
  (2) ESKİ KORUNDU: 429/502/503/504 HÂLÂ tekrar edilir, 200 sağlam → B1..B5 (gevşetme çapası)
  FP çapası (2) olmadan (1) trivial olurdu: retry'ı tümden söken bir "fix" de A'yı geçirir.

KULLANIM
  python tests/fixtures/retry_500_govde/run.py                  # düzeltilmiş modüle karşı
  python tests/fixtures/retry_500_govde/run.py --modul <yol>    # MUTASYON (eski sürüm) → RED
  (mutasyon tabani PINLI SHA olmali: `git show ab37296:scripts/sap_adt_lib.py > <scratch>/eski.py`)
  ⛔ `origin/main` VERME: bu PR merge edilince o ref "fix SONRASI"na kayar ve korpus
     ayirt etmiyormus gibi gorunur — HATA VERMEDEN (belgelenmis sinif: hareketli ref =
     olcum aletinin sessiz bosalmasi, infra-changelog 2026-08-10). Kosucu tabani
     OZ-DENETLER: verilen modulde 500 forcelist'te DEGILSE exit 2 + [DOGRULANAMADI].

⚠ İZOLASYON: ölçülen TEK değişken adapter'ın `status_forcelist`'idir. `_build_session`in
  geri kalanı (pool, verify, header'lar) GERÇEK kodla koşar; yalnız `_get_auth_headers`
  örnek üzerinde boş sözlüğe bağlanır (kimlik doğrulama bu testin konusu değil ve canlı
  SAP gerektirirdi). Sunucu YEREL (127.0.0.1) — ağ/SAP bağımlılığı yoktur.
"""
from __future__ import annotations

import importlib.util
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(p))

# Placeholder'lı sahte SAP hata gövdesi (kimlik izi YOK — core public repodur).
GOVDE_500 = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<exc:exception xmlns:exc="http://www.sap.com/abapxml/types/decorated">'
    '<message lang="EN">Object ZSD001 is blocked by user &lt;SAP_USER&gt; in request'
    ' &lt;TRANSPORT&gt; (CTS_WBO_API 019)</message></exc:exception>'
)
IMZA = "CTS_WBO_API 019"


class _Kolu(BaseHTTPRequestHandler):
    sayac: dict[str, int] = {}

    def _cevap(self):
        yol = self.path
        _Kolu.sayac[yol] = _Kolu.sayac.get(yol, 0) + 1
        # ⚠ İSTEK GÖVDESİ TÜKETİLMELİ: okunmazsa bağlantı kirli kalır, urllib3 bunu
        # bağlantı hatası sanıp POST/PUT'u TEKRAR EDER (`total=3` connect/read retry'si) →
        # "500 tekrar edilmedi" çapası sahte-KIRMIZI olur. İlk ölçümde tam bu yaşandı.
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
        except Exception:
            pass
        if yol == "/govde500":
            govde, kod = GOVDE_500.encode("utf-8"), 500
        elif yol == "/gecici503":
            govde, kod = b"gecici", 503
        elif yol == "/gecici429":
            govde, kod = b"gecici", 429
        elif yol == "/gecici502":
            govde, kod = b"gecici", 502
        else:
            govde, kod = b"<ok/>", 200
        self.send_response(kod)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    do_GET = do_POST = do_PUT = _cevap

    def log_message(self, *a):      # sunucu gürültüsü testin çıktısını boğmasın
        pass


def modul_yukle(yol: Path):
    spec = importlib.util.spec_from_file_location("sap_adt_lib_test", str(yol))
    m = importlib.util.module_from_spec(spec)
    sys.modules["sap_adt_lib_test"] = m
    spec.loader.exec_module(m)
    return m


def oturum_kur(mod):
    """GERÇEK `_build_session()` ile session üret (yalnız auth header'ları izole edilir)."""
    c = mod.SAPADTClient.__new__(mod.SAPADTClient)
    c._auth_provider = None
    c.client = "100"
    c.language = "TR"
    c._get_auth_headers = lambda: {}
    return c._build_session()


def main(modul_yolu: str | None = None) -> int:
    yol = Path(modul_yolu) if modul_yolu else (REPO / "scripts" / "sap_adt_lib.py")
    if not yol.is_file():
        sys.stderr.write("OLCULEMEDI: modul yok: %s\n" % yol)
        return 2
    mod = modul_yukle(yol)
    sess = oturum_kur(mod)
    forcelist = tuple(sess.get_adapter("http://x/").max_retries.status_forcelist)
    # TABAN OZ-DENETIMI: mutasyon modunda taban GERCEKTEN kusurlu olmali; degilse hicbir
    # sayi raporlanmaz (hareketli-ref sinifi, bkz. docstring).
    if modul_yolu and 500 not in forcelist:
        sys.stderr.write("[DOGRULANAMADI] mutasyon tabani kusurlu DEGIL (500 forcelist'te "
                         "yok): %s -> hicbir sayi raporlanmadi. Pinli SHA ver.\n" % yol)
        return 2

    srv = HTTPServer(("127.0.0.1", 0), _Kolu)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    kok = "http://127.0.0.1:%d" % srv.server_address[1]
    print("modul    :", yol)
    print("forcelist:", forcelist)

    sonuc: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, not_=""):
        sonuc.append((ad, bool(kosul), not_))

    try:
        # ── (1) YENİ DAVRANIŞ: 500 tekrar edilmez, gövde ulaşır ──────────────────
        _Kolu.sayac.clear()
        try:
            r = sess.get(kok + "/govde500", timeout=10)
            ekle("A1 500 -> istisna DEGIL, cevap dondu", True, "status=%s" % r.status_code)
            ekle("A2 500 status'u cagirana ulasti", r.status_code == 500)
            ekle("A3 500 GOVDESI cagirana ulasti (%s)" % IMZA, IMZA in (r.text or ""))
        except Exception as exc:
            ekle("A1 500 -> istisna DEGIL, cevap dondu", False, type(exc).__name__)
            ekle("A2 500 status'u cagirana ulasti", False, "istisna")
            ekle("A3 500 GOVDESI cagirana ulasti (%s)" % IMZA, False, str(exc)[:60])
        ekle("A4 500 TEKRAR EDILMEDI (tek istek)", _Kolu.sayac.get("/govde500") == 1,
             "istek=%s" % _Kolu.sayac.get("/govde500"))
        # yazma yolu da aynı sözleşmeye tabi (POST/PUT idempotent değil)
        _Kolu.sayac.clear()
        try:
            r = sess.post(kok + "/govde500", data=b"x", timeout=10)
            ekle("A5 POST 500 govdesi ulasti", IMZA in (r.text or ""))
        except Exception as exc:
            ekle("A5 POST 500 govdesi ulasti", False, type(exc).__name__)
        ekle("A6 POST 500 tekrar edilmedi", _Kolu.sayac.get("/govde500") == 1,
             "istek=%s" % _Kolu.sayac.get("/govde500"))

        # ── (2) FP ÇAPASI: gerçekten geçici statüler HÂLÂ tekrar edilir ──────────
        for ad, ucyol in (("B1 503", "/gecici503"), ("B2 429", "/gecici429"),
                          ("B3 502", "/gecici502")):
            _Kolu.sayac.clear()
            try:
                r = sess.get(kok + ucyol, timeout=10)
                nk = "istisnasiz dondu: %s" % r.status_code
            except Exception as exc:
                nk = type(exc).__name__
            tekrar = _Kolu.sayac.get(ucyol, 0)
            ekle("%s HALA tekrar ediliyor" % ad, tekrar >= 2, "istek=%d (%s)" % (tekrar, nk))
        _Kolu.sayac.clear()
        r = sess.get(kok + "/tamam", timeout=10)
        ekle("B4 200 saglam: tek istek + govde", r.status_code == 200
             and _Kolu.sayac.get("/tamam") == 1 and "<ok/>" in r.text)
        ekle("B5 500 forcelist'te YOK, 429/502/503/504 VAR",
             500 not in forcelist and {429, 502, 503, 504} <= set(forcelist), str(forcelist))
    finally:
        srv.shutdown()

    hata = 0
    for ad, ok, not_ in sonuc:
        hata += 0 if ok else 1
        print("[%s] %-45s %s" % ("ok" if ok else "FAIL", ad, not_))
    # ⚠ Kosucu ozeti bu bicimden ayristirir (run_fixture_tests: r"^\s*\d+/\d+ OK")
    print("%d/%d OK" % (len(sonuc) - hata, len(sonuc)))
    print("SONUC: %d/%d gecti" % (len(sonuc) - hata, len(sonuc)))
    return 1 if hata else 0


if __name__ == "__main__":
    arg = None
    if "--modul" in sys.argv:
        arg = sys.argv[sys.argv.index("--modul") + 1]
    sys.exit(main(arg))

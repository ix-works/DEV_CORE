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
  python tests/fixtures/retry_500_govde/run.py --mutasyon       # R1/R2 kum mutasyonlari (Issue #363)
  (mutasyon tabani PINLI SHA olmali: `git show ab37296:scripts/sap_adt_lib.py > <scratch>/eski.py`)
  ⛔ `origin/main` VERME: bu PR merge edilince o ref "fix SONRASI"na kayar ve korpus
     ayirt etmiyormus gibi gorunur — HATA VERMEDEN (belgelenmis sinif: hareketli ref =
     olcum aletinin sessiz bosalmasi, infra-changelog 2026-08-10). Kosucu tabani
     OZ-DENETLER: verilen modulde 500 forcelist'te DEGILSE exit 2 + [DOGRULANAMADI].

İKİNCİ KATMAN — `_retry_request` (DEV_CORE Issue #363, 2026-10-27) → C1..C8
  Bağdaştırıcı düzeltilmişti ama uygulama katmanı (`_should_retry` + `_retry_request`) hâlâ
  ① 500'ü 3 kez tekrarlıyordu ② SON denemede de bekleyip `continue` ediyor, döngü sonunda
  yanıtı ATIP `SAPConnectionError('... Unknown error')` fırlatıyordu ⇒ kalıcı 503'te de 500'de
  de SAP'nin gövdesi çağırana ULAŞMIYORDU. Vektörler istek fonksiyonunu ve `time.sleep`'i
  sahte çağrılarla ölçer (ağ yok); FP çapaları: 503→201 hâlâ tekrar edilip başarır (C3),
  CSRF dalı hâlâ taze token alır (C7), 408 hâlâ tekrar edilir (C8).
  ⚠ KAPSAM (bug-gate #378 F2): C2/C6 ("kalıcı 503/502'de son yanıt gövdesiyle döner") YALNIZ
  izole uygulama katmanının sözleşmesidir. GERÇEK oturumda 502/503/504 önce bağdaştırıcıda
  (`status_forcelist`) tekrarlanır ve `requests.exceptions.RetryError` ile biter (4 istek,
  gövde düşer — fix öncesi de böyleydi) ⇒ gerçek oturumda 503 gövdesi çağırana ULAŞMAZ.
  Gerçek oturumda gövdenin ulaştığı durum 500'dür (D1). D1/D2 iki katmanı birlikte koşar;
  D2 bugünkü 503 davranışını BELGELER (düzeltme değil).
  MUTASYON (`--mutasyon`): kum kopyasında iki geri-alma — R1 son-deneme koşulu eski hâline
  (`attempt >= self.max_retries`) → C2/C7 düşmeli · R2 500 tekrar kümesine geri → C1/D1 düşmeli.
  Her mutasyonun düşmesi BEKLENEN vektörü ilan edilir; kum tabanı (mutasyonsuz kopya) önce
  koşulur ve tam yeşil olmalıdır.

⚠ İZOLASYON: ölçülen TEK değişken adapter'ın `status_forcelist`'idir. `_build_session`in
  geri kalanı (pool, verify, header'lar) GERÇEK kodla koşar; yalnız `_get_auth_headers`
  örnek üzerinde boş sözlüğe bağlanır (kimlik doğrulama bu testin konusu değil ve canlı
  SAP gerektirirdi). Sunucu YEREL (127.0.0.1) — ağ/SAP bağımlılığı yoktur.
"""
from __future__ import annotations

import importlib.util
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


class _Yanit:
    def __init__(self, kod: int, govde: str):
        self.status_code = kod
        self.text = govde


def uygulama_katmani(mod, ekle) -> None:
    """C1..C8 — GERÇEK `_retry_request` + `_should_retry`; istek ve uyku sahte (ağ yok)."""
    c = mod.SAPADTClient.__new__(mod.SAPADTClient)
    c.max_retries, c.retry_delay = 3, 1.0
    c.retry_on_timeout = c.retry_on_csrf_fail = c.retry_on_5xx = True
    c.url = "http://127.0.0.1:1"
    csrf = []
    c.fetch_csrf_token = lambda force_refresh=False: csrf.append(force_refresh)
    uyku: list = []
    eski_time = mod.time
    mod.time = types.SimpleNamespace(sleep=lambda s: uyku.append(s), time=eski_time.time)

    def kos(seri):
        """`seri` sırayla dönülür (son eleman tekrar); (yanıt|istisna-adı, istek, uyku)."""
        istek = []
        uyku.clear()
        csrf.clear()

        def f():
            istek.append(1)
            return seri[min(len(istek), len(seri)) - 1]
        try:
            r = c._retry_request(f, "fixture")
        except Exception as exc:                     # çökme != FAIL: istisna ÖLÇÜLÜR
            r = type(exc).__name__ + ": " + str(exc)[:80]
        return r, len(istek), list(uyku)

    try:
        r, n, u = kos([_Yanit(500, GOVDE_500)])
        ekle("C1 500 -> TEK istek, uyku yok, yanit+GOVDE cagirana doner",
             n == 1 and not u and isinstance(r, _Yanit) and IMZA in r.text,
             "istek=%d uyku=%s r=%s" % (n, u, getattr(r, "status_code", r)))
        r, n, u = kos([_Yanit(503, "gecici-govde")])
        ekle("C2 kalici 503 -> 3 istek, SON yanit govdesiyle doner (istisna DEGIL)",
             n == 3 and isinstance(r, _Yanit) and r.status_code == 503 and r.text == "gecici-govde",
             "istek=%d r=%s" % (n, getattr(r, "status_code", r)))
        ekle("C2b son denemeden sonra UYKU YOK (2 bekleme, 3 degil)", len(u) == 2, "uyku=%s" % u)
        r, n, u = kos([_Yanit(503, "gecici"), _Yanit(201, "<ok/>")])
        ekle("C3 503 -> 201: tekrar HALA calisir (FP capasi)",
             n == 2 and isinstance(r, _Yanit) and r.status_code == 201, "istek=%d" % n)
        r, n, u = kos([_Yanit(400, "kalici-red")])
        ekle("C4 400 -> tek istek, yanit doner", n == 1 and getattr(r, "status_code", None) == 400,
             "istek=%d" % n)
        r, n, u = kos([_Yanit(201, "<ok/>")])
        ekle("C5 201 -> tek istek", n == 1 and getattr(r, "status_code", None) == 201, "istek=%d" % n)
        r, n, u = kos([_Yanit(502, "gecici")])
        ekle("C6 kalici 502 -> 3 istek + son yanit doner",
             n == 3 and getattr(r, "status_code", None) == 502, "istek=%d r=%s" % (n, r))
        r, n, u = kos([_Yanit(403, "CSRF token validation failed")])
        ekle("C7 kalici CSRF 403 -> 3 istek, 2 TAZE token, son yanit doner (CSRF dali korundu)",
             n == 3 and csrf == [True, True] and getattr(r, "status_code", None) == 403,
             "istek=%d csrf=%s r=%s" % (n, csrf, getattr(r, "status_code", r)))
        r, n, u = kos([_Yanit(408, "zaman"), _Yanit(200, "<ok/>")])
        ekle("C8 408 -> 200: zaman asimi tekrari korundu", n == 2
             and getattr(r, "status_code", None) == 200, "istek=%d" % n)
    finally:
        mod.time = eski_time


def birlesik(mod, sess, kok: str, ekle) -> None:
    """D1/D2 — iki katman BİRLİKTE: istek `_build_session` oturumundan (gerçek bağdaştırıcı)
    yerel sahte sunucuya gider, `_retry_request` onu sarar.

    D1: 500 → toplam 1 istek, gövde çağırana ulaşır (iki katman da 500'ü tekrarlamaz).
    D2 — MEVCUT DAVRANIŞI BELGELER (düzeltme DEĞİL): kalıcı 503'te bağdaştırıcı 4 istek atıp
    `requests.exceptions.RetryError` fırlatır; `_retry_request` onu yakalamaz ⇒ 503 gövdesi
    gerçek oturumda çağırana ULAŞMAZ (fix öncesi de böyleydi). C2/C6 bu yüzden YALNIZ uygulama
    katmanının sözleşmesidir. 503 gövdesini ulaştırmak ayrı bir karardır; o yapılırsa D2
    bilerek güncellenir.
    """
    import requests
    c = mod.SAPADTClient.__new__(mod.SAPADTClient)
    c.max_retries, c.retry_delay = 3, 0.01
    c.retry_on_timeout = c.retry_on_csrf_fail = c.retry_on_5xx = True
    c.url = kok
    c.fetch_csrf_token = lambda force_refresh=False: None
    _Kolu.sayac.clear()
    try:
        r = c._retry_request(lambda: sess.get(kok + "/govde500", timeout=10), "fixture")
        nk = r.status_code, IMZA in (r.text or "")
    except Exception as exc:
        nk = type(exc).__name__, False
    ekle("D1 birlesik 500 -> toplam TEK istek + govde cagirana ulasir",
         _Kolu.sayac.get("/govde500") == 1 and nk == (500, True),
         "istek=%s sonuc=%s" % (_Kolu.sayac.get("/govde500"), nk))
    _Kolu.sayac.clear()
    try:
        r = c._retry_request(lambda: sess.get(kok + "/gecici503", timeout=10), "fixture")
        nk = "yanit %s" % r.status_code
    except requests.exceptions.RetryError:
        nk = "RetryError"
    except Exception as exc:
        nk = type(exc).__name__
    ekle("D2 [MEVCUT DAVRANIS] birlesik kalici 503 -> bagdastirici 4 istek + RetryError (govde ULASMAZ)",
         _Kolu.sayac.get("/gecici503") == 4 and nk == "RetryError",
         "istek=%s sonuc=%s" % (_Kolu.sayac.get("/gecici503"), nk))


def main(modul_yolu: str | None = None, taban_denetimi: bool = True) -> int:
    yol = Path(modul_yolu) if modul_yolu else (REPO / "scripts" / "sap_adt_lib.py")
    if not yol.is_file():
        sys.stderr.write("OLCULEMEDI: modul yok: %s\n" % yol)
        return 2
    mod = modul_yukle(yol)
    sess = oturum_kur(mod)
    forcelist = tuple(sess.get_adapter("http://x/").max_retries.status_forcelist)
    # TABAN OZ-DENETIMI: mutasyon modunda taban GERCEKTEN kusurlu olmali; degilse hicbir
    # sayi raporlanmaz (hareketli-ref sinifi, bkz. docstring). `--mutasyon` kipinin kendi
    # kum kopyalari bu denetimden muaftir (onlar bilerek tek noktada bozulur).
    if modul_yolu and taban_denetimi and 500 not in forcelist:
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

        # ── (3) UYGULAMA KATMANI: `_retry_request` (Issue #363) ───────────────────
        try:
            uygulama_katmani(mod, ekle)
        except Exception as exc:                      # çökme != FAIL: ölçülür
            ekle("[BOLUM COKTU] uygulama_katmani", False, "%s: %s" % (type(exc).__name__, exc))

        # ── (4) BİRLEŞİK: GERÇEK oturum (bağdaştırıcı) + `_retry_request` (bug-gate #378 F2) ──
        try:
            birlesik(mod, sess, kok, ekle)
        except Exception as exc:                      # çökme != FAIL: ölçülür
            ekle("[BOLUM COKTU] birlesik", False, "%s: %s" % (type(exc).__name__, exc))
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


# (ad, eski, yeni, düşmesi BEKLENEN vektör önekleri) — CORE-07: çapa TAM 1 kez eşleşmeli.
MUTASYONLAR = [
    ("R1 son deneme yine tekrar edilir (eski kosul)",
     "        if attempt >= self.max_retries - 1:\n",
     "        if attempt >= self.max_retries:\n", ("C2 ", "C2b", "C7 ")),
    ("R2 500 uygulama katmaninda yine tekrar edilir",
     "        if status >= 500 and status != 500:\n",
     "        if status >= 500:\n", ("C1 ", "D1 ")),
]


def _mutasyon() -> int:
    """Kum kopyası: önce TABAN (mutasyonsuz kopya tam yeşil olmalı), sonra her mutasyon.

    Çıkış: 0 = hepsi beklenen vektörle YAKALANDI · 1 = KAÇTI/sapma · 3 = KURULAMADI.
    """
    kaynak = (REPO / "scripts" / "sap_adt_lib.py").read_bytes().decode("utf-8")
    kum = Path(tempfile.mkdtemp(prefix="retry500_kum_"))
    kotu, kurulamadi = [], []

    def kos(metin: str):
        hedef = kum / "sap_adt_lib.py"
        hedef.write_bytes(metin.encode("utf-8"))
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--modul", str(hedef),
                            "--kum"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
        dusen = [s.strip()[len("[FAIL] "):] for s in r.stdout.splitlines()
                 if s.strip().startswith("[FAIL]")]
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        return r.returncode, (m.group(0) if m else None), dusen, r.stdout + r.stderr

    try:
        rc, skor, dusen, cikti = kos(kaynak)
        print("--> [KUM TABANI] rc=%s %s" % (rc, skor))
        if rc != 0 or not skor or dusen:
            print("[KURULAMADI] kum tabani yesil degil: %s\n%s" % (dusen, cikti[-600:]))
            return 3
        for ad, eski, yeni, beklenen in MUTASYONLAR:
            if kaynak.count(eski) != 1:
                print("  [KURULAMADI] %s -> capa %d kez" % (ad, kaynak.count(eski)))
                kurulamadi.append(ad)
                continue
            rc, skor, dusen, cikti = kos(kaynak.replace(eski, yeni, 1))
            if skor is None:
                durum = "COKTU"
            else:
                eksik = [b for b in beklenen if not any(d.startswith(b) for d in dusen)]
                durum = "YAKALANDI" if rc != 0 and not eksik else "KACTI(beklenen dusmedi: %s)" % eksik
            if durum != "YAKALANDI":
                kotu.append(ad)
            print("--> [%s] rc=%s %s -> %s" % (ad, rc, skor or "-", durum))
            for d in dusen[:4]:
                print("      [FAIL] %s" % d[:110])
    finally:
        shutil.rmtree(kum, ignore_errors=True)
    n = len(MUTASYONLAR)
    print("\nMUTASYON OZETI: %d/%d yakalandi" % (n - len(kotu) - len(kurulamadi), n))
    if kurulamadi:
        return 3
    return 1 if kotu else 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(_mutasyon())
    arg = None
    if "--modul" in sys.argv:
        arg = sys.argv[sys.argv.index("--modul") + 1]
    sys.exit(main(arg, taban_denetimi="--kum" not in sys.argv))

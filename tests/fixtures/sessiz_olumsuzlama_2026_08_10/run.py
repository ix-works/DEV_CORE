# -*- coding: utf-8 -*-
"""SESSİZ OLUMSUZLAMA — bir aracın `false`/`0`'ı, GÖREMEDİĞİ katman için "hayır" değildir.

2026-08-10 bağlama turunda kayda geçen 7 araç kusurunun DÖRDÜ tek kök paylaşır: araç bir
HTTP/parse arızasını sessizce NEGATİF BİR SONUCA çevirdi ve çağıran onu kanıt sandı.
Üçü lideri fiilen yanılttı.

  A · `adt_transport_list` → `count:0` (sistemde 4 açık transport VARDI)
      kök: `sap_client.list_user_transports` `except Exception: return []` **+** ayrıştırıcı
      tek namespace'e çivili, oysa `user_transports()` 12 Accept header dener ve şekil
      Accept'e göre değişir.
  B · `adt_lock_check` → `/adt/locks` HTTP **404** → araç `locked:false` dedi (obje kilitliydi)
      kök: `sap_adt_lib.is_object_locked` 404 dalı. ⚠ İÇ KONTROL GRUBU: AYNI DOSYA aynı
      statüyü `lock_object`'te *"endpoint not found"* diye okur (satır ~2700 + ~2910 yorumu).
      Tek statü, iki karşıt yorum — biri uç-yokluğunu obje-hakkında-iddiaya çeviriyordu.
  C · `lock_object` uyuşmazlıkta `'NO_LOCK_SUPPORT'` **string'ini** lock handle gibi döndürdü
      kök: döngü-sonu KOŞULSUZ sentinel döndürüyordu, oysa hemen üstündeki yorum
      *"Only return NO_LOCK_SUPPORT if we got 404"* diyordu → DOKÜMAN KODU YALANLIYORDU.
  D · `deploy_ui --dry-run` sonunda **"canlı Component-preload == build çıktısı"** yazdı —
      oysa dry-run canlıya HİÇ bakmaz (`deploy_one`: `if dry: return`). App STALE'di.
      kök: mod banner'ı ÜÇ yollu, özet satırı İKİ yolluydu.

⛔ BU KORPUSUN OMURGASI FP ÇAPALARIDIR — hepsi "dürüst olumsuzlama HÂLÂ mümkün" der ve
   İKİ SÜRÜMDE DE geçmelidir (A5, B2, C1, D2/D3). Bunlar kalkarsa fix aşırı-sıkılaşır:
   · A5 yoksa gerçekten 0 transport'u olan kullanıcı hata alır
   · B2 yoksa araç hiçbir zaman "kilitli değil" diyemez (tool işlevsizleşir)
   · C1 yoksa kilit ucu OLMAYAN sistemlerde TÜM push'lar kapanır (#99'un birebir tekrarı)
   · D2/D3 yoksa gerçek deploy'un doğrulama cümlesi de silinmiş olur

Koşum   : python tests/fixtures/sessiz_olumsuzlama_2026_08_10/run.py           → 24/24
MUTASYON: python tests/fixtures/sessiz_olumsuzlama_2026_08_10/run.py --mutasyon → ayırt edici FAIL'ler
          (taban = `990f71b`, DÖRT kusurun da CANLI olduğu SHA; git'ten yüklenir)
          ⚠ `--ref`e DAL ADI VERME (D2/5). `origin/main` bu fix merge edilince "fix
            SONRASI"na kayar, ayırt edici vektörler PASS'e döner ve komut HATA VERMEDEN
            "korpus ölçmüyor" izlenimi verir. Taban öz-denetimi bunu yakalar → exit 2.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# ⛔ TEŞHİS AKIŞI — düz `print()` KULLANILMAZ (2026-08-29, CI run 33265820879).
# `yukle()` sap_client import-anı koruması için sys.stdout/sys.stderr'i BytesIO ile
# SARMALAR; `git_show()` tam o pencerenin İÇİNDEN çağrılır. Kurulum sebebi `print()`
# ile basılırsa ATILAN tampona gider ve `sys.exit(2)` sonrası dışarıdan görülen tek şey
# `KURULAMADI(rc=2): <boş>` olur — yani ARIZA VAR ama SEBEBİ YOK (teşhis edilemez).
# Gerçek akış, swap'tan önce (burada) yakalanır; reconfigure SONRASI olduğu için
# `errors="replace"` mirasla gelir (cp1254 kabukta `→` patlatmaz).
_GERCEK_ERR = sys.stderr

KOK = Path(__file__).resolve().parents[3]
SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


ap = argparse.ArgumentParser(add_help=True)
ap.add_argument("--mutasyon", action="store_true",
                help="fix ÖNCESİ sürümleri yükle (ayırt-etme kanıtı)")
# ⚠ SABİT SHA — DAL ADI DEĞİL (D2/5). 990f71b = bu worktree'nin tabanı; dört kusur da
# orada CANLI. Hareketli ref (origin/main) ölçüm aletini fix merge edilir edilmez boşaltır.
ap.add_argument("--ref", default="990f71b",
                help="mutasyon tabanı: kusurların CANLI olduğu SHA (dal adı VERME — kayar)")
ARG = ap.parse_args()

# Kum havuzu: sap_adt_lib import ANINDA cwd/env'den .conn_adt çözer.
KUM = Path(tempfile.mkdtemp(prefix="sessiz_"))
_eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
(KUM / ".conn_adt").write_text(
    "ADT_SAP_URL=https://ornek.invalid\nADT_SAP_USER=TESTUSER\n"
    "ADT_SAP_PASSWORD=x\nADT_SAP_CLIENT=100\nADT_SAP_TIER=DEV\n", encoding="utf-8")
(KUM / "ui" / "app1").mkdir(parents=True, exist_ok=True)
os.chdir(KUM)
sys.path.insert(0, str(KOK / "scripts"))


def git_show(rel: str) -> str:
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{ARG.ref}:{rel}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"[DOĞRULANAMADI] git show {ARG.ref}:{rel} → {r.stderr.strip()[:200]}",
              file=_GERCEK_ERR, flush=True)
        print("  Tipik sebep: SIĞ KLON (CI `actions/checkout` fetch-depth 1) — pinli "
              "taban SHA'nın blob'u o klonda YOK.", file=_GERCEK_ERR, flush=True)
        sys.exit(2)
    return r.stdout


def yukle(rel: str, ad: str):
    """Modülü çalışma ağacından ya da (--mutasyon) taban SHA'dan yükle.

    ⚠ D2/4: `sap_client.py` modül gövdesinde `sys.stdout = io.TextIOWrapper(...)` yapar.
    Sarmalayıcı çöp toplandığında ALTTAKİ GERÇEK buffer'ı KAPATIR → testin geri kalanı
    "I/O operation on closed file" ile ölür ve HİÇBİR sonuç satırı basılmaz (sayaç bile).
    Bu yüzden import ATILABİLİR akışlara yapılır, sonra yedek geri konur.
    """
    yedek_out, yedek_err = sys.stdout, sys.stderr
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    try:
        if ARG.mutasyon:
            p = KUM / f"{ad}_taban.py"
            p.write_text(git_show(rel), encoding="utf-8")
            spec = importlib.util.spec_from_file_location(ad, p)
            m = importlib.util.module_from_spec(spec)      # type: ignore[arg-type]
            sys.modules[ad] = m
            spec.loader.exec_module(m)                     # type: ignore[union-attr]
            return m
        return importlib.import_module(ad)
    finally:
        sys.stdout, sys.stderr = yedek_out, yedek_err


L = yukle("scripts/sap_adt_lib.py", "sap_adt_lib")
SC = yukle("scripts/sap_client.py", "sap_client")

if ARG.mutasyon:
    print(f"### MUTASYON MODU — sap_adt_lib/sap_client/deploy_ui @ {ARG.ref} (fix ÖNCESİ)\n")


class SahteYanit:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code
        self.cookies = {}
        self.headers = {}


# =============================================================================
# A — TRANSPORT LİSTESİ: "0 transport" KANIT MI, OKUYAMAMA MI? (KUSUR-1)
# =============================================================================
TM_NS = "http://www.sap.com/cts/adt/tm"


def tm_feed(sayi: int) -> str:
    """Kanonik CTS feed'i (ayrıştırıcının ÇİVİLENDİĞİ şekil)."""
    satirlar = "".join(
        f'<tm:request tm:number="DS4K90{1000 + i}" tm:desc="Is {i}" tm:status="D"/>'
        for i in range(sayi))
    return f'<?xml version="1.0"?><tm:root xmlns:tm="{TM_NS}">{satirlar}</tm:root>'


def tm_feed_varyant(sayi: int) -> str:
    """AYNI VERİ, BAŞKA ŞEKİL — fallback Accept header'ın döndürebileceği hâl:
    namespace YOK, attribute'lar nitelenmemiş. Eski ayrıştırıcı burada SESSİZ 0 verir."""
    satirlar = "".join(
        f'<request number="DS4K90{1000 + i}" desc="Is {i}" status="D"/>' for i in range(sayi))
    return (f'<?xml version="1.0"?><root xmlns:tm="{TM_NS}">'
            f'<workbench>{satirlar}</workbench></root>')


def sahte_sc(xml=None, patlat=None, accept="application/vnd.sap.adt.transportorganizer.v1+xml"):
    c = object.__new__(SC.SAPClient)

    class _Adt:
        _last_transport_accept = accept

        def user_transports(self, user=None, **kw):
            if patlat is not None:
                raise patlat
            return xml

    c.adt_client = _Adt()
    return c


def transport_cagir(**kw):
    """(sonuc, deger, istemci) — sonuc: 'ok' | 'hata' | 'cokme'."""
    c = sahte_sc(**kw)
    tampon = io.StringIO()
    try:
        with redirect_stdout(tampon):
            return "ok", c.list_user_transports(), c
    except Exception as exc:                                    # noqa: BLE001
        tip = type(exc).__name__
        return ("hata" if "Transport" in tip or "SAPADT" in tip else "cokme"), exc, c


# ── ÖZ-DENETİM: taban gerçekten "fix ÖNCESİ" mi? ─────────────────────────────
# "Doğrulama koşamadı ≠ doğrulandı"nın mutasyon-tarafı: yanlış tabanla koşan bir korpus
# SAYI ÜRETİR ve o sayı yanıltır. Taban geçersizse HİÇBİR vektör raporlanmaz → exit 2.
if ARG.mutasyon:
    _s, _d, _ = transport_cagir(xml="<bozuk")
    _s2, _d2, _ = transport_cagir(xml=tm_feed_varyant(4))
    if _s != "ok" or _d != [] or _s2 != "ok" or _d2 != []:
        print(f"[DOĞRULANAMADI] MUTASYON TABANI GEÇERSİZ: '{ARG.ref}' sessiz-sıfır veren "
              f"sürüm DEĞİL (bozuk-XML→{_s}/{_d!r}, "
              f"varyant-şekil→{_s2}/{len(_d2) if isinstance(_d2, list) else _d2}).")
        print("  Tipik sebep: --ref bir DAL adı (ör. origin/main) ve fix merge edildi →")
        print("  taban 'fix SONRASI'na kaydı; korpus ayırt etmiyormuş GİBİ görünür.")
        print("  Çözüm: kusurların CANLI olduğu SHA'yı ver → --ref 990f71b")
        os.chdir(_eski_cwd)
        shutil.rmtree(KUM, ignore_errors=True)
        sys.exit(2)
    print("### taban öz-denetimi OK — bu ref'te sessiz-sıfır GERÇEKTEN üretiliyor\n")

# A1 KONTROL GRUBU (bilinen-temiz) — iki sürümde de geçmeli
sonuc, deger, _ = transport_cagir(xml=tm_feed(4))
kontrol("A1 KONTROL: kanonik tm feed'inde 4 transport → 4 ayrıştırılır (davranış korundu)",
        sonuc == "ok" and isinstance(deger, list) and len(deger) == 4
        and deger[0]["number"] == "DS4K901000" and deger[0]["status"] == "D",
        f"sonuç={sonuc} değer={str(deger)[:200]}")

# A2 AYIRT EDİCİ — şekil körlüğü (fallback Accept header sınıfı)
sonuc, deger, _ = transport_cagir(xml=tm_feed_varyant(4), accept="application/xml")
kontrol("A2 AYIRT EDİCİ: BAŞKA ŞEKİLDEKİ aynı 4 transport da bulunur (namespace-bağımsız)",
        sonuc == "ok" and isinstance(deger, list) and len(deger) == 4,
        f"sonuç={sonuc} bulunan={len(deger) if isinstance(deger, list) else deger!r} "
        f"(fix öncesi: 0 — sessizce 'transport yok')")

# A3 AYIRT EDİCİ — yutulan parse hatası
sonuc, deger, _ = transport_cagir(xml="<tm:root xmlns:tm='x'><bozuk")
kontrol("A3 AYIRT EDİCİ: bozuk XML → HATA (eskiden sessiz [] = 'transport yok')",
        sonuc == "hata" and "AYRIŞTIRILAMADI" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:200]!r}")

# A4 AYIRT EDİCİ — alt katman istisnası yutulmuyor
sonuc, deger, _ = transport_cagir(patlat=RuntimeError("ag koptu"))
kontrol("A4 AYIRT EDİCİ: alt katman istisnası YUKARI ÇIKAR (eskiden [] olup yutuluyordu)",
        sonuc in ("hata", "cokme") and "ag koptu" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:160]!r}")

# A5 FP ÇAPASI — GERÇEK sıfır hâlâ mümkün (İKİ SÜRÜMDE DE geçer)
sonuc, deger, _ = transport_cagir(xml=tm_feed(0))
kontrol("A5 FP ÇAPASI: geçerli tm feed'i + hiç request → 0, HATA YOK (kanıtlanmış sıfır)",
        sonuc == "ok" and deger == [],
        f"sonuç={sonuc} değer={str(deger)[:160]!r}")

# A6 AYIRT EDİCİ — tanınmayan gövde (200 dönen HTML hata sayfası vb.)
sonuc, deger, _ = transport_cagir(xml="<html><body>Service unavailable</body></html>")
kontrol("A6 AYIRT EDİCİ: tanınmayan gövde → 'ŞEKLİ TANINMADI' hatası (sıfır İDDİA EDİLMEZ)",
        sonuc == "hata" and "ŞEKLİ TANINMADI" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:200]!r}")

# A7 TEŞHİS İZİ — "0" cevabının dayanağı yanıta taşınıyor
sonuc, deger, c = transport_cagir(xml=tm_feed(0), accept="application/xml")
meta = getattr(c, "_last_transport_meta", None)
kontrol("A7 TEŞHİS İZİ: hangi Accept cevapladı + şekil tanındı mı KAYDEDİLİYOR",
        isinstance(meta, dict) and meta.get("accept") == "application/xml"
        and meta.get("shape_recognized") is True,
        f"meta={meta!r}")

# =============================================================================
# B — KİLİT SONDASI: 404 "kilitli değil" DEĞİLDİR (KUSUR-2)
# =============================================================================
SAHIP = "TESTOWNER"          # jenerik — gerçek kimlik YAZILMAZ (genericize kuralı)
KILIT_XML = ('<asx:abap xmlns:asx="http://www.sap.com/abapxml"><values><DATA>'
             '<LOCK_HANDLE>ABCDEF0123</LOCK_HANDLE>'
             f'<LOCK_OWNER>{SAHIP}</LOCK_OWNER>'
             '</DATA></values></asx:abap>')


def kilit_cagir(status, govde="", patlat=None):
    c = object.__new__(L.SAPADTClient)
    c.url = ""
    c.timeout_short = 5
    c.debug_enabled = False
    c._get_headers = lambda *a, **k: {}

    class _Oturum:
        def get(self, *a, **k):
            if patlat is not None:
                raise patlat
            return SahteYanit(govde, status)

    c.session = _Oturum()
    return c.is_object_locked("/sap/bc/adt/oo/classes/zcl_ornek"), c


# B1 KONTROL — gerçek kilit tespiti (iki sürümde de)
deger, _ = kilit_cagir(200, KILIT_XML)
kontrol("B1 KONTROL: HTTP 200 + LOCK_HANDLE → locked:True + sahip okunur",
        isinstance(deger, dict) and deger.get("locked") is True
        and deger.get("lock_owner") == SAHIP,
        f"değer={deger!r}")

# B2 FP ÇAPASI — DÜRÜST OLUMSUZLAMA KORUNUR (iki sürümde de; OMURGA)
deger, _ = kilit_cagir(200, "<asx:abap><values><DATA/></values></asx:abap>")
kontrol("B2 FP ÇAPASI: HTTP 200 + kilit yok → locked:False (dürüst 'hayır' HÂLÂ mümkün)",
        isinstance(deger, dict) and deger.get("locked") is False,
        f"değer={deger!r}")

# B3 AYIRT EDİCİ — kusurun ta kendisi
deger, c = kilit_cagir(404)
kontrol("B3 AYIRT EDİCİ: HTTP 404 (uç YOK) → None; ARTIK 'locked:False' İDDİA EDİLMİYOR",
        deger is None,
        f"değer={deger!r} (fix öncesi: dict(locked=False) — lideri yanıltan cevap)")

kontrol("B3b KABLOLAMA: 404 sonucu dict DEĞİL → MCP katmanı onu `locked:null`+ok:false yapar",
        not isinstance(deger, dict),
        f"tip={type(deger).__name__} (adt_lock_check ayrımı: `isinstance(bilgi, dict)`)")

kontrol("B3c TEŞHİS: sebep kaydedildi (404 mü, 500 mü, ağ mı — 'araç bozuk'a saplanmasın)",
        getattr(c, "_last_lock_check_reason", None) == "http_404",
        f"sebep={getattr(c, '_last_lock_check_reason', '<yok>')!r}")

# B4 — sunucu hatası zaten None'dı (regresyon çapası; iki sürümde de)
deger, _ = kilit_cagir(500)
kontrol("B4 REGRESYON: HTTP 500 → None (bu dal zaten doğruydu, bozulmadı)",
        deger is None, f"değer={deger!r}")

# B5 — ağ hatası
deger, c = kilit_cagir(200, patlat=RuntimeError("timeout"))
kontrol("B5 ağ hatası → None + sebep kaydı (yokluk/kilitsizlik BEYAN EDİLMEZ)",
        deger is None and "timeout" in str(getattr(c, "_last_lock_check_reason", "")),
        f"değer={deger!r} sebep={getattr(c, '_last_lock_check_reason', '<yok>')!r}")


# =============================================================================
# C — lock_object SENTINEL'İ: "uç yok" mu, "kilit alınamadı" mı? (KUSUR-3)
# =============================================================================
def lock_cagir(statuler):
    """statuler: her POST çağrısı için sırayla dönecek HTTP statüsü listesi."""
    c = object.__new__(L.SAPADTClient)
    c.url = ""
    c.timeout_short = 5
    c.debug_enabled = False
    c.csrf_token = "TOKEN"
    c.user = "TESTUSER"
    c._get_headers = lambda *a, **k: {}
    c._update_cookies = lambda r: None
    kalan = list(statuler)

    class _Oturum:
        def post(self, *a, **k):
            s = kalan.pop(0) if kalan else 500
            if s == 200:
                return SahteYanit(
                    '<asx:abap xmlns:asx="http://www.sap.com/abapxml"><asx:values><DATA>'
                    '<LOCK_HANDLE>HANDLE123</LOCK_HANDLE><CORRNR/><IS_LINK_UP/>'
                    '</DATA></asx:values></asx:abap>', 200)
            return SahteYanit("<err/>", s)

    c.session = _Oturum()
    tampon = io.StringIO()
    try:
        with redirect_stdout(tampon):
            return "ok", c.lock_object("/sap/bc/adt/oo/classes/zcl_ornek",
                                       transport="DS4K900029"), c
    except L.SAPLockError as exc:
        return "hata", exc, c
    except Exception as exc:                                    # noqa: BLE001
        return "cokme", exc, c


# C1 FP ÇAPASI — OMURGA: kilit ucu OLMAYAN sistem çalışmaya devam eder (iki sürümde de)
sonuc, deger, c = lock_cagir([404, 404, 404])
kontrol("C1 FP ÇAPASI: TÜM stratejiler 404 → 'NO_LOCK_SUPPORT' (uç gerçekten yok; push AÇIK)",
        sonuc == "ok" and deger == "NO_LOCK_SUPPORT",
        f"sonuç={sonuc} değer={str(deger)[:160]!r} "
        f"[#99 regresyonunun çapası — kalkarsa kilitsiz sistemlerde her push kapanır]")

kontrol("C1b SEBEP AYRIMI: 404-yokluğu 'ENDPOINT_ABSENT_404' diye etiketlenir",
        getattr(c, "_last_lock_no_support_reason", None) == "ENDPOINT_ABSENT_404",
        f"sebep={getattr(c, '_last_lock_no_support_reason', '<yok>')!r}")

# C2 AYIRT EDİCİ — sunucu arızası artık "uç yok" diye maskelenmiyor
sonuc, deger, _ = lock_cagir([500, 500, 500])
kontrol("C2 AYIRT EDİCİ: TÜMÜ 500 → SAPLockError (eskiden sessizce 'NO_LOCK_SUPPORT'du)",
        sonuc == "hata" and "kilit ucu yok" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:180]!r}")

# C3 AYIRT EDİCİ — yetki hatası
sonuc, deger, _ = lock_cagir([403, 403, 403])
kontrol("C3 AYIRT EDİCİ: 403 yetki → SAPLockError (yetkisizlik 'lock yok'a dönüşmüyor)",
        sonuc == "hata" and "403" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:180]!r}")

# C4 AYIRT EDİCİ — KARIŞIK: tek bir non-404 kanıt yeter
sonuc, deger, _ = lock_cagir([404, 500, 404])
kontrol("C4 AYIRT EDİCİ: KARIŞIK (404+500) → hata; 'hepsi 404' şartı gerçekten aranıyor",
        sonuc == "hata", f"sonuç={sonuc} değer={str(deger)[:160]!r}")

# C5 KONTROL — başarı yolu değişmedi
sonuc, deger, _ = lock_cagir([200])
kontrol("C5 KONTROL: ilk strateji 200 → gerçek lock handle döner (başarı yolu bozulmadı)",
        sonuc == "ok" and deger == "HANDLE123",
        f"sonuç={sonuc} değer={str(deger)[:120]!r}")

# C6 KONTROL — 2. strateji kurtarıyor (404 sonrası 200)
sonuc, deger, _ = lock_cagir([404, 200])
kontrol("C6 KONTROL: 404 → sonraki strateji 200 → handle döner (fallback zinciri sağlam)",
        sonuc == "ok" and deger == "HANDLE123",
        f"sonuç={sonuc} değer={str(deger)[:120]!r}")

# C7 REGRESYON — 409 transport çakışması davranışı DEĞİŞMEDİ
sonuc, deger, _ = lock_cagir([409])
kontrol("C7 REGRESYON: 409 hâlâ SAPLockError (transport çakışma dalına dokunulmadı)",
        sonuc == "hata" and "locked under transport" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:160]!r}")

# =============================================================================
# D — deploy_ui ÖZET SATIRI: koşmayan doğrulama BEYAN EDİLMEZ (KUSUR-7)
# =============================================================================
D = yukle("scripts/deploy_ui.py", "deploy_ui")
D.REPO = KUM
D.deploy_one = lambda app, ui_root, conn, env, dry, verify_only: (
    app, True, "dry-run (build OK, BSP=ZTEST, deploy+dogrulama YOK)")


def deploy_cagir(*bayraklar):
    eski = sys.argv
    sys.argv = ["deploy_ui.py", "--app", "app1", "--ui-root", str(KUM / "ui"), *bayraklar]
    tampon, hata = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(tampon), redirect_stderr(hata):
            rc = D.main()
    except SystemExit as e:
        rc = e.code
    finally:
        sys.argv = eski
    return rc, tampon.getvalue() + hata.getvalue()


rc, cikti = deploy_cagir("--dry-run")
# D1 AYIRT EDİCİ — kusurun ta kendisi: dry-run DEPLOY cümlesini basıyordu
kontrol("D1 AYIRT EDİCİ: --dry-run çıktısında 'canlı ... == build çıktısı' İDDİASI YOK",
        "canlı Component-preload == build çıktısı" not in cikti,
        f"rc={rc} çıktı={cikti.strip()[-240:]!r}")

kontrol("D1b AYIRT EDİCİ: --dry-run 'doğrulandı' DEMİYOR (koşmayan doğrulamayı beyan etme)",
        "doğrulandı" not in cikti,
        f"çıktı={cikti.strip()[-240:]!r}")

kontrol("D1c GÖRÜNÜRLÜK: --dry-run ne YAPMADIĞINI açıkça söylüyor + doğru komutu veriyor",
        "CANLI İÇERİK OKUNMADI" in cikti and "--verify-only" in cikti,
        f"çıktı={cikti.strip()[-240:]!r}")

# D2 FP ÇAPASI — gerçek deploy'un doğrulama cümlesi DURUYOR (iki sürümde de)
rc2, cikti2 = deploy_cagir()
kontrol("D2 FP ÇAPASI: bayraksız (gerçek deploy) → 'canlı Component-preload == build "
        "çıktısı' HÂLÂ basılır",
        rc2 == 0 and "canlı Component-preload == build çıktısı" in cikti2,
        f"rc={rc2} çıktı={cikti2.strip()[-200:]!r}")

# D3 FP ÇAPASI — verify-only cümlesi DURUYOR (iki sürümde de)
rc3, cikti3 = deploy_cagir("--verify-only")
kontrol("D3 FP ÇAPASI: --verify-only → 'canlı == mevcut kaynak' HÂLÂ basılır (mesaj silinmedi)",
        rc3 == 0 and "canlı == mevcut kaynak" in cikti3,
        f"rc={rc3} çıktı={cikti3.strip()[-200:]!r}")

# D4 — mod banner'ı üç-yollu kalmalı (özet satırıyla hizalı)
kontrol("D4 HİZA: mod banner'ı [DRY-RUN] diyor VE özet satırı da dry-run'a özel",
        "[DRY-RUN]" in cikti and "DRY-RUN bitti" in cikti,
        f"çıktı={cikti.strip()[:200]!r}")

# =============================================================================
# F — "Bug 11 sessiz fallback": _find_existing_transport (SINIF A'nın 5. üyesi)
# =============================================================================
# Kök: `sap_client.py` `_find_existing_transport` `except Exception` → yalnız
# `debug_enabled` açıkken TEK debug satırı → kapalıyken (varsayılan) HİÇBİR iz yok.
# ⚠ Kanıt bu fonksiyonun KENDİ docstring'inde: *"Falls back **silently**"* (itiraf) +
# History satırı *"The except-clause silently swallowed the error → fix was a no-op"* —
# yani bu except, kendisini düzeltmeye çalışan fix'i de gizledi ve aylarca fark edilmedi.
#
# ⚠ FALLBACK KALDIRILMADI, SESSİZLİK KALDIRILDI. E071'e erişimi olmayan sistemlerde bu
# sorgu HTTP 500 verir ve push'un YİNE DE yürümesi gerekir (push_object'teki "Bug 11
# auto-retry" tam bu duruma göre yazılmış). Doğru fix "raise" DEĞİL, GÜRÜLTÜLÜ DEVAM:
# sonuç aynı, ama "doğrulandı" ile "varsayıldı" artık ayırt edilebilir.
DP_NS = "http://www.sap.com/adt/dataPreview"


def dp_govde(sutunlar: dict) -> str:
    """Gerçek datapreview şekli: her sütun `dp:metadata@name` + `dp:data` listesi."""
    bloklar = ""
    for ad, degerler in sutunlar.items():
        veri = "".join(f"<dp:data>{d}</dp:data>" for d in degerler)
        bloklar += (f'<dp:columns><dp:metadata dp:name="{ad}"/>{veri}</dp:columns>')
    return f'<?xml version="1.0"?><dp:tableData xmlns:dp="{DP_NS}">{bloklar}</dp:tableData>'


def transport_bul(xml=None, patlat=None, kullanici="TESTUSER",
                  istenen="DS4K900029", obje="ZSD001_CL_ORNEK"):
    """(donen, durum, stdout) — `_find_existing_transport` gerçek metot olarak koşar."""
    c = object.__new__(SC.SAPClient)
    c.debug_enabled = False

    class _Adt:
        user = kullanici

        def run_query(self, q, row_number=50):
            if patlat is not None:
                raise patlat
            return xml

    c.adt_client = _Adt()
    tampon = io.StringIO()
    try:
        with redirect_stdout(tampon):
            donen = c._find_existing_transport(obje, "class", istenen)
    except Exception as exc:                                    # noqa: BLE001
        return f"COKTU:{type(exc).__name__}", None, tampon.getvalue()
    return donen, getattr(c, "_last_transport_lookup", None), tampon.getvalue()


# F1 AYIRT EDİCİ — kusurun ta kendisi: sorgu patlıyor, kullanıcı HİÇBİR ŞEY görmüyor
donen, durum, cikti = transport_bul(patlat=RuntimeError("HTTP 500 E071 erisilemez"))
kontrol("F1 AYIRT EDİCİ: sorgu HATA verince artık GÖRÜNÜR uyarı basılıyor "
        "(eskiden debug kapalıyken TEK SATIR bile yoktu)",
        donen == "DS4K900029" and "[WARN]" in cikti and "SORGULANAMADI" in cikti,
        f"dönen={donen!r} çıktı={cikti.strip()[:200]!r}")

kontrol("F1b AYIRT EDİCİ: uyarı 'DOĞRULAMA DEĞİL, VARSAYIMDIR' diyor + sebebi taşıyor",
        "VARSAYIM" in cikti and "RuntimeError" in cikti,
        f"çıktı={cikti.strip()[:240]!r}")

kontrol("F1c DURUM KAYDI: sonuç makine-okunur (`error:RuntimeError`)",
        durum == "error:RuntimeError", f"durum={durum!r}")

# F2 FP ÇAPASI — ⚠ EN ÖNEMLİSİ: FALLBACK KALDIRILMADI (yazma yolu kapanmadı)
kontrol("F2 FP ÇAPASI: hata hâlinde HÂLÂ requested_transport dönüyor — push DURMUYOR "
        "(E071'siz sistemlerde fallback yük taşır; 'raise' YANLIŞ fix olurdu)",
        donen == "DS4K900029",
        f"dönen={donen!r} [bu vektör kalkarsa E071 erişimi olmayan sistemlerde her push kırılır]")

# F3 AYIRT EDİCİ — şekil körlüğü (:332 · sessiz VE yanıltıcı → DÜZELTİLDİ)
donen, durum, cikti = transport_bul(xml="<html><body>500 Internal Server Error</body></html>")
kontrol("F3 AYIRT EDİCİ: `dp:columns` YOK (tanınmayan gövde) → görünür uyarı + "
        "'kayıt yok SONUCU DEĞİL' der",
        donen == "DS4K900029" and durum == "shape_unrecognized"
        and "OKUYAMAMA" in cikti,
        f"dönen={donen!r} durum={durum!r} çıktı={cikti.strip()[:200]!r}")

# ── F4-F7 FP ÇAPALARI: YALNIZ DAVRANIŞ ölçülür (İKİ SÜRÜMDE DE geçmeli) ──────
#   ⚠ TASARIM NOTU (ilk yazımda yanlış yapıldı, mutasyon gösterdi): bu dört vektöre
#   `durum == ...` şartı da konmuştu. `_last_transport_lookup` alanı fix'le GELDİĞİ için
#   dördü de mutasyonda düşüyordu — yani "FP çapası" etiketli oldukları hâlde fiilen
#   AYIRT EDİCİ davranıyorlardı. Bir FP çapası, doğru çalışan vakanın davranışının
#   DEĞİŞMEDİĞİNİ kanıtlamalıdır; iki iddiayı (davranış + yeni teşhis alanı) tek vektörde
#   birleştirmek o kanıtı yok eder. Ayrıldılar: davranış burada, durum-kaydı F9'da.
donen, durum, cikti = transport_bul(xml=dp_govde({"TRKORR": []}))
kontrol("F4 FP ÇAPASI (:343 DOKUNULMADI): sütun VAR + satır YOK = yeni obje → istenen "
        "transport döner, uyarı BASILMAZ (davranış iki sürümde AYNI)",
        donen == "DS4K900029" and "[WARN]" not in cikti,
        f"dönen={donen!r} çıktı={cikti.strip()[:160]!r}")

donen2, durum2, cikti2 = transport_bul(xml=dp_govde({
    "TRKORR": ["DS4K900777"], "STRKORR": [""], "AS4USER": ["OTHERUSER"],
    "PGMID": ["R3TR"], "OBJECT": ["CLAS"]}))
kontrol("F5 FP ÇAPASI (:368 DOKUNULMADI): adaylar BAŞKA kullanıcının → istenen transport "
        "korunur, uyarı BASILMAZ (transport gaspı YASAK — bilinçli politika)",
        donen2 == "DS4K900029" and "[WARN]" not in cikti2,
        f"dönen={donen2!r} çıktı={cikti2.strip()[:160]!r}")

donen3, durum3, cikti3 = transport_bul(xml=dp_govde({
    "TRKORR": ["DS4K900555"], "STRKORR": [""], "AS4USER": ["TESTUSER"],
    "PGMID": ["R3TR"], "OBJECT": ["CLAS"]}))
kontrol("F6 FP ÇAPASI: obje kendi BAŞKA transport'una kayıtlı → o transport'a geçilir + "
        "eski [INFO] mesajı AYNEN korunur (başarı yolu bit düzeyinde aynı)",
        donen3 == "DS4K900555" and "already recorded in transport" in cikti3
        and "[WARN]" not in cikti3,
        f"dönen={donen3!r} çıktı={cikti3.strip()[:160]!r}")

donen4, durum4, cikti4 = transport_bul(xml=dp_govde({
    "TRKORR": ["DS4K900029"], "STRKORR": [""], "AS4USER": ["TESTUSER"],
    "PGMID": ["R3TR"], "OBJECT": ["CLAS"]}))
kontrol("F7 FP ÇAPASI: istenen transport zaten sahibi → sessiz kalır "
        "(gereksiz gürültü YOK — alarm-yorgunluğu freni)",
        donen4 == "DS4K900029" and "[WARN]" not in cikti4
        and "already recorded" not in cikti4,
        f"dönen={donen4!r} çıktı={cikti4.strip()[:160]!r}")

# F9 AYIRT EDİCİ — teşhis alanı: BEŞ durum da ayrı ayrı kaydediliyor mu
#   ("doğrulandı" ile "varsayıldı" makine tarafından da ayırt edilebilmeli)
_durumlar = {"no_entry": durum, "foreign_only": durum2,
             "resolved": durum3, "kept": durum4}
_sapan = [f"{b}!={a!r}" for b, a in _durumlar.items() if a != b]
kontrol("F9 AYIRT EDİCİ: sonuç makine-okunur 4 ayrı durumla etiketleniyor "
        "(no_entry/foreign_only/resolved/kept) — +F1c error:*",
        not _sapan, f"sapan={_sapan} (fix öncesi: alan HİÇ YOK → hepsi None)")

# F8 DOKÜMAN-DÜRÜSTLÜĞÜ — docstring artık "silently" DEMİYOR
#   (bu turun ana dersi: kusuru anlatan yorum, kusurun düzeldiği anlamına gelmez.
#    Kaynak MODÜLLE AYNI YERDEN okunur — D2/5 — yoksa mutasyonda sahte-PASS verir.)
_sc_kaynak = (git_show("scripts/sap_client.py") if ARG.mutasyon
              else (KOK / "scripts" / "sap_client.py").read_text(encoding="utf-8"))
kontrol("F8 DOKÜMAN-DÜRÜSTLÜĞÜ: docstring 'Falls back silently' İTİRAFINI artık taşımıyor",
        "Falls back silently" not in _sc_kaynak,
        f"'Falls back silently' geçiyor mu={('Falls back silently' in _sc_kaynak)}")

# =============================================================================
# E — 3. BAĞLAM (görev-DIŞI): korpusun kendi ölçüm aleti sağlam mı?
# =============================================================================
# run_fixture_tests OZEL_TESTLER listesi MÜKERRER kayıt taşırsa aynı fixture iki kez koşar
# ve TOPLAM şişer ("N/N PASS" sayısına güvenmenin bedeli). Bu tam olarak 2026-08-01'de
# yaşandı, yorumla belgelendi — ama mükerrer satır SİLİNMEMİŞTİ (dersin kendi fix'i eksik).
# ⚠ D2/5: STATİK çapa da kaynağı MODÜLLE AYNI YERDEN okur. Çalışma ağacından okunsaydı
# mutasyonda da PASS verir (çapa mutasyonu izlemez = sahte-PASS) ve mükerrer kaydın
# taban SHA'da GERÇEKTEN var olduğu görünmezdi.
_kosucu = (git_show("tests/run_fixture_tests.py") if ARG.mutasyon
           else (KOK / "tests" / "run_fixture_tests.py").read_text(encoding="utf-8"))
try:
    import ast as _ast
    _adlar: list[str] = []
    for _d in _ast.walk(_ast.parse(_kosucu)):
        if isinstance(_d, _ast.Assign) and any(
                getattr(t, "id", "") == "OZEL_TESTLER" for t in _d.targets):
            for _e in getattr(_d.value, "elts", []):
                if getattr(_e, "elts", None):
                    _adlar.append(_e.elts[0].value)
    _mukerrer = sorted({a for a in _adlar if _adlar.count(a) > 1})
    kontrol("E1 3.BAĞLAM: OZEL_TESTLER'de MÜKERRER fixture kaydı YOK (toplam sayı şişmez)",
            not _mukerrer and len(_adlar) > 10,
            f"mükerrer={_mukerrer} toplam_kayıt={len(_adlar)}")
except Exception as _exc:                                       # noqa: BLE001
    kontrol("E1 3.BAĞLAM: OZEL_TESTLER'de MÜKERRER fixture kaydı YOK (toplam sayı şişmez)",
            False, f"AST okunamadı: {type(_exc).__name__}: {_exc}")

os.chdir(_eski_cwd)
shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

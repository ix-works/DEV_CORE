# -*- coding: utf-8 -*-
"""SINIF ALT-INCLUDE'U PUSH'U (ccau/ccimp/ccdef/ccmac) — POST ≠ PUT, ve 201 ≠ "yazıldı".

2026-08-10 kuyruğundaki KUSUR-4/5/6 TEK SINIFTIR: *push zinciri sınıf alt-include'unu bir
KAVRAM OLARAK tanımıyordu.*

  KUSUR-4 · `push_object.py` testclasses'i bilmiyordu — `--type` choices'ta yoktu ve
            `object_types.normalize_object_type('ccau')` ValueError fırlatıyordu.
            Sonuç: operatör ham HTTP atmak zorunda kaldı…
  KUSUR-5 · …ve POST'un GÖVDEYİ YOK SAYDIĞINA çarptı: 201 döner ama include SAP'nin
            56 baytlık boş iskeletiyle yaratılır (ÖLÇÜLDÜ 2026-07-29: 11.639 → 56 bayt).
  KUSUR-6 · …ya da ters uçta: include ZATEN VARSA POST → HTTP 500.

Doğru akış bir ÇAĞRI değil bir SIRADIR ve yalnız `playbook/adt-classes.md §24.8`'de
ANLATILIYORDU, hiçbir yerde İMPLEMENT EDİLMİYORDU:

    include YOK   :  POST (iskelet) → PUT (gövde)     [PUT tek başına → 500]
    include VAR   :  PUT (gövde)                       [POST → 500]
    her iki hâlde :  READBACK — canlıdan geri oku, KIYASLA

⛔ EN PAHALI YÜZÜ SESSİZLİĞİDİR: POST'un 201'ine "başarı" denip durulursa include boş
   kalır, `adt_unit_run` HTTP 200 + `method_count = 0` döner ve bu *"test altyapısı
   kapalı"* gibi okunur — saatlerce yanlış yerde aranır. Bu yüzden readback OPSİYONEL
   DEĞİLDİR; V7/V8 tam bunu bekçilik eder.

🔴 DOĞRULANAMADI (dürüstlük sınırı): bu korpus HTTP katmanını SAHTELEŞTİRİR. Ölçtüğü şey
   *"kodumuz doğru SIRAYI kuruyor ve iskeleti yakalıyor mu"*dur — SAP'nin gerçekten bu
   statüleri döndürdüğü DEĞİL. Statüler `playbook §24.8`'in CANLI ölçümünden alınmıştır
   (2026-07-29). `testclasses` dışındaki segment adları (implementations/definitions/
   macros) bu evde CANLI ÖLÇÜLMEDİ — V10 bunun beyan edildiğini denetler.

Koşum   : python tests/fixtures/class_include_push/run.py            → 14/14
MUTASYON: python tests/fixtures/class_include_push/run.py --mutasyon  → yetenek YOK (0 vektör
          geçer) — taban öz-denetimi bunu doğrular.
          (taban = `990f71b`; ⚠ DAL ADI VERME — D2/5: hareketli ref fix merge edilince
           "fix SONRASI"na kayar ve korpus sessizce boşalır.)
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
from contextlib import redirect_stdout
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


def bayt(x) -> int:
    """Güvenli bayt sayısı. ⚠ ÇÖKME ≠ FAIL (D2/2): mutasyonda push HİÇ koşmaz, sahte
    oturumun `mevcut`u None kalır. Detay dizgeleri KOŞULDAN BAĞIMSIZ olarak (eagerly)
    kurulduğu için `None.encode()` koşucuyu ÇÖKERTİR ve mutasyon 'sonuç yok' verir —
    yani ölçüm aleti tam da ölçmesi gereken anda susar. İlk koşumda bu yaşandı."""
    return len(x.encode("utf-8")) if isinstance(x, str) else 0


def kirp(x, n=60) -> str:
    return repr(x[:n]) if isinstance(x, str) else repr(x)


ap = argparse.ArgumentParser(add_help=True)
ap.add_argument("--mutasyon", action="store_true", help="fix ÖNCESİ sürümü yükle")
ap.add_argument("--ref", default="990f71b",
                help="mutasyon tabanı: yeteneğin HİÇ OLMADIĞI SHA (dal adı VERME)")
ARG = ap.parse_args()

KUM = Path(tempfile.mkdtemp(prefix="ccau_"))
_eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
(KUM / ".conn_adt").write_text(
    "ADT_SAP_URL=https://ornek.invalid\nADT_SAP_USER=TESTUSER\n"
    "ADT_SAP_PASSWORD=x\nADT_SAP_CLIENT=100\nADT_SAP_TIER=DEV\n", encoding="utf-8")
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
    """D2/4 stdout koruması: `sap_client` import-anında sys.stdout'u SARMALAR."""
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


OT = yukle("scripts/object_types.py", "object_types")
L = yukle("scripts/sap_adt_lib.py", "sap_adt_lib")

# SAP'nin POST sonrası yazdığı ÖLÇÜLEN iskelet (playbook §24.8, 2026-07-29 → 56 bayt).
ISKELET = '*"* use this source file for your ABAP unit test classes\n'
GERCEK_KAYNAK = ("CLASS ltc_ornek DEFINITION FOR TESTING RISK LEVEL HARMLESS.\n"
                 "  PRIVATE SECTION.\n    METHODS ilk_test FOR TESTING.\n"
                 "ENDCLASS.\n\nCLASS ltc_ornek IMPLEMENTATION.\n"
                 "  METHOD ilk_test.\n    cl_abap_unit_assert=>assert_true( abap_true ).\n"
                 "  ENDMETHOD.\nENDCLASS.\n")

if ARG.mutasyon:
    print(f"### MUTASYON MODU — object_types/sap_adt_lib @ {ARG.ref} (yetenek ÖNCESİ)\n")


class SahteYanit:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code
        self.cookies = {}
        self.headers = {}


class SahteOturum:
    """ADT'nin ÖLÇÜLEN alt-include davranışını taklit eder (playbook §24.8).

    `mevcut` None ise include CANLIDA YOKTUR. Kurallar:
      GET  yok  → 404          | GET  var → 200 + içerik
      POST yok  → 201 **ama gövdeyi YOK SAYAR** (iskelet yazılır)   ← KUSUR-5
      POST var  → 500 ("could not be created")                       ← KUSUR-6
      PUT  yok  → 500 ("does not have any inactive version")
      PUT  var  → 200 + içerik GERÇEKTEN yazılır
    """

    def __init__(self, mevcut=None, post_govdeyi_yazar=False):
        self.mevcut = mevcut
        self.post_govdeyi_yazar = post_govdeyi_yazar
        self.iz: list[str] = []

    def get(self, url, **kw):
        self.iz.append("GET")
        if self.mevcut is None:
            return SahteYanit("Not Found", 404)
        return SahteYanit(self.mevcut, 200)

    def post(self, url, **kw):
        self.iz.append("POST")
        if self.mevcut is not None:
            return SahteYanit("<msg>include could not be created</msg>", 500)
        govde = (kw.get("data") or b"").decode("utf-8", "replace")
        self.mevcut = govde if self.post_govdeyi_yazar else ISKELET
        return SahteYanit("", 201)

    def put(self, url, **kw):
        self.iz.append("PUT")
        if self.mevcut is None:
            return SahteYanit("<msg>CCAU does not have any inactive version</msg>", 500)
        self.mevcut = (kw.get("data") or b"").decode("utf-8", "replace")
        return SahteYanit("", 200)

    def request(self, method, url, **kw):
        return getattr(self, method.lower())(url, **kw)


def istemci(oturum):
    c = object.__new__(L.SAPADTClient)
    c.url = ""
    c.timeout_short = 5
    c.timeout_default = 5
    c.debug_enabled = False
    c.csrf_token = "TOKEN"
    c._get_headers = lambda *a, **k: {}
    c.session = oturum
    c._request_with_csrf_retry = lambda m, u, **kw: oturum.request(m, u, **kw)
    return c


def push(oturum, kaynak=GERCEK_KAYNAK, kind="ccau", cls="ZCL_ORNEK"):
    """(sonuc, deger, oturum) — sonuc: 'ok' | 'hata' | 'yetenek_yok'."""
    c = istemci(oturum)
    tampon = io.StringIO()
    try:
        with redirect_stdout(tampon):
            return "ok", c.push_class_include(cls, kind, kaynak,
                                              lock_handle="H1", transport="DS4K900029"), oturum
    except AttributeError as exc:                 # metot HİÇ YOK (mutasyon) → FAIL, çökme DEĞİL
        return "yetenek_yok", exc, oturum
    except Exception as exc:                      # noqa: BLE001
        return "hata", exc, oturum


# ── ÖZ-DENETİM: taban gerçekten "yetenek ÖNCESİ" mi? ─────────────────────────
if ARG.mutasyon:
    _s, _d, _ = push(SahteOturum(mevcut=None))
    if _s != "yetenek_yok":
        print(f"[DOĞRULANAMADI] MUTASYON TABANI GEÇERSİZ: '{ARG.ref}' yetenek-ÖNCESİ sürüm "
              f"DEĞİL (push_class_include çağrısı → {_s}).")
        print("  Tipik sebep: --ref bir DAL adı ve fix merge edildi → taban 'fix SONRASI'na kaydı.")
        print("  Çözüm: yeteneğin HİÇ OLMADIĞI SHA'yı ver → --ref 990f71b")
        os.chdir(_eski_cwd)
        shutil.rmtree(KUM, ignore_errors=True)
        sys.exit(2)
    print("### taban öz-denetimi OK — bu ref'te push_class_include GERÇEKTEN YOK\n")

# ── V1/V2 KUSUR-4: tip sistemi alt-include'u TANIYOR mu ─────────────────────
try:
    _v1 = (OT.normalize_class_include("ccau") == "testclasses"
           and OT.normalize_class_include(".ccimp.abap") == "implementations"
           and OT.is_class_include("ccau") is True
           and OT.is_class_include("class") is False)
    _d1 = f"ccau→{OT.normalize_class_include('ccau')}"
except AttributeError as exc:
    _v1, _d1 = False, f"AttributeError: {exc} (fix öncesi: tip tablosu HİÇ YOK)"
kontrol("V1 KUSUR-4: 'ccau'/'.ccimp.abap' kanonik ada çözülüyor + is_class_include ayırıyor",
        _v1, _d1)

try:
    _url = OT.get_class_include_url("ZCL_ORNEK", "ccau")
    _v2 = _url == "/sap/bc/adt/oo/classes/zcl_ornek/includes/testclasses"
    _d2 = f"url={_url!r}"
except AttributeError as exc:
    _v2, _d2 = False, f"AttributeError: {exc}"
kontrol("V2 URL ŞEKLİ: /oo/classes/<cls>/includes/testclasses — '/source/main' EKLENMİYOR",
        _v2, _d2)

# V3 FP ÇAPASI: sıradan tipler BOZULMADI (iki sürümde de geçer)
kontrol("V3 FP ÇAPASI: sıradan tipler etkilenmedi (class/ddls hâlâ normal çözülüyor)",
        OT.normalize_object_type("clas") == "class"
        and OT.normalize_object_type("ddls") == "cds"
        and OT.get_object_url("ZCL_X", "class") == "/sap/bc/adt/oo/classes/zcl_x",
        f"clas→{OT.normalize_object_type('clas')} ddls→{OT.normalize_object_type('ddls')}")

# V4 YÖNLENDİRME: alt-include tek-parametreli URL üreticisine SOKULMUYOR
try:
    OT.get_object_url("ZCL_X", "ccau")
    _v4, _d4 = False, "get_object_url('ccau') hata VERMEDİ (sessizce yanlış URL üretir)"
except ValueError as exc:
    _v4 = "alt-include" in str(exc).lower() or "ALT-INCLUDE" in str(exc)
    _d4 = f"mesaj={str(exc)[:140]!r}"
except Exception as exc:                                        # noqa: BLE001
    _v4, _d4 = False, f"{type(exc).__name__}: {exc}"
kontrol("V4 YÖNLENDİRME: get_object_url('ccau') → doğru yolu SÖYLEYEN ValueError",
        _v4, _d4)

# ── V5 KUSUR-6: include VARSA POST ATILMAZ (doğrudan PUT) ───────────────────
sonuc, deger, ot = push(SahteOturum(mevcut="ESKI ICERIK\n"))
kontrol("V5 KUSUR-6: include VAR → POST HİÇ atılmaz (var olana POST HTTP 500 verirdi)",
        sonuc == "ok" and "POST" not in ot.iz and "PUT" in ot.iz
        and isinstance(deger, dict) and deger.get("created") is False,
        f"sonuç={sonuc} iz={ot.iz} değer={str(deger)[:160]}")

kontrol("V5b içerik GERÇEKTEN yazıldı ve readback ile doğrulandı",
        sonuc == "ok" and ot.mevcut == GERCEK_KAYNAK
        and isinstance(deger, dict) and deger.get("verified") is True,
        f"canlı={kirp(ot.mevcut)} değer={str(deger)[:160]}")

# ── V6 include YOK → POST sonra PUT (SIRA doğru mu) ─────────────────────────
sonuc, deger, ot = push(SahteOturum(mevcut=None))
kontrol("V6 include YOK → sıra GET→POST→PUT→GET; PUT tek başına atılmıyor (500 sınıfı)",
        sonuc == "ok" and ot.iz[:3] == ["GET", "POST", "PUT"]
        and isinstance(deger, dict) and deger.get("created") is True,
        f"sonuç={sonuc} iz={ot.iz} değer={str(deger)[:160]}")

# ── V7 KUSUR-5'İN KALBİ: POST 201 verdi ama gövdeyi yok saydı → PUT KURTARIYOR ─
kontrol("V7 KUSUR-5: POST gövdeyi yok saysa da PUT koştuğu için içerik TAM yazılıyor",
        sonuc == "ok" and ot.mevcut == GERCEK_KAYNAK and bayt(ot.mevcut) > bayt(ISKELET),
        f"canlı_bayt={bayt(ot.mevcut)} iskelet_bayt={bayt(ISKELET)} "
        f"(ölçülen canlı vaka: 11.639 gönderildi → 56 yazıldı)")


# ── V8 SAHTE-YEŞİL BEKÇİSİ: PUT sessizce uygulanmazsa readback YAKALAR ──────
class PutYutanOturum(SahteOturum):
    """POST 201 + iskelet, ama PUT 'başarılı' deyip İÇERİĞİ YAZMIYOR — 56 baytlık
    iskelet canlıda kalıyor. Bu, kusurun EN SESSİZ hâlidir: her HTTP kodu yeşil."""

    def put(self, url, **kw):
        self.iz.append("PUT")
        return SahteYanit("", 200)          # 200 der, hiçbir şey yazmaz


sonuc, deger, ot = push(PutYutanOturum(mevcut=None))
kontrol("V8 SAHTE-YEŞİL BEKÇİSİ: tüm HTTP kodları yeşil ama içerik iskelet → READBACK HATA veriyor",
        sonuc == "hata" and "READBACK UYUŞMADI" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:200]!r}")

kontrol("V8b TEŞHİS: hata mesajı 'POST GÖVDEYİ YOK SAYDI' vakasını ADIYLA söylüyor "
        "(+ method_count=0 sahte-yeşiline atıf)",
        sonuc == "hata" and "GÖVDEYİ YOK SAYDI" in str(deger)
        and "method_count=0" in str(deger),
        f"mesaj={str(deger)[-300:]!r}")

# ── V9 POST reddedilirse GÜRÜLTÜLÜ patlar (sessiz devam YOK) ────────────────
class PostRedOturum(SahteOturum):
    def post(self, url, **kw):
        self.iz.append("POST")
        return SahteYanit("<msg>no authorization</msg>", 403)


sonuc, deger, ot = push(PostRedOturum(mevcut=None))
kontrol("V9 POST 403 → SAPADTError (yaratılamadı; 'devam et' YOK)",
        sonuc == "hata" and "YARATILAMADI" in str(deger),
        f"sonuç={sonuc} değer={str(deger)[:180]!r}")


# ── V10 VARLIK ÇÖZÜLEMEZSE TAHMİN EDİLMİYOR (POST mu PUT mu bilinmiyor) ─────
class BelirsizOturum(SahteOturum):
    def get(self, url, **kw):
        self.iz.append("GET")
        return SahteYanit("<err/>", 500)          # ne 200 ne 404


sonuc, deger, ot = push(BelirsizOturum(mevcut=None))
kontrol("V10 varlık ÇÖZÜLEMEDİ (HTTP 500) → hata; körlemesine POST/PUT ATILMIYOR",
        sonuc == "hata" and "VARLIĞI ÇÖZÜLEMEDİ" in str(deger)
        and ot.iz == ["GET"],
        f"sonuç={sonuc} iz={ot.iz} değer={str(deger)[:180]!r}")

# ── V11 DÜRÜSTLÜK ÇAPASI: hangi segment adı CANLI ÖLÇÜLDÜ, beyan ediliyor mu ─
try:
    _olculen = {k for k, v in OT.CLASS_INCLUDE_TYPES.items() if v.get("olculdu")}
    _v11 = _olculen == {"testclasses"}
    _d11 = f"ölçülü={sorted(_olculen)} (yalnız testclasses canlı doğrulandı)"
except AttributeError as exc:
    _v11, _d11 = False, f"AttributeError: {exc}"
kontrol("V11 DÜRÜSTLÜK: yalnız 'testclasses' ÖLÇÜLDÜ diye işaretli — diğerleri tahmin "
        "olarak BEYAN EDİLİYOR",
        _v11, _d11)

# ── V12 3. BAĞLAM (görev-DIŞI): CLI yüzeyi gerçekten kablolandı mı ──────────
#   ⚠ STATİK çapa (push_object.py import edilirse stdout GASP EDİLİR — D2/4).
#   Kaynak MODÜLLE AYNI YERDEN okunur, yoksa mutasyonda sahte-PASS verir.
_po = (git_show("scripts/push_object.py") if ARG.mutasyon
       else (KOK / "scripts" / "push_object.py").read_text(encoding="utf-8"))
kontrol("V12 3.BAĞLAM (KABLOLAMA): push_object.py --type listesi ccau'yu KABUL EDİYOR "
        "ve alt-include yoluna dallanıyor",
        "'ccau'" in _po and "is_class_include" in _po and "push_class_include" in _po,
        f"ccau_choices={'ccau' in _po} dallanma={'is_class_include' in _po} "
        f"(fix öncesi: argparse 'ccau'yu REDDEDİYORDU)")

_sc = (git_show("scripts/sap_client.py") if ARG.mutasyon
       else (KOK / "scripts" / "sap_client.py").read_text(encoding="utf-8"))
kontrol("V12b KABLOLAMA: SAPClient.push_class_include var ve ANA SINIF üzerinden "
        "kilitleyip aktive ediyor",
        "def push_class_include" in _sc and "Locking parent class" in _sc
        and "Activating parent class" in _sc,
        f"metot={'def push_class_include' in _sc}")

os.chdir(_eski_cwd)
shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

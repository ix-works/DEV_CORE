# -*- coding: utf-8 -*-
"""Lock yanıtındaki MODIFICATION_SUPPORT: sinyal KAYDEDİLİR, akış KESİLMEZ (§12.7 + §12.7b).

TARİHÇE — bu korpus BİR KEZ YÖN DEĞİŞTİRDİ, ikisi de aynı gün (2026-08-09/10):
  V1 (#99) : `NoModification` → SAPLockError. Değerin anlamı DIŞ REFERANSTAN (abap-adt-api
             `AdtLock`) alınmıştı; korpusun kendi başlığı *"CANLI ÖRNEĞİ YOKTUR"* diye
             itiraf ediyordu. Yani ÖLÇÜLMEMİŞ bir değere göre kapı kuruldu.
  V2 (bugün): CANLI ÇAPRAZ ÖLÇÜM yapıldı — 8 obje / 2 paket / 2 tip:
                 CLAS → `NoModification` **5/5** (ve o 5 sınıfın hepsi BAŞARIYLA push edildi)
                 DDLS → alan BOŞ **3/3**
             ⇒ Değer OBJE TİPİNE bağlıdır, "engel" değildir. Sağlıklı sınıf da, transport'a
             kayıtlı olmayan sınıf da AYNI değeri döndürür ⇒ **ayırt edici gücü YOKTUR.**
             Fırlatan sürüm bu sistemde TÜM class-push yolunu kapattı (regresyon).

⛔ BU KORPUSUN ASIL İŞİ İKİ YÖNLÜDÜR — ikisi de aynı anda ölçülür:
  (a) HİÇBİR değer akışı kesmemeli (V1/V7/V10/V12: `NoModification` → hata YOK, kilit
      BIRAKILMAZ, handle döner) — regresyonun geri gelmesini engelleyen çapa.
  (b) Tanıma yine de DOĞRU olmalı: TAM EŞİTLİK korunur. Artık "hata YOK" bir şey kanıtlamaz
      (her şey hata vermiyor) → tanıma **çıktıdaki İZ** ile ölçülür: `NoModification` ve
      casefold varyantları İZ basar; `NoModificationAllowed` / `PartialNoModification` /
      `No Modification` / `Something` / boş / alan-yok **İZ BASMAZ** (V4/V6/V8).
      İz kontrolü kalkarsa V8 sessizce anlamsızlaşır — kontrol alt-dizgeye kayarsa kimse görmez.

§12.7'NİN GERÇEK VAKASI KAYBOLMADI, YER DEĞİŞTİRDİ: teşhis (E071 sorgusu) artık PUT'un
423'ünde basılır (`set_object_source`) — semptomu GERÇEKTEN gördüğümüz yerde, yanlış-pozitif
riski olmadan. V16/V16b/V17 bunu ölçer.

Koşum   : python tests/fixtures/lock_modification_support/run.py
MUTASYON: python tests/fixtures/lock_modification_support/run.py --mutasyon [--ref origin/main]
          (fix ÖNCESİ sap_adt_lib.py git'ten yüklenir; ayırt eden vektörler FAIL vermeli)
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
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

KOK = Path(__file__).resolve().parents[3]
SONUC: list[tuple[str, bool, str]] = []

# Tanımanın İZİ: bu dizge YALNIZ `NoModification` dalında basılır. Değerin kendisine
# bağlamıyoruz (casefold varyantları ham hâliyle yankılanır) — dalın kimliğine bağlıyoruz.
IZ = "§12.7b"


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


# ── modül yükleme ─────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser(add_help=True)
ap.add_argument("--mutasyon", action="store_true",
                help="fix ÖNCESİ sürümü yükle (ayırt-etme kanıtı)")
ap.add_argument("--ref", default="origin/main", help="mutasyon için git ref'i")
ARG = ap.parse_args()

# sap_adt_lib import-ANINDA cwd/env'den .conn_adt çözer → önce boş bir kum havuzuna geç.
KUM = Path(tempfile.mkdtemp(prefix="lockmod_"))
_eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
os.chdir(KUM)
sys.path.insert(0, str(KOK / "scripts"))

if ARG.mutasyon:
    ham = subprocess.run(["git", "-C", str(KOK), "show", f"{ARG.ref}:scripts/sap_adt_lib.py"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ham.returncode != 0:
        print(f"[DOĞRULANAMADI] git show {ARG.ref}: {ham.stderr.strip()[:200]}")
        sys.exit(1)
    taban = KUM / "sap_adt_lib_taban.py"
    taban.write_text(ham.stdout, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("sap_adt_lib_taban", taban)
    L = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    sys.modules["sap_adt_lib_taban"] = L
    spec.loader.exec_module(L)                          # type: ignore[union-attr]
    KAYNAK = ham.stdout
    print(f"### MUTASYON MODU — sap_adt_lib.py @ {ARG.ref} (fix ÖNCESİ)\n")
else:
    import sap_adt_lib as L  # type: ignore  # noqa: E402
    KAYNAK = (KOK / "scripts" / "sap_adt_lib.py").read_text(encoding="utf-8")

# ── sahte yanıt / istemci ─────────────────────────────────────────────────────
OBJ_URL = "/sap/bc/adt/oo/classes/zcl_ornek"
OBJ_ADI = "ZCL_ORNEK"
TR = "AB1K900123"


class SahteYanit:
    def __init__(self, text, status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}
        self.cookies = {}


def govde(mod_alani: str, corrnr: str = TR) -> str:
    """2026-08-09 canlı ölçümünün ŞEKLİ (tanımlayıcılar jenerikleştirildi)."""
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<asx:abap version="1.0" xmlns:asx="http://www.sap.com/abapxml"><asx:values><DATA>'
            '<LOCK_HANDLE>0123456789ABCDEF0123456789ABCDEF01234567</LOCK_HANDLE>'
            f'<CORRNR>{corrnr}</CORRNR><CORRUSER>TESTUSER</CORRUSER>'
            '<CORRTEXT>ABAP: Workbench</CORRTEXT><IS_LOCAL/><IS_LINK_UP/>'
            f'{mod_alani}<SCOPE_MESSAGES/></DATA></asx:values></asx:abap>')


def yeni_istemci():
    c = object.__new__(L.SAPADTClient)
    c.debug_enabled = False
    c.debug_log_path = None
    c.unlock_cagrilari = []

    def _unlock(object_url, lock_handle):
        c.unlock_cagrilari.append((object_url, lock_handle))
        return True

    c.unlock_object = _unlock
    return c


_AM_DESTEKLI = "access_mode" in inspect.signature(
    L.SAPADTClient._verify_and_return_lock).parameters


def cagir(xml: str, transport=TR, access_mode="MODIFY", obj_url=OBJ_URL):
    """(sonuc, deger, stdout, istemci) — sonuc: 'ok' | 'hata' | 'cokme'."""
    c = yeni_istemci()
    yanit = SahteYanit(xml)
    tampon = io.StringIO()
    kw = {"label": "fixture"}
    if _AM_DESTEKLI:
        kw["access_mode"] = access_mode
    try:
        with redirect_stdout(tampon):
            h = c._verify_and_return_lock(yanit, obj_url, transport, **kw)
        return "ok", h, tampon.getvalue(), c
    except L.SAPLockError as exc:
        return "hata", exc, tampon.getvalue(), c
    except Exception as exc:  # noqa: BLE001 — çökme ile hatayı AYIR
        return "cokme", exc, tampon.getvalue(), c


# ── V1 REGRESYON ÇAPASI: NoModification → AKIŞ DEVAM EDER (bloklamaz) ─────────
#   Bu vektör 2026-08-10 regresyonunun ta kendisidir: fırlatan sürüm bu sistemde HİÇBİR
#   class'ın push edilmesine izin vermiyordu. Ölçüm: sağlıklı CLAS 5/5 bu değeri döndürür.
sonuc, deger, cikti, ist = cagir(govde("<MODIFICATION_SUPPORT>NoModification</MODIFICATION_SUPPORT>"))
kontrol("V1 REGRESYON: NoModification + MODIFY → hata YOK, lock handle döner (akış sürer)",
        sonuc == "ok" and deger == "0123456789ABCDEF0123456789ABCDEF01234567",
        f"sonuç={sonuc} dönen={str(deger)[:160]!r}")

kontrol("V1b Kilit BIRAKILMAZ (akış sürüyor — kilidi bırakmak PUT'u 423'e mahkûm eder)",
        ist.unlock_cagrilari == [],
        f"unlock çağrıları={ist.unlock_cagrilari}")

kontrol("V1c TANIMA İZİ: değer yankılanır + §12.7b atfı basılır (sessizce yutulmaz)",
        IZ in cikti and "MODIFICATION_SUPPORT=NoModification" in cikti,
        f"stdout={cikti.strip()[:220]!r}")

# ── V1d BAĞLAM KORUNDU: değer teşhis için saklanıyor (423 anında okunacak) ────
kontrol("V1d BAĞLAM: _last_lock_modification_support/_state saklandı ('value')",
        getattr(ist, "_last_lock_modification_support", None) == "NoModification"
        and getattr(ist, "_last_lock_modification_support_state", None) == "value",
        f"değer={getattr(ist, '_last_lock_modification_support', '<yok>')!r} "
        f"durum={getattr(ist, '_last_lock_modification_support_state', '<yok>')!r}")

# ── V2 CANLI-ÖLÇÜM ÇAPASI: gerçek DDLS şekli (self-closing BOŞ) → sessiz geçer ─
sonuc, deger, cikti, _ = cagir(govde("<MODIFICATION_SUPPORT/>"))
kontrol("V2 CANLI ŞEKİL (self-closing BOŞ = DDLS) → hata YOK, İZ YOK, handle döner",
        sonuc == "ok" and deger == "0123456789ABCDEF0123456789ABCDEF01234567" and IZ not in cikti,
        f"sonuç={sonuc} dönen={deger!r} çıktı={cikti.strip()[:120]!r}")

# ── V3 alan tamamen YOK → sessiz geçer ───────────────────────────────────────
sonuc, deger, cikti, _ = cagir(govde(""))
kontrol("V3 alan yanıtta YOK → hata YOK + İZ YOK (eski sistem/uç davranışı meşru)",
        sonuc == "ok" and IZ not in cikti, f"sonuç={sonuc} değer={str(deger)[:120]!r}")

# ── V4 tanınmayan değer → sessiz geçer ───────────────────────────────────────
sonuc, deger, cikti, _ = cagir(govde("<MODIFICATION_SUPPORT>Something</MODIFICATION_SUPPORT>"))
kontrol("V4 tanınmayan değer ('Something') → hata YOK + İZ YOK (bilinmeyeni yorumlamak YASAK)",
        sonuc == "ok" and IZ not in cikti, f"sonuç={sonuc} çıktı={cikti.strip()[:120]!r}")

# ── V5 bozuk XML → çökme YOK, ama GÖRÜNÜR iz ─────────────────────────────────
sonuc, deger, cikti, _ = cagir("<asx:abap><DATA><LOCK_HANDLE>ABC")   # kapanmamış, parse edilemez
kontrol("V5 bozuk XML → çökme YOK + hata YOK (bugünkü davranış korunur)",
        sonuc == "ok", f"sonuç={sonuc} değer={str(deger)[:160]!r}")
kontrol("V5b bozuk XML → GÖRÜNÜR iz ('doğrulama koşamadı' ≠ 'doğrulandı')",
        "NOT verified" in cikti, f"stdout={cikti.strip()[:200]!r}")

# ── V6 KONTROL GRUBU: 'Modification' → sessiz geçer ──────────────────────────
sonuc, deger, cikti, _ = cagir(govde("<MODIFICATION_SUPPORT>Modification</MODIFICATION_SUPPORT>"))
kontrol("V6 KONTROL GRUBU: 'Modification' (destekli) → hata YOK + İZ YOK",
        sonuc == "ok" and IZ not in cikti, f"sonuç={sonuc} çıktı={cikti.strip()[:120]!r}")

# ── V7 HARF-DURUMU KARARI: casefold eşitlik — 4 varyant da TANINMALI ──────────
#   (Artık "hata verir" diye ölçemeyiz — hiçbir şey hata vermiyor. Tanımanın kanıtı İZ'dir.)
harf_ok = True
harf_detay = []
for varyant in ("nomodification", "NOMODIFICATION", "NoModification ", "noModification"):
    s, d, c_out, _ = cagir(govde(f"<MODIFICATION_SUPPORT>{varyant}</MODIFICATION_SUPPORT>"))
    if s != "ok" or IZ not in c_out:
        harf_ok = False
        harf_detay.append(f"{varyant!r}→sonuç={s} iz={IZ in c_out}")
kontrol("V7 harf-durumu bağımsız (casefold+strip): 4 varyantın hepsi TANINIR (İZ) ama BLOKLAMAZ",
        harf_ok, "; ".join(harf_detay))

# ── V8 FP ÇAPASI: TAM EŞİTLİK — alt-dizge eşleşmesi YASAK ────────────────────
#   ⚠ Bu vektör artık YALNIZ İZ ile anlamlıdır: kontrol alt-dizgeye kaysa bile hiçbir şey
#   hata vermeyeceği için "sonuç=ok" testi sessizce boşalırdı.
fp_ok = True
fp_detay = []
for varyant in ("NoModificationAllowed", "PartialNoModification", "No Modification"):
    s, d, c_out, _ = cagir(govde(f"<MODIFICATION_SUPPORT>{varyant}</MODIFICATION_SUPPORT>"))
    if s != "ok" or IZ in c_out:
        fp_ok = False
        fp_detay.append(f"{varyant!r}→sonuç={s} iz={IZ in c_out}: {str(d)[:60]}")
kontrol("V8 FP ÇAPASI: 'NoModificationAllowed' gibi değerler TANINMAZ (tam eşitlik, alt-dizge DEĞİL)",
        fp_ok, "; ".join(fp_detay))

# ── V9 3. BAĞLAM (görev-dışı): salt-okuma kilidi → dal hiç girilmez ──────────
s, d, c_out, _ = cagir(govde("<MODIFICATION_SUPPORT>NoModification</MODIFICATION_SUPPORT>"),
                       access_mode="READ")
kontrol("V9 3.BAĞLAM: access_mode='READ' → İZ YOK (dal yalnız MODIFY talebinde koşar)",
        s == "ok" and IZ not in c_out and _AM_DESTEKLI,
        f"sonuç={s} iz={IZ in c_out} access_mode_parametresi_var={_AM_DESTEKLI}")

# ── V10 PARSE YOLU: attribute'lu alan (hızlı regex kaçar, ET yakalar) ────────
s, d, c_out, _ = cagir(govde('<MODIFICATION_SUPPORT lang="EN">NoModification</MODIFICATION_SUPPORT>'))
kontrol("V10 attribute'lu alan → ET fallback TANIR (İZ basar), yine bloklamaz",
        s == "ok" and IZ in c_out, f"sonuç={s} iz={IZ in c_out} çıktı={c_out.strip()[:120]!r}")

# ── V11 REGRESYON ÇAPASI: CORRNR uyuşmazlığı davranışı DEĞİŞMEDİ ────────────
#   (Bu dal hâlâ HATA verir — gevşetme YALNIZ MODIFICATION_SUPPORT dalındadır.)
s, d, cikti, ist = cagir(govde("<MODIFICATION_SUPPORT/>", corrnr="AB1K900999"), transport=TR)
kontrol("V11 REGRESYON: CORRNR uyuşmazlığı hâlâ SAPLockError + eski mesaj + kilit bırakılır",
        s == "hata" and "SAP assigned transport AB1K900999" in str(d)
        and "TRANSPORT MISMATCH" in cikti and len(ist.unlock_cagrilari) == 1,
        f"sonuç={s} mesaj={str(d)[:100]!r} unlock={ist.unlock_cagrilari}")

# ── V11b REGRESYON: CORRNR BOŞ hâlâ yalnız [INFO] (üç obje ailesinin çapası) ──
s, d, cikti, _ = cagir('<asx:abap xmlns:asx="http://www.sap.com/abapxml"><asx:values><DATA>'
                       '<LOCK_HANDLE>ABC123</LOCK_HANDLE><CORRNR/><IS_LINK_UP/>'
                       '<MODIFICATION_SUPPORT/></DATA></asx:values></asx:abap>')
kontrol("V11b REGRESYON: CORRNR boş → hata YOK, yalnız [INFO] (DDLS/DTEL/DOMA çapası)",
        s == "ok" and "[INFO]" in cikti and "did not return CORRNR" in cikti,
        f"sonuç={s} çıktı={cikti.strip()[:140]!r}")

# ── V12 KABLOLAMA: gerçek giriş noktası lock_object() üzerinden ──────────────
#   (kod ≠ kablolama: dal `_verify_and_return_lock`'ta doğru olsa da lock_object'ten
#    geçen gerçek çağrı bloklanıyorsa üretimde class-push yine kapalıdır.)
def lock_object_ile(xml: str, access_mode="MODIFY"):
    c = yeni_istemci()
    c.csrf_token = "TOKEN"
    c.url = ""
    c.timeout_short = 5
    c._get_headers = lambda *a, **k: {}
    c._update_cookies = lambda r: None

    class _Oturum:
        def post(self, *a, **k):
            return SahteYanit(xml)

    c.session = _Oturum()
    tampon = io.StringIO()
    try:
        with redirect_stdout(tampon):
            return "ok", c.lock_object(OBJ_URL, access_mode=access_mode, transport=TR)
    except L.SAPLockError as exc:
        return "hata", exc
    except Exception as exc:  # noqa: BLE001
        return "cokme", exc


s1, d1 = lock_object_ile(govde("<MODIFICATION_SUPPORT>NoModification</MODIFICATION_SUPPORT>"))
s2, d2 = lock_object_ile(govde("<MODIFICATION_SUPPORT/>"))
kontrol("V12 KABLOLAMA: lock_object() → NoModification'da da handle döner (class-push AÇIK)",
        s1 == "ok" and str(d1).startswith("0123456789") and s2 == "ok",
        f"NoModification={s1}:{str(d1)[:80]!r} | boş={s2}:{str(d2)[:60]!r}")

# ── V13 AST ÇAPASI: lock_object'teki TÜM çağrılar access_mode taşıyor ────────
agac = ast.parse(KAYNAK)
cagrilar, eksik_am = 0, []
for d in ast.walk(agac):
    if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and d.func.attr == "_verify_and_return_lock"):
        cagrilar += 1
        if not any(k.arg == "access_mode" for k in d.keywords):
            eksik_am.append(getattr(d, "lineno", "?"))
kontrol("V13 AST ÇAPASI: _verify_and_return_lock'un HER çağrısı access_mode iletiyor",
        cagrilar >= 3 and not eksik_am,
        f"çağrı_sayısı={cagrilar} access_mode'suz_satırlar={eksik_am}")

# ── V14 ÜÇ-DEĞERLİ SÖZLEŞME: sınıflandırıcı doğrudan ölçülür ────────────────
try:
    c = yeni_istemci()
    vektorler = [
        ("<MODIFICATION_SUPPORT>NoModification</MODIFICATION_SUPPORT>", ("NoModification", "value")),
        ("<MODIFICATION_SUPPORT/>", (None, "empty")),
        ("<MODIFICATION_SUPPORT></MODIFICATION_SUPPORT>", (None, "empty")),
        ("", (None, "absent")),
    ]
    sapan = []
    for alan, beklenen in vektorler:
        alinan = c._extract_modification_support(SahteYanit(govde(alan)))
        if alinan != beklenen:
            sapan.append(f"{alan!r}: beklenen={beklenen} alınan={alinan}")
    bozuk = c._extract_modification_support(SahteYanit("<asx:abap><DATA"))
    if bozuk != (None, "unparsable"):
        sapan.append(f"bozuk-XML: beklenen=(None,'unparsable') alınan={bozuk}")
    bos_govde = c._extract_modification_support(SahteYanit(""))
    if bos_govde != (None, "unparsable"):
        sapan.append(f"boş-gövde: beklenen=(None,'unparsable') alınan={bos_govde}")
    kontrol("V14 üç-değerli sözleşme: value/empty/absent/unparsable ayrı ayrı ayırt ediliyor",
            not sapan, "; ".join(sapan))
except AttributeError as exc:
    kontrol("V14 üç-değerli sözleşme: value/empty/absent/unparsable ayrı ayrı ayırt ediliyor",
            False, f"AttributeError: {exc}")

# ── V15 KANARYA: korpusun gövde şekli canlı ölçümle aynı iskelette ──────────
#   (Şekil bozulursa V2/V3 sessizce anlamsızlaşır — "PASS ≠ baktı".)
ornek = govde("<MODIFICATION_SUPPORT/>")
kontrol("V15 KANARYA: gövde iskeleti canlı ölçümle aynı (asx/DATA + BÜYÜK HARF alanlar)",
        all(t in ornek for t in ("asx:values", "<DATA>", "<LOCK_HANDLE>", "<CORRNR>",
                                 "<IS_LINK_UP/>", "<MODIFICATION_SUPPORT/>", "<SCOPE_MESSAGES/>")),
        f"gövde={ornek[:160]!r}")


# ── V16 §12.7 TEŞHİSİ KAYBOLMADI: PUT 423'ünde basılır (gevşetmenin telafisi) ─
def put_ile(status: int, govde_metni: str = "<x>err</x>", mod_support="NoModification"):
    """set_object_source'u GERÇEK metot olarak koş; yalnız HTTP katmanı sahte."""
    c = yeni_istemci()
    c.csrf_token = "TOKEN"
    c.url = ""
    c.timeout_default = 5
    c.timeout_short = 5
    c._get_headers = lambda *a, **k: {}
    c._last_lock_modification_support = mod_support
    yanit = SahteYanit(govde_metni, status_code=status)
    c._request_with_csrf_retry = lambda *a, **k: yanit
    tampon = io.StringIO()
    try:
        with redirect_stdout(tampon):
            c.set_object_source(OBJ_URL + "/source/main", "REPORT x.", "LOCKHANDLE123",
                                TR, etag="ETAG1")
        return "ok", None, tampon.getvalue()
    except Exception as exc:  # noqa: BLE001
        return "hata", exc, tampon.getvalue()


s, d, c_out = put_ile(423)
mesaj = str(d)
beklenen = [
    f"obj_name = '{OBJ_ADI}'",   # E071 teşhis sorgusu, gerçek obje adıyla
    "FROM e071",
    "12.7",
    "423 TEŞHİSİ",
]
eksik = [p for p in beklenen if p not in mesaj]
kontrol("V16 TELAFİ: PUT 423 → §12.7 teşhisi (E071 sorgusu + obje adı) hem hatada hem stdout'ta",
        s == "hata" and not eksik and "FROM e071" in c_out,
        f"sonuç={s} eksik={eksik} stdout_e071={'FROM e071' in c_out} mesaj={mesaj[-260:]!r}")

kontrol("V16b TÜNEL-GÖRÜŞ ÇAPASI: 423 teşhisi İKİ kökü de sayar (transport + bayat lock)",
        "KAYITLI DEĞİL" in mesaj and "bayat" in mesaj and "KOVALAMA" in mesaj,
        f"mesaj={mesaj[-300:]!r}")

# ── V17 FP ÇAPASI: 423 OLMAYAN hata 423-teşhisi BASMAZ ──────────────────────
s, d, c_out = put_ile(500)
kontrol("V17 FP ÇAPASI: 500 → 423 teşhisi basılmaz (her hataya transport hikâyesi anlatma)",
        s == "hata" and "423 TEŞHİSİ" not in str(d) and "FROM e071" not in c_out,
        f"sonuç={s} mesaj={str(d)[-160:]!r}")

# ── V18 BAŞARI YOLU: 200 → hata yok, teşhis yok (kontrol grubu) ─────────────
s, d, c_out = put_ile(200)
kontrol("V18 KONTROL GRUBU: PUT 200 → başarı, hiçbir teşhis metni basılmaz",
        s == "ok" and "FROM e071" not in c_out,
        f"sonuç={s} değer={str(d)[:120]!r} çıktı={c_out.strip()[:120]!r}")

# ── V19 3. BAĞLAM (görev-DIŞI giriş noktası): clear_enqueue_lock ─────────────
#   Ayrı bir public API, ayrı amaç (kilit temizleme) ve ⚠ SESSİZ başarısızlık sınıfı:
#   içerideki her istisnayı yutup `False` döner (debug kapalıyken tek satır bile basmaz).
#   Fırlatan sürümde bu araç HER sınıf için sessizce "temizleyemedim" diyordu — üstelik
#   tam da bir kilit sorunu kovalanırken başvurulan araç. Yanlış teşhisi besleyen ikinci yüzey.
def clear_enqueue_ile(xml: str):
    c = yeni_istemci()
    c.csrf_token = "TOKEN"
    c.url = ""
    c.timeout_short = 5
    c._get_headers = lambda *a, **k: {}
    c._update_cookies = lambda r: None

    class _Oturum:
        def post(self, *a, **k):
            return SahteYanit(xml)

    c.session = _Oturum()
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        return c.clear_enqueue_lock(OBJ_URL, transport=TR), c.unlock_cagrilari


sonucu, unlocklar = clear_enqueue_ile(govde("<MODIFICATION_SUPPORT>NoModification</MODIFICATION_SUPPORT>"))
kontrol("V19 3.BAĞLAM: clear_enqueue_lock (CLAS + NoModification) → True + kilit gerçekten bırakıldı",
        sonucu is True and len(unlocklar) == 1,
        f"dönen={sonucu!r} unlock={unlocklar} "
        f"(ölçüldü — fırlatan sürümde: dönen=False; kilit yalnız hata-sonrası bırakma yolundan "
        f"düşüyor, temizlik BAŞARISIZ raporlanıyor ve istisna sessizce yutuluyor)")

os.chdir(_eski_cwd)
shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

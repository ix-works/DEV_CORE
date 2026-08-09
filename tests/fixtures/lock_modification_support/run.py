# -*- coding: utf-8 -*-
"""Lock yanıtındaki MODIFICATION_SUPPORT sinyali: `NoModification` → AÇIK hata (KAYIT §12.7).

KÖK: Bir sınıf push'u `423 InvalidLockHandle` verdi. Ölçülen kök sebep: obje kullanılan
transport'a KAYITLI DEĞİLDİ. SAP bu durumda kilidi VERİR (200 + LOCK_HANDLE) ama sonraki
PUT'u reddeder. Ayırt edici sinyal lock yanıtında ZATEN vardır — `MODIFICATION_SUPPORT` —
ve bugüne kadar HİÇ parse edilmiyordu (grep 0). Sonuç: çağıran 423'ün ham hâliyle karşılaşıp
CSRF/oturum teorilerine sapıyordu (yanlış teşhis iki kez yaşandı; known-errors.md §12.7).

⛔ SINIRI KORUYAN TARAF (bu korpusun ASIL işi): `CORRNR` boşluğu hataya ÇEVRİLMEZ. DDLS için
"CORRNR boş = değiştirilebilir" NORMAL, DTEL/DOMA bu kilit modelini hiç kullanmaz. Aynı şekilde
BOŞ / eksik / tanınmayan MODIFICATION_SUPPORT değeri de hata değildir. Fail-safe sözleşme:
**yalnız `NoModification` hata verir; diğer HER ŞEY bugünkü davranışta kalır.**

ÖLÇÜM SAĞLAMASI (provenance): gövde şekli 2026-08-09'da CANLIDAN alınan gerçek lock yanıtına
göre kurulmuştur (DDLS, HTTP 200): alanlar BÜYÜK HARF, `asx:abap/asx:values/DATA` altında ve
`MODIFICATION_SUPPORT` **self-closing BOŞ** döndü (obje sağlıklıydı) — V2 tam bu şekli korur.
Değerin kendisi (`NoModification`) dış referanstan (abap-adt-api `AdtLock`) gelir; CANLI
ÖRNEĞİ YOKTUR → karşılaştırma harf-durumundan bağımsız ama TAM EŞİTLİK'tir (V7 + V8 çifti).

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


# ── V1 POZİTİF: NoModification → AÇIK, eyleme dönük hata ─────────────────────
sonuc, deger, cikti, ist = cagir(govde("<MODIFICATION_SUPPORT>NoModification</MODIFICATION_SUPPORT>"))
mesaj = str(deger)
beklenen_parcalar = [
    f"obj_name = '{OBJ_ADI}'",                 # teşhis sorgusu, gerçek obje adıyla
    "FROM e071",
    "MODIFICATION_SUPPORT=NoModification",
    "423",
    "12.7",
]
eksik = [p for p in beklenen_parcalar if p not in mesaj]
kontrol("V1 POZİTİF: NoModification → SAPLockError + E071 teşhisi + §12.7 + 423",
        sonuc == "hata" and not eksik and getattr(deger, "status_code", None) == 423,
        f"sonuç={sonuc} eksik_parça={eksik} tip={type(deger).__name__} "
        f"status={getattr(deger, 'status_code', None)} mesaj={mesaj[:120]!r}")

kontrol("V1b Kilit BIRAKILDI (stale enqueue bırakmıyoruz)",
        sonuc == "hata" and len(ist.unlock_cagrilari) == 1,
        f"unlock çağrıları={ist.unlock_cagrilari}")

# ── V2 CANLI-ÖLÇÜM ÇAPASI: gerçek şekil (self-closing BOŞ) → HATA YOK ────────
sonuc, deger, cikti, _ = cagir(govde("<MODIFICATION_SUPPORT/>"))
kontrol("V2 CANLI ŞEKİL (self-closing BOŞ, sağlıklı obje) → hata YOK, handle döner",
        sonuc == "ok" and deger == "0123456789ABCDEF0123456789ABCDEF01234567",
        f"sonuç={sonuc} dönen={deger!r} çıktı={cikti.strip()[:120]!r}")

# ── V3 alan tamamen YOK → HATA YOK ───────────────────────────────────────────
sonuc, deger, cikti, _ = cagir(govde(""))
kontrol("V3 alan yanıtta YOK → hata YOK (eski sistem/uç davranışı meşru)",
        sonuc == "ok", f"sonuç={sonuc} değer={str(deger)[:120]!r}")

# ── V4 tanınmayan değer → HATA YOK ───────────────────────────────────────────
sonuc, deger, cikti, _ = cagir(govde("<MODIFICATION_SUPPORT>Something</MODIFICATION_SUPPORT>"))
kontrol("V4 tanınmayan değer ('Something') → hata YOK (bilinmeyeni hataya çevirmek YASAK)",
        sonuc == "ok", f"sonuç={sonuc} değer={str(deger)[:120]!r}")

# ── V5 bozuk XML → çökme YOK, hata YOK, ama GÖRÜNÜR iz ───────────────────────
sonuc, deger, cikti, _ = cagir("<asx:abap><DATA><LOCK_HANDLE>ABC")   # kapanmamış, parse edilemez
kontrol("V5 bozuk XML → çökme YOK + hata YOK (bugünkü davranış korunur)",
        sonuc == "ok", f"sonuç={sonuc} değer={str(deger)[:160]!r}")
kontrol("V5b bozuk XML → GÖRÜNÜR iz ('doğrulama koşamadı' ≠ 'doğrulandı')",
        "NOT verified" in cikti, f"stdout={cikti.strip()[:200]!r}")

# ── V6 KONTROL GRUBU: değiştirilebilir yanıt → HATA YOK ──────────────────────
sonuc, deger, cikti, _ = cagir(govde("<MODIFICATION_SUPPORT>Modification</MODIFICATION_SUPPORT>"))
kontrol("V6 KONTROL GRUBU: 'Modification' (destekli) → hata YOK",
        sonuc == "ok", f"sonuç={sonuc} değer={str(deger)[:120]!r}")

# ── V7 HARF-DURUMU KARARI: casefold eşitlik (sürüm/sistem farkı sinyali yutmasın) ──
harf_ok = True
harf_detay = []
for varyant in ("nomodification", "NOMODIFICATION", "NoModification ", "noModification"):
    s, d, _, _ = cagir(govde(f"<MODIFICATION_SUPPORT>{varyant}</MODIFICATION_SUPPORT>"))
    if s != "hata":
        harf_ok = False
        harf_detay.append(f"{varyant!r}→{s}")
kontrol("V7 harf-durumu bağımsız (casefold+strip): 4 varyantın hepsi hata verir",
        harf_ok, "; ".join(harf_detay))

# ── V8 FP ÇAPASI: TAM EŞİTLİK — alt-dizge eşleşmesi YASAK ────────────────────
fp_ok = True
fp_detay = []
for varyant in ("NoModificationAllowed", "PartialNoModification", "No Modification"):
    s, d, _, _ = cagir(govde(f"<MODIFICATION_SUPPORT>{varyant}</MODIFICATION_SUPPORT>"))
    if s != "ok":
        fp_ok = False
        fp_detay.append(f"{varyant!r}→{s}: {str(d)[:80]}")
kontrol("V8 FP ÇAPASI: 'NoModificationAllowed' gibi değerler hata VERMEZ (tam eşitlik)",
        fp_ok, "; ".join(fp_detay))

# ── V9 3. BAĞLAM (görev-dışı): salt-okuma kilidi → hata YOK ──────────────────
#   Değiştirmeyi İSTEMEDİĞİMİZ bir kilitte "değiştirilemez" bilgisi hata değildir.
s, d, _, _ = cagir(govde("<MODIFICATION_SUPPORT>NoModification</MODIFICATION_SUPPORT>"),
                   access_mode="READ")
kontrol("V9 3.BAĞLAM: access_mode='READ' + NoModification → hata YOK (yalnız MODIFY talebinde)",
        s == "ok" and _AM_DESTEKLI,
        f"sonuç={s} access_mode_parametresi_var={_AM_DESTEKLI}")

# ── V10 PARSE YOLU: attribute'lu alan (hızlı regex kaçar, ET yakalar) ────────
s, d, _, _ = cagir(govde('<MODIFICATION_SUPPORT lang="EN">NoModification</MODIFICATION_SUPPORT>'))
kontrol("V10 attribute'lu alan → ET fallback yakalar (regex tek başına yeterli değil)",
        s == "hata", f"sonuç={s} değer={str(d)[:120]!r}")

# ── V11 REGRESYON ÇAPASI: CORRNR uyuşmazlığı davranışı DEĞİŞMEDİ ────────────
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
#   (kod ≠ kablolama: kontrol _verify_and_return_lock'ta doğru olsa da lock_object
#    access_mode'u iletmezse ya da dal ulaşılmazsa üretimde HİÇ koşmaz.)
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
kontrol("V12 KABLOLAMA: lock_object() → NoModification hata verir, sağlıklı yanıt geçer",
        s1 == "hata" and s2 == "ok",
        f"bozuk={s1}:{str(d1)[:80]!r} | sağlıklı={s2}:{str(d2)[:60]!r}")

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

os.chdir(_eski_cwd)
shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

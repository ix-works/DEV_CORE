# -*- coding: utf-8 -*-
"""doctor_baglanti_kaniti — sap_doctor canlı probe: "ULAŞAMADIM" ≠ "bağlantı OK".

KÖK: `sap_doctor.run()` probe'u `contextlib.redirect_stdout(io.StringIO())` içinde çağırıp
çıktıyı ATIYOR ve dönen `None`'ı KOŞULSUZ `[OK] SAP bağlantı + auth OK (VPN ✓, kimlik ✓)`
sayıyordu. `sap_client.get_object_metadata` HER istisnayı yutup `None` döndürdüğü için
(KASITLI sözleşme — sınıflandırma çağıranın işidir, `atom._bos_sonuc_sinifi`) alttaki
`except Connection*` dalı ÖLÜ KODdu.

ÖLÇÜM 2026-09-03: DNS'te çözülmeyen host'ta İKİ ayrı projede de (biri probe/paket config'i
OLMAYAN yeni proje, diğeri probe + active_package DOLU olgun proje) `SONUÇ: OK ... devam
edilebilir` basıldı. Yani kusur proje kurulumundan bağımsız, bileşenin KENDİSİNDEdir.

Bu, 2026-08-01 ("doğrulama koşamadı = doğrulandı", 5 kayıt) ve 2026-08-19 (`run_sql_query`,
"altıncı üye") süpürgelerinin ATLADIĞI üyedir: her iki tur da MCP tool katmanını +
`sap_adt_lib`'i taradı, `scripts/` altındaki bu CLI tanı aracını DEĞİL.

Fixture AĞ KULLANMAZ: `sap_client` stub'lanır, sınıflandırmayı GERÇEK `_bos_sonuc_sinifi`
yapar. Böylece "VPN kapalı mı" değil "kod ne iddia ediyor" ölçülür.

Koşum:    python tests/fixtures/doctor_baglanti_kaniti/run.py
MUTASYON: python tests/fixtures/doctor_baglanti_kaniti/run.py --modul <sap_doctor.py yolu>
          Fix ÖNCESİ sürümle koşulduğunda A1-A4 + V9 FAIL, F1-F3 + V8 PASS beklenir
          (ölçüldü 2026-09-03: **4/9**). Kendi kopyanı ölç — CANLI dosyayı BOZUP GERİ YAZMA.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]     # core'un KENDİ varlığı → `__file__` MEŞRU (CORE-03)

# `--modul <yol>`: mutasyon ölçümü için ALTERNATİF bir sap_doctor sürümü.
# Sessiz geçme YOK — verilen yol dosya değilse ÖLÇÜLEMEDİ deyip exit 2.
DOCTOR = KOK / "scripts" / "sap_doctor.py"
if "--modul" in sys.argv:
    _arg = Path(sys.argv[sys.argv.index("--modul") + 1])
    if not _arg.is_file():
        print(f"OLCULEMEDI: modul yok: {_arg}", file=sys.stderr)
        raise SystemExit(2)
    DOCTOR = _arg
for _p in (str(KOK), str(KOK / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SONUC: list[tuple[str, bool, str]] = []
_YUKLU: dict[str, object] = {}
_CANLI: list = []   # GC koruma: doctor'ın ürettiği TextIOWrapper toplanırsa altındaki
                    # gerçek stdout buffer'ını KAPATIR (import yan etkisi).


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def _stub(log_text: str, ret=None, notfound: bool = False) -> None:
    """`sap_client` stub'ı: get_object_metadata log basar ve `ret` döner.

    Gerçek sınıfın SÖZLEŞMESİNİ taklit eder (istisnayı yutar, sebebi stdout'a basar) —
    kusurun yaşadığı yer burasıdır, o yüzden davranışı birebir korunur.
    """
    m = types.ModuleType("sap_client")

    class _C:
        def get_object_metadata(self, name, object_type="ddls"):
            if log_text:
                print(log_text)
            if notfound:
                from sap_adt_lib import SAPObjectNotFoundError  # type: ignore
                raise SAPObjectNotFoundError("yok")
            return ret

    m.SAPClient = _C  # type: ignore[attr-defined]
    sys.modules["sap_client"] = m


def _doctor():
    """Modül BİR KEZ yüklenir (import anında sys.stdout'u sarmalıyor)."""
    if "mod" not in _YUKLU:
        gercek = sys.stdout
        spec = importlib.util.spec_from_file_location("doctor_ut", DOCTOR)
        mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
        spec.loader.exec_module(mod)                          # type: ignore[union-attr]
        _CANLI.append(sys.stdout)                             # sarmalayıcıyı hayatta tut
        sys.stdout = gercek
        _YUKLU["mod"] = mod
    return _YUKLU["mod"]


def kos(log_text: str, ret=None, notfound: bool = False) -> tuple[int, str]:
    mod = _doctor()
    _stub(log_text, ret, notfound)      # import run() içinde → her koşuda taze stub
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.run("ZTEST_PROBE", "ddls", "ZTEST_PKG")      # type: ignore[attr-defined]
    return rc, buf.getvalue()


def _sadelestir(s: str) -> str:
    for a, b in (("İ", "I"), ("ı", "i"), ("Ü", "U"), ("Ğ", "G"),
                 ("Ş", "S"), ("Ç", "C"), ("Ö", "O")):
        s = s.replace(a, b)
    return s.upper()


# ⛔ NEDEN rc ÖLÇÜLMÜYOR (2026-09-03, CI kırmızısı): `run()`'ın çıkış kodu probe'un DEĞİL
# TÜM adımların toplamıdır (conn/tier/master-language/MCP-import). SDK'sız CI'da MCP-import
# adımı FAIL verdiği için rc HER vektörde 1 oldu ve korpus 2/9'a düştü — kusur kodda değil,
# ÖLÇÜMDEYDİ. Artık PROBE SATIRININ ETİKETİ ölçülür: ortam gürültüsünden bağımsız.
# (ad, log, ret, notfound, beklenen_etiket, gorunmeli, GORUNMEMELI)
VEKTORLER = [
    # ── AYIRT EDİCİLER: bağlantı KANITLANAMADIĞI hâller ──────────────────────
    ("A1 DNS çözülmedi -> FAIL (bağlantı iddiası YOK)",
     "[ERROR] HTTPSConnectionPool(...): NameResolutionError getaddrinfo failed", None, False,
     "FAIL", "ULASILAMADI", "AUTH OK"),
    ("A2 bağlantı reddedildi -> FAIL",
     "[ERROR] Connection refused", None, False,
     "FAIL", "ULASILAMADI", "AUTH OK"),
    ("A3 HTTP 500 -> sunucuya ULAŞILDI ama kimlik TEYİT EDİLMEDİ (VPN suçlanmaz)",
     "[ERROR] [500] Internal Server Error", None, False,
     "WARN", "TEYIT EDILMEDI", "VPN"),
    ("A4 HTTP 401 -> kimlik ✓ İDDİA EDİLMEZ",
     "[ERROR] [401] Unauthorized", None, False,
     "WARN", "TEYIT EDILMEDI", "KIMLIK ✓"),
    # ── FP ÇAPALARI: sağlıklı hâllerde HÂLÂ "OK" demeli (aşırı-düzeltme yok) ──
    ("F1 FP ÇAPASI: 404 = sunucuya ulaşıldı + kimlik geçti -> OK",
     "[ERROR] [404] Not found", None, False,
     "OK", "AUTH OK", "ULASILAMADI"),
    ("F2 FP ÇAPASI: canlı metadata okundu -> OK",
     "", "<adtcore:objectReference package='ZTEST_PKG'/>", False,
     "OK", "AUTH OK", "ULASILAMADI"),
    ("F3 FP ÇAPASI: SAPObjectNotFoundError (ulaşıldı, obje yok) -> OK",
     "", None, True,
     "OK", "AUTH OK", "ULASILAMADI"),
]

_PROBE_IZLERI = ("ULAŞILAMADI", "TEYİT EDİLMEDİ", "auth OK")


def probe_satiri(cikti: str) -> tuple[str, str]:
    """(etiket, satır) — probe HÜKMÜNÜ taşıyan satır. Yoksa ("YOK", "")."""
    for satir in cikti.splitlines():
        if any(iz in satir for iz in _PROBE_IZLERI):
            for etiket in ("[FAIL]", "[WARN]", "[OK]"):
                if etiket in satir:
                    return etiket.strip("[]"), satir.strip()
            return "ETIKETSIZ", satir.strip()
    return "YOK", ""


for ad, log, ret, nf, bekle_etiket, gorunmeli, gorunmemeli in VEKTORLER:
    _rc, ham = kos(log, ret, nf)
    etiket, satir = probe_satiri(ham)
    o = _sadelestir(satir)
    g = _sadelestir(gorunmeli) in o
    ng = _sadelestir(gorunmemeli) not in o
    kontrol(ad, etiket == bekle_etiket and g and ng,
            f"etiket={etiket} (beklenen={bekle_etiket}) '{gorunmeli}'={g} "
            f"'{gorunmemeli}' yok={ng} | probe satırı: {satir[:220] or '(BULUNAMADI)'} "
            f"| tam çıktı: {' '.join(ham.split())[:400]}")

# ── V10 — REGRESYON: MCP SDK YOKKEN de siniflandirma calisir (CI'nin yakaladigi kusur) ──
# 2026-09-03: siniflandirici `tools/atom.py`den import ediliyordu; atom.py `_app` uzerinden
# MCP SDK'sini ceker. CI `pip install requests urllib3 python-dotenv` yapar, SDK YOKTUR =>
# ImportError => dis except => arac "SAP probe hatasi" diyordu. Yani "ag mi, yetki mi"
# sorusuna YANLIS cevap. Siniflandirici bagimliliksiz `_bos_sonuc.py`ye TASINDI.
# Bu vektor SDK'yi import-engelleyiciyle bloklar ve hukumun HALA dogru ciktigini olcer.
def _sdk_siz_kos(log_text: str) -> tuple[str, str]:
    import importlib.util as _iu

    class _Engel:
        def find_module(self, name, path=None):
            if name == "mcp" or name.startswith("mcp."):
                return self

        def load_module(self, name):
            raise ImportError("No module named 'mcp' (SDK-siz ortam simulasyonu)")

    _stub(log_text)
    sys.meta_path.insert(0, _Engel())
    for _m in [k for k in sys.modules if k.startswith("mcp_servers")]:
        del sys.modules[_m]          # SDK'li onceki yukleme cache'ini dusur
    try:
        gercek = sys.stdout
        _spec = _iu.spec_from_file_location("doctor_sdksiz", DOCTOR)
        _mod = _iu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _CANLI.append(sys.stdout)
        sys.stdout = gercek
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf):
            _mod.run("ZTEST_PROBE", "ddls", "ZTEST_PKG")
        return probe_satiri(_buf.getvalue())
    finally:
        sys.meta_path.remove(_Engel) if False else sys.meta_path.pop(0)


_e10, _s10 = _sdk_siz_kos("[ERROR] HTTPSConnectionPool: NameResolutionError getaddrinfo failed")
kontrol("V10 REGRESYON: MCP SDK YOKKEN de 'ULAŞILAMADI' hükmü verilir ('probe hatası' DEĞİL)",
        _e10 == "FAIL" and "ULAŞILAMADI" in _s10,
        f"etiket={_e10} satır={_s10[:200] or '(BULUNAMADI)'}")

# ── V8 — 3. BAĞLAM (görev-dışı): kardeş çağrı yerleri bu kusuru TAŞIMIYOR mu? ──
# `get_object_metadata`'yı redirect_stdout içinde çağıran diğer üretim dosyaları,
# boş sonucu POZİTİF bir iddiaya çevirmemeli. `check_sap_master_language.py` bunu
# SKIPPED olarak işaretler (sahte-yeşil DEĞİL) — o davranış burada ÇİVİLENİR.
_ml = (KOK / "scripts" / "validators" / "check_sap_master_language.py").read_text(
    encoding="utf-8", errors="replace")
kontrol("V8 3.BAĞLAM: check_sap_master_language boş metadata'yı 'OK' değil SKIPPED sayar",
        "'metadata-okunamadi'" in _ml and "gate_status(_GATE, 'SKIPPED'" in _ml,
        "kardeş çağrı yeri sahte-yeşil üretmemeli")

# ── V9 — sözleşme: fix kanonik sınıflandırıcıyı KULLANIYOR (kendi kopyası değil) ──
_src = DOCTOR.read_text(encoding="utf-8", errors="replace")
kontrol("V9 sözleşme: sap_doctor kanonik `_bos_sonuc_sinifi`'nı import eder (kopya mantık yok)",
        "_bos_sonuc_sinifi" in _src and "from mcp_servers.sap_adt._bos_sonuc import" in _src,
        "sınıflandırma TEK yerde + BAĞIMLILIKSIZ modülde yaşamalı (SDK'sız CI'da da koşar)")

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

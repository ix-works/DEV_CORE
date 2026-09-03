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


# (ad, log, ret, notfound, FAIL_bekle, gorunmeli, GORUNMEMELI)
VEKTORLER = [
    # ── AYIRT EDİCİLER: bağlantı KANITLANAMADIĞI hâller ──────────────────────
    ("A1 DNS çözülmedi -> FAIL (bağlantı iddiası YOK)",
     "[ERROR] HTTPSConnectionPool(...): NameResolutionError getaddrinfo failed", None, False,
     True, "ULASILAMADI", "AUTH OK"),
    ("A2 bağlantı reddedildi -> FAIL",
     "[ERROR] Connection refused", None, False,
     True, "ULASILAMADI", "AUTH OK"),
    ("A3 HTTP 500 -> sunucuya ULAŞILDI ama kimlik TEYİT EDİLMEDİ (VPN suçlanmaz)",
     "[ERROR] [500] Internal Server Error", None, False,
     False, "TEYIT EDILMEDI", "VPN"),
    ("A4 HTTP 401 -> kimlik ✓ İDDİA EDİLMEZ",
     "[ERROR] [401] Unauthorized", None, False,
     False, "TEYIT EDILMEDI", "KIMLIK ✓"),
    # ── FP ÇAPALARI: sağlıklı hâllerde HÂLÂ "OK" demeli (aşırı-düzeltme yok) ──
    ("F1 FP ÇAPASI: 404 = sunucuya ulaşıldı + kimlik geçti -> OK",
     "[ERROR] [404] Not found", None, False,
     False, "AUTH OK", "ULASILAMADI"),
    ("F2 FP ÇAPASI: canlı metadata okundu -> OK",
     "", "<adtcore:objectReference package='ZTEST_PKG'/>", False,
     False, "AUTH OK", "ULASILAMADI"),
    ("F3 FP ÇAPASI: SAPObjectNotFoundError (ulaşıldı, obje yok) -> OK",
     "", None, True,
     False, "AUTH OK", "ULASILAMADI"),
]

for ad, log, ret, nf, bekle_fail, gorunmeli, gorunmemeli in VEKTORLER:
    rc, ham = kos(log, ret, nf)
    o = _sadelestir(ham)
    g = _sadelestir(gorunmeli) in o
    ng = _sadelestir(gorunmemeli) not in o
    kontrol(ad, (rc == 1) == bekle_fail and g and ng,
            f"rc={rc} (FAIL bekleniyordu={bekle_fail}) '{gorunmeli}'={g} "
            f"'{gorunmemeli}' yok={ng} | çıktı: {' '.join(ham.split())[:200]}")

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
        "_bos_sonuc_sinifi" in _src and "from mcp_servers.sap_adt.tools.atom import" in _src,
        "sınıflandırma TEK yerde yaşamalı (2026-08-01 kararı)")

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

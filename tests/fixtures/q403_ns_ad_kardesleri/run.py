#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""q403_ns_ad_kardesleri — sabit Z/Y önek kontrolü yapan araçlar ortak karara bağlandı (Q403, DEV_CORE #416).

NEDEN VAR (2026-11-11)
  Q393 (#397) "müşteri adı" kararını `scripts/utils/ad_politikasi.py`'ye taşıdı; beş araç
  ilk harfe bakmaya devam ediyordu (changelog Q393 "Sınır" paragrafı). Projede bildirilmiş
  `/<NS>/` programının textpool'u `push_textpool` ile yüklenemiyordu (`[BLOCK] yalnız Z/Y`),
  PULL-BEFORE-EDIT eklentisi namespace'li textpool dosyasını hiç tanımıyordu (kapı AÇIK),
  envanter namespace'li nesneyi SESSİZCE atlıyordu.

VEKTÖRLER (taban `d85de77` = düzeltme öncesi; K bölümü ayırt ediciliği ölçer)
  P*  push_textpool (GERÇEK `main`, SAPClient adımında durdurulur — ağ YOK):
      P1 ⭐ kayıtlı NS kabul · kayıtsız `/SCWM/` rc 2 + metin "yalnız müşteri ad alanı" + "bildirilmemi"
      · Z kabul · standart rc 2   T1 ⭐ Git Bash'in çevirdiği ad (`C:/Program Files/Git/…`) → MSYS ipucu
  Q*  pull_msag_textpool (GERÇEK `main`): Q1 ⭐ NS kapıyı geçer (sonraki adım "dosya yok") · kayıtsız red
  C*  scaffold_classic_program (sahte Path — diske YAZMAZ): C1 ⭐ NS dosyaları `#nspc#…` çıktı dizininde,
      hiçbiri dizin dışına kaçmaz · ABAP içeriği `REPORT /nspc/…` · C2 KONTROL Z adında dosya adı +
      içerik tabanla BAYT BAYT aynı · C3 kayıtsız NS rc 2
  B*  build_cbo_inventory (sahte SAPClient): B1 ⭐ NS nesnesi + boşluklu servis adı (IWSV `… 0001`)
      envanterde, kayıtsız/standart yok · B2 KONTROL yapılandırmasız envanter tabanla AYNI
  H*  _pbe_msag_textpool.sinifla: H1 ⭐ `#nspc#prog.symbols.txt` → `/NSPC/PROG` + MSYS notu · H2 msag
      `messages-#nspc#x.csv` · H3 çıplak ad + tek `#nspc#…prog.abap` · H4 kayıtsız NS → tanınmaz /
      yer tutucu · H5 KONTROL Z/Y dosya adlarında karar tabanla AYNI (yapılandırmalı + yapılandırmasız)
  A*  ad_politikasi.dosya_adi: A1 gidiş-dönüş + Z adında `.lower()` · A2 yol ayıracı kalırsa ValueError
  S   ⭐ KONTROL/SIKILAŞTIRMA: yapılandırmasız üç CLI kapısında (push/pull/scaffold) taban ↔ yeni farkı
      YALNIZ "Z/Y önekli ama gramer dışı" adlarda ve YALNIZ kabul→red yönünde
  K*  taban: K1 ⭐ taban push/pull/scaffold NS'yi reddediyordu · K2 taban kanca NS textpool'u tanımıyordu
      · K3 taban envanter NS nesnesini atlıyordu

KULLANIM
  python tests/fixtures/q403_ns_ad_kardesleri/run.py
  python tests/fixtures/q403_ns_ad_kardesleri/run.py --mutasyon-<kip>
  Mutasyon exit: 1 = ilan edilen küme TAM düştü · 2 = sapma · 3 = çapa ≠ 1 / derlenmedi / sayı yok.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path, PurePosixPath

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
TABAN_SHA = "d85de77"
_GIT_KOK = Path(os.environ.get("Q403_GIT_KOK") or REPO)
_KUM = Path(tempfile.mkdtemp(prefix="q403_"))
for _p in (REPO / "scripts" / "hooks", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))
os.environ.pop("IX_CUSTOMER_NAMESPACES", None)
os.environ.pop("IX_SOURCE_ROOT", None)

S: list = []
_TUT: list = []
_SAYAC = [0]
NL = chr(10)
YAML_NS = "sap_profile: s4_private\ncustomer_namespaces: [\"/NSPC/\"]\n"
YAML_YOK = "sap_profile: s4_private\n"
MSYS_AD = "C:/Program Files/Git/NSPC/SD001_P01"     # Git Bash'in `/NSPC/SD001_P01`'e yaptığı (ölçüldü)


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


def _yakala(fn, *a, **k):
    """(dönüş, istisna, stdout+stderr metni) — istisna ÖLÇÜLÜR (çökme ≠ FAIL)."""
    eski = (sys.stdout, sys.stderr)
    # TextIOWrapper(BytesIO): içe aktarımda `sys.stdout.buffer`'ı saran modüller (scaffold, envanter)
    # StringIO'da çöker. Sarmalayıcılar `_TUT`ta tutulur (GC kapatırsa alttaki BytesIO da kapanır).
    tampon = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    _TUT.append(tampon)
    sys.stdout = sys.stderr = tampon

    def metin():
        for akis in (sys.stdout, sys.stderr, tampon):
            try:
                akis.flush()
            except Exception:
                pass
        _TUT.extend((sys.stdout, sys.stderr))
        return tampon.buffer.getvalue().decode("utf-8", "replace")
    try:
        try:
            return fn(*a, **k), None, metin()
        except BaseException as exc:                  # noqa: BLE001
            return None, exc, metin()
    finally:
        sys.stdout, sys.stderr = eski


def _baglanti(d):
    lib = sys.modules.get("sap_adt_lib")
    if lib is not None:
        lib._explicit_working_dir = None
        lib.conn_path = Path(d) / ".conn_adt"


def proje(yaml_metni: str | None) -> Path:
    """Yeni proje kökü + sahte `.conn_adt` (namespace kökü = bağlantı dizini; ad_politikasi F2)."""
    _SAYAC[0] += 1
    d = _KUM / f"p{_SAYAC[0]}"
    d.mkdir(parents=True)
    if yaml_metni is not None:
        (d / "project.yaml").write_bytes(yaml_metni.encode("utf-8"))
    (d / ".conn_adt").write_bytes(b"ADT_SAP_URL=https://sahte.invalid\nADT_SAP_CLIENT=000\n")
    os.environ["CLAUDE_PROJECT_DIR"] = str(d)
    _baglanti(d)
    return d


def _imp(ad):
    import importlib
    m, exc, _ = _yakala(importlib.import_module, ad)
    if m is None:
        raise SystemExit(f"[fixture-hatasi] {ad} import edilemedi: {exc!r}")
    return m


def _taban_modul(yol, ad):
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:{yol}"], capture_output=True)
    if g.returncode != 0:
        raise RuntimeError(f"taban okunamadi {yol}: {g.stderr.decode('utf-8', 'replace')[:120]}")
    mod = types.ModuleType(ad)
    mod.__file__ = str(REPO / yol)
    _, exc, _ = _yakala(lambda: exec(compile(g.stdout.decode("utf-8"), mod.__file__, "exec"), mod.__dict__))
    if exc is not None:
        raise RuntimeError(f"taban derlenemedi {yol}: {exc!r}")
    return mod


# ── push_textpool ───────────────────────────────────────────────────────────
class _Gecti(Exception):
    pass


def push(PT, ad):
    """GERÇEK main; kapıyı geçerse SAPClient adımında `_Gecti` (ağ YOK). → ('GECTI'|rc, metin)."""
    def dur(*a, **k):
        raise _Gecti()
    yuk = _KUM / "symbols.txt"
    yuk.write_bytes(b"@MaxLength:3\nB00=abc")
    eski_c, eski_argv = PT.SAPClient, sys.argv
    PT.SAPClient = dur
    sys.argv = ["push_textpool.py", "--program", ad, "--transport", "<TRANSPORT>", "--symbols-file", str(yuk)]
    try:
        r, exc, metin = _yakala(PT.main)
    finally:
        PT.SAPClient, sys.argv = eski_c, eski_argv
    return ("GECTI" if isinstance(exc, _Gecti) else (r if exc is None else repr(exc))), metin


def pull(PM, ad, tur="textpool"):
    """GERÇEK main; kapıyı geçen ad bir sonraki adımda "dosya yok" der (istemci hiç kurulmaz)."""
    yok = _KUM / "olmayan" / "x.symbols.txt"
    bayrak = "--program" if tur == "textpool" else "--name"
    r, exc, metin = _yakala(PM.main, [tur, bayrak, ad, "--file", str(yok)], client=object())
    if exc is not None:
        return repr(exc), metin
    return ("GECTI" if "dosya yok" in metin else r), metin


class _SahtePath:
    """scaffold için diske YAZMAYAN Path: `/` birleşimi POSIX kuralıyla (mutlak parça öncekini
    siler — Windows'ta `out / "/ns/x"` sürücü köküne kaçar; aynı kaçış burada görünür)."""
    yazilan: dict = {}

    def __init__(self, *p):
        self.p = PurePosixPath(*[str(x).replace(chr(92), "/") for x in p]) if p else PurePosixPath(".")

    def __truediv__(self, o):
        return _SahtePath(str(self.p / str(o)))

    def mkdir(self, *a, **k):
        pass

    def write_text(self, t, encoding=None):
        _SahtePath.yazilan[str(self.p)] = t

    def __str__(self):
        return str(self.p)


def scaffold(SC, ad):
    """→ (rc|'COKTU', {yol: içerik})."""
    _SahtePath.yazilan = {}
    eski_p, eski_argv = SC.Path, sys.argv
    SC.Path = _SahtePath
    sys.argv = ["scaffold_classic_program.py", ad, "--out", "/cikti", "--desc", "aciklama"]
    try:
        r, exc, _ = _yakala(SC.main)
    finally:
        SC.Path, sys.argv = eski_p, eski_argv
    return (r if exc is None else f"COKTU {exc!r}"), dict(_SahtePath.yazilan)


# ── build_cbo_inventory ─────────────────────────────────────────────────────
NESNELER = [
    {"name": "ZSD001_T01", "type": "TABL/DT"},
    {"name": "/NSPC/SD001_T01", "type": "TABL/DT"},
    {"name": "/SCWM/X_TABLE", "type": "TABL/DT"},
    {"name": "ZSD001_SRV_ORNEK                0001", "type": "IWSV"},   # ADT'nin boşluklu servis adı (biçim ölçüldü)
    {"name": "/NSPC/SRV_ORNEK        0001", "type": "IWSV"},
    {"name": "ZSD001_SICF_ORNEK     4SYHDG1LJB52DAKB11MPN5S07", "type": "SICF/TYP"},
    {"name": "MARA", "type": "TABL/DT"},
    {"name": "EZSD001_L", "type": "ENQU/DL"},
    {"name": "ZSD001_PKG", "type": "DEVC/K"},
]


def envanter(BC):
    class _Istemci:
        def list_package_contents(self, pkg):
            return list(NESNELER)
    sahte = types.ModuleType("sap_client")
    sahte.SAPClient = _Istemci
    eski_mod = sys.modules.get("sap_client")
    sys.modules["sap_client"] = sahte
    hedef = _KUM / f"inv{_SAYAC[0]}"
    eski = (BC.REPO, BC.OUT, sys.argv)
    BC.REPO, BC.OUT = hedef, hedef / "governance" / "cbo-inventory.json"
    sys.argv = ["build_cbo_inventory.py", "ZSD001_PKG"]
    try:
        r, exc, _ = _yakala(BC.main)
    finally:
        BC.REPO, BC.OUT, sys.argv = eski
        if eski_mod is not None:
            sys.modules["sap_client"] = eski_mod
        else:
            sys.modules.pop("sap_client", None)
    if exc is not None or r != 0:
        return f"COKTU rc={r} {exc!r}"
    return set(json.loads((hedef / "governance" / "cbo-inventory.json").read_text(encoding="utf-8"))["objects"])


# ── kanca ───────────────────────────────────────────────────────────────────
def kanca_agaci(d: Path, prog_dosyasi: str | None = None) -> Path:
    tp = d / "SOURCE_CODES" / "SD" / "ZSD001_PKG" / "programs" / "textpool"
    tp.mkdir(parents=True, exist_ok=True)
    if prog_dosyasi:
        (tp.parent / prog_dosyasi).write_bytes(b"REPORT x.\n")
    return tp


def sinif(PB, yol):
    r, exc, _ = _yakala(PB.sinifla, yol)
    return f"COKTU {exc!r}" if exc is not None else r


def ozet(r):
    return None if not isinstance(r, dict) else (r.get("nesne"), r.get("tip"))


# ─────────────────────────────────────────────────────────────────────────────
def bolum_p(PT):
    proje(YAML_NS)
    ns, _ = push(PT, "/NSPC/SD001_P01")
    nsk, _ = push(PT, "/nspc/sd001_p01")
    sc, m_sc = push(PT, "/SCWM/X_PROG")
    z, _ = push(PT, "ZSD001_P01")
    st, _ = push(PT, "RSABAP_X")
    ekle("P1 ⭐ push_textpool: kayitli NS (buyuk/kucuk harf) kapidan gecer · kayitsiz /SCWM/ rc 2 + ortak "
         "metin + kayitsizlik gerekcesi · Z gecer · standart rc 2",
         ns == nsk == "GECTI" and sc == 2 and "yalnız müşteri ad alanı" in m_sc and "bildirilmemi" in m_sc
         and z == "GECTI" and st == 2, [ns, nsk, sc, z, st, m_sc[-160:]])
    rc, m = push(PT, MSYS_AD)
    ekle("T1 ⭐ Git Bash'in cevirdigi ad (C:/Program Files/Git/...) rc 2 + MSYS_NO_PATHCONV ipucu",
         rc == 2 and "MSYS_NO_PATHCONV=1" in m, [rc, m[-200:]])


def bolum_q(PM):
    proje(YAML_NS)
    a, _ = pull(PM, "/NSPC/SD001_P01")
    b, _ = pull(PM, "/NSPC/SD001", tur="msag")
    c, mc = pull(PM, "/SCWM/X_PROG")
    z, _ = pull(PM, "ZSD001_P01")
    ekle("Q1 ⭐ pull_msag_textpool: kayitli NS textpool + msag kapidan gecer · kayitsiz rc 1 + ortak metin · Z gecer",
         a == b == z == "GECTI" and c == 1 and "yalnız müşteri ad alanı" in mc and "bildirilmemi" in mc,
         [a, b, c, z, mc[-160:]])


def bolum_c(SC, TSC):
    proje(YAML_NS)
    rc, dosyalar = scaffold(SC, "/NSPC/SD001_P01")
    beklenen = {f"/cikti/#nspc#sd001_p01{s}.abap" for s in ("", "_top", "_cls", "_f01")}
    ana = dosyalar.get("/cikti/#nspc#sd001_p01.abap", "")
    ekle("C1 ⭐ scaffold NS: 4 dosya `#nspc#...` CIKTI DIZININDE (disari kacan yok) · ABAP `REPORT /nspc/sd001_p01.`",
         rc == 0 and set(dosyalar) == beklenen and "REPORT /nspc/sd001_p01." in ana
         and "INCLUDE /nspc/sd001_p01_top." in ana, [rc, sorted(dosyalar)])
    rz, dz = scaffold(SC, "ZSD001_P01")
    trz, tdz = scaffold(TSC, "ZSD001_P01")
    ekle("C2 ⭐ KONTROL: Z adinda dosya adlari + icerik tabanla BAYT BAYT ayni",
         rz == trz == 0 and dz == tdz and len(dz) == 4, [rz, trz, sorted(dz)])
    rk, dk = scaffold(SC, "/SCWM/X_PROG")
    ekle("C3 scaffold kayitsiz NS rc 2, dosya yok", rk == 2 and not dk, [rk, sorted(dk)])


def bolum_b(BC, TBC):
    proje(YAML_NS)
    yeni = envanter(BC)
    ekle("B1 ⭐ envanter: Z + kayitli NS + bosluklu servis adlari (Z ve NS) VAR · kayitsiz/standart/E-kilit/DEVC YOK",
         yeni == {"ZSD001_T01", "/NSPC/SD001_T01", "ZSD001_SRV_ORNEK                0001",
                  "/NSPC/SRV_ORNEK        0001", "ZSD001_SICF_ORNEK     4SYHDG1LJB52DAKB11MPN5S07"},
         sorted(yeni) if isinstance(yeni, set) else yeni)
    proje(YAML_YOK)
    y2, t2 = envanter(BC), envanter(TBC)
    ekle("B2 ⭐ KONTROL: yapilandirmasiz envanter tabanla AYNI (bosluklu Z servis adlari dahil)",
         isinstance(y2, set) and y2 == t2 and "ZSD001_SRV_ORNEK                0001" in y2,
         [sorted(y2) if isinstance(y2, set) else y2, sorted(t2) if isinstance(t2, set) else t2])


def bolum_h(PB, TPB):
    d = proje(YAML_NS)
    tp = kanca_agaci(d)
    r1 = sinif(PB, tp / "#nspc#sd001_p01.symbols.txt")
    ekle("H1 ⭐ kanca: `#nspc#sd001_p01.symbols.txt` -> /NSPC/SD001_P01 textpool + komutta ad + MSYS notu",
         ozet(r1) == ("/NSPC/SD001_P01", "textpool") and "--program /NSPC/SD001_P01 " in r1["komut"]
         and "MSYS_NO_PATHCONV=1" in r1["not"], r1)
    msag = d / "SOURCE_CODES" / "SD" / "ZSD001_PKG" / "messages-#nspc#sd001.csv"
    r2 = sinif(PB, msag)
    ekle("H2 kanca msag `messages-#nspc#sd001.csv` -> /NSPC/SD001 + MSYS notu",
         ozet(r2) == ("/NSPC/SD001", "msag") and "MSYS_NO_PATHCONV=1" in r2["not"], r2)
    d3 = proje(YAML_NS)
    tp3 = kanca_agaci(d3, "#nspc#sd001_p01.prog.abap")
    r3 = sinif(PB, tp3 / "symbols.txt")
    ekle("H3 kanca ciplak `symbols.txt` + tek `#nspc#sd001_p01.prog.abap` -> /NSPC/SD001_P01",
         ozet(r3) == ("/NSPC/SD001_P01", "textpool"), r3)
    d4 = proje(YAML_YOK)
    tp4 = kanca_agaci(d4, "#nspc#sd001_p01.prog.abap")
    r4a = sinif(PB, tp4 / "#nspc#sd001_p01.symbols.txt")
    r4b = sinif(PB, d4 / "SOURCE_CODES" / "SD" / "ZSD001_PKG" / "messages-#nspc#sd001.csv")
    r4c = sinif(PB, tp4 / "symbols.txt")
    ekle("H4 ⭐ kayitsiz NS: adli textpool TANINMAZ (None) · msag ve ciplak ad yer tutucu (pull'un reddedecegi ad istenmez)",
         r4a is None and ozet(r4b) == ("<MSAG_ADI>", "msag") and ozet(r4c) == ("<PROGRAM_ADI>", "textpool"),
         [r4a, ozet(r4b), ozet(r4c)])
    fark = []
    for yaml in (YAML_NS, YAML_YOK):
        dk = proje(yaml)
        tpk = kanca_agaci(dk, "zsd001_p01.prog.abap")
        kok = dk / "SOURCE_CODES" / "SD" / "ZSD001_PKG"
        yollar = [tpk / "zsd001_p01.symbols.txt", tpk / "ZSD001_P01.selections.txt", tpk / "mara.symbols.txt",
                  tpk / "z-x.symbols.txt", tpk / "symbols.txt", kok / "messages-zsd000.csv",
                  kok / "messages-all.csv", kok / "messages.csv", kok / "messages-mara.csv",
                  dk / "ref_docs" / "messages-zsd000.csv"]
        for y in yollar:
            if sinif(PB, y) != sinif(TPB, y):
                fark.append((yaml[:30], y.name, sinif(PB, y), sinif(TPB, y)))
    ekle("H5 ⭐ KONTROL: Z/Y/standart dosya adlarinda kanca karari tabanla AYNI (yapilandirmali + yapilandirmasiz, 20 karar)",
         not fark, fark[:3])


def bolum_a(A):
    gidis = ["/NSPC/SD001_P01", "/nspc/x", "ZSD001_X", "Y1"]
    ekle("A1 dosya_adi: /NSPC/X -> #nspc#x · Z adinda .lower() ile AYNI · dosya_adindan_ad(dosya_adi(x)) == x.upper()",
         A.dosya_adi("/NSPC/X") == "#nspc#x" and A.dosya_adi("ZSD001_X") == "zsd001_x"
         and all(A.dosya_adindan_ad(A.dosya_adi(x)) == x.upper() for x in gidis),
         [(x, A.dosya_adi(x)) for x in gidis])
    hatali = []
    for x in ("/AB/X", "/NSPC/A/B", "ZX" + chr(92) + "Y", "/"):
        _, exc, _ = _yakala(A.dosya_adi, x)
        if not isinstance(exc, ValueError):
            hatali.append((x, repr(exc)))
    ekle("A2 dosya_adi: yol ayiraci kalan ad ValueError ('/AB/X' gramer disi NS · ic '/' · ters bolu)",
         not hatali, hatali)


SIK_KORPUS = ["ZFOO", "zfoo", "Y_X", "Z", "ZSD001_P01", "ZA-B", "Z$X", "ZFOO ", "Z/X", "ZFOO" + NL,
              "Z.X", "MARA", "/NSPC/X", "/SCWM/X", "EZSD001_L", "LZFG1TOP", "ZCL_X", "Y"]


def bolum_s(PT, TPT, PM, TPM, SC, TSC):
    proje(YAML_YOK)
    gramer = re.compile(r"[ZY][A-Z0-9_]*", re.I)
    beklenen = sorted(a for a in SIK_KORPUS if a[:1].upper() in ("Z", "Y") and not gramer.fullmatch(a))
    sapma, sik = [], {"push": [], "pull": [], "scaffold": []}
    for a in SIK_KORPUS:
        for ad, y, t in (("push", push(PT, a)[0] == "GECTI", push(TPT, a)[0] == "GECTI"),
                         ("pull", pull(PM, a)[0] == "GECTI", pull(TPM, a)[0] == "GECTI"),
                         ("scaffold", scaffold(SC, a)[0] == 0, scaffold(TSC, a)[0] == 0)):
            if y == t:
                continue
            if t and not y:
                sik[ad].append(a)
            else:
                sapma.append((ad, a, y, t))
    ekle(f"S ⭐ KONTROL/SIKILASTIRMA: yapilandirmasiz {len(SIK_KORPUS)} ad x 3 CLI kapisi -> taban farki YALNIZ "
         f"gramer disi Z/Y adlarda ({len(beklenen)} ad: {beklenen!r}) ve YALNIZ kabul->red; gevsetme 0",
         not sapma and all(sorted(v) == beklenen for v in sik.values()), [sapma[:4], sik])


def bolum_k(TPT, TPM, TSC, TPB, TBC):
    d = proje(YAML_NS)
    tp = kanca_agaci(d)
    ekle("K1 ⭐ taban: push/pull/scaffold kayitli NS'yi REDDEDIYORDU",
         push(TPT, "/NSPC/SD001_P01")[0] == 2 and pull(TPM, "/NSPC/SD001_P01")[0] == 1
         and scaffold(TSC, "/NSPC/SD001_P01")[0] == 2, "")
    ekle("K2 ⭐ taban kanca NS textpool dosyasini TANIMIYORDU (kapi acik)",
         sinif(TPB, tp / "#nspc#sd001_p01.symbols.txt") is None, "")
    t = envanter(TBC)
    ekle("K3 ⭐ taban envanter kayitli NS nesnesini ATLIYORDU",
         isinstance(t, set) and "/NSPC/SD001_T01" not in t and "ZSD001_T01" in t, t)


def main() -> int:
    A = _imp("utils.ad_politikasi")
    _imp("sap_adt_lib")
    PT = _imp("push_textpool")
    PM = _imp("pull_msag_textpool")
    SC = _imp("scaffold_classic_program")
    BC = _imp("build_cbo_inventory")
    PB = _imp("_pbe_msag_textpool")
    try:
        TPT = _taban_modul("scripts/push_textpool.py", "push_textpool_taban")
        TPM = _taban_modul("scripts/pull_msag_textpool.py", "pull_msag_textpool_taban")
        TSC = _taban_modul("scripts/scaffold_classic_program.py", "scaffold_taban")
        TBC = _taban_modul("scripts/build_cbo_inventory.py", "build_cbo_inventory_taban")
        TPB = _taban_modul("scripts/hooks/_pbe_msag_textpool.py", "_pbe_msag_textpool_taban")
    except Exception as exc:                           # noqa: BLE001
        print(f"[fixture-hatasi] taban kurulamadi: {exc}")
        return 3
    for fn, a in ((bolum_p, (PT,)), (bolum_q, (PM,)), (bolum_c, (SC, TSC)), (bolum_b, (BC, TBC)),
                  (bolum_h, (PB, TPB)), (bolum_a, (A,)), (bolum_s, (PT, TPT, PM, TPM, SC, TSC)),
                  (bolum_k, (TPT, TPM, TSC, TPB, TBC))):
        try:
            fn(*a)
        except Exception as exc:                       # çökme != FAIL: ölçülür
            ekle(f"[BOLUM-COKTU] {fn.__name__}", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_KUM, ignore_errors=True)
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYONLAR: kip -> (dosya, çapa, yerine, düşmesi İLAN edilen vektör kümesi)
_AP = "scripts/utils/ad_politikasi.py"
_PT = "scripts/push_textpool.py"
_PM = "scripts/pull_msag_textpool.py"
_SC = "scripts/scaffold_classic_program.py"
_BC = "scripts/build_cbo_inventory.py"
_PB = "scripts/hooks/_pbe_msag_textpool.py"
BS = chr(92)
MUTASYONLAR = {
    "--mutasyon-push-eski": (_PT, "    if not _ap.musteri_adi_mi(prog, \"prog\"):\n",
                             "    if not prog[:1].upper() in (\"Z\", \"Y\"):\n",
                             {"P1", "S"}),   # T1 KALIR: red METNI hâlâ ortak yardımcıdan (`msys-ipucu` kipi ölçer)
    "--mutasyon-pull-eski": (_PM, "    if not _ap.musteri_adi_mi(a.nesne, \"msag\" if a.tur == \"msag\" else \"prog\"):\n",
                             "    if not a.nesne[:1].upper() in (\"Z\", \"Y\"):\n", {"Q1", "S"}),
    "--mutasyon-scaffold-eski": (_SC, "    if not _ap.musteri_adi_mi(args.program, \"prog\"):\n",
                                 "    if not args.program.upper().startswith((\"Z\", \"Y\")):\n",
                                 {"C1", "S"}),   # C3 KALIR: eski önek kontrolü de `/SCWM/`'i reddeder
    "--mutasyon-scaffold-dosya": (_SC, "    dosya = _ap.dosya_adi(prog)\n", "    dosya = prog.lower()\n", {"C1"}),
    "--mutasyon-cbo-eski": (_BC, "                                or _ap.ad_namespace(name.upper()) in ns_liste):\n",
                            "                                or False):\n", {"B1"}),
    "--mutasyon-cbo-tam-gramer": (_BC, "            if not name or not (name.upper().startswith((\"Z\", \"Y\"))\n"
                                       "                                or _ap.ad_namespace(name.upper()) in ns_liste):\n",
                                  "            if not name or not _ap.musteri_adi_mi(name.upper()):\n", {"B1", "B2"}),
    "--mutasyon-kanca-ns-yok": (_PB, "    return _ns_ad(parca, tip)\n", "    return None\n", {"H1", "H2", "H3"}),
    "--mutasyon-kanca-kayit-sarti": (_PB, "        if ad.startswith(\"/\") and _ap.musteri_adi_mi(ad, tip):\n",
                                     "        if ad.startswith(\"/\"):\n", {"H4"}),
    "--mutasyon-kanca-msys-notu": (_PB, "(_MSYS_NOTU if prog.startswith(\"/\") else \"\")", "\"\"", {"H1"}),
    "--mutasyon-msys-ipucu": (_AP, "    if _SURUCU_YOLU.match(a):\n", "    if False:\n", {"T1"}),
    "--mutasyon-dosya-adi-ayirac": (_AP, "    if \"/\" in a or \"" + BS + BS + "\" in a:\n", "    if False:\n", {"A2"}),
}
KIPLER = sorted(MUTASYONLAR)


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="q403_kum_"))
    try:
        for alt in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / alt, kok / alt,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kok / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        env = dict(os.environ)
        env["Q403_GIT_KOK"] = str(_GIT_KOK)
        r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, cwd=str(kok), env=env)
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    sys.exit(main())

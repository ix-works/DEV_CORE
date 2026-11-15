#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""namespace_tesisat — müşteri namespace'li (`/<NS>/`) ve Y önekli adların "eski tesisat" noktaları (2026-11-15).

NEDEN VAR
  Q393/#402/#405/#416 müşteri ad alanı kararını `scripts/utils/ad_politikasi.py`'ye taşıdı; tarama
  (2026-11-15, salt-okur) kararın dışında kalan eski betiklerde altı kardeş grup buldu: yerel dosya
  yolu YAZMA yönü (`Path / "/NS/X.abap"` sürücü köküne kaçar), `\\w+` ile ad yakalama, OData servis
  kökünde sabit `sap/`, URL→ad ters dönüşümünde `%2f` çözülmemesi, Z'ye kilitli paket/RAP ad kalıbı,
  başvurulan yapıya müşteri kararı uygulanması — ve sızıntı kapısının Y/namespace'e kör olması.

VEKTÖRLER (taban `4323bba` = düzeltme öncesi; K* ayırt ediciliği ölçer)
  A   A1-A4 ad_politikasi yeni yardımcıları (`yerel_ad` · `musteri_govdesi` · `url_adi`)
  G1  D1 ⭐ download_object `/NSPC/CL_X` → sandbox `#nspc#cl_x.abap`, kök dışına yol YOK · D1z KONTROL Z/Y
      dosya adı tabanla AYNI (`ZCL_X.abap`, `YCL_X.abap`) · D2 push_object varsayılan yolu aynı ad ·
      D3 ⭐ delete_object sandbox dosyasını siler, kök dışında exists/unlink YOK · D4 indirici betikler
      `yerel_ad` ile yazar (statik çapa) · B1 ⭐ bootstrap `/NSPC/SD001_CLC` → `SD/#nspc#sd001_clc`,
      UYARI yok · B1z KONTROL `ZSD001_CLC` klasörü + UYARI yok, küçük harfli ad UYARI · B2 `/AB/X_CLC`
      HATA + hiçbir şey yaratılmaz · B3 Y paketi UYARI yok (⚠GEVŞETME, yalnız uyarı metni)
  G2  F1 ⭐ gen_field_table namespace'li entity adı + projeksiyon + gövde · F1z KONTROL Z adı · F2 gramer
      dışı ad '?' · F3 projeksiyon arayüz dosyası `#ns#x.cds` klasör içinde · P1 ⭐ program_to_spec
      `FROM /nspc/tab` ayrı kovada, `ytab` standart kovada DEĞİL · P1z KONTROL Z/standart çıktı tabanla aynı
  G3  O1 ⭐ odata_servis_yolu / odata_uri_servisi · O2 ⭐ check_ui_odata_refs fetch_metadata URL'i · O3 ⭐
      manifest'ten namespace'li ana servis + model haritası · O3z KONTROL `sap/` manifestinde servis aynı ·
      O4 ⭐ create_rap_service step_verify URL'i (Z KONTROL dahil)
  G4  U1 ⭐ `_object_name_from_url` `%2f` çözer + 423 teşhis metni · U1z KONTROL Z · U2 statik çapa (lock
      403 metni + sap_set_object_description unlock uyarısı `url_adi`)
  G5  C1 ⭐ validate_sql_view_names `/NSPC/SD001_CLC` paketi + `#nspc#…cds` RAP entity → 0 hata · C2 Y
      paketi + Y entity → 0 hata · C3 kayıtsız `/SCWM/` paketi → B-5 · C4/C4b KONTROL Z paket adlarında
      `_derive_prefixes` + doğrulama tabanla AYNI · C5 ⭐ main `--only /NSPC/SD001_I_X` → create_one'a `/NSPC/SD001_I_X`
  G6  R1 ⭐ create_table ref_structure `/SCWM/S_X` kabul (başvuru = yalnız biçim) · R2 KONTROL yaratılan
      nesnede `/SCWM/X_TAB` RED · R3 gramer dışı başvuru RED · R4 CDS `from /scwm/…` ad denetimi yok (ölçüm) ·
      R5 DTEL domain adına müşteri denetimi yok (ölçüm, AST)
  K10 table_contents URL'i `%2F…` · K11 paket araması namespace'li pakette tek desen (Z KONTROL aynı) ·
  K12 kilit nesnesi E uyarısı namespace sonrası · K14 init_project şablonunda `customer_namespaces`
  Z9  ⭐ sızıntı kapısı Y + `/<NS>/` gövdeyi yakalar · Z9a örnek gövde allowlist'te · Z9z KONTROL Z bulguları
      tabanla AYNI · Z9fp FP: çekirdek ağacında bulgu 0
  K   taban: K1 download kökten kaçar · K2 gen_field_table '?' · K3 program_to_spec ns tabloyu kaybeder ·
      K4 OData sap/ sabit · K5 URL adı `%2F…` · K6 validate B-5 · K7 sızıntı Y/NS kör

KULLANIM
  python tests/fixtures/namespace_tesisat/run.py
  python tests/fixtures/namespace_tesisat/run.py --mutasyon-<kip>
  Mutasyon exit: 1 = ilan edilen küme TAM düştü · 2 = sapma · 3 = çapa ≠ 1 / derlenmedi / sayı yok.

GÜVENLİK: SAP'ye istek YOK (sahte istemciler). Yol ölçümü sandbox altında. İKİ katman:
  (1) taban (kusurlu) kod kök dışı yola SAHTE `open`/`IzPath` üzerinden "yazar" (kaçış kaydedilir);
  (2) SÜREÇ GENELİ YAZMA KALKANI (`_kalkan_kur`, import anında; mutasyon alt sürecinde de) — geçici
  dizin kökü dışına her yazma/silme PermissionError + `KACAK` kaydı. (2) olmadan MUTANT kopyalar kusuru
  gerçekten işletti: ilk koşumda sürücü köküne `NSPC/…` ve `AB/X_CLC/` açıldı (2026-11-15, elle silindi).
  Z0 kalkanı her koşumda sınar; koşum sonu `[KALKAN] … denemesi: N` satırı, mutasyon satırı `kalkan=N`.
  Her koşum kendi `mkdtemp` kumundan başlar; kök durumuna bağlı hüküm yok (B2 red NEDENİNİ ölçer).
  Namespace yapılandırması `ad_politikasi.musteri_namespaceleri` yamalanarak verilir (yapılandırma
  okuma yolu `q393_namespace_ad_politikasi`'nın konusudur).
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
TABAN_SHA = "4323bba"
_GIT_KOK = Path(os.environ.get("NST_GIT_KOK") or REPO)
_KUM = Path(tempfile.mkdtemp(prefix="nst_")).resolve()

# ── YAZMA KALKANI (2026-11-15) ─────────────────────────────────────────────────────────────
# Bu fixture'ın konusu "yol sürücü köküne kaçar" kusurudur; MUTANT kopyalar o kusuru GERÇEKTEN
# işletir (ölçüldü: ilk koşumda `C:/NSPC/CL_X.abap`, `C:/NSPC/SD001_CLC/`, `C:/AB/X_CLC/`
# açıldı — taban korumaları `IzPath` + sahte `open` yalnız TABAN modüle takılıydı). Kalkan süreç
# genelidir: geçici dizin kökü DIŞINA her yazma/silme PermissionError + `KACAK` kaydı. Okuma serbest.
# Mutasyon alt süreci aynı run.py'yi koştuğu için kalkan orada da kuruludur.
_IZINLI_KOK = Path(tempfile.gettempdir()).resolve()
KACAK: list = []


def _izinli(p) -> bool:
    try:
        Path(os.fspath(p)).resolve().relative_to(_IZINLI_KOK)
        return True
    except Exception:
        return False


def _kalkan(islem, p):
    if isinstance(p, int) or _izinli(p):
        return
    KACAK.append((islem, str(p)))
    raise PermissionError(f"[fixture-kalkani] gecici kok disina {islem}: {p}")


def _kalkan_kur():
    import builtins
    import io as _io
    import pathlib as _pl
    _ac = builtins.open

    def _open(file, mode="r", *a, **k):
        if any(c in mode for c in "wax+"):
            _kalkan("open:" + mode, file)
        return _ac(file, mode, *a, **k)
    builtins.open = _open
    _io.open = _open
    for ad in ("mkdir", "touch", "unlink", "rmdir", "write_text", "write_bytes", "rename", "replace"):
        asil = getattr(_pl.Path, ad)

        def sar(self, *a, _asil=asil, _ad=ad, **k):
            _kalkan(_ad, self)
            return _asil(self, *a, **k)
        setattr(_pl.Path, ad, sar)
    asil_open = _pl.Path.open

    def p_open(self, mode="r", *a, **k):
        if any(c in mode for c in "wax+"):
            _kalkan("Path.open:" + mode, self)
        return asil_open(self, mode, *a, **k)
    _pl.Path.open = p_open
    for ad in ("makedirs", "mkdir", "remove", "unlink", "rmdir", "rename", "replace"):
        asil = getattr(os, ad)

        def sar_os(yol, *a, _asil=asil, _ad=ad, **k):
            _kalkan("os." + _ad, yol)
            return _asil(yol, *a, **k)
        setattr(os, ad, sar_os)
    asil_rmtree = shutil.rmtree

    def rmtree(yol, *a, **k):
        _kalkan("rmtree", yol)
        return asil_rmtree(yol, *a, **k)
    shutil.rmtree = rmtree


_kalkan_kur()
_PROJE = _KUM / "proje"
_PROJE.mkdir()
(_PROJE / "project.yaml").write_text("sap_profile: s4_private\n", encoding="utf-8")
os.environ["CLAUDE_PROJECT_DIR"] = str(_PROJE)
for _k in ("IX_CUSTOMER_NAMESPACES", "IX_SOURCE_ROOT", "ADT_SAP_URL", "ADT_SAP_USER", "ADT_SAP_PASSWORD"):
    os.environ.pop(_k, None)
os.chdir(_PROJE)
for _p in (REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

S: list = []
NS_LISTE = ("/NSPC/",)


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


def _ic(p) -> bool:
    try:
        Path(p).resolve().relative_to(_KUM)
        return True
    except Exception:
        return False


@contextlib.contextmanager
def _akis_koru():
    """Bazı betikler import anında `sys.stdout`'u `TextIOWrapper(sys.stdout.buffer)` ile DEĞİŞTİRİR;
    aynı tamponu ikinci kez sarmak ilk sarmalayıcı çöp toplanınca tamponu KAPATIR (ölçüldü:
    `I/O operation on closed file`). Import süresince sahte akış verilir, sonra asıl akış geri konur."""
    asil = (sys.stdout, sys.stderr)
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    try:
        yield
    finally:
        sys.stdout, sys.stderr = asil


def _imp(ad):
    with _akis_koru():
        __import__(ad)
    return sys.modules[ad]


def _taban_modul(yol, ad):
    g = subprocess.run(["git", "-C", str(_GIT_KOK), "show", f"{TABAN_SHA}:{yol}"], capture_output=True)
    if g.returncode != 0:
        raise RuntimeError(f"git show {TABAN_SHA}:{yol} rc={g.returncode}")
    m = types.ModuleType(ad)
    m.__file__ = str(REPO / yol)
    sys.modules[ad] = m
    with _akis_koru():
        exec(compile(g.stdout.decode("utf-8"), str(REPO / yol), "exec"), m.__dict__)
    return m


@contextlib.contextmanager
def sessiz():
    o, e = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
        yield o, e


# ── kök dışına dokunmayan Path (3.11: `/` alt sınıfı korur) ────────────────────────────────
KAYIT: list = []


class IzPath(type(Path())):
    def exists(self, *a, **k):
        KAYIT.append(("exists", str(self)))
        return super().exists() if _ic(self) else False

    def unlink(self, *a, **k):
        KAYIT.append(("unlink", str(self)))
        if not _ic(self):
            return None          # kök dışı: ASLA gerçek silme
        return super().unlink(*a, **k)

    def mkdir(self, *a, **k):
        KAYIT.append(("mkdir", str(self)))
        if not _ic(self):
            return None
        return super().mkdir(*a, **k)


class SahteADT:
    def __init__(self):
        self.url = "https://sahte.invalid"

    def get_object_source(self, url):
        return "REPORT x.\r\n"

    def lock_object(self, url, transport=None):
        return "NO_LOCK_SUPPORT"

    def delete_object(self, url, handle, transport):
        return None

    def get_package_contents(self, p):
        raise RuntimeError("nodestructure yok (sahte)")


def sap_client_ornegi(SCm, alt="scr"):
    c = object.__new__(SCm.SAPClient)
    c.adt_client = SahteADT()
    c.local_base = IzPath(_KUM / alt / "classes")
    c.debug_enabled = False
    return c


# ── G1 ─────────────────────────────────────────────────────────────────────────────────────
def bolum_g1(SCm, TSC, A):
    KAYIT.clear()
    c = sap_client_ornegi(SCm, "d1")
    k0 = len(KACAK)
    with sessiz():
        with contextlib.suppress(PermissionError):    # kalkan: kök dışı yazma = vektör FAIL, bölüm çökmez
            c.download_object("/NSPC/CL_X", "class")
    hedef = _KUM / "d1" / "classes" / "#nspc#cl_x.abap"
    disari = [k for k in KAYIT if not _ic(k[1])] + KACAK[k0:]
    ekle("D1", hedef.is_file() and not disari, f"dosya={hedef.is_file()} disari={disari}")

    yazilan = []

    def sahte_open(p, *a, **k):
        yazilan.append(str(p))
        if _ic(p):
            return open(p, *a, **k)
        return io.StringIO()
    TSC.open = sahte_open
    try:
        for ad in ("ZCL_X", "YCL_X"):
            yazilan.clear()
            ct = sap_client_ornegi(TSC, "d1t")
            with sessiz():
                ct.download_object(ad, "class")
            taban_ad = Path(yazilan[0]).name if yazilan else None
            with sessiz():
                sap_client_ornegi(SCm, "d1y").download_object(ad, "class")
            yeni = (_KUM / "d1y" / "classes" / f"{ad}.abap").is_file()
            ekle(f"D1z-{ad}", taban_ad == f"{ad}.abap" and yeni, f"taban={taban_ad} yeni={yeni}")
        yazilan.clear()
        with sessiz():
            sap_client_ornegi(TSC, "k1").download_object("/NSPC/CL_X", "class")
        ekle("K1", yazilan and not _ic(yazilan[0]), f"taban yazdigi={yazilan}")
    finally:
        del TSC.open

    k0 = len(KACAK)
    r = {}
    with sessiz():
        with contextlib.suppress(PermissionError):
            r = sap_client_ornegi(SCm, "d2").push_object("/NSPC/CL_X", "class")
    sp = str(r.get("source_path", ""))
    ekle("D2", sp.replace("\\", "/").endswith("d2/classes/#nspc#cl_x.abap") and _ic(sp)
         and len(KACAK) == k0, f"{sp} kacak={KACAK[k0:]}")

    KAYIT.clear()
    d3 = _KUM / "d3" / "classes"
    d3.mkdir(parents=True)
    (d3 / "#nspc#cl_x.abap").write_text("x", encoding="utf-8")
    c3 = sap_client_ornegi(SCm, "d3")
    k0 = len(KACAK)
    ok = False
    with sessiz():
        with contextlib.suppress(PermissionError):
            ok = c3.delete_object("/NSPC/CL_X", "class", transport="<TR>", confirm=False)
    disari = [k for k in KAYIT if not _ic(k[1])] + KACAK[k0:]
    ekle("D3", ok and not (d3 / "#nspc#cl_x.abap").exists() and not disari, f"ok={ok} disari={disari}")

    hepsi = True
    for f in ("scripts/download_object.py", "scripts/download_ddic_objects.py"):
        t = (REPO / f).read_text(encoding="utf-8")
        hepsi &= bool(re.search(r'file_path = target_dir / f"\{yerel_ad\(', t))
    ekle("D4", hepsi)


def bootstrap(BP, ad):
    kok = _KUM / f"bp{len(S)}"
    (kok / "SRC").mkdir(parents=True)
    tm = kok / "tmpl"
    tm.mkdir()
    (tm / "folders.txt").write_text("docs\n", encoding="utf-8")
    (tm / "README.md.tmpl").write_text("{PKG_FULL}\n", encoding="utf-8")
    eski = sys.argv
    sys.argv = ["bootstrap_package.py", ad, "--title", "T", "--module", "SD",
                "--source-root", str(kok / "SRC"), "--templates-root", str(tm)]
    k0 = len(KACAK)
    try:
        with sessiz() as (o, e):
            try:
                rc = BP.main()
            except PermissionError:
                rc = "KALKAN"
        if len(KACAK) > k0:      # kök dışına yazma denendi ⇒ hiçbir rc beklentisi tutmaz
            rc = "KALKAN"
    finally:
        sys.argv = eski
    return rc, kok / "SRC" / "SD", e.getvalue()


def bolum_b(BP, A):
    rc, sd, err = bootstrap(BP, "/NSPC/SD001_CLC")
    icerik = sorted(p.name for p in sd.iterdir()) if sd.is_dir() else []
    ekle("B1", rc == 0 and (sd / "#nspc#sd001_clc" / "README.md").is_file() and "UYARI" not in err
         and icerik == ["#nspc#sd001_clc"], f"rc={rc} icerik={icerik} err={err[:160]}")
    rc, sd, err = bootstrap(BP, "ZSD001_CLC")
    ekle("B1z-Z", rc == 0 and (sd / "ZSD001_CLC" / "README.md").is_file() and "UYARI" not in err,
         f"rc={rc} err={err[:120]}")
    rc, sd, err = bootstrap(BP, "zsd001_clc")
    ekle("B1z-kucuk", "UYARI" in err, err[:120])
    rc, sd, err = bootstrap(BP, "/AB/X_CLC")
    # red NEDENİ de ölçülür: "klasör adına çevrilemedi" — kök durumuna bağlı "zaten var" reddi sayılmaz
    ekle("B2", rc == 1 and "klasör adına çevrilemedi" in err and not sd.exists(), f"rc={rc} err={err[:160]}")
    rc, sd, err = bootstrap(BP, "YSD001_CLC")
    ekle("B3", rc == 0 and "UYARI" not in err, err[:120])


# ── G2 ─────────────────────────────────────────────────────────────────────────────────────
CDS_NS = ("@ObjectModel.usageType: { serviceQuality: #A, sizeCategory: #L }\n"
          "define view entity /NSPC/SD001_C_X as projection on /NSPC/SD001_I_X {\n"
          "  key Vbeln,\n  Posnr\n}\n")


def bolum_g2(GF, TGF, PS, TPS):
    n, p, g = GF._body(CDS_NS)
    ekle("F1", (n, p) == ("/NSPC/SD001_C_X", "/NSPC/SD001_I_X") and "Vbeln" in g and "#A" not in g, (n, p, g))
    z = CDS_NS.replace("/NSPC/SD001_C_X", "ZSD001_C_X").replace("/NSPC/SD001_I_X", "ZSD001_I_X")
    ekle("F1z", GF._body(z) == TGF._body(z) == ("ZSD001_C_X", "ZSD001_I_X", "\n  key Vbeln,\n  Posnr\n"),
         (GF._body(z), TGF._body(z)))
    ekle("F2", GF._body(CDS_NS.replace("/NSPC/SD001_C_X", "/AB/X"))[0] == "?")
    d = _KUM / "f3"
    d.mkdir()
    (d / "c.cds").write_text(CDS_NS, encoding="utf-8")
    (d / "#nspc#sd001_i_x.cds").write_text(
        "define view entity /NSPC/SD001_I_X as select from t {\n  @EndUserText.label: 'Fatura'\n"
        "  key Vbeln,\n  Posnr\n}\n", encoding="utf-8")
    md = GF.build_table(str(d / "c.cds"))
    ekle("F3", "| Vbeln | Fatura |" in md, md[-200:])
    n2, p2, g2 = TGF._body(CDS_NS)
    ekle("K2", n2 == "?" and "#A" in g2, (n2, p2, g2[:60]))

    src = ("REPORT /nspc/sd001_r_x.\nSELECT * FROM ytab_cust INTO @x.\n"
           "SELECT * FROM /nspc/tab_cust INTO @y.\nSELECT * FROM vbak INTO @z.\nSELECT * FROM zt_kendi INTO @w.\n")
    doc = PS.render(PS.extract(src), ["x.abap"])
    std = next((l for l in doc.splitlines() if l.startswith("- **Standart")), "")
    nsl = next((l for l in doc.splitlines() if l.startswith("- **Namespace")), "")
    ekle("P1", "/nspc/tab_cust" in nsl and "ytab_cust" not in std and "vbak" in std
         and "# TASLAK FS/TS — /nspc/sd001_r_x" in doc, doc[:300])
    # KONTROL: Z/standart çıktı tabanla aynı (yalnız kova başlığı "Z tablolar" → "Z/Y tablolar") +
    # Türkçe sözcük KESİLMEZ (`satır` → `sat` değil; ASCII aday + harf sınırı — bağımsız kapı bulgusu)
    zsrc = ("REPORT zprog.\nSELECT * FROM vbak INTO @z.\nSELECT * FROM zt_kendi INTO @w.\nTABLES: mara.\n"
            "\" iki satır from satır gelir\n")
    yeni = PS.render(PS.extract(zsrc), ["x"]).replace("- **Z/Y tablolar:**", "- **Z tablolar:**")
    ekle("P1z", yeni == TPS.render(TPS.extract(zsrc), ["x"])
         and PS.extract(zsrc)["select_from"] == TPS.extract(zsrc)["select_from"], PS.extract(zsrc)["select_from"])
    tdoc = TPS.render(TPS.extract(src), ["x.abap"])
    tstd = next((l for l in tdoc.splitlines() if l.startswith("- **Standart")), "")
    ekle("K3", "/nspc/tab_cust" not in tdoc and "ytab_cust" in tstd, tdoc[:200])


# ── G3 ─────────────────────────────────────────────────────────────────────────────────────
class SahteOturum:
    URL: list = []

    def __init__(self):
        self.auth = None
        self.verify = True

    def get(self, url, params=None, timeout=None, **k):
        SahteOturum.URL.append(url)
        raise RuntimeError("sahte: ag yok")


def bolum_g3(A, CU, TCU, CR):
    ekle("O1", A.odata_servis_yolu("/NSPC/SD001_SRV") == "/sap/opu/odata/nspc/SD001_SRV"
         and A.odata_servis_yolu("ZSD001_SRV") == "/sap/opu/odata/sap/ZSD001_SRV"
         and A.odata_uri_servisi("/sap/opu/odata/nspc/SD001_SRV/") == "/NSPC/SD001_SRV"
         and A.odata_uri_servisi("/sap/opu/odata/sap/ZSD001_SRV/") == "ZSD001_SRV"
         and A.odata_uri_servisi("/sap/opu/odata/ab/X/") is None
         and A.odata_uri_servisi("/sap/opu/odata/nspc/SD001_SRV/Annotations(x)/$value/") is None)
    cfg = {"ADT_SAP_URL": "https://h", "ADT_SAP_USER": "u", "ADT_SAP_PASSWORD": "p"}
    sonuc = []
    for M in (CU, TCU):
        eski = M.requests.Session
        M.requests.Session = SahteOturum
        try:
            for s in ("/NSPC/SD001_SRV", "ZSD001_SRV"):
                SahteOturum.URL.clear()
                try:
                    M.fetch_metadata(cfg, s)
                except RuntimeError:
                    pass
                sonuc.append(SahteOturum.URL[:1])
        finally:
            M.requests.Session = eski
    ekle("O2", sonuc[0] == ["https://h/sap/opu/odata/nspc/SD001_SRV/$metadata"]
         and sonuc[1] == sonuc[3] == ["https://h/sap/opu/odata/sap/ZSD001_SRV/$metadata"], sonuc)
    ekle("K4", sonuc[2] == ["https://h/sap/opu/odata/sap//NSPC/SD001_SRV/$metadata"], sonuc[2])

    def uygulama(uri, ad):
        app = _KUM / ad
        (app / "webapp" / "controller").mkdir(parents=True)
        (app / "webapp" / "manifest.json").write_text(json.dumps({
            "sap.app": {"dataSources": {"mainService": {"uri": uri, "type": "OData"}}},
            "sap.ui5": {"models": {"": {"dataSource": "mainService"}}}}), encoding="utf-8")
        (app / "webapp" / "controller" / "A.controller.js").write_text(
            'this.getView().getModel().read("/Foo", {});\n', encoding="utf-8")
        return app

    def servis_bul(M, app):
        gorulen = []
        eski = (M.load_conn, M.metadata_al, sys.argv)
        M.load_conn = lambda cwd: {}
        M.metadata_al = lambda cfg, s: (gorulen.append(s), (None, "sahte"))[1]
        sys.argv = ["check_ui_odata_refs.py", "--app", str(app)]
        try:
            with sessiz() as (o, e):
                try:
                    M.main()
                except SystemExit:
                    pass
        finally:
            M.load_conn, M.metadata_al, sys.argv = eski
        return gorulen, o.getvalue()

    a_ns = uygulama("/sap/opu/odata/nspc/SD001_SRV/", "o3")
    g, out = servis_bul(CU, a_ns)
    harita, _ = CU.model_haritasi(str(a_ns))
    ekle("O3", g[:1] == ["/NSPC/SD001_SRV"] and harita == {"": "/NSPC/SD001_SRV"}, f"{g} {harita} {out[-160:]}")
    a_z = uygulama("/sap/opu/odata/sap/ZSD001_SRV/", "o3z")
    gz, _ = servis_bul(CU, a_z)
    gzt, _ = servis_bul(TCU, a_z)
    ekle("O3z", gz[:1] == gzt[:1] == ["ZSD001_SRV"] and CU.model_haritasi(str(a_z)) == TCU.model_haritasi(str(a_z)),
         (gz, gzt))
    # SAP'nin kendi namespace'li servisi (bildirilmemiş) ana servis SEÇİLMEZ → eski davranış (exit 2)
    a_s = uygulama("/sap/opu/odata/iwfnd/CATALOGSERVICE/", "o3s")
    gs, outs = servis_bul(CU, a_s)
    ekle("O3s", gs == [] and "servis adi cozulemedi" in outs, f"{gs} {outs[-160:]}")

    class Istemci:
        url = "https://h"

        class session:
            URL: list = []

            @staticmethod
            def get(url, **k):
                Istemci.session.URL.append(url)
                return types.SimpleNamespace(status_code=200, text="<edmx:Edmx/>")
    eski = CR.SRVB_NAME
    try:
        out = []
        for s in ("/NSPC/SD001_UI_O2", "ZSD001_UI_ORDER_O2"):
            CR.SRVB_NAME = s
            with sessiz():
                CR.step_verify(Istemci)
            out.append(Istemci.session.URL[-1])
    finally:
        CR.SRVB_NAME = eski
    ekle("O4", out == ["https://h/sap/opu/odata/nspc/SD001_UI_O2/$metadata",
                       "https://h/sap/opu/odata/sap/ZSD001_UI_ORDER_O2/$metadata"], out)


# ── G4 ─────────────────────────────────────────────────────────────────────────────────────
def bolum_g4(LIB, TLIB):
    c = object.__new__(LIB.SAPADTClient)
    t = object.__new__(TLIB.SAPADTClient)
    u = "/sap/bc/adt/oo/classes/%2fnspc%2fcl_x/source/main"
    tani = c.put_423_diagnosis(u)
    ekle("U1", c._object_name_from_url(u) == "/NSPC/CL_X" and "obj_name = '/NSPC/CL_X'" in tani,
         c._object_name_from_url(u))
    zs = ["/sap/bc/adt/oo/classes/zcl_foo", "/sap/bc/adt/programs/programs/zprog/source/main?x=1", "", "/"]
    ekle("U1z", [c._object_name_from_url(x) for x in zs] == [t._object_name_from_url(x) for x in zs]
         == ["ZCL_FOO", "ZPROG", "<OBJE>", "<OBJE>"], [c._object_name_from_url(x) for x in zs])
    ekle("K5", t._object_name_from_url(u) == "%2FNSPC%2FCL_X", t._object_name_from_url(u))
    lib = (REPO / "scripts" / "sap_adt_lib.py").read_text(encoding="utf-8")
    sod = (REPO / "scripts" / "sap_set_object_description.py").read_text(encoding="utf-8")
    ekle("U2", 'f"Object: {self._object_name_from_url(object_url)}",' in lib
         and 'kilit_birakilamadi_uyarisi(url_adi(url) or "<OBJE>")' in sod)


# ── G5 ─────────────────────────────────────────────────────────────────────────────────────
def _cds(d, dosya, ad):
    d.mkdir(parents=True, exist_ok=True)
    p = d / dosya
    p.write_text(f"@EndUserText.label: 'x'\ndefine view entity {ad} as select from t {{ key a }}\n", encoding="utf-8")
    return p


def bolum_g5(PC, TPC):
    d = _KUM / "c1"
    e = PC.validate_sql_view_names([_cds(d, "#nspc#sd001_i_x.cds", "/NSPC/SD001_I_X")], package="/NSPC/SD001_CLC")
    ekle("C1", e == [] and PC._derive_prefixes("/NSPC/SD001_CLC") == ("/NSPC/SD001_V_", "/nspc/sd001_ddl_"), e)
    e2 = PC.validate_sql_view_names([_cds(d, "ysd001_i_x.cds", "YSD001_I_X")], package="YSD001_CLC")
    ekle("C2", e2 == [], e2)
    e3 = PC.validate_sql_view_names([_cds(d, "#scwm#sd001_i_x.cds", "/SCWM/SD001_I_X")], package="/SCWM/SD001_CLC")
    ekle("C3", len(e3) == 1 and "B-5" in e3[0], e3)
    paketler = ["ZMOD001_CLC", "ZSD001", "zsd001_clc", "ZSDX_CLC", "ZMOD0011_CLC", "LEGACY_STUFF", "ZMOD002_X",
                "ZABCDE001_CLC", "Z_SD001", None, ""]
    ekle("C4", [PC._derive_prefixes(p) for p in paketler] == [TPC._derive_prefixes(p) for p in paketler],
         [PC._derive_prefixes(p) for p in paketler])
    ze = [_cds(d, "zmod001_i_x.cds", "ZMOD001_I_X"), _cds(d, "zmod001_x_bad.cds", "ZMOD001_X_BAD")]
    # Z HÜKMÜ tabanla aynı (hangi dosya, hangi kural); biçim metni önek-genel hâle getirildi (F4)
    def _hukum(es):
        return [m.split(" YASAK")[0] for m in es]
    yz, tz = (PC.validate_sql_view_names(ze, package="ZMOD001_CLC"),
              TPC.validate_sql_view_names(ze, package="ZMOD001_CLC"))
    ekle("C4b", len(yz) == 1 and _hukum(yz) == _hukum(tz), (yz, tz))
    k6 = TPC.validate_sql_view_names([d / "#nspc#sd001_i_x.cds"], package="/NSPC/SD001_CLC")
    ekle("K6", len(k6) == 1 and "B-5" in k6[0], k6)

    src = _KUM / "c5"
    _cds(src, "#nspc#sd001_i_x.cds", "/NSPC/SD001_I_X")
    _cds(src, "#nspc#sd001_i_y.cds", "/NSPC/SD001_I_Y")
    ad = []

    class FakeClient:
        pass
    eski = (PC.SAPADTClient, PC.create_one, sys.argv)
    PC.SAPADTClient = FakeClient
    PC.create_one = lambda **k: (ad.append(k["name"]), PC.SONUC_DRY_RUN)[1]
    sys.argv = ["populate_cds_views.py", "--package", "/NSPC/SD001_CLC", "--transport", "<TR>",
                "--source-dir", str(src), "--dry-run", "--only", "/NSPC/SD001_I_X"]
    try:
        with sessiz() as (o, _e):
            rc = PC.main()
    finally:
        PC.SAPADTClient, PC.create_one, sys.argv = eski
    ekle("C5", ad == ["/NSPC/SD001_I_X"], f"rc={rc} ad={ad} {o.getvalue()[-200:]}")


# ── G6 ─────────────────────────────────────────────────────────────────────────────────────
class _Dur(Exception):
    pass


def bolum_g6(LIB):
    c = object.__new__(LIB.SAPADTClient)
    gercek = c._validate_object_name

    def ref_sonucu(ref):
        def sar(name, object_type="Object", **k):
            gercek(name, object_type, **k)
            if object_type == "Referenced Structure":
                raise _Dur()
        c._validate_object_name = sar
        c._validate_package_name = lambda *a, **k: None
        c._validate_transport = lambda *a, **k: None
        c.csrf_token = "x"
        try:
            c.create_table("ZSD001_T_X", "Tablo", "ZSD001_CLC", ref_structure=ref, transport="<TR>")
        except _Dur:
            return "kabul"
        except LIB.SAPValidationError:
            return "red"
        except Exception as exc:                     # noqa: BLE001
            return f"baska:{type(exc).__name__}:{exc}"[:120]
        return "akis-bitti"
    sonuc = {r: ref_sonucu(r) for r in ("/SCWM/S_X", "BAPIRET2", "ZSD001_S_X", "/AB/X", "/scwm/s_x")}
    ekle("R1", sonuc["/SCWM/S_X"] == "kabul" and sonuc["BAPIRET2"] == "kabul" and sonuc["ZSD001_S_X"] == "kabul", sonuc)
    try:
        gercek("/SCWM/X_TAB", "Table")
        r2 = "kabul"
    except LIB.SAPValidationError:
        r2 = "red"
    ekle("R2", r2 == "red")
    ekle("R3", sonuc["/AB/X"] == "red" and sonuc["/scwm/s_x"] == "red", sonuc)
    try:
        c._validate_cds_source("define view entity ZSD001_I_X as select from /scwm/acc_def\n{ key a }\n")
        r4 = "kabul"
    except Exception as exc:                         # noqa: BLE001
        r4 = f"red:{exc}"
    ekle("R4", r4 == "kabul", r4)
    agac = ast.parse((REPO / "scripts" / "sap_adt_lib.py").read_text(encoding="utf-8"))
    dtel = next(n for n in ast.walk(agac) if isinstance(n, ast.FunctionDef) and n.name == "create_dataelement")
    cagri = [n for n in ast.walk(dtel) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "_validate_object_name"]
    ekle("R5", not cagri, len(cagri))


# ── küçükler ───────────────────────────────────────────────────────────────────────────────
def bolum_kucuk(LIB, SCm, A):
    c = object.__new__(LIB.SAPADTClient)
    c.url = "https://h"
    c.timeout_default = 1
    c._get_headers = lambda *a, **k: {}
    url = []

    class Oturum:
        @staticmethod
        def get(u, **k):
            url.append(u)
            return types.SimpleNamespace(status_code=200, text="ok")
    c.session = Oturum
    with sessiz():
        c.table_contents("/NSPC/TAB")
        c.table_contents("ZTAB")
    ekle("K10", url == ["https://h/sap/bc/adt/datapreview/freestyle/%2FNSPC%2FTAB",
                        "https://h/sap/bc/adt/datapreview/freestyle/ZTAB"], url)

    def desenler(pkg):
        cl = sap_client_ornegi(SCm, "k11")
        gor = []
        cl.search_objects = lambda p, **k: (gor.append(p), [])[1]
        with sessiz():
            try:
                cl.list_package_contents(pkg)
            except Exception:
                pass
        return gor
    ekle("K11", desenler("/NSPC/SD001") == ["/NSPC/SD001*"]
         and desenler("ZSD001") == ["ZSD001*", "Z_*", "ZS*"], (desenler("/NSPC/SD001"), desenler("ZSD001")))

    t = (REPO / "scripts" / "create_lock_object.py").read_text(encoding="utf-8")
    ekle("K12", "if not _ad[len(_ns or ''):].startswith('E'):" in t)
    ekle("K14", "# customer_namespaces:" in (REPO / "scripts" / "init_project.py").read_text(encoding="utf-8"))


# ── #9 sızıntı kapısı ──────────────────────────────────────────────────────────────────────
def bolum_z9(G, TG):
    y = "YSD0" + "42_T_FOO"
    ns1 = "/ACM" + "EX/SD04" + "2_T_FOO"
    ns2 = "table /acm" + "ex/sd04" + "2_x"
    metin = f"a {y} b `{ns1}` c {ns2}"
    bul = [b.upper() for b in G.z_obje_sizintilari(metin)]
    beklenen = ["YSD0" + "42", "/ACM" + "EX/SD04" + "2", "/ACM" + "EX/SD04" + "2"]
    ekle("Z9", bul == beklenen and TG.z_obje_sizintilari(metin) == [], (bul,))
    ornek = "YSD001_X /NSPC/SD001_CLC /XNS/SD001 /SCWM/SD001 /programs/zsd000 YOK404 `/NSPC/SD001_I_X`"
    ekle("Z9a", G.z_obje_sizintilari(ornek) == [], G.z_obje_sizintilari(ornek))
    zm = " ".join(["Z" + "SD0" + "42_T_FOO", "zsd001", "ZMOD001", "Z" + "ABC1" + "23", "x_" + "Z" + "SD0" + "43"])
    zy, zt = G.z_obje_sizintilari(zm), TG.z_obje_sizintilari(zm)
    ekle("Z9z", zy == zt and len(zt) == 3, (zy, zt))
    ekle("K7", TG.z_obje_sizintilari(f"{y} {ns1}") == [])
    git = subprocess.run(["git", "-C", str(_GIT_KOK), "ls-files", "-co", "--exclude-standard"],
                         capture_output=True, text=True).stdout.splitlines()
    bulgu, n = [], 0
    for f in git:
        if f.startswith(("core/", ".claude/")):
            continue
        try:
            tx = (_GIT_KOK / f).read_text(encoding="utf-8")
        except Exception:
            continue
        n += 1
        bulgu += [(f, b) for b in G.z_obje_sizintilari(tx)]
    ekle("Z9fp", n > 500 and not bulgu, f"dosya={n} bulgu={bulgu[:5]}")


def bolum_a(A):
    ekle("A1", A.yerel_ad("ZCL_X") == "ZCL_X" and A.yerel_ad("zcl_x") == "zcl_x"
         and A.yerel_ad("/NSPC/CL_X") == "#nspc#cl_x"
         and A.dosya_adindan_ad(A.yerel_ad("/NSPC/CL_X")) == "/NSPC/CL_X")
    hata = 0
    for x in ("/AB/X", "ZA/B", "Z" + chr(92) + "X"):
        try:
            A.yerel_ad(x)
        except ValueError:
            hata += 1
    ekle("A2", hata == 3, hata)
    ekle("A3", A.musteri_govdesi("ZSD001_CLC") == ("Z", "SD001_CLC")
         and A.musteri_govdesi("YSD001") == ("Y", "SD001")
         and A.musteri_govdesi("/NSPC/SD001_CLC") == ("/NSPC/", "SD001_CLC")
         and A.musteri_govdesi("/SCWM/SD001_CLC") is None and A.musteri_govdesi("MARA") is None)
    ekle("A4", A.url_adi("/sap/bc/adt/ddic/tables/%2Fnspc%2Ft1/source/main") == "/NSPC/T1"
         and A.url_adi("") == "")


def main() -> int:
    A = _imp("utils.ad_politikasi")
    A.musteri_namespaceleri = lambda root=None: NS_LISTE      # yapilandirma yolu q393'un konusu
    LIB = _imp("sap_adt_lib")
    SCm = _imp("sap_client")
    BP = _imp("bootstrap_package")
    GF = _imp("gen_field_table")
    PS = _imp("program_to_spec")
    CU = _imp("check_ui_odata_refs")
    CR = _imp("create_rap_service")
    PC = _imp("populate_cds_views")
    G = _imp("genericize_common")
    try:
        TSC = _taban_modul("scripts/sap_client.py", "sap_client_taban")
        TLIB = _taban_modul("scripts/sap_adt_lib.py", "sap_adt_lib_taban")
        TGF = _taban_modul("scripts/gen_field_table.py", "gen_field_table_taban")
        TPS = _taban_modul("scripts/program_to_spec.py", "program_to_spec_taban")
        TCU = _taban_modul("scripts/check_ui_odata_refs.py", "check_ui_odata_refs_taban")
        TPC = _taban_modul("scripts/populate_cds_views.py", "populate_cds_views_taban")
        TG = _taban_modul("scripts/genericize_common.py", "genericize_common_taban")
    except Exception as exc:                           # noqa: BLE001
        print(f"[fixture-hatasi] taban kurulamadi: {exc}")
        return 3
    for fn, a in ((bolum_a, (A,)), (bolum_g1, (SCm, TSC, A)), (bolum_b, (BP, A)),
                  (bolum_g2, (GF, TGF, PS, TPS)), (bolum_g3, (A, CU, TCU, CR)), (bolum_g4, (LIB, TLIB)),
                  (bolum_g5, (PC, TPC)), (bolum_g6, (LIB,)), (bolum_kucuk, (LIB, SCm, A)), (bolum_z9, (G, TG))):
        try:
            fn(*a)
        except Exception as exc:                       # çökme != FAIL: ölçülür
            import traceback
            ekle(f"[BOLUM-COKTU]-{fn.__name__}", False,
                 f"{type(exc).__name__}: {exc} {traceback.format_exc()[-300:]}")
    sonda = Path(_KUM.anchor) / "nst_kalkan_sondasi_yok" / "x.txt"
    try:
        sonda.write_text("x", encoding="utf-8")
        z0 = False
    except PermissionError:
        z0 = not sonda.exists()
    ekle("Z0", z0 and ("write_text", str(sonda)) in KACAK, f"kacak={KACAK[-3:]}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    print(f"[KALKAN] gecici kok disina yazma/silme denemesi: {len(KACAK) - 1} (Z0 sondasi haric)"
          + "".join(f"\n         {i}: {y}" for i, y in KACAK if "nst_kalkan_sondasi_yok" not in y)[:900])
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    os.chdir(BURASI)
    shutil.rmtree(_KUM, ignore_errors=True)
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYONLAR: kip -> (dosya, çapa, yerine, düşmesi İLAN edilen vektör kümesi)
_AP = "scripts/utils/ad_politikasi.py"
_SC = "scripts/sap_client.py"
_LIB = "scripts/sap_adt_lib.py"
_PCV = "scripts/populate_cds_views.py"
_GC = "scripts/genericize_common.py"
BS = chr(92)
MUTASYONLAR = {
    "--mutasyon-indir-yol": (_SC, 'file_path = target_dir / f"{_yerel_ad(object_name)}.abap"',
                             'file_path = target_dir / f"{object_name}.abap"', {"D1"}),
    "--mutasyon-push-yol": (_SC, 'local_file = package_base / subdir / f"{_yerel_ad(object_name)}.abap"   # G1',
                            'local_file = package_base / subdir / f"{object_name}.abap"   # G1', {"D2"}),
    "--mutasyon-sil-yol": (_SC, '            local_file = package_base / subdir / f"{_yerel_ad(object_name)}.abap"\n\n',
                           '            local_file = package_base / subdir / f"{object_name}.abap"\n\n', {"D3"}),
    "--mutasyon-ddic-yol": ("scripts/download_ddic_objects.py", "f\"{yerel_ad(obj['name'].upper())}.xml\"",
                            "f\"{obj['name'].upper()}.xml\"", {"D4"}),
    "--mutasyon-bootstrap-yol": ("scripts/bootstrap_package.py", "    pkg_dir = module_dir / pkg_klasor",
                                 "    pkg_dir = module_dir / pkg_full", {"B1"}),
    "--mutasyon-yerel-ad-ayirac": (_AP, '    if any(ayirac in a for ayirac in ("/", "' + BS + BS + '")):\n        return dosya_adi(a)\n',
                                   "    if False:\n        return dosya_adi(a)\n", {"A1", "A2", "D1", "D2", "D3", "B1", "B2", "F3"}),   # F3: arayüz dosya yolu da yerel_ad ile
    "--mutasyon-gft-ad": ("scripts/gen_field_table.py", "                  + AD_ADAYI + r\")\", text)\n",
                          "                  + r\"" + BS + "w+\" + r\")\", text)\n", {"F1"}),
    # projeksiyon adı ayrı regex'tir (define satırı mutasyonu onu etkilemez) ⇒ kendi vektörü
    "--mutasyon-gft-proj": ("scripts/gen_field_table.py",
                            'pm = re.search(r"as' + BS + 's+projection' + BS + 's+on' + BS + 's+(" + AD_ADAYI + r")"',
                            'pm = re.search(r"as' + BS + 's+projection' + BS + 's+on' + BS + 's+(' + BS + 'w+)"',
                            {"F1", "F3"}),
    "--mutasyon-gft-iface-yol": ("scripts/gen_field_table.py", 'ipath = os.path.join(folder, yerel_ad(proj) + ".cds")',
                                 'ipath = os.path.join(folder, proj + ".cds")', {"F3"}),
    "--mutasyon-pts-y-kova": ("scripts/program_to_spec.py",
                              '    z_tables = [t for t in tables if t.upper()[:1] in ("Z", "Y")]\n',
                              '    z_tables = [t for t in tables if t.upper()[:1] in ("Z", "Y")]\n'
                              '    std_tables += [t for t in tables if t.upper()[:1] == "Y"]\n', {"P1"}),
    "--mutasyon-pts-ns-kova": ("scripts/program_to_spec.py", "    if ns_tables:\n", "    if False:\n", {"P1"}),
    "--mutasyon-pts-harf-siniri": ("scripts/program_to_spec.py", '_ADAY = r"(?:" + AD_ADAYI + r"(?!' + BS + 'w)|' + BS + 'w+)"',
                                  '_ADAY = AD_ADAYI', {"P1z"}),
    "--mutasyon-odata-sap-sabit": (_AP, '        return f"{ODATA_KOK}/{ns[1:-1].lower()}/{s[len(ns):]}"\n',
                                   '        return f"{ODATA_KOK}/sap/{s}"\n', {"O1", "O2", "O4"}),
    "--mutasyon-odata-uri-ns": (_AP, "    return ns + ad if _NS_BICIM.match(ns) else None\n", "    return None\n",
                                {"O1", "O3"}),
    # çağıran katmanı ayrı vektör (yardımcı doğru, çağıran dalı kapalı): model haritası · ana servis
    "--mutasyon-harita-ns": ("scripts/check_ui_odata_refs.py",
                             '                if ns_servis and ns_servis.startswith("/"):\n',
                             "                if False:\n", {"O3"}),
    "--mutasyon-anaservis-musteri": ("scripts/check_ui_odata_refs.py",
                                     '                if aday and aday.startswith("/") and musteri_govdesi(aday) is not None:\n',
                                     "                if aday:\n", {"O3s"}),
    "--mutasyon-anaservis-ns": ("scripts/check_ui_odata_refs.py",
                                "        if not service:   # G3:", "        if False:   # G3:", {"O3"}),
    "--mutasyon-urlad-quote": (_AP, "    return url_parcasindan_ad(ad) if ad else \"\"\n",
                               "    return ad.upper() if ad else \"\"\n", {"U1", "A4"}),
    "--mutasyon-paket-kok-z": (_PCV, "    og = musteri_govdesi(str(package).strip().upper())\n",
                               "    og = musteri_govdesi(str(package).strip().upper())\n"
                               "    og = og if og and og[0] == 'Z' else None\n", {"C1", "C2", "C5"}),
    "--mutasyon-rap-ad-z": (_PCV, "            elif not rap_ve_adi_gecerli(vem.group(1)):\n",
                            "            elif not re.match(r'^Z[A-Z]{2,4}" + BS + "d{3}_(?:I|C|R|E)_[A-Z0-9_]+$', "
                            "vem.group(1).upper()):\n", {"C1", "C2", "C5"}),
    "--mutasyon-stem-upper": (_PCV, "        name = dosya_adindan_ad(f.stem)   # G1",
                              "        name = f.stem.upper()   # G1", {"C5"}),
    "--mutasyon-govde-kayit": (_AP, "    return (ns, a[len(ns):]) if ns in kayitli else None\n",
                               "    return (ns, a[len(ns):])\n", {"A3", "C3", "O3s"}),   # O3s: SAP ns'i müşteri sanılır
    "--mutasyon-ref-musteri": (_LIB, "            if referans and name == name.upper() and _ap.ad_gecerli_mi(name):\n",
                               "            if False:\n", {"R1"}),
    "--mutasyon-ref-gramer": (_LIB, "            if referans and name == name.upper() and _ap.ad_gecerli_mi(name):\n",
                              "            if referans:\n", {"R3"}),
    "--mutasyon-ref-cagri": (_LIB, "'Referenced Structure', referans=True)", "'Referenced Structure')", {"R1"}),
    "--mutasyon-tablo-icerik": (_LIB, "freestyle/{_adt_seg(table_name).upper()}", "freestyle/{table_name.upper()}", {"K10"}),
    "--mutasyon-paket-arama": (_SC, "            if _ad_namespace(str(package_name).upper()):\n", "            if False:\n", {"K11"}),
    "--mutasyon-sizinti-y": (_GC, "    bulunan += [m.group(1) for m in Y_OBJ_PAT.finditer(metin)\n",
                             "    bulunan += [m.group(1) for m in Y_OBJ_PAT.finditer('')\n", {"Z9"}),
    "--mutasyon-sizinti-ns": (_GC, "    bulunan += [m.group(1) + m.group(2) for m in NS_OBJ_PAT.finditer(metin)\n",
                              "    bulunan += [m.group(1) + m.group(2) for m in NS_OBJ_PAT.finditer('')\n", {"Z9"}),
    "--mutasyon-sizinti-allowlist": (_GC, "                if \"Z\" + m.group(2).upper() not in ORNEK_Z]\n",
                                     "                if True]\n", {"Z9a", "Z9fp"}),
}
KIPLER = sorted(MUTASYONLAR)


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="nst_kum_"))
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
        env["NST_GIT_KOK"] = str(_GIT_KOK)
        r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900, cwd=str(kok), env=env)
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        kk = re.search(r"^\[KALKAN\] .*?: (\d+)", r.stdout, re.M)
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}"
              f" · kalkan={kk.group(1) if kk else '?'}")
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

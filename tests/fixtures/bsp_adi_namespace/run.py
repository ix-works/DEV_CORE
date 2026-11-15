#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bsp_adi_namespace — Issue #440: BSP adı + canlı ICF yolu TEK KAYNAKTAN (2026-11-15).

NEDEN
-----
`deploy_ui.bsp_name` yalnız `Z[A-Z0-9_]+` (büyük harf, yorumsuz satır) kabul ediyordu ⇒
`/NSP/APP`, `Y…`, küçük harfli ad ve `ZAD # yorum` sessizce "" dönüyordu; dört tüketici
(deploy_ui · fetch_ui_source · verify_ui_static_assets · hooks/_pbe_ui) BSP'yi çözemiyordu.
Canlı ICF yolu `/sap/bc/ui5_ui5/sap/<bsp>/` iki yerde sabit yazılıydı (deploy_ui canlı preload,
verify_ui_static_assets statik varlık). FIX: ad kararı `utils.ad_politikasi.musteri_adi_mi`
(ADR 0005-A tek kaynak, kayıtsız namespace RED) + `deploy_ui.bsp_icf_yolu` tek URL yardımcısı.

⚠ KAPSAM BEYANI: `/NSP/APP` → `/sap/bc/ui5_ui5/<ns>/<app>/` yolu Issue sahibinin ortamında
ölçüldü; bu korpus yalnız URL'in NASIL KURULDUĞUNU ölçer (ağ sahte), SAP'nin o yolu servis
ettiğini ÖLÇMEZ. Gerçek deploy YOK.

ÜÇ BAĞLAM (F3)
  (1) bilinen-BOZUK : `--mutasyon-*` (fix bellekte geri alınır)
  (2) bilinen-TEMİZ : bugünkü kod — Z yolu regresyon vektörleri (A1/B1/C1/C3) dahil
  (3) görev-DIŞI    : `_pbe_ui.sinifla` (PBE kancası, başka giriş noktası) + namespace'siz
                      proje (yapılandırma yok → yalnız Z/Y, fail-closed)

KOŞUM : python tests/fixtures/bsp_adi_namespace/run.py [--mutasyon-<kip>]
ÇIKIŞ : 0 hepsi beklendiği gibi · 1 sapma (mutasyonda = DÜŞTÜ) · 3 KURULAMADI (çapa tutmadı)
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
SCRIPTS = KOK / "scripts"
DUI = SCRIPTS / "deploy_ui.py"
VUS = SCRIPTS / "verify_ui_static_assets.py"

# kip -> (dosya, eski, yeni) — bellekte uygulanır; gerçek kaynak DEĞİŞMEZ
MUTASYONLAR = {
    "--mutasyon-eski-z-deseni": (DUI, "        if musteri_adi_mi(ad):\n",
                                 '        if re.match(r"Z[A-Z0-9_]+\\Z", ad):  # MUTASYON\n'),
    "--mutasyon-kayitsiz-ns-kabul": (DUI, "        if musteri_adi_mi(ad):\n",
                                     "        if musteri_adi_mi(ad) or ad_namespace(ad):  # MUTASYON\n"),
    "--mutasyon-app-oncelik-yok": (DUI, '    return (app_icinde or herhangi or [""])[0]',
                                   '    return ((herhangi + app_icinde) or [""])[0]  # MUTASYON'),
    "--mutasyon-yorum-ayiklanmaz": (DUI, '    v = re.split(r"\\s#", ham, maxsplit=1)[0].strip()',
                                    "    v = ham.strip()  # MUTASYON"),
    "--mutasyon-buyuk-harf-yok": (DUI, "        ad = _yaml_skaler(m.group(1)).upper()",
                                  "        ad = _yaml_skaler(m.group(1))  # MUTASYON"),
    "--mutasyon-icf-ns-dali-yok": (DUI, "    if ns:\n        return f\"/sap/bc/ui5_ui5/{ns",
                                   "    if False:\n        return f\"/sap/bc/ui5_ui5/{ns"),
    "--mutasyon-icf-bicimsiz-sap-dugumune": (DUI, '    if "/" in bsp:\n',
                                             "    if False:  # MUTASYON\n"),
    "--mutasyon-preload-sabit-yol":(DUI, 'url = f"{base_url}{bsp_icf_yolu(bsp)}{PRELOAD}',
                                     'url = f"{base_url}/sap/bc/ui5_ui5/sap/{bsp.lower()}/{PRELOAD}'),
    "--mutasyon-statik-sabit-yol": (VUS, 'url = (f"{base_url}{bsp_icf_yolu(bsp)}{rel_url}"',
                                    'url = (f"{base_url}/sap/bc/ui5_ui5/sap/{bsp.lower()}/{rel_url}"'),
}

ARG = [a for a in sys.argv[1:] if a.startswith("--mutasyon")]
if any(a not in MUTASYONLAR for a in ARG):
    print(f"[KULLANIM] bilinmeyen kip: {ARG} -> gecerli: {', '.join(sorted(MUTASYONLAR))}")
    raise SystemExit(3)
KIP = ARG[0] if ARG else None

# ── kum: sahte bağlantı + project.yaml (namespace /NSP/) ─────────────────────────────────
KUM = Path(tempfile.mkdtemp(prefix="bsp_ns_"))
(KUM / ".conn_adt").write_bytes(b"ADT_SAP_URL=https://sahte.invalid\nADT_SAP_CLIENT=000\n")
(KUM / "project.yaml").write_text("sap_profile: s4_private\nsource_root: SOURCE_CODES\n"
                                  "customer_namespaces: [\"/NSP/\"]\n", encoding="utf-8")
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)   # deploy_ui REPO'yu import anında okur
os.chdir(KUM)
sys.path.insert(0, str(SCRIPTS))


def _yukle(ad: str, yol: Path):
    """Modülü (gerekirse mutasyonlu) yükle ve sys.modules'a koy — tüketiciler ONU import eder."""
    kaynak = yol.read_text(encoding="utf-8")
    if KIP and MUTASYONLAR[KIP][0] == yol:
        eski, yeni = MUTASYONLAR[KIP][1], MUTASYONLAR[KIP][2]
        if kaynak.count(eski) != 1:
            print(f"[KURULAMADI] {KIP}: çapa {kaynak.count(eski)} kez geçiyor (1 bekleniyordu)")
            raise SystemExit(3)
        kaynak = kaynak.replace(eski, yeni)
    m = types.ModuleType(ad)
    m.__file__ = str(yol)
    sys.modules[ad] = m
    try:
        exec(compile(kaynak, str(yol), "exec"), m.__dict__)
    except SyntaxError as exc:
        print(f"[KURULAMADI] {KIP}: mutant derlenmedi: {exc}")
        raise SystemExit(3)
    return m


import sap_adt_lib as LIB  # noqa: E402 — namespace kökü = ÇÖZÜLEN bağlantının dizini
LIB._explicit_working_dir = None
LIB.conn_path = KUM / ".conn_adt"   # ortamın kendi .conn_adt'si ölçüme SIZMASIN

D = _yukle("deploy_ui", DUI)
V = _yukle("verify_ui_static_assets", VUS)
import fetch_ui_source as F  # noqa: E402 — sys.modules'taki (mutasyonlu) deploy_ui'ı bağlar
sys.path.insert(0, str(SCRIPTS / "hooks"))
import _pbe_ui as P  # noqa: E402

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def yaml_app(app_adi: str, metadata: str = "com.example.alan.uygulama", app_blok: bool = True) -> Path:
    d = Path(tempfile.mkdtemp(prefix="app_", dir=KUM))
    govde = (f"specVersion: \"4.0\"\nmetadata:\n  name: {metadata}\ntype: application\n"
             "builder:\n  customTasks:\n    - name: deploy-to-abap\n      afterTask: generateCachebusterInfo\n"
             "      configuration:\n        target:\n          url: https://sahte.invalid\n")
    govde += (f"        app:\n          name: {app_adi}\n          package: ZPAKET\n" if app_blok
              else f"name: {app_adi}\n")
    (d / "ui5-deploy.yaml").write_text(govde, encoding="utf-8")
    return d


# ══ A — bsp_name ═════════════════════════════════════════════════════════════════════
VAKALAR = [
    ("A1 Z (kanonik şablon biçimi) — REGRESYON: aynen", "ZSD001_APP", {}, "ZSD001_APP"),
    ("A2 Y adı", "YSD001_APP", {}, "YSD001_APP"),
    ("A3 kayıtlı namespace /NSP/APP", "/NSP/APP", {}, "/NSP/APP"),
    ("A4 KAYITSIZ namespace /ABC/APP -> '' (ADR 0005-A, fail-closed)", "/ABC/APP", {}, ""),
    ("A5 SAP namespace /UI2/USHELL -> ''", "/UI2/USHELL", {}, ""),
    ("A6 standart ad (Z/Y değil) -> ''", "SAPUI5_APP", {}, ""),
    ("A7 küçük harf zsd001_app -> ZSD001_APP", "zsd001_app", {}, "ZSD001_APP"),
    ("A8 satır sonu yorum `ZSD001_APP # yorum`", "ZSD001_APP # yorum", {}, "ZSD001_APP"),
    ("A9 tırnaklı \"/NSP/APP\"", "\"/NSP/APP\"", {}, "/NSP/APP"),
    ("A10 metadata.name tek parçalı `zfoo` + app.name -> app.name ÖNCELİKLİ", "ZSD001_APP",
     {"metadata": "zfoo"}, "ZSD001_APP"),
    ("A11 app: bloğu YOK -> ilk müşteri adı (eski kural)", "ZSD001_APP", {"app_blok": False},
     "ZSD001_APP"),
]
for ad, deger, kw, beklenen in VAKALAR:
    sonuc = D.bsp_name(yaml_app(deger, **kw))
    kontrol(ad, sonuc == beklenen, f"bekl={beklenen!r} gelen={sonuc!r}")
kontrol("A12 ui5-deploy.yaml yok -> ''", D.bsp_name(Path(tempfile.mkdtemp(dir=KUM))) == "")

# ══ B — bsp_icf_yolu ═════════════════════════════════════════════════════════════════
for ad, bsp, beklenen in [
        ("B1 Z — REGRESYON: /sap/bc/ui5_ui5/sap/<bsp>/", "ZSD001_APP", "/sap/bc/ui5_ui5/sap/zsd001_app/"),
        ("B2 /NSP/APP -> /sap/bc/ui5_ui5/nsp/app/", "/NSP/APP", "/sap/bc/ui5_ui5/nsp/app/"),
        ("B3 Y -> sap düğümü", "YSD001_APP", "/sap/bc/ui5_ui5/sap/ysd001_app/"),
        ("B4 biçimsiz /NS/APP (2 harfli ns) -> ValueError, sahte `sap//ns/app/` yolu KURULMAZ",
         "/NS/APP", ValueError)]:
    try:
        gelen = D.bsp_icf_yolu(bsp)
    except Exception as exc:  # noqa: BLE001
        gelen = type(exc)
    kontrol(ad, gelen == beklenen, f"gelen={gelen!r}")

# ══ C — iki URL kurucusu yardımcıyı KULLANIYOR (ağ sahte; istenen URL yakalanır) ═════════
YAKALANAN: list[str] = []


class _Yanit:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b"x"


def _sahte_urlopen(req, context=None, timeout=None):
    YAKALANAN.append(req.full_url)
    return _Yanit()


D.urllib.request.urlopen = _sahte_urlopen
V.urllib.request.urlopen = _sahte_urlopen
BASE = "https://sahte.invalid"
for ad, cagri, onek in [
        ("C1 canlı preload Z — REGRESYON", lambda: D.fetch_live_preload(BASE, "u", "p", "100", "ZSD001_APP"),
         f"{BASE}/sap/bc/ui5_ui5/sap/zsd001_app/Component-preload.js?sap-client=100&cb="),
        ("C2 canlı preload /NSP/APP", lambda: D.fetch_live_preload(BASE, "u", "p", "100", "/NSP/APP"),
         f"{BASE}/sap/bc/ui5_ui5/nsp/app/Component-preload.js?sap-client=100&cb="),
        ("C3 statik varlık Z — REGRESYON", lambda: V.fetch(BASE, "u", "p", "100", "ZSD001_APP", "help/a.html"),
         f"{BASE}/sap/bc/ui5_ui5/sap/zsd001_app/help/a.html?sap-client=100&cb="),
        ("C4 statik varlık /NSP/APP", lambda: V.fetch(BASE, "u", "p", "100", "/NSP/APP", "help/a.html"),
         f"{BASE}/sap/bc/ui5_ui5/nsp/app/help/a.html?sap-client=100&cb=")]:
    YAKALANAN.clear()
    try:
        cagri()
        url = YAKALANAN[-1] if YAKALANAN else ""
    except Exception as exc:  # noqa: BLE001
        url = f"<{type(exc).__name__}: {exc}>"
    kontrol(ad, url.startswith(onek), f"url={url!r}")

# ══ T — dört tüketici AYNI çözümü kullanıyor (kablolama) ════════════════════════════
kontrol("T1 verify_ui_static_assets.bsp_name IS deploy_ui.bsp_name", V.bsp_name is D.bsp_name)
kontrol("T2 verify_ui_static_assets.bsp_icf_yolu IS deploy_ui.bsp_icf_yolu",
        getattr(V, "bsp_icf_yolu", None) is D.bsp_icf_yolu)
kontrol("T3 fetch_ui_source.bsp_name IS deploy_ui.bsp_name", F.bsp_name is D.bsp_name)

# 3. BAĞLAM — PBE kancası (_pbe_ui.sinifla, deploy_ui'ı kendi içinde import eder)
uygulama = KUM / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui"
for ad, app_adi, beklenen in [("T4 _pbe_ui.sinifla /NSP/APP -> nesne /NSP/APP", "/NSP/APP", "/NSP/APP"),
                              ("T5 _pbe_ui.sinifla Z — REGRESYON", "ZSD001_APP", "ZSD001_APP"),
                              ("T6 _pbe_ui.sinifla kayıtsız /ABC/APP -> yer tutucu", "/ABC/APP",
                               P.BSP_YER_TUTUCU)]:
    a = uygulama / f"app_{len(SONUC)}"
    (a / "webapp").mkdir(parents=True)
    (a / "webapp" / "Component.js").write_text("x", encoding="utf-8")
    (a / "ui5-deploy.yaml").write_text((yaml_app(app_adi) / "ui5-deploy.yaml").read_text(encoding="utf-8"),
                                       encoding="utf-8")
    s = P.sinifla(str(a / "webapp" / "Component.js"), str(KUM))
    kontrol(ad, bool(s) and s.get("nesne") == beklenen, f"sonuc={s and s.get('nesne')!r}")

# 3. BAĞLAM — namespace YAPILANDIRMASIZ proje: /NSP/ reddedilir, Z/Y aynen
(KUM / "project.yaml").write_text("sap_profile: s4_private\n", encoding="utf-8")
kontrol("N1 yapılandırmasız projede /NSP/APP -> '' (fail-closed)", D.bsp_name(yaml_app("/NSP/APP")) == "")
kontrol("N2 yapılandırmasız projede Z aynen", D.bsp_name(yaml_app("ZSD001_APP")) == "ZSD001_APP")

gecen = sum(1 for _a, ok, _d in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f"  ({detay})" if detay and not ok else ""))
print(f"\nbsp_adi_namespace: {gecen}/{len(SONUC)}" + (f"   (MUTASYON {KIP})" if KIP else ""))
print("KAPSAM: URL kuruluşu + ad çözümü ölçüldü; SAP'nin /NSP/ ICF yolunu servis etmesi ÖLÇÜLMEDİ (ağ sahte).")
os.chdir(KOK)
shutil.rmtree(KUM, ignore_errors=True)   # yalnız bu koşumun kendi geçici dizini
raise SystemExit(0 if gecen == len(SONUC) else 1)

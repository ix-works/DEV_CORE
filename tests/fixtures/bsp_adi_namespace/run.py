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

PR #445 kapısı (F1): `app:` bloğu GÖRÜLDÜYSE sonuç yalnız o bloktan — reddedilen app.name
blok dışı `metadata.name`e düşmez (A13-A16; mutasyon `--mutasyon-app-reddi-dusuyor`).

PR #445 3. kapı (lider kararı): satır regex'i KALDIRILDI — ad GERÇEK YAML ayrıştırıcıyla,
`fiori deploy`un okuduğu yoldan (İLK `deploy-to-abap` görevinin `configuration.app.name`).
Birincil: node + `yaml` paketi (fiori'nin kütüphane ailesi) · yedek: PyYAML (yinelenen anahtar ve
`<<` RED) · ikisi yoksa / belge hatalıysa "". `metadata.name`'e düşüş YOK (A11).
G01–G74 = kapının 74 probe girdisi (`g_vakalari.py`, AYNEN); beklenen değer, fiori'nin kendi
okuma kodunun (`parseDocument().toJSON()` + `find`) bu girdilerdeki sonucunun politikadan geçmiş
hâlidir (belge hatası ⇒ "") — ölçülüp SABİTLENDİ (BEKLENEN_DOLU). Her eksen (node · PyYAML) AYRI
koşulur. Node ekseni `yaml` paketi gerektirir: `BSP_FIXTURE_YAML_PAKETI=<.../node_modules/yaml>`
ya da `npm root -g` altında; bulunamazsa eksen ÖLÇÜLEMEDİ yazılır (CI'da beklenen hâl).

PR #445 4. kapı F1: `--all` listesi (L1–L4 + kâhin K1–K4) iki aracın GERÇEK main()'iyle — yalnız
ui5-deploy.yaml'sız dizin atlanır; yaml VAR ama ad çözülemeyen app FAIL + RC 1 (`--mutasyon-all-*`).

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
    "--mutasyon-eski-z-deseni": (DUI, "        if not musteri_adi_mi(bsp):\n",
                                 '        if not re.match(r"Z[A-Z0-9_]+\\Z", bsp):  # MUTASYON\n'),
    "--mutasyon-kayitsiz-ns-kabul": (DUI, "        if not musteri_adi_mi(bsp):\n",
                                     "        if not (musteri_adi_mi(bsp) or ad_namespace(bsp)):  # MUTASYON\n"),
    "--mutasyon-buyuk-harf-yok": (DUI, "        bsp = deger.upper()\n", "        bsp = deger  # MUTASYON\n"),
    # PR #445 3. kapı: ayrıştırıcı yerine satır regex'i (son `name:` satırı)
    "--mutasyon-ayristirici-yerine-regex": (
        DUI, 'AYRISTIRICILAR = (("node-yaml", _node_ile), ("PyYAML", _pyyaml_ile))',
        'AYRISTIRICILAR = (("regex", lambda y: ("OK", (re.findall(r"(?m)^\\s*name:\\s*(\\S+)", '
        'y.read_text(encoding="utf-8")) or [None])[-1])),)  # MUTASYON'),
    "--mutasyon-yinelenen-anahtar-kabul-node": (DUI, "  if (d.errors && d.errors.length) {",
                                                "  if (false) {  // MUTASYON"),
    "--mutasyon-yinelenen-anahtar-kabul-pyyaml": (DUI, "            if anahtar in gorulen:\n",
                                                  "            if False:  # MUTASYON\n"),
    "--mutasyon-gorev-suzgeci-yok-node": (DUI, "e => e && e.name === 'deploy-to-abap'",
                                          "e => e && e.configuration && e.configuration.app"),
    "--mutasyon-gorev-suzgeci-yok-pyyaml": (DUI, 'e.get("name") == _DEPLOY_GOREVI), None)',
                                            '"configuration" in e), None)  # MUTASYON'),
    "--mutasyon-metadata-dususu": (
        DUI, '        if deger is None:\n            return "", f"{_DEPLOY_GOREVI}',
        '        if deger is None:\n'
        '            _m = re.search(r"(?m)^  name:\\s*(\\S+)", y.read_text(encoding="utf-8"))\n'
        '            deger = _m.group(1) if _m else None  # MUTASYON metadata.name dususu\n'
        '        if deger is None:\n            return "", f"{_DEPLOY_GOREVI}'),
    "--mutasyon-ayristiramadi-sessiz": (DUI, '        print(f"[UYARI] BSP adı ayrıştırılamadı:',
                                        '        (lambda *a, **k: None)(f"[UYARI] BSP adı ayrıştırılamadı:'),  # MUTASYON
    "--mutasyon-icf-ns-dali-yok": (DUI, "    if ns:\n        return f\"/sap/bc/ui5_ui5/{ns",
                                   "    if False:\n        return f\"/sap/bc/ui5_ui5/{ns"),
    "--mutasyon-icf-bicimsiz-sap-dugumune": (DUI, '    if "/" in bsp:\n',
                                             "    if False:  # MUTASYON\n"),
    # 2026-11-27: preload dosya adı parametreli (`dosya`: uygulama Component-preload · library library-preload)
    "--mutasyon-preload-sabit-yol":(DUI, 'url = f"{base_url}{bsp_icf_yolu(bsp)}{dosya}',
                                     'url = f"{base_url}/sap/bc/ui5_ui5/sap/{bsp.lower()}/{dosya}'),
    "--mutasyon-statik-sabit-yol": (VUS, 'url = (f"{base_url}{bsp_icf_yolu(bsp)}{rel_url}"',
                                    'url = (f"{base_url}/sap/bc/ui5_ui5/sap/{bsp.lower()}/{rel_url}"'),
    # PR #445 4. kapı F1: `--all` listesi (L bölümü) — her yeni dal için bir kip
    "--mutasyon-all-eski-suzgec-dui": (
        DUI, "        apps, atlanan, cozulemeyen_sonuc = all_kipi(ui_root)\n",
        "        apps = sorted(d.name for d in ui_root.iterdir() if d.is_dir() and d.name != \"node_modules\" "
        "and bsp_name(d))  # MUTASYON\n"),
    "--mutasyon-all-eski-suzgec-vus": (
        VUS, "        apps, atlanan, cozulemeyen_sonuc = all_kipi(ui_root)\n",
        "        apps = sorted(d.name for d in ui_root.iterdir() if d.is_dir() and d.name != \"node_modules\" "
        "and bsp_name(d))  # MUTASYON\n"),
    "--mutasyon-all-yamlsiz-da-fail": (DUI, "        elif neden == NEDEN_YAML_YOK:\n",
                                       "        elif False:  # MUTASYON\n"),
    "--mutasyon-all-cozulemeyen-atlanir": (DUI, "            cozulemeyen.append((d.name, neden))\n",
                                           "            atlanan.append(d.name)  # MUTASYON\n"),
    "--mutasyon-all-ozet-kosmadi-yok": (DUI, "                         if cozulemeyen_n else []))\n",
                                        "                         if False else []))  # MUTASYON\n"),
    "--mutasyon-all-atlanan-notu-yok": (
        DUI, "    return f\" · {len(atlanan)} dizin ui5-deploy.yaml'sız ATLANDI\" if tum_kip else \"\"\n",
        "    return \"\"  # MUTASYON\n"),
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


def _yaml_paketi_bul():
    """Node ekseni için `yaml` paketi: env → `npm root -g`. Yoksa None (eksen ÖLÇÜLEMEDİ)."""
    import subprocess as _sp
    aday = os.environ.get("BSP_FIXTURE_YAML_PAKETI")
    if aday and (Path(aday) / "package.json").exists():
        return Path(aday)
    try:
        kok = _sp.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=60,
                      shell=(os.name == "nt")).stdout.strip()
    except (OSError, _sp.SubprocessError):
        return None
    aday = Path(kok) / "yaml" if kok else None
    return aday if aday and (aday / "package.json").exists() else None


YAML_PAKETI = _yaml_paketi_bul()
if YAML_PAKETI:   # KUM altındaki her app dizini `yaml`ı buradan çözer (Node üst dizinlere bakar)
    shutil.copytree(YAML_PAKETI, KUM / "node_modules" / "yaml")
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
    ("A11 deploy-to-abap'ta app YOK (üst düzey `name:` var) -> '' — DÜŞÜŞ YOK (3. kapı)",
     "ZSD001_APP", {"app_blok": False}, ""),
    # PR #445 kapısı F1: app: bloğu VARKEN reddedilen app.name blok DIŞINA düşmez
    ("A13 kayıtsız /ABC/APP + metadata `zfoo` -> '' (ZFOO'ya DÜŞMEZ)", "/ABC/APP",
     {"metadata": "zfoo"}, ""),
    ("A14 standart SAPUI5_STD + metadata `zfoo` -> ''", "SAPUI5_STD", {"metadata": "zfoo"}, ""),
    ("A15 Y-olmayan SAPAPP + metadata `yapp` -> ''", "SAPAPP", {"metadata": "yapp"}, ""),
    ("A16 ESKİ kardeş: standart SAPUI5_STD + metadata `ZFOO` (eski regex 'ZFOO' verirdi) -> ''",
     "SAPUI5_STD", {"metadata": "ZFOO"}, ""),
]
for ad, deger, kw, beklenen in VAKALAR:
    sonuc = D.bsp_name(yaml_app(deger, **kw))
    kontrol(ad, sonuc == beklenen, f"bekl={beklenen!r} gelen={sonuc!r}")


def yaml_ham(app_satirlari: str, metadata: str = "zfoo") -> Path:
    """`app` anahtarını VERİLEN biçimde yazar (akış / tırnaklı); metadata.name tek parçalı."""
    d = Path(tempfile.mkdtemp(prefix="app_", dir=KUM))
    govde = (f"specVersion: \"4.0\"\nmetadata:\n  name: {metadata}\ntype: application\n"
             "builder:\n  customTasks:\n    - name: deploy-to-abap\n      configuration:\n"
             "        target:\n          url: https://sahte.invalid\n" + app_satirlari)
    (d / "ui5-deploy.yaml").write_text(govde, encoding="utf-8")
    return d


# PR #445 re-gate F-YENİ-1: `app` anahtarı HER biçimde görüldü sayılır (kapı probu P8-P11)
for ad, app_satirlari, beklenen in [
        ("A17 AKIŞ `app: {name: /ABC/APP}` (kayıtsız) + metadata zfoo -> ''",
         "        app: {name: /ABC/APP, package: ZPAKET}\n", ""),
        ("A18 AKIŞ standart `SAPSTD` + metadata zfoo -> ''",
         "        app: {name: SAPSTD}\n", ""),
        ("A19 AKIŞ geçerli `ZAPP` -> ZAPP (pozitif kontrol)",
         "        app: {name: ZAPP, package: ZPAKET}  # yorum\n", "ZAPP"),
        ("A20 TIRNAKLI `\"app\":` blok + /ABC/APP + metadata zfoo -> ''",
         "        \"app\":\n          name: /ABC/APP\n", ""),
        ("A21 TIRNAKLI `'app':` blok + ZAPP -> ZAPP",
         "        'app':\n          name: ZAPP\n", "ZAPP"),
        ("A22 TIRNAKLI anahtar + AKIŞ `\"app\": {\"name\": \"/NSP/APP\"}` -> /NSP/APP",
         "        \"app\": {\"name\": \"/NSP/APP\"}\n", "/NSP/APP"),
        ("A23 ÇOK SATIRLI akış (geçerli YAML) -> ZAPP (gerçek ayrıştırıcı; fiori de ZAPP okur)",
         "        app: {\n          name: ZAPP }\n", "ZAPP"),
        ("A24 app bloğunda TIRNAKLI `\"name\":` ZSD001_APP -> ZSD001_APP (kapı P11)",
         "        app:\n          \"name\": ZSD001_APP\n", "ZSD001_APP")]:
    sonuc = D.bsp_name(yaml_ham(app_satirlari))
    kontrol(ad, sonuc == beklenen, f"bekl={beklenen!r} gelen={sonuc!r}")
kontrol("A12 ui5-deploy.yaml yok -> ''", D.bsp_name(Path(tempfile.mkdtemp(dir=KUM))) == "")

# ══ G — kapının 74 probe girdisi, HER ayrıştırıcı ekseni AYRI (PR #445 3. kapı) ══════════
# Beklenen: fiori'nin okuma kodunun (yaml 2.8.3: parseDocument().toJSON() + find deploy-to-abap)
# bu girdilerdeki app.name'i, politikadan geçmiş hâli; belge hatası (DUPLICATE_KEY vb.) ⇒ "".
# Ölçüm 2026-11-15 (node yaml 2.8.3 + PyYAML 6.0.3): 74/74 iki eksende de aynı → SABİTLENDİ.
BEKLENEN_DOLU = {g: "ZAPP" for g in (
    "G01 G02 G03 G06 G07 G08 G09 G11 G12 G14 G15 G26 G30 G31 G35 G40 G41 G48 G53 G54 G55 G57 "
    "G59 G67 G68 G69 G71").split()}
BEKLENEN_DOLU.update({"G38": "/NSP/APP", "G39": "/NSP/APP"})
G_HEAD = ('specVersion: "4.0"\nmetadata:\n  name: {meta}\ntype: application\nbuilder:\n  customTasks:\n'
          '    - name: deploy-to-abap\n      configuration:\n        target:\n          url: https://sahte.invalid\n')
G_DIZINLERI: list[tuple[str, Path]] = []


def _g_case(ad, body=None, meta="zfoo", full=None, raw=None):
    d = Path(tempfile.mkdtemp(prefix="g_", dir=KUM))
    if raw is not None:
        (d / "ui5-deploy.yaml").write_bytes(raw)
    else:
        metin = full if full is not None else G_HEAD.format(meta=meta) + body
        (d / "ui5-deploy.yaml").write_bytes(metin.encode("utf-8"))
    G_DIZINLERI.append((ad, d))


exec(compile((Path(__file__).parent / "g_vakalari.py").read_text(encoding="utf-8"), "g_vakalari.py", "exec"),
     {"case": _g_case, "A": "        ", "HEAD": G_HEAD})
kontrol("G00 kapı korpusu TAM: 74 vaka yüklendi", len(G_DIZINLERI) == 74, f"n={len(G_DIZINLERI)}")
import contextlib  # noqa: E402
import io  # noqa: E402
_ASIL = D.AYRISTIRICILAR
EKSENLER = []
for eksen_adi, fn in _ASIL:
    D.AYRISTIRICILAR = ((eksen_adi, fn),)
    sonda = fn(G_DIZINLERI[0][1] / "ui5-deploy.yaml")
    if sonda is None:
        print(f"  [ÖLÇÜLEMEDİ] G ekseni {eksen_adi}: ayrıştırıcı bu ortamda YOK "
              + ("(node `yaml` paketi bulunamadı — BSP_FIXTURE_YAML_PAKETI)" if eksen_adi == "node-yaml"
                 else "(PyYAML kurulu değil)"))
        continue
    EKSENLER.append(eksen_adi)
    yanlis = []
    for ad, d in G_DIZINLERI:
        with contextlib.redirect_stderr(io.StringIO()):   # [UYARI] satırları P1'de ayrıca ölçülür
            gelen = D.bsp_name(d)
        bek = BEKLENEN_DOLU.get(ad.split()[0], "")
        if gelen != bek:
            yanlis.append(f"{ad.split()[0]}:bekl={bek!r},gelen={gelen!r}")
    kontrol(f"G[{eksen_adi}] 74 kapı vakası fiori-politika beklentisiyle BİREBİR", not yanlis,
            " ".join(yanlis[:12]))
D.AYRISTIRICILAR = _ASIL
kontrol("G-EKSEN en az bir ayrıştırıcı ekseni ÖLÇÜLDÜ (ikisi de yoksa fixture kör)", bool(EKSENLER),
        f"eksenler={EKSENLER}")
if KIP and KIP.endswith("-node") and "node-yaml" not in EKSENLER:
    print(f"[KURULAMADI] {KIP}: node ekseni bu ortamda yok — mutasyon ölçülemez (KAÇTI DEĞİLDİR)")
    raise SystemExit(3)
if KIP and KIP.endswith("-pyyaml") and "PyYAML" not in EKSENLER:
    print(f"[KURULAMADI] {KIP}: PyYAML ekseni bu ortamda yok — mutasyon ölçülemez (KAÇTI DEĞİLDİR)")
    raise SystemExit(3)

# P — ayrıştırıcı HİÇ yoksa: "" + stderr [UYARI] (fail-closed, sessiz değil)
D.AYRISTIRICILAR = ()
_hata = io.StringIO()
with contextlib.redirect_stderr(_hata):
    _p1 = D.bsp_name(yaml_app("ZSD001_APP"))
D.AYRISTIRICILAR = _ASIL
kontrol("P1 ayrıştırıcı YOK -> '' + stderr `[UYARI] BSP adı ayrıştırılamadı` (sessiz değil)",
        _p1 == "" and "[UYARI] BSP adı ayrıştırılamadı" in _hata.getvalue(),
        f"gelen={_p1!r} stderr={_hata.getvalue()[:120]!r}")
_hata = io.StringIO()
with contextlib.redirect_stderr(_hata):
    _p2 = D.bsp_name(yaml_app("SAPUI5_STD"))
kontrol("P2 politika reddi (ayrıştırma BAŞARILI) -> '' ve [UYARI] YOK (teşhis karışmaz)",
        _p2 == "" and "[UYARI]" not in _hata.getvalue(), f"stderr={_hata.getvalue()[:120]!r}")

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

# ══ L — `--all` listesi, İKİ aracın GERÇEK main()'i (PR #445 4. kapı F1) ══════════════════
# Kusur: liste `... and bsp_name(d)` süzgeciyle kuruluyordu; `''` artık "belge hatası / ayrıştırıcı
# yok / politika reddi" de demek olunca app sessizce düşüyor, `[OK] 0 app doğrulandı` + RC 0
# basılıyordu (kontrol grubu 5fd32f0: aynı girdide RC 1). Kural (lider kararı): YALNIZ
# ui5-deploy.yaml'sız dizin atlanır; diğer her neden app başına FAIL satırı + RC 1.
# Kâhin (K*): verify_ui_static_assets `--apps <yaml'lı dizinlerin hepsi>` — liste yardımcısından
# GEÇMEYEN yol (check_app → bsp_name) — `--all` ile aynı RC ve aynı FAIL kümesini vermeli.
# deploy_one SAHTE (build/deploy/ağ YOK; koşan app'ler kaydedilir); check_app GERÇEK (help yok → atlandı).
import re  # noqa: E402

YAML_GECERLI = (yaml_app("ZSD001_APP") / "ui5-deploy.yaml").read_text(encoding="utf-8")
YAML_STANDART = (yaml_app("SAPUI5_STD") / "ui5-deploy.yaml").read_text(encoding="utf-8")
YAML_ADSIZ = (yaml_app("ZSD001_APP", app_blok=False) / "ui5-deploy.yaml").read_text(encoding="utf-8")
YAML_YINELENEN = G_HEAD.format(meta="zfoo") + "        app:\n          name: SAPSTD\n        app:\n          name: ZAPP\n"
KOSAN: list[str] = []


def _ui_kok(ad: str, uygulamalar: dict) -> Path:
    kok = KUM / f"ui_{ad}"
    for app, govde in uygulamalar.items():
        (kok / app).mkdir(parents=True)
        if govde is not None:
            (kok / app / "ui5-deploy.yaml").write_text(govde, encoding="utf-8")
    return kok


def _sahte_deploy_one(app, ui_root, conn, env, dry, verify_only):
    KOSAN.append(app)
    return (app, True, "sahte deploy_one (fixture): build/deploy/canlı YOK")


def _main(modul, argv: list) -> tuple:
    KOSAN.clear()
    out, err, eski = io.StringIO(), io.StringIO(), sys.argv
    sys.argv = argv
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = modul.main()
            except SystemExit as exc:
                rc = exc.code
    finally:
        sys.argv = eski
    return rc, out.getvalue(), err.getvalue(), list(KOSAN)


def _fail_kumesi(cikti: str) -> set:
    return set(re.findall(r"(?m)^\s+\[FAIL\] (\S+)  —", cikti))


_ASIL_DEPLOY_ONE = D.deploy_one
D.deploy_one = _sahte_deploy_one
ATL1 = "1 dizin ui5-deploy.yaml'sız ATLANDI"

# L1 — geçerli app + ui5-deploy.yaml'sız dizin: atlanan FAIL DEĞİLDİR (FP çapası)
kok1 = _ui_kok("L1", {"zapp": YAML_GECERLI, "notlar": None})
rc, o, e, k = _main(D, ["deploy_ui.py", "--all", "--verify-only", "--ui-root", str(kok1)])
kontrol("L1-D geçerli + yaml'sız dizin → RC 0, yalnız zapp koştu, özet satırında atlanan sayısı",
        rc == 0 and k == ["zapp"] and ATL1 in o and "[FAIL]" not in o + e, f"rc={rc} kosan={k} out={o[-200:]!r}")
rc, o, e, _k = _main(V, ["v.py", "--all", "--ui-root", str(kok1)])
kontrol("L1-V geçerli + yaml'sız dizin → RC 0, [OK] 1 app + atlanan sayısı",
        rc == 0 and "[OK] 1 app" in o and ATL1 in o, f"rc={rc} out={o[-200:]!r}")
rc_k, o_k, _e, _k = _main(V, ["v.py", "--apps", "zapp", "--ui-root", str(kok1)])
kontrol("K1 kâhin: V --apps zapp ile aynı RC (0)", rc_k == rc == 0, f"--apps rc={rc_k} --all rc={rc}")

# L2 — AYRIŞTIRICISIZ ortam + geçerli app (kapının ölçtüğü sessiz regresyon)
kok2 = _ui_kok("L2", {"zapp": YAML_GECERLI})
D.AYRISTIRICILAR = ()
for kip_adi, ek in (("verify-only", ["--verify-only"]), ("dry-run", ["--dry-run"]), ("deploy", [])):
    rc, o, e, k = _main(D, ["deploy_ui.py", "--all", "--ui-root", str(kok2), *ek])
    kontrol(f"L2-D[{kip_adi}] ayrıştırıcısız → RC 1, [FAIL] zapp (AYRISTIRILAMADI), hiçbir app KOŞMADI, "
            "özet 'HİÇ KOŞMADI'",
            rc == 1 and k == [] and _fail_kumesi(o) == {"zapp"} and "AYRISTIRILAMADI" in o
            and "1/1 app BSP adı ÇÖZÜLEMEDİĞİ için HİÇ KOŞMADI" in e and "doğrulandı" not in o,
            f"rc={rc} kosan={k} fail={_fail_kumesi(o)} err={e[-200:]!r}")
rc, o, e, _k = _main(V, ["v.py", "--all", "--ui-root", str(kok2)])
kontrol("L2-V ayrıştırıcısız → RC 1, [FAIL] zapp, özet 'HİÇ KOŞMADI'",
        rc == 1 and _fail_kumesi(o) == {"zapp"} and "1/1 app BSP adı ÇÖZÜLEMEDİĞİ için HİÇ KOŞMADI" in e,
        f"rc={rc} fail={_fail_kumesi(o)} err={e[-200:]!r}")
rc_k, o_k, _e, _k = _main(V, ["v.py", "--apps", "zapp", "--ui-root", str(kok2)])
kontrol("K2 kâhin: V --apps zapp ile aynı RC + aynı FAIL kümesi",
        rc_k == rc and _fail_kumesi(o_k) == _fail_kumesi(o), f"--apps rc={rc_k} {_fail_kumesi(o_k)} --all rc={rc}")
D.AYRISTIRICILAR = _ASIL

# L3 — YİNELENEN anahtar + geçerli app: geçerli olan koşar, belge hatası FAIL
kok3 = _ui_kok("L3", {"dup": YAML_YINELENEN, "zapp": YAML_GECERLI})
rc, o, e, k = _main(D, ["deploy_ui.py", "--all", "--verify-only", "--ui-root", str(kok3)])
kontrol("L3-D yinelenen anahtar → RC 1, [FAIL] dup, zapp KOŞTU, özet koşan/koşmayan ayrı (1/2 HİÇ KOŞMADI)",
        rc == 1 and k == ["zapp"] and _fail_kumesi(o) == {"dup"} and "1/2 app BSP adı ÇÖZÜLEMEDİĞİ" in e
        and "STALE" not in e, f"rc={rc} kosan={k} fail={_fail_kumesi(o)} err={e[-200:]!r}")
rc, o, e, _k = _main(V, ["v.py", "--all", "--ui-root", str(kok3)])
kontrol("L3-V yinelenen anahtar → RC 1, [FAIL] dup", rc == 1 and _fail_kumesi(o) == {"dup"},
        f"rc={rc} fail={_fail_kumesi(o)}")
rc_k, o_k, _e, _k = _main(V, ["v.py", "--apps", "dup,zapp", "--ui-root", str(kok3)])
kontrol("K3 kâhin: V --apps dup,zapp ile aynı RC + aynı FAIL kümesi",
        rc_k == rc and _fail_kumesi(o_k) == _fail_kumesi(o), f"--apps rc={rc_k} {_fail_kumesi(o_k)} --all rc={rc}")

# L4 — politika reddi (standart ad) + hedef ad YOK + geçerli
kok4 = _ui_kok("L4", {"sapstd": YAML_STANDART, "adsiz": YAML_ADSIZ, "zapp": YAML_GECERLI, "notlar": None})
rc, o, e, k = _main(D, ["deploy_ui.py", "--all", "--verify-only", "--ui-root", str(kok4)])
kontrol("L4-D politika reddi + ad yok → RC 1, iki FAIL satırı, yalnız zapp koştu, atlanan 1",
        rc == 1 and k == ["zapp"] and _fail_kumesi(o) == {"sapstd", "adsiz"} and ATL1 in e,
        f"rc={rc} kosan={k} fail={_fail_kumesi(o)} err={e[-200:]!r}")
rc, o, e, _k = _main(V, ["v.py", "--all", "--ui-root", str(kok4)])
kontrol("L4-V politika reddi + ad yok → RC 1, iki FAIL satırı",
        rc == 1 and _fail_kumesi(o) == {"sapstd", "adsiz"}, f"rc={rc} fail={_fail_kumesi(o)}")
rc_k, o_k, _e, _k = _main(V, ["v.py", "--apps", "sapstd,adsiz,zapp", "--ui-root", str(kok4)])
kontrol("K4 kâhin: V --apps <yaml'lı 3 dizin> ile aynı RC + aynı FAIL kümesi",
        rc_k == rc and _fail_kumesi(o_k) == _fail_kumesi(o), f"--apps rc={rc_k} {_fail_kumesi(o_k)} --all rc={rc}")
D.deploy_one = _ASIL_DEPLOY_ONE

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

# -*- coding: utf-8 -*-
"""pbe_ui fixture — PULL-BEFORE-EDIT (ADR 0016) UI eklentisi + `fetch_ui_source --damgala` (Q352-B).

Vaka (2026-09-26): başka makinede bir rapor uygulamasına kolon eklenip deploy edilmişti, repo
habersizdi; eski yerel kodla yapılacak deploy kolonu canlıdan SESSİZCE silerdi. Canlı kontrol
grubu: aynı canlı zip ↔ senkron-öncesi repo webapp'i → GERCEK-FARK=4 (view + controller + 2 i18n).
Bu fixture o vakanın SENTETİK karşılığını (canlıda fazladan kolon) taşır.

Eksenler:
  A  `_pbe_ui.sinifla()` — kapsam: webapp/** · muafiyet YALNIZ `deploy-to-abap` görevinin
     `configuration.exclude`'u (builder `excludes` / başka görev / görev-düzeyi `exclude` DEĞİL) ·
     HARF DUYARLI önek (deploy aracı `RegExp(regex,"g")`, i bayrağı yok — ölçüldü) · `/x/**` ve
     anlaşılmayan desen muafiyet VERMEZ · kök-segment / hariç üst dizin · proje kökü DIŞI webapp
     (`.wt` worktree'si) kapsamda · ui5-deploy.yaml yok → yer tutuculu dict · `komut` saf komut
     (`--session` yok, açıklama yok), açıklama + `--offline` kaçışı `not` anahtarında
  B  `fetch_ui_source --damgala` (in-process `main()`, indirme yamalı, damga API'si kayıt stub'ı):
     temiz → damga · fark / yalnız-canlı / harita sapması → damga YOK · `--zip` / yanlış app /
     yanlış BSP → rc 2, damga YOK · proje kökü DIŞI webapp → damga (mutlak anahtar) ·
     YALNIZ-CANLI test/ DEPLOY-DISI SAYILMAZ · `--offline` → indirmesiz damga + uyarı ·
     seans çözülemedi → rc 2 · `--damgala` YOKKEN rc semantiği DEĞİŞMEZ · damga seans boyunca
     geçerli (sonraki düzenlemeler bloklanmaz)
  C  3. BAĞLAM — GERÇEK kapı alt süreci (`hooks/pull_before_edit.py`, stdin payload) + GERÇEK
     store (`source_drift.tazelik_damgala`): damgasız → exit 2 + komut · damgadan sonra → exit 0 ·
     deploy-dışı dosya → exit 0 · başka seans → exit 2 · kök DIŞI webapp: blok → damgala → serbest
     (kalıcı kilit yok). Altyapı (Q352-A: eklenti kaydı + dosya-anahtarlı
     damga) bulunamazsa C0 FAIL (sessiz atlama yok).

Koşum:     python tests/fixtures/pbe_ui/run.py
MUTASYON:  --mutasyon-<ad>  (MUTASYONLAR; kaynağın BUGÜNKÜ kopyasına tek yama, desen TAM 1 kez
           geçmeli yoksa exit 2 KURULAMADI). Her kip en az bir vektörü düşürmeli.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
FUS = "scripts/fetch_ui_source.py"
PBE = "scripts/hooks/_pbe_ui.py"
# object_types: A kolunun source_drift'i onu import eder (Q352) — kumda yoksa taban KURULAMADI olurdu.
KOPYA = ("scripts/deploy_ui.py", "scripts/verify_ui_static_assets.py", "scripts/source_drift.py",
         "scripts/object_types.py", "scripts/hooks/pull_before_edit.py", PBE, FUS)

MUTASYONLAR = {
    # A — eklenti hiçbir dosyayı tanımaz (kapı UI'ye kör)
    "--mutasyon-sinifla-none": (
        PBE, '    """PULL-BEFORE-EDIT eklenti sözleşmesi (modül başlığı)."""\n',
        '    """PULL-BEFORE-EDIT eklenti sözleşmesi (modül başlığı)."""\n    return None\n'),
    # A — deploy exclude muafiyeti yok (test/** kapıda kalır; damga kipinde YALNIZ-YEREL → rc 1)
    "--mutasyon-deploy-haric-yok": (PBE, "    return any(r.startswith(o) for o in onekler)\n", "    return False\n"),
    # A — HER özel görevin `exclude`'u okunur (deploy-to-abap kapsamı kalkar)
    "--mutasyon-gorev-adi-yok": (PBE, "            if m_oge.group(\"ad\") == DEPLOY_GOREVI:\n", "            if True:\n"),
    # A — `configuration:` şartı kalkar (görev-düzeyi `exclude` da okunur)
    "--mutasyon-conf-kapsami-yok": (
        PBE, '        if conf_g is None:\n            if re.match(r"^configuration:\\s*(?:#.*)?$", govde):\n'
             '                conf_g = g\n            continue\n', ""),
    # A — anlaşılmayan desen de önek sayılır (fail-closed kırılır)
    "--mutasyon-anlasilmayan-muaf": (PBE, "                    anlasilmayan.append(ham)\n",
                                     "                    onekler.append(ham.strip('/^$.*') + '/')\n"),
    # A — `/x/**` düz desen sayılır (aracın regex'inde geçersiz/farklı anlamlı)
    "--mutasyon-yildiz-kabul": (PBE, '/?$")\nDEPLOY_GOREVI', '/?(?:\\*\\*)?$")\nDEPLOY_GOREVI'),
    # A — harf DUYARSIZ kıyas (M6: `Test/` dosyası `/test/` ile sahte-muaf olur)
    "--mutasyon-harf-duyarsiz": (PBE, '    r = rel.replace("\\\\", "/").lstrip("/")\n    return any(r.startswith(o) for o in onekler)\n',
                                 '    r = rel.replace("\\\\", "/").lstrip("/").lower()\n'
                                 '    return any(r.startswith(o.lower()) for o in onekler)\n'),
    # A — önek küçük harfe indirgenir (`/Test/` deseni `Test/` dosyasını muaf SAYMAZ olur)
    "--mutasyon-onek-kucuk": (PBE, '                    onekler.append(d.group("yol") + "/")\n',
                              '                    onekler.append(d.group("yol").lower() + "/")\n'),
    # A — kök DIŞI webapp (worktree) kapsam dışı sayılır (M14)
    "--mutasyon-kok-disi-none": (PBE, "        ust = [s.lower() for s in app.parts]\n", "        return None\n"),
    # A — komuta açıklama eklenir (kapının eklediği `--session` açıklamanın arkasına düşer)
    "--mutasyon-komut-aciklamali": (PBE, "--karsilastir \"{a}/{WEBAPP}\" --damgala'\n",
                                    "--karsilastir \"{a}/{WEBAPP}\" --damgala' + \"   (açıklama)\"\n"),
    # A — kök segment şartı kalkar (proje kaynak kökü dışındaki webapp da kapıya girer)
    "--mutasyon-kok-seg-yok": (PBE, "    if not (kok_seg & set(ust)) or (haric & set(ust)):\n",
                               "    if haric & set(ust):\n"),
    # A — hariç üst dizin (docs/node_modules…) şartı kalkar
    "--mutasyon-ust-haric-yok": (PBE, "    if not (kok_seg & set(ust)) or (haric & set(ust)):\n",
                                 "    if not (kok_seg & set(ust)):\n"),
    # A — BSP çözülemeyen app sessizce serbest
    "--mutasyon-bsp-yok-serbest": (PBE, "    if not bsp:\n        neden = ", "    if not bsp:\n        return None\n        neden = "),
    # B — fark varken de damgalanır (sahte-taze)
    "--mutasyon-damga-farkta": (FUS, "    if kalan:\n        return f\"{len(kalan)} dosya", "    if False:\n        return f\"{len(kalan)} dosya"),
    # B — damga kararı HER ZAMAN "damgalanabilir" (fark varken damgalar — brifin zorunlu negatifi)
    "--mutasyon-damga-hep": (FUS, 'rc≠0) damgayı keser."""\n', 'rc≠0) damgayı keser."""\n    return None\n'),
    # B — rc≠0 iken damga (ör. yalnız-canlı rc 1)
    "--mutasyon-damga-rc": (FUS, "    if rc != 0:\n        return f\"çıkış kodu", "    if False:\n        return f\"çıkış kodu"),
    # B — harita sapmasında damga
    "--mutasyon-damga-sapma": (FUS, "    if sapma:\n        return f\"kaynak haritası sapması", "    if False:\n        return f\"kaynak haritası sapması"),
    # B — damga_engeli anlık görüntü (zip) dalı kalkar (kullanım denetimi ayrı katman — ayrı vektör)
    "--mutasyon-damga-zip-engel-yok": (FUS, "    if not zip_taze:\n        return", "    if False:\n        return"),
    # B — kullanım katmanında --zip reddi kalkar
    "--mutasyon-zip-kullanim-yok": (FUS, "        if a.zip:\n            print(\"[KULLANIM] --damgala TAZE", "        if False:\n            print(\"[KULLANIM] --damgala TAZE"),
    # B — başka app'in webapp'i damgalanabilir
    "--mutasyon-app-uyumsuz": (FUS, "        if a.app_dir and Path(a.app_dir).resolve() != app.resolve():\n", "        if False:\n"),
    # B — BSP uyuşmazlığı denetimi kalkar
    "--mutasyon-bsp-uyumsuz": (FUS, "        if a.bsp and app_bsp and a.bsp.upper() != app_bsp.upper():\n", "        if False:\n"),
    # B — kök DIŞI webapp reddi geri gelir (bug gate HIGH: kapı bloklar, damga yolu yok = kalıcı kilit)
    "--mutasyon-kok-disi-red": (FUS, "            pbe = ui_eklenti_modulu()\n",
                                "            yerel_kok.resolve().relative_to(REPO.resolve())\n"
                                "            pbe = ui_eklenti_modulu()\n"),
    # B — `--offline` `--damgala`sız kabul edilir
    "--mutasyon-offline-tek": (FUS, "    if a.offline and not a.damgala:\n", "    if False:\n"),
    # B — çözülemeyen seans ('default') ile damga yazılır (kapı eşleştirmez → sessiz sahte-başarı)
    "--mutasyon-seans-default": (FUS, '    if not seans or seans == "default":\n', "    if not seans:\n"),
    # B — DEPLOY-DISI etiketi YALNIZ-YEREL'e de basılır (deploy-dışı olmayan yerel dosya gizlenir)
    "--mutasyon-deploy-disi-genis": (FUS, "DEPLOY_DISI if s == YALNIZ_YEREL and pbe.deploy_haric_mi(r, onekler) else s",
                                     "DEPLOY_DISI if s == YALNIZ_YEREL else s"),
    # B — DEPLOY-DISI etiketi YALNIZ-CANLI'ya da basılır (M1: canlıdaki test/ dosyası gizlenir)
    "--mutasyon-deploy-disi-canli": (FUS, "DEPLOY_DISI if s == YALNIZ_YEREL and",
                                     "DEPLOY_DISI if s in (YALNIZ_YEREL, YALNIZ_CANLI) and"),
}


def _dur(mesaj: str) -> None:
    print(f"[KURULAMADI] {mesaj}")
    sys.exit(2)


ARGS = sys.argv[1:]
KIP = None
if ARGS:
    if ARGS[0] in MUTASYONLAR and len(ARGS) == 1:
        KIP = ARGS[0]
    else:
        print(f"[KULLANIM] bilinmeyen argüman {ARGS}; geçerli: {sorted(MUTASYONLAR)}")
        sys.exit(2)

KUM = Path(tempfile.mkdtemp(prefix="pbe_ui_"))
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)   # deploy_ui / source_drift / kapı kökü import anında okur
os.environ.pop("IX_SOURCE_ROOT", None)
(KUM / "project.yaml").write_bytes(b"source_root: SOURCE_CODES\n")
SCRIPTS = KUM / "scripts"
shutil.copytree(KOK / "scripts" / "utils", SCRIPTS / "utils", ignore=shutil.ignore_patterns("__pycache__"))
for rel in KOPYA:
    metin = (KOK / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
    if KIP and MUTASYONLAR[KIP][0] == rel:
        eski, yeni = MUTASYONLAR[KIP][1], MUTASYONLAR[KIP][2]
        if metin.count(eski) != 1:
            _dur(f"YAMA TUTMADI {KIP}: desen {metin.count(eski)} kez geçiyor (1 bekleniyordu)")
        metin = metin.replace(eski, yeni)
    hedef = SCRIPTS / Path(rel).relative_to("scripts")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(metin.encode("utf-8"))
if KIP:
    print(f"### MUTASYON {KIP} — kum: {SCRIPTS}\n")
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(1, str(SCRIPTS / "hooks"))
try:
    _o, _e = sys.stdout, sys.stderr
    import fetch_ui_source as F  # noqa: E402
    import _pbe_ui as P  # noqa: E402
    import source_drift as SD  # noqa: E402
    sys.stdout, sys.stderr = _o, _e
except Exception as exc:  # pragma: no cover
    sys.stdout, sys.stderr = _o, _e
    _dur(f"modül yüklenemedi: {type(exc).__name__}: {exc}")
for _m in (F, P, SD):
    if SCRIPTS.resolve() not in Path(_m.__file__).resolve().parents:
        _dur(f"yanlış modül yüklendi: {_m.__file__} (beklenen {SCRIPTS} altı)")

SONUC: list[tuple[str, bool, str]] = []
COKMELER: list[str] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


# ───────────────────── sentetik proje (jenerik: ZSD001_APP1 / ZSD001_APP2) ─────────────────────
def deploy_yaml(bsp: str, exclude_satirlari: str = "          - /test/\n          - /.claude/\n") -> bytes:
    return ("specVersion: \"4.0\"\nmetadata:\n  name: ns.app\ntype: application\nbuilder:\n"
            "  resources:\n    excludes:\n      - /test/**\n      - /localService/**\n"
            "  customTasks:\n    - name: deploy-to-abap\n      afterTask: generateCachebusterInfo\n"
            "      configuration:\n        target:\n          url: https://sap.example.invalid:44300\n"
            "          client: \"100\"\n        app:\n"
            f"          name: {bsp}\n          description: Ornek\n          package: ZSD001_CLC\n"
            "          transport: XXXK900000\n        exclude:\n" + exclude_satirlari).encode()


CTRL = b'sap.ui.define([], function () {\n\t"use strict";\n\treturn { a: 1 };\n});\n'
VIEW = (b'<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns="sap.m">\n  <Table>\n    <columns>\n'
        b'      <Column><Text text="{i18n>colOrder}"/></Column>\n    </columns>\n  </Table>\n</mvc:View>\n')
# Vakanın sentetik karşılığı: canlıda FAZLADAN kolon (başka makinede eklenip deploy edilmiş).
VIEW_KOLONLU = VIEW.replace(b"    </columns>", b'      <Column><Text text="{i18n>colReport}"/></Column>\n    </columns>')
I18N = b"appTitle=Liste\ncolOrder=Siparis\n"
I18N_KOLONLU = I18N + b"colReport=Rapor Kodu\n"
MANIFEST = {"_version": "1.59.0", "sap.app": {"id": "ns.app"}, "sap.ui5": {"models": {}}}
META = b"<edmx:Edmx/>\n"


def crlf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def harita(hedef: str, kaynak: str) -> bytes:
    return json.dumps({"version": 3, "file": hedef, "sources": [kaynak], "mappings": "AAAA"}).encode()


def yerel_kaynak(view: bytes = VIEW, i18n: bytes = I18N) -> dict[str, bytes]:
    return {"Component.js": CTRL, "controller/List.controller.js": CTRL, "view/List.view.xml": view,
            "i18n/i18n.properties": i18n, "manifest.json": (json.dumps(MANIFEST, indent=2) + "\n").encode(),
            "localService/mainService/metadata.xml": META}


def canli_bsp(view: bytes = VIEW, i18n: bytes = I18N, **ek) -> dict[str, bytes]:
    m = json.loads(json.dumps(MANIFEST))
    m["sap.ui5"]["flexBundle"] = False                     # build eklemesi → BUILD-DONUSUMU
    d = {"Component-preload.js": b"sap.ui.require.preload({});",
         "Component-dbg.js": crlf(CTRL), "Component.js": b"min", "Component.js.map": harita("Component.js", "Component-dbg.js"),
         "controller/List-dbg.controller.js": crlf(CTRL), "controller/List.controller.js": b"min",
         "controller/List.controller.js.map": harita("List.controller.js", "List-dbg.controller.js"),
         "view/List.view.xml": crlf(view), "i18n/i18n.properties": crlf(i18n),
         "manifest.json": crlf((json.dumps(m, indent=2) + "\n").encode()),
         "localService/mainService/metadata.xml": crlf(META)}
    d.update(ek)
    return d


def zip_bayt(d: dict[str, bytes]) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for k, v in d.items():
            z.writestr(k, v)
    return b.getvalue()


def dizin_yaz(d: dict[str, bytes], kok: Path) -> Path:
    if kok.exists():
        shutil.rmtree(kok)
    for k, v in d.items():
        p = kok / k
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(v)
    return kok


def app_kur(ad: str, bsp: str | None, dosyalar: dict[str, bytes], kok: Path | None = None,
            yaml_bayt: bytes | None = None) -> Path:
    app = (kok or KUM / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui") / ad
    if app.exists():
        shutil.rmtree(app)
    dizin_yaz(dosyalar, app / "webapp")
    if yaml_bayt is not None:
        (app / "ui5-deploy.yaml").write_bytes(yaml_bayt)
    elif bsp:
        (app / "ui5-deploy.yaml").write_bytes(deploy_yaml(bsp))
    (app / "ui5.yaml").write_bytes(b"specVersion: \"4.0\"\n")
    return app


YEREL_TESTLI = dict(yerel_kaynak(), **{"test/flpSandbox.html": b"<html/>\n"})
APP1 = app_kur("app1", "ZSD001_APP1", YEREL_TESTLI)
APP2 = app_kur("app2", "ZSD001_APP2", yerel_kaynak())

# ───────────────────────────── A — sinifla() ─────────────────────────────
def s(p) -> object:
    try:
        return P.sinifla(Path(p), KUM)
    except Exception as e:   # noqa: BLE001
        COKMELER.append(f"sinifla({p}) → {type(e).__name__}: {e}")
        return f"CÖKME {type(e).__name__}"


r = s(APP1 / "webapp" / "view" / "List.view.xml")
kontrol("A1 webapp dosyası → dict: nesne=BSP, tip=bsp, komut SAF (--app-dir/--karsilastir/--damgala ile BİTER, "
        "--session YOK), `--offline` kaçışı `not`ta",
        isinstance(r, dict) and r.get("nesne") == "ZSD001_APP1" and r.get("tip") == "bsp"
        and "fetch_ui_source.py --app-dir \"SOURCE_CODES/SD/ZSD001_CLC/ui/app1\"" in r.get("komut", "")
        and "--karsilastir \"SOURCE_CODES/SD/ZSD001_CLC/ui/app1/webapp\" --damgala" in r.get("komut", "")
        and "--session" not in r.get("komut", "") and r.get("komut", "").endswith("--damgala")
        and "`--offline` ekle" in r.get("not", ""), repr(r))
kontrol("A2 app kökündeki dosya (ui5.yaml / ui5-deploy.yaml) → None (webapp değil)",
        s(APP1 / "ui5.yaml") is None and s(APP1 / "ui5-deploy.yaml") is None)
kontrol("A3 deploy `exclude: /test/` altı → None (canlıya hiç gitmez)",
        s(APP1 / "webapp" / "test" / "flpSandbox.html") is None)
r = s(APP1 / "webapp" / "localService" / "mainService" / "metadata.xml")
kontrol("A4 localService (yalnız builder `excludes` — canlıda VAR) → dict (muaf DEĞİL)",
        isinstance(r, dict) and r.get("nesne") == "ZSD001_APP1", repr(r))
kontrol("A5 kök segment (SOURCE_CODES) dışındaki webapp → None",
        s(KUM / "baska" / "ui" / "x" / "webapp" / "a.js") is None)
kontrol("A6 hariç üst dizin (docs / node_modules) altındaki webapp → None",
        s(KUM / "SOURCE_CODES" / "SD" / "docs" / "x" / "webapp" / "a.js") is None
        and s(APP1 / "node_modules" / "lib" / "webapp" / "a.js") is None)
APP_YAMLSIZ = app_kur("app_yamlsiz", None, yerel_kaynak())
r = s(APP_YAMLSIZ / "webapp" / "Component.js")
kontrol("A7 ui5-deploy.yaml YOK → dict YİNE döner (sessiz geçiş yok), komut `--bsp <BSP_ADI>`, neden `not`ta",
        isinstance(r, dict) and r.get("nesne") == "<BSP_ADI>" and "--bsp <BSP_ADI>" in r.get("komut", "")
        and r.get("komut", "").endswith("--damgala") and "ui5-deploy.yaml yok" in r.get("not", ""), repr(r))
APP_REGEX = app_kur("app_regex", "ZSD001_APP3", yerel_kaynak(),
                    yaml_bayt=deploy_yaml("ZSD001_APP3", "          - '^/test/.*$'\n"))
r = s(APP_REGEX / "webapp" / "test" / "x.js")
kontrol("A8 anlaşılmayan exclude deseni (regex) → muafiyet YOK, dict (fail-closed)",
        isinstance(r, dict) and P.deploy_haric_desenleri(APP_REGEX) == ([], ["^/test/.*$"]), repr(r))
APP_SATIRICI = app_kur("app_satirici", "ZSD001_APP4", yerel_kaynak(),
                       yaml_bayt=deploy_yaml("ZSD001_APP4", "").replace(b"        exclude:\n", b"        exclude: [/test/]\n"))
kontrol("A9 satır-içi `exclude: [/test/]` → anlaşılmayan, muafiyet YOK",
        isinstance(s(APP_SATIRICI / "webapp" / "test" / "x.js"), dict)
        and P.deploy_haric_desenleri(APP_SATIRICI) == ([], ["[/test/]"]), repr(P.deploy_haric_desenleri(APP_SATIRICI)))
r = s("SOURCE_CODES/SD/ZSD001_CLC/ui/app1/webapp/view/List.view.xml")
kontrol("A10 göreli yol kök'e göre çözülür → dict", isinstance(r, dict) and r.get("nesne") == "ZSD001_APP1", repr(r))
kontrol("A11 deploy_haric_desenleri gerçek biçim → ['test/', '.claude/'], anlaşılmayan yok",
        P.deploy_haric_desenleri(APP1) == (["test/", ".claude/"], []), repr(P.deploy_haric_desenleri(APP1)))
# Bug gate LOW (M6) — deploy aracı HARF DUYARLI eşler: `Test/` dosyası `/test/` ile canlıdan DÜŞMEZ.
_buyuk = APP1 / "webapp" / "Test" / "x.js"
r = s(_buyuk)
kontrol("A12 HARF DUYARLI: `/test/` deseni `Test/x.js`i MUAF SAYMAZ (dict) · deploy_haric_mi('Test/x.js',['test/'])=False",
        isinstance(r, dict) and P.deploy_haric_mi("Test/x.js", ["test/"]) is False
        and P.deploy_haric_mi("test/x.js", ["test/"]) is True, repr(r))
APP_BUYUK = app_kur("app_buyuk", "ZSD001_APP5", yerel_kaynak(),
                    yaml_bayt=deploy_yaml("ZSD001_APP5", "          - /Test/\n"))
kontrol("A13 HARF DUYARLI (ters yön): `/Test/` deseni `Test/x.js`i muaf sayar (önek küçültülmez)",
        s(APP_BUYUK / "webapp" / "Test" / "x.js") is None
        and P.deploy_haric_desenleri(APP_BUYUK) == (["Test/"], []), repr(P.deploy_haric_desenleri(APP_BUYUK)))
APP_YILDIZ = app_kur("app_yildiz", "ZSD001_APP6", yerel_kaynak(),
                     yaml_bayt=deploy_yaml("ZSD001_APP6", "          - /test/**\n"))
kontrol("A14 `/test/**` (aracın regex'inde geçersiz/farklı) → anlaşılmayan, muafiyet YOK",
        isinstance(s(APP_YILDIZ / "webapp" / "test" / "x.js"), dict)
        and P.deploy_haric_desenleri(APP_YILDIZ) == ([], ["/test/**"]), repr(P.deploy_haric_desenleri(APP_YILDIZ)))
# Bug gate APPLY — YALNIZ deploy-to-abap görevinin configuration.exclude'u.
_baska_gorev = (b"  customTasks:\n    - name: ui5-task-zipper\n      configuration:\n        exclude:\n"
                b"          - /test/\n")
APP_BASKA = app_kur("app_baska", "ZSD001_APP7", yerel_kaynak(),
                    yaml_bayt=deploy_yaml("ZSD001_APP7", "          - /xyz/\n").replace(b"  customTasks:\n", _baska_gorev))
kontrol("A15 BAŞKA özel görevin `configuration.exclude`'u okunmaz → test/ MUAF DEĞİL (dict)",
        isinstance(s(APP_BASKA / "webapp" / "test" / "x.js"), dict)
        and P.deploy_haric_desenleri(APP_BASKA) == (["xyz/"], []), repr(P.deploy_haric_desenleri(APP_BASKA)))
APP_GOREVDUZEY = app_kur("app_gorevduzey", "ZSD001_APP8", yerel_kaynak(),
                         yaml_bayt=deploy_yaml("ZSD001_APP8", "          - /xyz/\n").replace(
                             b"      afterTask: generateCachebusterInfo\n",
                             b"      afterTask: generateCachebusterInfo\n      exclude:\n        - /test/\n"))
kontrol("A16 deploy-to-abap GÖREV-DÜZEYİ `exclude` (configuration dışında) okunmaz → test/ MUAF DEĞİL",
        isinstance(s(APP_GOREVDUZEY / "webapp" / "test" / "x.js"), dict)
        and P.deploy_haric_desenleri(APP_GOREVDUZEY) == (["xyz/"], []), repr(P.deploy_haric_desenleri(APP_GOREVDUZEY)))
# Bug gate HIGH (M14) — proje kökü DIŞINDAKİ webapp (kanonik `.wt` worktree'si) kapıdadır.
DIS = Path(tempfile.mkdtemp(prefix="pbe_ui_dis_"))
APP_DIS = app_kur("appd", "ZSD001_APP1", yerel_kaynak(), kok=DIS / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui")
r = s(APP_DIS / "webapp" / "view" / "List.view.xml")
kontrol("A17 kök DIŞI webapp (kök segmentli) → dict (kapıda) · komut MUTLAK --app-dir",
        isinstance(r, dict) and r.get("nesne") == "ZSD001_APP1"
        and f'--app-dir "{APP_DIS.as_posix()}"' in r.get("komut", ""), repr(r))
kontrol("A18 kök DIŞI, kök segmentsiz webapp → None",
        s(DIS / "baska" / "ui" / "x" / "webapp" / "a.js") is None)

# ───────────────────────── B — fetch_ui_source --damgala ─────────────────────────
STORE: dict[str, str] = {}
INDIRME: list[str] = []
SEANS = ["S-TEST"]
_asil_anahtar = getattr(SD, "tazelik_anahtari", None)


def anahtar(p) -> str:
    if _asil_anahtar:
        return _asil_anahtar(p, KUM)
    try:
        return Path(p).resolve().relative_to(KUM.resolve()).as_posix().upper()
    except ValueError:
        return Path(p).resolve().as_posix().upper()


def stub_damgala(seans, path, root=None) -> str:
    k = anahtar(path)
    STORE[k] = seans
    return k


def canli_ayarla(d: dict[str, bytes]) -> None:
    zb = zip_bayt(d)

    def _indir(bsp, conn):
        INDIRME.append(bsp)
        return zb, {"Name": bsp, "Package": "ZSD001_CLC", "Description": "x"}
    F.zip_indir = _indir


F.baglanti = lambda: ("https://sap.example.invalid", "u", "p", "100")
_asil_sd = {k: getattr(SD, k, None) for k in ("seans_kimligi", "tazelik_damgala")}
SD.seans_kimligi = lambda explicit="": explicit or SEANS[0]
SD.tazelik_damgala = stub_damgala


def cagir(argv: list[str]) -> tuple:
    t, h = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(t), redirect_stderr(h):
            rc = F.main(argv)
    except SystemExit as e:
        rc = e.code
        if rc != 2:
            COKMELER.append(f"{argv[:3]}… → SystemExit({rc!r})")
    except Exception as e:   # noqa: BLE001
        COKMELER.append(f"{argv[:3]}… → {type(e).__name__}: {e}")
        rc = f"CÖKME {type(e).__name__}"
    return rc, t.getvalue() + h.getvalue()


def damgali(app: Path) -> list[str]:
    on = anahtar(app / "webapp").rstrip("/") + "/"
    return sorted(k for k in STORE if k.startswith(on))


def kapidan_gecer(p: Path) -> bool:
    """Kapının kararının simülasyonu: sinifla None ya da dosya anahtarı store'da."""
    return P.sinifla(p, KUM) is None or anahtar(p) in STORE


W1 = str(APP1 / "webapp")
canli_ayarla(canli_bsp())
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala"])
beklenen = sorted(anahtar(APP1 / "webapp" / r) for r in yerel_kaynak())
kontrol("B1 kontrol grubu: canlı = yerel → rc 0, deploy-dışı test/ DEPLOY-DISI, 6 dosya damgalı (test/ HARİÇ)",
        rc == 0 and damgali(APP1) == beklenen and "DEPLOY-DISI     test/flpSandbox.html" in out
        and "PBE damgası: YAZILDI — 6 dosya" in out, f"rc={rc} damga={damgali(APP1)}\n{out[-900:]}")
kontrol("B1b damga sonrası kapı: webapp dosyaları geçer; test/ zaten kapsam dışı",
        all(kapidan_gecer(APP1 / "webapp" / r) for r in YEREL_TESTLI))
# Seans içi: kendi deploy'undan sonra (canlı = yerel, hiçbir şey yeniden çalıştırılmadan) ardışık düzenlemeler
for _ in range(3):
    (APP1 / "webapp" / "view" / "List.view.xml").write_bytes(VIEW_KOLONLU)
kontrol("B1c damga seans boyunca geçerli: düzenleme/deploy sonrası tekrar tekrar geçer (yeniden karşılaştırma YOK)",
        kapidan_gecer(APP1 / "webapp" / "view" / "List.view.xml") and len(INDIRME) == 1, f"indirme={INDIRME}")
(APP1 / "webapp" / "view" / "List.view.xml").write_bytes(VIEW)

canli_ayarla(canli_bsp(view=VIEW_KOLONLU, i18n=I18N_KOLONLU))
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala"])
kontrol("B2 VAKA: canlıda fazladan kolon (başka makine deploy'u) → rc 1, GERCEK-FARK=2, HİÇBİR dosya damgalanmaz",
        rc == 1 and "GERCEK-FARK=2" in out and not STORE and "PBE damgası: YAPILMADI" in out,
        f"rc={rc} store={sorted(STORE)}\n{out[-700:]}")
kontrol("B2b fark varken kapı view dosyasını BLOKLAR (damga yok)",
        not kapidan_gecer(APP1 / "webapp" / "view" / "List.view.xml"))

canli_ayarla(canli_bsp(**{"view/Yeni.view.xml": crlf(b"<x/>\n")}))
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala"])
kontrol("B3 YALNIZ-CANLI dosya → rc 1, damga YOK", rc == 1 and not STORE and "YALNIZ-CANLI=1" in out,
        f"rc={rc} store={sorted(STORE)}")

APP2_YEREL = dict(yerel_kaynak(), **{"view/Yerel.view.xml": b"<x/>\n"})
app_kur("app2", "ZSD001_APP2", APP2_YEREL)
canli_ayarla(canli_bsp())
STORE.clear()
rc, out = cagir(["--app-dir", str(APP2), "--karsilastir", str(APP2 / "webapp"), "--damgala"])
kontrol("B4 deploy-dışı OLMAYAN YALNIZ-YEREL → DEPLOY-DISI sayılmaz, rc 1, damga YOK",
        rc == 1 and not STORE and "YALNIZ-YEREL    view/Yerel.view.xml" in out, f"rc={rc}\n{out[-500:]}")
app_kur("app2", "ZSD001_APP2", yerel_kaynak())

zp = KUM / "snap.zip"
zp.write_bytes(zip_bayt(canli_bsp()))
STORE.clear()
rc, out = cagir(["--zip", str(zp), "--karsilastir", W1, "--damgala"])
kontrol("B5 --zip anlık görüntüsü + --damgala → rc 2 KULLANIM, damga YOK", rc == 2 and not STORE and "TAZE indirme" in out,
        f"rc={rc}\n{out[-300:]}")
kontrol("B5b damga_engeli(zip_taze=False) tek başına da keser (ikinci katman)",
        F.damga_engeli([], zip_taze=False, sapma=[], rc=0) is not None)
kontrol("B5c damga_engeli: rc 1 → keser · sapma → keser · temiz → None",
        F.damga_engeli([], True, [], 1) is not None and F.damga_engeli([], True, ["x"], 0) is not None
        and F.damga_engeli([("a", F.AYNI, "", []), ("t", F.DEPLOY_DISI, "", [])], True, [], 0) is None)
kontrol("B5d damga_engeli: rc 0 OLSA BİLE GERCEK-FARK / YALNIZ-CANLI / YALNIZ-YEREL satırı keser (rc'den bağımsız katman)",
        all(F.damga_engeli([("a", F.AYNI, "", []), ("x", k, "", [])], True, [], 0) is not None
            for k in (F.GERCEK, F.YALNIZ_CANLI, F.YALNIZ_YEREL)))

sapmali = canli_bsp(**{"controller/List.controller.js.map": harita("List.controller.js", "List.controller.ts")})
canli_ayarla(sapmali)
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala"])
kontrol("B6 kaynak haritası sapması (TS izi) → rc 1, damga YOK", rc == 1 and not STORE and "harita" in out,
        f"rc={rc} store={sorted(STORE)}\n{out[-400:]}")

canli_ayarla(canli_bsp())
STORE.clear()
rc, out = cagir(["--app-dir", str(APP2), "--karsilastir", W1, "--damgala"])
kontrol("B7 --app-dir başka app, --karsilastir app1 → rc 2, damga YOK", rc == 2 and not STORE and "FARKLI uygulama" in out,
        f"rc={rc}\n{out[-300:]}")
rc, out = cagir(["--bsp", "ZSD001_APP2", "--karsilastir", W1, "--damgala"])
kontrol("B8 --bsp app'in yaml BSP'sinden farklı → rc 2, damga YOK", rc == 2 and not STORE and "damga YAZILMAZ" in out,
        f"rc={rc}\n{out[-300:]}")
STORE.clear()
rc, out = cagir(["--app-dir", str(APP_DIS), "--karsilastir", str(APP_DIS / "webapp"), "--damgala"])
beklenen_dis = sorted(anahtar(APP_DIS / "webapp" / r) for r in yerel_kaynak())
kontrol("B9 kök DIŞI webapp (worktree) → rc 0, 6 dosya MUTLAK anahtarla damgalı, kapı geçer (kalıcı kilit YOK)",
        rc == 0 and damgali(APP_DIS) == beklenen_dis and all(k.startswith(DIS.resolve().as_posix().upper())
                                                             for k in beklenen_dis)
        and kapidan_gecer(APP_DIS / "webapp" / "view" / "List.view.xml"), f"rc={rc} store={sorted(STORE)}\n{out[-400:]}")
STORE.clear()
rc, out = cagir(["--app-dir", str(APP_DIS), "--karsilastir", str(APP_DIS / "webapp"), "--damgala", "--offline"])
kontrol("B9b kök DIŞI webapp --offline → rc 0, damgalı", rc == 0 and damgali(APP_DIS) == beklenen_dis,
        f"rc={rc}\n{out[-300:]}")

INDIRME.clear()
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala", "--offline"])
kontrol("B10 --offline → İNDİRME YOK, rc 0, 6 dosya damgalı, [OFFLINE] uyarısı + kapsam beyanında OFFLINE",
        rc == 0 and not INDIRME and damgali(APP1) == beklenen and "[OFFLINE]" in out
        and "fetch YAPILMADI" in out and "ezme riskini kabul ettin" in out
        and "PBE damgası: OFFLINE" in out, f"rc={rc} indirme={INDIRME}\n{out[-500:]}")
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--offline"])
kontrol("B11 --offline --damgala'sız → rc 2 KULLANIM, damga YOK", rc == 2 and not STORE and not INDIRME, f"rc={rc}")

SEANS[0] = "default"
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala"])
kontrol("B12 seans çözülemedi ('default') → rc 2, damga YOK, --session önerilir",
        rc == 2 and not STORE and "--session" in out, f"rc={rc} store={sorted(STORE)}\n{out[-300:]}")
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala", "--session", "S-ELLE"])
kontrol("B13 --session geçersiz kılma → o seansla damgalanır",
        rc == 0 and damgali(APP1) == beklenen and set(STORE.values()) == {"S-ELLE"}, f"rc={rc} {set(STORE.values())}")
SEANS[0] = "S-TEST"

STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1])
kontrol("B14 --damgala YOKKEN rc semantiği DEĞİŞMEZ: test/ YALNIZ-YEREL → rc 1, DEPLOY-DISI yok, damga yok",
        rc == 1 and not STORE and "YALNIZ-YEREL=1" in out and "DEPLOY-DISI" not in out
        and "PBE damgası: İSTENMEDİ" in out, f"rc={rc}\n{out[-400:]}")
rc, out = cagir(["--app-dir", str(APP1), "--damgala"])
kontrol("B15 --damgala --karsilastir'sız → rc 2", rc == 2 and not STORE, f"rc={rc}")
# Bug gate LOW (M1) — canlıda olup yerelde olmayan deploy-exclude yolu DEPLOY-DISI SAYILMAZ (canlıda VAR =
# başka makinenin deploy'u; gizlenirse sahte-taze damga).
canli_ayarla(canli_bsp(**{"test/Canli.js": crlf(b"x\n")}))
STORE.clear()
rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala"])
kontrol("B16 damga kipi: canlıda `test/Canli.js` (yerelde yok) → YALNIZ-CANLI kalır, rc 1, damga YOK",
        rc == 1 and not STORE and "YALNIZ-CANLI    test/Canli.js" in out and "YALNIZ-CANLI=1" in out,
        f"rc={rc} store={sorted(STORE)}\n{out[-600:]}")
kontrol("B16b deploy_disi_etiketle saf: YALNIZ-CANLI satırı exclude altında olsa da değişmez",
        F.deploy_disi_etiketle([("test/a.js", F.YALNIZ_CANLI, "", []), ("test/b.js", F.YALNIZ_YEREL, "", [])],
                               ["test/"]) == [("test/a.js", F.YALNIZ_CANLI, "", []), ("test/b.js", F.DEPLOY_DISI, "", [])])

for _k, _v in _asil_sd.items():   # C eksenine GERÇEK API ile geç
    if _v is None:
        if hasattr(SD, _k):
            delattr(SD, _k)
    else:
        setattr(SD, _k, _v)

# ─────────────── C — 3. BAĞLAM: gerçek kapı alt süreci + gerçek store ───────────────
KAPI = SCRIPTS / "hooks" / "pull_before_edit.py"
a_kolu = (_asil_sd["tazelik_damgala"] is not None
          and "_EK_DENETCILER" in KAPI.read_text(encoding="utf-8") and '"_pbe_ui"' in KAPI.read_text(encoding="utf-8"))
if not a_kolu:
    # Q352-A dalda (86915ec) — altyapı kaybolursa bu SESSİZ atlama değil FAIL'dir (geçer sayılmaz).
    kontrol("C0 gerçek kapı altyapısı (source_drift.tazelik_damgala + pull_before_edit._EK_DENETCILER/_pbe_ui) VAR",
            False, "A kolu altyapısı bulunamadı — gerçek kapı/store uçtan uca koşmadı")
else:
    def kapi(p: Path, seans: str = "S-KAPI") -> tuple[int, str]:
        yuk = json.dumps({"tool_name": "Edit", "session_id": seans, "tool_input": {"file_path": str(p)}})
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(KUM), PYTHONIOENCODING="utf-8")
        r_ = subprocess.run([sys.executable, str(KAPI)], input=yuk.encode("utf-8"), capture_output=True,
                            cwd=str(KUM), env=env, timeout=60)
        return r_.returncode, r_.stderr.decode("utf-8", "replace")

    SD.FRESH_STORE = KUM / ".claude" / ".session_fresh.json"
    hedef = APP1 / "webapp" / "view" / "List.view.xml"
    kod, err = kapi(hedef)
    kontrol("C1 GERÇEK kapı, damgasız webapp dosyası → exit 2 + fetch_ui_source --damgala komutu",
            kod == 2 and "fetch_ui_source.py --app-dir" in err and "--damgala" in err, f"exit={kod}\n{err[-500:]}")
    kod, err = kapi(APP1 / "webapp" / "test" / "flpSandbox.html")
    kontrol("C2 GERÇEK kapı, deploy-dışı test/ dosyası → exit 0", kod == 0, f"exit={kod}\n{err[-300:]}")
    canli_ayarla(canli_bsp())
    rc, out = cagir(["--app-dir", str(APP1), "--karsilastir", W1, "--damgala", "--session", "S-KAPI"])
    kod, err = kapi(hedef)
    kontrol("C3 GERÇEK store'a damga → aynı dosyada GERÇEK kapı exit 0",
            rc == 0 and kod == 0, f"rc={rc} exit={kod}\n{out[-300:]}\n{err[-300:]}")
    kod, err = kapi(hedef, seans="S-BASKA")
    kontrol("C4 başka seans → GERÇEK kapı yine exit 2 (damga seansa bağlı)", kod == 2, f"exit={kod}")
    hedef_dis = APP_DIS / "webapp" / "view" / "List.view.xml"
    kod1, err1 = kapi(hedef_dis, seans="S-DIS")
    rc, out = cagir(["--app-dir", str(APP_DIS), "--karsilastir", str(APP_DIS / "webapp"), "--damgala",
                     "--session", "S-DIS"])
    kod2, err2 = kapi(hedef_dis, seans="S-DIS")
    kontrol("C5 kök DIŞI webapp: GERÇEK kapı exit 2 → --damgala (gerçek store, mutlak anahtar) → GERÇEK kapı exit 0",
            kod1 == 2 and "--damgala" in err1 and rc == 0 and kod2 == 0,
            f"exit1={kod1} rc={rc} exit2={kod2}\n{err1[-300:]}\n{out[-300:]}\n{err2[-300:]}")

kontrol("Z0 hiçbir çağrı ÇÖKMEDİ (çökme geçer sayılmaz)", not COKMELER, "; ".join(COKMELER))

# ───────────────────────────── özet ─────────────────────────────
gecen = sum(ok for _, ok, _ in SONUC)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok and detay:
        # Koşucu çıktısındaki `[KULLANIM]` alıntısı bataryada KIP-RED sanılmasın (ayrı mesaj biçimi).
        print("         " + detay.replace("[KULLANIM]", "(KULLANIM)").replace("\n", "\n         ")[:1500])
print(f"\npbe_ui: {gecen}/{len(SONUC)} PASS" + (f" (MUTASYON {KIP})" if KIP else ""))
shutil.rmtree(KUM, ignore_errors=True)
shutil.rmtree(DIS, ignore_errors=True)
sys.exit(0 if gecen == len(SONUC) else 1)

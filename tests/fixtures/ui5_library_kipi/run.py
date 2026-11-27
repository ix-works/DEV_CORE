# -*- coding: utf-8 -*-
"""ui5_library_kipi — UI5 reuse library (`ui5.yaml` type: library) kipi: deploy_ui · verify_ui_static_assets ·
PULL-BEFORE-EDIT UI eklentisi (`hooks/_pbe_ui`) · fetch_ui_source (2026-11-27).

KÖK (ölçüldü, @ui5/cli 4.0.61 · @sap/ux-ui5-tooling 1.30.0): dört araç yalnız UYGULAMA düzenini tanıyordu
(`<app>/webapp/**` kaynak, `dist/Component-preload.js`). Library'de kaynak `<lib>/src/<ns-yolu>/`, paket
`library-preload.js`, ve varsayılan build çıktısı `dist/resources/<ns-yolu>/`'dadır. deploy_ui'nin koştuğu
`fiori deploy` CLI'ı dist'i OLDUĞU GİBİ arşivler (`createDistWorkspace`: `<cwd>/dist` ↔ `/resources/fiori/cli/`)
⇒ Namespace düzenli dist BSP'ye `resources/<ns>/…` yükler. Doğru düzen `--output-style Flat` ile kurulur.

Vektörler:
  A deploy_ui   — library Flat dist → library-preload doğrulaması · Namespace dist → deploy KOŞMAZ ·
                  tipi okunamayan library → uygulama yolu deploy öncesi FAIL · uygulama kontrol grubu
                  (Component-preload, eski imza) · changed_apps src (yalnız library) · --all · tip belgesi seçimi
  B verify      — library kaynak kökü src/<ns> · kaynak farkı · Namespace dist FAIL · iki .library FAIL ·
                  uygulama çıktısı (etiket `webapp`) aynen
  C PBE         — library src dosyası kapıda · deploy-exclude ns köküne göre · src'li UYGULAMA kapıda DEĞİL ·
                  tipi okunamayan library fail-closed kapıda · kök segment dışı · lib/test dışı · webapp komutu aynen
  D fetch       — geri kurma library-preload'u atar · paket haritası sondadan muaf (uygulamada değil) ·
                  manifest/resources.json build ürünü (yalnız library + yerelde .library) · --damgala kaynak kökü ·
                  --eslik library'de rc 2
  E gerçek build — `UI5_CLI` (ya da PATH'te `ui5`) varsa GERÇEK `ui5 build` (Flat + generateResourcesJson ve
                  Default): Flat çıktısı geri kurulup src ile kıyaslanınca YALNIZ AYNI/BUILD · Default çıktısı
                  deploy engeline takılır. CLI yoksa `[ATLA]` (PASS DEĞİL).

Harness: araçların `main()`'i gerçek giriş noktası; yalnız ağ/kimlik/build/deploy sahtelenir. SAP'ye dokunulmaz.
Kum: `mkdtemp`; süreç geneli YAZMA KALKANI (TEMP dışı yazma/silme → PermissionError + KACAK, Z0 sınar).

Koşum:     python tests/fixtures/ui5_library_kipi/run.py   (gerçek build için: UI5_CLI=<.../@ui5/cli/bin/ui5.cjs>)
MUTASYON:  --mutasyon-<ad> (MUTASYONLAR; kum kopyasına tek yama; yama tutmazsa exit 2 KURULAMADI)
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
sys.dont_write_bytecode = True

KOK = Path(__file__).resolve().parents[3]
DUI = "scripts/deploy_ui.py"
VUS = "scripts/verify_ui_static_assets.py"
FUS = "scripts/fetch_ui_source.py"
PBE = "scripts/hooks/_pbe_ui.py"
KOPYA = (DUI, VUS, FUS, PBE, "scripts/source_drift.py", "scripts/object_types.py")

MUTASYONLAR = {
    # A — library hiç tanınmaz (bugünkü uygulama yolu)
    "--mutasyon-tip-hep-uygulama": (DUI, "    kutuphane = kutuphane_mi(app_dir)   # yalnız",
                                    "    kutuphane = False   # yalnız"),
    # A — Flat düzen engeli kalkar (Namespace dist'in teşhisi kaybolur)
    "--mutasyon-flat-engeli-yok": (DUI, '    if (dist / "resources").is_dir():\n        return ("dist/resources/ VAR',
                                   '    if False:\n        return ("dist/resources/ VAR'),
    # A — canlı doğrulama library'de de Component-preload'u ister
    "--mutasyon-fetch-adi": (DUI, "bsp, dosya=LIB_PRELOAD) if kutuphane", "bsp) if kutuphane"),
    # A — changed_apps src dalı yok
    "--mutasyon-changed-src-yok": (DUI, "            if m and kutuphane_mi(ui_root / m.group(1)):\n",
                                   "            if False:\n"),
    # A — changed_apps src'yi tipe bakmadan sayar (src'li uygulama da listeye girer)
    "--mutasyon-changed-src-tipsiz": (DUI, "            if m and kutuphane_mi(ui_root / m.group(1)):\n",
                                      "            if m:\n"),
    # A — tip ilk belgeden okunur (@ui5/project'in seçtiği project belgesi değil)
    "--mutasyon-tip-ilk-belge": (DUI, '    projeler = [b for b in belgeler if (b.get("kind") or "project") == "project"]\n',
                                 "    projeler = belgeler[:1]\n"),
    # A — PyYAML varsayılanı: yinelenen anahtarda SONUNCUYU alır (@ui5/project HATA verir)
    "--mutasyon-yinelenen-anahtar": (DUI, "Loader=_yinelenen_anahtar_yukleyici(_yaml))", "Loader=_yaml.SafeLoader)"),
    # A — şema dışı tip (`Library`) None değil, ham değer döner
    "--mutasyon-tip-semasiz": (DUI, "    if tip not in UI5_PROJE_TIPLERI:\n", "    if False:\n"),
    # A — eşleme olmayan belge (boş/liste) yok sayılır (@ui5/project HATA verir)
    "--mutasyon-belge-eslemesiz": (DUI, "    if not all(isinstance(b, dict) for b in belgeler):\n",
                                   "    belgeler = [b for b in belgeler if isinstance(b, dict)]\n    if False:\n"),
    # B — verify library dalı yok (webapp tabanı)
    "--mutasyon-vus-lib-yok": (VUS, "    if kutuphane_mi(app_dir):\n        # Library (2026-11-27)",
                               "    if False:\n        # Library (2026-11-27)"),
    # B — verify Namespace dist engeli yok
    "--mutasyon-vus-namespace-yok": (VUS, '        if (app_dir / "dist" / "resources").is_dir():\n',
                                     "        if False:\n"),
    # C — PBE library dalı yok
    "--mutasyon-pbe-lib-yok": (PBE, "            if kutuphane_kaynagi_mi(a.parent):\n", "            if False:\n"),
    # C — PBE tipe bakmaz (src + ui5.yaml olan her dizin library sayılır)
    "--mutasyon-pbe-tip-yok": (PBE, '        if tip is not None:\n            return tip == "library"\n',
                               "        return True\n"),
    # C — tipi okunamayan library'de yapısal işaret yok (fail-open)
    "--mutasyon-pbe-yapisal-yok": (PBE, '    return any((app / LIB_KAYNAK).rglob(".library"))\n', "    return False\n"),
    # C — kaynak kökü ns dizinine inmez (exclude src'ye göre kıyaslanır)
    "--mutasyon-pbe-ns-kok-yok": (PBE, "                    kaynak = _sade(ns)\n", "                    pass\n"),
    # C — ns kökü DIŞINDAKİ src dosyası kapıda kalır (src kökü, damgalanamaz komut — Flat build onu dağıtmaz)
    "--mutasyon-ns-disi-kapida": (PBE, "                        return None\n                    kaynak = _sade(ns)\n",
                                  "                        break\n                    kaynak = _sade(ns)\n"),
    # D — geri kurmada library-preload kalır
    "--mutasyon-fus-lib-preload-kalir": (FUS, ' or (lib and rel in (LIB_PRELOAD, LIB_PRELOAD + ".map")):\n', ":\n"),
    # D — library build ürünleri YALNIZ-CANLI kalır (kalıcı kilit)
    "--mutasyon-fus-lib-urun-yok": (FUS, "            if kutuphane and rel in LIB_BUILD_URUNLERI and KUTUPHANE_TANIM in yerel:\n",
                                    "            if False:\n"),
    # D — build ürünü sayımı library/.library şartına bakmaz
    "--mutasyon-fus-lib-urun-sartsiz": (FUS, "            if kutuphane and rel in LIB_BUILD_URUNLERI and KUTUPHANE_TANIM in yerel:\n",
                                        "            if rel in LIB_BUILD_URUNLERI:\n"),
    # D — paket haritası sondadan muaf değil (library'de sahte sapma)
    "--mutasyon-fus-lib-harita": (FUS, '        if lib and rel == LIB_PRELOAD + ".map":', '        if False:'),
    # D — --damgala yalnız `webapp` adlı kökü kabul eder (eski kural)
    "--mutasyon-fus-damga-webapp": (FUS, "            app = pbe.kaynak_kokunden_uygulama(yerel_kok, REPO)\n",
                                    "            app = pbe.uygulama_coz(yerel_kok / \"_\", REPO)[0] "
                                    "if yerel_kok.name.lower() == pbe.WEBAPP and pbe.uygulama_coz(yerel_kok / \"_\", REPO) else None\n"),
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

KUM = Path(tempfile.mkdtemp(prefix="ui5_lib_")).resolve()

# ── YAZMA KALKANI: TEMP kökü dışına her yazma/silme PermissionError + KACAK (namespace_tesisat deseni) ──
_IZINLI = Path(tempfile.gettempdir()).resolve()
KACAK: list = []


def _izinli(p) -> bool:
    try:
        Path(os.fspath(p)).resolve().relative_to(_IZINLI)
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
    for ad in ("makedirs", "mkdir", "remove", "unlink", "rmdir", "rename", "replace"):
        asil = getattr(os, ad)

        def sar_os(yol, *a, _asil=asil, _ad=ad, **k):
            # POSIX shutil.rmtree (_rmtree_safe_fd) çocukları dir_fd'ye GÖRELİ adla siler (os.unlink("x.js", dir_fd=fd));
            # kök zaten rmtree sarmalayıcısında denetlendi ⇒ dir_fd'li çağrı cwd'ye göre çözülmez (CI #459: sahte KACAK)
            if k.get("dir_fd") is None:
                _kalkan("os." + _ad, yol)
            return _asil(yol, *a, **k)
        setattr(os, ad, sar_os)
    asil_rmtree = shutil.rmtree

    def rmtree(yol, *a, **k):
        _kalkan("rmtree", yol)
        return asil_rmtree(yol, *a, **k)
    shutil.rmtree = rmtree


_kalkan_kur()

os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)   # deploy_ui / source_drift kökü import anında okur
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
    import deploy_ui as D  # noqa: E402
    import verify_ui_static_assets as V  # noqa: E402
    import fetch_ui_source as F  # noqa: E402
    import _pbe_ui as P  # noqa: E402
    sys.stdout, sys.stderr = _o, _e
except Exception as exc:  # pragma: no cover
    sys.stdout, sys.stderr = _o, _e
    _dur(f"modül yüklenemedi: {type(exc).__name__}: {exc}")
for _m in (D, V, F, P):
    if SCRIPTS.resolve() not in Path(_m.__file__).resolve().parents:
        _dur(f"yanlış modül yüklendi: {_m.__file__} (beklenen {SCRIPTS} altı)")

SONUC: list[tuple[str, bool, str]] = []
ATLANAN: list[tuple[str, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), str(detay)[:400]))


# ───────────────────────── sahte ağ / build / deploy (SAP'ye dokunulmaz) ─────────────────────────
CONN = ("https://sahte.invalid", "kullanici", "parola", "100")
BUILD: dict[str, object] = {}       # app dizini (str) → dist yazan çağrılabilir
CAGRI: list[tuple] = []             # ("build"|"deploy", app dizini) · ("fetch", bsp, dosya)
CANLI: dict[tuple[str, str], bytes] = {}


def _sahte_run(cmd, cwd, env):
    if "fiori deploy" in cmd:
        CAGRI.append(("deploy", str(cwd)))
        return (0, "Deployment Successful")
    if "npm run build" in cmd:
        CAGRI.append(("build", str(cwd)))
        yazici = BUILD.get(str(cwd))
        if yazici is not None:
            yazici()
        return (0, "build ok")
    return D._asil_run(cmd, cwd, env)


def _sahte_preload(base, user, pw, client, bsp, dosya=D.PRELOAD):
    CAGRI.append(("fetch", bsp, dosya))
    if (bsp, dosya) not in CANLI:
        raise OSError(f"sahte 404 {bsp}/{dosya}")
    return CANLI[(bsp, dosya)]


def _sahte_fetch(base, user, pw, client, bsp, rel_url):
    import urllib.error
    if (bsp, rel_url) not in CANLI:
        raise urllib.error.HTTPError(rel_url, 404, "Not Found", None, None)
    return CANLI[(bsp, rel_url)]


D._asil_run = D.run
D.run = _sahte_run
D.read_conn = lambda: CONN
D.fetch_live_preload = _sahte_preload
V.read_conn = lambda: CONN
V.fetch = _sahte_fetch


def cagir(modul, argv: list[str]) -> tuple:
    eski = sys.argv
    sys.argv = argv
    t, h = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(t), redirect_stderr(h):
            rc = modul.main() if modul is not F else F.main(argv[1:])
    except SystemExit as e:
        rc = e.code
    except Exception as e:  # çökme FAIL değildir ama hüküm de değildir → vektör düşer (rc metin)
        rc = f"COKTU {type(e).__name__}: {e}"
    finally:
        sys.argv = eski
    return rc, t.getvalue() + h.getvalue()


def yaz(kok: Path, dosyalar: dict) -> None:
    for rel, b in dosyalar.items():
        p = kok / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)


def crlf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


# ───────────────────────── sentetik library (jenerik: com.example.sd.reuse / ZSD001_UI_LIB) ─────────────────────────
NS = "com.example.sd.reuse"
NSY = NS.replace(".", "/")
LIB_BSP = "ZSD001_UI_LIB"
UI5_LIB = f'specVersion: "4.0"\nmetadata:\n  name: {NS}\ntype: library\n'.encode()
UI5_APP = b'specVersion: "4.0"\nmetadata:\n  name: com.example.sd.app\ntype: application\n'
DOT_LIBRARY = (f'<?xml version="1.0" encoding="UTF-8" ?>\n<library xmlns="http://www.sap.com/sap.ui.library.xsd" >\n'
               f"  <name>{NS}</name>\n  <vendor>Example</vendor>\n  <version>0.0.1</version>\n  <copyright></copyright>\n"
               "  <title>Ortak ekran kutuphanesi</title>\n  <documentation>Ortak kod</documentation>\n  <dependencies>\n"
               "    <dependency><libraryName>sap.ui.core</libraryName></dependency>\n"
               "    <dependency><libraryName>sap.m</libraryName></dependency>\n  </dependencies>\n"
               "  <appData>\n    <manifest xmlns=\"http://www.sap.com/ui5/buildext/manifest\">\n"
               "      <i18n>i18n/i18n.properties</i18n>\n    </manifest>\n  </appData>\n</library>\n").encode()
LIB_JS = (f'sap.ui.define(["sap/ui/core/Lib"], function (Lib) {{\n\t"use strict";\n\treturn Lib.init({{\n'
          f'\t\tname: "{NS}",\n\t\tversion: "0.0.1",\n\t\tdependencies: ["sap.ui.core", "sap.m"],\n'
          "\t\tnoLibraryCSS: true\n\t});\n});\n").encode()
SAYI_JS = b'sap.ui.define([], function () {\n\t"use strict";\n\treturn { bicimle: function (n) { return String(n); } };\n});\n'
FRAG = (b'<core:FragmentDefinition xmlns="sap.m" xmlns:core="sap.ui.core">\n\t<Text text="{i18n>bilgi}"/>\n'
        b"</core:FragmentDefinition>\n")
I18N_TR = "bilgi=Görünüm\n".encode()
I18N_TR_DIST = b"bilgi=G\\u00f6r\\u00fcn\\u00fcm\n"
I18N_KOK = b"bilgi=Gorunum\n"
SRC = {".library": DOT_LIBRARY, "library.js": LIB_JS, "util/Sayi.js": SAYI_JS,
       "fragment/Bilgi.fragment.xml": FRAG, "i18n/i18n.properties": I18N_KOK, "i18n/i18n_tr.properties": I18N_TR}


def harita(hedef: str, kaynak: str) -> bytes:
    return json.dumps({"version": 3, "file": hedef, "sources": [kaynak], "mappings": "AAAA"}).encode()


LIB_PRELOAD_B = (f"//@ui5-bundle {NSY}/library-preload.js\n"
                 f'sap.ui.predefine("{NSY}/library", ["sap/ui/core/Lib"],function(e){{"use strict";return e.init({{name:"{NS}"}})}});\n'
                 f'sap.ui.predefine("{NSY}/util/Sayi", [],function(){{"use strict";return{{bicimle:function(i){{return String(i)}}}}}});\n'
                 "sap.ui.require.preload({\n"
                 f"\t\"{NSY}/fragment/Bilgi.fragment.xml\":'<core:FragmentDefinition/>\\n',\n"
                 f"\t\"{NSY}/manifest.json\":'{{\"sap.app\":{{\"id\":\"{NS}\",\"type\":\"library\"}}}}'\n"
                 "});\n").encode()
LIB_MANIFEST = json.dumps({"_version": "1.21.0", "sap.app": {"id": NS, "type": "library", "resources": "resources.json"}},
                          indent=2).encode() + b"\n"
RESOURCES_JSON = b'{\n\t"_version": "1.1.0",\n\t"resources": []\n}\n'


def flat_dist(src: dict | None = None, preload: bytes = LIB_PRELOAD_B) -> dict:
    """Ölçülen Flat library build düzeni (@ui5/cli 4.0.61; gerçek build E1 aynı dosya kümesini doğrular)."""
    s = dict(SRC if src is None else src)
    return {".library": s[".library"], "library-dbg.js": s["library.js"], "library.js": b"min",
            "library.js.map": harita("library.js", "library-dbg.js"),
            "library-preload.js": preload,
            "library-preload.js.map": json.dumps({"version": 3, "file": "library-preload.js", "sections": []}).encode(),
            "util/Sayi-dbg.js": s["util/Sayi.js"], "util/Sayi.js": b"min",
            "util/Sayi.js.map": harita("Sayi.js", "Sayi-dbg.js"),
            "fragment/Bilgi.fragment.xml": s["fragment/Bilgi.fragment.xml"],
            "i18n/i18n.properties": s["i18n/i18n.properties"], "i18n/i18n_tr.properties": I18N_TR_DIST,
            "manifest.json": LIB_MANIFEST, "resources.json": RESOURCES_JSON}


def lib_kur(ui: Path, ad: str = "reuse_lib", *, ui5: bytes = UI5_LIB, bsp: str = LIB_BSP,
            src: dict | None = None, ns_yolu: str = NSY) -> Path:
    d = ui / ad
    yaz(d / "src" / ns_yolu, SRC if src is None else src)
    (d / "ui5.yaml").write_bytes(ui5)
    (d / "ui5-deploy.yaml").write_bytes(
        (f"specVersion: '4.0'\nbuilder:\n  customTasks:\n    - name: deploy-to-abap\n      afterTask: generateLibraryPreload\n"
         f"      configuration:\n        app:\n          name: {bsp}\n        exclude:\n          - /test/\n").encode())
    return d


def app_kur(ui: Path, ad: str, bsp: str, *, ui5: bytes | None = UI5_APP, ek: dict | None = None) -> Path:
    d = ui / ad
    yaz(d / "webapp", {"Component.js": SAYI_JS, "i18n/i18n.properties": I18N_KOK})
    if ui5 is not None:
        (d / "ui5.yaml").write_bytes(ui5)
    (d / "ui5-deploy.yaml").write_bytes(
        (f"specVersion: '4.0'\nbuilder:\n  customTasks:\n    - name: deploy-to-abap\n"
         f"      configuration:\n        app:\n          name: {bsp}\n").encode())
    if ek:
        yaz(d, ek)
    BUILD[str(d)] = lambda d=d: yaz(d / "dist", {"Component-preload.js": b"sap.ui.require.preload({});\n"})
    return d


def dist_yazici(d: Path, dosyalar: dict):
    def _yaz():
        if (d / "dist").exists():
            shutil.rmtree(d / "dist")
        yaz(d / "dist", dosyalar)
    return _yaz


def cagri_kumesi(tur: str) -> list:
    return [c for c in CAGRI if c[0] == tur]


UI = KUM / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui_lib"

# ════════════════════════════════ Z0 — kalkan sondası ════════════════════════════════
_kok_sonda = Path(Path(KUM).anchor) / "ui5_lib_kalkan_sondasi.txt"
try:
    _kok_sonda.write_bytes(b"x")
    kontrol("Z0 yazma kalkanı TEMP dışı yazmayı engeller", False, f"{_kok_sonda} YAZILDI")
except PermissionError:
    kontrol("Z0 yazma kalkanı TEMP dışı yazmayı engeller", bool(KACAK), repr(KACAK[-1:]))
KACAK.clear()

# ════════════════════════════════ A — deploy_ui ════════════════════════════════
LIB = lib_kur(UI)
BUILD[str(LIB)] = dist_yazici(LIB, flat_dist())
CANLI[(LIB_BSP, D.LIB_PRELOAD)] = crlf(LIB_PRELOAD_B)
CAGRI.clear()
rc, out = cagir(D, ["deploy_ui.py", "--app", "reuse_lib", "--ui-root", str(UI)])
kontrol("A1 AYIRT EDİCİ: Flat library → deploy + canlı library-preload.js doğrulaması, rc 0",
        rc == 0 and ("fetch", LIB_BSP, D.LIB_PRELOAD) in CAGRI and cagri_kumesi("deploy")
        and "CANLI==dist" in out and "library-preload == build" in out, f"rc={rc} cagri={CAGRI} out={out[-300:]!r}")

BUILD[str(LIB)] = dist_yazici(LIB, {f"resources/{NSY}/{k}": v for k, v in flat_dist().items()})
CAGRI.clear()
rc, out = cagir(D, ["deploy_ui.py", "--app", "reuse_lib", "--ui-root", str(UI)])
kontrol("A2 AYIRT EDİCİ: Namespace dist (dist/resources/) → deploy KOŞMAZ, rc 1, Flat yönlendirmesi",
        rc == 1 and not cagri_kumesi("deploy") and "--output-style Flat" in out and "deploy KOŞMADI" in out,
        f"rc={rc} cagri={CAGRI} out={out[-400:]!r}")

BUILD[str(LIB)] = dist_yazici(LIB, flat_dist())
CANLI[(LIB_BSP, D.LIB_PRELOAD)] = crlf(LIB_PRELOAD_B.replace(b"String(i)", b"String(i+1)"))
CAGRI.clear()
rc, out = cagir(D, ["deploy_ui.py", "--app", "reuse_lib", "--ui-root", str(UI), "--verify-only"])
kontrol("A3 library --verify-only: canlı library-preload farklı → STALE, rc 1, deploy YOK",
        rc == 1 and "STALE" in out and not cagri_kumesi("deploy") and ("fetch", LIB_BSP, D.LIB_PRELOAD) in CAGRI,
        f"rc={rc} out={out[-300:]!r}")
CANLI[(LIB_BSP, D.LIB_PRELOAD)] = crlf(LIB_PRELOAD_B)

UIA = KUM / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui"
APP = app_kur(UIA, "app1", "ZSD001_APP1")
CANLI[("ZSD001_APP1", D.PRELOAD)] = b"sap.ui.require.preload({});\r\n"
APP_ESKI = app_kur(UIA, "app_eski", "ZSD001_APP2", ui5=None)
CANLI[("ZSD001_APP2", D.PRELOAD)] = b"sap.ui.require.preload({});\r\n"
CAGRI.clear()
rc, out = cagir(D, ["deploy_ui.py", "--apps", "app1,app_eski", "--ui-root", str(UIA)])
kontrol("A4 KONTROL GRUBU: uygulama (type application + ui5.yaml'sız) → Component-preload.js, rc 0, özet eski metin",
        rc == 0 and ("fetch", "ZSD001_APP1", D.PRELOAD) in CAGRI and ("fetch", "ZSD001_APP2", D.PRELOAD) in CAGRI
        and "(canlı Component-preload == build çıktısı)." in out and "library" not in out.split("=== SONUÇ ===")[-1],
        f"rc={rc} cagri={CAGRI} out={out[-300:]!r}")

LIB_BOZUK = lib_kur(UI, "lib_bozuk", ui5=b"type: library\n  : : [\n", bsp="ZSD001_UI_LIB2")
BUILD[str(LIB_BOZUK)] = dist_yazici(LIB_BOZUK, flat_dist())
CAGRI.clear()
rc, out = cagir(D, ["deploy_ui.py", "--app", "lib_bozuk", "--ui-root", str(UI)])
kontrol("A5 FAIL-CLOSED: tipi okunamayan library → uygulama yolu, deploy KOŞMAZ, '.library var' ipucu",
        rc == 1 and not cagri_kumesi("deploy") and "Component-preload.js yok" in out and ".library var" in out,
        f"rc={rc} out={out[-300:]!r}")

# A6 — tip belgesi seçimi (@ui5/project Module.js: loadAll, kind yoksa project, tam 1 project belgesi)
# Beklenen değerler KAHİN ölçümüdür (@ui5/project 4.0.17 graphFromPackageDependencies().getRoot().getType(),
# 2026-11-27; None = @ui5/project HATA). E3 aynı tabloyu CLI varsa gerçek @ui5/project'e karşı yeniden ölçer.
_TIP_ADI = b'specVersion: "4.0"\nmetadata:\n  name: com.example.k\n'
TIP_VAKALARI = (
    ("duz_library", _TIP_ADI + b"type: library\n", "library"),
    ("duz_application", _TIP_ADI + b"type: application\n", "application"),
    ("tirnak_yorum", _TIP_ADI + b'type: "library"   # yorum\n', "library"),
    ("bom_crlf", b"\xef\xbb\xbf" + (_TIP_ADI + b"type: library\n").replace(b"\n", b"\r\n"), "library"),
    ("akis_bicimi", b'{specVersion: "4.0", metadata: {name: com.example.k}, type: library}\n', "library"),
    ("ext_once", b"specVersion: '4.0'\nkind: extension\ntype: task\nmetadata:\n  name: ornek-gorev\ntask:\n"
                 b"  path: t.js\n---\n" + _TIP_ADI + b"type: library\n", "library"),
    ("kind_project", b"kind: project\n" + _TIP_ADI + b"type: library\n", "library"),
    ("iki_proje", _TIP_ADI + b"type: library\n---\n" + _TIP_ADI + b"type: application\n", None),
    ("tipsiz", _TIP_ADI, None),
    ("yinelenen_type", _TIP_ADI + b"type: library\ntype: application\n", None),
    ("buyuk_harf", _TIP_ADI + b"type: Library\n", None),
    ("tema_lib", _TIP_ADI + b"type: theme-library\n", "theme-library"),
    ("liste_belge", b"- a\n- b\n---\n" + _TIP_ADI + b"type: library\n", None),
    ("bos_belge_once", b"---\n---\n" + _TIP_ADI + b"type: library\n", None),
    ("sonda_ayrac", _TIP_ADI + b"type: library\n---\n", None),   # sondaki `---` boş belge açar → şema HATASI
)
_tipler = {}
for ad, icerik, beklenen in TIP_VAKALARI:
    dd = KUM / "tip" / ad
    yaz(dd, {"ui5.yaml": icerik})
    _tipler[ad] = (D.proje_tipi(dd)[0], beklenen)
kontrol(f"A6 proje_tipi ↔ KAHİN tablosu ({len(TIP_VAKALARI)} vaka: belge seçimi · yinelenen anahtar · şema dışı tip · "
        "eşleme olmayan belge · tırnak/yorum/BOM/CRLF/akış biçimi)",
        all(g == b for g, b in _tipler.values()), repr({k: v for k, v in _tipler.items() if v[0] != v[1]}))


# A7 — changed_apps (gerçek git deposu kumda)
def git(*a):
    return subprocess.run(["git", "-C", str(KUM), *a], capture_output=True, text=True)


UIG = KUM / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui_git"
LIBG = lib_kur(UIG, "reuse_lib")
APPG = app_kur(UIG, "app1", "ZSD001_APP4")
APPSRC = app_kur(UIG, "app_src", "ZSD001_APP5", ek={"src/helper.js": b"x\n"})
git("init", "-q")
git("config", "user.email", "t@example.com")
git("config", "user.name", "test")
git("config", "core.autocrlf", "false")
git("add", "-A")
git("commit", "-q", "-m", "ilk")
git("commit", "-q", "--allow-empty", "-m", "iki")
(LIBG / "src" / NSY / "util" / "Sayi.js").write_bytes(SAYI_JS + b"// degisti\n")
(APPSRC / "src" / "helper.js").write_bytes(b"y\n")
lst, hatalar = D.changed_apps(UIG)
kontrol("A7 changed_apps: library src değişikliği listede, src'li UYGULAMA listede DEĞİL",
        lst == ["reuse_lib"] and not hatalar, f"liste={lst} hata={hatalar}")
(APPG / "webapp" / "Component.js").write_bytes(SAYI_JS + b"// degisti\n")
lst, hatalar = D.changed_apps(UIG)
kontrol("A8 KONTROL GRUBU: webapp değişikliği eskisi gibi listede",
        lst == ["app1", "reuse_lib"] and not hatalar, f"liste={lst} hata={hatalar}")

# A9 — --all library'yi kendi ui-root'unda deployable sayar
UIALL = KUM / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui_all"
LIBALL = lib_kur(UIALL, "reuse_lib", bsp="ZSD001_UI_LIB4")
BUILD[str(LIBALL)] = dist_yazici(LIBALL, flat_dist())
CAGRI.clear()
rc, out = cagir(D, ["deploy_ui.py", "--all", "--ui-root", str(UIALL), "--dry-run"])
kontrol("A9 --all (library tek başına ui-root'ta) → 1 deployable, dry-run build OK, deploy YOK",
        rc == 0 and "1 deployable app: reuse_lib" in out and not cagri_kumesi("deploy"), f"rc={rc} out={out[-300:]!r}")

# ════════════════════════════════ B — verify_ui_static_assets ════════════════════════════════
BUILD[str(LIB)] = dist_yazici(LIB, flat_dist())
BUILD[str(LIB)]()
for rel in ("i18n/i18n.properties", "i18n/i18n_tr.properties"):
    CANLI[(LIB_BSP, rel)] = crlf(flat_dist()[rel])
rc, out = cagir(V, ["verify.py", "--app", "reuse_lib", "--ui-root", str(UI), "--subdir", "i18n"])
kontrol(f"B1 AYIRT EDİCİ: library i18n — kaynak src/{NSY}, dist Flat, \\uXXXX dönüşümü beklenen → rc 0",
        rc == 0 and "2/2 dosya canlıda AYNI" in out and "taban=dist" in out and "build dönüşümü BEKLENEN (1)" in out
        and f"src/{NSY} baytı" in out, f"rc={rc} out={out[-500:]!r}")

(LIB / "src" / NSY / "i18n" / "i18n_tr.properties").write_bytes("bilgi=Görünüm2\n".encode())
rc, out = cagir(V, ["verify.py", "--app", "reuse_lib", "--ui-root", str(UI), "--subdir", "i18n"])
kontrol("B2 library kaynakta build edilmemiş değişiklik → KAYNAK FARKI, rc 1",
        rc == 1 and "KAYNAK FARKI : i18n_tr.properties" in out and f"src/{NSY}'te build" in out,
        f"rc={rc} out={out[-400:]!r}")
(LIB / "src" / NSY / "i18n" / "i18n_tr.properties").write_bytes(I18N_TR)

yaz(LIB / "dist", {f"resources/{NSY}/.library": DOT_LIBRARY})
rc, out = cagir(V, ["verify.py", "--app", "reuse_lib", "--ui-root", str(UI), "--subdir", "i18n"])
kontrol("B3 library Namespace dist → FAIL, ölçüm KOŞMAZ", rc == 1 and "Namespace düzeninde" in out,
        f"rc={rc} out={out[-300:]!r}")
shutil.rmtree(LIB / "dist" / "resources")

LIB2 = lib_kur(UI, "lib_iki", bsp="ZSD001_UI_LIB3")
yaz(LIB2 / "src" / "com" / "example" / "baska", {".library": DOT_LIBRARY})
rc, out = cagir(V, ["verify.py", "--app", "lib_iki", "--ui-root", str(UI), "--subdir", "i18n"])
kontrol("B4 iki .library → kaynak kökü çözülemedi FAIL", rc == 1 and "2 .library" in out, f"rc={rc} out={out[-300:]!r}")

yaz(APP / "webapp", {"i18n/i18n_tr.properties": I18N_TR})
yaz(APP / "dist", {"i18n/i18n_tr.properties": I18N_TR_DIST, "i18n/i18n.properties": I18N_KOK})
CANLI[("ZSD001_APP1", "i18n/i18n_tr.properties")] = crlf(I18N_TR_DIST)
CANLI[("ZSD001_APP1", "i18n/i18n.properties")] = crlf(I18N_KOK)
rc, out = cagir(V, ["verify.py", "--app", "app1", "--ui-root", str(UIA), "--subdir", "i18n"])
kontrol("B5 KONTROL GRUBU: uygulama çıktısı etiketi 'webapp' (değişmedi), rc 0",
        rc == 0 and "webapp baytı ≠ dist" in out and "src/" not in out, f"rc={rc} out={out[-300:]!r}")

# ════════════════════════════════ C — PULL-BEFORE-EDIT UI eklentisi ════════════════════════════════
r = P.sinifla(LIB / "src" / NSY / "util" / "Sayi.js", KUM)
kontrol("C1 AYIRT EDİCİ: library src dosyası kapıda; komut --karsilastir <lib>/src/<ns>",
        isinstance(r, dict) and r.get("nesne") == LIB_BSP
        and f'--karsilastir "SOURCE_CODES/SD/ZSD001_CLC/ui_lib/reuse_lib/src/{NSY}" --damgala' in r.get("komut", ""),
        repr(r))
r = P.sinifla(LIB / "src" / NSY / "test" / "x.js", KUM)
kontrol("C2 deploy-exclude (/test/) ns KÖKÜNE göre muaf → None", r is None, repr(r))
r = P.sinifla(APPSRC / "src" / "helper.js", KUM)
kontrol("C3 KONTROL GRUBU: src'li UYGULAMA (type application) kapıda DEĞİL", r is None, repr(r))
r = P.sinifla(LIB_BOZUK / "src" / NSY / "library.js", KUM)
kontrol("C4 FAIL-CLOSED: tipi okunamayan library (.library var) kapıda", isinstance(r, dict), repr(r))
LIBDOC = lib_kur(KUM / "docs" / "ui", "reuse_lib")
r = P.sinifla(LIBDOC / "src" / NSY / "library.js", KUM)
kontrol("C5 kök segment dışındaki library → None", r is None, repr(r))
yaz(LIB / "test", {"unit.js": b"x\n"})
r = P.sinifla(LIB / "test" / "unit.js", KUM)
kontrol("C6 <lib>/test/** (src dışı) → None", r is None, repr(r))
r = P.sinifla(APP / "webapp" / "Component.js", KUM)
kontrol("C7 KONTROL GRUBU: webapp komutu aynen --karsilastir <app>/webapp",
        isinstance(r, dict) and '--karsilastir "SOURCE_CODES/SD/ZSD001_CLC/ui/app1/webapp" --damgala' in r.get("komut", ""),
        repr(r))
_c8 = (P.kaynak_kokunden_uygulama(LIB / "src" / NSY, KUM), P.kaynak_kokunden_uygulama(LIB / "src", KUM),
       P.kaynak_kokunden_uygulama(APP / "webapp", KUM))
kontrol("C8 kaynak_kokunden_uygulama: ns kökü → lib · src → None · webapp → app",
        _c8 == (LIB, None, APP), repr(_c8))
yaz(LIB / "src", {"disari.js": b"x\n", "com/example/komsu.js": b"y\n"})
_c9 = (P.sinifla(LIB / "src" / "disari.js", KUM), P.sinifla(LIB / "src" / "com" / "example" / "komsu.js", KUM))
kontrol("C9 ns kökü DIŞINDAKİ src dosyası (Flat build dağıtmaz — ölçüldü) → None", _c9 == (None, None), repr(_c9))
r = P.sinifla(LIB / "src" / "lib" / ".." / NSY / "util" / "Sayi.js", KUM)
kontrol("C9b `..` ile ns'ye dönen yol yine kapıda (sadeleşmiş yolda karar)", isinstance(r, dict), repr(r))
if os.name == "nt":
    _harf = Path(str(LIB / "src") + "/" + NSY.upper()) / "util" / "Sayi.js"
    r = P.sinifla(_harf, KUM)
    kontrol("C10 Windows: ns segmenti farklı harfle verilen yol yine kapıda (WindowsPath eşitliği)", isinstance(r, dict), repr(r))
else:
    ATLANAN.append(("C10 ns harf duyarlılığı", "POSIX: farklı harfli yol ayrı dizindir"))

# ════════════════════════════════ D — fetch_ui_source ════════════════════════════════
CANLI_LIB = {k: (crlf(v) if F.metin_mi(k) else v) for k, v in flat_dist().items()}
kaynak, atilan = F.geri_kur(CANLI_LIB)
kontrol("D1 geri kurma: library-preload.js(.map) atılır, library-dbg.js → library.js",
        "library-preload.js" not in kaynak and "library-preload.js.map" not in kaynak
        and kaynak.get("library.js") == LIB_JS and ("library-preload.js", "preload") in atilan, repr(sorted(kaynak)))
app_zip = {"Component-preload.js": b"x", "library-preload.js": b"y", "library-preload.js.map": b"{}"}
k_app, _ = F.geri_kur(app_zip)
kontrol("D2 KONTROL GRUBU: kökte .library YOKSA library-preload kalır, harita sondası eskisi gibi",
        "library-preload.js" in k_app and bool(F.harita_sondasi(app_zip)) and not F.harita_sondasi(CANLI_LIB),
        f"{sorted(k_app)} sonda_app={F.harita_sondasi(app_zip)} sonda_lib={F.harita_sondasi(CANLI_LIB)}")
s_lib = {r: s for r, s, _d, _f in F.karsilastir(kaynak, SRC, kutuphane=True)}
s_app = {r: s for r, s, _d, _f in F.karsilastir(kaynak, SRC, kutuphane=False)}
s_tanimsiz = {r: s for r, s, _d, _f in F.karsilastir(kaynak, {k: v for k, v in SRC.items() if k != ".library"},
                                                       kutuphane=True)}
kontrol("D3 library build ürünleri (manifest/resources.json) BUILD; uygulama ve .library'siz yerelde YALNIZ-CANLI",
        s_lib.get("manifest.json") == F.BUILD and s_lib.get("resources.json") == F.BUILD
        and s_app.get("manifest.json") == F.YALNIZ_CANLI and s_tanimsiz.get("manifest.json") == F.YALNIZ_CANLI
        and set(s_lib.values()) <= {F.AYNI, F.BUILD}, f"lib={s_lib} app={s_app} tanimsiz={s_tanimsiz}")

ZIP = KUM / "canli_lib.zip"
_b = io.BytesIO()
with zipfile.ZipFile(_b, "w") as z:
    for k, v in CANLI_LIB.items():
        z.writestr(k, v)
ZIP.write_bytes(_b.getvalue())
F.zip_indir = lambda bsp, conn: (ZIP.read_bytes(), {"Name": bsp, "Package": "ZSD001_CLC", "Description": "x"})
F.baglanti = lambda: CONN
rc, out = cagir(F, ["fetch_ui_source.py", "--app-dir", str(LIB), "--karsilastir", str(LIB / "src" / NSY),
                    "--damgala", "--session", "ui5libtest"])
kontrol("D4 AYIRT EDİCİ: --damgala <lib>/src/<ns> → yalnız AYNI/BUILD, damga YAZILDI, rc 0",
        rc == 0 and "seans-taze damgalandı" in out and "GERCEK-FARK=0" in out and "YALNIZ-CANLI=0" in out,
        f"rc={rc} out={out[-700:]!r}")
rc, out = cagir(F, ["fetch_ui_source.py", "--app-dir", str(LIB), "--karsilastir", str(LIB / "src"),
                    "--damgala", "--session", "ui5libtest"])
kontrol("D5 --damgala <lib>/src (ns kökü değil) → KULLANIM rc 2", rc == 2 and "[KULLANIM]" in out,
        f"rc={rc} out={out[-300:]!r}")
rc, out = cagir(F, ["fetch_ui_source.py", "--zip", str(ZIP), "--eslik"])
kontrol("D6 --eslik library zip → ÖLÇÜLEMEDİ rc 2 (library eşliği yok, açık mesaj)",
        rc == 2 and "UI5 library BSP'si" in out, f"rc={rc} out={out[-300:]!r}")

# ════════════════════════════════ T — library şablonu (playbook/templates/ui5-freestyle/library) ════════════════════════════════
SABLON = KOK / "playbook" / "templates" / "ui5-freestyle" / "library"
_pkg = json.loads((SABLON / "package.json").read_bytes().decode("utf-8"))
SABLON_BUILD = _pkg.get("scripts", {}).get("build", "").split()
_dep = (SABLON / "ui5-deploy.yaml").read_bytes().decode("utf-8")
_dep_kod = "".join(s for s in _dep.splitlines(True) if not s.lstrip().startswith("#"))   # yorum satırları hariç
kontrol("T1 şablon: build Flat + generateResourcesJson · deploy afterTask library görevi (generateCachebusterInfo DEĞİL)"
        " · iki yaml tipi library",
        SABLON_BUILD[:2] == ["ui5", "build"] and "--output-style" in SABLON_BUILD
        and SABLON_BUILD[SABLON_BUILD.index("--output-style") + 1] == "Flat"
        and "generateResourcesJson" in SABLON_BUILD
        and "afterTask: generateLibraryPreload" in _dep_kod and "afterTask: generateCachebusterInfo" not in _dep_kod
        and D.proje_tipi(SABLON)[0] == "library",
        f"build={SABLON_BUILD} tip={D.proje_tipi(SABLON)}")
yaz(KUM / "sablon_kopya", {"ui5-deploy.yaml": _dep.replace("<BSP_ADI>", "ZSD001_UI_LIB5").encode("utf-8")})
kontrol("T2 şablon ui5-deploy.yaml'dan BSP adı çözülür (yer tutucu dolunca)",
        D.bsp_name(KUM / "sablon_kopya") == "ZSD001_UI_LIB5", repr(D.bsp_name(KUM / "sablon_kopya")))

# ════════════════════════════════ E — gerçek ui5 build (CLI varsa) ════════════════════════════════
UI5_CLI = os.environ.get("UI5_CLI") or shutil.which("ui5")
if not UI5_CLI:
    ATLANAN.append(("E1/E2 gerçek ui5 build", "ui5 CLI yok (UI5_CLI env ya da PATH'te `ui5`)"))
else:
    EL = KUM / "gercek" / "lib"
    yaz(EL / "src" / NSY, SRC)
    (EL / "ui5.yaml").write_bytes((SABLON / "ui5.yaml").read_bytes().replace(b"com.example.alan.ortak", NS.encode()))
    (EL / "package.json").write_bytes(json.dumps({"name": NS, "version": "0.0.1", "private": True}).encode())
    komut = ["node", UI5_CLI] if UI5_CLI.endswith((".cjs", ".js")) else [UI5_CLI]

    def ui5_build(dest: str, *ek: str):
        return subprocess.run([*komut, "build", "--config=ui5.yaml", "--clean-dest", "--dest", str(EL / dest), *ek],
                              cwd=str(EL), capture_output=True, text=True, encoding="utf-8", errors="replace",
                              shell=(os.name == "nt" and len(komut) == 1))
    # E1 ŞABLONUN build komutunu koşar (`ui5 build` sonrası argümanlar; --dest dist dahil) — şablon ↔ ölçüm bağı
    r1 = subprocess.run([*komut, *SABLON_BUILD[1:]], cwd=str(EL), capture_output=True, text=True, encoding="utf-8",
                        errors="replace", shell=(os.name == "nt" and len(komut) == 1))
    if r1.returncode != 0:
        kontrol("E1 gerçek Flat build", False, (r1.stdout + r1.stderr)[-400:])
    else:
        dist_d = F.dizin_oku(EL / "dist")
        beklenen = set(flat_dist())
        canli = {k: (crlf(v) if F.metin_mi(k) else v) for k, v in dist_d.items()}
        kgk, _ = F.geri_kur(canli)
        siniflar = {r: s for r, s, _d, _f in F.karsilastir(kgk, F.dizin_oku(EL / "src" / NSY), kutuphane=True)}
        kontrol("E1 GERÇEK BUILD: Flat çıktı kümesi ölçülen düzen + geri kurma ↔ src YALNIZ AYNI/BUILD + engel yok",
                set(dist_d) == beklenen and set(siniflar.values()) <= {F.AYNI, F.BUILD} and not F.harita_sondasi(canli)
                and D.kutuphane_dist_engeli(EL / "dist") == "",
                f"fark={sorted(set(dist_d) ^ beklenen)} sinif={siniflar} sonda={F.harita_sondasi(canli)}")
    r2 = ui5_build("dist_ns")
    kontrol("E2 GERÇEK BUILD: Default (Namespace) çıktı deploy engeline takılır",
            r2.returncode == 0 and "--output-style Flat" in D.kutuphane_dist_engeli(EL / "dist_ns")
            and (EL / "dist_ns" / "resources" / NSY / "library-preload.js").is_file(),
            f"rc={r2.returncode} engel={D.kutuphane_dist_engeli(EL / 'dist_ns')!r}")

    # E3 KAHİN: TIP_VAKALARI'nı GERÇEK @ui5/project'e sor (CLI'ın yanındaki kopya) — A6'daki beklenen tablo bayatlamasın
    _cli = Path(UI5_CLI).resolve()
    _proje = next((a for a in (_cli.parents[1] / "node_modules" / "@ui5" / "project", _cli.parents[2] / "project")
                   if (a / "lib" / "graph" / "graph.js").is_file()), None)
    if _proje is None:
        ATLANAN.append(("E3 KAHİN @ui5/project", f"{_cli} yanında @ui5/project bulunamadı"))
    else:
        dizinler = []
        for ad, icerik, _b in TIP_VAKALARI:
            dd = KUM / "kahin" / ad
            yaz(dd, {"ui5.yaml": icerik, "package.json": json.dumps({"name": "k-" + ad.replace("_", "-"),
                                                                       "version": "0.0.1"}).encode(),
                     "src/com/example/k/.library": DOT_LIBRARY.replace(NS.encode(), b"com.example.k"),
                     "src/com/example/k/library.js": b"sap.ui.define([], function () {});\n",
                     "webapp/manifest.json": b'{"sap.app": {"id": "com.example.k", "type": "application"}}'})
            dizinler.append(str(dd))
        js = KUM / "kahin" / "kahin.cjs"
        js.write_bytes((
            "const path = require('path'); const {pathToFileURL} = require('url');\n"
            "(async () => {\n"
            "  const {graphFromPackageDependencies} = await import(pathToFileURL(path.join(process.argv[2], 'lib',"
            " 'graph', 'graph.js')).href);\n"
            "  const out = {};\n"
            "  for (const d of process.argv.slice(3)) {\n"
            "    try { out[path.basename(d)] = (await graphFromPackageDependencies({cwd: d})).getRoot().getType(); }\n"
            "    catch (e) { out[path.basename(d)] = null; }\n"
            "  }\n"
            "  console.log(JSON.stringify(out));\n"
            "})();\n").encode())
        r3 = subprocess.run(["node", str(js), str(_proje), *dizinler], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        try:
            kahin = json.loads((r3.stdout.strip().splitlines() or ["{}"])[-1])
        except ValueError:
            kahin = {}
        fark = {ad: (D.proje_tipi(KUM / "kahin" / ad)[0], kahin.get(ad, "YOK")) for ad, _i, _b in TIP_VAKALARI
                if D.proje_tipi(KUM / "kahin" / ad)[0] != kahin.get(ad, "YOK")}
        kontrol(f"E3 KAHİN: proje_tipi == @ui5/project getType() ({len(TIP_VAKALARI)} vaka, fark 0)",
                len(kahin) == len(TIP_VAKALARI) and not fark, f"fark={fark} stderr={r3.stderr[-300:]!r}")

# ════════════════════════════════ özet ════════════════════════════════
kontrol("Z1 kalkan: koşum boyunca TEMP dışı yazma denemesi yok", not KACAK, repr(KACAK[:3]))
gecen = sum(1 for _a, ok, _d in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         → {detay}"))
for ad, neden in ATLANAN:
    print(f"  [ATLA] {ad} — {neden}")
print(f"[KALKAN] TEMP dışı yazma denemesi: {len(KACAK)}")
print(f"\nui5_library_kipi: {gecen}/{len(SONUC)} {'PASS' if gecen == len(SONUC) else 'FAIL'}"
      + (f" · {len(ATLANAN)} ATLA (ölçülmedi)" if ATLANAN else ""))
sys.exit(0 if gecen == len(SONUC) else 1)

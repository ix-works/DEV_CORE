# -*- coding: utf-8 -*-
"""deploy_ui.py — Freestyle UI5 app'i BSP'ye GÜVENLİ deploy eder (build + deploy + CANLI doğrulama).

⛔ NEDEN VAR (2026-07-06 dersi): Yalın `fiori deploy --config ui5-deploy.yaml` build YAPMAZ —
   eski `dist/`'i archive edip "Deployment Successful" DER ama canlıya BAYAT içerik gider
   (abap-deploy-task "UI5 build result" = dist/ klasörü; güncel değilse stale). 3 tur FE
   deploy'u sessizce stale gitti, kullanıcı canlıda göremeyince yakalandı.
   → Bu script build'i GÖMER (atlanamaz) + deploy SONRASI canlı Component-preload.js'i
   yerel dist ile HASH-karşılaştırır ("Successful" mesajına güvenmez, içeriği kanıtlar).

Kanonik deploy yolu budur. Yalın `fiori deploy` PreToolUse guard ile BLOKLANIR (deploy_ui.py'ye
zorlar). Bkz. standards/03-coding-ui-fiori.md §2.4.1 + feedback_ui-deploy-noninteractive (madde 8).

Her app için sırayla (atlanamaz):
  1) ui5 build --clean-dest --dest dist            (BUILD ZORUNLU — dist tazelenir)
  2) dist/Component-preload.js → sha256 (local)
  3) npx fiori deploy --config ui5-deploy.yaml --yes   (env auth, .conn_adt'den)
  4) canlı GET .../<bsp>/Component-preload.js?cb=<ts> (no-cache) → sha256 (live)
  5) local == live ?  PASS : FAIL (STALE/CACHE — canlı ≠ dist)
     ⚠ Q281: `--verify-only`de fark YALNIZ preload string'lerindeki kaçışlı `\\r\\n` ise (içerik
     modül modül eşit) STALE sayılmaz, `[OK~]` ayrı kovasında basılır. Deploy kipinde katı kalır.

Kullanım:
    python scripts/deploy_ui.py --apps sip_se,dsk_se,fih_se
    python scripts/deploy_ui.py --app dsk_se
    python scripts/deploy_ui.py --all-changed          # git'e göre webapp'i (library: src'si) değişen app'ler
    python scripts/deploy_ui.py --apps sip_se --dry-run # build+doğrula plan, deploy YOK
    # --ui-root ile farklı paket: --ui-root <source_root>/SD/ZSD001_CLC/ui (varsayılan)

UI5 REUSE LIBRARY (`ui5.yaml` type: library, 2026-11-27): aynı akış, iki fark — doğrulanan dosya
`library-preload.js` ve build çıktısı `--output-style Flat` olmalı (dist kökü = BSP kökü; Namespace
düzeni deploy ÖNCESİ FAIL). Kaynak `<lib>/src/<ns-yolu>/`; `--all-changed` src değişikliğini YALNIZ
library dizininde sayar. Tip okunamazsa (PyYAML yok / belge hatası) uygulama yolu koşar → deploy
öncesi FAIL. Ayrıntı: `LIB_PRELOAD` bloğu + playbook/templates/ui5-freestyle/library/.
"""
import argparse
import base64
import hashlib
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[0]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten
# Issue #440: "müşteri adı mı" kararının TEK kaynağı (Z/Y + project.yaml customer_namespaces).
from utils.ad_politikasi import ad_namespace, musteri_adi_mi

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# D24: proje kökü env→cwd (junction'da __file__ DEV_CORE'a çözülür; .conn_adt /
# ui-root / git hedefi PROJE'dir — __file__-türetimi YASAK).
from utils.project_config import cfg as _cfg, project_root as _project_root
REPO = _project_root()
# B10/K12: varsayılan UI kökü PROJE-CONFIG'ten (project.yaml default_ui_root:
# "SOURCE_CODES/SD/<PKG>/ui"); yoksa --ui-root ZORUNLU (core paket VARSAYMAZ).
DEFAULT_UI_ROOT = _cfg("default_ui_root")  # None olabilir
PRELOAD = "Component-preload.js"

# ── UI5 reuse library (`type: library`) kipi (2026-11-27) ─────────────────────────────────────
# Uygulama (`type: application`) yolu DEĞİŞMEDİ; library yalnız `ui5.yaml` tipi `library` olan dizinde
# açılır. Ölçülen üç gerçek (@ui5/cli 4.0.61 · @sap/ux-ui5-tooling 1.30.0, fixture `ui5_library_kipi`):
#   ① library build çıktısı varsayılan (Namespace) düzende `dist/resources/<ns-yolu>/`'dadır;
#      `--output-style Flat` ile `dist/` köküne iner: `.library`, `library.js`, `library-preload.js`,
#      `manifest.json`, `i18n/`, alt klasörler — canlı SAP library BSP'sinin kök düzeniyle aynı.
#   ② deploy_ui'nin koştuğu `fiori deploy` CLI'ı build YAPMAZ ve `/resources/<ns>/` kırpması YAPMAZ:
#      `createDistWorkspace()` `<cwd>/dist`'i `/resources/fiori/cli/`e bağlar, arşiv o öneki kırpar ⇒
#      `dist/` OLDUĞU GİBİ yüklenir. Namespace düzenli dist BSP'ye `resources/<ns>/…` yükler (yanlış
#      kök, "Deployment Successful" yine basılır) ⇒ library kipinde deploy ÖNCESİ Flat düzen zorunlu.
#   ③ `afterTask: generateCachebusterInfo` library görev listesinde yok: `ui5 build --config
#      ui5-deploy.yaml` "Could not find task generateCachebusterInfo" ile düşer (CLI yolu bu alanı
#      okumaz; şablon `generateLibraryPreload` kullanır — playbook/templates/ui5-freestyle/library/).
LIB_PRELOAD = "library-preload.js"
TIP_UYGULAMA, TIP_KUTUPHANE = "application", "library"
UI5_YAML = "ui5.yaml"
KUTUPHANE_KAYNAK = "src"
KUTUPHANE_TANIM = ".library"


def proje_tipi(app_dir: Path) -> tuple:
    """`ui5.yaml` → (tip, açıklama). Tip @ui5/project'in seçtiği belgedendir (Module.js 4.0.17:
    `jsyaml.loadAll` → `kind` yoksa "project" · birden çok project belgesi HATA): TEK `kind: project`
    belgesinin `type`'ı. Okunamazsa (dosya yok / PyYAML yok / belge hatası / 0 ya da >1 project
    belgesi / tip metin değil / tip @ui5/project şemasında yok / YİNELENEN anahtar — js-yaml gibi) tip None
    + neden. KAHİN: @ui5/project 4.0.17 `graphFromPackageDependencies().getRoot().getType()` ile
    kıyaslandı (2026-11-27, 22 vaka, fark 1): tek ayrışma @ui5/project'in TİP DIŞI şema doğrulamasıdır
    (ör. `metadata.name` deseni) — orada build zaten düşer; tip burada şemaya bakılmadan okunur.

    ⛔ Karar kuralı (çağıranlar): YALNIZ tip == "library" library kipini açar; None dahil her şey
    bugünkü UYGULAMA yoludur (davranış değişmez). Library'nin tipi okunamazsa uygulama yolu
    `Component-preload.js` ister ve deploy ÖNCESİ FAIL verir (fail-closed)."""
    y = Path(app_dir) / UI5_YAML
    if not y.is_file():
        return None, f"{UI5_YAML} yok"
    try:
        import yaml as _yaml
    except Exception:                                   # noqa: BLE001
        return None, "PyYAML yok"
    try:
        belgeler = list(_yaml.load_all(y.read_text(encoding="utf-8-sig"), Loader=_yinelenen_anahtar_yukleyici(_yaml)))
    except Exception as exc:                            # noqa: BLE001
        return None, f"{UI5_YAML} ayrıştırılamadı ({type(exc).__name__})"
    if not all(isinstance(b, dict) for b in belgeler):
        # @ui5/project her belgeyi şemayla doğrular: boş (`---\n---`) ya da liste belge "Configuration must be
        # of type 'object'" HATASI (KAHİN ölçümü 2026-11-27) ⇒ tip okunamaz.
        return None, f"{UI5_YAML}'da eşleme (object) olmayan belge var"
    projeler = [b for b in belgeler if (b.get("kind") or "project") == "project"]
    if len(projeler) != 1:
        return None, f"{UI5_YAML}'da {len(projeler)} 'kind: project' belgesi (tam 1 beklenir)"
    tip = projeler[0].get("type")
    if not isinstance(tip, str):
        return None, f"{UI5_YAML} project belgesinde `type` yok"
    if tip not in UI5_PROJE_TIPLERI:
        return None, f"{UI5_YAML} `type: {tip}` @ui5/project şemasında yok ({', '.join(UI5_PROJE_TIPLERI)})"
    return tip, ""


# @ui5/project 4.0.17 `lib/validation/schema/specVersion/kind/project.json` `type.enum` (ölçüldü 2026-11-27).
# Şema dışı tip (`Library` gibi) @ui5/project'te "Invalid ui5.yaml configuration" HATASIDIR ⇒ None (KAHİN eşliği).
UI5_PROJE_TIPLERI = ("application", "library", "theme-library", "module")


def _yinelenen_anahtar_yukleyici(_yaml):
    """PyYAML SafeLoader + YİNELENEN ANAHTAR = HATA. @ui5/project js-yaml ile okur ve yinelenen anahtarda
    "Failed to parse configuration" verir; PyYAML ise sessizce SONUNCUYU alır (ölçüldü 2026-11-27, KAHİN:
    `type: library` + `type: application` → PyYAML application, @ui5/project HATA). Eşlik için reddedilir."""
    class _Yukleyici(_yaml.SafeLoader):
        pass

    def _esleme(loader, node, deep=False):
        anahtarlar = set()
        for k_node, _v in node.value:
            k = loader.construct_object(k_node, deep=deep)
            try:
                if k in anahtarlar:
                    raise _yaml.constructor.ConstructorError(None, None, f"yinelenen anahtar: {k!r}",
                                                              k_node.start_mark)
                anahtarlar.add(k)
            except TypeError:   # hash edilemeyen anahtar — SafeLoader'ın kendi hatasına bırak
                pass
        return loader.construct_mapping(node, deep=deep)
    _Yukleyici.add_constructor(_yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _esleme)
    return _Yukleyici


def kutuphane_mi(app_dir: Path) -> bool:
    return proje_tipi(app_dir)[0] == TIP_KUTUPHANE


def kutuphane_kaynak_koku(app_dir: Path) -> tuple:
    """Library kaynak kökü = `src/` altındaki TEK `.library` dosyasının dizini (`src/<ns-yolu>/`) →
    (Path|None, neden). Build'in `dist/` köküne (Flat) koyduğu ağaç budur."""
    src = Path(app_dir) / KUTUPHANE_KAYNAK
    if not src.is_dir():
        return None, f"{KUTUPHANE_KAYNAK}/ yok"
    adaylar = sorted(p.parent for p in src.rglob(KUTUPHANE_TANIM) if p.is_file())
    if len(adaylar) != 1:
        return None, f"{KUTUPHANE_KAYNAK}/ altında {len(adaylar)} {KUTUPHANE_TANIM} (tam 1 beklenir)"
    return adaylar[0], ""


def kutuphane_dist_engeli(dist: Path) -> str:
    """Library dist'i deploy edilebilir mi (Flat düzen)? "" = evet; aksi hâlde NEDEN (deploy KOŞMAZ)."""
    if (dist / "resources").is_dir():
        return ("dist/resources/ VAR — build Namespace düzeninde; `fiori deploy` dist'i OLDUĞU GİBİ yükler "
                "⇒ BSP'ye `resources/<ns>/…` gider (yanlış kök). package.json build script'ine "
                "`--output-style Flat` ekle (şablon: playbook/templates/ui5-freestyle/library/)")
    eksik = [a for a in (LIB_PRELOAD, KUTUPHANE_TANIM) if not (dist / a).is_file()]
    if eksik:
        return f"build sonrası dist/ kökünde {', '.join(eksik)} yok — library build çıktısı beklenmedik"
    return ""


def _conn_field(text: str, key: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(key) and "=" in s:
            return s.split("=", 1)[1].strip().replace("\r", "")
    return ""


def read_conn():
    """(.conn_adt) → (base_url, user, password, client). Yoksa hata."""
    conn = REPO / ".conn_adt"
    if not conn.exists():
        print(f"[FAIL] .conn_adt yok: {conn}", file=sys.stderr)
        sys.exit(1)
    t = conn.read_text(encoding="utf-8", errors="ignore")
    url = _conn_field(t, "ADT_SAP_URL").rstrip("/")
    return (
        url,
        _conn_field(t, "ADT_SAP_USER"),
        _conn_field(t, "ADT_SAP_PASSWORD"),
        _conn_field(t, "ADT_SAP_CLIENT") or "100",
    )


BSP_ADI_BEKLENEN = ("müşteri ad alanında BSP adı (app.name: Z/Y ya da project.yaml "
                    "customer_namespaces'te kayıtlı /<NS>/ ile başlayan)")
# PR #445 3. kapı (2026-11-15, lider kararı): satır regex'i yerine GERÇEK YAML ayrıştırıcı.
# Üç regex turu yakınsamadı (akış map içinde `app`, `? app` açık anahtar, alt ağaçtaki blok
# skaler/iç map, `name:ZAPP` boşluksuz, yinelenen anahtar…) — her turda kapı yeni bir biçim buldu.
# HEDEF = `fiori deploy`un OKUDUĞU yer. Ölçüldü (@sap/ux-ui5-tooling 1.25.0, dist/cli/index.cjs
# `readConfig`): `parseDocument(readFileSync(<config>, "utf8")).toJSON()` (eemeli `yaml`, pakete
# GÖMÜLÜ) → `builder.customTasks.find(e => e.name === "deploy-to-abap").configuration` → app.name.
# ⚠ `yaml` (2.8.3 ölçüldü) yinelenen anahtarda `errors=[DUPLICATE_KEY]` kaydeder ama `toJSON()`
# SONUNCUYU döndürür ve fiori `errors`a bakmaz ⇒ burada `errors` doluysa "" (fail-closed).
_DEPLOY_GOREVI = "deploy-to-abap"
_NODE_BETIGI = r"""
const fs = require('fs');
const [, yol, dizin] = process.argv;
let Y;
try { Y = require(require.resolve('yaml', { paths: [dizin] })); }
catch (e) { console.log(JSON.stringify({ durum: 'KUTUPHANE_YOK' })); process.exit(0); }
let s;
try {
  const d = Y.parseDocument(fs.readFileSync(yol, 'utf8'));
  if (d.errors && d.errors.length) {
    s = { durum: 'HATA', neden: d.errors.map(e => e.code || e.name).join(',') };
  } else {
    const j = d.toJSON();
    const g = j && j.builder && Array.isArray(j.builder.customTasks)
      ? j.builder.customTasks.find(e => e && e.name === 'deploy-to-abap') : undefined;
    const a = g && g.configuration && g.configuration.app;
    s = { durum: 'OK', ad: (a && typeof a.name === 'string') ? a.name : null };
  }
} catch (e) { s = { durum: 'HATA', neden: String((e && e.message) || e).slice(0, 200) }; }
console.log(JSON.stringify(s));
"""


def _node_ile(yol: Path):
    """fiori'nin kütüphane AİLESİ (`yaml`) ile oku — app'in node_modules'undan çözülür.

    Döner: ("OK", ad|None) · ("HATA", neden) · None (node ya da `yaml` paketi YOK → sıradaki yol).
    """
    import json as _json
    try:
        r = subprocess.run(["node", "-e", _NODE_BETIGI, str(yol), str(yol.parent)],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        v = _json.loads((r.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return ("HATA", f"node çıktısı okunamadı (rc={r.returncode})")
    if v.get("durum") == "KUTUPHANE_YOK":
        return None
    if v.get("durum") == "OK":
        return ("OK", v.get("ad"))
    return ("HATA", f"yaml: {v.get('neden')}")


def _pyyaml_ile(yol: Path):
    """Yedek yol: PyYAML, yinelenen anahtar ve `<<` birleştirme anahtarı REDDEDİLİR (fiori'nin
    YAML 1.2 kütüphanesi `<<`'i birleştirme saymaz — kabul etmek farklı bir ad üretebilirdi).
    Döner: ("OK", ad|None) · ("HATA", neden) · None (PyYAML yok)."""
    try:
        import yaml as _yaml
    except Exception:                                  # noqa: BLE001 — bozuk kurulum = yok
        return None

    class _TekilYukleyici(_yaml.SafeLoader):
        pass

    def _harita(loader, node, deep=False):
        gorulen = []
        for k, _v in node.value:
            if k.tag == "tag:yaml.org,2002:merge":
                raise _yaml.constructor.ConstructorError(None, None, "'<<' birlestirme anahtari",
                                                         k.start_mark)
            anahtar = loader.construct_object(k, deep=True)
            if anahtar in gorulen:
                raise _yaml.constructor.ConstructorError(None, None, f"yinelenen anahtar {anahtar!r}",
                                                         k.start_mark)
            gorulen.append(anahtar)
        return loader.construct_mapping(node, deep=deep)

    _TekilYukleyici.add_constructor(_yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _harita)
    try:
        with open(yol, encoding="utf-8") as fh:
            j = _yaml.load(fh, Loader=_TekilYukleyici)  # noqa: S506 — SafeLoader alt sınıfı
    except Exception as exc:                           # noqa: BLE001
        return ("HATA", type(exc).__name__)
    gorevler = (j.get("builder") or {}).get("customTasks") if isinstance(j, dict) else None
    if not isinstance(gorevler, list):
        return ("OK", None)
    g = next((e for e in gorevler if isinstance(e, dict) and e.get("name") == _DEPLOY_GOREVI), None)
    a = g.get("configuration", {}).get("app") if isinstance(g, dict) and isinstance(
        g.get("configuration"), dict) else None
    ad = a.get("name") if isinstance(a, dict) else None
    return ("OK", ad if isinstance(ad, str) else None)


AYRISTIRICILAR = (("node-yaml", _node_ile), ("PyYAML", _pyyaml_ile))


NEDEN_YAML_YOK = "ui5-deploy.yaml yok"   # `--all`un ATLAYABİLDİĞİ TEK neden (all_app_listesi)


def bsp_adi_cozumle(app_dir: Path) -> tuple:
    """(bsp, açıklama). bsp = politikadan geçen app.name (BÜYÜK harf) ya da "".

    Açıklama "" ise ad bulundu; aksi hâlde NEDEN boş (teşhis — karar DEĞİL)."""
    y = app_dir / "ui5-deploy.yaml"
    if not y.exists():
        return "", NEDEN_YAML_YOK
    for ad_, fn in AYRISTIRICILAR:
        sonuc = fn(y)
        if sonuc is None:
            continue
        durum, deger = sonuc
        if durum != "OK":
            return "", f"AYRISTIRILAMADI ({ad_}: {deger})"
        if deger is None:
            return "", f"{_DEPLOY_GOREVI} görevinde configuration.app.name YOK ({ad_})"
        bsp = deger.upper()
        if not musteri_adi_mi(bsp):
            return "", f"app.name {deger!r} müşteri ad alanında DEĞİL ({ad_})"
        return bsp, ""
    return "", "AYRISTIRILAMADI (ayrıştırıcı YOK: node+`yaml` paketi de PyYAML de bulunamadı)"


def bsp_name(app_dir: Path) -> str:
    """ui5-deploy.yaml'dan hedef BSP adını (`fiori deploy`un okuduğu app.name) çıkar; yoksa "".

    Issue #440 (2026-11-15): eskiden yalnız `Z[A-Z0-9_]+` satır regex'i vardı ⇒ `/NS/APP`, `Y…`,
    küçük harfli ad, `ZAD # yorum` sessizce "" idi. Karar `utils.ad_politikasi.musteri_adi_mi`'den
    (ADR 0005-A tek kaynak; kayıtsız namespace RED); ad BÜYÜK harfe çevrilir.
    PR #445 3. kapı: ad GERÇEK YAML ayrıştırıcıyla, fiori'nin okuduğu yoldan alınır —
    `builder.customTasks` içinde İLK `name: deploy-to-abap` görevinin `configuration.app.name`'i.
    Önce node + app'in `node_modules`'undaki `yaml` (fiori'nin kütüphane ailesi), yoksa PyYAML;
    ikisi de yoksa ya da belge hatalıysa (yinelenen anahtar dahil) "" + stderr `[UYARI]`.
    `metadata.name`'e ya da başka bir `name:`e DÜŞÜŞ YOK: hedef ad yoksa "".
    ⚠ KAPSAM: birincil yol fiori'nin GÖMÜLÜ `yaml` kopyasını değil app'in kendi `yaml` paketini
    kullanır (aynı aile, sürüm eşliği ÖLÇÜLMEDİ). PyYAML yedeği YAML 1.1'dir; JS yolundan farklı
    karar verdiği girdilerde (fixture'da ölçülen) sonuç ya aynı ad ya "" olur, BAŞKA bir ad olmaz.
    """
    bsp, neden = bsp_adi_cozumle(app_dir)
    if not bsp and neden.startswith("AYRISTIRILAMADI"):
        print(f"[UYARI] BSP adı ayrıştırılamadı: {app_dir / 'ui5-deploy.yaml'} — {neden}",
              file=sys.stderr)
    return bsp


def all_app_listesi(ui_root: Path) -> tuple:
    """`--all` listesi — deploy_ui ve verify_ui_static_assets'in ORTAK tek kaynağı.

    Dönüş (apps, atlanan, cozulemeyen):
      apps         BSP adı çözülen app dizin adları (sıralı) → normal akışa girer
      atlanan      `ui5-deploy.yaml`'ı OLMAYAN dizinler → deployable değil, ATLANIR (eskiden de böyleydi)
      cozulemeyen  [(app, neden)] — `ui5-deploy.yaml` VAR ama ad çözülemedi (belge hatası · yinelenen
                   anahtar · ayrıştırıcı yok · hedef ad yok · politika reddi) → çağıran app başına
                   FAIL satırı basar ve çıkış kodu 1 olur.
    Neden (PR #445 4. kapı F1): liste eskiden `... and bsp_name(d)` süzgeciyle kuruluyordu; bu PR'la
    `''` "belge hatası / ayrıştırıcı yok" da demek olunca `--all` o app'i sessizce düşürüp
    `[OK] 0 app doğrulandı` + RC 0 basıyordu (ölçüldü; kontrol grubu 5fd32f0 aynı girdide RC 1).
    KOŞMAYAN doğrulama BEYAN EDİLMEZ (deploy_ui özet ilkesi)."""
    apps, atlanan, cozulemeyen = [], [], []
    for d in sorted(ui_root.iterdir(), key=lambda p: p.name):
        if not d.is_dir() or d.name == "node_modules":
            continue
        bsp, neden = bsp_adi_cozumle(d)
        if bsp:
            apps.append(d.name)
        elif neden == NEDEN_YAML_YOK:
            atlanan.append(d.name)
        else:
            cozulemeyen.append((d.name, neden))
    return apps, atlanan, cozulemeyen


def all_kipi(ui_root: Path) -> tuple:
    """`--all` girişi (iki araç ortak): listeyi kurar, `[i]` satırını basar.

    Dönüş (apps, atlanan, cozulemeyen_sonuc) — cozulemeyen_sonuc = (app, False, not) sonuç satırları;
    çağıran bunları sonuç listesinin BAŞINA koyar (FAIL sayılır, çıkış kodu 1)."""
    apps, atlanan, cozulemeyen = all_app_listesi(ui_root)
    print(f"[i] --all → {len(apps)} deployable app: {', '.join(apps)}"
          + (f" · {len(cozulemeyen)} app'te ui5-deploy.yaml VAR ama BSP adı ÇÖZÜLEMEDİ (FAIL): "
             f"{', '.join(a for a, _n in cozulemeyen)}" if cozulemeyen else "")
          + f" · {len(atlanan)} dizin ui5-deploy.yaml'sız (atlandı)")
    return apps, atlanan, [(app, False, f"BSP adı ÇÖZÜLEMEDİ — {neden} · beklenen: {BSP_ADI_BEKLENEN} "
                                        "(doğrulama/deploy KOŞMADI)") for app, neden in cozulemeyen]


def fail_ozeti(fail: int, toplam: int, cozulemeyen_n: int, kosan_metni: str) -> str:
    """FAIL özet gövdesi (iki araç ortak): KOŞUP başarısız olanlar ile BSP adı çözülemediği için HİÇ
    KOŞMAYANLAR ayrı sayılır — koşmayan app 'STALE/güncel değil' diye beyan edilmez."""
    kosan = fail - cozulemeyen_n
    return " · ".join(([f"{kosan}/{toplam} {kosan_metni}"] if kosan else [])
                      + ([f"{cozulemeyen_n}/{toplam} app BSP adı ÇÖZÜLEMEDİĞİ için HİÇ KOŞMADI"]
                         if cozulemeyen_n else []))


def atlanan_notu(atlanan: list, tum_kip: bool) -> str:
    """Özet satırı eki: `--all`da ui5-deploy.yaml'sız atlanan dizin sayısı (yalnız --all; aksi hâlde "")."""
    return f" · {len(atlanan)} dizin ui5-deploy.yaml'sız ATLANDI" if tum_kip else ""


def bsp_icf_yolu(bsp: str) -> str:
    """Canlı BSP'nin ICF yolu (`/` ile biter) — iki URL kurucusunun (canlı preload ·
    statik varlık doğrulaması) TEK kaynağı (Issue #440).

    · Z/Y: `/sap/bc/ui5_ui5/sap/<bsp>/` — bugüne kadarki tek yol, aynen korunur.
    · `/NS/APP`: `/sap/bc/ui5_ui5/<ns>/<app>/` — `sap` düğümünün KARDEŞİ olan namespace
      düğümü. ⚠ Bu yol Issue #440 sahibinin ortamında (tek sistem, ilk deploy) ölçüldü;
      çekirdek sahibinin sisteminde namespace'li BSP olmadığı için burada ÖLÇÜLEMEDİ —
      yalnız ICF ağacının yapısı (UI5_UI5 altında SAP ile kardeş namespace düğümleri) görüldü.
    """
    ns = ad_namespace(bsp)
    if ns:
        return f"/sap/bc/ui5_ui5/{ns.strip('/').lower()}/{bsp[len(ns):].lower()}/"
    if "/" in bsp:
        # `/X/APP` (namespace 3-8 karakter değil) ya da başka eğik çizgili ad: `sap` düğümüne
        # düşürmek `/sap/bc/ui5_ui5/sap//x/app/` gibi SAHTE bir yol kurar ⇒ 404 "BSP yok"
        # diye okunur (sessiz yanlış teşhis). Fail-closed.
        raise ValueError(f"BSP adı ICF yoluna çevrilemez (namespace biçimi /<3-8>/ değil): {bsp!r}")
    return f"/sap/bc/ui5_ui5/sap/{bsp.lower()}/"


def satir_sonu_normalize(b: bytes) -> bytes:
    """GERÇEK CR/LF baytlarını LF'e indir (sha() ve modül kıyası ORTAK kullanır)."""
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha(b: bytes) -> str:
    """Satır-sonu NORMALIZE'lı sha256 — SAP BSP dosyayı \\r\\n ile saklar, dist \\n; bu
    CRLF/LF farkı byte-noise'tur (içerik aynı). Normalize etmeden karşılaştırmak yanlış-pozitif
    STALE üretir (2026-07-06 dsk vakası: 20 byte = 20×\\r). Gerçek içerik farkı korunur.
    ⚠ Yalnız GERÇEK baytı görür; string İÇİNDEKİ kaçışlı `\\r\\n` için → preload_karsilastir()."""
    return hashlib.sha256(satir_sonu_normalize(b)).hexdigest()


# ── Q281 (2026-09-13): KAÇIŞLI satır sonu — preload STRING'lerinin İÇİNDE ─────────────────
# `ui5 build` XML/properties/json kaynaklarını preload'a JS STRING olarak gömer:
#     sap.ui.require.preload({ "<ns>/view/App.view.xml":'<mvc:View\r\n  ...', ... })
# Çalışma ağacı CRLF ise (git `i/lf w/crlf`) satır sonu string içinde 4 baytlık `\r\n`
# KAÇIŞI olur. sha() yalnız GERÇEK CR/LF baytını gördüğünden aynı içerik CRLF ağaçtan ve
# LF ağaçtan build edilince FARKLI hash verir ⇒ yanlış STALE (ölçüldü: 2 BSP'de modül modül
# içerik EŞİT, fark 0 satır; 19 BSP'lik taramada eski hüküm 2/19 STALE, kaçış indirilince 0/19).
# ⛔ NORMALİZASYON GLOBAL DEĞİL: preload'un JS KOD bölümünde de kaçışlı `\r` geçebilir
#    (ölçüldü: 19 BSP'nin 1'inde) ve `split("\r\n")` ↔ `split("\n")` GERÇEK davranış farkıdır.
#    Kaçış yalnız haritadaki `.xml` / `.properties` / `.json` string modüllerinde indirilir
#    (19 BSP'lik canlı korpusta haritada ÖLÇÜLEN uzantılar bunlardır). Bu üçünde satır sonu
#    ayrıştırıcıya görünmez; `.txt`/`.csv`/`.html` gibi HAM metin kaynakta CRLF↔LF kullanıcıya
#    görünen bir fark olabilir (indirilen şablon) → KATI kalır. JS kodu, `.js` string modülü,
#    harita iskeleti ve ayrıştırılamayan HER bayt KATI kıyaslanır. Harita yoksa hiçbir şey gevşetilmez.
# ⛔ Sınıfı yalnız `--verify-only` KABUL eder. Gerçek deploy'dan hemen sonra canlı, yüklenen
#    dist'in KENDİSİ olmalıdır; orada kaçış farkı "yüklenen dosya canlıda DEĞİL" demektir ⇒
#    deploy kipinde STALE/CACHE kalır (sınıf yalnız teşhis notu olarak basılır).
PRELOAD_HARITASI = b"sap.ui.require.preload("
_PRELOAD_GIRDISI = re.compile(
    rb'"([^"\\\n]+/[^"\\\n]+\.([A-Za-z0-9]+))"\s*:\s*'
    rb"('(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\")")
# ÇİFT sayıda ters bölüden sonra gelen `\r\n` kaçışı. `\\r\\n` (kaçışlanmış ters bölü + "r")
# metnin kendisinde "\r" YAZISIDIR, satır sonu değildir → dokunulmaz.
_KACISLI_CRLF = re.compile(rb"(?<!\\)((?:\\\\)*)\\r\\n")
KACIS_INDIRILEN_UZANTILAR = {b"xml", b"properties", b"json"}
JS_ISKELETI = "<js-kodu+harita-iskeleti>"
SATIR_SONU = "SATIR_SONU"
SATIR_SONU_ETIKETI = "CANLI≈kaynak — YALNIZ SATIR SONU farkı"


def preload_modulleri(b: bytes, kacis_indir: bool = True) -> dict | None:
    """Component-preload.js → {modül-adı: içerik-baytı}. Harita yoksa None (kıyas KATI kalır).

    Haritadaki her string girdi kendi adıyla ayrılır; geri kalan HER bayt (JS kodu, anahtarlar,
    ayraçlar, ayrıştırılamayan girdiler) `JS_ISKELETI` altında HAM kalır — hiçbir bayt kaybolmaz.
    `kacis_indir=True` yalnız `KACIS_INDIRILEN_UZANTILAR` (xml/properties/json) string modüllerinde
    kaçışlı `\\r\\n`'i `\\n`'e indirir.
    """
    b = satir_sonu_normalize(b)
    bas = b.rfind(PRELOAD_HARITASI)
    if bas < 0:
        return None
    moduller: dict = {}
    iskelet = [b[:bas]]
    konum = bas
    for m in _PRELOAD_GIRDISI.finditer(b, bas):
        iskelet.append(b[konum:m.start(3)])
        ad = m.group(1).decode("utf-8", "replace")
        deger = m.group(3)
        if kacis_indir and m.group(2).lower() in KACIS_INDIRILEN_UZANTILAR:
            deger = _KACISLI_CRLF.sub(rb"\1\\n", deger)
        anahtar, n = ad, 2
        while anahtar in moduller:   # aynı ad iki kez geçerse ikisi de AYRI kıyaslanır
            anahtar, n = f"{ad}#{n}", n + 1
        moduller[anahtar] = deger
        konum = m.end(3)
    iskelet.append(b[konum:])
    moduller[JS_ISKELETI] = b"".join(iskelet)
    return moduller


def preload_karsilastir(yerel: bytes, canli: bytes) -> tuple:
    """→ (sınıf, modüller). Sınıf: `AYNI` (hash eşit) · `SATIR_SONU` (içerik modül modül eşit,
    fark YALNIZ string modüllerindeki kaçışlı `\\r\\n`) · `FARKLI`. Modüller: SATIR_SONU'da kaçış
    farkı taşıyan, FARKLI'da içeriği farklı olan modül adları (harita ayrıştırılamadıysa boş)."""
    if sha(yerel) == sha(canli):
        return "AYNI", []
    my, mc = preload_modulleri(yerel), preload_modulleri(canli)
    if my is None or mc is None:
        return "FARKLI", []
    farkli = sorted(k for k in my.keys() | mc.keys() if my.get(k) != mc.get(k))
    if farkli:
        return "FARKLI", farkli
    hy, hc = preload_modulleri(yerel, False), preload_modulleri(canli, False)
    return SATIR_SONU, sorted(k for k in hy.keys() | hc.keys() if hy.get(k) != hc.get(k))


def _kisalt(adlar: list, n: int = 4) -> str:
    return ", ".join(adlar[:n]) + (f" (+{len(adlar) - n})" if len(adlar) > n else "")


def run(cmd: str, cwd: Path, env: dict) -> tuple:
    """shell komutu çalıştır → (rc, tail_output). Windows cmd.exe/npm.cmd için shell=True."""
    p = subprocess.run(cmd, cwd=str(cwd), env=env, shell=True,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def fetch_live_preload(base_url: str, user: str, pw: str, client: str, bsp: str,
                       dosya: str = PRELOAD) -> bytes:
    """Canlı BSP preload'unu (uygulama: Component-preload.js · library: library-preload.js) cache-bust
    + no-cache + identity-encoding ile çek."""
    ts = str(int(time.time()))
    url = f"{base_url}{bsp_icf_yolu(bsp)}{dosya}?sap-client={client}&cb={ts}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {auth}",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Accept-Encoding": "identity",
    })
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.read()


def deploy_one(app: str, ui_root: Path, conn, env: dict, dry: bool, verify_only: bool) -> tuple:
    """Tek app: build → (deploy) → canlı doğrula. mode: dry (deploy YOK, canlı YOK) /
    verify_only (build + canlı karşılaştır, DEPLOY YOK — 'stale mi' kontrolü) / normal.
    Dönüş (app, ok, note)."""
    base_url, user, pw, client = conn
    app_dir = ui_root / app
    if not app_dir.is_dir():
        return (app, False, f"app dizini yok: {app_dir}")
    bsp = bsp_name(app_dir)
    if not bsp:
        return (app, False, f"ui5-deploy.yaml'da {BSP_ADI_BEKLENEN} bulunamadı")

    kutuphane = kutuphane_mi(app_dir)   # yalnız `ui5.yaml` type: library — aksi hâlde bugünkü yol
    preload_adi = LIB_PRELOAD if kutuphane else PRELOAD
    if kutuphane:
        print(f"  [{app}] UI5 library (ui5.yaml type: library) — doğrulama {LIB_PRELOAD}, dist Flat düzen")

    # 1) BUILD (zorunlu — mevcut webapp/src kaynağından taze dist)
    print(f"  [{app}] build (ui5 build --clean-dest --dest dist)…")
    rc, out = run("npm run build", app_dir, env)
    if rc != 0:
        return (app, False, f"BUILD FAIL rc={rc}: {out.strip()[-300:]}")
    if kutuphane:
        engel = kutuphane_dist_engeli(app_dir / "dist")
        if engel:
            return (app, False, f"{engel} (deploy KOŞMADI)")
    dist_preload = app_dir / "dist" / preload_adi
    if not dist_preload.exists():
        ipucu = ""
        if not kutuphane and (app_dir / KUTUPHANE_KAYNAK).is_dir() and any(
                (app_dir / KUTUPHANE_KAYNAK).rglob(KUTUPHANE_TANIM)):
            ipucu = (f" · src/ altında {KUTUPHANE_TANIM} var: library ise {UI5_YAML} tipi okunamadı "
                     f"({proje_tipi(app_dir)[1]})")
        return (app, False, f"build sonrası dist/{preload_adi} yok — build çıktısı beklenmedik{ipucu}")
    local_bytes = dist_preload.read_bytes()
    local_hash = sha(local_bytes)
    print(f"  [{app}] dist/{preload_adi} sha(norm)={local_hash[:12]}…")

    if dry:
        return (app, True, f"dry-run (build OK, BSP={bsp}, deploy+doğrulama YOK)")

    # DEPLOY (verify_only ise ATLA — sadece canlıyı mevcut kaynakla karşılaştır)
    if not verify_only:
        print(f"  [{app}] deploy → {bsp} …")
        rc, out = run("npx --no-install fiori deploy --config ui5-deploy.yaml --yes", app_dir, env)
        if rc != 0 or "Deployment Successful" not in out:
            return (app, False, f"DEPLOY FAIL rc={rc}: {out.strip()[-400:]}")

    # CANLI DOĞRULAMA — "Successful" mesajına GÜVENME, içeriği kanıtla (satır-sonu normalize'lı)
    print(f"  [{app}] canlı {preload_adi} {'karşılaştır (verify)' if verify_only else 'doğrula'} (cache-bust)…")
    try:
        # Uygulama çağrısı BİREBİR eski biçim (imza değişmez); library yalnız dosya adını verir.
        live = (fetch_live_preload(base_url, user, pw, client, bsp, dosya=LIB_PRELOAD) if kutuphane
                else fetch_live_preload(base_url, user, pw, client, bsp))
    except Exception as e:
        return (app, False, f"canlı çekme HATASI ({type(e).__name__}): {e} — doğrulanamadı")
    live_hash = sha(live)
    if live_hash != local_hash:
        sinif, moduller = preload_karsilastir(local_bytes, live)
        # Q281: yalnız VERIFY kipinde ve yalnız içerik modül modül EŞİTSE STALE sayılmaz.
        if verify_only and sinif == SATIR_SONU:
            return (app, True,
                    f"{SATIR_SONU_ETIKETI} (kaçışlı \\r\\n, {len(moduller)} modül: {_kisalt(moduller)}) · "
                    f"içerik modül modül EŞİT → STALE SAYILMADI · dist(norm)={local_hash[:12]} "
                    f"canlı(norm)={live_hash[:12]}, BSP={bsp}")
        tag = "⛔ STALE: canlı ≠ mevcut kaynak" if verify_only else "⛔ STALE/CACHE: canlı ≠ dist"
        extra = ("canlı BSP, git/working-tree kaynaktan build ile UYUŞMUYOR — geçmişte bayat "
                 "deploy edilmiş VEYA henüz deploy edilmemiş değişiklik var."
                 if verify_only else
                 "Deploy 'Successful' dedi ama canlı içerik ESKİ — build atlanmış/cache/deploy hatası.")
        if sinif == SATIR_SONU:
            modul_notu = (f" Fark YALNIZ kaçışlı satır sonu ({len(moduller)} modül) — içerik eşit ama "
                          "yüklenen dist canlıda DEĞİL.")
        elif moduller:
            modul_notu = f" Farklı modül ({len(moduller)}): {_kisalt(moduller)}."
        else:
            modul_notu = " (preload haritası ayrıştırılamadı — modül kıyası YAPILAMADI, hash hükmü geçerli.)"
        return (app, False,
                f"{tag}! dist(norm)={local_hash[:12]} vs canlı(norm)={live_hash[:12]}. {extra}{modul_notu}")
    ok_note = "CANLI==kaynak ✓ (güncel)" if verify_only else "CANLI==dist ✓ (deploy doğrulandı)"
    return (app, True, f"{ok_note} sha={local_hash[:12]}, BSP={bsp}")


def changed_apps(ui_root: Path) -> tuple[list, list]:
    """git'e göre webapp/ altı (library: src/ altı) değişen app'ler → (app_listesi, hatalar).

    ⛔ 2026-08-01 (KAYIT S5): eskiden git ÇIKIŞ KODLARI hiç kontrol edilmiyordu ve yalnız
    `list` dönüyordu. `HEAD~1` çözülemeyen bir ağaçta (tek-commit'lik repo, `--depth 1`
    shallow clone, detached/köksüz durum) git **exit 128 + stderr'e "fatal:"** verir; o
    çıktıda hiçbir yol satırı olmadığı için küme BOŞ kalır ve çağıran bunu "değişen app
    yok" diye okuyup **exit 0 ile sessizce hiçbir şey deploy etmez.** Yani ARAÇ ARIZASI ile
    İŞ YOKLUĞU ayırt edilemiyordu (ölçüldü: tek-commit'lik sentetik repoda rc=128 → `[]`).
    Artık hata AYRI dönüyor: çağıran "boş liste"yi ancak git'in ikisi de BAŞARILIYSA
    'gerçekten değişiklik yok' diye okuyabilir.
    """
    hatalar: list[str] = []
    bloklar = []
    for etiket, komut in (
        ("son commit farkı (HEAD~1..HEAD)", f'git -C "{REPO}" diff --name-only HEAD~1 HEAD'),
        ("çalışma ağacı (status)", f'git -C "{REPO}" status --porcelain'),
    ):
        rc, out = run(komut, REPO, os.environ.copy())
        if rc != 0:
            hatalar.append(f"{etiket}: git rc={rc} — {out.strip().splitlines()[0] if out.strip() else '(çıktı yok)'}")
            continue
        bloklar.append(out)

    names = set()
    rel = ui_root.relative_to(REPO).as_posix()
    for block in bloklar:
        for line in block.splitlines():
            satir = line.replace("\\", "/")
            m = re.search(re.escape(rel) + r"/([^/]+)/webapp/", satir)
            if m:
                names.add(m.group(1))
                continue
            # Library (2026-11-27): kaynak `<lib>/src/`. YALNIZ ui5.yaml tipi library olan dizin sayılır —
            # `src/`'si olan bir uygulama (ya da yardımcı dizin) listeye girmez.
            m = re.search(re.escape(rel) + r"/([^/]+)/" + KUTUPHANE_KAYNAK + r"/", satir)
            if m and kutuphane_mi(ui_root / m.group(1)):
                names.add(m.group(1))
    return sorted(names), hatalar


def main() -> int:
    ap = argparse.ArgumentParser(description="Freestyle UI5 app GÜVENLİ deploy (build+deploy+canlı doğrula)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--app", help="Tek app (ör. dsk_se)")
    g.add_argument("--apps", help="Virgülle app listesi (ör. sip_se,dsk_se,fih_se)")
    g.add_argument("--all-changed", action="store_true",
                   help="git'e göre webapp (library: src) değişen app'ler")
    g.add_argument("--all", action="store_true", help="ui-root'taki TÜM deployable app (ui5-deploy.yaml olan)")
    ap.add_argument("--ui-root", default=DEFAULT_UI_ROOT,
                help=f"UI workspace kökü (varsayılan: project.yaml default_ui_root={DEFAULT_UI_ROOT})")
    ap.add_argument("--dry-run", action="store_true", help="build+doğrula planı, deploy YAPMA")
    ap.add_argument("--verify-only", action="store_true",
                    help="DEPLOY ETME — sadece canlı BSP == mevcut kaynaktan build mi karşılaştır (stale tarama)")
    args = ap.parse_args()

    ui_root = (REPO / args.ui_root) if not Path(args.ui_root).is_absolute() else Path(args.ui_root)
    if not ui_root.is_dir():
        print(f"[FAIL] ui-root yok: {ui_root}", file=sys.stderr)
        return 1

    cozulemeyen_sonuc, atlanan = [], []   # yalnız --all doldurur (PR #445 4. kapı F1)
    if args.app:
        apps = [args.app]
    elif args.apps:
        apps = [a.strip() for a in args.apps.split(",") if a.strip()]
    elif args.all:
        apps, atlanan, cozulemeyen_sonuc = all_kipi(ui_root)
    else:
        apps, git_hatalari = changed_apps(ui_root)
        if git_hatalari:
            # "Sorgu çalışmadı" ≠ "değişiklik yok". Sessizce 0 dönmek, deploy'u ATLAYIP
            # başarılı görünmektir (KAYIT S5). Fail-closed: sebebi söyle, alternatifi ver.
            print("[FAIL] --all-changed: git sorgusu BAŞARISIZ — 'değişen app yok' SONUCU "
                  "ÇIKARILAMAZ:", file=sys.stderr)
            for h in git_hatalari:
                print(f"        · {h}", file=sys.stderr)
            print("        (tek-commit'lik repo / shallow clone `--depth 1` / git ağacı yok?)\n"
                  "        Açık liste ver: --app <ad> | --apps a,b | --all", file=sys.stderr)
            return 1
        if not apps:
            print("[i] git'e göre webapp/src değişen app yok — deploy edilecek bir şey yok.")
            return 0
        print(f"[i] --all-changed → {', '.join(apps)}")

    conn = read_conn()
    env = os.environ.copy()
    env["FIORI_TOOLS_USER"] = conn[1]
    env["FIORI_TOOLS_PASSWORD"] = conn[2]
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

    kutuphaneler = [a for a in apps if (ui_root / a).is_dir() and kutuphane_mi(ui_root / a)]
    mode = "[VERIFY-ONLY]" if args.verify_only else ("[DRY-RUN]" if args.dry_run else "[DEPLOY]")
    print(f"=== UI {mode}: {', '.join(apps)} (ui-root={ui_root}) ===")
    results = list(cozulemeyen_sonuc)
    for app in apps:
        print(f"\n--- {app} ---")
        results.append(deploy_one(app, ui_root, conn, env, args.dry_run, args.verify_only))

    print("\n=== SONUÇ ===")
    fail = 0
    # Q281 · CORE-06: "yalnız satır sonu farkıyla içerik-eşit" AYRI KOVADIR — "hash-eşit" ile
    # aynı `[OK]` etiketine karışırsa kabul edilen gevşetme görünmez olur.
    satir_sonu = [app for app, ok, note in results if ok and note.startswith(SATIR_SONU_ETIKETI)]
    for app, ok, note in results:
        etiket = "[FAIL]" if not ok else ("[OK~] " if app in satir_sonu else "[OK]  ")
        print(f"  {etiket} {app}  — {note}")
        if not ok:
            fail += 1
    satir_sonu_notu = (f"    [OK~] = {len(satir_sonu)} app bayt-eş DEĞİL, fark YALNIZ preload string'lerindeki "
                       f"kaçışlı \\r\\n (CRLF çalışma ağacından build); içerik modül modül eşit, STALE "
                       f"SAYILMADI: {', '.join(satir_sonu)}")
    atl = atlanan_notu(atlanan, args.all)
    if fail:
        if args.verify_only:
            act = "STALE tespit edildi (canlı ≠ kaynak)"
        elif args.dry_run:
            act = "BUILD başarısız (deploy zaten yapılmadı)"
        else:
            act = "deploy DOĞRULANAMADI (bayat gitmiş olabilir)"
        print(f"\n[FAIL] {fail_ozeti(fail, len(results), len(cozulemeyen_sonuc), 'app ' + act)}{atl} — "
              "yukarıyı incele, kullanıcıya raporla (asla 'başarılı' deme).", file=sys.stderr)
        if satir_sonu:
            print(satir_sonu_notu, file=sys.stderr)
        return 1

    # ⛔ 2026-08-10 — ÖZET SATIRI ÜÇ-YOLLU OLMAK ZORUNDA. Mod banner'ı (yukarıda) üç
    # yolluydu ama bu satır İKİ yolluydu: `verify_only` değilse DEPLOY cümlesini basıyordu.
    # Sonuç: `--dry-run` — ki `deploy_one()` içinde canlıya HİÇ BAKMAZ (`if dry: return`) —
    # ekrana **"N app doğrulandı (canlı Component-preload == build çıktısı)"** yazıyordu.
    # Ölçülen bedel (2026-08-10): app STALE'ken bu satır okundu ve "güncel" sanıldı.
    # Bu script'in VAR OLMA SEBEBİ tam olarak "Successful mesajına güvenme, içeriği kanıtla"
    # olduğu için, kendi özet satırının koşmayan bir doğrulamayı beyan etmesi kapının
    # kendisini yalanlıyordu. Kural: KOŞMAYAN doğrulama BEYAN EDİLMEZ — "doğrulandı" ve
    # "canlı ==" sözcükleri dry-run dalında GEÇMEZ.
    if args.verify_only and satir_sonu:
        print(f"\n[OK] {len(results)} app doğrulandı (canlı == mevcut kaynak — hepsi güncel; "
              f"{len(results) - len(satir_sonu)}'i hash-eşit, {len(satir_sonu)}'i YALNIZ SATIR SONU "
              f"farkıyla içerik-eşit).{atl}")
        print(satir_sonu_notu)
    elif args.verify_only:
        print(f"\n[OK] {len(results)} app doğrulandı (canlı == mevcut kaynak — hepsi güncel).{atl}")
    elif args.dry_run:
        print(f"\n[i] DRY-RUN bitti: {len(results)} app BUILD edildi. "
              f"DEPLOY YAPILMADI, CANLI İÇERİK OKUNMADI.{atl}")
        print("    Bu çıktı 'canlı == build' KANITI DEĞİLDİR ve app'in güncel olduğunu GÖSTERMEZ.")
        print("    Bayatlık (stale) taraması için: --verify-only · gerçek deploy için bayraksız koş.")
    else:
        lib_notu = (f" · {len(kutuphaneler)} library: canlı library-preload == build çıktısı "
                    f"({', '.join(kutuphaneler)})" if kutuphaneler else "")
        print(f"\n[OK] {len(results)} app doğrulandı (canlı Component-preload == build çıktısı{lib_notu}).{atl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

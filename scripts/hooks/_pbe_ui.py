# -*- coding: utf-8 -*-
"""_pbe_ui.py — PULL-BEFORE-EDIT (ADR 0016) eklentisi: freestyle UI5 `webapp/` dosyaları (Q352-B).

⛔ NEDEN VAR (canlı vaka, 2026-09-26): başka bir makinede bir rapor uygulamasına kolon eklenip
   canlıya deploy edilmişti; repo habersizdi. Eski yerel kodla yapılacak bir sonraki deploy o
   kolonu canlıdan SESSİZCE silerdi. ABAP tarafında aynı sınıfı `pull_before_edit` kapatıyordu;
   UI dosyaları kapsam dışıydı. Ölçüm: tüketici projede 6 BSP'nin 6'sı canlı = yerel (rc 0);
   aynı canlı zip ↔ kolon senkronundan ÖNCEKİ repo webapp'i → GERCEK-FARK=4 (kontrol grubu).

SÖZLEŞME (kapı `pull_before_edit._EK_DENETCILER` bu modülü yükler):
    sinifla(path, root) -> None | {"nesne": <BSP>, "tip": "bsp", "komut": <blok mesajı komutu>,
                                   "not": <açıklama + --offline kaçışı (opsiyonel)>}
  · Tazelik kontrolünü KAPI yapar (dosya anahtarıyla, store'dan). Damgayı
    `fetch_ui_source.py --damgala` yazar (canlıyla eşitlik ölçüldükten sonra).

KAPSAM (karar Q352-B AR-1, lider onaylı):
  · `<kök-segment>/…/<app>/webapp/**` — `<app>` = `webapp`'in ebeveyni. `<kök-segment>` =
    çekirdek kapının kök segmentleri (proje `source_root` + geçiş-eski `erp`).
  · App'in KENDİSİ `_EXCLUDED_DIR_SEGMENTS` (ref_docs/docs/.tmp/legacy/archive/drafts) ya da
    `node_modules` altındaysa canlı uygulama değildir → None.
  · Proje kökü DIŞINDAKİ webapp (ör. kanonik `.wt` worktree'si) ve proje ağacındaki bir
    junction/symlink'in ARKASINDAKİ webapp da kapsamdadır — kapsam kararı `..`'sı sadeleşmiş ama
    bağı İZLENMEMİŞ yolda verilir; kök/hariç segmentleri kök dışında mutlak yolun parçalarında
    aranır (çekirdek `pbe_siniflandir` kuralı); anahtar
    `tazelik_anahtari`'nin mutlak dalı (ABAP ile simetrik; `fetch_ui_source --damgala` aynı
    anahtarla damgalar). ⚠ Store + anahtar kökü `CLAUDE_PROJECT_DIR`'den, boşsa CWD'den çözülür
    (ABAP ile ortak; kök çözüm ertelendi T-PBE-KOK-CWD) ⇒ araç proje kökünden (ya da
    `CLAUDE_PROJECT_DIR` ile) koşulduğunda kapı damgayı görür; araç yazdığı store'u basar.
  · YALNIZ `deploy-to-abap` özel görevinin `configuration.exclude` listesindeki yollar → None:
    o dosyalar canlıya HİÇ gitmez (ölçüldü: canlı zip'te `test/` YOK, `localService/` VAR —
    builder `resources.excludes` etkin değil). Dosyadaki BAŞKA `exclude:` anahtarları okunmaz.
  · EŞLEŞME ANLAMI deploy aracının KODUNDAN ölçüldü (`@sap/ux-ui5-tooling` 1.25.0,
    `dist/tasks/deploy/index.js`, arşiv kurulumu):
        exclude.some((regex) => RegExp(regex, "g").exec(resource.getPath()))
    ⇒ her girdi bir REGEX'tir, `i` bayrağı YOK = HARF DUYARLI, çapasızdır (yolun herhangi bir
    yerinde eşleşir), yol `/resources/<proje-adı>/<rel>` biçimindedir. Burada yalnız düz
    segmentli girdiler (`/test/`, `test`, `/a/b/`) webapp köküne göre, HARF DUYARLI bir ÖNEK
    olarak muaf sayılır — bu, aracın dışladığı kümenin ALT kümesidir. Muafiyet kıyası ÇÖZÜLMÜŞ
    dosyanın çözülmüş webapp'e göre yolundadır (`..` çözülür, Windows'ta disk harf biçimi) — yazım
    biçimi karar vermez; bu şartla sahte-muaf yok (dosya henüz yoksa kapı zaten serbest bırakır;
    webapp içinden `test/`e giden bağ ölçülmedi). `*`,
    `[`, `(`, `^`, `$` … taşıyan ya da satır-içi liste biçimindeki girdi MUAFİYET VERMEZ
    (fail-closed) — dosya kapıda kalır.
  · `ui5-deploy.yaml` yok ya da BSP adı çözülemiyor → dict YİNE döner (sessiz geçiş YOK),
    komut `--bsp <BSP_ADI>` yer tutuculu.
  · `komut` YALNIZ çalıştırılabilir komuttur (kapı sonuna `--session <id>` ekleyebilir);
    açıklama + `--offline` kaçışı opsiyonel `"not"` anahtarındadır.

BAKILMAYAN: aracın iç içe (`view/test/…`) ve regex eşleşmeleri — daha dar muafiyet = daha çok
kapı, güvenli yön.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional

WEBAPP = "webapp"
DEPLOY_YAML = "ui5-deploy.yaml"
ARAC = "core/scripts/fetch_ui_source.py"
BSP_YER_TUTUCU = "<BSP_ADI>"
# App dizininin üstünde bunlardan biri varsa canlı uygulama değildir (bağımlılık kopyası).
_UI_EK_HARIC = frozenset({"node_modules"})
# Anlaşılan deploy-exclude biçimi: `/seg/`, `seg`, `/a/b/` … (yalnız düz yol segmentleri; `*` YOK —
# aracın regex'inde `/**` geçersiz/farklı anlamlıdır, muafiyet sayılmaz).
_DUZ_DESEN = re.compile(r"^/?(?P<yol>[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*)/?$")
DEPLOY_GOREVI = "deploy-to-abap"

_SCRIPTS = str(Path(__file__).resolve().parents[1])
if _SCRIPTS not in sys.path:
    sys.path.append(_SCRIPTS)


def _kapi_kumeleri() -> tuple[frozenset, frozenset]:
    """(kök segmentleri, hariç üst segmentler) — çekirdek kapıyla TEK KAYNAK (source_drift)."""
    import source_drift as sd  # kapı zaten bunu yükler; yüklenemezse kapı hiç karar veremez
    kok = getattr(sd, "PBE_KOK_SEGMENTLERI", None) or frozenset({sd.SOURCE_ROOT_NAME.lower(), "erp"})
    return frozenset(kok), frozenset(sd._EXCLUDED_DIR_SEGMENTS) | _UI_EK_HARIC


def _girinti(s: str) -> int:
    return len(s) - len(s.lstrip())


def deploy_haric_desenleri(app_dir: Path) -> tuple[list[str], list[str]]:
    """`ui5-deploy.yaml` → (anlaşılan önekler, ANLAŞILMAYAN ham desenler).

    YALNIZ `customTasks` içindeki `name: deploy-to-abap` öğesinin `configuration.exclude` listesi
    okunur. Builder `excludes:` (çoğul) ve başka görevlerin `exclude:`'u OKUNMAZ (sahte-muaf yönü)."""
    y = Path(app_dir) / DEPLOY_YAML
    try:
        satirlar = y.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    except OSError:
        return [], []
    satirlar = [s for s in satirlar if s.strip() and not s.lstrip().startswith("#")]
    onekler: list[str] = []
    anlasilmayan: list[str] = []
    gorev_g = None     # deploy-to-abap liste öğesinin `-` girintisi
    conf_g = None      # o öğedeki `configuration:` girintisi
    liste_g = None     # o configuration altındaki `exclude:` girintisi
    for s in satirlar:
        g = _girinti(s)
        govde = s.strip()
        m_oge = re.match(r"^-\s*name:\s*['\"]?(?P<ad>[^'\"#\s]+)", govde)
        if gorev_g is not None and (g < gorev_g or (g == gorev_g and govde.startswith("-"))):
            gorev_g = conf_g = liste_g = None           # deploy görevi öğesi bitti
        if m_oge and gorev_g is None:
            if m_oge.group("ad") == DEPLOY_GOREVI:
                gorev_g = g
            continue
        if gorev_g is None:
            continue
        if conf_g is not None and g <= conf_g:
            conf_g = liste_g = None
        if liste_g is not None:
            m_li = re.match(r"^-\s*(.+?)\s*$", govde)
            if m_li and g >= liste_g:
                ham = m_li.group(1).split(" #", 1)[0].strip().strip("'\"")
                d = _DUZ_DESEN.match(ham)
                if d:
                    onekler.append(d.group("yol") + "/")
                else:
                    anlasilmayan.append(ham)
                continue
            liste_g = None
        if conf_g is None:
            if re.match(r"^configuration:\s*(?:#.*)?$", govde):
                conf_g = g
            continue
        m_ex = re.match(r"^exclude:\s*(?P<satir_ici>[^#\s].*?)?\s*(?:#.*)?$", govde)
        if m_ex:
            if m_ex.group("satir_ici"):                 # `exclude: [/test/]` — satır-içi biçim ölçülmedi
                anlasilmayan.append(m_ex.group("satir_ici"))
            else:
                liste_g = g
    return onekler, anlasilmayan


def deploy_haric_mi(rel: str, onekler) -> bool:
    """webapp'e göre posix `rel` deploy-exclude önekiyle mi başlıyor? HARF DUYARLI — deploy aracı
    `RegExp(regex, "g")` (i bayrağı yok) kullanır; duyarsız kıyas sahte-muaf üretirdi."""
    r = rel.replace("\\", "/").lstrip("/")
    return any(r.startswith(o) for o in onekler)


def _cozulmus(p: Path) -> Path:
    try:
        return p.resolve()
    except (OSError, RuntimeError, ValueError):   # ValueError: yolda NUL vb. (eski davranış: yazıldığı gibi)
        return p


def _sade(p: Path) -> Path:
    """`..`/`.` sadeleşir, bağ (junction/symlink) İZLENMEZ — çekirdek `pbe_siniflandir` ile aynı ilke."""
    try:
        return Path(os.path.normpath(p))
    except (ValueError, TypeError):
        return p


def uygulama_coz(path, root=None) -> Optional[tuple[Path, str]]:
    """Dosya → (app dizini, webapp'e göre posix rel) ya da None (UI webapp kapsamı değil).

    İKİ AYRI YOL (bug gate 2.+3. tur):
      · KAPSAM (webapp'in yeri, kök/hariç segment) → `_sade(p)`: `..` sadeleşir ama junction/symlink
        İZLENMEZ. Çözülmüş yolla karar verilseydi proje ağacındaki bir junction'ın arkasındaki webapp
        kök segmentini kaybedip SESSİZCE kapsam dışı kalırdı (3. tur MEDIUM, ölçüldü).
      · MUAFİYET `rel`'i → çözülmüş dosya ↔ çözülmüş webapp: Windows harf duyarsız ve `..` kabul
        eder ⇒ yazıldığı biçimle kıyaslanan `rel` sahte-muaf üretirdi (`webapp/test/x.js` yazılır,
        diskte `Test/x.js` — araç onu DIŞLAMAZ). `resolve()` `..`'yı çözer ve Windows'ta var olan
        bileşenlerin DİSK harf biçimini döndürür (ölçüldü, Py 3.11). İki çözülmüş yol birbirine
        göre ifade edilemezse (webapp içinden dışarı giden bağ) sadeleşmiş yola düşülür — dosya kapıda
        kalır (fixture A21/C8). webapp içinden `test/`'e giden bağ ÖLÇÜLMEDİ (deploy aracı bağı izliyor mu).
    """
    p = Path(path)
    if not p.is_absolute() and root is not None:
        p = Path(root) / p
    ps = _sade(p)
    webapp = next((a for a in ps.parents if a.name.lower() == WEBAPP), None)
    if webapp is None:
        return None
    app = webapp.parent
    kok_seg, haric = _kapi_kumeleri()
    try:
        ust = ([s.lower() for s in app.relative_to(_sade(Path(root))).parts]
               if root is not None else None)
    except (ValueError, OSError):
        ust = None
    if ust is None:
        # Kök DIŞI (ör. kanonik `.wt` worktree'si): mutlak yolun TÜM parçaları — çekirdek kapının
        # `pbe_siniflandir`'ıyla AYNI kural (ABAP ile simetrik). `fetch_ui_source --damgala` bu
        # webapp'i de damgalar (anahtar mutlak) — aksi hâlde kapı bloklar, damga yolu olmaz.
        ust = [s.lower() for s in app.parts]
    if not (kok_seg & set(ust)) or (haric & set(ust)):
        return None
    try:
        rel = _cozulmus(ps).relative_to(_cozulmus(webapp)).as_posix()
    except ValueError:
        rel = ps.relative_to(webapp).as_posix()
    return app, rel


def _goreli(p: Path, root) -> str:
    try:
        return p.resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError, TypeError):
        return p.as_posix()


def komut_uret(app: Path, root, bsp: str) -> str:
    """Blok mesajındaki komut — YALNIZ çalıştırılabilir komut (proje kökünden ya da
    `CLAUDE_PROJECT_DIR` ile koşulur — aksi hâlde damga başka store'a gider).

    `--session` BURADA BASILMAZ: kapı kendi seans kimliğini ekler (çift olmasın); elle koşulursa
    araç SessionStart marker'ına düşer. Açıklama `not_uret()`te — komutun arkasına eklenmez ki
    kapının eklediği `--session` açıklamanın arkasına düşmesin."""
    a = _goreli(app, root)
    kaynak = f'--app-dir "{a}"' if bsp != BSP_YER_TUTUCU else f"--bsp {BSP_YER_TUTUCU}"
    return f'python {ARAC} {kaynak} --karsilastir "{a}/{WEBAPP}" --damgala'


def not_uret(neden: str = "") -> str:
    """Blok mesajı açıklaması + `--offline` kaçışı (sözleşmede opsiyonel `"not"` anahtarı)."""
    return ((f"[{neden} — BSP adını ver; app henüz hiç deploy edilmediyse `--offline` ekle] " if neden else "")
            + "Komutu PROJE KÖKÜNDEN (ya da CLAUDE_PROJECT_DIR=<proje> ile) koş — başka dizinden koşulursa "
            "damga başka store'a yazılır, kapı görmez (araç yazdığı store'u basar). "
            "Komut canlı ↔ yerel karşılaştırır, TEMİZSE webapp'i damgalar — dosyaya YAZMAZ. Fark çıkarsa: "
            "playbook/howto-ui-kaynagi-geri-kurma.md §2.1. SAP erişilemiyorsa ya da yerel canlıdan İLERİDEYSE "
            "(commit'li, henüz deploy edilmemiş iş): aynı komuta `--offline` ekle — canlıdan ezme riskini "
            "bilerek kabul edersin.")


def sinifla(path, root) -> Optional[dict]:
    """PULL-BEFORE-EDIT eklenti sözleşmesi (modül başlığı)."""
    c = uygulama_coz(path, root)
    if c is None:
        return None
    app, rel = c
    onekler, _ = deploy_haric_desenleri(app)
    if deploy_haric_mi(rel, onekler):
        return None
    bsp = ""
    try:
        from deploy_ui import bsp_name   # tek kaynak: fetch_ui_source --app-dir ile AYNI çözüm
        bsp = bsp_name(app)
    except Exception:   # noqa: BLE001 — çözülemeyen app sessiz geçmez, yer tutucuya düşer
        bsp = ""
    if not bsp:
        neden = (f"{DEPLOY_YAML} yok" if not (app / DEPLOY_YAML).is_file()
                 else f"{DEPLOY_YAML}'da BSP adı (Z…) çözülemedi")
        return {"nesne": BSP_YER_TUTUCU, "tip": "bsp",
                "komut": komut_uret(app, root, BSP_YER_TUTUCU), "not": not_uret(neden)}
    return {"nesne": bsp, "tip": "bsp", "komut": komut_uret(app, root, bsp), "not": not_uret()}

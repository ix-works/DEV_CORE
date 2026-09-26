# -*- coding: utf-8 -*-
"""pbe_ui.py — PULL-BEFORE-EDIT (ADR 0016) eklentisi: freestyle UI5 `webapp/` dosyaları (Q352-B).

⛔ NEDEN VAR (canlı vaka, 2026-09-26): başka bir makinede bir rapor uygulamasına kolon eklenip
   canlıya deploy edilmişti; repo habersizdi. Eski yerel kodla yapılacak bir sonraki deploy o
   kolonu canlıdan SESSİZCE silerdi. ABAP tarafında aynı sınıfı `pull_before_edit` kapatıyordu;
   UI dosyaları kapsam dışıydı. Ölçüm: tüketici projede 6 BSP'nin 6'sı canlı = yerel (rc 0);
   aynı canlı zip ↔ kolon senkronundan ÖNCEKİ repo webapp'i → GERCEK-FARK=4 (kontrol grubu).

SÖZLEŞME (kapı `pull_before_edit._EK_DENETCILER` bu modülü yükler):
    sinifla(path, root) -> None | {"nesne": <BSP>, "tip": "bsp", "komut": <blok mesajı komutu>}
  · Tazelik kontrolünü KAPI yapar (dosya anahtarıyla, store'dan). Damgayı
    `fetch_ui_source.py --damgala` yazar (canlıyla eşitlik ölçüldükten sonra).

KAPSAM (karar Q352-B AR-1, lider onaylı):
  · `<kök-segment>/…/<app>/webapp/**` — `<app>` = `webapp`'in ebeveyni. `<kök-segment>` =
    çekirdek kapının kök segmentleri (proje `source_root` + geçiş-eski `erp`).
  · App'in KENDİSİ `_EXCLUDED_DIR_SEGMENTS` (ref_docs/docs/.tmp/legacy/archive/drafts) ya da
    `node_modules` altındaysa canlı uygulama değildir → None.
  · `ui5-deploy.yaml` deploy görevinin `configuration.exclude` listesindeki yollar → None:
    o dosyalar canlıya HİÇ gitmez (ölçüldü: canlı zip'te `test/` YOK, `localService/` VAR —
    builder `resources.excludes` etkin değil, deploy `exclude` etkin). Anlaşılmayan bir desen
    (regex/glob karakteri) MUAFİYET VERMEZ (fail-closed) — dosya kapıda kalır.
  · `ui5-deploy.yaml` yok ya da BSP adı çözülemiyor → dict YİNE döner (sessiz geçiş YOK),
    komut `--bsp <BSP_ADI>` yer tutuculu.

BAKILMAYAN: deploy `exclude` girdisinin kök-dışı (iç içe `view/test/…`) eşleşmesi — yalnız
webapp köküne göre ÖNEK olarak yorumlanır (daha dar muafiyet = daha çok kapı, güvenli yön).
"""
from __future__ import annotations

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
# Anlaşılan deploy-exclude biçimi: `/seg/`, `seg`, `/seg/**`, `/a/b/` … (yalnız düz yol segmentleri).
_DUZ_DESEN = re.compile(r"^/?(?P<yol>[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*)/?(?:\*\*)?$")

_SCRIPTS = str(Path(__file__).resolve().parents[1])
if _SCRIPTS not in sys.path:
    sys.path.append(_SCRIPTS)


def _kapi_kumeleri() -> tuple[frozenset, frozenset]:
    """(kök segmentleri, hariç üst segmentler) — çekirdek kapıyla TEK KAYNAK (source_drift)."""
    import source_drift as sd  # kapı zaten bunu yükler; yüklenemezse kapı hiç karar veremez
    kok = getattr(sd, "PBE_KOK_SEGMENTLERI", None) or frozenset({sd.SOURCE_ROOT_NAME.lower(), "erp"})
    return frozenset(kok), frozenset(sd._EXCLUDED_DIR_SEGMENTS) | _UI_EK_HARIC


def deploy_haric_desenleri(app_dir: Path) -> tuple[list[str], list[str]]:
    """`ui5-deploy.yaml` → (anlaşılan önekler, ANLAŞILMAYAN ham desenler).

    Yalnız `exclude:` anahtarı (tekil) okunur — builder'ın `excludes:` (çoğul) listesi DEĞİL
    (ölçüldü: builder excludes'taki `localService/**` canlıda VAR)."""
    y = Path(app_dir) / DEPLOY_YAML
    try:
        satirlar = y.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    except OSError:
        return [], []
    onekler: list[str] = []
    anlasilmayan: list[str] = []
    girinti: Optional[int] = None
    for s in satirlar:
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        g = len(s) - len(s.lstrip())
        m = re.match(r"^\s*exclude:\s*(?P<satir_ici>[^#\s].*?)?\s*(?:#.*)?$", s)
        if m:
            if m.group("satir_ici"):          # `exclude: [/test/]` — satır-içi biçim ölçülmedi
                anlasilmayan.append(m.group("satir_ici"))
                girinti = None
            else:
                girinti = g
            continue
        if girinti is None:
            continue
        mm = re.match(r"^\s*-\s*(.+?)\s*$", s)
        if mm and g >= girinti:
            ham = mm.group(1).split(" #", 1)[0].strip().strip("'\"")
            d = _DUZ_DESEN.match(ham)
            if d:
                onekler.append(d.group("yol").lower() + "/")
            else:
                anlasilmayan.append(ham)
            continue
        girinti = None   # liste bitti
    return onekler, anlasilmayan


def deploy_haric_mi(rel: str, onekler) -> bool:
    """webapp'e göre posix `rel` deploy-exclude önekiyle mi başlıyor? (harf duyarsız)"""
    r = rel.replace("\\", "/").lstrip("/").lower()
    return any(r.startswith(o) for o in onekler)


def uygulama_coz(path, root=None) -> Optional[tuple[Path, str]]:
    """Dosya → (app dizini, webapp'e göre posix rel) ya da None (UI webapp kapsamı değil)."""
    p = Path(path)
    if not p.is_absolute() and root is not None:
        p = Path(root) / p
    webapp = next((a for a in p.parents if a.name.lower() == WEBAPP), None)
    if webapp is None:
        return None
    app = webapp.parent
    kok_seg, haric = _kapi_kumeleri()
    try:
        ust = [s.lower() for s in app.resolve().relative_to(Path(root).resolve()).parts] \
            if root is not None else None
    except (ValueError, OSError):
        ust = None
    if ust is None:
        ust = [s.lower() for s in app.parts]
    if not (kok_seg & set(ust)) or (haric & set(ust)):
        return None
    return app, p.relative_to(webapp).as_posix()


def _goreli(p: Path, root) -> str:
    try:
        return p.resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError, TypeError):
        return p.as_posix()


def komut_uret(app: Path, root, bsp: str) -> str:
    """Blok mesajındaki komut (proje kökünden koşulur; `--session` GEREKMEZ — seans marker'dan)."""
    a = _goreli(app, root)
    kaynak = f'--app-dir "{a}"' if bsp != BSP_YER_TUTUCU else f"--bsp {BSP_YER_TUTUCU}"
    return (f'python {ARAC} {kaynak} --karsilastir "{a}/{WEBAPP}" --damgala'
            f"   (canlı ↔ yerel karşılaştırır, TEMİZSE webapp'i damgalar — dosyaya YAZMAZ. Fark çıkarsa "
            f"playbook/howto-ui-kaynagi-geri-kurma.md §2.1. SAP erişilemiyorsa ya da yerel canlıdan "
            f"İLERİDEYSE (commit'li, henüz deploy edilmemiş iş): aynı komuta `--offline` ekle — "
            f"canlıdan ezme riskini bilerek kabul edersin)")


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
                "komut": komut_uret(app, root, BSP_YER_TUTUCU)
                + f"   [{neden} — BSP adını ver; app henüz hiç deploy edilmediyse `--offline` ekle]"}
    return {"nesne": bsp, "tip": "bsp", "komut": komut_uret(app, root, bsp)}

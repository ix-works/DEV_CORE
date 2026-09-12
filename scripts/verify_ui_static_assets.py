# -*- coding: utf-8 -*-
"""verify_ui_static_assets.py — BSP'deki STATİK app varlıkları canlıda güncel mi? (salt-okuma)

⛔ NEDEN VAR (infra-findings 2026-08-07, 2026-08-10'da 12 app'te yeniden ölçüldü):
   `deploy_ui.py`'nin doğrulaması YALNIZ `Component-preload.js`'i kanıtlar. Uygulamanın
   `webapp/help/kullanici-kilavuzu.html` gibi STATİK dosyaları preload paketine **girmez**
   (dist'e kopyalanır, ayrı servis edilir) ⇒ in-app yardım bayat kalsa bile deploy_ui
   **"CANLI==kaynak ✓ (güncel)"** der. Yani orada sessiz bir doğrulama boşluğu vardır.
   Bu script o boşluğu kapatan ÖLÇÜM aracıdır: dosyaların KENDİSİNİ canlıdan çeker.

⚠ KARŞILAŞTIRMANIN İNCELİĞİ — ham byte kıyası YANLIŞ POZİTİF verir:
   BSP/ICF runtime, servis ettiği HTML'in `<head>`'ine üç meta enjekte eder —
   `sap-client`, `sap-ui-fesr`, `sap.whitelistService` (~185 karakter, yalnız 1. satır).
   2026-08-10 ölçümünde ham kıyas **12/12 app'i "STALE"** gösterdi; oysa hiçbiri bayat
   değildi. Enjekte blok ayıklanınca fark **0/12**. PNG/ikili varlıkta böyle bir sorun yok.
   📌 Bu script'i "bozuk" sanmadan önce: dokunulmamış bir app de kırmızıysa kusur ölçümdedir.

⚠ İKİNCİ İNCELİK — `ui5 build` bazı metin varlıklarını DÖNÜŞTÜRÜR (Q285, 2026-09-13):
   `.properties` → non-ASCII `\\uXXXX` kaçışı + LF. Eski kıyas tabanı `webapp` olduğu için
   `--subdir i18n` HER dosyada yanlış "FARKLI" + yanlış "önce build" yönlendirmesi veriyordu
   (ölçüldü: 19 BSP × 2 dosya → canlı↔webapp bayt 38/38 "FARKLI"; canlı↔dist 38/38 AYNI;
   `\\uXXXX` çözülünce canlı↔webapp anahtar/değer 38/38 EŞİT).

Ne yapar (her app için, `<subdir>` varsayılan: help):
  1) `ui5-deploy.yaml` → hedef BSP adı
  2) `webapp/<subdir>/**` ∪ `dist/<subdir>/**` altındaki HER dosya
  3) canlı GET `/sap/bc/ui5_ui5/sap/<bsp>/<subdir>/<rel>?cb=<ts>` (no-cache, identity)
  4) EKSEN ① canlı ↔ dist (deploy edilen şey): HTML'de enjekte meta ayıklanır, satır sonu
     normalize edilir → fark = `FARKLI`. Dosya dist'te yoksa taban webapp'e düşer (not basılır).
  5) EKSEN ② canlı ↔ webapp (KAYNAK): `.properties` → `\\uXXXX` çözülmüş (anahtar, değer)
     dizisi; diğer metin → normalize; ikili → ham bayt. Fark = `KAYNAK FARKI` (canlı == dist
     ama webapp'te build edilmemiş değişiklik). ⛔ ② KALDIRILAMAZ: help dosyası webapp'te
     düzenlenip build edilmemişse canlı == (bayat) dist'tir; ② olmadan bu kaçar.

Kullanım:
    python core/scripts/verify_ui_static_assets.py --all
    python core/scripts/verify_ui_static_assets.py --app <app_adi>
    python core/scripts/verify_ui_static_assets.py --apps a,b --subdir i18n
    # farklı paket: --ui-root <source_root>/<MODULE>/<PKG>/ui  (varsayılan: project.yaml default_ui_root)

Çıkış kodu: 0 = tüm dosyalar canlıda AYNI · 1 = fark/eksik var (ya da yapılandırma hatası).
YAZMAZ, DEPLOY ETMEZ — yalnız ölçer. Deploy: `deploy_ui.py` (kanonik).
"""
import argparse
import base64
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Bağlantı okuma + BSP adı çözümleme + proje kökü DEPLOY_UI'DAN GELİR (kopya üretme:
# aynı .conn_adt sözleşmesi ve aynı ui5-deploy.yaml ayrıştırması tek yerde kalsın).
from deploy_ui import DEFAULT_UI_ROOT, REPO, bsp_name, read_conn  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# BSP runtime'ının HTML <head>'ine enjekte ettiği sabit blok (sıra deterministik).
INJECTED_META = re.compile(
    r'<meta name="sap-client"[^>]*>'
    r'<meta name="sap-ui-fesr"[^>]*>'
    r'<meta name="sap\.whitelistService"[^>]*>'
)
TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".json", ".txt", ".xml", ".properties"}
# Build'in içeriği KODLAMA düzeyinde dönüştürdüğü uzantılar: kaynak (webapp) kıyası bayt
# üzerinden değil ÇÖZÜLMÜŞ içerik üzerinden yapılır. Yalnız ÖLÇÜLEN uzantı listelenir.
BUILD_DONUSUMLU = {".properties"}
# ÇİFT sayıda ters bölüden sonra gelen `\uXXXX` (`\\u00fc` metnin kendisinde "ü" yazısıdır).
_U_KACIS = re.compile(r"(?<!\\)((?:\\\\)*)\\u([0-9a-fA-F]{4})")
_PROP_SATIR = re.compile(r"\s*((?:[^=:\s\\]|\\.)+)\s*[=:]?\s*(.*)$")


def normalize(raw: bytes, is_text: bool) -> bytes:
    """Kıyaslanabilir hâle getir: metinde enjekte meta + satır-sonu; ikilide ham byte."""
    if not is_text:
        return raw
    s = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return INJECTED_META.sub("", s).encode("utf-8", errors="replace")


def properties_cozumle(raw: bytes) -> list:
    """`.properties` → sıralı (anahtar, değer) listesi. `\\uXXXX` çözülür (ters bölü paritesi
    korunur, vekil çiftleri birleşir); yorum/boş satır atlanır. Diğer kaçışlar İKİ tarafta da
    aynen kalır ⇒ kıyas simetriktir. Sıra ve tekrar KORUNUR (sıra değişikliği de kaynak farkıdır)."""
    t = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    t = _U_KACIS.sub(lambda m: m.group(1) + chr(int(m.group(2), 16)), t)
    t = t.encode("utf-16", "surrogatepass").decode("utf-16", errors="replace")
    ciftler = []
    for satir in t.split("\n"):
        s = satir.lstrip()
        if not s or s[0] in "#!":
            continue
        m = _PROP_SATIR.match(satir)
        ciftler.append((m.group(1), m.group(2)) if m else (s, ""))
    return ciftler


def icerik_esit(a: bytes, b: bytes, sonek: str, cozumle: bool) -> bool:
    """`cozumle=True` (bir taraf dönüştürülmemiş kaynak) ve uzantı build-dönüşümlüyse
    çözülmüş içerik; aksi hâlde normalize edilmiş bayt kıyası."""
    if cozumle and sonek in BUILD_DONUSUMLU:
        return properties_cozumle(a) == properties_cozumle(b)
    is_text = sonek in TEXT_SUFFIXES
    return normalize(a, is_text) == normalize(b, is_text)


def _kisalt(adlar: list, n: int = 4) -> str:
    return ", ".join(adlar[:n]) + (f" (+{len(adlar) - n})" if len(adlar) > n else "")


def _prop_fark(a: bytes, b: bytes) -> str:
    da, db = dict(properties_cozumle(a)), dict(properties_cozumle(b))
    anahtarlar = sorted(k for k in da.keys() | db.keys() if da.get(k) != db.get(k))
    if not anahtarlar:
        return " — anahtar/değer kümesi aynı, SIRA ya da tekrar farkı"
    return f" — anahtar: {_kisalt(anahtarlar)}"


def fetch(base_url: str, user: str, pw: str, client: str, bsp: str, rel_url: str) -> bytes:
    """Canlı BSP dosyasını cache-bust + no-cache + identity-encoding ile çek."""
    url = (f"{base_url}/sap/bc/ui5_ui5/sap/{bsp.lower()}/{rel_url}"
           f"?sap-client={client}&cb={int(time.time() * 1000)}")
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


def _dosyalar(kok: Path) -> dict:
    if not kok.is_dir():
        return {}
    return {p.relative_to(kok).as_posix(): p for p in kok.rglob("*") if p.is_file()}


def check_app(app: str, ui_root: Path, subdir: str, conn) -> tuple:
    """(app, ok, not) — app'in <subdir> altındaki her dosyasını canlıyla iki eksende kıyasla."""
    app_dir = ui_root / app
    bsp = bsp_name(app_dir)
    if not bsp:
        return (app, False, "ui5-deploy.yaml yok/BSP adı okunamadı (deployable değil)")
    src = app_dir / "webapp" / subdir
    dist = app_dir / "dist" / subdir
    if not src.is_dir() and not dist.is_dir():
        return (app, True, f"webapp/{subdir} ve dist/{subdir} yok — kıyaslanacak statik varlık yok (atlandı)")

    base_url, user, pw, client = conn
    webapp_d, dist_d = _dosyalar(src), _dosyalar(dist)
    adlar = sorted(webapp_d.keys() | dist_d.keys())
    same, diff, kaynak_farki, missing, dist_stale = [], [], [], [], []
    taban_webapp, yalniz_dist, donusum = [], [], []
    for rel in adlar:
        w, d = webapp_d.get(rel), dist_d.get(rel)
        sonek = Path(rel).suffix.lower()
        try:
            live = fetch(base_url, user, pw, client, bsp, f"{subdir}/{rel}")
        except urllib.error.HTTPError as e:
            missing.append(f"{rel} (HTTP {e.code})")
            continue
        except Exception as e:  # ağ/TLS — ölçüm yapılamadı, "aynı" SAYILMAZ
            missing.append(f"{rel} ({type(e).__name__})")
            continue
        wb = w.read_bytes() if w is not None else None
        # EKSEN ① canlı ↔ deploy edilen şey (dist; yoksa webapp)
        if d is not None:
            db = d.read_bytes()
            if not icerik_esit(live, db, sonek, cozumle=False):
                diff.append(f"{rel} (canlı={len(live)}B dist={len(db)}B)")
                if wb is not None and not icerik_esit(db, wb, sonek, cozumle=True):
                    dist_stale.append(rel)
                continue
        else:
            taban_webapp.append(rel)
            if not icerik_esit(live, wb, sonek, cozumle=True):
                diff.append(f"{rel} (canlı={len(live)}B webapp={len(wb)}B — dist'te yok, taban webapp)")
                continue
        # EKSEN ② canlı ↔ kaynak (webapp)
        if wb is None:
            yalniz_dist.append(rel)
            same.append(rel)
            continue
        if not icerik_esit(live, wb, sonek, cozumle=True):
            kaynak_farki.append(rel + (_prop_fark(live, wb) if sonek in BUILD_DONUSUMLU else ""))
            continue
        if d is not None and sonek in BUILD_DONUSUMLU and db != wb:
            donusum.append(rel)
        same.append(rel)

    for rel in diff:
        print(f"      ⛔ FARKLI : {rel}")
    for rel in kaynak_farki:
        print(f"      ⛔ KAYNAK FARKI : {rel}  (canlı == dist ama webapp'te build edilmemiş değişiklik "
              "→ build + deploy)")
    for rel in missing:
        print(f"      ⛔ CANLIDA YOK/OKUNAMADI : {rel}")
    for rel in dist_stale:
        print(f"      ⚠ webapp ≠ dist : {rel}  (deploy dist'i gönderir → önce build)")
    if taban_webapp:
        print(f"      ℹ dist/{subdir}'de yok → taban webapp ({len(taban_webapp)}): {_kisalt(taban_webapp)}")
    if yalniz_dist:
        print(f"      ℹ yalnız dist'te (kaynak kıyası yok) ({len(yalniz_dist)}): {_kisalt(yalniz_dist)}")
    if donusum:
        print(f"      ℹ build dönüşümü BEKLENEN ({len(donusum)}): webapp baytı ≠ dist, "
              f"\\uXXXX çözülünce anahtar/değer EŞİT — {_kisalt(donusum)}")

    ok = not diff and not missing and not kaynak_farki
    taban = "dist" if dist.is_dir() else "webapp (dist yok)"
    note = f"{len(same)}/{len(adlar)} dosya canlıda AYNI (BSP={bsp}, taban={taban})"
    if diff:
        note += f" · FARKLI={len(diff)}"
    if kaynak_farki:
        note += f" · KAYNAK-FARKI={len(kaynak_farki)}"
    if missing:
        note += f" · YOK={len(missing)}"
    if dist_stale:
        note += f" · webapp≠dist={len(dist_stale)}"
    if donusum:
        note += f" · build-dönüşümü={len(donusum)}"
    return (app, ok, note)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="BSP'deki statik app varlıkları (varsayılan: in-app yardım) canlıda güncel mi — SALT OKUMA")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--app", help="Tek app")
    g.add_argument("--apps", help="Virgülle app listesi")
    g.add_argument("--all", action="store_true", help="ui-root'taki TÜM deployable app")
    ap.add_argument("--ui-root", default=DEFAULT_UI_ROOT,
                    help=f"UI workspace kökü (varsayılan: project.yaml default_ui_root={DEFAULT_UI_ROOT})")
    ap.add_argument("--subdir", default="help",
                    help="webapp/dist altında kıyaslanacak statik klasör (varsayılan: help)")
    args = ap.parse_args()

    if not args.ui_root:
        print("[FAIL] ui-root belirsiz: project.yaml'da default_ui_root yok → --ui-root ver.",
              file=sys.stderr)
        return 1
    ui_root = Path(args.ui_root) if Path(args.ui_root).is_absolute() else (REPO / args.ui_root)
    if not ui_root.is_dir():
        print(f"[FAIL] ui-root yok: {ui_root}", file=sys.stderr)
        return 1

    if args.app:
        apps = [args.app]
    elif args.apps:
        apps = [a.strip() for a in args.apps.split(",") if a.strip()]
    else:
        apps = sorted(d.name for d in ui_root.iterdir()
                      if d.is_dir() and d.name != "node_modules" and bsp_name(d))
        print(f"[i] --all → {len(apps)} deployable app")

    conn = read_conn()
    print(f"=== STATİK VARLIK DOĞRULAMA [{args.subdir}: canlı↔dist · canlı↔webapp kaynak] : "
          f"{', '.join(apps)} ===")
    results = []
    for app in apps:
        print(f"\n--- {app} ---")
        results.append(check_app(app, ui_root, args.subdir, conn))
        print(f"  {results[-1][2]}")

    print("\n=== SONUÇ ===")
    fail = 0
    for app, ok, note in results:
        print(f"  {'[OK]  ' if ok else '[FAIL]'} {app}  — {note}")
        if not ok:
            fail += 1
    if fail:
        print(f"\n[FAIL] {fail}/{len(results)} app'te statik varlık canlıda GÜNCEL DEĞİL.\n"
              "       FARKLI (canlı ≠ dist) → `deploy_ui.py --app <ad>` (build + deploy) → bu script'i tekrar koş.\n"
              "       KAYNAK FARKI (canlı == dist ≠ webapp) → dist bayat: build + deploy.\n"
              "       ⚠ 'FARKLI' çıkanlar dokunulmamış app'leri de kapsıyorsa önce ÖLÇÜMDEN şüphelen "
              "(enjekte meta bloğu ya da build dönüşümü değişmiş olabilir — dosya başlığındaki notlara bak).",
              file=sys.stderr)
        return 1
    print(f"\n[OK] {len(results)} app — {args.subdir} altındaki tüm dosyalar canlıda AYNI "
          "(canlı == dist, kaynak webapp ile eşdeğer).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

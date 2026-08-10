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

Ne yapar (her app için):
  1) `ui5-deploy.yaml` → hedef BSP adı
  2) `webapp/<subdir>/**` altındaki HER dosya (varsayılan subdir: help)
  3) canlı GET `/sap/bc/ui5_ui5/sap/<bsp>/<subdir>/<rel>?cb=<ts>` (no-cache, identity)
  4) HTML ise enjekte meta bloğu ayıklanır, satır-sonu normalize edilir → içerik kıyası
  5) ayrıca `webapp` ↔ `dist` eşitliği (deploy `dist`'i gönderir; `dist` bayatsa canlı da bayat kalır)

Kullanım:
    python core/scripts/verify_ui_static_assets.py --all
    python core/scripts/verify_ui_static_assets.py --app <app_adi>
    python core/scripts/verify_ui_static_assets.py --apps a,b --subdir help
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


def normalize(raw: bytes, is_text: bool) -> bytes:
    """Kıyaslanabilir hâle getir: metinde enjekte meta + satır-sonu; ikilide ham byte."""
    if not is_text:
        return raw
    s = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return INJECTED_META.sub("", s).encode("utf-8", errors="replace")


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


def check_app(app: str, ui_root: Path, subdir: str, conn) -> tuple:
    """(app, ok, not) — app'in webapp/<subdir> altındaki her dosyasını canlıyla kıyasla."""
    app_dir = ui_root / app
    bsp = bsp_name(app_dir)
    if not bsp:
        return (app, False, "ui5-deploy.yaml yok/BSP adı okunamadı (deployable değil)")
    src = app_dir / "webapp" / subdir
    if not src.is_dir():
        return (app, True, f"webapp/{subdir} yok — kıyaslanacak statik varlık yok (atlandı)")

    base_url, user, pw, client = conn
    files = sorted(p for p in src.rglob("*") if p.is_file())
    same = []
    diff = []
    missing = []
    dist_stale = []
    for f in files:
        rel = f.relative_to(src).as_posix()
        local = f.read_bytes()
        is_text = f.suffix.lower() in TEXT_SUFFIXES
        dist_f = app_dir / "dist" / subdir / Path(rel)
        if dist_f.exists() and dist_f.read_bytes() != local:
            dist_stale.append(rel)
        try:
            live = fetch(base_url, user, pw, client, bsp, f"{subdir}/{rel}")
        except urllib.error.HTTPError as e:
            missing.append(f"{rel} (HTTP {e.code})")
            continue
        except Exception as e:  # ağ/TLS — ölçüm yapılamadı, "aynı" SAYILMAZ
            missing.append(f"{rel} ({type(e).__name__})")
            continue
        if normalize(live, is_text) == normalize(local, is_text):
            same.append(rel)
        else:
            diff.append(f"{rel} (canlı={len(live)}B yerel={len(local)}B)")

    for rel in diff:
        print(f"      ⛔ FARKLI : {rel}")
    for rel in missing:
        print(f"      ⛔ CANLIDA YOK/OKUNAMADI : {rel}")
    for rel in dist_stale:
        print(f"      ⚠ webapp ≠ dist : {rel}  (deploy dist'i gönderir → önce build)")

    ok = not diff and not missing
    note = f"{len(same)}/{len(files)} dosya canlıda AYNI (BSP={bsp})"
    if diff:
        note += f" · FARKLI={len(diff)}"
    if missing:
        note += f" · YOK={len(missing)}"
    if dist_stale:
        note += f" · webapp≠dist={len(dist_stale)}"
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
                    help="webapp altında kıyaslanacak statik klasör (varsayılan: help)")
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
    print(f"=== STATİK VARLIK DOĞRULAMA [webapp/{args.subdir}] : {', '.join(apps)} ===")
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
              "       Çare: `deploy_ui.py --app <ad>` (build + deploy) → bu script'i tekrar koş.\n"
              "       ⚠ 'FARKLI' çıkanlar dokunulmamış app'leri de kapsıyorsa önce ÖLÇÜMDEN şüphelen "
              "(enjekte meta bloğu değişmiş olabilir — dosya başlığındaki nota bak).", file=sys.stderr)
        return 1
    print(f"\n[OK] {len(results)} app — webapp/{args.subdir} altındaki tüm dosyalar canlıda AYNI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

Kullanım:
    python scripts/deploy_ui.py --apps sip_se,dsk_se,fih_se
    python scripts/deploy_ui.py --app dsk_se
    python scripts/deploy_ui.py --all-changed          # git'e göre webapp'i değişen app'ler
    python scripts/deploy_ui.py --apps sip_se --dry-run # build+doğrula plan, deploy YOK
    # --ui-root ile farklı paket: --ui-root <source_root>/SD/ZSD015_CLC/ui (varsayılan)
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

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parents[1]
DEFAULT_UI_ROOT = SOURCE_ROOT_NAME + "/SD/ZSD015_CLC/ui"
PRELOAD = "Component-preload.js"


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


def bsp_name(app_dir: Path) -> str:
    """ui5-deploy.yaml'dan hedef BSP adını (Z ile başlayan app.name) çıkar."""
    y = app_dir / "ui5-deploy.yaml"
    if not y.exists():
        return ""
    for line in y.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*name:\s*(Z[A-Z0-9_]+)\s*$", line)
        if m:
            return m.group(1)
    return ""


def sha(b: bytes) -> str:
    """Satır-sonu NORMALIZE'lı sha256 — SAP BSP dosyayı \\r\\n ile saklar, dist \\n; bu
    CRLF/LF farkı byte-noise'tur (içerik aynı). Normalize etmeden karşılaştırmak yanlış-pozitif
    STALE üretir (2026-07-06 dsk vakası: 20 byte = 20×\\r). Gerçek içerik farkı korunur."""
    b = b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(b).hexdigest()


def run(cmd: str, cwd: Path, env: dict) -> tuple:
    """shell komutu çalıştır → (rc, tail_output). Windows cmd.exe/npm.cmd için shell=True."""
    p = subprocess.run(cmd, cwd=str(cwd), env=env, shell=True,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def fetch_live_preload(base_url: str, user: str, pw: str, client: str, bsp: str) -> bytes:
    """Canlı BSP Component-preload.js'i cache-bust + no-cache + identity-encoding ile çek."""
    ts = str(int(time.time()))
    url = f"{base_url}/sap/bc/ui5_ui5/sap/{bsp.lower()}/{PRELOAD}?sap-client={client}&cb={ts}"
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
        return (app, False, "ui5-deploy.yaml'da BSP adı (Z...) bulunamadı")

    # 1) BUILD (zorunlu — mevcut webapp kaynağından taze dist)
    print(f"  [{app}] build (ui5 build --clean-dest --dest dist)…")
    rc, out = run("npm run build", app_dir, env)
    if rc != 0:
        return (app, False, f"BUILD FAIL rc={rc}: {out.strip()[-300:]}")
    dist_preload = app_dir / "dist" / PRELOAD
    if not dist_preload.exists():
        return (app, False, f"build sonrası dist/{PRELOAD} yok — build çıktısı beklenmedik")
    local_hash = sha(dist_preload.read_bytes())
    print(f"  [{app}] dist/{PRELOAD} sha(norm)={local_hash[:12]}…")

    if dry:
        return (app, True, f"dry-run (build OK, BSP={bsp}, deploy+doğrulama YOK)")

    # DEPLOY (verify_only ise ATLA — sadece canlıyı mevcut kaynakla karşılaştır)
    if not verify_only:
        print(f"  [{app}] deploy → {bsp} …")
        rc, out = run("npx --no-install fiori deploy --config ui5-deploy.yaml --yes", app_dir, env)
        if rc != 0 or "Deployment Successful" not in out:
            return (app, False, f"DEPLOY FAIL rc={rc}: {out.strip()[-400:]}")

    # CANLI DOĞRULAMA — "Successful" mesajına GÜVENME, içeriği kanıtla (satır-sonu normalize'lı)
    print(f"  [{app}] canlı {PRELOAD} {'karşılaştır (verify)' if verify_only else 'doğrula'} (cache-bust)…")
    try:
        live = fetch_live_preload(base_url, user, pw, client, bsp)
    except Exception as e:
        return (app, False, f"canlı çekme HATASI ({type(e).__name__}): {e} — doğrulanamadı")
    live_hash = sha(live)
    if live_hash != local_hash:
        tag = "⛔ STALE: canlı ≠ mevcut kaynak" if verify_only else "⛔ STALE/CACHE: canlı ≠ dist"
        extra = ("canlı BSP, git/working-tree kaynaktan build ile UYUŞMUYOR — geçmişte bayat "
                 "deploy edilmiş VEYA henüz deploy edilmemiş değişiklik var."
                 if verify_only else
                 "Deploy 'Successful' dedi ama canlı içerik ESKİ — build atlanmış/cache/deploy hatası.")
        return (app, False,
                f"{tag}! dist(norm)={local_hash[:12]} vs canlı(norm)={live_hash[:12]}. {extra}")
    ok_note = "CANLI==kaynak ✓ (güncel)" if verify_only else "CANLI==dist ✓ (deploy doğrulandı)"
    return (app, True, f"{ok_note} sha={local_hash[:12]}, BSP={bsp}")


def changed_apps(ui_root: Path) -> list:
    """git status'a göre webapp/ altı değişen app'ler (uncommitted + son commit)."""
    rc, out = run(f'git -C "{REPO}" diff --name-only HEAD~1 HEAD', REPO, os.environ.copy())
    rc2, out2 = run(f'git -C "{REPO}" status --porcelain', REPO, os.environ.copy())
    names = set()
    rel = ui_root.relative_to(REPO).as_posix()
    for block in (out, out2):
        for line in block.splitlines():
            m = re.search(re.escape(rel) + r"/([^/]+)/webapp/", line.replace("\\", "/"))
            if m:
                names.add(m.group(1))
    return sorted(names)


def main() -> int:
    ap = argparse.ArgumentParser(description="Freestyle UI5 app GÜVENLİ deploy (build+deploy+canlı doğrula)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--app", help="Tek app (ör. dsk_se)")
    g.add_argument("--apps", help="Virgülle app listesi (ör. sip_se,dsk_se,fih_se)")
    g.add_argument("--all-changed", action="store_true", help="git'e göre webapp değişen app'ler")
    g.add_argument("--all", action="store_true", help="ui-root'taki TÜM deployable app (ui5-deploy.yaml olan)")
    ap.add_argument("--ui-root", default=DEFAULT_UI_ROOT, help=f"UI workspace kökü (varsayılan {DEFAULT_UI_ROOT})")
    ap.add_argument("--dry-run", action="store_true", help="build+doğrula planı, deploy YAPMA")
    ap.add_argument("--verify-only", action="store_true",
                    help="DEPLOY ETME — sadece canlı BSP == mevcut kaynaktan build mi karşılaştır (stale tarama)")
    args = ap.parse_args()

    ui_root = (REPO / args.ui_root) if not Path(args.ui_root).is_absolute() else Path(args.ui_root)
    if not ui_root.is_dir():
        print(f"[FAIL] ui-root yok: {ui_root}", file=sys.stderr)
        return 1

    if args.app:
        apps = [args.app]
    elif args.apps:
        apps = [a.strip() for a in args.apps.split(",") if a.strip()]
    elif args.all:
        apps = sorted(d.name for d in ui_root.iterdir()
                      if d.is_dir() and d.name != "node_modules" and bsp_name(d))
        print(f"[i] --all → {len(apps)} deployable app: {', '.join(apps)}")
    else:
        apps = changed_apps(ui_root)
        if not apps:
            print("[i] git'e göre webapp değişen app yok — deploy edilecek bir şey yok.")
            return 0
        print(f"[i] --all-changed → {', '.join(apps)}")

    conn = read_conn()
    env = os.environ.copy()
    env["FIORI_TOOLS_USER"] = conn[1]
    env["FIORI_TOOLS_PASSWORD"] = conn[2]
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

    mode = "[VERIFY-ONLY]" if args.verify_only else ("[DRY-RUN]" if args.dry_run else "[DEPLOY]")
    print(f"=== UI {mode}: {', '.join(apps)} (ui-root={ui_root}) ===")
    results = []
    for app in apps:
        print(f"\n--- {app} ---")
        results.append(deploy_one(app, ui_root, conn, env, args.dry_run, args.verify_only))

    print("\n=== SONUÇ ===")
    fail = 0
    for app, ok, note in results:
        print(f"  {'[OK]  ' if ok else '[FAIL]'} {app}  — {note}")
        if not ok:
            fail += 1
    if fail:
        act = "STALE tespit edildi (canlı ≠ kaynak)" if args.verify_only else "deploy DOĞRULANAMADI (bayat gitmiş olabilir)"
        print(f"\n[FAIL] {fail}/{len(results)} app {act} — yukarıyı incele, kullanıcıya raporla "
              "(asla 'başarılı' deme).", file=sys.stderr)
        return 1
    tail = "canlı == mevcut kaynak (hepsi güncel)" if args.verify_only else "canlı Component-preload == build çıktısı"
    print(f"\n[OK] {len(results)} app doğrulandı ({tail}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

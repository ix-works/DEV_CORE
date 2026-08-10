"""
run_ui_smoke.py — G1 runtime smoke-test gate runner (ADR 0017).

.conn_adt SAP kimliğini env'e koyar → LOCKOUT-SAFE tek-doğrula (401'de DUR, playwright koşturma)
→ playwright-cli (headless) çalıştırır. Araç: SADECE playwright-cli (MCP-browser DEĞİL).

Kullanım:
    python scripts/ui-smoke/run_ui_smoke.py --port 8099
    python scripts/ui-smoke/run_ui_smoke.py --base-url http://localhost:8097

ÖN KOŞUL (tek sefer): scripts/ui-smoke/ içinde `npm install` + `npx playwright install chromium`.
"""
import argparse
import base64
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# `HERE` = bu script'in CORE içindeki dizini → playwright config'i buradan çözülür (MEŞRU:
# hedef core'un KENDİ ağacı). PROJE kökü için `__file__` KULLANILMAZ: core script'i proje
# içinden `core/` junction'ıyla koşar, `Path(__file__)` DAİMA DEV_CORE'a çözülür (ADR 0020).
# `.conn_adt` PROJE kökündedir → kanonik `project_config.project_root()` (env→cwd).
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # core `scripts/` → `utils` paketi
from utils.project_config import project_root  # noqa: E402


def _kok_ve_kaynak():
    """(proje_kökü, kaynağın insan-okur adı) — hangi kökün DENENDİĞİ hata mesajına yazılır."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return project_root(), ("env CLAUDE_PROJECT_DIR" if env else "cwd (CLAUDE_PROJECT_DIR yok)")


def read_creds():
    kok, kaynak = _kok_ve_kaynak()
    conn = kok / ".conn_adt"
    if not conn.exists():
        # GÜRÜLTÜLÜ başarısızlık: cwd yanlışsa sessizce başka köke düşmüş olmayı DEĞİL,
        # hangi kökün denendiğini gör (sessiz-yanlış > gürültülü-hata dersi).
        sys.exit(f".conn_adt yok: {conn}\n"
                 f"  denenen proje kökü : {kok}  ({kaynak})\n"
                 f"  ÇÖZÜM: proje kökünden koş ya da CLAUDE_PROJECT_DIR=<proje kökü> ver.")
    u = p = None
    for ln in conn.read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.strip()
        if s.upper().startswith("ADT_SAP_USER="):
            u = s.split("=", 1)[1].strip()
        elif s.upper().startswith("ADT_SAP_PASSWORD="):
            p = s.split("=", 1)[1].strip()
    if not u or not p:
        sys.exit(".conn_adt'de ADT_SAP_USER/ADT_SAP_PASSWORD bulunamadı")
    return u, p


def verify_auth_once(base_url, u, p):
    """LOCKOUT-SAFE: TEK istek. 401 → kimlik yanlış → DUR. Başka → authed → devam."""
    url = base_url.rstrip("/") + "/sap/opu/odata/sap/"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode())
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        print(f"[uyarı] auth ön-doğrulama isteği başarısız ({e})")
        return None


def main():
    ap = argparse.ArgumentParser(description="G1 UI runtime smoke-test runner (playwright-cli)")
    ap.add_argument("--port", type=int, help="app portu (örn. 8099)")
    ap.add_argument("--base-url", help="tam base url (örn. http://localhost:8097)")
    ap.add_argument("--spec", help="opsiyonel: belirli spec dosyası")
    args = ap.parse_args()
    base = args.base_url or (f"http://localhost:{args.port}" if args.port else "http://localhost:8099")

    u, p = read_creds()
    status = verify_auth_once(base, u, p)
    if status == 401:
        sys.exit(f"[DUR] {base} auth 401 — .conn_adt kimliği reddedildi. playwright KOŞTURULMADI "
                 f"(hesap kilidi önlemi — 2 yanlış giriş kilitler). Kimliği düzelt.")
    if status is None:
        sys.exit(f"[DUR] {base} ulaşılamadı — app çalışıyor mu? (npm run start-noflp -- --port ...)")
    print(f"[ok] auth ön-doğrulama: {base} → HTTP {status} (401 değil = kimlik kabul). playwright başlıyor...")

    env = dict(os.environ, SAP_USER=u, SAP_PASS=p, SMOKE_BASE_URL=base)
    # --spec, config'teki `testMatch`'i GENİŞLETMEK için env'e verilir; konumsal
    # argüman Playwright'ta testMatch'in ÜSTÜNE filtre uygular, yani env'siz
    # bırakılsa kesişim BOŞ olur ve açık `--spec` çağrısı sessizce 0 test koşardı.
    # (Varsayılan testMatch = yalnız jenerik smoke — bkz. playwright.config.ts)
    if args.spec:
        env["SMOKE_SPEC"] = args.spec
    cmd = ["npx", "playwright", "test", "--config", str(HERE / "playwright.config.ts")]
    if args.spec:
        cmd.append(args.spec)
    rc = subprocess.run(cmd, cwd=str(HERE), env=env, shell=(os.name == "nt")).returncode
    sys.exit(rc)


if __name__ == "__main__":
    main()

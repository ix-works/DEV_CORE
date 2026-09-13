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
    python scripts/deploy_ui.py --all-changed          # git'e göre webapp'i değişen app'ler
    python scripts/deploy_ui.py --apps sip_se --dry-run # build+doğrula plan, deploy YOK
    # --ui-root ile farklı paket: --ui-root <source_root>/SD/ZSD001_CLC/ui (varsayılan)
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

# D24: proje kökü env→cwd (junction'da __file__ DEV_CORE'a çözülür; .conn_adt /
# ui-root / git hedefi PROJE'dir — __file__-türetimi YASAK).
from utils.project_config import cfg as _cfg, project_root as _project_root
REPO = _project_root()
# B10/K12: varsayılan UI kökü PROJE-CONFIG'ten (project.yaml default_ui_root:
# "SOURCE_CODES/SD/<PKG>/ui"); yoksa --ui-root ZORUNLU (core paket VARSAYMAZ).
DEFAULT_UI_ROOT = _cfg("default_ui_root")  # None olabilir
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
    local_bytes = dist_preload.read_bytes()
    local_hash = sha(local_bytes)
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
    """git'e göre webapp/ altı değişen app'ler → (app_listesi, hatalar).

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
            m = re.search(re.escape(rel) + r"/([^/]+)/webapp/", line.replace("\\", "/"))
            if m:
                names.add(m.group(1))
    return sorted(names), hatalar


def main() -> int:
    ap = argparse.ArgumentParser(description="Freestyle UI5 app GÜVENLİ deploy (build+deploy+canlı doğrula)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--app", help="Tek app (ör. dsk_se)")
    g.add_argument("--apps", help="Virgülle app listesi (ör. sip_se,dsk_se,fih_se)")
    g.add_argument("--all-changed", action="store_true", help="git'e göre webapp değişen app'ler")
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

    if args.app:
        apps = [args.app]
    elif args.apps:
        apps = [a.strip() for a in args.apps.split(",") if a.strip()]
    elif args.all:
        apps = sorted(d.name for d in ui_root.iterdir()
                      if d.is_dir() and d.name != "node_modules" and bsp_name(d))
        print(f"[i] --all → {len(apps)} deployable app: {', '.join(apps)}")
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
    if fail:
        if args.verify_only:
            act = "STALE tespit edildi (canlı ≠ kaynak)"
        elif args.dry_run:
            act = "BUILD başarısız (deploy zaten yapılmadı)"
        else:
            act = "deploy DOĞRULANAMADI (bayat gitmiş olabilir)"
        print(f"\n[FAIL] {fail}/{len(results)} app {act} — yukarıyı incele, kullanıcıya raporla "
              "(asla 'başarılı' deme).", file=sys.stderr)
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
              "farkıyla içerik-eşit).")
        print(satir_sonu_notu)
    elif args.verify_only:
        print(f"\n[OK] {len(results)} app doğrulandı (canlı == mevcut kaynak — hepsi güncel).")
    elif args.dry_run:
        print(f"\n[i] DRY-RUN bitti: {len(results)} app BUILD edildi. "
              "DEPLOY YAPILMADI, CANLI İÇERİK OKUNMADI.")
        print("    Bu çıktı 'canlı == build' KANITI DEĞİLDİR ve app'in güncel olduğunu GÖSTERMEZ.")
        print("    Bayatlık (stale) taraması için: --verify-only · gerçek deploy için bayraksız koş.")
    else:
        print(f"\n[OK] {len(results)} app doğrulandı (canlı Component-preload == build çıktısı).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

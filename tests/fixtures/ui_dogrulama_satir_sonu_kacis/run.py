# -*- coding: utf-8 -*-
"""ui_dogrulama_satir_sonu_kacis — UI canlı doğrulama araçlarının iki yanlış kırmızısı (Q281 + Q285).

Q281 · `deploy_ui.py --verify-only` YANLIŞ STALE: `ui5 build` XML/properties'i preload'a JS
STRING olarak gömer; CRLF çalışma ağacından build edilince satır sonları string İÇİNDE `\\r\\n`
KAÇIŞI olur. `sha()` yalnız GERÇEK CR/LF baytını normalize ettiği için içerik-eşit preload
STALE görünüyordu. Fix: haritadaki `.xml`/`.properties`/`.json` string modüllerinde kaçış
indirilir, sınıf yalnız verify kipinde kabul edilir ve `[OK~]` ile AYRI kovada basılır.
⛔ JS kodu / `.js` string modülü / ham metin `.txt` / harita-dışı biçim / deploy kipi / ters bölü
paritesi KATI kalır (A4/A5/A11/A9/A7/A8 negatif vektörleri).

Q285 · `verify_ui_static_assets.py --subdir i18n` YANLIŞ KIRMIZI: `ui5 build` `.properties`'i
`\\uXXXX` kaçışına çevirir; araç `webapp` baytıyla kıyaslıyordu. Fix: taban = dist (deploy
edilen şey) + `webapp` ile ÇÖZÜLMÜŞ anahtar/değer kaynak kıyası.
⛔ Kaynak ekseni gevşetilmez: webapp'te build edilmemiş değişiklik FAIL kalır (B3/B6).

Harness: iki aracın `main()`'i GERÇEK giriş noktası olarak çağrılır; yalnız ağ/kimlik/build
sahtelenir (`run`, `fetch_live_preload`, `fetch`, `read_conn`). SAP'ye/BSP'ye dokunulmaz.

Koşum:     python tests/fixtures/ui_dogrulama_satir_sonu_kacis/run.py
MUTASYON:  --mutasyon-<ad>  (MUTASYONLAR sözlüğü; her biri kaynağın BUGÜNKÜ kopyasına tek yama
           uygular, yama tutmazsa exit 2 KURULAMADI). Her kip en az bir vektörü düşürmeli.
ESKİ KOD:  --taban <sha>   (bir kerelik ölçüm; git blob'u yoksa — sığ klon — exit 2)
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
DUI = "scripts/deploy_ui.py"
VUS = "scripts/verify_ui_static_assets.py"

# Her kip: (dosya, eski-metin, yeni-metin). Metin BUGÜNKÜ kaynakta TAM 1 kez geçmeli.
MUTASYONLAR = {
    # Q281 — sınıf hiç kabul edilmez (fix öncesi davranış)
    "--mutasyon-kacis-yok": (
        DUI, "        if verify_only and sinif == SATIR_SONU:\n", "        if False:\n"),
    # Q281 — naif yazım: kaçış JS KODU dahil TÜM baytta indirilir
    "--mutasyon-kacis-global": (
        DUI,
        "    b = satir_sonu_normalize(b)\n    bas = b.rfind(PRELOAD_HARITASI)\n",
        "    b = satir_sonu_normalize(b)\n    if kacis_indir:\n"
        + r'        b = _KACISLI_CRLF.sub(rb"\1\\n", b)' + "\n"
        + "    bas = b.rfind(PRELOAD_HARITASI)\n"),
    # Q281 — uzantı listesi kaldırılır: `.js` / `.txt` string modülü de gevşetilir
    "--mutasyon-uzanti-yok": (
        DUI, "        if kacis_indir and m.group(2).lower() in KACIS_INDIRILEN_UZANTILAR:\n",
        "        if kacis_indir:\n"),
    # Q281 — eski geniş kural: `.js`-DIŞI her uzantı (ham metin `.txt` dahil) gevşetilir
    "--mutasyon-js-disi-hepsi": (
        DUI, "        if kacis_indir and m.group(2).lower() in KACIS_INDIRILEN_UZANTILAR:\n",
        '        if kacis_indir and m.group(2).lower() != b"js":\n'),
    # Q281 — ters bölü paritesi yok sayılır
    "--mutasyon-parite": (
        DUI,
        r'_KACISLI_CRLF = re.compile(rb"(?<!\\)((?:\\\\)*)\\r\\n")',
        r'_KACISLI_CRLF = re.compile(rb"()\\r\\n")'),
    # Q281 — sınıf deploy kipinde de kabul edilir
    "--mutasyon-deploy-gevset": (
        DUI, "        if verify_only and sinif == SATIR_SONU:\n", "        if sinif == SATIR_SONU:\n"),
    # Q285 — eski taban: canlı webapp baytıyla kıyaslanır
    "--mutasyon-taban-webapp": (
        VUS,
        "            if not icerik_esit(live, db, sonek, cozumle=False):\n",
        "            if not icerik_esit(live, wb if wb is not None else db, sonek, cozumle=False):\n"),
    # Q285 — .properties kaçışı çözülmez
    "--mutasyon-cozme-yok": (
        VUS, "    if cozumle and sonek in BUILD_DONUSUMLU:\n", "    if False:\n"),
    # Q285 — kaynak (webapp) ekseni kaldırılır (gevşetme)
    "--mutasyon-kaynak-kiyasi-yok": (
        VUS,
        "        if not icerik_esit(live, wb, sonek, cozumle=True):\n            kaynak_farki.append(",
        "        if False:\n            kaynak_farki.append("),
    # Q285 — vekil çiftleri birleştirilmez
    "--mutasyon-vekil": (
        VUS, '    t = t.encode("utf-16", "surrogatepass").decode("utf-16", errors="replace")\n', ""),
    # Q285 — \uXXXX ters bölü paritesi yok sayılır
    "--mutasyon-u-parite": (
        VUS,
        r'_U_KACIS = re.compile(r"(?<!\\)((?:\\\\)*)\\u([0-9a-fA-F]{4})")',
        r'_U_KACIS = re.compile(r"()\\u([0-9a-fA-F]{4})")'),
}


def _dur(mesaj: str) -> None:
    print(f"[KURULAMADI] {mesaj}")
    sys.exit(2)


ARGS = sys.argv[1:]
KIP = None
TABAN_SHA = None
if ARGS:
    if ARGS[0] in MUTASYONLAR and len(ARGS) == 1:
        KIP = ARGS[0]
    elif ARGS[0] == "--taban" and len(ARGS) == 2:
        TABAN_SHA = ARGS[1]
    else:
        print(f"[KULLANIM] bilinmeyen argüman {ARGS}; geçerli: {sorted(MUTASYONLAR)} | --taban <sha>")
        sys.exit(2)

KUM = Path(tempfile.mkdtemp(prefix="ui_dogrulama_"))


def _kaynak(rel: str) -> str:
    if TABAN_SHA:
        r = subprocess.run(["git", "-C", str(KOK), "show", f"{TABAN_SHA}:{rel}"],
                           capture_output=True)
        if r.returncode != 0:
            _dur(f"git show {TABAN_SHA}:{rel} rc={r.returncode} (sığ klon?)")
        return r.stdout.decode("utf-8").replace("\r\n", "\n")
    return (KOK / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")


# ── modül yükleme: normal kip GERÇEK dosyalar; mutasyon/taban kum kopyası (import kökü dahil) ─
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)   # deploy_ui REPO'yu İMPORT ANINDA okur
if KIP or TABAN_SHA:
    SCRIPTS = KUM / "scripts"
    shutil.copytree(KOK / "scripts" / "utils", SCRIPTS / "utils",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for rel in (DUI, VUS):
        metin = _kaynak(rel)
        if KIP and MUTASYONLAR[KIP][0] == rel:
            eski, yeni = MUTASYONLAR[KIP][1], MUTASYONLAR[KIP][2]
            if metin.count(eski) != 1:
                _dur(f"YAMA TUTMADI {KIP}: desen {metin.count(eski)} kez geçiyor (1 bekleniyordu)")
            metin = metin.replace(eski, yeni)
        (SCRIPTS / Path(rel).name).write_bytes(metin.encode("utf-8"))
    print(f"### {'MUTASYON ' + KIP if KIP else 'TABAN ' + str(TABAN_SHA)} — kum: {SCRIPTS}\n")
else:
    SCRIPTS = KOK / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    _gercek_out, _gercek_err = sys.stdout, sys.stderr
    import deploy_ui as D  # noqa: E402
    import verify_ui_static_assets as V  # noqa: E402
    sys.stdout, sys.stderr = _gercek_out, _gercek_err
except Exception as exc:  # pragma: no cover
    sys.stdout, sys.stderr = _gercek_out, _gercek_err
    _dur(f"modül yüklenemedi: {type(exc).__name__}: {exc}")

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


CONN = ("https://sahte.invalid", "kullanici", "parola", "100")
CANLI_PRELOAD: dict[str, bytes] = {}
CANLI_DOSYA: dict[tuple[str, str], bytes] = {}


def _sahte_run(cmd, cwd, env):
    return (0, "Deployment Successful" if "deploy" in cmd else "build ok")


def _sahte_preload(base, user, pw, client, bsp):
    return CANLI_PRELOAD[bsp]


def _sahte_fetch(base, user, pw, client, bsp, rel_url):
    if (bsp, rel_url) not in CANLI_DOSYA:
        raise urllib.error.HTTPError(rel_url, 404, "Not Found", None, None)
    return CANLI_DOSYA[(bsp, rel_url)]


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
            rc = modul.main()
    except SystemExit as e:
        rc = e.code
    except Exception as e:  # çökme ≠ FAIL değil ama vektör sonucu olarak raporlanır
        rc = f"COKTU {type(e).__name__}: {e}"
    finally:
        sys.argv = eski
    return rc, t.getvalue() + h.getvalue()


def sonuc_satiri(cikti: str, app: str) -> str:
    bolum = cikti.split("=== SONUÇ ===", 1)[-1]
    for satir in bolum.splitlines():
        if f" {app}  — " in satir:
            return satir.strip()
    return ""


# ─────────────────────────── yardımcılar: sentetik artefaktlar ───────────────────────────
KACIS_CRLF = b"\\r\\n"     # 4 bayt: ters bölü r ters bölü n
KACIS_LF = b"\\n"


def xml_degeri(eol: bytes, attr: bytes = b'height="100%"') -> bytes:
    satirlar = [b"<mvc:View", b'  controllerName="ns.app.controller.App"',
                b'  xmlns:mvc="sap.ui.core.mvc"', b"  " + attr + b'><App id="app"/></mvc:View>', b""]
    return b"'" + eol.join(satirlar) + b"'"


def preload(eol: bytes, *, xml: bytes | None = None, js: bytes = b'function(){"use strict";return{a:1}}',
            ek: tuple | None = None, harita: bool = True) -> bytes:
    """`ek=(modül-adı, satır-sonu)` → haritaya iki satırlık ek string modülü."""
    girdiler = [b'\t"ns/app/view/App.view.xml":' + (xml if xml is not None else xml_degeri(eol)),
                b"\t\"ns/app/i18n/i18n.properties\":'appTitle=Uygulama" + eol + b"x=\\\\u00fc" + eol + b"'"]
    if ek is not None:
        girdiler.append(b'\t"' + ek[0] + b"\":'satir1;" + ek[1] + b"satir2;'")
    govde = b",\n".join(girdiler)
    satirlar = [b"//@ui5-bundle ns/app/Component-preload.js",
                b'sap.ui.predefine("ns/app/Component",[],' + js + b");"]
    if harita:
        satirlar.append(b"sap.ui.require.preload({\n" + govde + b"\n});")
    else:   # eski paketleyici biçimi — harita sözleşmesi YOK
        satirlar.append(b'jQuery.sap.registerPreloadedModules({"version":"2.0","modules":{\n'
                        + govde + b"\n}});")
    return b"\n".join(satirlar) + b"\n"


def bsp_gibi(b: bytes) -> bytes:
    """BSP canlı dosyayı gerçek CRLF ile servis eder (ölçüldü: 19/19 preload)."""
    return b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def ui5_kacis(metin: str) -> bytes:
    """`ui5 build` .properties dönüşümü (ölçüldü): non-ASCII → \\uXXXX (UTF-16 birimi), CRLF → LF."""
    metin = metin.replace("\r\n", "\n")
    parca = []
    for ch in metin:
        if ord(ch) < 128:
            parca.append(ch)
        else:
            birim = ch.encode("utf-16-be")
            for i in range(0, len(birim), 2):
                parca.append("\\u%04x" % int.from_bytes(birim[i:i + 2], "big"))
    return "".join(parca).encode("ascii")


def app_kur(ui: Path, ad: str, bsp: str, *, dist_preload: bytes | None = None,
            webapp: dict | None = None, dist: dict | None = None) -> None:
    d = ui / ad
    (d / "webapp").mkdir(parents=True, exist_ok=True)
    (d / "ui5-deploy.yaml").write_bytes(f"specVersion: '3.0'\napp:\n  name: {bsp}\n".encode())
    if dist_preload is not None:
        (d / "dist").mkdir(parents=True, exist_ok=True)
        (d / "dist" / "Component-preload.js").write_bytes(dist_preload)
    for kok, dosyalar in (("webapp", webapp or {}), ("dist", dist or {})):
        for rel, icerik in dosyalar.items():
            p = d / kok / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(icerik)


def deploy_vektor(etiket: str, dist_b: bytes, canli_b: bytes, *bayrak: str) -> tuple:
    ui = KUM / f"ui_{etiket}"
    bsp = f"ZFX_{etiket}"
    app_kur(ui, "app1", bsp, dist_preload=dist_b)
    CANLI_PRELOAD[bsp] = canli_b
    return cagir(D, ["deploy_ui.py", "--app", "app1", "--ui-root", str(ui), *bayrak])


# ════════════════════════ A — Q281 deploy_ui --verify-only ════════════════════════
CRLF_BUILD = preload(KACIS_CRLF)
LF_BUILD = preload(KACIS_LF)

rc, out = deploy_vektor("A1", CRLF_BUILD, bsp_gibi(LF_BUILD), "--verify-only")
satir = sonuc_satiri(out, "app1")
kontrol("A1 AYIRT EDİCİ: yalnız kaçışlı \\r\\n farkı → STALE DEĞİL (rc=0), [OK~] kovasında",
        rc == 0 and satir.startswith("[OK~]") and "STALE:" not in out, f"rc={rc} satır={satir!r}")
kontrol("A2 GÖRÜNÜRLÜK: sınıf adı + etkilenen modül + özet satırında AYRI sayım basılıyor",
        "YALNIZ SATIR SONU" in satir and "App.view.xml" in satir
        and "YALNIZ SATIR SONU farkıyla" in out and "canlı == mevcut kaynak" in out,
        f"çıktı sonu={out.strip()[-400:]!r}")

rc, out = deploy_vektor("A3", CRLF_BUILD, bsp_gibi(preload(KACIS_LF, xml=xml_degeri(KACIS_LF, b'height="50%"'))),
                        "--verify-only")
kontrol("A3 NEGATİF: kaçış farkı + GERÇEK XML farkı → hâlâ STALE, rc=1",
        rc == 1 and "STALE:" in out, f"rc={rc} satır={sonuc_satiri(out, 'app1')!r}")
kontrol("A3b GÖRÜNÜRLÜK: STALE notu farklı MODÜLÜ adlandırıyor (kaçış farkı olan i18n'i DEĞİL)",
        "Farklı modül (1): ns/app/view/App.view.xml" in out, f"satır={sonuc_satiri(out, 'app1')!r}")

rc, out = deploy_vektor("A4", preload(KACIS_LF, js=b'function(){return"a".split("\\r\\n")}'),
                        bsp_gibi(preload(KACIS_LF, js=b'function(){return"a".split("\\n")}')), "--verify-only")
kontrol("A4 NEGATİF (gevşetme sınırı): JS KODUNDA \\r\\n ↔ \\n farkı → STALE (JS kodu normalize edilmez)",
        rc == 1 and "STALE:" in out, f"rc={rc} satır={sonuc_satiri(out, 'app1')!r}")

rc, out = deploy_vektor("A5", preload(KACIS_LF, ek=(b"ns/app/util/metin.js", KACIS_CRLF)),
                        bsp_gibi(preload(KACIS_LF, ek=(b"ns/app/util/metin.js", KACIS_LF))), "--verify-only")
kontrol("A5 NEGATİF: string gömülü `.js` modülünde kaçış farkı → STALE (.js kodu gevşetilmez)",
        rc == 1 and "STALE:" in out, f"rc={rc} satır={sonuc_satiri(out, 'app1')!r}")

rc, out = deploy_vektor("A11", preload(KACIS_LF, ek=(b"ns/app/sablon/ornek.txt", KACIS_CRLF)),
                        bsp_gibi(preload(KACIS_LF, ek=(b"ns/app/sablon/ornek.txt", KACIS_LF))), "--verify-only")
kontrol("A11 NEGATİF: HAM metin `.txt` modülünde CRLF↔LF (kullanıcıya görünebilir) → STALE, liste dışı uzantı",
        rc == 1 and "STALE:" in out, f"rc={rc} satır={sonuc_satiri(out, 'app1')!r}")

rc, out = deploy_vektor("A6", LF_BUILD, bsp_gibi(LF_BUILD), "--verify-only")
satir = sonuc_satiri(out, "app1")
kontrol("A6 FP ÇAPASI/KONTROL GRUBU: yalnız GERÇEK CR farkı (BSP) → [OK] 'CANLI==kaynak', [OK~] DEĞİL, "
        "özet satırı eski metin",
        rc == 0 and satir.startswith("[OK] ") and "CANLI==kaynak" in satir
        and "canlı == mevcut kaynak — hepsi güncel)." in out and "[OK~]" not in out,
        f"rc={rc} satır={satir!r}")

rc, out = deploy_vektor("A7", CRLF_BUILD, bsp_gibi(LF_BUILD))
kontrol("A7 SIKI KALIR: GERÇEK DEPLOY kipinde kaçış farkı → STALE/CACHE, rc=1 (yüklenen dist canlıda değil)",
        rc == 1 and "STALE/CACHE" in out, f"rc={rc} satır={sonuc_satiri(out, 'app1')!r}")
kontrol("A7b GÖRÜNÜRLÜK: deploy FAIL notu farkın YALNIZ satır sonu olduğunu söylüyor (teşhis)",
        "YALNIZ kaçışlı satır sonu" in out, f"satır={sonuc_satiri(out, 'app1')!r}")

# metinde kaçışlanmış ters bölü + "r" (XML içeriğinde "\r" YAZISI) ≠ satır sonu.
# dist metni: `\r` yazısı + satır sonu · canlı metni: `\n` yazısı (satır sonu YOK) = GERÇEK fark.
# Pariteyi yok sayan naif regex dist'teki `\r\n`'i (ikinci ters bölüden başlayarak) yakalayıp
# `\\n` baytına indirir ve ikisini EŞİT sanır — bu vektör tam o yazımı düşürür.
A8_DIST = preload(KACIS_LF, xml=b"'<t>x" + b"\\\\" + b"r" + b"\\n" + b"y</t>'")
A8_CANLI = preload(KACIS_LF, xml=b"'<t>x" + b"\\\\" + b"n" + b"y</t>'")
rc, out = deploy_vektor("A8", A8_DIST, bsp_gibi(A8_CANLI), "--verify-only")
kontrol("A8 PARİTE: `\\\\r\\n` (ters bölü+r YAZISI + satır sonu) ↔ `\\\\n` (ters bölü+n YAZISI) → GERÇEK fark, STALE",
        rc == 1 and "STALE:" in out, f"rc={rc} satır={sonuc_satiri(out, 'app1')!r}")

rc, out = deploy_vektor("A9", preload(KACIS_CRLF, harita=False), bsp_gibi(preload(KACIS_LF, harita=False)),
                        "--verify-only")
kontrol("A9 3.BAĞLAM (harita sözleşmesi olmayan paketleyici): kaçış farkı GEVŞETİLMEZ → STALE, rc=1",
        rc == 1 and "STALE:" in out, f"rc={rc} satır={sonuc_satiri(out, 'app1')!r}")

ui = KUM / "ui_A10"
app_kur(ui, "app1", "ZFX_A10A", dist_preload=CRLF_BUILD)
app_kur(ui, "app2", "ZFX_A10B", dist_preload=CRLF_BUILD)
CANLI_PRELOAD["ZFX_A10A"] = bsp_gibi(LF_BUILD)
CANLI_PRELOAD["ZFX_A10B"] = bsp_gibi(preload(KACIS_LF, xml=xml_degeri(KACIS_LF, b'height="1%"')))
rc, out = cagir(D, ["deploy_ui.py", "--apps", "app1,app2", "--ui-root", str(ui), "--verify-only"])
kontrol("A10 KOVA AYRIMI (çok app): [OK~] ve [FAIL] aynı koşumda ayrı; rc=1; FAIL özetinde [OK~] notu",
        rc == 1 and sonuc_satiri(out, "app1").startswith("[OK~]")
        and sonuc_satiri(out, "app2").startswith("[FAIL]") and "STALE SAYILMADI: app1" in out,
        f"rc={rc} app1={sonuc_satiri(out, 'app1')!r} app2={sonuc_satiri(out, 'app2')!r}")


# ════════════════════════ B — Q285 verify_ui_static_assets ════════════════════════
def statik_vektor(etiket: str, subdir: str, *, webapp: dict, dist: dict | None, canli: dict) -> tuple:
    ui = KUM / f"ui_{etiket}"
    bsp = f"ZFX_{etiket}"
    app_kur(ui, "app1", bsp,
            webapp={f"{subdir}/{k}": v for k, v in webapp.items()},
            dist=None if dist is None else {f"{subdir}/{k}": v for k, v in dist.items()})
    for rel, icerik in canli.items():
        CANLI_DOSYA[(bsp, f"{subdir}/{rel}")] = icerik
    return cagir(V, ["verify_ui_static_assets.py", "--app", "app1", "--ui-root", str(ui), "--subdir", subdir])


PROP_KAYNAK = ("# ZSD001 Rapor — Türkçe metinler\r\nappTitle=Teslimat Detay Raporu\r\n"
               "fld.showBatchDetail=Parti Detayını Göster\r\n")
PROP_W = PROP_KAYNAK.encode("utf-8")                 # webapp: UTF-8 + CRLF (çalışma ağacı)
PROP_D = ui5_kacis(PROP_KAYNAK)                      # dist: \uXXXX + LF (build)

rc, out = statik_vektor("B1", "i18n", webapp={"i18n_tr.properties": PROP_W},
                        dist={"i18n_tr.properties": PROP_D}, canli={"i18n_tr.properties": bsp_gibi(PROP_D)})
kontrol("B1 AYIRT EDİCİ: build'in \\uXXXX dönüşümü → AYNI, rc=0 (FARKLI yok)",
        rc == 0 and "FARKLI" not in out, f"rc={rc} çıktı={out.strip()[-300:]!r}")
kontrol("B1b YANLIŞ YÖNLENDİRME YOK: beklenen dönüşümde '⚠ webapp ≠ dist … önce build' basılmıyor",
        "webapp ≠ dist" not in out, f"çıktı={out.strip()[-300:]!r}")
kontrol("B1c GÖRÜNÜRLÜK: beklenen build dönüşümü sayılıp AYRI basılıyor",
        "build dönüşümü BEKLENEN (1)" in out and "build-dönüşümü=1" in out, f"çıktı={out.strip()[-300:]!r}")

PROP_D_DEGISIK = ui5_kacis(PROP_KAYNAK.replace("Göster", "Gizle"))
rc, out = statik_vektor("B2", "i18n", webapp={"i18n_tr.properties": PROP_W},
                        dist={"i18n_tr.properties": PROP_D}, canli={"i18n_tr.properties": PROP_D_DEGISIK})
kontrol("B2 NEGATİF: canlı değer ≠ dist → FARKLI, rc=1", rc == 1 and "FARKLI" in out,
        f"rc={rc} çıktı={out.strip()[-300:]!r}")

PROP_W_YENI = PROP_KAYNAK.replace("Göster", "Göster (yeni)").encode("utf-8")
rc, out = statik_vektor("B3", "i18n", webapp={"i18n_tr.properties": PROP_W_YENI},
                        dist={"i18n_tr.properties": PROP_D}, canli={"i18n_tr.properties": PROP_D})
kontrol("B3 NEGATİF (gevşetme sınırı): canlı == dist ama webapp'te build edilmemiş değer → rc=1",
        rc == 1, f"rc={rc} çıktı={out.strip()[-300:]!r}")
kontrol("B3b GÖRÜNÜRLÜK: KAYNAK FARKI sınıfı + farklı ANAHTAR adı basılıyor",
        "KAYNAK FARKI" in out and "fld.showBatchDetail" in out, f"çıktı={out.strip()[-300:]!r}")

META = (b'<meta name="sap-client" content="100"><meta name="sap-ui-fesr" content="true">'
        b'<meta name="sap.whitelistService" content="/sap/public/bc/uics/whitelist/service">')
HTML = b"<!DOCTYPE html>\r\n<html><head><title>KD</title></head>\r\n<body><h1>Kilavuz</h1></body></html>\r\n"
HTML_CANLI = HTML.replace(b"<head>", b"<head>" + META)
PNG = bytes(range(256)) * 4
rc, out = statik_vektor("B4", "help", webapp={"kd.html": HTML, "img/a.png": PNG},
                        dist={"kd.html": HTML, "img/a.png": PNG}, canli={"kd.html": HTML_CANLI, "img/a.png": PNG})
kontrol("B4 KONTROL GRUBU (help): enjekte meta + CRLF + ikili → iki dosya da AYNI, rc=0 (eski davranış korunur)",
        rc == 0 and "2/2 dosya canlıda AYNI" in out, f"rc={rc} çıktı={out.strip()[-300:]!r}")

rc, out = statik_vektor("B5", "help", webapp={"kd.html": HTML}, dist={"kd.html": HTML},
                        canli={"kd.html": HTML_CANLI.replace(b"Kilavuz", b"Eski")})
kontrol("B5 NEGATİF (help): canlı gövde farklı → FARKLI, rc=1", rc == 1 and "FARKLI" in out,
        f"rc={rc} çıktı={out.strip()[-300:]!r}")

rc, out = statik_vektor("B6", "help", webapp={"kd.html": HTML.replace(b"Kilavuz", b"Yeni")},
                        dist={"kd.html": HTML}, canli={"kd.html": HTML_CANLI})
kontrol("B6 NEGATİF (gevşetme sınırı, help): webapp düzenlendi + build edilmedi, canlı == dist → rc=1",
        rc == 1, f"rc={rc} çıktı={out.strip()[-300:]!r}")

rc, out = statik_vektor("B7", "i18n", webapp={"i18n_tr.properties": PROP_W}, dist=None,
                        canli={"i18n_tr.properties": PROP_D})
kontrol("B7 3.BAĞLAM (dist hiç yok → taban webapp): çözülmüş kıyas → AYNI, rc=0, taban notu görünür",
        rc == 0 and "taban=webapp (dist yok)" in out, f"rc={rc} çıktı={out.strip()[-300:]!r}")

EMOJI = "ok=Tamam \U0001F600\n"
rc, out = statik_vektor("B8", "i18n", webapp={"i18n.properties": EMOJI.encode("utf-8")},
                        dist={"i18n.properties": ui5_kacis(EMOJI)}, canli={"i18n.properties": ui5_kacis(EMOJI)})
kontrol("B8 VEKİL ÇİFTİ: webapp ham emoji ↔ dist `\\ud83d\\ude00` → AYNI, rc=0",
        rc == 0, f"rc={rc} çıktı={out.strip()[-300:]!r}")

B9_CANLI = b"k=x\\" + "ü".encode("utf-8") + b"\n"     # değer: x\ü
B9_WEBAPP = b"k=x\\\\u00fc\n"                          # değer: x\\u00fc (ters bölü YAZISI + u00fc)
rc, out = statik_vektor("B9", "i18n", webapp={"i18n.properties": B9_WEBAPP},
                        dist={"i18n.properties": B9_CANLI}, canli={"i18n.properties": B9_CANLI})
kontrol("B9 PARİTE: `\\\\u00fc` (kaçışlanmış ters bölü) çözülmez → kaynak farkı, rc=1",
        rc == 1, f"rc={rc} çıktı={out.strip()[-300:]!r}")

rc, out = statik_vektor("B10", "i18n", webapp={"i18n.properties": PROP_W},
                        dist={"i18n.properties": PROP_D}, canli={})
kontrol("B10 REGRESYON: canlıda yok (404) → CANLIDA YOK, rc=1", rc == 1 and "CANLIDA YOK" in out,
        f"rc={rc} çıktı={out.strip()[-300:]!r}")

shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)

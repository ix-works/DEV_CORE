# -*- coding: utf-8 -*-
"""fetch_ui_source — BSP kaynağını SAP'den geri kurma aracının saf mantığı + gerçek giriş noktası (Issue #304).

Eksenler:
  A  geri kurma: `-dbg` eşlemesi (builder debugFileRegex son ekleri), atılanlar, metin LF / ikili HAM,
     kaynak haritası sondası (TS/transpile izi)
  B  karşılaştırma: `.properties` `\\uXXXX` çözülmüş SATIR kıyası (yorum dahil, ters bölü paritesi),
     manifest'te YALNIZ ölçülmüş iki build yolu, gerçek farkta unified diff, liste farkları
  C  `main()` — AĞSIZ (`--zip`): sıfır-fark anında KAPSAM BEYANI, fark → rc 1, dolu `--out` → rc 2,
     yazılan dosyalarda CRLF yok, bozuk zip → ÖLÇÜLEMEDİ (rc 2, "temiz" değil)
  D  `--eslik` — 3. BAĞLAM: gerçek alt süreç (`deploy_ui.run`, shell) ile SAHTE bir `ui5` CLI koşar;
     sahte CLI kendisine verilen webapp'i kaydeder ve senaryo dist'ini yazar. SAP'ye/ağa dokunulmaz.

Koşum:     python tests/fixtures/fetch_ui_source/run.py
MUTASYON:  --mutasyon-<ad>  (MUTASYONLAR; kaynağın BUGÜNKÜ kopyasına tek yama, desen TAM 1 kez
           geçmeli yoksa exit 2 KURULAMADI). Her kip en az bir vektörü düşürmeli.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import stat
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

KOK = Path(__file__).resolve().parents[3]
FUS = "scripts/fetch_ui_source.py"
BAGIMLI = ("scripts/deploy_ui.py", "scripts/verify_ui_static_assets.py")

MUTASYONLAR = {
    # A — -dbg dosyası yeniden adlandırılmaz
    "--mutasyon-dbg-yok": (FUS, "        hedef = dbg_hedef.get(rel, rel)\n", "        hedef = rel\n"),
    # A — son ek kümesi brifteki iki biçime daraltılır (builder'ın .fragment/.view… kaybolur)
    "--mutasyon-sonek-dar": (
        FUS, r'(?P<sonek>(?:\.view|\.fragment|\.controller|\.designtime|\.support)?\.js)$")',
        r'(?P<sonek>(?:\.controller)?\.js)$")'),
    # A — metin LF'e indirilmez
    "--mutasyon-lf-yok": (
        FUS, "        kaynak[hedef] = satir_sonu_normalize(b) if metin_mi(hedef) else b\n",
        "        kaynak[hedef] = b\n"),
    # A — ikili dosya da normalize edilir (PNG bozulur)
    "--mutasyon-ikili-normalize": (
        FUS, "        kaynak[hedef] = satir_sonu_normalize(b) if metin_mi(hedef) else b\n",
        "        kaynak[hedef] = satir_sonu_normalize(b)\n"),
    # A/D — kaynak haritası sondası susturulur
    "--mutasyon-harita-sonda-yok": (FUS, "    return sapma\n", "    return []\n"),
    # B — \uXXXX çözülmez
    "--mutasyon-u-cozme-yok": (
        FUS, "    t = _U_KACIS.sub(lambda m: m.group(1) + chr(int(m.group(2), 16)), t)\n", ""),
    # B — build yolu yerelde VARKEN de canlıdan silinir (FP: aynı değer sahte GERCEK-FARK olur)
    "--mutasyon-manifest-hepsi": (FUS, "        if canlida and not yerelde:\n", "        if canlida:\n"),
    # B — build yolu İKİ taraftan da silinir (gevşetme: yereldeki DEĞER farkı gizlenir)
    "--mutasyon-manifest-iki-taraf": (
        FUS, "        if canlida and not yerelde:\n            _yol_sil(c, yol)\n",
        "        if canlida and yerelde:\n            _yol_sil(y, yol)\n"
        "        if canlida:\n            _yol_sil(c, yol)\n"),
    # C — dolu --out dizinine yazılır
    "--mutasyon-out-dolu": (
        FUS, "    if out is not None and out.exists() and any(out.iterdir()):\n", "    if False:\n"),
    # C — sıfır-fark anında kapsam beyanı basılmaz
    "--mutasyon-kapsam-yok": (
        FUS, '    print("\\n" + kapsam_beyani(zip_kaynagi, eslik_durumu, yerel_kok is not None))\n    return rc\n',
        "    return rc\n"),
    # D — preload dışı tam-liste hükmü kaldırılır (yalnız preload kıyası)
    "--mutasyon-tam-liste-yok": (FUS, "        if liste_farki and sinif != ESLIK_YOK:\n", "        if False:\n"),
    # D — eşlik YOK iken DURMAZ (--out yazılır)
    "--mutasyon-eslik-dur-yok": (
        FUS, '        if sinif == ESLIK_YOK:\n            print("\\n" + kapsam_beyani(zip_kaynagi, eslik_durumu, False))\n',
        '        if False:\n            print("\\n" + kapsam_beyani(zip_kaynagi, eslik_durumu, False))\n'),
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

KUM = Path(tempfile.mkdtemp(prefix="fetch_ui_source_"))
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)   # deploy_ui REPO'yu import anında okur
if KIP:
    SCRIPTS = KUM / "scripts"
    shutil.copytree(KOK / "scripts" / "utils", SCRIPTS / "utils", ignore=shutil.ignore_patterns("__pycache__"))
    for rel in BAGIMLI + (FUS,):
        metin = (KOK / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
        if MUTASYONLAR[KIP][0] == rel:
            eski, yeni = MUTASYONLAR[KIP][1], MUTASYONLAR[KIP][2]
            if metin.count(eski) != 1:
                _dur(f"YAMA TUTMADI {KIP}: desen {metin.count(eski)} kez geçiyor (1 bekleniyordu)")
            metin = metin.replace(eski, yeni)
        (SCRIPTS / Path(rel).name).write_bytes(metin.encode("utf-8"))
    print(f"### MUTASYON {KIP} — kum: {SCRIPTS}\n")
else:
    SCRIPTS = KOK / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    _o, _e = sys.stdout, sys.stderr
    import fetch_ui_source as F  # noqa: E402
    sys.stdout, sys.stderr = _o, _e
except Exception as exc:  # pragma: no cover
    sys.stdout, sys.stderr = _o, _e
    _dur(f"modül yüklenemedi: {type(exc).__name__}: {exc}")
if Path(F.__file__).resolve().parent != SCRIPTS.resolve():
    _dur(f"yanlış modül yüklendi: {F.__file__} (beklenen {SCRIPTS})")

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def cagir(argv: list[str]) -> tuple:
    t, h = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(t), redirect_stderr(h):
            rc = F.main(argv)
    except SystemExit as e:
        rc = e.code
    except Exception as e:  # çökme vektör sonucu olarak raporlanır
        rc = f"COKTU {type(e).__name__}: {e}"
    return rc, t.getvalue() + h.getvalue()


# ───────────────────────── sentetik BSP (jenerik: ns/app, ZSD001_APP) ─────────────────────────
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01" + b"\r\n" * 3   # başlık gerçek \r\n taşır
CTRL_SRC = b'sap.ui.define([], function () {\n\t"use strict";\n\treturn { a: 1 };\n});\n'
FRAG_SRC = b"sap.ui.define([], function () { return 1; });\n"
VIEW = b'<mvc:View xmlns:mvc="sap.ui.core.mvc">\n  <Page title="{i18n>appTitle}"/>\n</mvc:View>\n'
I18N_YEREL = "# Başlık yorumu\nappTitle=Sipariş Listesi\nx=Müşteri\n".encode("utf-8")
I18N_CANLI = b"# Ba\\u015fl\\u0131k yorumu\nappTitle=Sipari\\u015f Listesi\nx=M\\u00fc\\u015fteri\n"
MANIFEST_YEREL = {"_version": "1.59.0", "sap.app": {"id": "ns.app", "title": "{{appTitle}}"},
                  "sap.ui5": {"models": {"i18n": {"type": "sap.ui.model.resource.ResourceModel",
                                                  "settings": {"bundleName": "ns.app.i18n.i18n"}}}}}


def manifest_canli(m: dict) -> dict:
    c = json.loads(json.dumps(m))
    c["sap.ui5"]["flexBundle"] = False
    c["sap.ui5"]["models"]["i18n"]["settings"]["supportedLocales"] = ["", "tr"]
    return c


def jb(o) -> bytes:
    return (json.dumps(o, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def crlf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def harita(hedef_ad: str, kaynak: str) -> bytes:
    return json.dumps({"version": 3, "file": hedef_ad, "sources": [kaynak], "mappings": "AAAA"}).encode()


def canli_bsp(**degis) -> dict[str, bytes]:
    """SAP BSP gibi: metin CRLF, build çıktısı (dbg + küçültülmüş + map + preload)."""
    d = {
        "Component-preload.js": crlf(b'sap.ui.require.preload({\n"ns/app/view/Main.view.xml":\'<x/>\'\n});\n'),
        "Component-preload.js.map": b'{"version":3,"sections":[]}',
        "Component-dbg.js": crlf(CTRL_SRC), "Component.js": b"sap.ui.define([],function(){return{a:1}});",
        "Component.js.map": harita("Component.js", "Component-dbg.js"),
        "controller/Main-dbg.controller.js": crlf(CTRL_SRC),
        "controller/Main.controller.js": b"min", "controller/Main.controller.js.map":
            harita("Main.controller.js", "Main-dbg.controller.js"),
        "fragment/Popup-dbg.fragment.js": crlf(FRAG_SRC), "fragment/Popup.fragment.js": b"min",
        "fragment/Popup.fragment.js.map": harita("Popup.fragment.js", "Popup-dbg.fragment.js"),
        "lib/vendor.js": crlf(b"var vendor = 1;\n"),           # -dbg karşılığı YOK → aynen
        "lib/my-dbg-helper.js": crlf(b"var h = 1;\n"),          # adında -dbg geçer ama biçim değil
        "view/Main.view.xml": crlf(VIEW), "i18n/i18n.properties": crlf(I18N_CANLI),
        "manifest.json": crlf(jb(manifest_canli(MANIFEST_YEREL))), "img/logo.png": PNG,
    }
    d.update(degis)
    return {k: v for k, v in d.items() if v is not None}


def yerel_webapp(**degis) -> dict[str, bytes]:
    d = {"Component.js": CTRL_SRC, "controller/Main.controller.js": CTRL_SRC,
         "fragment/Popup.fragment.js": FRAG_SRC, "lib/vendor.js": b"var vendor = 1;\n",
         "lib/my-dbg-helper.js": b"var h = 1;\n", "view/Main.view.xml": VIEW,
         "i18n/i18n.properties": I18N_YEREL, "manifest.json": jb(MANIFEST_YEREL), "img/logo.png": PNG}
    d.update(degis)
    return {k: v for k, v in d.items() if v is not None}


def zip_yaz(dosyalar: dict[str, bytes], yol: Path) -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, b in dosyalar.items():
            z.writestr(rel, b)
    yol.write_bytes(buf.getvalue())
    return yol


def dizin_yaz(dosyalar: dict[str, bytes], kok: Path) -> Path:
    for rel, b in dosyalar.items():
        (kok / rel).parent.mkdir(parents=True, exist_ok=True)
        (kok / rel).write_bytes(b)
    return kok


def sinif_haritasi(satirlar) -> dict[str, str]:
    return {rel: s for rel, s, _, _ in satirlar}


# ───────────────────────────── A — geri kurma ─────────────────────────────
kaynak, atilan = F.geri_kur(canli_bsp())
atilan_ad = dict(atilan)
kontrol("A1 X-dbg.js → X.js · X-dbg.controller.js → X.controller.js",
        kaynak.get("Component.js") == CTRL_SRC and kaynak.get("controller/Main.controller.js") == CTRL_SRC,
        str(sorted(kaynak)))
kontrol("A2 builder son eki: X-dbg.fragment.js → X.fragment.js (debugFileRegex)",
        kaynak.get("fragment/Popup.fragment.js") == FRAG_SRC and "fragment/Popup-dbg.fragment.js" not in kaynak,
        str(sorted(kaynak)))
kontrol("A3 atılanlar: preload(+map) · her .map · -dbg karşılığı olan küçültülmüş",
        atilan_ad.get("Component-preload.js") == "preload" and atilan_ad.get("Component-preload.js.map") == "preload"
        and atilan_ad.get("controller/Main.controller.js.map") == "map"
        and atilan_ad.get("controller/Main.controller.js", "").startswith("küçültülmüş")
        and not any(r.endswith(".map") or "-dbg" in r.rpartition("/")[2] and r != "lib/my-dbg-helper.js"
                    for r in kaynak), str(atilan))
kontrol("A4 -dbg karşılığı OLMAYAN .js aynen kalır; adında '-dbg' geçen düz dosya yeniden adlandırılmaz",
        kaynak.get("lib/vendor.js") == b"var vendor = 1;\n" and kaynak.get("lib/my-dbg-helper.js") == b"var h = 1;\n"
        and "lib/my.js" not in kaynak, str(sorted(kaynak)))
kontrol("A5 metin dosyaları LF (CRLF yok)",
        all(b"\r" not in kaynak.get(r, b"\r") for r in ("view/Main.view.xml", "i18n/i18n.properties", "manifest.json",
                                               "controller/Main.controller.js")))
kontrol("A6 ikili dosya HAM (PNG başlığındaki \\r\\n korunur)", kaynak.get("img/logo.png") == PNG)
kontrol("A7 kaynak haritası sondası: düz JS build → sapma yok", F.harita_sondasi(canli_bsp()) == [],
        str(F.harita_sondasi(canli_bsp())))
ts = canli_bsp(**{"controller/Main.controller.js.map": harita("Main.controller.js", "Main.controller.ts")})
kontrol("A8 sondası: sources özgün .ts'i gösterir → sapma", len(F.harita_sondasi(ts)) == 1, str(F.harita_sondasi(ts)))
dbgmap = canli_bsp(**{"controller/Main-dbg.controller.js.map": harita("Main-dbg.controller.js", "Main.controller.ts")})
kontrol("A9 sondası: -dbg dosyasının kendi haritası var → sapma",
        any("KENDİ haritası" in s for s in F.harita_sondasi(dbgmap)), str(F.harita_sondasi(dbgmap)))

# ───────────────────────────── B — karşılaştırma ─────────────────────────────
s = sinif_haritasi(F.karsilastir(kaynak, yerel_webapp()))
kontrol("B1 temiz çift: .properties \\uXXXX + manifest iki build yolu → BUILD-DONUSUMU, gerisi AYNI",
        s.get("i18n/i18n.properties") == F.BUILD and s.get("manifest.json") == F.BUILD
        and all(v in (F.AYNI, F.BUILD) for v in s.values())
        and sum(v == F.AYNI for v in s.values()) == len(s) - 2, str(s))
kontrol("B2 CRLF canlı ↔ LF yerel view → AYNI", s.get("view/Main.view.xml") == F.AYNI)
rs = F.karsilastir(kaynak, yerel_webapp(**{"i18n/i18n.properties": I18N_YEREL.replace(b"Listesi", b"Tablosu")}))
fark = next(f for r, _, _, f in rs if r == "i18n/i18n.properties")
kontrol("B3 .properties gerçek değer farkı → GERCEK-FARK + çözülmüş diff",
        sinif_haritasi(rs)["i18n/i18n.properties"] == F.GERCEK and "+appTitle=Sipariş Listesi" in fark, str(fark))
yorum = I18N_YEREL.replace("# Başlık yorumu".encode(), "# Başka yorum".encode())
kontrol("B4 .properties YORUM farkı gizlenmez → GERCEK-FARK (anahtar/değer ayrıştırması yok)",
        sinif_haritasi(F.karsilastir(kaynak, yerel_webapp(**{"i18n/i18n.properties": yorum})))["i18n/i18n.properties"]
        == F.GERCEK)
par_c = F.geri_kur(canli_bsp(**{"i18n/i18n.properties": b"x=\\\\u00fc\n"}))[0]
kontrol("B5 ters bölü paritesi: canlı `\\\\u00fc` (metin) ≠ yerel `\\ü` → GERCEK-FARK",
        F.dosya_kiyasla("i18n/i18n.properties", par_c["i18n/i18n.properties"], "x=\\ü\n".encode())[0] == F.GERCEK)
m_diger = manifest_canli(MANIFEST_YEREL)
m_diger["sap.ui5"]["models"]["@i18n"] = {"settings": {"supportedLocales": [""]}}
y_diger = json.loads(json.dumps(MANIFEST_YEREL))
y_diger["sap.ui5"]["models"]["@i18n"] = {"settings": {}}
kontrol("B6 manifest: ÖLÇÜLMEMİŞ yol (@i18n supportedLocales) → GERCEK-FARK",
        F.dosya_kiyasla("manifest.json", jb(m_diger), jb(y_diger))[0] == F.GERCEK)
y_deger = json.loads(json.dumps(MANIFEST_YEREL))
y_deger["sap.ui5"]["models"]["i18n"]["settings"]["supportedLocales"] = ["en"]
kontrol("B7 manifest: build yolu YERELDE VAR ve değer farklı → GERCEK-FARK (silinmez)",
        F.dosya_kiyasla("manifest.json", jb(manifest_canli(MANIFEST_YEREL)), jb(y_deger))[0] == F.GERCEK)
kontrol("B7b FP çapası: build yolları YERELDE AYNI değerle var → GERCEK-FARK DEĞİL",
        F.dosya_kiyasla("manifest.json", jb(manifest_canli(MANIFEST_YEREL)),   # biçim farklı ⇒ bayt ≠
                        json.dumps(manifest_canli(MANIFEST_YEREL), indent=4).encode())[0] != F.GERCEK)
y_baslik = json.loads(json.dumps(MANIFEST_YEREL))
y_baslik["sap.app"]["title"] = "baska"
sb, detay, mc, my = F.dosya_kiyasla("manifest.json", jb(manifest_canli(MANIFEST_YEREL)), jb(y_baslik))
kontrol("B8 manifest gerçek fark + build yolları ayıklanmış diff (flexBundle diff'te YOK)",
        sb == F.GERCEK and "flexBundle" not in mc and "flexBundle" in detay, f"{sb} {detay}")
rv = F.karsilastir(kaynak, yerel_webapp(**{"view/Main.view.xml": VIEW.replace(b"<Page", b"<Page busy=\"true\"")}))
fv = next(f for r, _, _, f in rv if r == "view/Main.view.xml")
kontrol("B9 view gerçek fark → GERCEK-FARK + unified diff satırı",
        sinif_haritasi(rv)["view/Main.view.xml"] == F.GERCEK and any(x.startswith("-  <Page busy") for x in fv), str(fv))
rl = sinif_haritasi(F.karsilastir(kaynak, yerel_webapp(**{"lib/vendor.js": None, "test/x.js": b"t\n"})))
kontrol("B10 YALNIZ-CANLI / YALNIZ-YEREL", rl.get("lib/vendor.js") == F.YALNIZ_CANLI
        and rl.get("test/x.js") == F.YALNIZ_YEREL, str(rl))
kontrol("B11 ikili: satır sonu farkı normalize EDİLMEZ → GERCEK-FARK",
        F.dosya_kiyasla("img/logo.png", PNG, PNG.replace(b"\r\n", b"\n"))[0] == F.GERCEK)

# ───────────────────────────── C — main() AĞSIZ ─────────────────────────────
TEMIZ_ZIP = zip_yaz(canli_bsp(), KUM / "canli.zip")
yerel = dizin_yaz(yerel_webapp(), KUM / "yerel" / "webapp")
rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--karsilastir", str(yerel)])
kontrol("C1 sıfır gerçek fark → rc 0 + ÖZET + KAPSAM BEYANI (bakılmayan dahil)",
        rc == 0 and "GERCEK-FARK=0" in out and "KAPSAM BEYANI" in out and "BAKILMAYAN" in out, f"rc={rc}\n{out[-600:]}")
fark_dizin = dizin_yaz(yerel_webapp(**{"view/Main.view.xml": VIEW.replace(b"Page", b"Panel")}), KUM / "yerel2" / "webapp")
rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--karsilastir", str(fark_dizin)])
kontrol("C2 gerçek fark → rc 1 + diff basılı", rc == 1 and "GERCEK-FARK     view/Main.view.xml" in out
        and "+++ canli/view/Main.view.xml" in out, f"rc={rc}")
dolu = KUM / "dolu"
dolu.mkdir()
(dolu / "korunan.txt").write_bytes(b"dokunma")
rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--out", str(dolu)])
kontrol("C3 dolu --out → rc 2, hiçbir şey yazılmaz",
        rc == 2 and sorted(p.name for p in dolu.iterdir()) == ["korunan.txt"], f"rc={rc} {sorted(dolu.iterdir())}")
hedef = KUM / "cikti" / "webapp"
rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--out", str(hedef)])
yazilan = F.dizin_oku(hedef) if hedef.is_dir() else {}
kontrol("C4 --out: geri kurulan küme yazılır, metin baytlarında CR YOK, PNG ham",
        rc == 0 and set(yazilan) == set(kaynak) and all(b"\r" not in yazilan[r] for r in yazilan if F.metin_mi(r))
        and yazilan.get("img/logo.png") == PNG, f"rc={rc} {sorted(yazilan)}")
bozuk = KUM / "bozuk.zip"
bozuk.write_bytes(b"PK-degil")
rc, out = cagir(["--zip", str(bozuk), "--karsilastir", str(yerel)])
kontrol("C5 bozuk zip → rc 2 + OLCULEMEDI (temiz sayılmaz)", rc == 2 and "[OLCULEMEDI]" in out, f"rc={rc} {out[:200]}")
rc, out = cagir(["--zip", str(KUM / "yok.zip")])
kontrol("C6 olmayan --zip → rc 2 + OLCULEMEDI (çökme değil)", rc == 2 and "[OLCULEMEDI]" in out, f"rc={rc} {out[:200]}")
kacak = zip_yaz({"../kacak.txt": b"x", "manifest.json": b"{}"}, KUM / "kacak.zip")
rc, out = cagir(["--zip", str(kacak), "--out", str(KUM / "kacak_hedef")])
kontrol("C7 zip içi `../` yolu hedef dışına yazılmaz", not (KUM / "kacak.txt").exists() and rc != 0,
        f"rc={rc} {out[:200]}")

# ───────────────── D — --eslik: gerçek alt süreç + SAHTE ui5 CLI (3. bağlam) ─────────────────
SAHTE_PY = KUM / "sahte_ui5.py"
SAHTE_PY.write_text(
    "import json, os, shutil, sys\n"
    "from pathlib import Path\n"
    "a = sys.argv[1:]\n"
    "kayit = {'argv': a, 'ui5yaml': Path('ui5.yaml').read_text(encoding='utf-8'),\n"
    "         'webapp': {p.relative_to('webapp').as_posix(): p.read_bytes().hex()\n"
    "                    for p in Path('webapp').rglob('*') if p.is_file()}}\n"
    "Path(os.environ['SAHTE_KAYIT']).write_text(json.dumps(kayit), encoding='utf-8')\n"
    "if a[:1] != ['build'] or 'ns.app' not in kayit['ui5yaml']:\n"
    "    print('sahte ui5: beklenmeyen cagri'); sys.exit(7)\n"
    "d = Path(a[a.index('--dest') + 1])\n"
    "shutil.rmtree(d, ignore_errors=True)\n"
    "shutil.copytree(os.environ['SAHTE_DIST'], d)\n", encoding="utf-8")
if os.name == "nt":
    SAHTE_CLI = KUM / "sahte_ui5.cmd"
    SAHTE_CLI.write_text(f'@"{sys.executable}" "{SAHTE_PY}" %*\r\n', encoding="utf-8")
else:
    SAHTE_CLI = KUM / "sahte_ui5"
    SAHTE_CLI.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{SAHTE_PY}" "$@"\n', encoding="utf-8")
    SAHTE_CLI.chmod(SAHTE_CLI.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
KAYIT = KUM / "sahte_kayit.json"
os.environ["SAHTE_KAYIT"] = str(KAYIT)


def eslik(canli: dict[str, bytes], dist: dict[str, bytes], ad: str, *ek: str) -> tuple:
    z = zip_yaz(canli, KUM / f"{ad}.zip")
    dd = dizin_yaz(dist, KUM / f"{ad}_dist")
    os.environ["SAHTE_DIST"] = str(dd)
    if KAYIT.exists():
        KAYIT.unlink()
    return cagir(["--zip", str(z), "--eslik", "--ui5-cli", str(SAHTE_CLI), *ek])


def lf(d: dict[str, bytes]) -> dict[str, bytes]:
    return {k: (v.replace(b"\r\n", b"\n") if F.metin_mi(k) else v) for k, v in d.items()}


rc, out = eslik(canli_bsp(), lf(canli_bsp()), "d1", "--out", str(KUM / "d1_out"))
kayit = json.loads(KAYIT.read_text(encoding="utf-8")) if KAYIT.exists() else {}
kontrol("D1 build canlıyı üretir → ESLIK-TAM rc 0 + --out yazılır",
        rc == 0 and "[ESLIK-TAM]" in out and (KUM / "d1_out" / "manifest.json").is_file(), f"rc={rc}\n{out[-500:]}")
verilen = {k: bytes.fromhex(v) for k, v in kayit.get("webapp", {}).items()}
kontrol("D2 build'e verilen webapp = geri kurulan kaynak (değiştirilmeden, LF) + ui5.yaml sap.app.id + argv",
        verilen == kaynak and kayit.get("argv", [])[:1] == ["build"] and "--dest" in kayit.get("argv", []),
        str(sorted(verilen)) + " " + str(kayit.get("argv")))
canli_esc = canli_bsp(**{"Component-preload.js":
                         crlf(b'sap.ui.require.preload({\n"ns/app/view/Main.view.xml":\'<x\\r\\n/>\'\n});\n')})
dist_esc = lf(canli_bsp(**{"Component-preload.js":
                           b'sap.ui.require.preload({\n"ns/app/view/Main.view.xml":\'<x\\n/>\'\n});\n'}))
rc, out = eslik(canli_esc, dist_esc, "d3")
kontrol("D3 fark YALNIZ kaçışlı \\r\\n → ESLIK-SATIR-SONU (ayrı kova) rc 0",
        rc == 0 and "[ESLIK-SATIR-SONU]" in out and "[ESLIK-TAM]" not in out, f"rc={rc}\n{out[-500:]}")
dist_kod = lf(canli_bsp(**{"Component-preload.js":
                           b'window.x=1;sap.ui.require.preload({\n"ns/app/view/Main.view.xml":\'<x/>\'\n});\n'}))
rc, out = eslik(canli_bsp(), dist_kod, "d4", "--out", str(KUM / "d4_out"))
kontrol("D4 preload JS kodu farklı → ESLIK-YOK rc 1, DUR (--out YAZILMAZ)",
        rc == 1 and "[ESLIK-YOK]" in out and not (KUM / "d4_out").exists(), f"rc={rc}\n{out[-500:]}")
dist_map = lf(canli_bsp(**{"controller/Main.controller.js.map": b'{"version":3,"sources":["Main-dbg.controller.js"],'
                                                                 b'"mappings":"AACA"}'}))
rc, out = eslik(canli_bsp(), dist_map, "d5")
kontrol("D5 preload EŞİT ama .map farklı (yorum-yalnız -dbg farkı izi) → ESLIK-YOK rc 1",
        rc == 1 and "[ESLIK-TAM]" in out and "preload dışında 1 dosya" in out, f"rc={rc}\n{out[-500:]}")
rc, out = eslik(ts, lf(ts), "d6")
kontrol("D6 her şey eşit ama kaynak haritası .ts'i gösteriyor → ESLIK-YOK rc 1",
        rc == 1 and "KAYNAK HARİTASI SAPMASI" in out and "kaynak haritası sapması var" in out, f"rc={rc}\n{out[-500:]}")
rc, out = eslik(canli_bsp(), {k: v for k, v in lf(canli_bsp()).items() if k != "lib/vendor.js"}, "d7")
kontrol("D7 build çıktısında canlı dosya eksik → ESLIK-YOK rc 1", rc == 1 and "yalnız-canlı 1" in out, f"rc={rc}")
rc, out = eslik(canli_bsp(**{"Component-preload.js": None}), lf(canli_bsp()), "d8")
kontrol("D8 zip'te preload yok → ÖLÇÜLEMEDİ rc 2", rc == 2 and "[OLCULEMEDI]" in out, f"rc={rc} {out[:200]}")
z = zip_yaz(canli_bsp(), KUM / "d9.zip")
rc, out = cagir(["--zip", str(z), "--eslik", "--ui5-cli", str(KUM / "yok" / "ui5")])
kontrol("D9 ui5 CLI koşamıyor → ÖLÇÜLEMEDİ rc 2 (ESLIK hükmü basılmaz)",
        rc == 2 and "[OLCULEMEDI]" in out and "[ESLIK-" not in out, f"rc={rc} {out[:300]}")

# ───────────────────────────── özet ─────────────────────────────
gecen = sum(ok for _, ok, _ in SONUC)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok and detay:
        print("         " + detay.replace("\n", "\n         ")[:1500])
print(f"\nfetch_ui_source: {gecen}/{len(SONUC)} PASS" + (f" (MUTASYON {KIP})" if KIP else ""))
shutil.rmtree(KUM, ignore_errors=True)
sys.exit(0 if gecen == len(SONUC) else 1)

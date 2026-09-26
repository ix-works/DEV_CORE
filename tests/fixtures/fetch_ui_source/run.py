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
        FUS, "    if out is not None and out.is_dir() and any(out.iterdir()):\n", "    if False:\n"),
    # C — dolu-dizin ön kontrolü `exists()`a döner: --out bir DOSYA ise iterdir() çöker (bug-gate bulgu 1)
    "--mutasyon-out-dosya-onkontrol": (
        FUS, "    if out is not None and out.is_dir() and any(out.iterdir()):\n",
        "    if out is not None and out.exists() and any(out.iterdir()):\n"),
    # C — sıfır-fark anında kapsam beyanı basılmaz
    "--mutasyon-kapsam-yok": (
        FUS, '    print("\\n" + beyan(zip_kaynagi))\n    return rc\n', "    return rc\n"),
    # C — zip-slip denetimi kaldırılır (bug-gate bulgu 1)
    "--mutasyon-zip-slip-yok": (FUS, "        if kok not in (hedef / rel).resolve().parents:", "        if False:"),
    # C — atomik yazım kaldırılır: doğrudan hedefe yazılır (yazım ORTASI G/Ç hatası KISMİ ağaç bırakır; re-gate R2)
    "--mutasyon-atomik-yok": (FUS, "            p = gecici / rel\n", "            p = hedef / rel\n"),
    # C — ham zip'te harf-büyüklüğü çakışması denetimi kaldırılır (re-gate P-2)
    "--mutasyon-harf-ham-yok": (
        FUS, "    cakisma = harf_cakismasi(dosyalar)\n", "    cakisma = []\n"),
    # C — geri kurma SONRASI (X-dbg.js → X.js) harf çakışması denetimi kaldırılır (re-gate P-2, ikinci katman)
    "--mutasyon-harf-yaz-yok": (FUS, "    cakisma = harf_cakismasi(kaynak)\n", "    cakisma = []\n"),
    # C — --karsilastir yerel dizin okuma hatası ÖLÇÜLEMEDİ'ye çevrilmez (re-gate P-1)
    "--mutasyon-kars-oku-yok": (
        FUS, "        try:\n            yerel_dosyalar = dizin_oku(yerel_kok)\n        except OSError as e:   # re-gate P-1\n",
        "        if True:\n            yerel_dosyalar = dizin_oku(yerel_kok)\n        if False:\n"),
    # E — --dist-karsilastir dizin okuma hatası ÖLÇÜLEMEDİ'ye çevrilmez (re-gate P-1)
    "--mutasyon-dist-oku-yok": (
        FUS, "        try:\n            dist_dosyalar = dizin_oku(dist_kok)\n        except OSError as e:   # re-gate P-1\n",
        "        if True:\n            dist_dosyalar = dizin_oku(dist_kok)\n        if False:\n"),
    # D — eşlik build dizini G/Ç hatası (dist okuma, package.json yazımı) yakalanmaz (re-gate P-1)
    "--mutasyon-eslik-gc-yok": (
        FUS, "    except OSError as e:   # re-gate P-1: package.json", "    except KeyError as e:   # re-gate P-1: package.json"),
    # D — eşlik geçici dizini (mkdtemp) açılamazsa yakalanmaz (re-gate P-1)
    "--mutasyon-eslik-mkdtemp-yok": (
        FUS, "    except OSError as e:   # re-gate P-1: geçici build", "    except KeyError as e:   # re-gate P-1: geçici build"),
    # C — dış except programlama hatasını (AttributeError) ortam sorunu gibi yutar (re-gate R3)
    "--mutasyon-dis-except-genis": (
        FUS, "    except (OSError, ValueError) as e:\n", "    except (OSError, ValueError, AttributeError) as e:\n"),
    # C — --out yazımı ÖLÇÜLEMEDİ'ye çevrilmez (Olculemedi çökme olur; bulgu 1)
    "--mutasyon-out-try-yok": (
        FUS, "        try:\n            yaz(kaynak, out)\n        except Olculemedi as e:\n"
             '            return olculemedi(zip_kaynagi, f"--out: {e}")\n',
        "        yaz(kaynak, out)\n"),
    # C — indirme/çözme bloğu yalnız Olculemedi yakalar (OSError/AttributeError… çöker; bulgu 1)
    "--mutasyon-indirme-hata-dar": (FUS, "    except (OSError, ValueError) as e:\n", "    except ValueError as e:\n"),
    # C — zip_coz yalnız BadZipFile yakalar (bozuk deflate = zlib.error kendi mesajını kaybeder; bulgu 1)
    "--mutasyon-zipcoz-dar": (
        FUS, "    except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError) as e:\n",
        "    except zipfile.BadZipFile as e:\n"),
    # C — yanıt `d` nesnesi denetimi kaldırılır (liste gövdesi AttributeError; bulgu 1)
    "--mutasyon-yanit-bicim-yok": (
        FUS, '    d = j.get("d") if isinstance(j, dict) else None\n', '    d = j.get("d", {})\n'),
    # C — ZipArchive base64 hatası yerelde yakalanmaz (bulgu 1)
    "--mutasyon-b64-yerel-yok": (
        FUS, "    except (binascii.Error, ValueError, TypeError) as e:\n", "    except KeyError as e:\n"),
    # C — .conn_adt sarmalayıcısı atlanır: read_conn'un sys.exit(1)'i rc 1 olur (bulgu 2)
    "--mutasyon-conn-sarmalayici-yok": (FUS, "zip_indir(bsp, baglanti())", "zip_indir(bsp, read_conn())"),
    # C — boş ADT_SAP_URL/USER denetimi kaldırılır (bulgu 2)
    "--mutasyon-bos-url-kontrol-yok": (FUS, "    if not conn[0] or not conn[1]:\n", "    if False:\n"),
    # B — manifest tip-duyarsız kıyas: true == 1 (bulgu 3)
    "--mutasyon-manifest-tip": (
        FUS, "    if json.dumps(_json_norm(c), sort_keys=True) == json.dumps(_json_norm(y), sort_keys=True):\n",
        "    if c == y:\n"),
    # B — sayı normalizasyonu kaldırılır: canlı `1` ↔ yerel `1.0` sahte GERCEK-FARK (re-gate R1, bu turun regresyonu)
    "--mutasyon-sayi-norm-yok": (
        FUS, "    if isinstance(o, float) and o.is_integer():\n        return int(o)\n", ""),
    # B — .properties katı çözme kaldırılır: farklı bozuk baytlar AYNI U+FFFD'ye iner (bulgu 4)
    "--mutasyon-prop-kati-yok": (FUS, '    hata = "strict" if kati else "replace"\n', '    hata = "replace"\n'),
    # C — istenip koşmayan adım "İSTENMEDİ" yazılır (bulgu 5)
    "--mutasyon-kapsam-istendi-yok": (
        FUS, '    return f"İSTENDİ — KOŞMADI ({sebep})" if istendi else "İSTENMEDİ"\n', '    return "İSTENMEDİ"\n'),
    # E — canlıda olup dist'te olmayan dosya rc'yi etkilemez (deploy listesi kör)
    "--mutasyon-deploy-listesi-kor": (FUS, "        if yalniz_c:\n            print(\"  ⛔ canlıda",
                                      "        if False:\n            print(\"  ⛔ canlıda"),
    # D — preload dışı tam-liste hükmü kaldırılır (yalnız preload kıyası)
    "--mutasyon-tam-liste-yok": (FUS, "        if liste_farki and sinif != ESLIK_YOK:\n", "        if False:\n"),
    # D — eşlik YOK iken DURMAZ (--out yazılır)
    "--mutasyon-eslik-dur-yok": (
        FUS, '        if sinif == ESLIK_YOK:\n            print("     DUR:', '        if False:\n            print("     DUR:'),
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
COKMELER: list[str] = []   # main() çökmesi ASLA geçer sayılmaz → Z0 vektörü (bug-gate 2026-09-26, bulgu 1)


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def cagir(argv: list[str]) -> tuple:
    t, h = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(t), redirect_stderr(h):
            rc = F.main(argv)
    except SystemExit as e:
        rc = e.code
        if rc != 2:   # argparse kullanım hatası (2) dışındaki her SystemExit bir çökmedir (re-gate R4)
            COKMELER.append(f"{argv[:2]}… → SystemExit({rc!r})")
    except Exception as e:  # çökme: rc sayı DEĞİL (hiçbir rc kıyası tutmaz) + Z0'da FAIL
        COKMELER.append(f"{argv[:2]}… → {type(e).__name__}: {e}")
        rc = f"CÖKME {type(e).__name__}"
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
m_bool, m_int = json.loads(json.dumps(MANIFEST_YEREL)), json.loads(json.dumps(MANIFEST_YEREL))
m_bool["sap.ui5"]["bayrak"], m_int["sap.ui5"]["bayrak"] = True, 1
kontrol("B12 manifest tip farkı: canlı `1` ↔ yerel `true` → GERCEK-FARK (Python true==1 tuzağı)",
        F.dosya_kiyasla("manifest.json", jb(m_int), jb(m_bool))[0] == F.GERCEK)
m_bir = jb(m_int).replace(b'"bayrak": 1', b'"bayrak": 1.0').replace(b'"1.59.0"', b'"1.59.0", "sayi": 1e3')
m_bin = jb(m_int).replace(b'"1.59.0"', b'"1.59.0", "sayi": 1000')
kontrol("B12b FP çapası: sayı biçimi (canlı `1` ↔ yerel `1.0` · `1000` ↔ `1e3`) → BUILD-DONUSUMU (JS anlambilimi)",
        b'"bayrak": 1.0' in m_bir and F.dosya_kiyasla("manifest.json", m_bin, m_bir)[0] == F.BUILD,
        str(F.dosya_kiyasla("manifest.json", m_bin, m_bir)[:2]))
kontrol("B13 .properties iki FARKLI bozuk bayt (yerel \\xfe · canlı \\xff) → GERCEK-FARK (U+FFFD'de birleşmez)",
        F.dosya_kiyasla("i18n/i18n.properties", b"x=\xff\n", b"x=\xfe\n")[0] == F.GERCEK)
p14 = F.dosya_kiyasla("i18n/i18n.properties", b"x=\xff\n", "x=\ufffd\n".encode("utf-8"))
kontrol("B14 canlı geçersiz UTF-8 ↔ yerel harfiyen U+FFFD → GERCEK-FARK (canlıdaki kayıp BUILD sayılmaz)",
        p14[0] == F.GERCEK and "canlı geçersiz" in p14[1], str(p14[:2]))
kontrol("B15 FP çapası: canlı meşru `\\ufffd` KAÇIŞI ↔ yerel U+FFFD → BUILD-DONUSUMU",
        F.dosya_kiyasla("i18n/i18n.properties", b"x=\\ufffd\n", "x=\ufffd\n".encode("utf-8"))[0] == F.BUILD)

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
kontrol("C3 dolu --out → rc 2 (ön kontrol mesajıyla), hiçbir şey yazılmaz",
        rc == 2 and "--out dizini dolu" in out and sorted(p.name for p in dolu.iterdir()) == ["korunan.txt"],
        f"rc={rc} {sorted(dolu.iterdir())}")
hedef = KUM / "cikti" / "webapp"
rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--out", str(hedef)])
yazilan = F.dizin_oku(hedef) if hedef.is_dir() else {}
kontrol("C4 --out: geri kurulan küme yazılır, metin baytlarında CR YOK, PNG ham, geçici dizin ARTIĞI YOK",
        rc == 0 and set(yazilan) == set(kaynak) and all(b"\r" not in yazilan[r] for r in yazilan if F.metin_mi(r))
        and yazilan.get("img/logo.png") == PNG and sorted(p.name for p in hedef.parent.iterdir()) == ["webapp"],
        f"rc={rc} {sorted(yazilan)} {sorted(p.name for p in hedef.parent.iterdir()) if hedef.parent.exists() else '-'}")
bos_hedef = KUM / "bos_hedef"
bos_hedef.mkdir()
rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--out", str(bos_hedef)])
kontrol("C4b var olan BOŞ --out dizini (atomik taşıma önce onu kaldırır) → rc 0, küme yazılır",
        rc == 0 and bos_hedef.is_dir() and set(F.dizin_oku(bos_hedef)) == set(kaynak), f"rc={rc} {out[-300:]}")
bozuk = KUM / "bozuk.zip"
bozuk.write_bytes(b"PK-degil")
rc, out = cagir(["--zip", str(bozuk), "--karsilastir", str(yerel)])
kontrol("C5 bozuk zip → rc 2 + OLCULEMEDI (temiz sayılmaz) + istenen --karsilastir 'İSTENDİ — KOŞMADI'",
        rc == 2 and "[OLCULEMEDI]" in out and "karşılaştırma: İSTENDİ — KOŞMADI (ÖLÇÜLEMEDİ" in out,
        f"rc={rc} {out[-700:]}")
rc, out = cagir(["--zip", str(KUM / "yok.zip")])
kontrol("C6 olmayan --zip → rc 2 + OLCULEMEDI (çökme değil)", rc == 2 and "[OLCULEMEDI]" in out, f"rc={rc} {out[:200]}")
# Sıra bilinçli: a.txt ve manifest.json kaçak girdiden ÖNCE gelir ⇒ "önce yaz sonra doğrula" kısmi yazım bırakırdı.
kacak = zip_yaz({"a.txt": b"x\n", "manifest.json": b"{}", "zz/../../kacak.txt": b"x"}, KUM / "kacak.zip")
kacak_hedef = KUM / "kacak_hedef"
rc, out = cagir(["--zip", str(kacak), "--out", str(kacak_hedef)])
kontrol("C7 zip-slip: `zz/../../` → rc 2 + OLCULEMEDI + kapsam beyanı; hedef dışına VE hedefe HİÇBİR dosya yazılmaz",
        rc == 2 and "[OLCULEMEDI]" in out and "KAPSAM BEYANI" in out and not (KUM / "kacak.txt").exists()
        and not (kacak_hedef.exists() and any(kacak_hedef.rglob("*"))),
        f"rc={rc} {sorted(kacak_hedef.rglob('*')) if kacak_hedef.exists() else '-'} {out[:300]}")
out_dosya = KUM / "out_bir_dosya.txt"
out_dosya.write_bytes(b"dokunma")
rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--out", str(out_dosya)])
kontrol("C8 --out bir DOSYA → rc 2 + OLCULEMEDI (çökme değil), dosya değişmez",
        rc == 2 and "[OLCULEMEDI]" in out and out_dosya.read_bytes() == b"dokunma", f"rc={rc} {out[:300]}")


def deflate_boz(dosyalar: dict[str, bytes], yol: Path) -> Path:
    """Sıkıştırılmış veriyi 0xFF ile ez ⇒ BTYPE=11 (ayrılmış) ⇒ z.read() zlib.error (CRC'ye varmadan)."""
    zip_yaz(dosyalar, yol)
    ham = bytearray(yol.read_bytes())
    with zipfile.ZipFile(yol) as z:
        for zi in z.infolist():
            bas = zi.header_offset + 30 + len(zi.filename.encode()) + len(zi.extra)
            ham[bas:bas + zi.compress_size] = b"\xff" * zi.compress_size
    yol.write_bytes(bytes(ham))
    return yol


rc, out = cagir(["--zip", str(deflate_boz({"manifest.json": b"{}" * 50}, KUM / "zlib.zip"))])
kontrol("C9 bozuk deflate (zlib.error) → rc 2 + 'zip çözülemedi' (çökme değil)",
        rc == 2 and "zip çözülemedi" in out and "error" in out, f"rc={rc} {out[:300]}")

# ── ağ katmanı SAHTE (urlopen + read_conn yamalı): SAP'ye/ağa dokunulmaz ──
CONN = ("https://sahte.invalid", "<SAP_USER>", "x", "100")
ISTEKLER: list[str] = []


class _Yanit:
    def __init__(self, govde: bytes):
        self.govde = govde

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self) -> bytes:
        return self.govde


def sahte_ag(govde: bytes, *ek: str) -> tuple:
    asil_url, asil_conn = F.urllib.request.urlopen, F.read_conn

    def _ac(req, context=None, timeout=None):
        ISTEKLER.append(req.get_method())
        return _Yanit(govde)
    F.urllib.request.urlopen, F.read_conn = _ac, (lambda: CONN)
    try:
        return cagir(["--bsp", "ZSD001_APP", *ek])
    finally:
        F.urllib.request.urlopen, F.read_conn = asil_url, asil_conn


rc, out = sahte_ag(b"[1, 2]")
kontrol("C10 yanıt JSON ama nesne değil (liste) → rc 2 + '`d` nesnesi yok' (AttributeError çökmesi değil)",
        rc == 2 and "`d` nesnesi yok" in out, f"rc={rc} {out[:300]}")
rc, out = sahte_ag(b'{"d": {"ZipArchive": "abc", "Name": "ZSD001_APP"}}')
kontrol("C11 ZipArchive bozuk base64 → rc 2 + 'base64 çözülemedi'", rc == 2 and "base64 çözülemedi" in out,
        f"rc={rc} {out[:300]}")
import base64 as _b64  # noqa: E402
iyi_govde = json.dumps({"d": {"ZipArchive": _b64.b64encode(TEMIZ_ZIP.read_bytes()).decode(), "Name": "ZSD001_APP",
                              "Package": "ZSD001", "Description": "x"}}).encode()
engel = KUM / "engel_dosya"
engel.write_bytes(b"x")
rc, out = sahte_ag(iyi_govde, "--zip-kaydet", str(engel / "alt" / "canli.zip"))
kontrol("C12 --zip-kaydet yazılamıyor (üst yol bir dosya; OSError) → rc 2 + OLCULEMEDI (çökme değil)",
        rc == 2 and "[OLCULEMEDI]" in out and "indirme/çözme" in out, f"rc={rc} {out[:300]}")
rc, out = sahte_ag(iyi_govde, "--karsilastir", str(yerel))
kontrol("C13 kontrol grubu: sahte ağ + geçerli yanıt → rc 0, GERCEK-FARK=0; ağa giden HER istek GET",
        rc == 0 and "GERCEK-FARK=0" in out and ISTEKLER and set(ISTEKLER) == {"GET"}, f"rc={rc} {ISTEKLER} {out[-300:]}")

# ── .conn_adt: gerçek giriş noktası (alt süreç) + boş alanlar (bulgu 2) ──
bos_proje = KUM / "bos_proje"
bos_proje.mkdir()
p = subprocess.run([sys.executable, str(SCRIPTS / "fetch_ui_source.py"), "--bsp", "ZSD001_APP"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(bos_proje),
                   env={**os.environ, "CLAUDE_PROJECT_DIR": str(bos_proje), "PYTHONIOENCODING": "utf-8"}, timeout=120)
kontrol("C14 CLAUDE_PROJECT_DIR=.conn_adt'siz dizin (alt süreç) → rc 2 + OLCULEMEDI + kapsam beyanı (rc 1 değil)",
        p.returncode == 2 and "[OLCULEMEDI]" in p.stderr and ".conn_adt okunamadı" in p.stderr
        and "KAPSAM BEYANI" in p.stdout, f"rc={p.returncode} {p.stderr[-300:]}")
(KUM / ".conn_adt").write_text("ADT_SAP_URL=\nADT_SAP_USER=\n", encoding="utf-8")
try:
    rc, out = cagir(["--bsp", "ZSD001_APP"])
finally:
    (KUM / ".conn_adt").unlink()
kontrol("C15 .conn_adt'de URL/kullanıcı BOŞ → rc 2 + '.conn_adt … boş' (ağa çıkmadan)",
        rc == 2 and "ADT_SAP_URL / ADT_SAP_USER boş" in out, f"rc={rc} {out[:300]}")

# ── re-gate R2: yazım ORTASINDA G/Ç hatası (dosya `b` ↔ dizin `b/`) → hedef KISMİ kalmaz ──
catisma = zip_yaz({"a.txt": b"x\n", "b": b"dosya\n", "b/c.txt": b"y\n"}, KUM / "catisma.zip")
catisma_hedef = KUM / "catisma_ust" / "webapp"
rc, out = cagir(["--zip", str(catisma), "--out", str(catisma_hedef)])
ust_icerik = sorted(p.name for p in catisma_hedef.parent.iterdir()) if catisma_hedef.parent.exists() else []
kontrol("C16 yazım ortasında G/Ç hatası (`b` dosyası + `b/c.txt`) → rc 2 + 'DOKUNULMADI'; hedef YOK, geçici artık YOK",
        rc == 2 and "[OLCULEMEDI]" in out and "DOKUNULMADI" in out and not catisma_hedef.exists() and ust_icerik == [],
        f"rc={rc} üst={ust_icerik} {out[:300]}")

# ── re-gate P-2: yalnız harf büyüklüğüyle ayrışan yollar ──
rc, out = cagir(["--zip", str(zip_yaz(canli_bsp(**{"view/main.view.xml": crlf(VIEW)}), KUM / "harf.zip")),
                 "--karsilastir", str(yerel)])
kontrol("C17 zip'te `view/Main.view.xml` + `view/main.view.xml` → rc 2 + OLCULEMEDI (sessiz üzerine yazma yok)",
        rc == 2 and "harf büyüklüğüyle" in out and "KAPSAM BEYANI" in out, f"rc={rc} {out[:300]}")
harf_hedef = KUM / "harf_hedef"
rc, out = cagir(["--zip", str(zip_yaz({"A-dbg.js": b"var a;\n", "a.js": b"var b;\n"},
                                      KUM / "harf2.zip")), "--out", str(harf_hedef)])
kontrol("C18 geri kurma SONRASI çakışma (`A-dbg.js`→`A.js` ↔ `a.js`; ham zip'te çift YOK) → rc 2, hiçbir şey yazılmaz",
        rc == 2 and "geri kurulan kaynakta" in out and not harf_hedef.exists(), f"rc={rc} {out[:300]}")

# ── re-gate P-1: yerel/dist/eşlik G/Ç hatası → ÖLÇÜLEMEDİ rc 2 + beyan (Traceback + rc 1 değil) ──


def izin_yok(_kok):
    raise PermissionError(13, "erişim reddedildi (sahte)", str(_kok))


asil_dizin_oku = F.dizin_oku
F.dizin_oku = izin_yok
try:
    rc, out = cagir(["--zip", str(TEMIZ_ZIP), "--karsilastir", str(yerel)])
    rc2, out2 = cagir(["--zip", str(TEMIZ_ZIP), "--dist-karsilastir", str(yerel)])
finally:
    F.dizin_oku = asil_dizin_oku
kontrol("C19 --karsilastir dizini okunamıyor (PermissionError) → rc 2 + OLCULEMEDI + kapsam beyanı",
        rc == 2 and "--karsilastir dizini okunamadı" in out and "KAPSAM BEYANI" in out, f"rc={rc} {out[:300]}")
kontrol("C20 --dist-karsilastir dizini okunamıyor → rc 2 + OLCULEMEDI + kapsam beyanı",
        rc2 == 2 and "--dist-karsilastir dizini okunamadı" in out2 and "KAPSAM BEYANI" in out2, f"rc={rc2} {out2[:300]}")

# ── re-gate R3: programlama hatası ortam sorunu gibi YUTULMAZ (çağrı doğrudan; COKMELER'e yazılmaz) ──
asil_zip_coz = F.zip_coz


def _bozuk_coz(_b):
    raise AttributeError("sahte programlama hatası")


F.zip_coz = _bozuk_coz
try:
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        F.main(["--zip", str(TEMIZ_ZIP)])
    yutuldu = "yutuldu (main döndü)"
except AttributeError:
    yutuldu = ""
except BaseException as e:  # noqa: BLE001
    yutuldu = f"beklenmeyen {type(e).__name__}"
finally:
    F.zip_coz = asil_zip_coz
kontrol("C21 indirme bloğunda AttributeError → YAYILIR (ÖLÇÜLEMEDİ'ye çevrilmez; programlama hatası görünür kalır)",
        yutuldu == "", yutuldu)

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
rc, out = eslik(canli_bsp(), dist_kod, "d4", "--out", str(KUM / "d4_out"), "--karsilastir", str(yerel),
                "--dist-karsilastir", str(yerel))
kontrol("D4 preload JS kodu farklı → ESLIK-YOK rc 1, DUR (--out YAZILMAZ; DUR satırı --dist-karsilastir'ı da anar; "
        "istenen üç adım kapsamda 'İSTENDİ — KOŞMADI')",
        rc == 1 and "[ESLIK-YOK]" in out and not (KUM / "d4_out").exists()
        and "ve --dist-karsilastir KOŞMADI" in out
        and all(f"{e}: İSTENDİ — KOŞMADI (ESLIK-YOK → DUR)" in out for e in ("--out    ", "deploy listesi",
                                                                            "karşılaştırma"))
        and "=== KARŞILAŞTIR" not in out and "=== DEPLOY LİSTESİ" not in out, f"rc={rc}\n{out[-900:]}")
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

# re-gate P-1: eşlik build dizini G/Ç (dist okuma) ve geçici dizin açılamaması → ÖLÇÜLEMEDİ rc 2
F.dizin_oku = izin_yok
try:
    rc, out = eslik(canli_bsp(), lf(canli_bsp()), "d10")
finally:
    F.dizin_oku = asil_dizin_oku
kontrol("D10 eşlik: build dist'i okunamıyor (PermissionError) → rc 2 + 'build dizini G/Ç' + kapsam beyanı",
        rc == 2 and "build dizini G/Ç" in out and "KAPSAM BEYANI" in out, f"rc={rc} {out[:300]}")
asil_mkdtemp = F.tempfile.mkdtemp


def _mkdtemp(*a, **k):
    if k.get("prefix") == "fetch_ui_eslik_":
        raise OSError(28, "aygıtta yer yok (sahte)")
    return asil_mkdtemp(*a, **k)


F.tempfile.mkdtemp = _mkdtemp
try:
    rc, out = eslik(canli_bsp(), lf(canli_bsp()), "d11")
finally:
    F.tempfile.mkdtemp = asil_mkdtemp
kontrol("D11 eşlik: geçici build dizini açılamıyor → rc 2 + 'geçici build dizini açılamadı'",
        rc == 2 and "geçici build dizini açılamadı" in out, f"rc={rc} {out[:300]}")

# ─────────────── E — deploy listesi (--dist-karsilastir, §2.4 localService riski) ───────────────
LS = {"localService/mainService/metadata.xml": crlf(b"<edmx/>\n")}
canli_ls = canli_bsp(**LS)
z = zip_yaz(canli_ls, KUM / "e.zip")
dist_tam = dizin_yaz(lf(canli_ls), KUM / "e1_dist")
rc, out = cagir(["--zip", str(z), "--dist-karsilastir", str(dist_tam)])
kontrol("E1 dist == canlı (yalnız satır sonu farkı) → rc 0, YALNIZ-CANLI=0, değişecek=0",
        rc == 0 and "YALNIZ-CANLI=0" in out and "değişecek=0" in out and "deploy listesi: canlı ham" in out,
        f"rc={rc}\n{out[-400:]}")
dist_ex = dizin_yaz({k: v for k, v in lf(canli_ls).items() if not k.startswith("localService/")}, KUM / "e2_dist")
rc, out = cagir(["--zip", str(z), "--dist-karsilastir", str(dist_ex)])
kontrol("E2 dist'te localService YOK (excludes) → YALNIZ-CANLI listelenir, rc 1",
        rc == 1 and "YALNIZ-CANLI    localService/mainService/metadata.xml" in out, f"rc={rc}\n{out[-400:]}")
dist_yeni = lf(canli_ls)
dist_yeni["view/Yeni.view.xml"] = b"<x/>\n"
dist_yeni["view/Main.view.xml"] = VIEW.replace(b"Page", b"Panel")
rc, out = cagir(["--zip", str(z), "--dist-karsilastir", str(dizin_yaz(dist_yeni, KUM / "e3_dist"))])
kontrol("E3 yeni + değişen dosya → YALNIZ-DIST / DEGISECEK listelenir, rc 0 (engel değil)",
        rc == 0 and "YALNIZ-DIST     view/Yeni.view.xml" in out and "DEGISECEK       view/Main.view.xml" in out,
        f"rc={rc}\n{out[-400:]}")
rc, out = cagir(["--zip", str(z), "--dist-karsilastir", str(KUM / "yok_dist")])
kontrol("E4 dist dizini yok → rc 2 (kullanım; 'temiz' değil)", rc == 2, f"rc={rc}")

kontrol("Z0 hiçbir main() çağrısı ÇÖKMEDİ (çökme geçer sayılmaz)", not COKMELER, "; ".join(COKMELER))

# ───────────────────────────── özet ─────────────────────────────
gecen = sum(ok for _, ok, _ in SONUC)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok and detay:
        print("         " + detay.replace("\n", "\n         ")[:1500])
print(f"\nfetch_ui_source: {gecen}/{len(SONUC)} PASS" + (f" (MUTASYON {KIP})" if KIP else ""))
shutil.rmtree(KUM, ignore_errors=True)
sys.exit(0 if gecen == len(SONUC) else 1)

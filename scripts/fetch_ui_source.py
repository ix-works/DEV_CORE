# -*- coding: utf-8 -*-
"""fetch_ui_source.py — Deploy edilmiş freestyle UI5 BSP'sinin kaynağını SAP'den SALT-OKUR geri kurar.

⛔ NEDEN VAR (Issue #304, 2026-09-26):
   `deploy_ui.py` ve `standards/03-coding-ui-fiori.md` §2.4.1 kaynağın yerelde ZATEN var
   olduğunu varsayar (`<ui_root>/<app>/webapp` → build → deploy → canlı preload hash).
   Kaynağı repoda hiç olmayan ya da başka bir makinede revize edilip deploy edilmiş bir
   uygulama için çekirdekte tarif yoktu; ajan ya kaynağı kullanıcıdan istedi (iş durdu)
   ya da elle, her seferinde yeniden türetilen betiklerle indirdi.

NE YAPAR (yalnız GET — SAP'ye hiçbir şey yazmaz):
  1) İNDİR  `GET /sap/opu/odata/UI5/ABAP_REPOSITORY_SRV/Repositories('<BSP>')
             ?$format=json&CodePage='UTF8'&DownloadFiles='RUNTIME'` → `d.ZipArchive` (base64 zip).
     BSP'deki dosyalar BUILD ÇIKTISIDIR (dist). ICF yolu (`/sap/bc/ui5_ui5/sap/<bsp>/…`) kaynak
     indirmede KULLANILMAZ: dizin listelemez ve HTML `<head>`'ine çalışma zamanında meta enjekte
     eder (bkz. `verify_ui_static_assets.py` başlığı, INJECTED_META).
  2) GERİ KUR (`-dbg` kuralı) — özgün kaynak `*-dbg*.js`'te durur (her `X.js.map`'in `sources`u
     `X-dbg.js`'i gösterir; Issue #304 ölçümü 5/5):
       · `X-dbg.js` → `X.js` · `X-dbg.controller.js` → `X.controller.js` (ve aşağıdaki son ekler)
       · atılır: `Component-preload.js(.map)` · her `*.map` · `-dbg` karşılığı OLAN küçültülmüş `.js`
       · kalan her şey AYNEN kopyalanır; METİN dosyaları LF yazılır (SAP BSP dosyaları CRLF saklar,
         ölçüldü 4 BSP'de .css/.html/.js/.json/.properties/.xml hepsi CRLF). İkili (png…) HAM kalır —
         PNG başlığının kendisi `\\r\\n` baytı taşır, normalize etmek dosyayı bozar.
     Son ek kümesi UYDURULMADI: @ui5/builder `lib/processors/minifier.js`
     `debugFileRegex = /((?:\\.view|\\.fragment|\\.controller|\\.designtime|\\.support)?\\.js)$/`
     (ölçülen sürüm 4.x; `-dbg` bu grubun ÖNÜNE eklenir). Aynı küme burada tersine uygulanır.
  3) KİPLER
     `--out <dizin>`         geri kurulan webapp'i yazar (dizin YOK ya da BOŞ olmalı — yerel kaynağın
                             üzerine yazmaz; önce `--karsilastir`, sonra seçerek kopyala).
     `--karsilastir <webapp>` dosya listesi + içerik: `AYNI | BUILD-DONUSUMU | GERCEK-FARK |
                             YALNIZ-CANLI | YALNIZ-YEREL`; gerçek farkta unified diff.
     `--eslik`               geri kurulan kaynağı DEĞİŞTİRMEDEN `ui5 build` ile derler; ÜÇ şart:
                             ① çıkan `Component-preload.js` AYNI zip'teki preload ile
                             `deploy_ui.preload_karsilastir` üzerinden eşit (AYNI ya da SATIR_SONU)
                             ② preload DIŞINDAKİ her dosya (küçültülmüş .js, .map, varlıklar) eşit ve
                             liste birebir ③ kaynak haritası sondası temiz (`harita_sondasi`).
                             Biri tutmazsa DUR: `--out`/`--karsilastir` KOŞMAZ.
                             ⚠ ① tek başına YETMEZ (ölçüldü): -dbg'deki yalnız-yorum farkı küçültmede
                             kaybolur, preload EŞİT çıkar — iz yalnız `.map`'te kalır (②). Transpile
                             edilmiş -dbg (TS) de eşit küçültülmüş kod üretebilir — iz `sources`ta (③).
     `--dist-karsilastir <dist>` DEPLOY LİSTESİ: canlı ham dosya listesi ↔ deploy edilecek `dist/`
                             (ad + içerik). `YALNIZ-CANLI` = canlıda olup deploy kümesinde olmayan dosya
                             (ör. yanlış `excludes` ile düşen `localService/**`) → rc 1, kullanıcıya göster.
                             Deploy SONRASI yeniden indirilen zip'le koşulunca tam-liste doğrulamasıdır.
     `--zip-kaydet <dosya>`  indirilen ham zip'i saklar (sonraki drift kıyası için anlık görüntü).
     `--zip <dosya>`         AĞ YOK: daha önce kaydedilmiş zip'i girdi olarak kullanır.

BUILD DÖNÜŞÜMLERİ (`--karsilastir`; yalnız ÖLÇÜLENLER, başka hiçbir fark gevşetilmez):
  · `.properties` — `ui5 build` non-ASCII'yi `\\uXXXX`'e çevirir (Q285). İki taraf da çözülüp
    SATIR SATIR kıyaslanır (yorumlar dahil — anahtar/değer ayrıştırması YOK, yorum farkı da farktır).
  · `manifest.json` — build iki alan EKLER (3 BSP'de ölçüldü): `sap.ui5/flexBundle` ve
    `sap.ui5/models/i18n/settings/supportedLocales`. Bu iki yol YEREL'de YOKSA canlıdan çıkarılıp
    JSON olarak kıyaslanır. Yerelde varsa değerleri normal kıyaslanır. Başka HER manifest farkı
    (başka modelin supportedLocales'i dahil) GERCEK-FARK'tır — ölçülmemiş dönüşüm varsayılmaz.

SATIR SONU — `--eslik` sonucunda AÇIKÇA sınıflanır (deploy_ui Q281 sözlüğü):
  `ESLIK-TAM` (preload sha eşit) · `ESLIK-SATIR-SONU` (içerik modül modül eşit, fark YALNIZ string
  modüllerindeki kaçışlı `\\r\\n` — canlı CRLF ağaçtan build edilmiş, geri kurma LF yazar) ·
  `ESLIK-YOK` (DUR). Issue #304 ölçümü: kaynak LF → preload AYNI; CRLF bırakılınca SATIR_SONU.

Bağlantı / BSP adı / sha / satır sonu / preload kıyası `deploy_ui`'dan GELİR — kopya üretilmez
(`read_conn`, `bsp_name`, `sha`, `satir_sonu_normalize`, `preload_karsilastir`, `run`, `REPO`).
Metin uzantıları ve `\\uXXXX` deseni `verify_ui_static_assets`'ten gelir (`TEXT_SUFFIXES`, `_U_KACIS`).

Kullanım:
    python core/scripts/fetch_ui_source.py --bsp ZSD001_APP --eslik --ui5-cli "<ui>/node_modules/.bin/ui5"
    python core/scripts/fetch_ui_source.py --app-dir <ui>/<app> --karsilastir <ui>/<app>/webapp
    python core/scripts/fetch_ui_source.py --bsp ZSD001_APP --out <scratch>/webapp --zip-kaydet <scratch>/canli.zip
    python core/scripts/fetch_ui_source.py --zip <scratch>/canli.zip --karsilastir <ui>/<app>/webapp

Çıkış kodu: 0 = istenen her adım temiz (eşlik TAM/SATIR-SONU; karşılaştırmada yalnız AYNI ve
BUILD-DONUSUMU) · 1 = fark var / eşlik YOK · 2 = ÖLÇÜLEMEDİ ya da kullanım hatası (ağ, ui5 CLI
yok, zip'te preload yok, `--out` dolu…). ⛔ 2 asla "temiz" okunmaz.
Playbook: `playbook/howto-ui-kaynagi-geri-kurma.md`.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import difflib
import hashlib
import io
import json
import re
import shutil
import ssl
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Tek kaynak: bağlantı sözleşmesi, BSP adı, satır sonu ve preload kıyası deploy_ui'da yaşar.
from deploy_ui import (PRELOAD, REPO, SATIR_SONU, bsp_name, preload_karsilastir,  # noqa: E402
                       read_conn, run, satir_sonu_normalize, sha)
from verify_ui_static_assets import TEXT_SUFFIXES, _U_KACIS  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# @ui5/builder minifier.js `debugFileRegex`'inin TERSİ: `-dbg` bu son ek grubunun ÖNÜNDEDİR.
_DBG = re.compile(r"^(?P<ad>.+)-dbg(?P<sonek>(?:\.view|\.fragment|\.controller|\.designtime|\.support)?\.js)$")
_DBG_ILERI = re.compile(r"((?:\.view|\.fragment|\.controller|\.designtime|\.support)?\.js)$")   # builder'ın kendisi
# Build'in manifest'e EKLEDİĞİ, ölçülmüş yollar (3 BSP). Liste dışlama değil ÖLÇÜLEN listedir.
MANIFEST_BUILD_YOLLARI = (
    ("sap.ui5", "flexBundle"),
    ("sap.ui5", "models", "i18n", "settings", "supportedLocales"),
)
AYNI, BUILD, GERCEK, YALNIZ_CANLI, YALNIZ_YEREL = (
    "AYNI", "BUILD-DONUSUMU", "GERCEK-FARK", "YALNIZ-CANLI", "YALNIZ-YEREL")
ESLIK_TAM, ESLIK_SATIR_SONU, ESLIK_YOK = "ESLIK-TAM", "ESLIK-SATIR-SONU", "ESLIK-YOK"
_BSP_ADI = re.compile(r"^[A-Za-z0-9_/]+$")


class Olculemedi(Exception):
    """Ölçüm yapılamadı (ağ, yapılandırma, araç yok) — 'temiz' DEĞİL, çıkış 2."""


# ───────────────────────────── saf mantık (fixture'lı) ─────────────────────────────
def metin_mi(rel: str) -> bool:
    return Path(rel).suffix.lower() in TEXT_SUFFIXES


def dbg_kaynak_adi(rel: str) -> str | None:
    """`a/X-dbg.controller.js` → `a/X.controller.js`; `-dbg` dosyası değilse None."""
    dizin, _, ad = rel.rpartition("/")
    m = _DBG.match(ad)
    if not m:
        return None
    yeni = m.group("ad") + m.group("sonek")
    return f"{dizin}/{yeni}" if dizin else yeni


def dbg_adi(rel: str) -> str:
    """Küçültülmüş `a/X.controller.js` → `X-dbg.controller.js` (builder'ın İLERİ yönü, yalnız ad)."""
    return _DBG_ILERI.sub(r"-dbg\1", rel.rpartition("/")[2])


def harita_sondasi(dosyalar: dict[str, bytes]) -> list[str]:
    """Kaynak haritası sondası → sapma listesi (boş = beklenen biçim).

    ⛔ NEDEN: eşlik kapısı KÜÇÜLTÜLMÜŞ çıktıyı kıyaslar. `-dbg.js` bir TRANSPILE çıktısıysa
    (TypeScript vb.) ondan yeniden build de aynı küçültülmüş kodu üretir ⇒ preload EŞİT çıkar ama
    geri kurulan dosya özgün kaynak DEĞİLDİR. Ayırt edici iz haritadadır: düz JS build'inde
    `X.js.map` `sources`u YALNIZ `X-dbg.js`'i gösterir ve `-dbg` dosyasının kendi haritası yoktur
    (ölçüldü 3 BSP · 21/21 harita). Girdi build'den ÖNCE dönüştürülmüşse builder `-dbg`'e de harita
    üretir (minifier.js `dbgSourceMapResource`) ve `sources` özgün dosyayı gösterir."""
    sapma = []
    for rel in sorted(dosyalar):
        if not rel.endswith(".map") or rel.rpartition("/")[2] == PRELOAD + ".map":
            continue
        hedef = rel[:-4]
        if dbg_kaynak_adi(hedef):
            sapma.append(f"{rel}: -dbg dosyasının KENDİ haritası var (girdi build öncesi dönüştürülmüş?)")
            continue
        try:
            kaynaklar = json.loads(dosyalar[rel].decode("utf-8-sig")).get("sources")
        except (ValueError, UnicodeDecodeError, AttributeError):
            sapma.append(f"{rel}: harita okunamadı")
            continue
        beklenen = [dbg_adi(hedef)]
        if kaynaklar != beklenen:
            sapma.append(f"{rel}: sources={kaynaklar} (beklenen {beklenen})")
    return sapma


def geri_kur(dosyalar: dict[str, bytes]) -> tuple[dict[str, bytes], list[tuple[str, str]]]:
    """BSP dosyaları (rel → bayt) → (geri kurulan kaynak, [(atılan rel, neden)]).

    Metin dosyaları LF'e indirilir; ikili dosyalar HAM kalır."""
    dbg_hedef = {rel: h for rel in dosyalar if (h := dbg_kaynak_adi(rel))}
    kucultulmus = set(dbg_hedef.values())
    kaynak: dict[str, bytes] = {}
    atilan: list[tuple[str, str]] = []
    for rel in sorted(dosyalar):
        ad = rel.rpartition("/")[2]
        if ad in (PRELOAD, PRELOAD + ".map"):
            atilan.append((rel, "preload"))
            continue
        if rel.endswith(".map"):
            atilan.append((rel, "map"))
            continue
        if rel in kucultulmus:
            atilan.append((rel, "küçültülmüş (-dbg karşılığı var)"))
            continue
        hedef = dbg_hedef.get(rel, rel)
        b = dosyalar[rel]
        kaynak[hedef] = satir_sonu_normalize(b) if metin_mi(hedef) else b
    return kaynak, atilan


def properties_metni(b: bytes, kati: bool = False) -> str:
    """`.properties` → `\\uXXXX` çözülmüş LF metin (ters bölü paritesi korunur, vekil çiftleri
    birleşir). Yorum ve sıra KORUNUR — satır bazında kıyaslanır.
    `kati=True`: geçersiz UTF-8 ya da eşsiz vekil (`\\ud800`) → UnicodeDecodeError — farklı bozuk
    girdiler AYNI U+FFFD'ye inip "eşit" görünmesin. Meşru `\\ufffd` kaçışı katı kipte de geçer."""
    hata = "strict" if kati else "replace"
    t = satir_sonu_normalize(b).decode("utf-8", errors=hata)
    t = _U_KACIS.sub(lambda m: m.group(1) + chr(int(m.group(2), 16)), t)
    return t.encode("utf-16", "surrogatepass").decode("utf-16", errors=hata)


def _yol_al(obj, yol):
    for k in yol:
        if not isinstance(obj, dict) or k not in obj:
            return False, None
        obj = obj[k]
    return True, obj


def _yol_sil(obj, yol) -> None:
    for k in yol[:-1]:
        obj = obj[k]
    del obj[yol[-1]]


def manifest_kiyasla(canli: bytes, yerel: bytes) -> tuple[str, list[str], str, str]:
    """→ (sınıf, ayrıştırılan build yolları, canlı metni, yerel metni) — metinler diff içindir.

    Build yolu YALNIZ yerelde yoksa canlıdan çıkarılır; JSON olarak eşitse BUILD-DONUSUMU."""
    try:
        c, y = json.loads(canli.decode("utf-8-sig")), json.loads(yerel.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return GERCEK, [], _metin(canli), _metin(yerel)
    ayiklanan = []
    for yol in MANIFEST_BUILD_YOLLARI:
        canlida, _ = _yol_al(c, yol)
        yerelde, _ = _yol_al(y, yol)
        if canlida and not yerelde:
            _yol_sil(c, yol)
            ayiklanan.append("/".join(yol))
    # Tip-duyarlı kıyas: Python `==` true==1 / false==0 sayar ⇒ gerçek fark BUILD görünürdü.
    if json.dumps(c, sort_keys=True) == json.dumps(y, sort_keys=True):
        return BUILD, ayiklanan, "", ""
    return (GERCEK, ayiklanan, json.dumps(c, indent=2, ensure_ascii=False) + "\n",
            json.dumps(y, indent=2, ensure_ascii=False) + "\n")


def _metin(b: bytes) -> str:
    return satir_sonu_normalize(b).decode("utf-8", errors="replace")


def dosya_kiyasla(rel: str, canli: bytes, yerel: bytes) -> tuple[str, str, str, str]:
    """→ (sınıf, detay, canlı metni, yerel metni). Metinler yalnız GERCEK-FARK'ta doludur."""
    if not metin_mi(rel):
        if canli == yerel:
            return AYNI, "", "", ""
        return GERCEK, f"ikili: canlı {len(canli)}B sha {hashlib.sha256(canli).hexdigest()[:12]} · " \
                       f"yerel {len(yerel)}B sha {hashlib.sha256(yerel).hexdigest()[:12]}", "", ""
    if satir_sonu_normalize(canli) == satir_sonu_normalize(yerel):
        return AYNI, "", "", ""
    if Path(rel).suffix.lower() == ".properties":
        # İKİ taraf da KATI çözülür: `errors="replace"` farklı bozuk baytları aynı U+FFFD'ye indirip
        # gerçek farkı BUILD-DONUSUMU gösteriyordu (bug-gate 2026-09-26).
        for taraf, veri in (("yerel", yerel), ("canlı", canli)):
            try:
                properties_metni(veri, kati=True)
            except UnicodeDecodeError:
                return (GERCEK, f"{taraf} geçersiz UTF-8 / eşsiz vekil — build dönüşümü sayılmadı",
                        _metin(canli), _metin(yerel))
        pc, py = properties_metni(canli, kati=True), properties_metni(yerel, kati=True)
        if pc == py:
            return BUILD, "\\uXXXX kaçışı çözülünce satır satır eşit", "", ""
        return GERCEK, "\\uXXXX çözülmüş metin", pc, py
    if rel == "manifest.json":
        sinif, yollar, mc, my = manifest_kiyasla(canli, yerel)
        if sinif == BUILD:
            return BUILD, ("build yolları: " + ", ".join(yollar)) if yollar else "JSON eşit (yalnız biçim)", "", ""
        not_ = ("canlıdan ayıklanan build yolları: " + ", ".join(yollar)) if yollar else ""
        return GERCEK, not_, mc or _metin(canli), my or _metin(yerel)
    return GERCEK, "", _metin(canli), _metin(yerel)


def karsilastir(kaynak: dict[str, bytes], yerel: dict[str, bytes]) -> list[tuple[str, str, str, list[str]]]:
    """→ [(rel, sınıf, detay, unified-diff satırları)] — rel sıralı."""
    satirlar = []
    for rel in sorted(kaynak.keys() | yerel.keys()):
        if rel not in yerel:
            satirlar.append((rel, YALNIZ_CANLI, "", []))
            continue
        if rel not in kaynak:
            satirlar.append((rel, YALNIZ_YEREL, "", []))
            continue
        sinif, detay, mc, my = dosya_kiyasla(rel, kaynak[rel], yerel[rel])
        fark = []
        if sinif == GERCEK and (mc or my):
            fark = list(difflib.unified_diff(my.splitlines(), mc.splitlines(),
                                             f"yerel/{rel}", f"canli/{rel}", lineterm=""))
        satirlar.append((rel, sinif, detay, fark))
    return satirlar


def liste_kiyasla(canli: dict[str, bytes], dist: dict[str, bytes]) -> tuple[list, list, list, int]:
    """Ham BSP (zip) ↔ deploy edilecek dist → (yalnız-canlı, yalnız-dist, içeriği değişen, eşit sayısı).

    Deploy dist'i gönderir; yalnız-canlı = deploy SONRASI canlıda kalmayabilecek dosya (ör. yanlış
    `excludes` ile dist'e girmeyen `localService/**`). Metin satır sonu normalize, ikili ham."""
    ortak = canli.keys() & dist.keys()
    degisen = sorted(r for r in ortak if not (
        satir_sonu_normalize(canli[r]) == satir_sonu_normalize(dist[r]) if metin_mi(r) else canli[r] == dist[r]))
    return (sorted(canli.keys() - dist.keys()), sorted(dist.keys() - canli.keys()), degisen,
            len(ortak) - len(degisen))


def eslik_sinifi(build_preload: bytes, canli_preload: bytes) -> tuple[str, list[str]]:
    """deploy_ui.preload_karsilastir sözlüğü → eşlik sınıfı."""
    sinif, moduller = preload_karsilastir(build_preload, canli_preload)
    if sinif == "AYNI":
        return ESLIK_TAM, moduller
    if sinif == SATIR_SONU:
        return ESLIK_SATIR_SONU, moduller
    return ESLIK_YOK, moduller


# ───────────────────────────── G/Ç ─────────────────────────────
def zip_coz(zip_bayt: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bayt)) as z:
            return {n.replace("\\", "/").lstrip("/"): z.read(n) for n in z.namelist() if not n.endswith("/")}
    # z.read(): bozuk deflate → zlib.error · CRC → BadZipFile · şifreli → RuntimeError · desteksiz yöntem →
    # NotImplementedError. Hiçbiri çökme olmamalı: ÖLÇÜLEMEDİ (bug-gate 2026-09-26, bulgu 1).
    except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError) as e:
        raise Olculemedi(f"zip çözülemedi ({len(zip_bayt)}B): {type(e).__name__}: {e}")


def zip_indir(bsp: str, conn) -> tuple[bytes, dict]:
    """ABAP_REPOSITORY_SRV'den zip (yalnız GET). → (zip baytı, üst bilgi)."""
    base_url, user, pw, client = conn
    anahtar = urllib.parse.quote(bsp, safe="")
    url = (f"{base_url}/sap/opu/odata/UI5/ABAP_REPOSITORY_SRV/Repositories('{anahtar}')"
           f"?$format=json&CodePage='UTF8'&DownloadFiles='RUNTIME'&sap-client={client}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(url, method="GET", headers={
        "Authorization": f"Basic {auth}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=300) as r:
            govde = r.read()
    except urllib.error.HTTPError as e:
        raise Olculemedi(f"ABAP_REPOSITORY_SRV HTTP {e.code} ({bsp}) — BSP yok / yetki yok / servis kapalı")
    except Exception as e:  # ağ/TLS
        raise Olculemedi(f"ABAP_REPOSITORY_SRV erişilemedi ({type(e).__name__}: {e})")
    try:
        j = json.loads(govde)
    except ValueError:
        raise Olculemedi(f"yanıt JSON değil ({len(govde)}B)")
    d = j.get("d") if isinstance(j, dict) else None
    if not isinstance(d, dict):
        raise Olculemedi(f"yanıt OData biçiminde değil — `d` nesnesi yok ({type(j).__name__})")
    zb64 = d.get("ZipArchive")
    if not zb64:
        raise Olculemedi(f"yanıtta ZipArchive yok/boş — alanlar: {sorted(d.keys())}")
    ust = {k: d.get(k) for k in ("Name", "Package", "Description")}
    try:
        return base64.b64decode(zb64), ust
    except (binascii.Error, ValueError, TypeError) as e:
        raise Olculemedi(f"ZipArchive base64 çözülemedi ({type(e).__name__}: {e})")


def dizin_oku(kok: Path) -> dict[str, bytes]:
    return {p.relative_to(kok).as_posix(): p.read_bytes() for p in sorted(kok.rglob("*")) if p.is_file()}


def yaz(kaynak: dict[str, bytes], hedef: Path) -> None:
    """Önce TÜM yollar doğrulanır, sonra yazılır — reddedilen bir girdi kısmi yazım bırakmaz."""
    if hedef.exists() and not hedef.is_dir():
        raise Olculemedi(f"hedef bir dizin değil: {hedef}")
    kok = hedef.resolve()
    hedefler = []
    for rel, b in kaynak.items():
        p = hedef / rel
        if kok not in p.resolve().parents:   # zip içi `../` yolu hedef dışına yazamaz
            raise Olculemedi(f"zip girdisi hedef dizin dışını gösteriyor: {rel!r} — HİÇBİR dosya yazılmadı")
        hedefler.append((p, b))
    try:
        for p, b in hedefler:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)   # bayt kipi: metin zaten LF — platform satır sonu EKLENMEZ
    except OSError as e:
        raise Olculemedi(f"yazılamadı ({type(e).__name__}: {e})")


def baglanti() -> tuple:
    """`deploy_ui.read_conn()` `.conn_adt` yoksa `sys.exit(1)` yapar (deploy_ui değişmez) —
    burada ÖLÇÜLEMEDİ'ye çevrilir; boş URL/kullanıcı da aynı yerde yakalanır."""
    try:
        conn = read_conn()
    except SystemExit:
        raise Olculemedi(f".conn_adt okunamadı (proje kökü: {REPO}) — env CLAUDE_PROJECT_DIR / cwd")
    if not conn[0] or not conn[1]:
        raise Olculemedi(f".conn_adt'de ADT_SAP_URL / ADT_SAP_USER boş (proje kökü: {REPO})")
    return conn


def _uygulama_kimligi(kaynak: dict[str, bytes]) -> str:
    try:
        return json.loads(kaynak["manifest.json"].decode("utf-8-sig"))["sap.app"]["id"]
    except (KeyError, ValueError, TypeError, UnicodeDecodeError):
        raise Olculemedi("manifest.json yok ya da `sap.app.id` okunamadı — build projesi kurulamaz")


def eslik_olc(kaynak: dict[str, bytes], canli: dict[str, bytes], ui5_cli: str | None) -> tuple:
    """Geri kurulan kaynağı DEĞİŞTİRMEDEN derle → (sınıf, modüller, tam-liste özeti)."""
    if PRELOAD not in canli:
        raise Olculemedi(f"zip'te {PRELOAD} yok — eşlik ölçülemez (preload'suz build?)")
    cli = ui5_cli or shutil.which("ui5")
    if not cli:
        raise Olculemedi("ui5 CLI bulunamadı (PATH'te `ui5` yok) → `--ui5-cli \"<ui>/node_modules/.bin/ui5\"` ver")
    app_id = _uygulama_kimligi(kaynak)
    kum = Path(tempfile.mkdtemp(prefix="fetch_ui_eslik_"))
    try:
        yaz(kaynak, kum / "webapp")
        paket = re.sub(r"[^a-z0-9._-]", "-", app_id.lower()) or "app"
        (kum / "package.json").write_bytes(json.dumps(
            {"name": paket, "version": "0.0.0", "private": True}, indent=2).encode() + b"\n")
        (kum / "ui5.yaml").write_bytes(
            f'specVersion: "4.0"\nmetadata:\n  name: {app_id}\ntype: application\n'.encode())
        komut = f'"{cli}" build --config ui5.yaml --clean-dest --dest dist'
        rc, cikti = run(komut, kum, None)
        dist = kum / "dist"
        if rc != 0 or not (dist / PRELOAD).is_file():
            raise Olculemedi(f"ui5 build rc={rc}: {cikti.strip()[-400:]}")
        build = dizin_oku(dist)
        sinif, moduller = eslik_sinifi(build[PRELOAD], canli[PRELOAD])
        farkli = sorted(r for r in canli.keys() & build.keys()
                        if not (satir_sonu_normalize(canli[r]) == satir_sonu_normalize(build[r]) if metin_mi(r)
                                else canli[r] == build[r]))
        ozet = (len(canli.keys() & build.keys()) - len(farkli), len(canli), farkli,
                sorted(canli.keys() - build.keys()), sorted(build.keys() - canli.keys()))
        return sinif, moduller, ozet
    finally:
        shutil.rmtree(kum, ignore_errors=True)
        if kum.exists():
            print(f"  ⚠ geçici build dizini silinemedi: {kum}", file=sys.stderr)


def _kisalt(adlar: list, n: int = 6) -> str:
    return ", ".join(adlar[:n]) + (f" (+{len(adlar) - n})" if len(adlar) > n else "")


KARSILASTIRMA_TANIMI = ("dosya listesi + içerik; build dönüşümü YALNIZ .properties \\uXXXX ve manifest "
                        + " · ".join("/".join(y) for y in MANIFEST_BUILD_YOLLARI))


def istek_durumu(istendi: bool, sebep: str) -> str:
    """Koşmayan adımın dürüst etiketi: istenip koşmadıysa İSTENMEDİ YAZILMAZ."""
    return f"İSTENDİ — KOŞMADI ({sebep})" if istendi else "İSTENMEDİ"


def kapsam_beyani(zip_kaynagi: str, eslik_durumu: str, karsilastirma: str, deploy_notu: str,
                  out_notu: str) -> str:
    return "\n".join([
        "KAPSAM BEYANI:",
        f"  bakılan  : {zip_kaynagi} · geri kurma = -dbg kuralı (ui5 builder debugFileRegex tersi)",
        f"             metin (LF) = {', '.join(sorted(TEXT_SUFFIXES))} · diğer uzantılar ham bayt",
        f"  eşlik    : {eslik_durumu}",
        f"  --out    : {out_notu}",
        f"  deploy listesi: {deploy_notu}",
        f"  karşılaştırma: {karsilastirma}",
        "  BAKILMAYAN: canlı = indirilen zip anı (ICF servis katmanı / HTML meta enjeksiyonu ölçülmedi) ·",
        "             TypeScript ya da özel build — preload kıyası KÜÇÜLTÜLMÜŞ kodu ölçer, transpile edilmiş -dbg",
        "             ondan eşit çıktı üretebilir; tek ayırt edici kaynak haritası sondasıdır (canlı TS BSP'de",
        "             DOĞRULANMADI) · -dbg'de küçültmede kaybolan yorum/biçim farkı · Fiori Elements ·",
        "             namespace'li BSP adı (/X/…) · deploy'un canlıdan dosya SİLME davranışı ·",
        "             manifest'te ölçülen iki yol DIŞINDAKİ build eklemeleri (GERCEK-FARK görünür).",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BSP kaynağını SAP'den SALT-OKUR geri kur + canlıyla eşlik/karşılaştırma")
    kaynak_g = ap.add_mutually_exclusive_group(required=True)
    kaynak_g.add_argument("--bsp", help="BSP adı (ör. ZSD001_APP)")
    kaynak_g.add_argument("--app-dir", help="ui5-deploy.yaml'ı olan app dizini (BSP adı oradan okunur)")
    kaynak_g.add_argument("--zip", help="AĞ YOK: önceden kaydedilmiş zip (--zip-kaydet çıktısı)")
    ap.add_argument("--out", help="geri kurulan webapp'in yazılacağı dizin (yok ya da BOŞ olmalı)")
    ap.add_argument("--karsilastir", help="yerel webapp dizini ile karşılaştır")
    ap.add_argument("--dist-karsilastir",
                    help="deploy edilecek dist dizininin DOSYA LİSTESİ ↔ canlı ham liste (deploy öncesi/sonrası)")
    ap.add_argument("--eslik", action="store_true", help="değiştirmeden ui5 build → zip preload ile kıyasla")
    ap.add_argument("--ui5-cli", help="ui5 CLI yolu (varsayılan: PATH'teki `ui5`)")
    ap.add_argument("--zip-kaydet", help="indirilen ham zip'i bu dosyaya yaz")
    ap.add_argument("--diff-satir", type=int, default=400, help="dosya başına basılan diff satırı üst sınırı")
    a = ap.parse_args(argv)

    out = Path(a.out) if a.out else None
    if out is not None and out.is_dir() and any(out.iterdir()):
        print(f"[KULLANIM] --out dizini dolu: {out} — yerel kaynağın üzerine yazılmaz. Boş dizin ver; "
              "yerelle kıyas için --karsilastir kullan.", file=sys.stderr)
        return 2
    yerel_kok = Path(a.karsilastir) if a.karsilastir else None
    if yerel_kok is not None and not yerel_kok.is_dir():
        print(f"[KULLANIM] --karsilastir dizini yok: {yerel_kok}", file=sys.stderr)
        return 2
    dist_kok = Path(a.dist_karsilastir) if a.dist_karsilastir else None
    if dist_kok is not None and not dist_kok.is_dir():
        print(f"[KULLANIM] --dist-karsilastir dizini yok: {dist_kok} (önce `npm run build`)", file=sys.stderr)
        return 2

    # Kapsam beyanı: koşmayan ama İSTENEN adım "İSTENMEDİ" yazılmaz (bug-gate 2026-09-26, bulgu 5).
    bekliyor = istek_durumu(True, "henüz koşmadı")
    durum = {
        "eslik": bekliyor if a.eslik else "İSTENMEDİ (--eslik yok) — geri kurmanın build-eşliği ÖLÇÜLMEDİ",
        "kars": istek_durumu(yerel_kok is not None, "henüz koşmadı"),
        "dist": istek_durumu(dist_kok is not None, "henüz koşmadı"),
        "out": istek_durumu(out is not None, "henüz koşmadı"),
    }

    def beyan(zip_k: str, sebep: str | None = None) -> str:
        if sebep is not None:   # erken çıkış: istenip henüz koşmamış her adım bu sebeple işaretlenir
            for k in durum:
                if durum[k] == bekliyor:
                    durum[k] = istek_durumu(True, sebep)
        return kapsam_beyani(zip_k, durum["eslik"], durum["kars"], durum["dist"], durum["out"])

    def olculemedi(zip_k: str, mesaj: str) -> int:
        print(f"[OLCULEMEDI] {mesaj}", file=sys.stderr)
        print(beyan(zip_k, f"ÖLÇÜLEMEDİ: {mesaj}"))
        return 2

    zip_kaynagi = "— (indirme BAŞARISIZ)"
    try:
        if a.zip:
            try:
                zip_bayt = Path(a.zip).read_bytes()
            except OSError as e:
                raise Olculemedi(f"--zip okunamadı: {a.zip} ({type(e).__name__})")
            zip_kaynagi = f"yerel zip {a.zip} (AĞ YOK)"
        else:
            bsp = a.bsp or bsp_name(Path(a.app_dir))
            if not bsp:
                print(f"[KULLANIM] {a.app_dir}/ui5-deploy.yaml'da BSP adı (Z…) bulunamadı", file=sys.stderr)
                return 2
            if not _BSP_ADI.match(bsp):
                print(f"[KULLANIM] geçersiz BSP adı: {bsp!r}", file=sys.stderr)
                return 2
            print(f"=== İNDİR (yalnız GET): ABAP_REPOSITORY_SRV Repositories('{bsp}') — proje={REPO} ===")
            zip_bayt, ust = zip_indir(bsp, baglanti())
            print(f"  Name={ust['Name']} Package={ust['Package']} Description={ust['Description']!r}")
            zip_kaynagi = f"ABAP_REPOSITORY_SRV zip ({bsp})"
            if a.zip_kaydet:
                Path(a.zip_kaydet).parent.mkdir(parents=True, exist_ok=True)
                Path(a.zip_kaydet).write_bytes(zip_bayt)
                print(f"  ham zip kaydedildi: {a.zip_kaydet} ({len(zip_bayt)}B)")
        canli = zip_coz(zip_bayt)
    except Olculemedi as e:
        return olculemedi(zip_kaynagi, str(e))
    # Yanıt/zip biçimi bozuk (dict olmayan JSON · base64 · CRC/deflate · dosya G/Ç): çökme DEĞİL, ÖLÇÜLEMEDİ.
    except (ValueError, AttributeError, binascii.Error, zlib.error, OSError, zipfile.BadZipFile) as e:
        return olculemedi(zip_kaynagi, f"indirme/çözme ({type(e).__name__}: {e})")

    kaynak, atilan = geri_kur(canli)
    zip_kaynagi += f" — {len(canli)} dosya → {len(kaynak)} kaynak, {len(atilan)} atıldı"
    print(f"\n=== GERİ KURMA: {len(canli)} dosya → {len(kaynak)} kaynak · {len(atilan)} atıldı "
          f"(preload {sum(1 for _, n in atilan if n == 'preload')} · map {sum(1 for _, n in atilan if n == 'map')} "
          f"· küçültülmüş {sum(1 for _, n in atilan if n.startswith('küçültülmüş'))}) ===")
    dbg_sayisi = sum(1 for r in canli if dbg_kaynak_adi(r))
    if not dbg_sayisi and any(r.endswith(".js") for r in canli):
        print("  ⚠ zip'te hiç `-dbg` dosyası yok — küçültülmemiş build ya da özel build; .js AYNEN kopyalandı "
              "(özgün kaynak olduğu KANITLANMADI → --eslik koş)")
    sapma = harita_sondasi(canli)
    for s in sapma:
        print(f"  ⚠ KAYNAK HARİTASI SAPMASI: {s}")
    if sapma:
        print("    → geri kurulan -dbg dosyaları ÖZGÜN KAYNAK OLMAYABİLİR (TypeScript/transpile?). "
              "--eslik bu durumda DURUR.")

    rc = 0
    if a.eslik:
        try:
            sinif, moduller, (esit, toplam, farkli, yalniz_c, yalniz_b) = eslik_olc(kaynak, canli, a.ui5_cli)
        except Olculemedi as e:
            durum["eslik"] = f"ÖLÇÜLEMEDİ — {e}"
            return olculemedi(zip_kaynagi, f"eşlik: {e}")
        print(f"\n=== EŞLİK: değiştirilmemiş kaynak → ui5 build → {PRELOAD} ↔ zip {PRELOAD} ===")
        if sinif == ESLIK_TAM:
            print(f"  [{ESLIK_TAM}] preload sha(norm) eşit")
        elif sinif == ESLIK_SATIR_SONU:
            print(f"  [{ESLIK_SATIR_SONU}] içerik modül modül EŞİT; fark YALNIZ kaçışlı \\r\\n "
                  f"({len(moduller)} modül: {_kisalt(moduller)}) — canlı CRLF ağaçtan build edilmiş, "
                  "geri kurma LF yazar. Bayt-eş DEĞİL; ayrı kova.")
        else:
            print(f"  ⛔ [{ESLIK_YOK}] build çıktısı canlıdan FARKLI"
                  + (f" — modül ({len(moduller)}): {_kisalt(moduller)}" if moduller else
                     " — preload haritası ayrıştırılamadı, hash hükmü geçerli")
                  + "\n     Geri kurulan kaynak canlıyı ÜRETMİYOR (TypeScript / özel build / farklı tooling?).")
        # Tam liste — preload DIŞINDAKİ her dosya (preload yukarıda modül modül kıyaslandı).
        liste_farki = [r for r in farkli if r != PRELOAD] + yalniz_c + yalniz_b
        print(f"  tam liste: {esit}/{toplam} canlı dosya build çıktısıyla eşit"
              + (f" · farklı {len(farkli)}: {_kisalt(farkli)}" if farkli else "")
              + (f" · yalnız-canlı {len(yalniz_c)}: {_kisalt(yalniz_c)}" if yalniz_c else "")
              + (f" · yalnız-build {len(yalniz_b)}: {_kisalt(yalniz_b)}" if yalniz_b else ""))
        if liste_farki and sinif != ESLIK_YOK:
            print(f"  ⛔ [{ESLIK_YOK}] preload {sinif} AMA preload dışında {len(liste_farki)} dosya farklı/eksik "
                  f"({_kisalt(liste_farki)}) — küçültmede kaybolan bir -dbg farkı haritada iz bırakır.")
            sinif = ESLIK_YOK
        if sapma and sinif != ESLIK_YOK:
            print(f"  ⛔ [{ESLIK_YOK}] preload {sinif} AMA kaynak haritası sapması var ({len(sapma)}) — "
                  "yeniden build küçültülmüş kodu eşit üretse bile -dbg özgün kaynak değil (yukarıdaki ⚠ satırları).")
            sinif = ESLIK_YOK
        durum["eslik"] = f"{sinif} (build ↔ aynı zip'teki {PRELOAD}; deploy_ui.preload_karsilastir)"
        if sinif == ESLIK_YOK:
            print("     DUR: --out, --karsilastir ve --dist-karsilastir KOŞMADI; kaynağı kullanıcıdan iste.")
            print("\n" + beyan(zip_kaynagi, f"{ESLIK_YOK} → DUR"))
            return 1

    if out is not None:
        try:
            yaz(kaynak, out)
        except Olculemedi as e:
            return olculemedi(zip_kaynagi, f"--out: {e}")
        durum["out"] = f"YAZILDI — {len(kaynak)} dosya → {out}"
        print(f"\n=== YAZILDI: {len(kaynak)} dosya → {out} (metin LF, ikili ham) ===")

    if yerel_kok is not None:
        satirlar = karsilastir(kaynak, dizin_oku(yerel_kok))
        print(f"\n=== KARŞILAŞTIR: canlı (geri kurulan) ↔ yerel {yerel_kok} ===")
        sayim: dict[str, int] = {}
        for rel, sinif, detay, fark in satirlar:
            sayim[sinif] = sayim.get(sinif, 0) + 1
            if sinif == AYNI:
                continue
            print(f"  {sinif:<15} {rel}" + (f"  — {detay}" if detay else ""))
            for s in fark[:a.diff_satir]:
                print(f"      {s}")
            if len(fark) > a.diff_satir:
                print(f"      … diff kısaltıldı: {len(fark) - a.diff_satir} satır daha (--diff-satir)")
        print("  ÖZET: " + " · ".join(f"{k}={sayim.get(k, 0)}"
                                      for k in (AYNI, BUILD, GERCEK, YALNIZ_CANLI, YALNIZ_YEREL))
              + f" (toplam {len(satirlar)})")
        if any(sayim.get(k) for k in (GERCEK, YALNIZ_CANLI, YALNIZ_YEREL)):
            rc = 1
        durum["kars"] = KARSILASTIRMA_TANIMI

    if dist_kok is not None:
        yalniz_c, yalniz_d, degisen, esit = liste_kiyasla(canli, dizin_oku(dist_kok))
        print(f"\n=== DEPLOY LİSTESİ: canlı ham ({len(canli)}) ↔ dist {dist_kok} ===")
        for r in yalniz_c:
            print(f"  {YALNIZ_CANLI:<15} {r}  — dist'te YOK: deploy sonrası canlıda kalmayabilir")
        for r in yalniz_d:
            print(f"  {'YALNIZ-DIST':<15} {r}  — canlıya YENİ girecek")
        for r in degisen:
            print(f"  {'DEGISECEK':<15} {r}")
        print(f"  ÖZET: eşit={esit} · değişecek={len(degisen)} · yalnız-dist={len(yalniz_d)} · "
              f"YALNIZ-CANLI={len(yalniz_c)}")
        if yalniz_c:
            print("  ⛔ canlıda olup deploy kümesinde olmayan dosya var — bilinçli silme mi, yanlış "
                  "`excludes` mu? Kullanıcıya göster (standards/03 §2.4).")
            rc = 1
        durum["dist"] = f"canlı ham ↔ {dist_kok} (ad + içerik)"

    print("\n" + beyan(zip_kaynagi))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

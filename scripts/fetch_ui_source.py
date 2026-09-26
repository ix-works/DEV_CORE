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
     `--damgala`             PULL-BEFORE-EDIT (ADR 0016, Q352-B) seans-tazelik damgası: `--karsilastir
                             <app>/webapp` TEMİZ çıkarsa o webapp'in dosyaları seans-taze damgalanır →
                             kapı (`hooks/_pbe_ui`) düzenlemeye izin verir. Damga YALNIZ: taze indirme
                             (`--zip` → YOK) · rc 0 · kaynak haritası sapması yok · webapp kapının kapsamında
                             (proje kökü DIŞINDAKİ `.wt` worktree'si dahil — anahtar mutlak; ABAP kapısıyla
                             simetrik) ve BSP'si app'in `ui5-deploy.yaml`'ıyla tutarlı. ⚠ Store + anahtar
                             kökü `CLAUDE_PROJECT_DIR`'den, boşsa CWD'den çözülür (ABAP ile ortak;
                             ertelendi T-PBE-KOK-CWD) ⇒ kapı damgayı YALNIZ araç proje kökünden (ya da
                             `CLAUDE_PROJECT_DIR` ile) koşulduğunda görür; araç yazdığı store'u + kökü basar. Bu kipte YALNIZ `deploy-to-abap` görevinin `configuration.exclude`
                             önekleri (HARF DUYARLI — deploy aracı `RegExp(regex,"g")`) altındaki
                             YALNIZ-YEREL dosyalar `DEPLOY-DISI` etiketlenir (canlıya hiç gitmez;
                             rc'ye sayılmaz). rc 1/2'de ASLA damga yok. `--session` opsiyonel geçersiz kılma
                             (varsayılan: SessionStart marker'ı, `source_drift.seans_kimligi`).
     `--offline`             (yalnız `--damgala` ile) İNDİRMEDEN damgala — `sap_sync_pull --offline` ile
                             aynı anlam: SAP erişilemiyor / yerel canlıdan İLERİDE (commit'li ama henüz
                             deploy edilmemiş iş); canlıdaki belgelenmemiş değişikliği ezme riskini
                             BİLEREK kabul edersin. Görünür uyarı basar.

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
import os
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
DEPLOY_DISI = "DEPLOY-DISI"   # yalnız --damgala: deploy `exclude` altında YALNIZ-YEREL (canlıya hiç gitmez)
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


def _json_norm(o):
    """JS sayı anlambilimi: tam-sayı değerli float → int (`1.0`, `1e3` = `1`, `1000`). bool AYRI kalır
    (Python'da bool int'in alt sınıfıdır ama `true` hiçbir zaman `1`e eşit sayılmaz)."""
    if isinstance(o, bool):
        return o
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: _json_norm(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_json_norm(v) for v in o]
    return o


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
    # Tip-duyarlı kıyas: Python `==` true==1 / false==0 sayar ⇒ gerçek fark BUILD görünürdü. Sayılar
    # JS anlambilimiyle (manifestEnhancer JSON.parse→stringify): 1 ≡ 1.0 ≡ 1e0 — `_json_norm`.
    if json.dumps(_json_norm(c), sort_keys=True) == json.dumps(_json_norm(y), sort_keys=True):
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


def ui_eklenti_modulu():
    """PULL-BEFORE-EDIT UI eklentisi (`hooks/_pbe_ui.py`; `_` öneki = hook değil yardımcı modül, C-TPL-01) — kapsam + deploy-exclude TEK KAYNAĞI."""
    hooks = str(Path(__file__).resolve().parent / "hooks")
    if hooks not in sys.path:
        sys.path.append(hooks)
    import _pbe_ui
    return _pbe_ui


def deploy_disi_etiketle(satirlar: list, onekler) -> list:
    """YALNIZ-YEREL + deploy `exclude` altında → DEPLOY-DISI (yalnız --damgala kipinde çağrılır)."""
    pbe = ui_eklenti_modulu()
    return [(r, DEPLOY_DISI if s == YALNIZ_YEREL and pbe.deploy_haric_mi(r, onekler) else s, d, f)
            for r, s, d, f in satirlar]


def damga_engeli(satirlar: list, zip_taze: bool, sapma: list, rc: int) -> str | None:
    """Damga kararı (saf). None = damgalanabilir; aksi hâlde görünür NEDEN.

    ⛔ Damga = kapıya "bu dosya canlıyla eşit" beyanıdır; sahte-taze damga kapıyı öldürür.
    Bu yüzden ölçüm kanıtı zayıf her dal (anlık görüntü, harita sapması, rc≠0) damgayı keser."""
    if not zip_taze:
        return "girdi `--zip` anlık görüntüsü — canlının BUGÜNKÜ hâli ölçülmedi"
    if rc != 0:
        return f"çıkış kodu {rc} (istenen adımlardan biri temiz değil)"
    if sapma:
        return f"kaynak haritası sapması ({len(sapma)}) — geri kurulan -dbg özgün kaynak olmayabilir"
    kalan = [r for r, s, _, _ in satirlar if s not in (AYNI, BUILD, DEPLOY_DISI)]
    if kalan:
        return f"{len(kalan)} dosya canlıyla eşit değil: {_kisalt(kalan)}"
    return None


def damga_yeri() -> str:
    """Damganın HANGİ store'a, hangi köke göre yazıldığı (bug gate 2. tur: cwd'ye düşen kök
    yanıltıcı \"damgalandı\" üretiyordu — kapı başka store'a bakar). Kök çözümü değişmez."""
    try:
        import source_drift as sd
        store = str(sd.FRESH_STORE)
    except Exception as e:   # noqa: BLE001
        return f"store=ÖLÇÜLEMEDİ ({type(e).__name__}) · anahtar kökü={REPO}"
    s = f"store={store} · anahtar kökü={REPO}"
    # Uyarı YALNIZ kök şüpheliyse (3. tur): env boş ajan Bash'inde olağandır; proje kökünden koşulduğunda
    # (kökte `project.yaml` var) tek satır bilgi yeter. Env boş VE kökte proje işareti yoksa ⚠.
    if not os.environ.get("CLAUDE_PROJECT_DIR") and not (Path(REPO) / "project.yaml").is_file():
        s += (f" · ⚠ CLAUDE_PROJECT_DIR BOŞ ve çalışma dizini ({Path.cwd()}) proje kökü DEĞİL (project.yaml yok) "
              "— kapı başka kökte koşuyorsa bu damgayı GÖRMEZ (proje kökünden koş ya da CLAUDE_PROJECT_DIR=<proje> ver)")
    return s


def damgala(webapp: Path, rels: list, session: str | None) -> tuple[list[str], str | None]:
    """webapp/rel dosyalarını seans-taze damgala → (yazılan anahtarlar, hata ya da None).

    Tek kaynak: `source_drift.seans_kimligi` + `tazelik_damgala` (kapı AYNI anahtarı okur)."""
    try:
        import source_drift as sd
        seans = sd.seans_kimligi(session or "")
        damga = sd.tazelik_damgala
    except (ImportError, AttributeError) as e:
        return [], f"damga altyapısı yüklenemedi (source_drift: {type(e).__name__}: {e})"
    if not seans or seans == "default":
        return [], ("seans kimliği çözülemedi (SessionStart marker'ı yok) — kapı bu damgayı "
                    "EŞLEŞTİRMEZ; `--session <id>` ver")
    yazilan, eksik = [], []
    for rel in rels:
        k = damga(seans, webapp / rel, REPO)
        if k:
            yazilan.append(k)
        else:
            eksik.append(rel)
    if eksik:
        return yazilan, f"{len(eksik)} dosya damgalanamadı: {_kisalt(eksik)}"
    return yazilan, None


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
            dosyalar = {n.replace("\\", "/").lstrip("/"): z.read(n) for n in z.namelist() if not n.endswith("/")}
    # z.read(): bozuk deflate → zlib.error · CRC → BadZipFile · şifreli → RuntimeError · desteksiz yöntem →
    # NotImplementedError. Hiçbiri çökme olmamalı: ÖLÇÜLEMEDİ (bug-gate 2026-09-26, bulgu 1).
    except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError) as e:
        raise Olculemedi(f"zip çözülemedi ({len(zip_bayt)}B): {type(e).__name__}: {e}")
    cakisma = harf_cakismasi(dosyalar)
    if cakisma:   # re-gate P-2: sessiz üzerine yazma / tek yerel dosyayla iki kaynak eşlemesi olmasın
        raise Olculemedi(f"zip'te yalnız harf büyüklüğüyle ayrışan girdiler: {cakisma[:3]} — büyük/küçük harf "
                         "duyarsız dosya sisteminde tek dosyaya düşer")
    return dosyalar


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
    """`kok` altındaki her dosya → {bağ ÜZERİNDEN görünen posix rel: bayt}.

    Dizin bağları (Windows junction · Windows dizin symlink'i · POSIX symlink) PLATFORMDAN BAĞIMSIZ
    izlenir (Q352-B 5. tur). Eskiden `rglob("*")`: Py 3.11/3.12 `entry.is_dir(follow_symlinks=False)`
    ile özyineler ⇒ junction'a iner, symlink'e inmez (3.13'te `recurse_symlinks` ayrı). Sonuç: kapı
    `webapp/lnkdis/s.js`'i bloklar ama symlink platformunda `--damgala` o dosyayı hiç listelemezdi ⇒
    blok mesajındaki komut kilidi açamazdı = kalıcı kilit (Linux CI, fixture pbe_ui C8).
    Döngü koruması: yalnız ATA zincirindeki bir dizini (realpath) gösteren bağa inilmez — aynı hedefe
    giden iki ayrı bağ iki kez listelenir (junction'daki eski davranış). G/Ç hatası YUTULMAZ
    (çağıranlar OSError'ı ÖLÇÜLEMEDİ'ye çevirir; `rglob` PermissionError'lı dizini sessizce atlıyordu)."""
    sonuc: dict[str, bytes] = {}

    def gez(dizin: str, onek: str, atalar: frozenset) -> None:
        with os.scandir(dizin) as it:
            girdiler = sorted(it, key=lambda e: e.name)
        for e in girdiler:
            rel = onek + e.name
            if e.is_dir():   # follow_symlinks=True (varsayılan): junction + symlink AYNI davranır
                gercek = os.path.normcase(os.path.realpath(e.path))
                if gercek not in atalar:   # bağ kendi atasını gösteriyorsa (döngü) inilmez
                    gez(e.path, rel + "/", atalar | {gercek})
            elif e.is_file():   # dosya symlink'i izlenir; kırık bağ atlanır (eski `is_file()` ile aynı)
                with open(e.path, "rb") as f:
                    sonuc[rel] = f.read()

    gez(str(kok), "", frozenset({os.path.normcase(os.path.realpath(kok))}))
    return dict(sorted(sonuc.items()))


def harf_cakismasi(adlar) -> list[tuple[str, str]]:
    """Yalnız büyük/küçük harfle ayrışan yol çiftleri — Windows/macOS varsayılan dosya sisteminde TEK dosyaya
    düşer (sessiz üzerine yazma). Karşılaştırmada da iki ayrı kaynak tek yerel dosyayla eşleşemez."""
    gorulen: dict[str, str] = {}
    cift = []
    for a in sorted(adlar):
        k = a.casefold()
        if k in gorulen:
            cift.append((gorulen[k], a))
        else:
            gorulen[k] = a
    return cift


def yaz(kaynak: dict[str, bytes], hedef: Path) -> None:
    """ATOMİK: önce TÜM yollar doğrulanır, sonra kardeş geçici dizine yazılır, bitince hedefe taşınır.
    Doğrulama reddi ya da yazım ORTASINDAKİ G/Ç hatası (dosya↔dizin çakışması, disk, izin, yol uzunluğu)
    hedefte KISMİ ağaç bırakmaz (re-gate R2, 2026-09-26)."""
    if hedef.exists() and not hedef.is_dir():
        raise Olculemedi(f"hedef bir dizin değil: {hedef}")
    hedef_vardi = hedef.is_dir()   # dolu hedef: main ön kontrolü reddeder; olsa da rmdir() düşer → dokunulmaz
    cakisma = harf_cakismasi(kaynak)
    if cakisma:
        raise Olculemedi(f"geri kurulan kaynakta yalnız harf büyüklüğüyle ayrışan yollar: {cakisma[:3]} — "
                         "büyük/küçük harf duyarsız dosya sisteminde üzerine yazılır; HİÇBİR dosya yazılmadı")
    kok = hedef.resolve()
    for rel in kaynak:
        if kok not in (hedef / rel).resolve().parents:   # zip içi `../` yolu hedef dışına yazamaz
            raise Olculemedi(f"zip girdisi hedef dizin dışını gösteriyor: {rel!r} — HİÇBİR dosya yazılmadı")
    try:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        gecici = Path(tempfile.mkdtemp(prefix=f".{hedef.name}.yaziliyor-", dir=hedef.parent))
    except OSError as e:
        raise Olculemedi(f"geçici yazım dizini açılamadı ({type(e).__name__}: {e})")
    try:
        for rel, b in kaynak.items():
            p = gecici / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)   # bayt kipi: metin zaten LF — platform satır sonu EKLENMEZ
        if hedef_vardi:
            hedef.rmdir()      # boş olduğu yukarıda doğrulandı; Windows'ta os.replace var olan dizine taşımaz
        os.replace(gecici, hedef)
    except OSError as e:
        shutil.rmtree(gecici, ignore_errors=True)
        if hedef_vardi and not hedef.exists():
            hedef.mkdir()
        kalan = f" · ⚠ geçici dizin SİLİNEMEDİ: {gecici}" if gecici.exists() else ""
        raise Olculemedi(f"yazılamadı ({type(e).__name__}: {e}) — hedef DOKUNULMADI (atomik yazım){kalan}")


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
    try:
        kum = Path(tempfile.mkdtemp(prefix="fetch_ui_eslik_"))
    except OSError as e:   # re-gate P-1: geçici build dizini açılamıyorsa çökme değil ÖLÇÜLEMEDİ
        raise Olculemedi(f"eşlik: geçici build dizini açılamadı ({type(e).__name__}: {e})")
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
    except OSError as e:   # re-gate P-1: package.json/ui5.yaml yazımı · dist okuma
        raise Olculemedi(f"eşlik: build dizini G/Ç ({type(e).__name__}: {e})")
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
                  out_notu: str, damga_notu: str = "İSTENMEDİ") -> str:
    return "\n".join([
        "KAPSAM BEYANI:",
        f"  bakılan  : {zip_kaynagi} · geri kurma = -dbg kuralı (ui5 builder debugFileRegex tersi)",
        f"             metin (LF) = {', '.join(sorted(TEXT_SUFFIXES))} · diğer uzantılar ham bayt",
        f"  eşlik    : {eslik_durumu}",
        f"  --out    : {out_notu}",
        f"  deploy listesi: {deploy_notu}",
        f"  karşılaştırma: {karsilastirma}",
        f"  PBE damgası: {damga_notu}",
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
    ap.add_argument("--damgala", action="store_true",
                    help="--karsilastir <app>/webapp TEMİZse webapp dosyalarını PULL-BEFORE-EDIT seans-taze damgala")
    ap.add_argument("--session", default="", help="(--damgala) seans kimliği; boşsa SessionStart marker'ı")
    ap.add_argument("--offline", action="store_true",
                    help="(--damgala) İNDİRMEDEN damgala — canlıdan ezme riskini BİLEREK kabul (sap_sync_pull --offline)")
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

    # PULL-BEFORE-EDIT damgası (Q352-B): kullanım denetimleri İNDİRMEDEN önce — sahte-taze damga
    # üretebilecek her bileşim burada reddedilir (rc 2, hiçbir şey damgalanmaz).
    damga_onekler: list[str] = []
    damga_anlasilmayan: list[str] = []
    if a.offline and not a.damgala:
        print("[KULLANIM] --offline yalnız --damgala ile anlamlıdır", file=sys.stderr)
        return 2
    if a.damgala:
        if yerel_kok is None:
            print("[KULLANIM] --damgala, --karsilastir <app>/webapp ister (damga = karşılaştırılan dosyalar)",
                  file=sys.stderr)
            return 2
        if a.zip:
            print("[KULLANIM] --damgala TAZE indirme ister; --zip anlık görüntüsüyle damga YAZILMAZ "
                  "(canlının bugünkü hâli ölçülmemiş olur)", file=sys.stderr)
            return 2
        if a.offline and (a.eslik or out is not None or dist_kok is not None or a.zip_kaydet):
            print("[KULLANIM] --offline indirme yapmaz; --eslik/--out/--dist-karsilastir/--zip-kaydet ile birlikte "
                  "kullanılamaz", file=sys.stderr)
            return 2
        # Proje kökü DIŞINDAKİ webapp (kanonik `.wt` worktree'si) da damgalanır — kapı onu kapsıyor
        # (`uygulama_coz` mutlak yolda kök segmentini arar); anahtar `tazelik_anahtari`'nin mutlak dalı,
        # store PROJE kökününki. Aksi hâlde kapı bloklar ama damga yolu olmaz = kalıcı kilit (bug gate).
        try:
            pbe = ui_eklenti_modulu()
            cozum = pbe.uygulama_coz(yerel_kok / "_", REPO) if yerel_kok.name.lower() == pbe.WEBAPP else None
        except Exception as e:   # noqa: BLE001 — eklenti yüklenemezse damga YOK (sahte-taze yok)
            print(f"[OLCULEMEDI] PULL-BEFORE-EDIT UI eklentisi yüklenemedi ({type(e).__name__}: {e}) — "
                  "damga YAZILMADI", file=sys.stderr)
            return 2
        if cozum is None:
            print(f"[KULLANIM] --damgala yalnız PULL-BEFORE-EDIT kapısının kapsadığı bir `<kök-segment>/…/<app>/webapp` "
                  f"dizini için (ref_docs/docs/.tmp/node_modules … altı değil): {yerel_kok}", file=sys.stderr)
            return 2
        app = cozum[0]
        app_bsp = bsp_name(app)
        if a.app_dir and Path(a.app_dir).resolve() != app.resolve():
            print(f"[KULLANIM] --app-dir ({a.app_dir}) ile --karsilastir ({yerel_kok}) FARKLI uygulama — "
                  "bir BSP'nin canlısıyla başka app damgalanamaz", file=sys.stderr)
            return 2
        if a.bsp and app_bsp and a.bsp.upper() != app_bsp.upper():
            print(f"[KULLANIM] --bsp {a.bsp} ama {app}/ui5-deploy.yaml BSP'si {app_bsp} — damga YAZILMAZ",
                  file=sys.stderr)
            return 2
        damga_onekler, damga_anlasilmayan = pbe.deploy_haric_desenleri(app)

    # Kapsam beyanı: koşmayan ama İSTENEN adım "İSTENMEDİ" yazılmaz (bug-gate 2026-09-26, bulgu 5).
    bekliyor = istek_durumu(True, "henüz koşmadı")
    durum = {
        "eslik": bekliyor if a.eslik else "İSTENMEDİ (--eslik yok) — geri kurmanın build-eşliği ÖLÇÜLMEDİ",
        "kars": istek_durumu(yerel_kok is not None, "henüz koşmadı"),
        "dist": istek_durumu(dist_kok is not None, "henüz koşmadı"),
        "out": istek_durumu(out is not None, "henüz koşmadı"),
        "damga": istek_durumu(a.damgala, "henüz koşmadı"),
    }
    exclude_notu = (f" · deploy exclude önekleri {damga_onekler or '[]'}"
                    + (f" · ANLAŞILMAYAN (muafiyet YOK): {damga_anlasilmayan}" if damga_anlasilmayan else ""))

    def beyan(zip_k: str, sebep: str | None = None) -> str:
        if sebep is not None:   # erken çıkış: istenip henüz koşmamış her adım bu sebeple işaretlenir
            for k in durum:
                if durum[k] == bekliyor:
                    durum[k] = istek_durumu(True, sebep)
        return kapsam_beyani(zip_k, durum["eslik"], durum["kars"], durum["dist"], durum["out"],
                             durum["damga"] + (exclude_notu if a.damgala else ""))

    def olculemedi(zip_k: str, mesaj: str) -> int:
        print(f"[OLCULEMEDI] {mesaj}", file=sys.stderr)
        print(beyan(zip_k, f"ÖLÇÜLEMEDİ: {mesaj}"))
        return 2

    if a.offline:   # yalnız --damgala ile (yukarıda denetlendi): İNDİRME YOK
        try:
            yerel_dosyalar = dizin_oku(yerel_kok)
        except OSError as e:
            return olculemedi("— (--offline: indirme YOK)", f"--karsilastir dizini okunamadı ({type(e).__name__}: {e})")
        pbe = ui_eklenti_modulu()
        rels = [r for r in sorted(yerel_dosyalar) if not pbe.deploy_haric_mi(r, damga_onekler)]
        yazilan, hata = damgala(yerel_kok, rels, a.session)
        durum["kars"] = istek_durumu(True, "--offline: canlı İNDİRİLMEDİ, karşılaştırma YOK")
        if hata:
            durum["damga"] = f"BAŞARISIZ — {hata} (yazılan {len(yazilan)})"
            print(f"[OLCULEMEDI] PBE damgası: {hata}", file=sys.stderr)
            print("\n" + beyan("— (--offline: indirme YOK)"))
            return 2
        durum["damga"] = f"OFFLINE — {len(yazilan)} dosya, canlıyla KARŞILAŞTIRILMADAN · {damga_yeri()}"
        print(f"[OFFLINE] {yerel_kok}: fetch YAPILMADI, {len(yazilan)} dosya seans-taze damgalandı "
              f"({damga_yeri()}). "
              "DİKKAT: canlıdaki belgelenmemiş değişikliği (başka makinenin deploy'u) ezme riskini kabul ettin "
              "(sap_sync_pull --offline ile aynı anlam).")
        print("\n" + beyan("— (--offline: indirme YOK)"))
        return 0

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
    # Ortam hatası (dosya G/Ç · geçersiz URL biçimi): çökme DEĞİL, ÖLÇÜLEMEDİ. Biçim hataları (JSON · base64 ·
    # zip) zip_indir/zip_coz'da KENDİ mesajıyla Olculemedi olur; AttributeError/TypeError gibi programlama
    # hataları burada BİLEREK yakalanmaz — ortam sorunu gibi görünmesin, traceback'le düşsün (re-gate R3).
    except (OSError, ValueError) as e:
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
        try:
            yerel_dosyalar = dizin_oku(yerel_kok)
        except OSError as e:   # re-gate P-1
            return olculemedi(zip_kaynagi, f"--karsilastir dizini okunamadı ({type(e).__name__}: {e})")
        satirlar = karsilastir(kaynak, yerel_dosyalar)
        if a.damgala:
            satirlar = deploy_disi_etiketle(satirlar, damga_onekler)
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
                                      for k in (AYNI, BUILD, GERCEK, YALNIZ_CANLI, YALNIZ_YEREL)
                                      + ((DEPLOY_DISI,) if a.damgala else ()))
              + f" (toplam {len(satirlar)})")
        if any(sayim.get(k) for k in (GERCEK, YALNIZ_CANLI, YALNIZ_YEREL)):
            rc = 1
        durum["kars"] = KARSILASTIRMA_TANIMI

    if dist_kok is not None:
        try:
            dist_dosyalar = dizin_oku(dist_kok)
        except OSError as e:   # re-gate P-1
            return olculemedi(zip_kaynagi, f"--dist-karsilastir dizini okunamadı ({type(e).__name__}: {e})")
        yalniz_c, yalniz_d, degisen, esit = liste_kiyasla(canli, dist_dosyalar)
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

    if a.damgala:
        engel = damga_engeli(satirlar, zip_taze=not a.zip, sapma=sapma, rc=rc)
        if engel:
            durum["damga"] = f"YAPILMADI — {engel}"
            print(f"\n=== PBE DAMGASI: YAPILMADI — {engel} ===\n"
                  "  → kapı bu webapp'in dosyalarını bloklamaya devam eder. Fark varsa: canlıyı anlık görüntüle "
                  "(`--zip-kaydet`), `--zip <snap> --out <scratch>/webapp` ile geri kur, otoriteyi KULLANICI seçer, "
                  "seçerek kopyala, sonra bu komutu yeniden koş (playbook howto-ui-kaynagi-geri-kurma §2.1).")
            rc = max(rc, 1)
        else:
            rels = [r for r, s, _, _ in satirlar if s in (AYNI, BUILD)]
            yazilan, hata = damgala(yerel_kok, rels, a.session)
            if hata:
                durum["damga"] = f"BAŞARISIZ — {hata} (yazılan {len(yazilan)})"
                print(f"\n[OLCULEMEDI] PBE damgası: {hata}", file=sys.stderr)
                rc = 2
            else:
                durum["damga"] = f"YAZILDI — {len(yazilan)} dosya (canlıyla eşit ölçülenler) · {damga_yeri()}"
                print(f"\n=== PBE DAMGASI: {len(yazilan)} dosya seans-taze damgalandı ({yerel_kok}) ===\n"
                      f"  {damga_yeri()}")

    print("\n" + beyan(zip_kaynagi))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

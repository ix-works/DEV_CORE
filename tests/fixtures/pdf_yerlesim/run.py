#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf_yerlesim — `html_to_pdf.js` yol kodlaması + dizin listesi dedektörü + yalnız-PDF yerleşim
düzeltmesi (DEV_CORE Issue #389, 2026-11-07).

VAKA (f646f36'da ölçüldü): ① klasör adında `#` olan belge (`src/#NS#ZSD001/`) `PDF OK` ile
üst klasörün DİZİN LİSTESİNİ basıyordu · ② başlık satırı olmayan geniş görsel sayfadan taşıp
BÜTÜN belgeyi küçültüyordu (gövde 10,5 → 7,0 pt) · ③ geniş `pre` kırpılıyordu (190 karakterin
105'i) · ④ tablo hücresindeki bölünmeyen satır içi kod tabloyu taşırıp belgeyi küçültüyordu.

TABAN = `_taban_html_to_pdf.js` (f646f36 sürümünün birebir kopyası; sığ klonda `git show` yok ⇒
kardeş dosya). Her kusur vektörü önce TABANDA kusurun gerçekten oluştuğunu ölçer ("yer gerçeği";
tutmazsa vektör FAIL — Chromium davranışı değişmiştir, aracın çıktısı tek başına kanıt değil).
Belgeler SENTETİKTİR (koşumda üretilir); ölçüm PDF'in kendisinden (PyMuPDF).

Üretim GERÇEK giriş noktasından: `build_doc_pdf.py` / `build_kd_pdf.py` + (mutasyonlu olabilen)
`html_to_pdf.js` kum `scripts/` dizinine kopyalanır; `build_doc_pdf.py --pdf` komşu js'i bulur.

SENARYOLAR
  S1  kaynakta `url.pathToFileURL(IN)` var, `"file:///" + IN` birleştirmesi YOK (statik) [--mutasyon-url]
  S2  PDF_CSS'te işaretsiz tablo hücresi `overflow-wrap:anywhere` YOK (statik)      [--mutasyon-tablo-global]
  S3  page.pdf seçenek literali tabanla AYNI (statik; Q366)
  Y1  `#`'lı klasör, `build_doc_pdf.py --pdf` (gerçek giriş) → rc 0, PDF OK, gövde işareti PDF'te,
      başlık meta = "/NS/ZSD001 Deneme", sayfa sayısı = kontrol (Y1k). Yer gerçeği: taban PDF'inde
      işaret YOK ve başlık "Index of"                                               [--mutasyon-url]
  Y1k kontrol: aynı belge `#`'sız klasörde (taban da doğru basar)
  Y2  girdi bir DİZİN → rc 2, "PDF FAIL" + "DIZIN LISTESI", PDF yazılmaz. Yer gerçeği: taban rc 0
                                                                                  [--mutasyon-dizin]
  Y2k FP kontrol: `<title>Index of …</title>` taşıyan GERÇEK belge → rc 0, PDF OK
  Y3  başlıksız 2400 px görsel → görsel sağ kenarı ≤ sayfa − sağ boşluk, gövde 10,5 pt.
      Yer gerçeği: taban gövde < 10,5 pt                                            [--mutasyon-img]
  Y3k kontrol: başlıklı (figure) aynı görsel → tabanda da sığar
  Y4  190 karakterlik `pre` satırı → karakterlerin TAMAMI PDF metninde, kırpık 0.
      Yer gerçeği: tabanda eksik karakter var                                       [--mutasyon-pre]
  Y5  tablo hücresinde 120 karakterlik satır içi `code` → gövde 10,5 pt, kod metni tam,
      beyan "kod 1, tum hucre 0". Yer gerçeği: taban gövde < 10,5     [--mutasyon-tablo-kod]
  Y5b tablo hücresinde boşluksuz 150 harflik sözcük (kod değil) → 2. kademe ("tum hucre 1"),
      gövde 10,5 pt. Yer gerçeği: taban gövde < 10,5                                [--mutasyon-tablo-hucre]
  Y5k kontrol: SIĞAN tablo (40 karakterlik kod + uzun düzyazı) → beyan "kod 0" + sayfa sayfa
      metin TABANLA AYNI (global `anywhere` sütun dağılımını değiştirirdi)           [--mutasyon-tablo-global]
  Y6  paragraf içinde boşluksuz 220 karakterlik dizi → gövde 10,5 pt, kalan taşma 0.
      Yer gerçeği: taban gövde < 10,5                                               [--mutasyon-govde]
  Y7  düzeltilemeyen 2000 px `div` → rc 0, `PDF UYARILI`, stderr "UYARI YERLESIM", `PDF OK` YOK,
      beyan "kalan tasan 1 (div 1)"                                                 [--mutasyon-uyari]
  Y7b 695 px `div` (JS margin genişliği 703 px'e SIĞAR, belgenin `@page` 14 mm'lik genişliği 688 px'e
      SIĞMAZ) → UYARI. Yer gerçeği: taban gövde < 10,5 (Chromium gerçekten küçültüyor)
                                                                                  [--mutasyon-genislik]
  Y7c satır içi `white-space:pre;overflow-x:auto` ile düzeltmeyi EZEN `pre` → UYARI + "kirpik 1"
                                                                                  [--mutasyon-kirpik]
  Y8  3. BAĞLAM — `build_kd_pdf.py` (eski KD üreticisi, ayrı CSS) başlıksız geniş görsel + 190
      karakterlik `pre` → görsel sığar, gövde 10,5, karakterler tam. Yer gerçeği: taban gövde < 10,5
                                                                         [--mutasyon-img, --mutasyon-pre]
Y*/S3 dışı satırlar node + playwright-core + msedge + markdown + PIL + PyMuPDF ister; biri yoksa
ATLANDI basılır (CI bu bağımlılıkları KURMAZ — ölçülmemiş satır PASS sayılmaz).
KAPSAM DIŞI: `--sayfa-no`/`--yer-imi` (pdf_sayfa_no_yer_imi), mermaid render.

Koşum:  python tests/fixtures/pdf_yerlesim/run.py [--mutasyon-<kip>]
"""
import collections
import concurrent.futures
import importlib.util
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

if sys.platform == "win32":
    for _a in (sys.stdout, sys.stderr):
        try:
            _a.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
SCRIPTS = KOK / "scripts"
JS = SCRIPTS / "html_to_pdf.js"
TABAN_JS = Path(__file__).resolve().parent / "_taban_html_to_pdf.js"

MUTASYON = {
    "--mutasyon-url": ("  const fileUrl = dosyaUrl(IN);",
                       '  const fileUrl = "file:///" + IN.split(path.sep).join("/");'),
    # localhost UNC düzeltmesini söker (2458c17 davranışı) → U1 (+ Y15 koşulabiliyorsa)
    "--mutasyon-unc": ('yol.replace(LOCALHOST_UNC_RE, (m, onek) => onek + "127.0.0.1")', "yol"),
    "--mutasyon-dizin": ("  if (dz.liste) {", "  if (false) {"),
    # tablo dışı taşan görsel kuralı yok → Y3 + Y8 + Y12
    "--mutasyon-img": ('  "img[data-ix-pdf-sar]," +', '  "" +'),
    # 2458c17'nin GLOBAL img kuralı (+height:auto) → sığan tablo (Y9) + oranı bozuk sığan görsel (Y11) + S2
    "--mutasyon-img-global": ('  "img[data-ix-pdf-sar]," +', '  "img," +'),
    # height:auto yok (F3) → w/h öznitelikli geniş görselin oranı bozulur: Y12 + Y14
    "--mutasyon-img-oran": ("img{max-width:100%;height:auto}", "img{max-width:100%}"),
    # tablo dışı taşan/kırpık pre kuralı yok → Y4 (+ pre taşıyan Y1/Y1k/Y8/Y16)
    "--mutasyon-pre": ('  "pre[data-ix-pdf-sar]," +', '  "" +'),
    # 2458c17'nin GLOBAL pre kuralı → sığan tablo hücresindeki pre (Y10) + S2
    "--mutasyon-pre-global": ('  "pre[data-ix-pdf-sar]," +', '  "pre," +'),
    # öğe işareti hiç konmaz → tablo dışı görsel/pre düzeltmesi düşer
    "--mutasyon-isaret": ("        if (tasar || (!gorsel && kirpik(e))) {", "        if (false) {"),
    # yalnız kırpık (sayfaya taşmayan) pre işaretlenmez → Y16
    "--mutasyon-pre-kirpik": ("if (tasar || (!gorsel && kirpik(e))) {", "if (tasar) {"),
    # hücre içi görsel/pre de öğe bazında işaretlenir (kademe atlanır) → Y13 + Y14 beyanı
    "--mutasyon-isaret-hucre": ('.filter(e => !e.closest("td,th"));', ".filter(e => true);"),
    "--mutasyon-govde": ('  "body{overflow-wrap:break-word}" +', '  "" +'),
    "--mutasyon-tablo-kod": ('  "table[data-ix-pdf-sar] :is(td,th) code{overflow-wrap:anywhere}" +', '  "" +'),
    # taşan tablonun 1. kademesinde hücre içi pre sarılmaz → Y13
    "--mutasyon-tablo-pre": ('"table[data-ix-pdf-sar] :is(td,th) pre{', '"pre[data-ix-pdf-sar]{'),
    # taşan tablonun 2. kademesinde hücre içi görsel sığdırılmaz → Y14
    "--mutasyon-tablo-gorsel": (r'"table:is([data-ix-pdf-sar=\"2\"],[data-ix-pdf-sar=\"3\"]) :is(td,th) img{',
                                '"img[data-ix-pdf-sar]{'),
    "--mutasyon-tablo-hucre": (r'  "table[data-ix-pdf-sar=\"3\"] :is(td,th){overflow-wrap:anywhere}";', '  "";'),
    # işaretli tablo yerine HER tablo hücresindeki koda anywhere (reddedilen tasarım) → Y5k + S2
    "--mutasyon-tablo-global": ('  "table[data-ix-pdf-sar] :is(td,th) code{overflow-wrap:anywhere}" +',
                                '  ":is(td,th) code{overflow-wrap:anywhere}" +'),
    "--mutasyon-uyari": ("  const yerlesimUyari = y.tasanN + y.kirpikN;", "  const yerlesimUyari = 0;"),
    # belgenin @page yan boşluğunu yok sayar (yalnız JS margin) → Y7b
    "--mutasyon-genislik": ("          if (a + c > yan) {", "          if (false) {"),
    "--mutasyon-kirpik": ("    const ta = tasanlar(), ki = kirpiklar();", "    const ta = tasanlar(), ki = [];"),
}
GECERLI_KIP = set(MUTASYON)
KIP = None
for _a in sys.argv[1:]:
    if _a not in GECERLI_KIP:
        print(f"[KULLANIM] bilinmeyen kip: {_a}  (gecerli: {' '.join(sorted(GECERLI_KIP))})")
        sys.exit(2)
    KIP = _a

SONUC, ATLANAN = [], []


def kontrol(ad, ok, detay=""):
    SONUC.append((ad, bool(ok), detay))


def atla(ad, sebep):
    ATLANAN.append((ad, sebep))


def kos(komut, zaman=180, cwd=None):
    p = subprocess.run(komut, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=zaman, cwd=cwd)
    return p.returncode, p.stdout or "", p.stderr or ""


# ── kaynak (mutasyon uygulanmış) ─────────────────────────────────────────────
src = JS.read_text(encoding="utf-8")
if KIP:
    eski, yeni = MUTASYON[KIP]
    if src.count(eski) != 1:
        print(f"[DURDU] mutasyon çapası bulunamadı/çoğul ({KIP}): {eski!r} -> {src.count(eski)}")
        sys.exit(3)
    src = src.replace(eski, yeni)
taban_src = TABAN_JS.read_text(encoding="utf-8")

# ── S: statik (bağımlılıksız) ────────────────────────────────────────────────
kontrol("S1 fileUrl = dosyaUrl(IN) (url.pathToFileURL), \"file:///\" + IN atamasi yok",
        "const fileUrl = dosyaUrl(IN);" in src and "url.pathToFileURL(" in src
        and not re.search(r'=\s*"file:///"\s*\+', src))
_css = re.search(r"const PDF_CSS =(.*?);\n", src, re.S)
_css_t = _css.group(1) if _css else ""
_css_metin = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', _css_t)).replace('\\"', '"')
_kural = re.findall(r"([^{}]+)\{([^}]*)\}", _css_metin)


def _secici_bol(liste):
    """Seçici listesini parantez DIŞINDAKİ virgülden böler (`:is(td,th)` tek parça kalır)."""
    parca, d, cur = [], 0, ""
    for ch in liste:
        d += (ch == "(") - (ch == ")")
        if ch == "," and d == 0:
            parca.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return parca + [cur.strip()]


_secici = [s for sec, _ in _kural for s in _secici_bol(sec)]
_isaretsiz = [s for s in _secici if s != "body" and "data-ix-pdf-sar" not in s]
# F1 (bug-gate): global img/pre/tablo kuralı SIĞAN tabloyu değiştirir ⇒ body dışı HER seçici işarete bağlı
kontrol("S2 PDF_CSS'te body dışı her seçici data-ix-pdf-sar işaretine bağlı (global img/pre/tablo kuralı YOK)",
        bool(_kural) and not _isaretsiz, f"secici={len(_secici)} isaretsiz={_isaretsiz}")
OPTS_RE = re.compile(r'\{ path: OUT, format: "A4", printBackground: true, margin: \{[^}]*\} \}')
kontrol("S3 page.pdf seçenek literali tabanla AYNI (Q366)",
        len(OPTS_RE.findall(src)) == 1 and OPTS_RE.findall(src) == OPTS_RE.findall(taban_src))

# ── U1: `dosyaUrl` birim (F4) — kaynaktan çıkarılan fonksiyon node'da koşulur (tarayıcısız) ──
# Windows yol anlamı gerekir (pathToFileURL platforma bağlı) ⇒ win32 dışında ATLANDI.
UNC_VAKA = [   # (girdi, beklenen href)
    ("\\\\localhost\\C$\\a #1\\b.html", "file://127.0.0.1/C$/a%20%231/b.html"),
    ("\\\\LocalHost\\paylasim\\b.html", "file://127.0.0.1/paylasim/b.html"),
    ("\\\\?\\UNC\\localhost\\C$\\b.html", "file://127.0.0.1/C$/b.html"),
    ("\\\\127.0.0.1\\C$\\a\\b.html", "file://127.0.0.1/C$/a/b.html"),      # kontrol: değişmez
    ("\\\\srv\\paylasim\\b.html", "file://srv/paylasim/b.html"),           # kontrol: başka host
    ("\\\\localhostx\\s\\b.html", "file://localhostx/s/b.html"),           # kontrol: önek değil host
    ("\\\\?\\C:\\x\\b.html", "file:///C:/x/b.html"),                        # kontrol: uzun yerel yol
    ("C:\\x\\#NS#ZSD001\\b.html", "file:///C:/x/%23NS%23ZSD001/b.html"),    # kontrol: '#'
]
_fn = re.search(r"^const LOCALHOST_UNC_RE = .*?^}\n", src, re.S | re.M)
if sys.platform != "win32" or not shutil.which("node"):
    atla("U1", "Windows + node gerekir (pathToFileURL Windows yol anlamı)")
elif not _fn:
    kontrol("U1 dosyaUrl kaynakta bulundu", False, "LOCALHOST_UNC_RE/dosyaUrl tanımı yok")
else:
    _u = Path(tempfile.mkdtemp(prefix="i389u_")) / "u.js"
    _u.write_text('const url = require("url");\n' + _fn.group(0) +
                  "const V = JSON.parse(process.argv[2]);\n"
                  "console.log(JSON.stringify(V.map(v => dosyaUrl(v))));\n", encoding="utf-8")
    import json as _json
    _r = subprocess.run(["node", str(_u), _json.dumps([v for v, _ in UNC_VAKA])],
                        capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        _cik = _json.loads(_r.stdout)
    except ValueError:
        _cik = None
    _fark = [(v, b, c) for (v, b), c in zip(UNC_VAKA, _cik or [])] if _cik else []
    _fark = [x for x in _fark if x[1] != x[2]]
    kontrol("U1 dosyaUrl: \\\\localhost UNC → 127.0.0.1 host; başka host/yerel yol değişmez (8 vaka)",
            _r.returncode == 0 and _cik is not None and len(_cik) == len(UNC_VAKA) and not _fark,
            f"rc={_r.returncode} fark={_fark} {(_r.stderr or '')[:200]!r}")
    shutil.rmtree(_u.parent, ignore_errors=True)


def bagimlilik():
    eksik = [m for m in ("markdown", "fitz", "PIL") if importlib.util.find_spec(m) is None]
    if not shutil.which("node"):
        return eksik + ["node"]
    r, o, e = kos(["node", "-e", "const p=require('path'),fs=require('fs'),os=require('os');"
                   "const s='npm/node_modules/@playwright/cli/node_modules/playwright-core';"
                   "const c=[process.env.APPDATA&&path.join(process.env.APPDATA,s),"
                   "path.join(os.homedir(),'AppData/Roaming',s)].filter(Boolean).find(x=>fs.existsSync(x))"
                   "||'playwright-core';const {chromium}=require(c);"
                   "chromium.launch({channel:'msedge',headless:true}).then(b=>b.close()).then(()=>console.log('OK'))"
                   ".catch(e=>{console.log('YOK '+e.message.split('\\n')[0]);process.exit(1)})"], 90)
    if r != 0:
        eksik.append("playwright/msedge (%s)" % (o + e).strip()[:80])
    return eksik


def png(yol, w, h):
    """Bağımlılıksız düz renkli PNG."""
    satir = b"\x00" + b"\x5a\x8a\xc0" * w
    ham = zlib.compress(satir * h, 9)

    def parca(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    yol.write_bytes(b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                    + parca(b"IDAT", ham) + parca(b"IEND", b""))


PARAGRAF = ("Bu paragraf gövde puntosunu ölçmek için yeterince uzun bir düzyazıdır; çğıöşü ÇĞİÖŞÜ. " * 6).strip()
PRE_SATIR = "".join(chr(ord("A") + (i % 26)) for i in range(190))          # 190 karakter, boşluksuz
TABLO_KOD = "ZSD001_CL_ORNEK=>" + "UZUN_METOT_ADI_" * 7                      # 122 karakter
SOZCUK = "uzunsozcuk" * 15                                                    # 150 harf, boşluksuz
DIZI = "https://ornek.invalid/" + "yol" * 66                                  # 220 karakter
TABLO_PRE = "SELECT * FROM ZSD001_T_ORNEK WHERE X = 1"                          # sığan hücre pre'si (CE5)
PRE_KISA = "".join(chr(ord("a") + (i % 26)) for i in range(80))                # 300 px kutuda kırpık, sayfaya sığar


def govde(*ek):
    L = ["# Yerleşim Deneme Belgesi", "", "IX389-GOVDE-ISARETI", "", PARAGRAF, ""]
    for e in ek:
        L += [e, ""]
    L += [PARAGRAF, "", PARAGRAF, ""]
    return "\n".join(L) + "\n"


BELGELER = {
    # ad: (alt dizin, md, ek dosya üretici)
    "Y1": ("src/#NS#ZSD001", govde("```", PRE_SATIR, "```"), None),
    "Y1k": ("duz/NSZSD001", govde("```", PRE_SATIR, "```"), None),
    "Y2k": ("indexbaslik", govde(), None),
    "Y3": ("y3", govde("![genis](screenshots/genis.png)", "Görselden sonraki paragraf."), "genis"),
    "Y3k": ("y3k", govde("![genis](screenshots/genis.png)", "*Şekil 1 — Başlıklı görsel*"), "genis"),
    "Y4": ("y4", govde("```", PRE_SATIR, "```"), None),
    "Y5": ("y5", govde("| Alan | Açıklama | Değer |\n|---|---|---|\n| A1 | `%s` | 7 |\n| A2 | kısa | 8 |" % TABLO_KOD), None),
    "Y5b": ("y5b", govde("| Alan | Açıklama | Değer |\n|---|---|---|\n| A1 | %s | 7 |\n| A2 | kısa | 8 |" % SOZCUK), None),
    "Y5k": ("y5k", govde("| Sınıf | Açıklama | Değer |\n|---|---|---|\n"
                         + "\n".join("| `ZSD001_CL_ORNEK_SINIF_ADI_%02d` | %s | %d |" % (i, PARAGRAF[:160 + i * 9], i)
                                     for i in range(1, 7))), None),
    "Y6": ("y6", govde("Bağlantı: %s sonu." % DIZI), None),
    "Y7": ("y7", govde('<div style="width:2000px;height:20px;background:#ccc">GENIS-KUTU</div>'), None),
    "Y7b": ("y7b", govde('<div style="width:695px;height:20px;background:#ccc">ORTA-KUTU</div>'), None),
    "Y7c": ("y7c", govde('<pre style="white-space:pre;overflow-x:auto">%s</pre>' % PRE_SATIR), None),
    # ── bug-gate F1/F3 (2026-11-07): sığan tabloya / sığan görsele DOKUNULMAZ; taşan tablonun hücre içi
    #    görsel/pre'si kademeyle sarılır; w/h öznitelikli geniş görselin oranı korunur ──
    "Y9": ("y9", govde("| Simge | Açıklama | Not |\n|---|---|---|\n| ![i](screenshots/ikon.png) | %s | %s |"
                       % (PARAGRAF[:300], PARAGRAF[:300])), "ikon"),
    "Y10": ("y10", govde("<table><tr><td><pre>%s</pre></td><td>%s %s</td></tr></table>" % (TABLO_PRE, PARAGRAF, PARAGRAF)),
            None),
    "Y11": ("y11", govde('<p><img src="screenshots/ikon.png" width="260" height="240"></p>'), "ikon"),
    "Y12": ("y12", govde('<p><img src="screenshots/genis12.png" width="1200" height="300"></p>'), "genis12"),
    "Y13": ("y13", govde("<table><tr><td><pre>%s</pre></td><td>kısa açıklama</td></tr></table>" % PRE_SATIR), None),
    "Y14": ("y14", govde('<table><tr><td><img src="screenshots/genis12.png" width="1200" height="300"></td>'
                         "<td>kısa açıklama</td></tr></table>"), "genis12"),
    "Y16": ("y16", govde('<div style="width:300px"><pre>%s</pre></div>' % PRE_KISA), None),
}
GORSEL = {"genis": [("genis.png", 2400, 160)], "ikon": [("ikon.png", 260, 120)],
          "genis12": [("genis12.png", 1200, 300)]}
BASLIK = {"Y1": "/NS/ZSD001 Deneme", "Y1k": "/NS/ZSD001 Deneme", "Y2k": "Index of C:\\gercek\\belge\\"}


def punto(pdf):
    import fitz
    c = collections.Counter()
    for pg in fitz.open(pdf):
        for b in pg.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for s in ln["spans"]:
                    c[round(s["size"], 1)] += len(s["text"].strip())
    return c.most_common(1)[0][0] if c else None


def gorsel_x1(pdf):
    import fitz
    d = fitz.open(pdf)
    return max([im["bbox"][2] for pg in d for im in pg.get_image_info()] or [0]), d[0].rect.width


def gorsel_kutulari(pdf, w, h):
    """Özgün boyutu w×h olan görselin PDF'teki kutuları (gölge/zemin bitmap'leri boyutundan ayrılır)."""
    import fitz
    d = fitz.open(pdf)
    k = []
    for pg in d:
        for im in pg.get_images(full=True):
            if im[2] == w and im[3] == h:
                k += [tuple(round(v, 1) for v in r) for r in pg.get_image_rects(im[0])]
    return k, d[0].rect.width


def oran(kutu):
    return (kutu[2] - kutu[0]) / (kutu[3] - kutu[1]) if kutu[3] > kutu[1] else None


def metin(pdf, bosluksuz=True):
    import fitz
    t = "".join(pg.get_text() for pg in fitz.open(pdf))
    return re.sub(r"\s+", "", t) if bosluksuz else t


def sayfa_metinleri(pdf):
    import fitz
    return ["\n".join(s.rstrip() for s in pg.get_text().splitlines() if s.strip()) for pg in fitz.open(pdf)]


def meta(pdf):
    import fitz
    d = fitz.open(pdf)
    return d.page_count, (d.metadata or {}).get("title")


KADEME_RE = r"kod/pre (\d+), gorsel (\d+), tum hucre (\d+)"
ISARET_RE = r"tasan gorsel (\d+), tasan/kirpik pre (\d+)"


def beyan(cikti, desen):
    m = re.search(desen, cikti)
    return m.groups() if m else None


Y_ADLAR = ["Y1", "Y1k", "Y2", "Y2k", "Y3", "Y3k", "Y4", "Y5", "Y5b", "Y5k", "Y6", "Y7", "Y7b", "Y7c", "Y8",
           "Y9", "Y10", "Y11", "Y12", "Y13", "Y14", "Y15", "Y16"]
eksik = bagimlilik()
if eksik:
    for a in Y_ADLAR:
        atla(a, "bağımlılık yok: " + ", ".join(eksik))
else:
    kum = Path(tempfile.mkdtemp(prefix="i389_"))
    ks = kum / "scripts"
    ks.mkdir()
    for f in ("build_doc_pdf.py", "build_kd_pdf.py", "doc_tools.py"):
        shutil.copy2(SCRIPTS / f, ks / f)
    (ks / "html_to_pdf.js").write_text(src, encoding="utf-8")
    yeni_js, taban_js = ks / "html_to_pdf.js", ks / "_taban.js"
    taban_js.write_text(taban_src, encoding="utf-8")
    BUILD, BUILD_KD = ks / "build_doc_pdf.py", ks / "build_kd_pdf.py"

    html = {}
    for ad, (alt, md, ek) in BELGELER.items():
        d = kum / alt
        (d / "screenshots").mkdir(parents=True, exist_ok=True)
        for _ad, _w, _h in GORSEL.get(ek, []):
            png(d / "screenshots" / _ad, _w, _h)
        (d / "belge.md").write_text(md, encoding="utf-8")
        html[ad] = d / "belge.html"
        if ad in ("Y1", "Y1k"):
            continue   # gerçek giriş noktası: aşağıda build_doc_pdf --pdf
        r, o, e = kos([sys.executable, str(BUILD), str(d / "belge.md"), str(html[ad]), BASLIK.get(ad, "Deneme")])
        if r != 0:
            print(f"[DURDU] HTML üretilemedi {ad} rc={r}: {(o + e)[:300]}")
            sys.exit(3)
    # Y8: eski KD üreticisi (ayrı CSS) — 3. bağlam
    d8 = kum / "kd"
    (d8 / "screenshots").mkdir(parents=True)
    png(d8 / "screenshots" / "genis.png", 2400, 160)
    (d8 / "KD-SD-001_Ornek.md").write_text(govde("![genis](screenshots/genis.png)", "Sonraki paragraf.",
                                                 "```", PRE_SATIR, "```"), encoding="utf-8")
    html["Y8"] = d8 / "KD-SD-001_Ornek.html"
    r, o, e = kos([sys.executable, str(BUILD_KD), str(d8 / "KD-SD-001_Ornek.md"), str(html["Y8"])])
    if r != 0 or not html["Y8"].exists():
        print(f"[DURDU] KD HTML üretilemedi rc={r}: {(o + e)[:300]}")
        sys.exit(3)

    def uret(is_):
        ad, js, girdi, cikti = is_
        return (ad, js), kos(["node", str(js), str(girdi), str(cikti)])

    isler = []
    for ad, h in html.items():
        if ad in ("Y1", "Y1k"):
            continue
        isler.append((ad, yeni_js, h, h.with_name(h.stem + ".yeni.pdf")))
        isler.append((ad, taban_js, h, h.with_name(h.stem + ".taban.pdf")))
    isler.append(("Y2", yeni_js, kum / "y3", kum / "dizin.yeni.pdf"))
    isler.append(("Y2", taban_js, kum / "y3", kum / "dizin.taban.pdf"))
    # Y15 (F4): aynı belge `\\localhost\<sürücü>$\…` yönetim paylaşımından. Paylaşım erişilemiyorsa ATLANDI.
    _y4 = str(html["Y4"].resolve())
    unc15 = ("\\\\localhost\\" + _y4[0] + "$" + _y4[2:]) if sys.platform == "win32" and _y4[1:2] == ":" else None
    unc15_var = bool(unc15) and Path(unc15).exists()
    if unc15_var:
        isler.append(("Y15", yeni_js, unc15, kum / "unc.yeni.pdf"))
        isler.append(("Y15", taban_js, unc15, kum / "unc.taban.pdf"))
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        S = dict(ex.map(uret, isler))
    # Y1/Y1k gerçek giriş noktası (build_doc_pdf.py --pdf → komşu html_to_pdf.js); taban ayrıca
    Y1 = {}
    for ad in ("Y1", "Y1k"):
        alt = kum / BELGELER[ad][0]
        Y1[ad] = kos([sys.executable, str(BUILD), str(alt / "belge.md"), str(html[ad]), BASLIK[ad], "--pdf"])
        S[(ad, taban_js)] = kos(["node", str(taban_js), str(html[ad]), str(alt / "belge.taban.pdf")])

    def P(ad, tur):
        h = html[ad]
        return h.with_name(h.stem + "." + tur + ".pdf")

    # ── Y1 / Y1k ──
    r, o, e = Y1["Y1"]
    pdf1 = html["Y1"].with_suffix(".pdf")
    rk, ok_, ek_ = Y1["Y1k"]
    pdf1k = html["Y1k"].with_suffix(".pdf")
    yg1 = (pdf1.with_name("belge.taban.pdf").exists()
           and "IX389-GOVDE-ISARETI" not in metin(pdf1.with_name("belge.taban.pdf"))
           and str(meta(pdf1.with_name("belge.taban.pdf"))[1]).startswith("Index of"))
    ok = (r == 0 and "PDF OK" in o and pdf1.exists() and "IX389-GOVDE-ISARETI" in metin(pdf1)
          and meta(pdf1)[1] == "/NS/ZSD001 Deneme" and pdf1k.exists() and meta(pdf1)[0] == meta(pdf1k)[0])
    kontrol("Y1 '#'lı klasör (build_doc_pdf --pdf) → doğru PDF + yer gerçeği (taban dizin listesi)", ok and yg1,
            f"rc={r} yer_gercegi={yg1} meta={meta(pdf1) if pdf1.exists() else None} {(o + e)[-240:]!r}")
    kontrol("Y1k kontrol: '#'sız klasör → PDF OK, taban da işareti basar",
            rk == 0 and "PDF OK" in ok_ and "IX389-GOVDE-ISARETI" in metin(pdf1k)
            and "IX389-GOVDE-ISARETI" in metin(pdf1k.with_name("belge.taban.pdf")), f"rc={rk} {(ok_ + ek_)[-200:]!r}")

    # ── Y2 / Y2k ──
    (r, o, e), (rt, ot, et) = S[("Y2", yeni_js)], S[("Y2", taban_js)]
    kontrol("Y2 girdi dizin → rc 2 'PDF FAIL' + 'DIZIN LISTESI', PDF yok; yer gerçeği: taban rc 0",
            r == 2 and "PDF FAIL" in e and "DIZIN LISTESI" in e and not (kum / "dizin.yeni.pdf").exists() and rt == 0,
            f"rc={r} taban_rc={rt} {(o + e)[:240]!r}")
    r, o, e = S[("Y2k", yeni_js)]
    kontrol("Y2k FP kontrol: 'Index of' başlıklı gerçek belge → rc 0 PDF OK",
            r == 0 and "PDF OK" in o and "IX389-GOVDE-ISARETI" in metin(P("Y2k", "yeni")), f"rc={r} {(o + e)[:240]!r}")

    def sigar(pdf):
        # Ölçüt = görsel SAYFA içinde. Sağ boşluk ölçüt DEĞİL: Skia `box-shadow`'u ayrı bir görüntü olarak
        # yazar ve o, içerik kutusunun ~9 pt dışına taşar (ölçüldü: görsel 555.0, gölge 565.2, sayfa 595.9).
        x1, w = gorsel_x1(pdf)
        return x1 <= w, round(x1, 1)

    # ── Y3 / Y3k ──
    r, o, e = S[("Y3", yeni_js)]
    s, x1 = sigar(P("Y3", "yeni"))
    pt_t = punto(P("Y3", "taban"))
    kontrol("Y3 başlıksız geniş görsel → işaret 'tasan gorsel 1', sığar + gövde 10,5; yer gerçeği taban küçültür",
            r == 0 and "PDF OK" in o and s and punto(P("Y3", "yeni")) == 10.5 and pt_t is not None and pt_t < 10.5
            and beyan(o, ISARET_RE) == ("1", "0"),
            f"rc={r} x1={x1} punto={punto(P('Y3', 'yeni'))} taban_punto={pt_t} isaret={beyan(o, ISARET_RE)} "
            f"{(o + e)[-200:]!r}")
    r, o, e = S[("Y3k", yeni_js)]
    kontrol("Y3k kontrol: başlıklı görsel → yeni ve taban sığar, 10,5",
            r == 0 and "PDF OK" in o and sigar(P("Y3k", "yeni"))[0] and sigar(P("Y3k", "taban"))[0]
            and punto(P("Y3k", "yeni")) == 10.5 == punto(P("Y3k", "taban")),
            f"rc={r} x1={sigar(P('Y3k', 'yeni'))}/{sigar(P('Y3k', 'taban'))} punto={punto(P('Y3k', 'yeni'))}/"
            f"{punto(P('Y3k', 'taban'))} {(o + e)[-200:]!r}")

    # ── Y4 ──
    r, o, e = S[("Y4", yeni_js)]
    kontrol("Y4 190 karakterlik pre → işaret 'pre 1', karakterler TAM, kırpık 0; yer gerçeği taban eksik",
            r == 0 and "PDF OK" in o and PRE_SATIR in metin(P("Y4", "yeni")) and PRE_SATIR not in metin(P("Y4", "taban"))
            and beyan(o, r"kalan tasan 0, kirpik 0") is not None and beyan(o, ISARET_RE) == ("0", "1"),
            f"rc={r} {(o + e)[-260:]!r}")

    # ── Y5 / Y5b / Y5k ──
    r, o, e = S[("Y5", yeni_js)]
    pt_t = punto(P("Y5", "taban"))
    kontrol("Y5 tablo hücresinde uzun satır içi kod → 1. kademe (kod/pre 1, gorsel 0, tum hucre 0), 10,5, kod tam; "
            "taban küçültür",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("1", "0", "0")
            and punto(P("Y5", "yeni")) == 10.5 and TABLO_KOD in metin(P("Y5", "yeni")) and pt_t is not None and pt_t < 10.5,
            f"rc={r} beyan={beyan(o, KADEME_RE)} punto={punto(P('Y5', 'yeni'))} taban={pt_t} {(o + e)[-200:]!r}")
    r, o, e = S[("Y5b", yeni_js)]
    pt_t = punto(P("Y5b", "taban"))
    kontrol("Y5b hücrede boşluksuz uzun sözcük → 3. kademe (1, 1, tum hucre 1), 10,5; taban küçültür",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("1", "1", "1")
            and punto(P("Y5b", "yeni")) == 10.5 and pt_t is not None and pt_t < 10.5,
            f"rc={r} beyan={beyan(o, KADEME_RE)} punto={punto(P('Y5b', 'yeni'))} taban={pt_t}")
    r, o, e = S[("Y5k", yeni_js)]
    kontrol("Y5k kontrol: SIĞAN tablo → kod 0 + sayfa sayfa metin TABANLA AYNI",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("0", "0", "0")
            and sayfa_metinleri(P("Y5k", "yeni")) == sayfa_metinleri(P("Y5k", "taban")),
            f"rc={r} beyan={beyan(o, KADEME_RE)} esit="
            f"{sayfa_metinleri(P('Y5k', 'yeni')) == sayfa_metinleri(P('Y5k', 'taban'))}")

    # ── Y6 ──
    r, o, e = S[("Y6", yeni_js)]
    pt_t = punto(P("Y6", "taban"))
    kontrol("Y6 paragrafta boşluksuz 220 karakter → 10,5, kalan taşma 0; taban küçültür",
            r == 0 and "PDF OK" in o and punto(P("Y6", "yeni")) == 10.5 and pt_t is not None and pt_t < 10.5
            and DIZI in metin(P("Y6", "yeni")), f"rc={r} punto={punto(P('Y6', 'yeni'))} taban={pt_t} {(o + e)[-200:]!r}")

    # ── Y7 / Y7b / Y7c ──
    r, o, e = S[("Y7", yeni_js)]
    kontrol("Y7 düzeltilemeyen 2000 px div → PDF UYARILI + stderr UYARI, 'PDF OK' yok, 'kalan tasan 1 (div 1)'",
            r == 0 and "PDF UYARILI" in o and "PDF OK" not in o and "UYARI YERLESIM" in e
            and "kalan tasan 1 (div 1)" in o and P("Y7", "yeni").exists(), f"rc={r} {(o + e)[-300:]!r}")
    r, o, e = S[("Y7b", yeni_js)]
    pt_t = punto(P("Y7b", "taban"))
    kontrol("Y7b 695 px div (@page 14 mm genişliğine sığmaz) → UYARI; yer gerçeği taban küçültür",
            r == 0 and "UYARI YERLESIM" in e and "PDF OK" not in o and pt_t is not None and pt_t < 10.5,
            f"rc={r} taban_punto={pt_t} {(o + e)[-300:]!r}")
    r, o, e = S[("Y7c", yeni_js)]
    kontrol("Y7c düzeltmeyi ezen pre → UYARI + 'kirpik 1 (pre 1)'",
            r == 0 and "UYARI YERLESIM" in e and "kirpik 1 (pre 1)" in o and "PDF OK" not in o,
            f"rc={r} {(o + e)[-300:]!r}")

    # ── Y8 (3. bağlam: build_kd_pdf) ──
    r, o, e = S[("Y8", yeni_js)]
    s, x1 = sigar(P("Y8", "yeni"))
    pt_t = punto(P("Y8", "taban"))
    kontrol("Y8 build_kd_pdf: başlıksız görsel sığar + pre tam + 10,5; taban küçültür",
            r == 0 and "PDF OK" in o and s and punto(P("Y8", "yeni")) == 10.5 and PRE_SATIR in metin(P("Y8", "yeni"))
            and pt_t is not None and pt_t < 10.5,
            f"rc={r} x1={x1} punto={punto(P('Y8', 'yeni'))} taban={pt_t} {(o + e)[-200:]!r}")

    # ── Y9 / Y10 / Y11: KONTROL — taşan öğe YOK ⇒ tabanla aynı (bug-gate F1 CE1/CE5, F3 yan etkisi) ──
    def ayni(ad, w=None, h=None):
        k_y = gorsel_kutulari(P(ad, "yeni"), w, h)[0] if w else None
        k_t = gorsel_kutulari(P(ad, "taban"), w, h)[0] if w else None
        return (sayfa_metinleri(P(ad, "yeni")) == sayfa_metinleri(P(ad, "taban")) and k_y == k_t), k_y, k_t

    r, o, e = S[("Y9", yeni_js)]
    es, ky, kt = ayni("Y9", 260, 120)
    kontrol("Y9 kontrol: SIĞAN tabloda 260 px ikon + uzun metin → işaret 0, görsel kutusu + sayfa metni TABANLA AYNI",
            r == 0 and "PDF OK" in o and es and bool(ky) and beyan(o, ISARET_RE) == ("0", "0")
            and beyan(o, KADEME_RE) == ("0", "0", "0"), f"rc={r} kutu yeni={ky} taban={kt} esit={es}")
    r, o, e = S[("Y10", yeni_js)]
    es = ayni("Y10")[0]
    kontrol("Y10 kontrol: SIĞAN tablo hücresinde kısa pre → işaret 0, sayfa metni TABANLA AYNI",
            r == 0 and "PDF OK" in o and es and TABLO_PRE in metin(P("Y10", "yeni"), False)
            and beyan(o, ISARET_RE) == ("0", "0") and beyan(o, KADEME_RE) == ("0", "0", "0"),
            f"rc={r} esit={es} {(o + e)[-200:]!r}")
    r, o, e = S[("Y11", yeni_js)]
    es, ky, kt = ayni("Y11", 260, 120)
    # öznitelik oranı (260×240) özgün orandan (260×120) BİLEREK farklı: tabanda kutu ≈ 195×180 pt
    yg = bool(kt) and oran(kt[0]) is not None and abs(oran(kt[0]) - 260 / 240) < 0.05
    kontrol("Y11 kontrol: sığan, öznitelik oranı bozuk görsel → kutu TABANLA AYNI (global height:auto onu değiştirirdi)",
            r == 0 and "PDF OK" in o and es and yg and beyan(o, ISARET_RE) == ("0", "0"),
            f"rc={r} kutu yeni={ky} taban={kt} yer_gercegi={yg}")

    # ── Y12: F3 — w/h öznitelikli geniş görsel (1200×300) → sığar + oran 4,0 korunur ──
    r, o, e = S[("Y12", yeni_js)]
    ky, gen = gorsel_kutulari(P("Y12", "yeni"), 1200, 300)
    kt = gorsel_kutulari(P("Y12", "taban"), 1200, 300)[0]
    yg = bool(kt) and kt[0][2] > gen
    ok = (r == 0 and "PDF OK" in o and len(ky) == 1 and ky[0][2] <= gen and abs(oran(ky[0]) - 4.0) < 0.05
          and beyan(o, ISARET_RE) == ("1", "0"))
    kontrol("Y12 w/h öznitelikli 1200×300 görsel → sığar, en-boy oranı 4,0 korunur; yer gerçeği taban sayfa dışı",
            ok and yg, f"rc={r} kutu yeni={ky} oran={oran(ky[0]) if ky else None} taban={kt} sayfa={gen}")

    # ── Y13 / Y14: taşan tablonun hücre içi pre (1. kademe) / görsel (2. kademe) ──
    r, o, e = S[("Y13", yeni_js)]
    pt_t = punto(P("Y13", "taban"))
    kontrol("Y13 tablo hücresinde 190 karakterlik pre → 1. kademe (1, 0, 0), pre tam, 10,5; taban küçültür",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("1", "0", "0") and PRE_SATIR in metin(P("Y13", "yeni"))
            and punto(P("Y13", "yeni")) == 10.5 and pt_t is not None and pt_t < 10.5,
            f"rc={r} beyan={beyan(o, KADEME_RE)} punto={punto(P('Y13', 'yeni'))} taban={pt_t} {(o + e)[-200:]!r}")
    r, o, e = S[("Y14", yeni_js)]
    pt_t = punto(P("Y14", "taban"))
    ky, gen = gorsel_kutulari(P("Y14", "yeni"), 1200, 300)
    kontrol("Y14 tablo hücresinde 1200×300 görsel → 2. kademe (1, 1, 0), görsel sığar + oran 4,0, 10,5; taban küçültür",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("1", "1", "0") and len(ky) == 1 and ky[0][2] <= gen
            and abs(oran(ky[0]) - 4.0) < 0.05 and punto(P("Y14", "yeni")) == 10.5 and pt_t is not None and pt_t < 10.5,
            f"rc={r} beyan={beyan(o, KADEME_RE)} kutu={ky} punto={punto(P('Y14', 'yeni'))} taban={pt_t}")

    # ── Y15: F4 — `\\localhost\…` UNC uçtan uca (yönetim paylaşımı erişilebiliyorsa) ──
    if not unc15_var:
        atla("Y15", f"\\\\localhost yönetim paylaşımı erişilemedi ({unc15!r}); birim kanıt U1")
    else:
        (r, o, e), (rt, ot, et) = S[("Y15", yeni_js)], S[("Y15", taban_js)]
        isr = (kum / "unc.yeni.pdf").exists() and PRE_SATIR in metin(kum / "unc.yeni.pdf")
        kontrol("Y15 \\\\localhost UNC girdi → rc 0, PDF OK, belge basıldı; kontrol: taban da basar (regresyon sınıfı)",
                r == 0 and "PDF OK" in o and isr and rt == 0 and (kum / "unc.taban.pdf").exists(),
                f"rc={r} taban_rc={rt} isaret={isr} {(o + e)[-240:]!r}")

    # ── Y16: yalnız KIRPIK pre (300 px kutuda overflow-x:auto, sayfaya sığar) → işaret + tam metin ──
    r, o, e = S[("Y16", yeni_js)]
    kontrol("Y16 kırpık (sayfaya taşmayan) pre → işaret 'pre 1', 80 karakter TAM, kırpık 0; yer gerçeği taban eksik",
            r == 0 and "PDF OK" in o and PRE_KISA in metin(P("Y16", "yeni")) and PRE_KISA not in metin(P("Y16", "taban"))
            and beyan(o, ISARET_RE) == ("0", "1") and beyan(o, r"duzeltme oncesi tasan 0, kirpik 1") is not None,
            f"rc={r} isaret={beyan(o, ISARET_RE)} {(o + e)[-260:]!r}")
    shutil.rmtree(kum, ignore_errors=True)

print(f"pdf_yerlesim{(' ' + KIP) if KIP else ''}")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
for ad, sebep in ATLANAN:
    print(f"  [ATLANDI] {ad} — {sebep}")
gecen = sum(1 for _, ok, _ in SONUC if ok)
print(f"TOPLAM: {gecen}/{len(SONUC)} PASS · {len(ATLANAN)} ATLANDI (ölçülmedi; PASS sayılmaz)")
sys.exit(0 if gecen == len(SONUC) else 1)

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
    "--mutasyon-url": ("  const fileUrl = url.pathToFileURL(IN).href;",
                       '  const fileUrl = "file:///" + IN.split(path.sep).join("/");'),
    "--mutasyon-dizin": ("  if (dz.liste) {", "  if (false) {"),
    "--mutasyon-img": ('  "img{max-width:100%}" +', '  "" +'),
    "--mutasyon-pre": ('  "pre{white-space:pre-wrap;overflow-wrap:anywhere}" +', '  "" +'),
    "--mutasyon-govde": ('  "body{overflow-wrap:break-word}" +', '  "" +'),
    "--mutasyon-tablo-kod": ('  "table[data-ix-pdf-sar] :is(td,th) code{overflow-wrap:anywhere}" +', '  "" +'),
    "--mutasyon-tablo-hucre": (r'  "table[data-ix-pdf-sar=\"2\"] :is(td,th){overflow-wrap:anywhere}";', '  "";'),
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
kontrol("S1 url.pathToFileURL var, \"file:///\" + IN atamasi yok",
        "url.pathToFileURL(IN)" in src and not re.search(r'=\s*"file:///"\s*\+', src))
_css = re.search(r"const PDF_CSS =(.*?);\n", src, re.S)
_css_t = _css.group(1) if _css else ""
_css_metin = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', _css_t)).replace('\\"', '"')
_kural = re.findall(r"([^{}]+)\{([^}]*)\}", _css_metin)
_isaretsiz = [sec for sec, gov in _kural
              if "anywhere" in gov and re.search(r"\b(td|th|code|table)\b", sec) and "data-ix-pdf-sar" not in sec]
kontrol("S2 PDF_CSS'te işaretsiz tablo hücresi/kod anywhere YOK (yalnız data-ix-pdf-sar'lı tablo)",
        bool(_kural) and not _isaretsiz, f"kural={len(_kural)} isaretsiz={_isaretsiz}")
OPTS_RE = re.compile(r'\{ path: OUT, format: "A4", printBackground: true, margin: \{[^}]*\} \}')
kontrol("S3 page.pdf seçenek literali tabanla AYNI (Q366)",
        len(OPTS_RE.findall(src)) == 1 and OPTS_RE.findall(src) == OPTS_RE.findall(taban_src))


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
}
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


KADEME_RE = r"kod (\d+), tum hucre (\d+)"


def beyan(cikti, desen):
    m = re.search(desen, cikti)
    return m.groups() if m else None


Y_ADLAR = ["Y1", "Y1k", "Y2", "Y2k", "Y3", "Y3k", "Y4", "Y5", "Y5b", "Y5k", "Y6", "Y7", "Y7b", "Y7c", "Y8"]
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
        if ek == "genis":
            png(d / "screenshots" / "genis.png", 2400, 160)
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
    kontrol("Y3 başlıksız geniş görsel → sığar + gövde 10,5; yer gerçeği taban küçültür",
            r == 0 and "PDF OK" in o and s and punto(P("Y3", "yeni")) == 10.5 and pt_t is not None and pt_t < 10.5,
            f"rc={r} x1={x1} punto={punto(P('Y3', 'yeni'))} taban_punto={pt_t} {(o + e)[-200:]!r}")
    r, o, e = S[("Y3k", yeni_js)]
    kontrol("Y3k kontrol: başlıklı görsel → yeni ve taban sığar, 10,5",
            r == 0 and "PDF OK" in o and sigar(P("Y3k", "yeni"))[0] and sigar(P("Y3k", "taban"))[0]
            and punto(P("Y3k", "yeni")) == 10.5 == punto(P("Y3k", "taban")),
            f"rc={r} x1={sigar(P('Y3k', 'yeni'))}/{sigar(P('Y3k', 'taban'))} punto={punto(P('Y3k', 'yeni'))}/"
            f"{punto(P('Y3k', 'taban'))} {(o + e)[-200:]!r}")

    # ── Y4 ──
    r, o, e = S[("Y4", yeni_js)]
    kontrol("Y4 190 karakterlik pre → karakterler TAM, kırpık 0; yer gerçeği taban eksik",
            r == 0 and "PDF OK" in o and PRE_SATIR in metin(P("Y4", "yeni")) and PRE_SATIR not in metin(P("Y4", "taban"))
            and beyan(o, r"kalan tasan 0, kirpik 0") is not None, f"rc={r} {(o + e)[-260:]!r}")

    # ── Y5 / Y5b / Y5k ──
    r, o, e = S[("Y5", yeni_js)]
    pt_t = punto(P("Y5", "taban"))
    kontrol("Y5 tablo hücresinde uzun satır içi kod → 1. kademe (kod 1, tum hucre 0), 10,5, kod tam; taban küçültür",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("1", "0")
            and punto(P("Y5", "yeni")) == 10.5 and TABLO_KOD in metin(P("Y5", "yeni")) and pt_t is not None and pt_t < 10.5,
            f"rc={r} beyan={beyan(o, KADEME_RE)} punto={punto(P('Y5', 'yeni'))} taban={pt_t} {(o + e)[-200:]!r}")
    r, o, e = S[("Y5b", yeni_js)]
    pt_t = punto(P("Y5b", "taban"))
    kontrol("Y5b hücrede boşluksuz uzun sözcük → 2. kademe (tum hucre 1), 10,5; taban küçültür",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("1", "1")
            and punto(P("Y5b", "yeni")) == 10.5 and pt_t is not None and pt_t < 10.5,
            f"rc={r} beyan={beyan(o, KADEME_RE)} punto={punto(P('Y5b', 'yeni'))} taban={pt_t}")
    r, o, e = S[("Y5k", yeni_js)]
    kontrol("Y5k kontrol: SIĞAN tablo → kod 0 + sayfa sayfa metin TABANLA AYNI",
            r == 0 and "PDF OK" in o and beyan(o, KADEME_RE) == ("0", "0")
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

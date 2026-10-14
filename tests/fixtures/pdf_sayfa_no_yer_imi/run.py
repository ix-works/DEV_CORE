#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf_sayfa_no_yer_imi — `html_to_pdf.js` / `build_doc_pdf.py` OPT-IN "Sayfa X / Y" altbilgisi
+ başlıklardan yer imi (Q366, 2026-10-12).

KABUL ÖLÇÜTÜ (kaydın ⚠ RİSK bloğu): bayraksız üretim eskisiyle AYNI (sayfa sayısı + içerik);
bayraklı üretimde her sayfada "Sayfa X / Y", yer imi sayısı = başlık sayısı, Türkçe doğru.

TABAN = `_taban_html_to_pdf.js` (değişiklik ÖNCESİ sürümün birebir kopyası; pinli SHA'ya
`git show` sığ klonda yoktur ⇒ kardeş dosya). Girdi markdown'ı SENTETİKTİR (koşumda üretilir).

SENARYOLAR
  S1  bayraksız page.pdf seçenek literali tabanla AYNI (statik çapa; bağımlılıksız)
  S2  bilinmeyen bayrak → exit 2 [KULLANIM] (yol sanılmaz) · S3 eksik argüman → exit 2
  S4  build_doc_pdf.to_pdf: bayraksız komut ESKİSİ (node js html pdf) · bayraklı = sona eklenir
  S5  build_doc_pdf: --sayfa-no --pdf'siz → exit 2 · S6 bilinmeyen PDF bayrağı to_pdf'te RED
  S7  to_pdf rc 0'da stderr UYARISI yutulmaz (eski `stdout or stderr`)        [--mutasyon-stderr]
  P1  bayraksız (yeni) ↔ taban: sayfa sayısı + sayfa sayfa metin AYNI          [--mutasyon-bayraksiz]
  P2  bayraklı: HER sayfada tam bir "Sayfa i / N"
  P3  bayraklı gövde ↔ taban: sayfa sayısı + metin + blok y-konumları AYNI (gövde daralmadı)
                                                                                [--mutasyon-govde]
  P4  yer imi sayısı = HTML'deki h1..h6 sayısı
  P5  yer imi başlıkları = başlık metni (Türkçe harf + SATIRA KAYAN başlıkta boşluk)
                                                                                [--mutasyon-bosluk]
  P6  altbilgi kutusu gövdenin ALTINDA ve sayfa içinde (ölçülmüş yerleşim)
  P7  NEGATİF: `@page{margin:0}` belgede --sayfa-no → exit 2 [DURDU], PDF YAZILMAZ
                                                                                [--mutasyon-olcum]
  P7b NEGATİF (bug-gate 2026-10-12): `@media screen { @page { margin: 0 } }` — ekran emülasyonunda
      UYGULANIR — → exit 2 (eski sürüm grubun içine girmiyordu, 16 mm sanıyordu) [--mutasyon-medya]
  P7c kontrol: `<style media="print">` / `@media print` içindeki @page ekranda UYGULANMAZ → JS
      margin, exit 0 (eski sürüm stil sayfası medyasını süzmüyordu: sahte DURDU) [--mutasyon-sayfa-medya]
      YER GERÇEĞİ ÖNKOŞULU (bug-gate 2. tur 2026-10-14): aynı HTML taban betikle bayraksız basılınca
      ilk blok y = @page'siz kontrolün y'si (kural baskıda GERÇEKTEN uygulanmıyor); tutmazsa
      Chromium davranışı değişmiştir ⇒ P7c FAIL (aracın kararı tek başına kanıt değil).
  P7d NEGATİF `@page :first { margin: 0 }` → en küçük alt boşluk alınır, exit 2  [--mutasyon-sozde]
  P7e NEGATİF (bug-gate 2. tur): `@media (max-width: 900px) { @page { margin: 0 } }` — baskıda
      UYGULANIR (yer gerçeği önkoşulu: taban y = @page{margin:0} y'si) ama ekran viewport'u 1280 px
      ⇒ eski `matchMedia` 16 mm sanıp altbilgiyi gövdeye bastırıyordu → exit 2 + "VIEWPORT'A BAGLI"
                                                                                [--mutasyon-viewport]
  P7f SINIR: `@media (min-width: 1000px) { @page { margin: 0 } }` — baskıda UYGULANMAZ (önkoşul:
      taban y = kontrol y) ama muhafazakâr kural gereği exit 2 (bilinçli sahte DURDU, yüksek sesli)
  P7g NEGATİF "her iki dal": `@page{margin:0}` + `@media (min-width: 1000px){@page{margin:20mm}}` —
      baskıda medya UYGULANMAZ ⇒ etkin 0 (önkoşul: taban y = @page{margin:0} y'si); belirsiz grubun
      seçicisiz @page'i tabanı EZMEMELİ → exit 2                               [--mutasyon-belirsiz-taban]
  P7g-sayfa/-media/-supports/-layer/-import (bug-gate 2. re-gate 2026-10-14) belirsizliğin İÇ gruplara
      yayılması: `@page{margin:0}` + baskıda UYGULANMAYAN `(min-width: 1000px)` kabuğunun içinde
      `@page{margin:20mm}`; kabuk = stil sayfası medyası · iç içe `@media screen` · `@supports` ·
      `@layer` · iç içe `data:` @import (dış @import'un medyası). Yer gerçeği 0 mm → exit 2. Her kabuğun
      KENDİ kipi yalnız kendi vektöründe düşer          [--mutasyon-yayilim-sayfa|-media|-supports|-layer|-import]
  P7h1-5 M1: VIEWPORT_OZELLIK_RE'nin width dışındaki her seçeneği (orientation · aspect-ratio · height ·
      resolution · pixel-ratio) baskıda UYGULANAN bir `@page{margin:0}` ile → exit 2 + `@media~(` +
      "1 viewport'a bagli". orientation/aspect-ratio/height'te daraltma SESSİZ GEÇİŞTİR (ekran 1280×720 ≠
      baskı kutusu); resolution/pixel-ratio'da baskı = ekran (1dppx, ölçüldü) ⇒ daraltma yalnız
      sınıflandırmayı (etiket + kapsam sayısı) bozar                         [--mutasyon-viewport-dar]
  P7k1-4 L2 NEGATİF: okunamayan stil sayfası/import (`file://` → SecurityError) — `<link>`, `<link media=
      (max-width:900px)>`, `@import url()`, `@import url() (max-width:900px)`; kural baskıda UYGULANIR (yer
      gerçeği 0 mm) → exit 2 "stil sayfasi okunamadi … OLCULEMEDI"      [--mutasyon-okunamayan-sayfa
      (P7k1-2 + P7k5/P7f-alt) · --mutasyon-okunamayan-import (P7k3-4) · --mutasyon-okunamayan-durdu (P7k1-4)]
  P7c-link/P7c-import (bug-gate 3. tur 2026-10-14) kontrol: `<link media="print" href=sifir.css>` ve
      `@import url(sifir.css) print` — baskıda UYGULANMAZ (yer gerçeği = y_kontrol) ⇒ okunmadan atlanır:
      rc 0 + `| okunamayan stil sayfasi/import 0`     [--mutasyon-baski-sayfa-okunur | -baski-import-okunur]
  P7k5 NEGATİF `<meta http-equiv="Default-Style" content="alt">` + `<link rel="alternate stylesheet"
      title="alt" href=sifir.css>` — küme SEÇİLİ, baskıda UYGULANIR (yer gerçeği 0 mm) → okunamayan DURDU.
      rel/title'a bakıp atlayan sürüm burada SESSİZ geçer                        [--mutasyon-alternatif-atla]
  P7f-alt SINIR: aynı alternate `<link>` Default-Style'sız — baskıda UYGULANMAZ (yer gerçeği = y_kontrol)
      ama stil sayfası kümesi (title) seçimi modellenmez ⇒ bilinçli sahte DURDU [--mutasyon-alternatif-atla]
  P7j NEGATİF `document.adoptedStyleSheets` (JS `new CSSStyleSheet()` + `replaceSync('@page{margin:0}')`)
      — baskıda UYGULANIR (yer gerçeği 0 mm) → exit 2, kaynak `css-adopted>@page`, beyan
      `adoptedStyleSheets 1`                                                       [--mutasyon-adopted]
  P10 KAPSAM BEYANI: "(muhafazakar)" yalnız viewport sorgusu > 0 VE okunamayan 0 iken; satırda okunamayan
      sayısı + `adoptedStyleSheets N | shadow root TARANMADI`                  [--mutasyon-muhafazakar-etiket]
      (`--mutasyon-okunamayan-sayfa` P10'u da düşürür: etiketi bastıran sayım o kipte kaybolur)
  P7b-P7k vektörleri paralel koşar (4 iş parçacığı; her vektör ayrı HTML/PDF dosyası).
  P8  pre-wrap yerleşimi DEĞİŞTİRECEK başlık (kaynak içi satır sonu · baştaki boşluk) → düzeltme
      GERİ ALINIR, gövde blok y'leri tabanla AYNI                              [--mutasyon-geri-alma]
  P4b üretim SONRASI yer imi sayımı (PDF `Outlines /Count`) = PyMuPDF toc = başlık sayısı, uyarı yok
  P9  NEGATİF: outline üretmeyen kopya + --yer-imi → "YER-IMI PDF: 0" + "⚠ UYARI … YER IMI YOK"
                                                                            [--mutasyon-yer-imi-denetim]
  B1  3. BAĞLAM: build_doc_pdf.py CLI uçtan uca `--pdf --sayfa-no --yer-imi` (gerçek giriş noktası)
P*/B* node + playwright-core + msedge + markdown + PyMuPDF ister; biri yoksa ATLANDI basılır
(CI bu bağımlılıkları kurmaz — ölçülmemiş satır PASS sayılmaz, payda ayrı yazılır).

Koşum:  python tests/fixtures/pdf_sayfa_no_yer_imi/run.py [--mutasyon-<kip>]
"""
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path

if sys.platform == "win32":
    for _a in (sys.stdout, sys.stderr):
        try:
            _a.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
JS = KOK / "scripts" / "html_to_pdf.js"
TABAN_JS = Path(__file__).resolve().parent / "_taban_html_to_pdf.js"
BUILD = KOK / "scripts" / "build_doc_pdf.py"
# Bağımlılık yoklaması SAHTE modül enjeksiyonundan ÖNCE (sonra find_spec ValueError verir —
# ölçüldü: `python -S` ile CI benzetimi).
VAR_MARKDOWN = importlib.util.find_spec("markdown") is not None
VAR_FITZ = importlib.util.find_spec("fitz") is not None

GECERLI_KIP = {"--mutasyon-bayraksiz", "--mutasyon-govde", "--mutasyon-bosluk", "--mutasyon-olcum",
               "--mutasyon-geri-alma", "--mutasyon-medya", "--mutasyon-sayfa-medya", "--mutasyon-sozde",
               "--mutasyon-yer-imi-denetim", "--mutasyon-stderr", "--mutasyon-viewport",
               "--mutasyon-belirsiz-taban", "--mutasyon-viewport-dar", "--mutasyon-yayilim-sayfa",
               "--mutasyon-yayilim-media", "--mutasyon-yayilim-supports", "--mutasyon-yayilim-layer",
               "--mutasyon-yayilim-import", "--mutasyon-okunamayan-sayfa", "--mutasyon-okunamayan-import",
               "--mutasyon-okunamayan-durdu", "--mutasyon-muhafazakar-etiket", "--mutasyon-baski-sayfa-okunur",
               "--mutasyon-baski-import-okunur", "--mutasyon-alternatif-atla", "--mutasyon-adopted"}
_kip = [a for a in sys.argv[1:] if a.startswith("--")]
for a in _kip:
    if a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {a}")
        sys.exit(2)
KIP = _kip[0] if _kip else None

# Mutasyonlar html_to_pdf.js'in KUM kopyasına uygulanır (gerçek dosyaya yazılmaz).
MUTASYON = {
    # bayraksız yola altbilgi sızdırır → P1 düşmeli
    "--mutasyon-bayraksiz": ('if (BAYRAK.has("--sayfa-no")) {', 'if (true) {'),
    # altbilgi için gövdeyi daraltır (alt boşluğu büyütür) → P3 düşmeli
    "--mutasyon-govde": ('    opts.displayHeaderFooter = true;',
                         '    await p.addStyleTag({ content: "@page { margin-bottom: 60mm; }" });\n'
                         '    opts.displayHeaderFooter = true;'),
    # satır-kayma boşluk düzeltmesini söker → P5 düşmeli
    "--mutasyon-bosluk": ('      h.style.whiteSpace = "pre-wrap";', '      h.style.whiteSpace = eski;'),
    # etkin alt boşluk ölçümünü söker (her zaman yeter sayar) → P7 düşmeli
    "--mutasyon-olcum": ('    if (!(o.etkinMm >= gerek)) {', '    if (false) {'),
    # yerleşimi değiştiren başlıkta pre-wrap'i geri almaz → P8 düşmeli
    "--mutasyon-geri-alma": ('else { h.style.whiteSpace = eski; geri++; }', 'else { geri++; }'),
    # @media grubunun içine girmez (eski davranış) → P7b düşmeli
    "--mutasyon-medya": ('if (k !== "hayir") gez(r.cssRules', 'if (false) gez(r.cssRules'),
    # stil sayfası medyasını süzmez → P7c düşmeli (sahte DURDU)
    "--mutasyon-sayfa-medya": ('if (k === "hayir") continue;', 'if (false) continue;'),
    # viewport'a bağlı sorguyu ekran matchMedia'sıyla karara bağlar (eski davranış) → P7e düşmeli
    "--mutasyon-viewport": ('if (viewportRe.test(m.mediaText)) {', 'if (false) {'),
    # belirsiz grubun seçicisiz @page'i tabanı ezer (yalnız tek dal) → P7g düşmeli
    "--mutasyon-belirsiz-taban": ('if (sec || belirsiz) {', 'if (sec) {'),
    # viewport özellik listesini width'e daraltır (gate mutantı) → P7h1-5 düşmeli
    "--mutasyon-viewport-dar": ("/(?:width|height|aspect-ratio|orientation|resolution|pixel-ratio)/i",
                                "/(?:width)/i"),
    # belirsizliğin iç gruplara yayılımını keser — her biri yalnız KENDİ kabuğunda → P7g-<kabuk> düşmeli
    "--mutasyon-yayilim-sayfa": ('k === "belirsiz" || onek === "adopted>");', 'onek === "adopted>");'),
    "--mutasyon-yayilim-media": ('etiket("@media", k, r.media.mediaText), belirsiz || k === "belirsiz")',
                                 'etiket("@media", k, r.media.mediaText), k === "belirsiz")'),
    "--mutasyon-yayilim-supports": ('gez(r.cssRules, iz + "@supports>", belirsiz)',
                                    'gez(r.cssRules, iz + "@supports>", false)'),
    "--mutasyon-yayilim-layer": ("gez(r.cssRules, iz, belirsiz);   // @layer", "gez(r.cssRules, iz, false);   // @layer"),
    "--mutasyon-yayilim-import": ('belirsiz || k === "belirsiz"); }', 'k === "belirsiz"); }'),
    # okunamayan stil sayfasını / @import'u sessizce atlar (eski davranış) → P7k1-2 / P7k3-4 düşmeli
    "--mutasyon-okunamayan-sayfa": ('catch (e) { okunamayan.push(ss.href || "<style>"); continue; }',
                                    'catch (e) { continue; }'),
    "--mutasyon-okunamayan-import": ('catch (e) { okunamayan.push("@import " + (r.href || "?")); }',
                                     'catch (e) { }'),
    # okunamayan sayılır ama DURDU verilmez → P7k1-4 düşmeli
    "--mutasyon-okunamayan-durdu": ("    if (okn > 0) {", "    if (false) {"),
    # "(muhafazakar)" etiketini koşulsuz basar (eski davranış) → P10 düşmeli
    "--mutasyon-muhafazakar-etiket": ('(o.medya.viewport > 0 && okn === 0 ? " (muhafazakar)" : "")',
                                      '" (muhafazakar)"'),
    # bug-gate 3. tur (gate mutantlarının BİREBİR metni): baskıda uygulanmayan (medyası "hayir") sayfa /
    # @import yine de okunmaya çalışılır ve okunamayan sayılır → P7c-link / P7c-import düşmeli (sahte DURDU)
    "--mutasyon-baski-sayfa-okunur": ('      if (k === "hayir") continue;\n      let kurallar;',
                                      '      if (k === "hayir") { try { ss.cssRules; } catch (e) { okunamayan.push(ss.href || "?"); } continue; }\n      let kurallar;'),
    "--mutasyon-baski-import-okunur": ('if (k !== "hayir" && r.styleSheet) {',
                                       'if (k === "hayir" && r.styleSheet) { try { r.styleSheet.cssRules; } catch (e) { okunamayan.push("x"); } }\n          if (k !== "hayir" && r.styleSheet) {'),
    # naif (a): rel'inde "alternate" olan sayfayı okumadan atlar → P7k5 (sessiz geçiş) + P7f-alt düşmeli
    "--mutasyon-alternatif-atla": ('      if (ss.disabled) continue;',
                                   r'      if (ss.disabled || /\balternate\b/i.test((ss.ownerNode && ss.ownerNode.rel) || "")) continue;'),
    # adoptedStyleSheets taranmaz (eski davranış) → P7j düşmeli
    "--mutasyon-adopted": ('    const adopted = Array.from(document.adoptedStyleSheets || []);', '    const adopted = [];'),
    # sözde sayfa kuralını en küçüğe katmaz → P7d düşmeli
    "--mutasyon-sozde": ('if (s.mm < etkin) {', 'if (false) {'),
    # üretim sonrası yer imi denetimini söker → P9 düşmeli
    "--mutasyon-yer-imi-denetim": ('if (n === 0 && yerImi.toplam > 0) {', 'if (false) {'),
}
# build_doc_pdf.py'ye uygulanan mutasyonlar (S-bölümü, bağımlılıksız)
MUTASYON_BUILD = {
    # rc 0'da stderr uyarısını yine yutar → S7 düşmeli
    "--mutasyon-stderr": ("    if r.stdout.strip() and r.stderr.strip():\n", "    if False:\n"),
}
assert set(MUTASYON) | set(MUTASYON_BUILD) == GECERLI_KIP, "GECERLI_KIP ile mutasyon sözlükleri uyuşmuyor"

SONUC = []


def kontrol(ad, ok, detay=""):
    SONUC.append((ad, bool(ok), detay))


ATLANAN = []


def atla(ad, sebep):
    ATLANAN.append((ad, sebep))


def kos(komut, zaman=180):
    p = subprocess.run(komut, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=zaman)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ── bağımlılık yoklaması ─────────────────────────────────────────────────────
def bagimlilik():
    eksik = []
    if not shutil.which("node"):
        eksik.append("node")
    for m, var in (("markdown", VAR_MARKDOWN), ("fitz", VAR_FITZ)):
        if not var:
            eksik.append(m)
    if not eksik:
        r, o = kos(["node", "-e", "const p=require('path'),fs=require('fs'),os=require('os');"
                    "const s='npm/node_modules/@playwright/cli/node_modules/playwright-core';"
                    "const c=[process.env.APPDATA&&path.join(process.env.APPDATA,s),"
                    "path.join(os.homedir(),'AppData/Roaming',s)].filter(Boolean).find(x=>fs.existsSync(x))"
                    "||'playwright-core';const {chromium}=require(c);"
                    "chromium.launch({channel:'msedge',headless:true}).then(b=>b.close()).then(()=>console.log('OK'))"
                    ".catch(e=>{console.log('YOK '+e.message.split('\\n')[0]);process.exit(1)})"], 90)
        if r != 0:
            eksik.append("playwright/msedge (%s)" % o.strip()[:80])
    return eksik


# ── S: bağımlılıksız vektörler ───────────────────────────────────────────────
OPTS_RE = re.compile(r'\{ path: OUT, format: "A4", printBackground: true, margin: \{[^}]*\} \}')
yeni_txt = JS.read_text(encoding="utf-8")
taban_txt = TABAN_JS.read_text(encoding="utf-8")
m_y, m_t = OPTS_RE.findall(yeni_txt), OPTS_RE.findall(taban_txt)
kontrol("S1 bayraksız page.pdf seçenek literali tabanla AYNI",
        len(m_y) == 1 and m_y == m_t, f"yeni={m_y} taban={m_t}")

if shutil.which("node"):
    r, o = kos(["node", str(JS), "a.html", "b.pdf", "--sayfa-numarasi"])
    kontrol("S2 bilinmeyen bayrak → exit 2 [KULLANIM]", r == 2 and "[KULLANIM]" in o, f"rc={r} {o[:120]!r}")
    r, o = kos(["node", str(JS), "a.html"])
    kontrol("S3 eksik argüman → exit 2 [KULLANIM]", r == 2 and "[KULLANIM]" in o, f"rc={r} {o[:120]!r}")
else:
    atla("S2", "node yok")
    atla("S3", "node yok")


def build_modulu():
    """build_doc_pdf'i içe al; markdown yoksa yalnız bu import için sahte modül (to_pdf
    markdown KULLANMAZ — S4/S6 yalnız komut satırını ölçer)."""
    sys.path.insert(0, str(KOK / "scripts"))
    sahte = not VAR_MARKDOWN
    if sahte:
        sys.modules["markdown"] = types.ModuleType("markdown")
    try:
        if KIP in MUTASYON_BUILD:   # build_doc_pdf mutasyonu: kaynak METNİ değiştirilip gerçek __file__ ile
            eski, yeni = MUTASYON_BUILD[KIP]
            btxt = BUILD.read_text(encoding="utf-8")
            if btxt.count(eski) != 1:
                print(f"[DURDU] mutasyon çapası bulunamadı/çoğul ({KIP}): {eski!r}")
                sys.exit(3)
            mod = types.ModuleType("build_doc_pdf_fx")
            mod.__file__ = str(BUILD)
            exec(compile(btxt.replace(eski, yeni), str(BUILD), "exec"), mod.__dict__)
        else:
            spec = importlib.util.spec_from_file_location("build_doc_pdf_fx", BUILD)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
    finally:
        if sahte:
            sys.modules.pop("markdown", None)
    return mod


bd = build_modulu()
yakalanan = []


class _R:
    returncode, stdout, stderr = 0, "PDF OK", ""


_gercek_run = subprocess.run
bd.subprocess = types.SimpleNamespace(run=lambda c, **k: (yakalanan.append(c), _R())[1])
import builtins  # noqa: E402
_eski_import = builtins.__import__


def _imp(ad, *a, **k):
    if ad == "subprocess":
        return bd.subprocess
    return _eski_import(ad, *a, **k)


builtins.__import__ = _imp
try:
    tmpd = Path(tempfile.mkdtemp(prefix="q366s_"))
    h = tmpd / "x.html"
    h.write_text("<html></html>", encoding="utf-8")
    bd.to_pdf(str(h))
    bd.to_pdf(str(h), bayraklar=("--sayfa-no", "--yer-imi"))
    try:
        bd.to_pdf(str(h), bayraklar=("--zirva",))
        s6 = False
    except SystemExit as e:
        s6 = "bilinmeyen" in str(e)
    # S7 — rc 0 + stdout VE stderr: stderr'deki uyarı yutulmamalı (eski `stdout or stderr`)
    class _RU:
        returncode, stdout, stderr = 0, "YER-IMI PDF: 0 yer imi / 5 baslik\nPDF OK", "⚠ UYARI --yer-imi: YER IMI YOK"
    bd.subprocess.run = lambda c, **k: _RU()
    _s7 = io.StringIO()
    with redirect_stdout(_s7):
        bd.to_pdf(str(h), bayraklar=("--yer-imi",))
    s7 = _s7.getvalue()
finally:
    builtins.__import__ = _eski_import
js_abs = os.path.join(os.path.dirname(os.path.abspath(str(BUILD))), "html_to_pdf.js")
kontrol("S4a to_pdf bayraksız komut ESKİSİYLE AYNI (node js html pdf, ek argüman yok)",
        len(yakalanan) >= 1 and yakalanan[0] == ["node", js_abs, os.path.abspath(str(h)),
                                                  os.path.abspath(str(h))[:-5] + ".pdf"],
        f"{yakalanan[:1]}")
kontrol("S4b to_pdf bayraklı → bayraklar SONA eklenir",
        len(yakalanan) >= 2 and yakalanan[1][-2:] == ["--sayfa-no", "--yer-imi"], f"{yakalanan[1:2]}")
kontrol("S6 to_pdf bilinmeyen bayrak → RED (sessiz geçiş yok)", s6 and len(yakalanan) == 2, f"{yakalanan}")
kontrol("S7 to_pdf rc 0'da stderr UYARISI yutulmaz (stdout + stderr ikisi de basılır)",
        "PDF OK" in s7 and "YER IMI YOK" in s7, f"{s7!r}")

if VAR_MARKDOWN:
    r, o = kos([sys.executable, str(BUILD), "a.md", "b.html", "--sayfa-no"])
    kontrol("S5 build_doc_pdf --sayfa-no --pdf'siz → exit 2", r == 2 and "--pdf" in o, f"rc={r} {o[:160]!r}")
else:
    atla("S5", "markdown yok (build_doc_pdf modül başında import eder)")


# ── P: gerçek PDF üretimi ────────────────────────────────────────────────────
UZUN_H1 = "Örnek Kullanıcı Kılavuzu — ZSD001 Şık ve Uzun Başlıklı Doküman Çğıİöşü Denemesi"


def ornek_md():
    L = [f"# {UZUN_H1}", "", "Giriş paragrafı: çğıöşü ÇĞİÖŞÜ.", ""]
    for i in range(1, 6):
        L += [f"## {i}. Bölüm — Şartlar ve İşleyiş {i}", ""]
        L += [("Bu bölüm ığüşöç ile dolu bir paragraftır. " * 12).strip(), ""]
        L += [f"### {i}.1 Alt başlık Ğğ {i}", ""]
        L += ["| Alan | Açıklama | Değer |", "|---|---|---|"]
        L += [f"| ALAN{j} | Türkçe açıklama ışığı {j} | {j * 7} |" for j in range(1, 14)] + [""]
        L += [f"#### {i}.1.1 Ayrıntı İçerik {i}", "", "Kısa not.", ""]
    return "\n".join(L) + "\n"


def baslik_metinleri(html):
    out = []
    for m in re.finditer(r"<h([1-6])[^>]*>(.*?)</h\1>", html, re.S):
        t = re.sub(r"<[^>]+>", "", m.group(2))
        t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        out.append((int(m.group(1)), re.sub(r"\s+", " ", t).strip()))
    return out


ALTBILGI_RE = re.compile(r"Sayfa (\d+) / (\d+)")


def sayfa_metinleri(pdf, altbilgi_sil=False):
    import fitz
    d = fitz.open(pdf)
    out = []
    for pg in d:
        t = pg.get_text()
        if altbilgi_sil:
            t = ALTBILGI_RE.sub("", t)
        out.append("\n".join(s.rstrip() for s in t.splitlines() if s.strip()))
    return out


def blok_y(pdf):
    import fitz
    d = fitz.open(pdf)
    return [[round(b[1], 1) for b in pg.get_text("blocks") if not ALTBILGI_RE.search(b[4])] for pg in d]


eksik = bagimlilik()
P_ADLAR = ["P1", "P2", "P3", "P4", "P4b", "P5", "P6", "P7", "P7b", "P7c", "P7d", "P7e", "P7f", "P7g",
           "P7g-sayfa", "P7g-media", "P7g-supports", "P7g-layer", "P7g-import",
           "P7h1", "P7h2", "P7h3", "P7h4", "P7h5", "P7k1", "P7k2", "P7k3", "P7k4",
           "P7c-link", "P7c-import", "P7k5", "P7f-alt", "P7j", "P10",
           "P8", "P9", "B1"]
if eksik:
    for a in P_ADLAR:
        atla(a, "bağımlılık yok: " + ", ".join(eksik))
else:
    import fitz
    kum = Path(tempfile.mkdtemp(prefix="q366_"))
    js = kum / "html_to_pdf.js"
    src = yeni_txt
    if KIP in MUTASYON:
        eski, yeni = MUTASYON[KIP]
        if src.count(eski) != 1:
            print(f"[DURDU] mutasyon çapası bulunamadı/çoğul ({KIP}): {eski!r}")
            sys.exit(3)
        src = src.replace(eski, yeni)
    js.write_text(src, encoding="utf-8")
    md = kum / "ornek.md"
    md.write_text(ornek_md(), encoding="utf-8")
    html = kum / "ornek.html"
    r, o = kos([sys.executable, str(BUILD), str(md), str(html), "Örnek Kılavuz"])
    if r != 0:
        print(f"[DURDU] HTML üretilemedi rc={r}: {o[:300]}")
        sys.exit(3)
    taban, bsz, bli = kum / "taban.pdf", kum / "bayraksiz.pdf", kum / "bayrakli.pdf"
    uretim_cikti = []
    for kmt in ([str(TABAN_JS), str(html), str(taban)], [str(js), str(html), str(bsz)],
                [str(js), str(html), str(bli), "--sayfa-no", "--yer-imi"]):
        r, o = kos(["node"] + kmt)
        if r != 0:
            print(f"[DURDU] PDF üretilemedi rc={r} {kmt[-1]}: {o[:300]}")
            sys.exit(3)
        uretim_cikti.append(o)
    t_tab, t_bsz = sayfa_metinleri(taban), sayfa_metinleri(bsz)
    kontrol("P1 bayraksız ↔ taban: sayfa sayısı + metin AYNI",
            len(t_tab) == len(t_bsz) and t_tab == t_bsz and len(t_tab) >= 3,
            f"sayfa taban={len(t_tab)} yeni={len(t_bsz)}")
    d = fitz.open(bli)
    N = d.page_count
    p2 = [ALTBILGI_RE.findall(pg.get_text()) for pg in d]
    kontrol("P2 bayraklı: her sayfada tam bir 'Sayfa i / N'",
            all(x == [(str(i + 1), str(N))] for i, x in enumerate(p2)), f"{p2}")
    t_bli = sayfa_metinleri(bli, altbilgi_sil=True)
    kontrol("P3 bayraklı gövde ↔ taban: sayfa sayısı + metin + blok y AYNI (gövde daralmadı)",
            N == len(t_tab) and t_bli == t_tab and blok_y(bli) == blok_y(taban),
            f"sayfa taban={len(t_tab)} bayrakli={N}")
    basliklar = baslik_metinleri(html.read_text(encoding="utf-8"))
    toc = d.get_toc()
    kontrol("P4 yer imi sayısı = başlık sayısı", len(toc) == len(basliklar) and len(toc) >= 10,
            f"toc={len(toc)} baslik={len(basliklar)}")
    o_bli = uretim_cikti[2]
    kontrol("P4b üretim SONRASI denetim: 'YER-IMI PDF: N yer imi / N baslik' (PDF'ten sayılan = PyMuPDF), uyarı yok",
            f"YER-IMI PDF: {len(toc)} yer imi / {len(basliklar)} baslik" in o_bli and "⚠" not in o_bli,
            f"{o_bli[-300:]!r}")
    kiyas = [(lv, re.sub(r"\s+", " ", t).strip()) for lv, t, _ in toc]
    farkli = [(a, b) for a, b in zip(kiyas, basliklar) if a != b]
    kontrol("P5 yer imi başlıkları = başlık metni (Türkçe + satıra kayan başlıkta boşluk)",
            not farkli and len(kiyas) == len(basliklar) and kiyas[0][1] == UZUN_H1,
            f"ilk fark={farkli[:2]}")
    p6 = []
    for pg in d:
        bl = pg.get_text("blocks")
        ab = [b for b in bl if ALTBILGI_RE.search(b[4])]
        gv = [b for b in bl if not ALTBILGI_RE.search(b[4])]
        p6.append(len(ab) == 1 and ab[0][1] > max(b[3] for b in gv) and ab[0][3] <= pg.rect.height)
    kontrol("P6 altbilgi gövdenin ALTINDA ve sayfa içinde (her sayfa)", all(p6), f"{p6}")
    # P7 — negatif: @page margin:0 → altbilgiye yer yok
    h0 = kum / "sifir.html"
    h0.write_text('<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8"><style>'
                  '@page { size: A4; margin: 0; } body{margin:0}</style></head><body>'
                  '<h1>Sıfır boşluk</h1><p>gövde</p></body></html>', encoding="utf-8")
    p0 = kum / "sifir.pdf"
    r, o = kos(["node", str(js), str(h0), str(p0), "--sayfa-no"])
    kontrol("P7 NEGATİF @page{margin:0} + --sayfa-no → exit 2 [DURDU], PDF yok",
            r == 2 and "[DURDU]" in o and not p0.exists(), f"rc={r} var={p0.exists()} {o[-160:]!r}")

    # P7b-d — bug-gate 2026-10-12: @page koşullu grup / sözde sayfa içindeyken de ölçülür.
    # Uygulanıp uygulanmadığı ÖLÇÜLDÜ (bayraksız PDF'te ilk blok y: uygulanan 11.8pt, uygulanmayan 50.8pt).
    # YER GERÇEĞİ (bug-gate 2. tur 2026-10-14): her vektörün HTML'i ayrıca TABAN betikle bayraksız
    # basılır, ilk blok y'si iki kontrolle kıyaslanır — `@page`'siz (y_kontrol) ve `@page{margin:0}`
    # (y_sifir). Aracın kararı tek başına kanıt değildir (kapı ile tüketici aynı ortamı ölçmeli).
    def css_dene(ad, css_head, arac=True):
        hh = kum / (ad + ".html")
        hh.write_text('<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
                      '<style>body{margin:0}</style>' + css_head +
                      '</head><body><h1>Koşullu</h1><p>gövde</p></body></html>', encoding="utf-8")
        pt = kum / (ad + "_taban.pdf")
        rt, ot = kos(["node", str(TABAN_JS), str(hh), str(pt)])
        ty = None
        if rt == 0 and pt.exists():
            bl = fitz.open(pt)[0].get_text("blocks")
            ty = round(min(b[1] for b in bl), 1) if bl else None
        if not arac:
            return None, "", False, ty
        pp = kum / (ad + ".pdf")
        rr, oo = kos(["node", str(js), str(hh), str(pp), "--sayfa-no"])
        return rr, oo, pp.exists(), ty
    (kum / "sifir.css").write_text("@page { margin: 0; }", encoding="utf-8")   # P7k: <link>/@import hedefi
    B0 = "<style>@page { margin: 0; }</style>"   # koşulsuz taban 0 (P7g ailesi)
    I20 = "@page { margin: 20mm; }"              # baskıda UYGULANMAYAN kabuğun içindeki değer
    VEKTOR = {   # ad: (head, araç da koşsun mu) — her vektör ayrı dosya ⇒ paralel koşum güvenli
        "yg_kontrol": ("", True),       # @page'siz kontrol (yer gerçeği) + P10 (viewport 0)
        "yg_sifir": (B0, False),
        "medya_ekran": ("<style>@media screen { @page { margin: 0; } } body{margin:0}</style>", True),
        "medya_baski": ('<style media="print">@page { margin: 0; }</style>'
                        "<style>@media print { @page { margin: 0; } }</style>", True),
        "sozde_ilk": ("<style>@page :first { margin: 0; }</style>", True),
        "vp_max900": ("<style>@media (max-width: 900px) { @page { margin: 0; } }</style>", True),
        "vp_min1000": ("<style>@media (min-width: 1000px) { @page { margin: 0; } }</style>", True),
        "vp_iki_dal": ("<style>@page { margin: 0; } @media (min-width: 1000px) { @page { margin: 20mm; } }</style>", True),
        # M1 — VIEWPORT_OZELLIK_RE'nin width dışındaki her seçeneği; hepsi baskıda UYGULANIR (yer gerçeği)
        "vp_yon": ("<style>@media (orientation: portrait) { @page { margin: 0; } }</style>", True),
        "vp_oran": ("<style>@media (max-aspect-ratio: 1/1) { @page { margin: 0; } }</style>", True),
        "vp_yukseklik": ("<style>@media (min-height: 900px) { @page { margin: 0; } }</style>", True),
        "vp_cozunurluk": ("<style>@media (max-resolution: 1dppx) { @page { margin: 0; } }</style>", True),
        "vp_piksel_orani": ("<style>@media (-webkit-max-device-pixel-ratio: 1) { @page { margin: 0; } }</style>", True),
        # L1 — belirsizliğin iç gruplara yayılımı: (min-width: 1000px) baskıda UYGULANMAZ ⇒ etkin 0
        "yay_sayfa": (B0 + '<style media="(min-width: 1000px)">' + I20 + "</style>", True),
        "yay_media": ("<style>@page { margin: 0; } @media (min-width: 1000px) { @media screen { " + I20 + " } }</style>", True),
        "yay_supports": ("<style>@page { margin: 0; } @media (min-width: 1000px) { @supports (display: block) { "
                         + I20 + " } }</style>", True),
        "yay_layer": ("<style>@page { margin: 0; } @media (min-width: 1000px) { @layer a { " + I20 + " } }</style>", True),
        # iç @import medyasız; belirsizlik DIŞ @import'un medyasından miras (data: URL okunur — ölçüldü)
        "yay_import": (B0 + "<style>@import url(\"data:text/css,@import url('data:text/css," + I20
                       + "');\") (min-width: 1000px);</style>", True),
        # L2 — okunamayan stil sayfası / @import (file:// → SecurityError); kural baskıda UYGULANIR
        "okn_link": ('<link rel="stylesheet" href="sifir.css">', True),
        "okn_link_vp": ('<link rel="stylesheet" media="(max-width: 900px)" href="sifir.css">', True),
        "okn_import": ('<style>@import url("sifir.css");</style>', True),
        "okn_import_vp": ('<style>@import url("sifir.css") (max-width: 900px);</style>', True),
        # bug-gate 3. tur — E1 baskı medyalı <link>/@import (baskıda UYGULANMAZ ⇒ okunmadan atlanır)
        "baski_link": ('<link rel="stylesheet" media="print" href="sifir.css">', True),
        "baski_import": ('<style>@import url("sifir.css") print;</style>', True),
        # E2 stil sayfası kümesi: Default-Style seçerse alternate UYGULANIR; seçmezse UYGULANMAZ
        "alt_secili": ('<meta http-equiv="Default-Style" content="alt">'
                       '<link rel="alternate stylesheet" title="alt" href="sifir.css">', True),
        "alt_saf": ('<link rel="alternate stylesheet" title="alt" href="sifir.css">', True),
        # E3 adoptedStyleSheets (baskıda UYGULANIR)
        "adopted": ("<script>const s=new CSSStyleSheet();s.replaceSync('@page{margin:0}');"
                    "document.adoptedStyleSheets=[s];</script>", True),
    }
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as _ex:
        SON = dict(zip(VEKTOR, _ex.map(lambda a: css_dene(a, *VEKTOR[a]), VEKTOR)))
    y_kontrol, y_sifir = SON["yg_kontrol"][3], SON["yg_sifir"][3]
    yg_ok = y_kontrol is not None and y_sifir is not None and abs(y_kontrol - y_sifir) > 10
    yg_iz = f"y_kontrol={y_kontrol} y_sifir={y_sifir}"
    uygulanmadi = lambda ty: yg_ok and ty is not None and abs(ty - y_kontrol) < 0.5   # noqa: E731
    uygulandi = lambda ty: yg_ok and ty is not None and abs(ty - y_sifir) < 0.5       # noqa: E731

    def beyan(o):
        """ALTBILGI kapsam beyanı satırı (DURDU mesajı '(muhafazakar)' taşıyabilir — yalnız bu satır ölçülür)."""
        m = re.search(r"ALTBILGI: [^\n]*", o)
        return m.group(0) if m else ""
    r, o, var, ty = SON["medya_ekran"]
    kontrol("P7b NEGATİF @media screen{@page{margin:0}} (ekran emülasyonunda UYGULANIR) → exit 2, PDF yok",
            r == 2 and "[DURDU]" in o and "@media(screen)" in o and not var and uygulandi(ty),
            f"rc={r} var={var} taban_y={ty} {yg_iz} {o[-200:]!r}")
    r, o, var, ty = SON["medya_baski"]
    kontrol("P7c kontrol: print medyalı @page (ekranda UYGULANMAZ — yer gerçeği önkoşulu) → JS margin, exit 0",
            uygulanmadi(ty) and r == 0 and "(js-margin)" in o and var,
            f"ONKOSUL taban_y={ty} {yg_iz} (y_kontrol'e eşit olmalı) · rc={r} var={var} {o[-200:]!r}")
    r, o, var, ty = SON["sozde_ilk"]
    kontrol("P7d NEGATİF @page :first{margin:0} (yalnız 1. sayfa) → EN KÜÇÜK alınır, exit 2",
            r == 2 and "@page :first" in o and not var, f"rc={r} var={var} {o[-200:]!r}")
    r, o, var, ty = SON["vp_max900"]
    kontrol("P7e NEGATİF @media (max-width:900px){@page{margin:0}} (baskıda UYGULANIR — yer gerçeği) → exit 2 VIEWPORT",
            uygulandi(ty) and r == 2 and "[DURDU]" in o and "@media~((max-width: 900px))" in o
            and "VIEWPORT'A BAGLI" in o and not var,
            f"ONKOSUL taban_y={ty} {yg_iz} (y_sifir'e eşit olmalı) · rc={r} var={var} {o[-240:]!r}")
    r, o, var, ty = SON["vp_min1000"]
    kontrol("P7f SINIR @media (min-width:1000px){@page{margin:0}} (baskıda UYGULANMAZ — yer gerçeği) → muhafazakâr exit 2",
            uygulanmadi(ty) and r == 2 and "VIEWPORT'A BAGLI" in o and not var,
            f"ONKOSUL taban_y={ty} {yg_iz} (y_kontrol'e eşit olmalı) · rc={r} var={var} {o[-240:]!r}")
    r, o, var, ty = SON["vp_iki_dal"]
    kontrol("P7g NEGATİF @page{margin:0} + @media(min-width:1000px){@page{margin:20mm}} (baskıda 0 — yer gerçeği) → exit 2",
            uygulandi(ty) and r == 2 and "[DURDU]" in o and not var,
            f"ONKOSUL taban_y={ty} {yg_iz} (y_sifir'e eşit olmalı) · rc={r} var={var} {o[-240:]!r}")
    # P7g-<kabuk> — L1: belirsizlik iç gruba yayılmalı (yer gerçeği: baskıda etkin 0 mm)
    for ad, kabuk in (("yay_sayfa", "sayfa"), ("yay_media", "media"), ("yay_supports", "supports"),
                      ("yay_layer", "layer"), ("yay_import", "import")):
        r, o, var, ty = SON[ad]
        kontrol(f"P7g-{kabuk} NEGATİF belirsiz kabuk ({kabuk}) içindeki seçicisiz @page{{margin:20mm}} tabanı "
                f"EZMEZ (baskıda 0 — yer gerçeği) → exit 2",
                uygulandi(ty) and r == 2 and "[DURDU]" in o and not var,
                f"ONKOSUL taban_y={ty} {yg_iz} (y_sifir'e eşit olmalı) · rc={r} var={var} {beyan(o)!r}")
    # P7h1-5 — M1: viewport özellik listesinin her seçeneği (yer gerçeği: baskıda UYGULANIR)
    for i, (ad, oz) in enumerate((("vp_yon", "orientation"), ("vp_oran", "max-aspect-ratio"),
                                  ("vp_yukseklik", "min-height"), ("vp_cozunurluk", "max-resolution"),
                                  ("vp_piksel_orani", "-webkit-max-device-pixel-ratio")), 1):
        r, o, var, ty = SON[ad]
        kontrol(f"P7h{i} NEGATİF @media ({oz}…){{@page{{margin:0}}}} (baskıda UYGULANIR — yer gerçeği) → exit 2 "
                f"VIEWPORT + '~' etiketi + '1 viewport'a bagli'",
                uygulandi(ty) and r == 2 and "[DURDU]" in o and f"@media~(({oz}" in o and "VIEWPORT'A BAGLI" in o
                and "1 viewport'a bagli" in beyan(o) and not var,
                f"ONKOSUL taban_y={ty} {yg_iz} (y_sifir'e eşit olmalı) · rc={r} var={var} {beyan(o)!r}")
    # P7k1-4 — L2: okunamayan stil sayfası / @import → muhafazakâr DURDU (yer gerçeği: baskıda UYGULANIR)
    for i, ad in enumerate(("okn_link", "okn_link_vp", "okn_import", "okn_import_vp"), 1):
        r, o, var, ty = SON[ad]
        kontrol(f"P7k{i} NEGATİF okunamayan {ad[4:]} (sifir.css baskıda UYGULANIR — yer gerçeği) → exit 2 "
                f"'stil sayfasi okunamadi … OLCULEMEDI'",
                uygulandi(ty) and r == 2 and "stil sayfasi okunamadi (1 kaynak" in o and "OLCULEMEDI" in o
                and "okunamayan stil sayfasi/import 1" in beyan(o) and not var,
                f"ONKOSUL taban_y={ty} {yg_iz} (y_sifir'e eşit olmalı) · rc={r} var={var} {o[-260:]!r}")
    # P7c-link / P7c-import — E1: baskı medyalı <link>/@import okunmadan atlanır (yer gerçeği: UYGULANMAZ)
    for ad, et in (("baski_link", "link"), ("baski_import", "import")):
        r, o, var, ty = SON[ad]
        kontrol(f"P7c-{et} kontrol: print medyalı {et} sifir.css (baskıda UYGULANMAZ — yer gerçeği) → okunmaz, "
                f"exit 0 + 'okunamayan stil sayfasi/import 0'",
                uygulanmadi(ty) and r == 0 and "(js-margin)" in o and "okunamayan stil sayfasi/import 0" in beyan(o) and var,
                f"ONKOSUL taban_y={ty} {yg_iz} (y_kontrol'e eşit olmalı) · rc={r} var={var} {o[-260:]!r}")
    # P7k5 / P7f-alt — E2: stil sayfası kümesi (title) seçimi modellenmez (bilinçli bedel, lider kararı)
    r, o, var, ty = SON["alt_secili"]
    kontrol("P7k5 NEGATİF Default-Style seçili alternate sifir.css (baskıda UYGULANIR — yer gerçeği) → okunamayan DURDU",
            uygulandi(ty) and r == 2 and "stil sayfasi okunamadi (1 kaynak" in o and not var,
            f"ONKOSUL taban_y={ty} {yg_iz} (y_sifir'e eşit olmalı) · rc={r} var={var} {o[-260:]!r}")
    r, o, var, ty = SON["alt_saf"]
    kontrol("P7f-alt SINIR seçilmemiş alternate sifir.css (baskıda UYGULANMAZ — yer gerçeği) → bilinçli sahte DURDU",
            uygulanmadi(ty) and r == 2 and "stil sayfasi okunamadi (1 kaynak" in o and not var,
            f"ONKOSUL taban_y={ty} {yg_iz} (y_kontrol'e eşit olmalı) · rc={r} var={var} {o[-260:]!r}")
    # P7j — E3: document.adoptedStyleSheets taranır (yer gerçeği: baskıda UYGULANIR)
    r, o, var, ty = SON["adopted"]
    kontrol("P7j NEGATİF adoptedStyleSheets @page{margin:0} (baskıda UYGULANIR — yer gerçeği) → exit 2 "
            "'css-adopted>@page' + 'adoptedStyleSheets 1'",
            uygulandi(ty) and r == 2 and "css-adopted>@page" in o and "adoptedStyleSheets 1 |" in beyan(o) and not var,
            f"ONKOSUL taban_y={ty} {yg_iz} (y_sifir'e eşit olmalı) · rc={r} var={var} {o[-260:]!r}")
    # P10 — kapsam beyanı: "(muhafazakar)" yalnız viewport > 0 VE okunamayan 0 iken
    s0, s1, s2 = beyan(SON["yg_kontrol"][1]), beyan(SON["okn_link_vp"][1]), beyan(SON["vp_max900"][1])
    kontrol("P10 kapsam beyanı: '(muhafazakar)' yalnız viewport sorgusu > 0 VE okunamayan 0 iken + okunamayan sayısı "
            "+ taranan yüzeyler (adoptedStyleSheets / shadow root TARANMADI)",
            SON["yg_kontrol"][0] == 0 and "0 viewport'a bagli |" in s0 and "(muhafazakar)" not in s0
            and "okunamayan stil sayfasi/import 0 | adoptedStyleSheets 0 | shadow root TARANMADI" in s0
            and "1 viewport'a bagli |" in s1 and "(muhafazakar)" not in s1
            and "1 viewport'a bagli (muhafazakar) | okunamayan stil sayfasi/import 0" in s2,
            f"viewport0={s0!r} okunamayan={s1!r} viewport1={s2!r}")
    # P9 — yer imi denetimi NEGATİF: outline üretmeyen bir kopyada uyarı basılmalı
    js_nout = kum / "html_to_pdf_outline_yok.js"
    if src.count("opts.outline = true;") != 1:
        print("[DURDU] P9 çapası bulunamadı/çoğul: opts.outline = true;")
        sys.exit(3)
    js_nout.write_text(src.replace("opts.outline = true;", "opts.outline = false;"), encoding="utf-8")
    r, o = kos(["node", str(js_nout), str(html), str(kum / "outline_yok.pdf"), "--yer-imi"])
    kontrol("P9 NEGATİF outline üretilmeyen PDF → 'YER-IMI PDF: 0' + '⚠ UYARI … YER IMI YOK'",
            r == 0 and "YER-IMI PDF: 0 yer imi" in o and "YER IMI YOK" in o, f"rc={r} {o[-300:]!r}")
    # P8 — pre-wrap'in yerleşimi değiştireceği başlıklar: düzeltme geri alınmalı
    h8 = kum / "riskli.html"
    h8.write_text('<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8"></head><body>'
                  '<h2>Satır' + chr(10) + 'Bölünmüş Başlık</h2><h3>  Baştaki boşluk</h3><p>gövde metni</p>'
                  '</body></html>', encoding="utf-8")
    p8t, p8y = kum / "riskli_taban.pdf", kum / "riskli_yeni.pdf"
    r1, _ = kos(["node", str(TABAN_JS), str(h8), str(p8t)])
    r2, o2 = kos(["node", str(js), str(h8), str(p8y), "--yer-imi"])
    kontrol("P8 yerleşimi değiştirecek başlıkta düzeltme GERİ ALINIR, gövde y'leri AYNI",
            r1 == 0 and r2 == 0 and "geri alindi (yerlesim degisirdi): 2" in o2
            and blok_y(p8y) == blok_y(p8t), f"rc={r1},{r2} {o2[:160]!r}")
    # B1 — 3. bağlam: gerçek giriş noktası (build_doc_pdf CLI) uçtan uca, gerçek js ile
    if KIP:
        atla("B1", "mutasyon kipinde (B1 gerçek scripts/html_to_pdf.js'i koşar; kum kopyasını görmez)")
    else:
        h2 = kum / "KD-SD-001_Uctan_Uca.html"
        r, o = kos([sys.executable, str(BUILD), str(md), str(h2), "Uçtan Uca", "--pdf",
                    "--sayfa-no", "--yer-imi"])
        p2f = Path(str(h2)[:-5] + ".pdf")
        ok = r == 0 and p2f.exists()
        if ok:
            dd = fitz.open(p2f)
            ok = (dd.page_count == len(t_tab)
                  and all(ALTBILGI_RE.search(pg.get_text()) for pg in dd)
                  and len(dd.get_toc()) == len(basliklar))
        kontrol("B1 build_doc_pdf --pdf --sayfa-no --yer-imi uçtan uca (sayfa no + yer imi)", ok,
                f"rc={r} {o[-200:]!r}")
    shutil.rmtree(kum, ignore_errors=True)

# ── rapor ────────────────────────────────────────────────────────────────────
print(f"pdf_sayfa_no_yer_imi{(' ' + KIP) if KIP else ''}")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
for ad, sebep in ATLANAN:
    print(f"  [ATLANDI] {ad} — {sebep}")
gecen = sum(1 for _, ok, _ in SONUC if ok)
print(f"TOPLAM: {gecen}/{len(SONUC)} PASS · {len(ATLANAN)} ATLANDI (ölçülmedi; PASS sayılmaz)")
sys.exit(0 if gecen == len(SONUC) else 1)

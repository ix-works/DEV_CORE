/** HTML → PDF (Edge, page.pdf). Kullanım:
 *   node scripts/html_to_pdf.js <input.html> <output.pdf> [--sayfa-no] [--yer-imi]
 * KD/FS/TS markdown→HTML (build_kd_pdf.py / build_doc_pdf.py) çıktısını şık A4 PDF'e çevirir.
 *
 * OPT-IN BAYRAKLAR (Q366, 2026-10-12) — bayraksız çıktı ESKİSİYLE AYNIDIR (aynı page.pdf
 * seçenekleri; eski dokümanın yeniden üretimi md5 dışında değişmez):
 *   --sayfa-no  her sayfanın alt boşluğuna "Sayfa X / Y" (yalnız METİN; footerTemplate).
 *   --yer-imi   başlık hiyerarşisinden (h1..h6) PDF yer imleri (Playwright `outline`).
 *
 * ⛔ ALTBİLGİ GÖVDEYİ DARALTMAZ: altbilgi MEVCUT alt boşluğa yerleşir, margin değiştirilmez
 *    ⇒ sayfa sayısı ve tablo bölünmesi bayraklı/bayraksız AYNI kalır. Bunun bedeli: alt
 *    boşluk altbilgiye yetmiyorsa altbilgi kırpılır/görünmez — o yüzden ETKİN alt boşluk
 *    belgeden ÖLÇÜLÜR (sabit varsayılmaz) ve yetmiyorsa SESSİZ değil exit 2.
 *    Ölçülen tuzaklar (bu evde iki kez):
 *    · CSS `@page { margin: … }` page.pdf'e verilen JS margin'i SESSİZCE ezer
 *      (build_doc_pdf/build_kd_pdf CSS'i `@page` margin TAŞIR ⇒ etkin boşluk CSS'inkidir).
 *    · footerTemplate ZEMİN BOYAMAZ (mürekkep yalnız border+metin) ⇒ altbilgi yalnız metin.
 *    · footerTemplate kendi yazı boyutunu açıkça ister (varsayılan neredeyse görünmez).
 *    · `<thead>` tekrarı bu yolda çalışmaz — altbilgi için kullanılmadı.
 */
const path = require("path");
const fs = require("fs");
const os = require("os");
// playwright-core yolunu DİNAMİK çöz (hardcode/username-placeholder YOK).
// Global npm kurulumundaki @playwright/cli altındaki playwright-core'u ara; bulunamazsa
// normal modül çözümüne düş (yerel node_modules / NODE_PATH).
function resolvePlaywrightCore() {
  const suffix = "npm/node_modules/@playwright/cli/node_modules/playwright-core";
  const cands = [
    process.env.APPDATA && path.join(process.env.APPDATA, suffix),           // Windows: C:\Users\<user>\AppData\Roaming
    path.join(os.homedir(), "AppData/Roaming", suffix),                       // Windows fallback
    process.env.npm_config_prefix && path.join(process.env.npm_config_prefix, "node_modules/@playwright/cli/node_modules/playwright-core"),
  ].filter(Boolean);
  for (const c of cands) { if (fs.existsSync(c)) return c; }
  return "playwright-core";                                                   // son çare: normal require çözümü
}

// ── argümanlar: bilinmeyen bayrak YOL sanılmaz (sessiz yanlış dosya yerine kullanım hatası)
const BILINEN_BAYRAK = new Set(["--sayfa-no", "--yer-imi"]);
const _arg = process.argv.slice(2);
const BAYRAK = new Set(_arg.filter(a => a.startsWith("--")));
const KONUM = _arg.filter(a => !a.startsWith("--"));
for (const b of BAYRAK) {
  if (!BILINEN_BAYRAK.has(b)) {
    console.error("[KULLANIM] bilinmeyen bayrak: " + b + "  (bilinen: " + [...BILINEN_BAYRAK].join(" ") + ")");
    process.exit(2);
  }
}
if (KONUM.length !== 2) {
  console.error("[KULLANIM] node scripts/html_to_pdf.js <input.html> <output.pdf> [--sayfa-no] [--yer-imi]");
  process.exit(2);
}

const { chromium } = require(resolvePlaywrightCore());
const IN = path.resolve(KONUM[0]);
const OUT = path.resolve(KONUM[1]);

// Altbilgi şablonu: Chromium `pageNumber`/`totalPages` sınıflarını doldurur. Yalnız metin
// (zemin boyanmaz); font boyutu AÇIK (varsayılan şablon fontu okunamayacak kadar küçük).
const ALTBILGI_HTML =
  '<div style="width:100%;font-family:\'Segoe UI\',Arial,sans-serif;font-size:8pt;color:#5a6b7b;' +
  'text-align:right;padding:0 12mm;box-sizing:border-box;">' +
  'Sayfa <span class="pageNumber"></span> / <span class="totalPages"></span></div>';
// Altbilgi ile gövde arasında en az bu kadar boşluk kalmalı (mm) — altbilgi gövde metnine
// yapışmasın. Altbilginin KENDİ yüksekliği ölçülür; bu yalnız ek nefes payıdır.
const ALTBILGI_PAY_MM = 2;

// Viewport'a bağlı medya özellikleri (min-/max-/device-/aralık sözdizimi dahil — alt dizge eşleşir).
const VIEWPORT_OZELLIK_RE = /(?:width|height|aspect-ratio|orientation|resolution|pixel-ratio)/i;

/** Belgenin ETKİN alt boşluğunu (mm) ve altbilginin yüksekliğini (mm) ölçer.
 *  Kaynak: belgedeki `@page` kuralı (varsa JS margin'i ezer) — yoksa JS margin'i.
 *  Koşullu gruplar (bug-gate 2026-10-12, ÖLÇÜLDÜ): bu betik `emulateMedia("screen")` ile basar ⇒
 *  `@media print { @page {…} }` UYGULANMAZ (JS margin geçerli kalır), `@media screen|all { @page {…} }`
 *  UYGULANIR. Medya TÜRÜ (stil sayfası/`@media`/`@import`) `matchMedia` (emüle ekran) ile, `@supports`
 *  `CSS.supports` ile süzülür; `@layer` gibi koşulsuz gruplara girilir. Sözde sayfa
 *  (`@page :first|:left|:right|<ad>`) yalnız bazı sayfalara uygulanır ⇒ altbilgi HER sayfaya
 *  sığmalı ⇒ tabanla birlikte EN KÜÇÜĞÜ.
 *  ⛔ VIEWPORT'A BAĞLI MEDYA SORGUSU = MUHAFAZAKÂR (bug-gate 2. tur 2026-10-14, ÖLÇÜLDÜ): Chromium
 *  baskıda `width/height/orientation/aspect-ratio`'yu `evaluate` anındaki EKRAN viewport'una (1280 px)
 *  göre değil, sayfa kutusuna göre değerlendirir ⇒ `window.matchMedia` burada YANLIŞ cevap verir
 *  (eski sürüm: `@media (max-width: 900px) { @page { margin: 0 } }` baskıda uygulanırken 16 mm sanıp
 *  altbilgiyi gövdenin ÜSTÜNE bastırıyordu, sessiz; `(min-width: 1000px)` için sahte DURDU).
 *  Kural: medya metni viewport'a bağlı bir özellik içeriyorsa (VIEWPORT_OZELLIK_RE) grup "belirsiz"
 *  sayılır ve içindeki HER `@page` (seçicisiz olanlar da) HER İKİ dal için EN KÜÇÜĞE katılır ⇒
 *  margin'i yetmezse DURDU. Baskı kutusunu modellemek (iframe/ızgara) bilinçli REDDEDİLDİ (lider
 *  kararı 2026-10-14: yeni arıza yüzeyi — boyut özdenetimi, eşik toleransı, Chromium sürümü).
 *  Belirsizlik İÇ GRUPLARA YAYILIR: belirsiz bir stil sayfası/`@media`/`@import` içindeki `@media
 *  screen`, `@supports`, `@layer`, `@import` de belirsizdir (içlerindeki seçicisiz `@page` tabanı EZMEZ,
 *  en küçüğe katılır).
 *  ⛔ OKUNAMAYAN STİL SAYFASI / `@import` = MUHAFAZAKÂR DURDU (bug-gate 2. re-gate 2026-10-14, lider
 *  kararı; ÖLÇÜLDÜ): `file://` belgeden `<link href=…>` ve `@import url(…)` ile gelen sayfanın
 *  `cssRules`'ı `SecurityError` atar ⇒ içindeki `@page` görülemez (eski sürüm sessizce atlayıp
 *  js-margin sanıyordu; kural baskıda UYGULANIRKEN rc 0). Okunamayan her sayfa/import sayılır ve
 *  `--sayfa-no` DURDU verir ("@page margin'i OLCULEMEDI"). Medya TÜRÜ uymayan (`media="print"`)
 *  sayfa okunmadan atlanır (ekranda uygulanmaz). Var OLMAYAN dosyaya `<link>`/`@import` da aynı
 *  `SecurityError`'ı atar (ölçüldü) ⇒ o da DURDU verir (sahte ama yüksek sesli; ayırt edilemez).
 *  `data:` URL'li `@import` OKUNUR (ölçüldü) ⇒ normal yoldan gezilir.
 *  ⛔ ADOPTED STİL SAYFALARI (bug-gate 3. tur 2026-10-14, ÖLÇÜLDÜ): JS ile `document.adoptedStyleSheets`'e
 *  konan sayfanın `@page`'i baskıda UYGULANIR (taban ilk y 16.1 pt) ama eski sürüm onları hiç gezmiyordu
 *  (rc 0 `16.0mm (js-margin)`, sessiz). Şimdi aynı medya/belirsizlik mantığıyla gezilir, iz öneki
 *  `adopted>`. Seçicisiz `@page`'leri tabanı EZMEZ, en küçüğe katılır (muhafazakâr; kaskatta belge
 *  sayfalarından sonra geldikleri modellenmez ⇒ `<style>@page{margin:0}</style>` + adopted 20 mm
 *  sahte DURDU kalır). Shadow root'lar TARANMAZ (kapsam beyanında yazılır).
 *  SINIR: ① viewport sorgusu baskıdaki sonucundan bağımsız en küçüğe katılır ⇒ baskıda UYGULANMAYAN
 *  viewport sorgusu da (ör. `(min-width: 1000px)`, `print and (max-width: …)`) margin'i küçükse DURDU
 *  verir; baskıda uygulanan ama daha büyük değer veren ya da sırada sonraki koşulsuz kuralca ezilen
 *  viewport sorgusu da DURDU verir (iki dalın en küçüğü alınır; ör. `@page{margin:0} @media
 *  (max-width:900px){@page{margin:20mm}}` ve `@media (max-width:900px){@page{margin:0}}
 *  @page{margin:20mm}` — ikisinde de baskıdaki margin 20 mm). Sahte DURDU, bilinçli kabul edilen
 *  YÜKSEK SESLİ yön (sessiz kırpma değil); çare: o `@page`'i sorgudan çıkar ya da bayraksız üret.
 *  Okunamayan sayfa da margin'i yetse bile DURDU verir (aynı yön; çare: stili `<style>` içine göm).
 *  STİL SAYFASI KÜMESİ (title) SEÇİMİ modellenmez (bug-gate 3. tur 2026-10-14, ÖLÇÜLDÜ): baskıda
 *  uygulanmayan küme sayfası da okunur ⇒ `@page`'i küçükse ya da okunamıyorsa sahte DURDU — ör.
 *  `<link rel="alternate stylesheet" title=…>` (CSSOM `disabled` = false der) ve iki farklı `title`'lı
 *  `rel="stylesheet"`'in ikincisi. Rel/title'a bakıp atlamak YANLIŞ olurdu: `<meta http-equiv=
 *  "Default-Style">` alternate kümeyi seçerse kural baskıda UYGULANIR (taban ilk y 16.1 pt) ⇒ sessiz
 *  geçiş; doğrusu HTML tercih edilen küme algoritmasını modellemektir (reddedilen iframe ile aynı sınıf).
 *  ② `@page` içi `@bottom-*` kenar kutuları ve özgüllük/!important çakışması modellenmez (düz
 *  `@page` kurallarında belge sırasındaki SON değer alınır). */
async function altBoslukOlc(page, jsAltMm) {
  return await page.evaluate(([jsAlt, html, reKaynak]) => {
    const viewportRe = new RegExp(reKaynak, "i");
    const pxToMm = px => px * 25.4 / 96;
    const uzunlukMm = deger => {
      const d = document.createElement("div");
      d.style.cssText = "position:absolute;visibility:hidden;height:" + deger;
      document.body.appendChild(d);
      const h = d.getBoundingClientRect().height;
      d.remove();
      return pxToMm(h);
    };
    let sorgu = 0, viewportSay = 0;
    const okunamayan = [];   // cssRules'ı okunamayan stil sayfası / @import kaynakları (çapraz köken)
    // evet | hayir | belirsiz  (belirsiz = viewport'a bağlı: baskıdaki sonucu buradan bilinemez)
    const medyaKarar = m => {
      if (!m || !m.mediaText) return "evet";
      sorgu++;
      if (viewportRe.test(m.mediaText)) { viewportSay++; return "belirsiz"; }
      return window.matchMedia(m.mediaText).matches ? "evet" : "hayir";
    };
    const etiket = (ad, k, metin) => ad + (k === "belirsiz" ? "~" : "") + "(" + metin + ")>";
    let tabanAlt = null, kaynak = "js-margin";
    const sozde = [];
    const gez = (kurallar, iz, belirsiz) => {
      for (const r of Array.from(kurallar || [])) {
        if (r.type === 6 /* CSSRule.PAGE_RULE */ && r.style) {
          const mb = r.style.getPropertyValue("margin-bottom");
          if (!mb) continue;
          const sec = (r.selectorText || "").trim();
          if (sec || belirsiz) { sozde.push({ mm: uzunlukMm(mb), iz: iz + "@page" + (sec ? " " + sec : "") }); }
          else { tabanAlt = uzunlukMm(mb); kaynak = "css-" + iz + "@page"; }
        } else if (r.type === 4 /* MEDIA_RULE */) {
          const k = medyaKarar(r.media);
          if (k !== "hayir") gez(r.cssRules, iz + etiket("@media", k, r.media.mediaText), belirsiz || k === "belirsiz");
        } else if (r.type === 12 /* SUPPORTS_RULE */) {
          let ok = false;
          try { ok = CSS.supports(r.conditionText); } catch (e) { ok = false; }
          if (ok) gez(r.cssRules, iz + "@supports>", belirsiz);
        } else if (r.type === 3 /* IMPORT_RULE */) {
          const k = medyaKarar(r.media);
          if (k !== "hayir" && r.styleSheet) {
            try { gez(r.styleSheet.cssRules, iz + (k === "evet" ? "@import>" : etiket("@import", k, r.media.mediaText)),
                      belirsiz || k === "belirsiz"); }
            catch (e) { okunamayan.push("@import " + (r.href || "?")); }   // çapraz köken: ÖLÇÜLEMEDİ
          }
        } else if (r.cssRules) {
          gez(r.cssRules, iz, belirsiz);   // @layer vb. koşulsuz grup
        }
      }
    };
    // TARANAN YÜZEYLER (kapsam beyanı ALTBILGI satırında): document.styleSheets + document.adoptedStyleSheets
    // (JS ile `new CSSStyleSheet()`; iz öneki "adopted>"; seçicisiz @page'i tabanı EZMEZ, en küçüğe katılır).
    // Shadow root'ların adoptedStyleSheets'i / <style>'ı TARANMAZ (ölçülemedi ≠ temiz).
    const adopted = Array.from(document.adoptedStyleSheets || []);
    const yuzey = Array.from(document.styleSheets).map(ss => ["", ss]).concat(adopted.map(ss => ["adopted>", ss]));
    for (const [onek, ss] of yuzey) {
      if (ss.disabled) continue;
      const k = medyaKarar(ss.media);   // <style media="print"> ekran emülasyonunda uygulanmaz
      if (k === "hayir") continue;
      let kurallar;
      try { kurallar = ss.cssRules; }
      catch (e) { okunamayan.push(ss.href || "<style>"); continue; }   // çapraz-köken sayfa: ÖLÇÜLEMEDİ
      gez(kurallar, onek + (k === "evet" ? "" : etiket("<style media=", k, ss.media.mediaText)),
          k === "belirsiz" || onek === "adopted>");
    }
    let etkin = tabanAlt === null ? jsAlt : tabanAlt;
    for (const s of sozde) {
      if (s.mm < etkin) { etkin = s.mm; kaynak = "css-" + s.iz; }
    }
    const k = document.createElement("div");
    k.style.cssText = "position:absolute;visibility:hidden;left:0;top:0;width:180mm";
    k.innerHTML = html;
    document.body.appendChild(k);
    const altbilgi = pxToMm(k.getBoundingClientRect().height);
    k.remove();
    return { etkinMm: etkin, kaynak, altbilgiMm: altbilgi, medya: { sorgu, viewport: viewportSay }, okunamayan,
             adopted: adopted.length };
  }, [jsAltMm, ALTBILGI_HTML, VIEWPORT_OZELLIK_RE.source]);
}

/** Üretilen PDF'teki yer imi (outline) sayısı — `Outlines` sözlüğünün `/Count`'u (ham bayttan).
 *  Döner: sayı · Outlines yok ve sıkıştırılmış nesne akışı da yok → 0 · ölçülemedi → null
 *  (`/ObjStm` varsa sözlük akışın içinde olabilir; ölçüldü 2026-10-12: Chromium/Skia ObjStm
 *  YAZMIYOR, `/Type /Outlines … /Count 19` düz metinde). */
function pdfYerImiSayisi(yol) {
  const ham = fs.readFileSync(yol).toString("latin1");
  const m = /<<((?:(?!<<|>>)[\s\S])*?\/Type\s*\/Outlines\b(?:(?!<<|>>)[\s\S])*?)>>/.exec(ham);
  if (m) {
    const c = /\/Count\s+(-?\d+)/.exec(m[1]);
    return c ? Math.abs(parseInt(c[1], 10)) : 0;
  }
  return /\/ObjStm\b/.test(ham) ? null : 0;
}

/** Yer imi BAŞLIK METNİ için hazırlık (yalnız --yer-imi).
 *  ⛔ ÖLÇÜLDÜ (2026-10-12): Chromium yer imi başlığını YERLEŞİM metninden üretir; birden çok
 *  satıra kayan bir başlıkta kayma noktasındaki boşluk düşer ("Şık Doküman" → "ŞıkDoküman").
 *  `aria-label` bu başlığı DEĞİŞTİRMEZ (denendi). `white-space:pre-wrap` satır sonundaki boşluğu
 *  "asılı" tutar ⇒ boşluk metne girer, kırılma noktaları aynı kalır. Ama pre-wrap baştaki
 *  boşluğu / kaynak içi satır sonunu da GÖRÜNÜR kılabilir ⇒ her başlıkta satır kutuları
 *  (sol, üst, yükseklik) iki genişlikte önce/sonra ölçülür; değişen başlıkta geri alınır
 *  (o başlığın yer iminde boşluk düşebilir — sayısı raporlanır, gövde yerleşimi korunur). */
async function basliklariHazirla(page) {
  return await page.evaluate(() => {
    // İMZA = boşluk OLMAYAN her karakterin (üst, sol) konumu + başlık kutusunun yüksekliği.
    // Boşluk karakterleri bilinçli dışarıda: asılı satır-sonu boşluğu ayrı rect üretir
    // (ölçüldü: rect-kıyası her satıra kayan başlığı "değişti" sayıp düzeltmeyi geri alıyordu);
    // baştaki boşluk / kaynak içi satır sonu ise sonraki GÖRÜNÜR karakteri kaydırır ⇒ yakalanır.
    const kutular = el => {
      const s = [];
      const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const r = document.createRange();
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        for (let i = 0; i < n.data.length; i++) {
          if (/\s/.test(n.data[i])) continue;
          r.setStart(n, i); r.setEnd(n, i + 1);
          const x = r.getBoundingClientRect();
          s.push(Math.round(x.top) + "," + Math.round(x.left));
        }
      }
      return Math.round(el.getBoundingClientRect().height) + "|" + s.join(";");
    };
    const kok = document.documentElement;
    const eskiGenislik = kok.style.width;
    const olc = el => {
      const s = [];
      for (const g of ["", "120mm"]) { kok.style.width = g; s.push(kutular(el)); }
      kok.style.width = eskiGenislik;
      return s.join("|");
    };
    let toplam = 0, uygulanan = 0, geri = 0;
    for (const h of document.querySelectorAll("h1,h2,h3,h4,h5,h6")) {
      toplam++;
      const once = olc(h);
      const eski = h.style.whiteSpace;
      h.style.whiteSpace = "pre-wrap";
      if (olc(h) === once) { uygulanan++; } else { h.style.whiteSpace = eski; geri++; }
    }
    return { toplam, uygulanan, geri };
  });
}

(async () => {
  const fileUrl = "file:///" + IN.split(path.sep).join("/");
  const b = await chromium.launch({ channel: "msedge", headless: true, args: ["--no-sandbox"] });
  const p = await (await b.newContext()).newPage();
  await p.goto(fileUrl, { waitUntil: "networkidle", timeout: 60000 });
  await p.emulateMedia({ media: "screen" });
  // ⛔ Bayraksız seçenek nesnesi ESKİSİYLE BİREBİR (Q366 zorunlu önlemi: varsayılan çıktı değişmez).
  const opts = { path: OUT, format: "A4", printBackground: true, margin: { top: "14mm", bottom: "16mm", left: "12mm", right: "12mm" } };
  if (BAYRAK.has("--sayfa-no")) {
    const o = await altBoslukOlc(p, 16);
    const gerek = o.altbilgiMm + ALTBILGI_PAY_MM;
    const okn = o.okunamayan.length;
    // KAPSAM BEYANI: "(muhafazakar)" yalnız viewport sorgusu VARKEN ve okunamayan grup YOKKEN basılır
    // (0 sorguda muhafazakârlık yoktur; okunamayan grup varken ölçüm muhafazakâr değil EKSİKTİR).
    console.log("ALTBILGI: etkin alt bosluk " + o.etkinMm.toFixed(1) + "mm (" + o.kaynak +
                "), altbilgi " + o.altbilgiMm.toFixed(1) + "mm + pay " + ALTBILGI_PAY_MM + "mm" +
                " | medya " + o.medya.sorgu + " sorgu, " + o.medya.viewport + " viewport'a bagli" +
                (o.medya.viewport > 0 && okn === 0 ? " (muhafazakar)" : "") +
                " | okunamayan stil sayfasi/import " + okn +
                " | adoptedStyleSheets " + o.adopted + " | shadow root TARANMADI");
    if (okn > 0) {
      await b.close();
      console.error("[DURDU] --sayfa-no: stil sayfasi okunamadi (" + okn + " kaynak: " +
                    o.okunamayan.slice(0, 3).join(", ") + (okn > 3 ? ", …" : "") + "), @page margin'i OLCULEMEDI " +
                    "(muhafazakar: okunamayan sayfa baskida @page margin'ini degistirebilir, altbilgi KIRPILABILIRDI). " +
                    "Stili <style> icine gom ya da bayraksiz uret.");
      process.exit(2);
    }
    if (!(o.etkinMm >= gerek)) {
      await b.close();
      // "~(" = viewport'a bağlı medya sorgusu grubu (altBoslukOlc etiketi)
      const vp = o.kaynak.includes("~(") ? " Kaynak VIEWPORT'A BAGLI medya sorgusu (muhafazakar): baskida uygulanip " +
                 "uygulanmadigi ekran viewport'undan bilinemez, en kucuk deger alindi." : "";
      console.error("[DURDU] --sayfa-no: etkin alt bosluk " + o.etkinMm.toFixed(1) + "mm < gereken " +
                    gerek.toFixed(1) + "mm (" + o.kaynak + ")." + vp + " Altbilgi KIRPILIRDI; govdeyi daraltmamak icin " +
                    "margin degistirilmez. Belgenin @page margin-bottom degerini buyut ya da bayraksiz uret.");
      process.exit(2);
    }
    opts.displayHeaderFooter = true;
    opts.headerTemplate = "<span></span>";   // boş üst bilgi (varsayılan tarih/başlık basılmasın)
    opts.footerTemplate = ALTBILGI_HTML;
  }
  let yerImi = null;
  if (BAYRAK.has("--yer-imi")) {
    yerImi = await basliklariHazirla(p);
    const y = yerImi;
    console.log("YER-IMI: " + y.toplam + " baslik; satir-kaydirma boslugu korundu: " + y.uygulanan +
                ", geri alindi (yerlesim degisirdi): " + y.geri);
    opts.outline = true;   // başlıklardan PDF yer imi (Chromium; etiketli PDF ister)
    opts.tagged = true;
  }
  await p.pdf(opts);
  await b.close();
  if (yerImi) {
    // Üretim SONRASI denetim (bug-gate 2026-10-12 önerisi): "outline: true" vermek yer imi
    // üretildiğinin kanıtı değil — PDF'in kendisinden sayılır. Uyarıdır, çıkış kodu değişmez.
    const n = pdfYerImiSayisi(OUT);
    if (n === null) {
      console.error("⚠ YER-IMI OLCULEMEDI: PDF sikistirilmis nesne akisi (ObjStm) tasiyor — sayi okunamadi");
    } else {
      console.log("YER-IMI PDF: " + n + " yer imi / " + yerImi.toplam + " baslik");
      if (n === 0 && yerImi.toplam > 0) {
        console.error("⚠ UYARI --yer-imi: PDF'te YER IMI YOK (" + yerImi.toplam + " baslik vardi) — " +
                      "Chromium/Playwright surumu outline desteklemiyor olabilir");
      } else if (n !== yerImi.toplam) {
        console.error("⚠ UYARI --yer-imi: yer imi sayisi (" + n + ") baslik sayisindan (" + yerImi.toplam +
                      ") farkli — bos/gizli baslik ya da kapali dal olabilir, PDF'i kontrol et");
      }
    }
  }
  console.log("PDF OK:", OUT);
})().catch(e => { console.error("ERR", e); process.exit(1); });

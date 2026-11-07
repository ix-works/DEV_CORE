/** HTML → PDF (Edge, page.pdf). Kullanım:
 *   node scripts/html_to_pdf.js <input.html> <output.pdf> [--sayfa-no] [--yer-imi]
 * KD/FS/TS markdown→HTML (build_kd_pdf.py / build_doc_pdf.py) çıktısını şık A4 PDF'e çevirir.
 *
 * ÇIKIŞ: 0 PDF yazıldı (`PDF OK` yalnız yerleşim temizken; kalan taşma/kırpıkta `PDF UYARILI` + stderr
 *   `⚠ UYARI YERLESIM`) · 1 hata (ERR) · 2 [KULLANIM] / [DURDU] (dizin listesi açıldı · --sayfa-no eşiği).
 * ⚠ Git Bash (MSYS): `/` ile başlayan ARGÜMAN (ör. üreticinin başlığı "/NS/ZSD001 …") Windows yolu
 *   sanılıp dönüştürülür ("C:/Program Files/Git/NS/ZSD001 …"; ölçüldü). Çağrının önüne
 *   `MSYS_NO_PATHCONV=1` koy (PowerShell/cmd'de gerekmez). Kod bunu düzeltmez — argüman süreçten önce bozulur.
 *
 * OPT-IN BAYRAKLAR (Q366, 2026-10-12) — bayraksız page.pdf SEÇENEKLERİ eskisiyle aynıdır; Issue #389'dan
 * beri bayraktan bağımsız YERLEŞİM düzeltmesi uygulanır (aşağıdaki blok; yalnız taşan/kırpık öğeye ve
 * taşan tabloya dokunur — neyin ölçüldüğü ve sınırı orada):
 *   --sayfa-no  her sayfanın alt boşluğuna "Sayfa X / Y" (yalnız METİN; footerTemplate).
 *   --yer-imi   başlık hiyerarşisinden (h1..h6) PDF yer imleri (Playwright `outline`).
 *
 * ⛔ ALTBİLGİ GÖVDEYİ DARALTMAZ: altbilgi MEVCUT alt boşluğa yerleşir, margin değiştirilmez
 *    ⇒ sayfa sayısı ve tablo bölünmesi bayraklı/bayraksız AYNI kalır. Bunun bedeli: alt
 *    boşluk altbilgiye yetmiyorsa altbilgi kırpılır/görünmez — o yüzden ETKİN alt boşluk
 *    belgeden ÖLÇÜLÜR (sabit varsayılmaz) ve yetmiyorsa SESSİZ değil exit 2. Gereken boşluk =
 *    altbilginin sayfa altından uzaklığı (ALTBILGI_ALT_IC_MM, ölçülmüş sabit) + altbilgi yüksekliği
 *    (AYRI sayfada ölçülür, belge CSS'i dokunamaz) + pay (Issue #360). PDF yazmadan çıkılırken hedefte
 *    önceki bir PDF varsa stderr'e UYARI basılır (dosya silinmez). Uyarının KAPSAMADIĞI çıkışlar
 *    (uyarısız; hedef dosya olduğu gibi kalır): `[KULLANIM]` exit 2 (bilinmeyen bayrak / yanlış argüman
 *    sayısı; OUT henüz çözülmemiştir) ve modül düzeyindeki `require(resolvePlaywrightCore())` hatası
 *    (playwright-core yok → Node'un kendi hatası, `catch` dalına girilmez).
 *    Ölçülen tuzaklar (bu evde iki kez):
 *    · CSS `@page { margin: … }` page.pdf'e verilen JS margin'i SESSİZCE ezer
 *      (build_doc_pdf/build_kd_pdf CSS'i `@page` margin TAŞIR ⇒ etkin boşluk CSS'inkidir).
 *    · footerTemplate ZEMİN BOYAMAZ (mürekkep yalnız border+metin) ⇒ altbilgi yalnız metin.
 *    · footerTemplate kendi yazı boyutunu açıkça ister (varsayılan neredeyse görünmez).
 *    · `<thead>` tekrarı bu yolda çalışmaz — altbilgi için kullanılmadı.
 */
/*
 * YERLEŞİM DÜZELTMESİ (DEV_CORE Issue #389, 2026-11-07) — HER koşumda, bayraktan bağımsız.
 * ⚠ Q366'nın "bayraksız çıktı eskisiyle aynı" kuralı DARALDI (kullanıcı onayı): page.pdf SEÇENEK
 *   NESNESİ hâlâ eskisiyle BİREBİR (S1); ama belge, basılmadan önce yalnız-PDF CSS'i alır. Bu CSS'in
 *   `body` dışındaki HER kuralı `data-ix-pdf-sar` işaretli öğeye/tabloya bağlıdır (pdf_yerlesim S2) ve
 *   işaret yalnız baskı genişliğinde TAŞAN (görsel, `pre` içeriği, tablo) ya da KIRPIK (`pre`) öğeye
 *   konur ⇒ taşan/kırpık öğesi olmayan belgede işaret 0, geriye `body{overflow-wrap:break-word}` kalır.
 *   ÖLÇÜLEN (taban kıyası, sayfa sayfa metin + görsel kutusu): sığan tablo (pdf_yerlesim Y5k ikon/uzun
 *   metin Y9, hücre içi `pre` Y10) · öznitelik oranı bozuk sığan görsel Y11 · pdf_sayfa_no_yer_imi P1/P3.
 *   ÖLÇÜLMEDİ/SINIR: kendi dar kutusundan taşan ama sayfaya taşmayan bölünmeyen sözcük `break-word` ile
 *   kırılır (sayfadan taşan öğe yoktur ama yerleşim değişir). Taşan öğesi olan belgede çıktı bilinçli
 *   olarak DEĞİŞİR (kullanıcı onayı) — ama yalnız işaretli öğede; aynı belgedeki sığan tablo değişmez.
 *   Önceki metin (2458c17) "taşan öğesi OLMAYAN belgede çıktı aynıdır" diyordu; global `img`/`pre`
 *   kuralı sığan tablonun sütunlarını değiştirdiği için yanlıştı (bug-gate F1).
 * Ölçülen kusurlar (f646f36): ① yol `"file:///" + IN` ile kuruluyordu ⇒ klasör adındaki `#` URL
 *   parçası sayılıp yolu kesiyordu; Edge kesik yolun DİZİN LİSTESİNİ basıyordu ve araç `PDF OK`
 *   diyordu (sessiz). Şimdi `url.pathToFileURL` + açılan sayfa dizin listesiyse exit 2.
 *   ② `max-width` yalnız `figure img`'deydi: başlık satırı olmayan görsel taşıyordu. ③ geniş `pre`
 *   (`white-space:pre`) kırpılıyordu (190 karakterin 105'i basıldı). ④ tablo hücresindeki bölünmeyen
 *   satır içi kod tabloyu sayfadan taşırıyordu. Chromium baskıda sayfadan taşan içerik görünce
 *   BÜTÜN belgeyi küçültür (ölçüldü: gövde 10,5 pt → 7,0 pt; bir tüketici korpusunda 75 PDF'in
 *   43'ünde en sık punto < 9,5).
 * ⛔ CSS YERİ = BURASI, üreticinin CSS'i DEĞİL: `emulateMedia("screen")` ⇒ `@media print` kuralı
 *   PDF'e HİÇ ulaşmaz; üretici CSS'ine düz kural yazmak ekran HTML'ini (uygulama içi yardım) da
 *   değiştirirdi. Burada `addStyleTag` iki üreticiyi + diskteki ESKİ HTML'leri tek yerde kapsar.
 * ⛔ `img`/`pre`/tablo kuralı GLOBAL VERİLMEZ (bug-gate F1, ÖLÇÜLDÜ): `overflow-wrap:anywhere`,
 *   `white-space:pre-wrap` ve yüzdeli `max-width` hücrenin min-content'ini küçültür ⇒ SIĞAN (100 %'lük)
 *   tabloların sütun dağılımını da değiştirir (ikon 195 → 43,6 pt; hücredeki `pre` "SELEC|T *" diye
 *   bölündü). `height:auto` global verilse öznitelik oranı bilinçli farklı sığan görseli de düzeltirdi.
 *   Bu yüzden: tablo hücresi DIŞINDA taşan görsel / taşan ya da kırpık `pre` öğe bazında işaretlenir;
 *   hücre içindekiler yalnız TAŞAN tablonun kademesiyle sarılır — 1. kademe hücre içi `code` + `pre`,
 *   hâlâ taşıyorsa 2. kademe hücre içi `img` (`max-width` + `height:auto`), hâlâ taşıyorsa 3. kademe tüm
 *   hücre. Görselde `height:auto` ŞART: yalnız `max-width` + `width`/`height` öznitelikleri en-boy oranını
 *   bozar (1200×300 → 516×225, oran 4,0 → 2,29; F3).
 *   `body{overflow-wrap:break-word}` min-content'i DEĞİŞTİRMEZ (CSS Text 3) ⇒ global verilebilir.
 */
const path = require("path");
const fs = require("fs");
const os = require("os");
const url = require("url");
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
// Altbilgi satır kutusunun ALT kenarı ile sayfanın alt kenarı arasındaki mesafe (mm). GEREKEN alt
// boşluk = ALTBILGI_ALT_IC_MM + altbilgi yüksekliği + ALTBILGI_PAY_MM (Issue #360, 2026-10-19).
// Neden: Chromium footerTemplate'i alt boşluğun BOYUNDAN BAĞIMSIZ, sayfa altından sabit bir yükseklikte
// çizer. Eski eşik (altbilgi + pay) bu mesafeyi saymıyordu ⇒ 6–11 mm alt boşlukta rc 0 ama "Sayfa X / Y"
// gövdenin son satırına biniyordu (ölçüldü: 6 ve 9 mm'de metin kutuları kesişiyor, 11 mm'de aralık < 2 mm).
// ÖLÇÜM TARİFİ (sabit değişirse yeniden koş): `@page{margin:10mm 10mm <N>mm 10mm}` + `html,body{height:100%}`
// + gövde flex `justify-content:flex-end` (son satır dipte) → `--sayfa-no` PDF'i → PyMuPDF
// `search_for("Sayfa 1 / 1")` metin kutusunun sayfa altına uzaklığı:
//   · N = 6 / 18 / 30 mm, 8 pt  → kutu alt 5.34 mm, üst 9.09 mm (N'den BAĞIMSIZ)
//   · 4 / 16 / 24 pt (N 18/18/40) → alt 5.16 / 5.16 / 5.24 mm · line-height:3 → alt 7.72 mm
//     (satır kutusu 8.47 mm, metin ortalı ⇒ kutunun alt kenarı ≈ 5.36 mm)
//   ⇒ satır kutusunun alt kenarı ≈ 5.2–5.4 mm'de sabit; üstü = 5.3 + kutu yüksekliği (8 pt'de 5.3 + 4.0 =
//     9.3 mm ≥ ölçülen metin üstü 9.09 mm — muhafazakâr yön).
// ⚠ ÖLÇÜLEN ORTAM: Windows 11 + msedge 155.0.4283.62 + playwright-core 1.62.0-alpha. Linux / Chrome /
//   başka Chromium sürümünde değer ÖLÇÜLMEDİ (CI tarayıcı kurmaz; fixture P*-satırları orada ATLANDI).
const ALTBILGI_ALT_IC_MM = 5.3;

// Viewport'a bağlı medya özellikleri (min-/max-/device-/aralık sözdizimi dahil — alt dizge eşleşir).
const VIEWPORT_OZELLIK_RE = /(?:width|height|aspect-ratio|orientation|resolution|pixel-ratio)/i;

/** Belgenin ETKİN alt boşluğunu (mm) ölçer (altbilginin yüksekliği AYRI sayfada: `altbilgiOlc`).
 *  Kaynak: belgedeki `@page` kuralı (varsa JS margin'i ezer) — yoksa JS margin'i.
 *  ⛔ UZUNLUK ÖLÇÜMÜ BELGE CSS'İNDEN YALITILIR (Issue #360 kardeşi, 2026-10-19, ÖLÇÜLDÜ): `@page`
 *  margin değeri eskiden `document.body`'ye eklenen bir div'in yüksekliğiyle mm'ye çevriliyordu ⇒ belge
 *  CSS'i o div'e de uyuyordu: `div{padding:20px !important}` 5 mm'yi 15.6 mm, `body{zoom:3}` 5 mm'yi
 *  15 mm yapıyordu (baskıda ikisi de 5 mm — sessiz geçiş yönü), `2em` gövde yazı boyutuna göre
 *  çözülüyordu (`body{font-size:30px}` → 15.9 mm; baskıda 8.5 mm). Baskı ÖLÇÜMÜ (taban betik, dipteki
 *  satır): `@page` uzunluğu KÖK elemana göre çözülür — `em`/`rem` = html yazı boyutu, `html{zoom}`
 *  margin'i ölçekler (20 mm × 0.5 → 9.7), `body{zoom}` ölçeklemez. Şimdi ölçüm elemanı KÖKÜN (html)
 *  çocuğu olan bir gölge kökte: `:host{all:initial !important; font:inherit !important}` + iç div
 *  `all:initial` + `font:inherit` (iki katmanda da), yükseklik satır içi `!important` ⇒ belge kuralları
 *  dokunamaz (gölge-içi `!important` belge `!important`'ını yener), kökün yazı tipi ve zoom'u geçer.
 *  ⛔ `font:inherit`, `font-size:inherit` DEĞİL (bug-gate 2026-10-27, ÖLÇÜLDÜ): yalnız yazı boyutu miras
 *  alınırsa satır yüksekliği ve yazı ailesi başlangıç değerine döner ⇒ `lh`/`ex`/`ch` yanlış ölçülür.
 *  `html{line-height:0.5}` + `3lh` → 14.3 mm sanıp rc 0, baskıda 6.0 mm, altbilgi son satıra -4.2 mm
 *  biner (sessiz). Ters yön, yani sahte DURDU: `html{line-height:3}` + `3lh` 14.3/37.8 mm,
 *  Courier + `8ch` 16.9/20.1 mm, Impact + `6ex` 11.4/16.1 mm.
 *  Belge zoom'u gölge köke SIZMAZ (`html > *{zoom:3 !important}` + 6 mm → 6.0 mm, baskı 5.8; ölçüldü).
 *  `%` eski davranışla AYNI (host = 100vh ⇒ ekran viewport yüksekliğinin yüzdesi; baskıdaki anlamı
 *  modellenmez). `html{transform}` gibi baskı yerleşimini bozan belgeler modellenmez. CSP'li belge
 *  (`style-src` gölge kökteki `<style>`'ı engeller) yalıtımı DÜŞÜRÜR, modellenmez (bug-gate
 *  2026-10-27, ÖLÇÜLDÜ: `style-src 'sha256-…'` + `html > *{zoom:3 !important}` + 6 mm → 18.0 mm, rc 0;
 *  eski araç da aynı — regresyon değil; çekirdek üreteçlerinin HTML'i CSP taşımaz).
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
  return await page.evaluate(([jsAlt, reKaynak]) => {
    const viewportRe = new RegExp(reKaynak, "i");
    const pxToMm = px => px * 25.4 / 96;
    const uzunlukMm = deger => {
      const h = document.createElement("ix-uzunluk-olcum");
      const s = h.attachShadow({ mode: "closed" });
      s.innerHTML = "<style>:host{all:initial !important;font:inherit !important;display:block !important;" +
        "position:absolute !important;visibility:hidden !important;left:0 !important;top:0 !important;" +
        "width:0 !important;height:100vh !important}" +
        "div{all:initial !important;display:block !important;font:inherit !important}</style><div></div>";
      const d = s.querySelector("div");
      d.style.setProperty("height", deger, "important");   // satır içi: değer metni HTML'e gömülmez
      document.documentElement.appendChild(h);
      const v = d.getBoundingClientRect().height;
      h.remove();
      return pxToMm(v);
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
    return { etkinMm: etkin, kaynak, medya: { sorgu, viewport: viewportSay }, okunamayan,
             adopted: adopted.length };
  }, [jsAltMm, VIEWPORT_OZELLIK_RE.source]);
}

/** Altbilgi şablonunun yüksekliği (mm) — verilen sayfanın gövdesinde, A4 genişliğinde ölçülür.
 *  ⛔ ÇAĞIRAN AYRI, BOŞ bir sayfa verir (Issue #360, 2026-10-19, ÖLÇÜLDÜ): Chromium altbilgiyi belgeden
 *  AYRI bir bağlamda çizer — belge CSS'i ona ulaşmaz (PDF'te altbilgi metin kutusu her durumda 3.75 mm).
 *  Eski sürüm ölçümü belgenin kendi gövdesinde yapıyordu ⇒ `div{padding:20px !important}` 25.1 mm,
 *  `*{font-size:40pt !important;line-height:3 !important}` 42.3 mm (sahte DURDU), `*{font-size:2pt
 *  !important;line-height:0.2 !important}` 0.1 mm, `html{zoom:0.2}` 0.8 mm (sessiz geçiş yönü).
 *  Issue'nun önerdiği gölge kök + `:host{all:initial !important}` de ÖLÇÜLDÜ ve YETMEDİ: ataların
 *  `zoom`'u (`html{zoom:0.2}` → 0.79 mm) ve `display:none`'ı (`*{display:none !important}` → 0) gölge
 *  kökü de etkiler. Ayrı sayfada (aynı tarayıcı ⇒ aynı fontlar) tüm bu vakalarda 3.97 mm. */
async function altbilgiOlc(sayfa) {
  return await sayfa.evaluate(html => {
    const k = document.createElement("div");
    k.style.cssText = "position:absolute;visibility:hidden;left:0;top:0;width:210mm";
    k.innerHTML = html;
    document.body.appendChild(k);
    const h = k.getBoundingClientRect().height * 25.4 / 96;
    k.remove();
    return h;
  }, ALTBILGI_HTML);
}

/** Bu koşu PDF YAZMADAN çıkarken (DURDU exit 2 · hata exit 1) hedefte ÖNCEKİ bir dosya duruyorsa
 *  stderr'e uyarır (Issue #360, 2026-10-19). Dosya SİLİNMEZ (kullanıcının önceki çıktısıdır); ama
 *  uyarısız bırakılırsa "PDF orada" görüntüsü bu koşunun çıktısı sanılır (ölçüldü: `@page` alt 4 mm +
 *  hedefte eski d.pdf → rc 2, d.pdf "eski" içerikle kaldı, tek satır uyarı yoktu). */
function eskiPdfUyar() {
  if (fs.existsSync(OUT)) {
    console.error("⚠ UYARI: hedefte ONCEKI bir PDF duruyor ve bu kosu onu YAZMADI: " + OUT +
                  " — o dosya bu kosunun ciktisi DEGILDIR (silinmedi).");
  }
}
let PDF_YAZILDI = false;

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

/** Açılan sayfa Chromium'un DİZİN LİSTESİ mi (Issue #389 ①). Ölçüldü (Edge 155): liste sayfası
 *  `#parentDirLinkBox` + `#tbody` + global `addRow()` taşır; başlık "Index of …" (yerele bağlı olabilir ⇒
 *  başlık TEK BAŞINA ölçüt değil: "Index of" başlıklı gerçek belge listelenmez). */
async function dizinListesiMi(page) {
  return await page.evaluate(() => ({
    liste: !!document.getElementById("parentDirLinkBox") && !!document.getElementById("tbody") &&
           typeof window.addRow === "function",
    baslik: document.title,
  }));
}

/** Girdi yolunun `file:` URL'i (Issue #389 ①). `url.pathToFileURL`: `#`, `%`, `?`, boşluk ve Türkçe harf
 *  kodlanır (eski elle birleştirme `#`'tan sonrasını URL parçası sayıyordu).
 *  ⛔ `\\localhost\…` UNC (bug-gate F4, ÖLÇÜLDÜ node 24): `pathToFileURL` `file://localhost/…` kurar, WHATWG
 *  ayrıştırıcısı `file:` şemasında `localhost` host'unu BOŞALTIR ⇒ `file:///C$/…` (paylaşım adı yerel yol
 *  sanılır, `ERR_FILE_NOT_FOUND`; f646f36'nın elle birleştirmesi bu yolu açıyordu ⇒ regresyon). Çare yalnız
 *  bu host'a dardır: `localhost` → `127.0.0.1` (aynı makine, SMB; host korunur). `\\?\UNC\localhost\…`
 *  aynı sınıftır. Başka host (`\\srv\…`, `\\127.0.0.1\…`, `\\localhost.\…`) ve yerel yol DEĞİŞMEZ. */
const LOCALHOST_UNC_RE = /^(\\\\(?:\?\\UNC\\)?)localhost(?=\\)/i;
function dosyaUrl(yol) {
  return url.pathToFileURL(yol.replace(LOCALHOST_UNC_RE, (m, onek) => onek + "127.0.0.1")).href;
}

// Yalnız PDF'e giden CSS (ekran HTML'i değişmez). Belge, daha yüksek özgüllüklü kendi kuralıyla ezebilir
// (ör. satır içi `style="white-space:pre"`); ezilen öğe aşağıdaki YERLESIM ölçümünde kalan taşma olarak sayılır.
// `body` dışındaki her seçici `data-ix-pdf-sar` işaretine bağlıdır: işareti `yerlesimOlc` yalnız taşan/kırpık
// öğeye ve taşan tabloya koyar (seçici listesi satır satır: mutasyon çapaları tek eşleşmeli).
const PDF_CSS =
  "img[data-ix-pdf-sar]," +
  "table:is([data-ix-pdf-sar=\"2\"],[data-ix-pdf-sar=\"3\"]) :is(td,th) img{max-width:100%;height:auto}" +
  "pre[data-ix-pdf-sar]," +
  "table[data-ix-pdf-sar] :is(td,th) pre{white-space:pre-wrap;overflow-wrap:anywhere}" +
  "body{overflow-wrap:break-word}" +
  "table[data-ix-pdf-sar] :is(td,th) code{overflow-wrap:anywhere}" +
  "table[data-ix-pdf-sar=\"3\"] :is(td,th){overflow-wrap:anywhere}";
const SAYFA_GENISLIK_MM = 210;   // format "A4" (preferCSSPageSize verilmez ⇒ CSS `size` geçersiz)

/** Baskı genişliğinde taşan / kırpık öğeleri sayar; `duzelt` ise önce tablo hücresi dışındaki taşan
 *  görsele / taşan ya da kırpık `pre`'ye öğe işareti, sonra taşan tablolara kademeli (1 kod+pre · 2 görsel
 *  · 3 tüm hücre) sarma işareti koyar (`data-ix-pdf-sar`; PDF_CSS yalnız işaretliye uygulanır). Baskı genişliği = A4 − yan boşluk; yan boşluk = JS margin ile belgedeki HER `@page`
 *  kuralının (koşullu gruplar dahil, koşulu DEĞERLENDİRİLMEDEN) sol+sağ toplamının EN BÜYÜĞÜ
 *  (muhafazakâr: dar genişlik ⇒ fazla işaret/uyarı, sessiz taşma değil). Mutlak olmayan birim
 *  (`em`/`%`) ve okunamayan stil sayfası ölçülmez, sayısı beyanda yazılır. Ölçüm kökün genişliği
 *  geçici olarak baskı genişliğine çekilerek yapılır (`basliklariHazirla` ile aynı yöntem), sonra
 *  geri alınır. Taşan = sağ kenarı sınırı aşan, kırpan atası olmayan EN DIŞTAKİ öğe (Chromium
 *  bunu görünce belgeyi küçültür); kırpık = `overflow-x` görünür değilken içeriği sığmayan öğe
 *  (baskıda içerik kesilir). TARANMAYAN: shadow root, iframe, sola taşma. */
async function yerlesimOlc(page, duzelt) {
  return await page.evaluate(([sayfaMm, jsSol, jsSag, duz]) => {
    const BIRIM = { mm: 1, cm: 10, in: 25.4, pt: 25.4 / 72, pc: 25.4 / 6, px: 25.4 / 96, q: 0.25 };
    const mmYap = v => {
      const m = /^\s*(-?[\d.]+)\s*(mm|cm|in|pt|pc|px|q)\s*$/i.exec(v || "");
      return m ? parseFloat(m[1]) * BIRIM[m[2].toLowerCase()] : null;
    };
    let yan = jsSol + jsSag, yanKaynak = "js-margin", birimsiz = 0, okunamaz = 0;
    const sayfaKurallari = kurallar => {
      for (const r of Array.from(kurallar || [])) {
        if (r.type === 6 /* PAGE_RULE */ && r.style) {
          const sl = r.style.getPropertyValue("margin-left"), sg = r.style.getPropertyValue("margin-right");
          if (!sl && !sg) continue;
          const a = sl ? mmYap(sl) : jsSol, c = sg ? mmYap(sg) : jsSag;
          if (a === null || c === null) { birimsiz++; continue; }
          if (a + c > yan) { yan = a + c; yanKaynak = "css-@page" + (r.selectorText ? " " + r.selectorText : ""); }
        } else if (r.type === 3 /* IMPORT_RULE */) {
          try { sayfaKurallari(r.styleSheet && r.styleSheet.cssRules); } catch (e) { okunamaz++; }
        } else if (r.cssRules) {
          sayfaKurallari(r.cssRules);
        }
      }
    };
    for (const ss of Array.from(document.styleSheets).concat(Array.from(document.adoptedStyleSheets || []))) {
      try { sayfaKurallari(ss.cssRules); } catch (e) { okunamaz++; }
    }
    const genislikMm = sayfaMm - yan;
    const W = genislikMm * 96 / 25.4;
    const kok = document.documentElement, eskiKokGenislik = kok.style.width;
    kok.style.width = W + "px";
    const sinir = () => kok.getBoundingClientRect().left + W + 1;
    const kirpanAta = e => {
      for (let a = e.parentElement; a && a !== kok; a = a.parentElement) {
        if (getComputedStyle(a).overflowX !== "visible") return true;
      }
      return false;
    };
    const ogeler = () => Array.from(document.body ? document.body.querySelectorAll("*") : []);
    const tasanlar = () => {
      const L = sinir();
      return ogeler().filter(e => {
        const R = e.getBoundingClientRect();
        if (!(R.right > L) || (R.width === 0 && R.height === 0)) return false;
        const ust = e.parentElement;
        if (ust && ust !== document.body && ust.getBoundingClientRect().right > L) return false;   // en dıştaki
        return !kirpanAta(e);
      });
    };
    const kirpiklar = () => ogeler().filter(e => getComputedStyle(e).overflowX !== "visible" &&
                                                 e.scrollWidth > e.clientWidth + 1);
    // Öğe işareti (tablo hücresi DIŞI): sayfadan taşan görsel · içeriği sayfadan taşan ya da kırpık `pre`.
    // Hücre içindekiler işaretlenmez — onlar taşan tablonun kademesine girer (sığan tablo değişmesin).
    const icerikSag = e => { const r = document.createRange(); r.selectNodeContents(e); return r.getBoundingClientRect().right; };
    const kirpik = e => getComputedStyle(e).overflowX !== "visible" && e.scrollWidth > e.clientWidth + 1;
    let isGorsel = 0, isPre = 0;
    if (duz) {
      const L = sinir();
      const adaylar = Array.from(document.querySelectorAll("img,pre")).filter(e => !e.closest("td,th"));
      for (const e of adaylar) {
        const gorsel = e.tagName === "IMG";
        const tasar = (gorsel ? e.getBoundingClientRect().right : icerikSag(e)) > L && !kirpanAta(e);
        if (tasar || (!gorsel && kirpik(e))) { e.setAttribute("data-ix-pdf-sar", "1"); if (gorsel) isGorsel++; else isPre++; }
      }
    }
    let kademe1 = 0, kademe2 = 0, kademe3 = 0;
    if (duz) {
      for (const t of document.querySelectorAll("table")) {
        if (t.getBoundingClientRect().right > sinir()) { t.setAttribute("data-ix-pdf-sar", "1"); kademe1++; }
      }
      for (const t of document.querySelectorAll('table[data-ix-pdf-sar="1"]')) {
        if (t.getBoundingClientRect().right > sinir()) { t.setAttribute("data-ix-pdf-sar", "2"); kademe2++; }
      }
      for (const t of document.querySelectorAll('table[data-ix-pdf-sar="2"]')) {
        if (t.getBoundingClientRect().right > sinir()) { t.setAttribute("data-ix-pdf-sar", "3"); kademe3++; }
      }
    }
    const say = arr => {
      const m = {};
      for (const e of arr) { const k = e.tagName.toLowerCase(); m[k] = (m[k] || 0) + 1; }
      return Object.keys(m).sort().map(k => k + " " + m[k]).join(", ");
    };
    const ta = tasanlar(), ki = kirpiklar();
    kok.style.width = eskiKokGenislik;
    return { genislikMm, yanKaynak, birimsiz, okunamaz, isGorsel, isPre, kademe1, kademe2, kademe3,
             tasanN: ta.length, tasan: say(ta), kirpikN: ki.length, kirpik: say(ki) };
  }, [SAYFA_GENISLIK_MM, 12, 12, !!duzelt]);
}

(async () => {
  // ⛔ `dosyaUrl` (pathToFileURL + localhost UNC düzeltmesi; Issue #389 ①, F4).
  const fileUrl = dosyaUrl(IN);
  const b = await chromium.launch({ channel: "msedge", headless: true, args: ["--no-sandbox"] });
  const p = await (await b.newContext()).newPage();
  await p.goto(fileUrl, { waitUntil: "networkidle", timeout: 60000 });
  await p.emulateMedia({ media: "screen" });
  const dz = await dizinListesiMi(p);
  if (dz.liste) {
    const acilan = p.url();
    await b.close();
    console.error("[DURDU] PDF FAIL: acilan sayfa bir DIZIN LISTESI (baslik: " + JSON.stringify(dz.baslik) +
                  "), belge degil — girdi yolu bir dizin mi ya da yol URL'e cevrilirken kesildi mi? " +
                  "Girdi: " + IN + " · acilan: " + acilan);
    eskiPdfUyar();
    process.exit(2);
  }
  // YERLEŞİM (Issue #389 ②③④): önce ölç, yalnız-PDF CSS'i ekle, taşan tabloları işaretle, yeniden ölç.
  // --sayfa-no / --yer-imi ölçümlerinden ÖNCE: onlar SON yerleşimi ölçmeli.
  const yOnce = await yerlesimOlc(p, false);
  await p.addStyleTag({ content: PDF_CSS });
  const y = await yerlesimOlc(p, true);
  console.log("YERLESIM: baski genisligi " + y.genislikMm.toFixed(1) + "mm (" + y.yanKaynak + ")" +
              " | duzeltme oncesi tasan " + yOnce.tasanN + ", kirpik " + yOnce.kirpikN +
              " | PDF-CSS isaretli oge: tasan gorsel " + y.isGorsel + ", tasan/kirpik pre " + y.isPre +
              " | tasan tablo sarildi: kod/pre " + y.kademe1 + ", gorsel " + y.kademe2 + ", tum hucre " + y.kademe3 +
              " | kalan tasan " + y.tasanN + (y.tasanN ? " (" + y.tasan + ")" : "") +
              ", kirpik " + y.kirpikN + (y.kirpikN ? " (" + y.kirpik + ")" : "") +
              " | olculmeyen @page yan boslugu " + y.birimsiz + ", okunamayan stil sayfasi " + y.okunamaz +
              " | shadow root/iframe TARANMADI");
  const yerlesimUyari = y.tasanN + y.kirpikN;
  if (yerlesimUyari > 0) {
    console.error("⚠ UYARI YERLESIM: " + y.tasanN + " oge baski genisligini (" + y.genislikMm.toFixed(1) +
                  "mm) asiyor — Chromium BUTUN belgeyi kucultebilir; " + y.kirpikN +
                  " oge kirpik (icerigi PDF'te kesilir). Belge kendi CSS'iyle duzeltmeyi eziyor olabilir.");
  }
  // ⛔ Bayraksız seçenek nesnesi ESKİSİYLE BİREBİR (Q366 zorunlu önlemi). Çıktının kendisi #389'dan beri
  //    yalnız taşan/kırpık öğeli belgede değişir (YERLEŞİM bloğu); önceki metin "varsayılan çıktı değişmez" diyordu.
  const opts = { path: OUT, format: "A4", printBackground: true, margin: { top: "14mm", bottom: "16mm", left: "12mm", right: "12mm" } };
  if (BAYRAK.has("--sayfa-no")) {
    const o = await altBoslukOlc(p, 16);
    const pa = await p.context().newPage();   // AYRI, boş sayfa: belge CSS'i altbilgi ölçümüne ulaşmaz
    await pa.setContent('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body></body></html>');
    o.altbilgiMm = await altbilgiOlc(pa);
    await pa.close();
    const gerek = ALTBILGI_ALT_IC_MM + o.altbilgiMm + ALTBILGI_PAY_MM;
    const okn = o.okunamayan.length;
    // KAPSAM BEYANI: "(muhafazakar)" yalnız viewport sorgusu VARKEN ve okunamayan grup YOKKEN basılır
    // (0 sorguda muhafazakârlık yoktur; okunamayan grup varken ölçüm muhafazakâr değil EKSİKTİR).
    console.log("ALTBILGI: etkin alt bosluk " + o.etkinMm.toFixed(1) + "mm (" + o.kaynak +
                "), gereken " + gerek.toFixed(1) + "mm = alt kenar " + ALTBILGI_ALT_IC_MM + "mm + altbilgi " +
                o.altbilgiMm.toFixed(1) + "mm (ayri sayfada) + pay " + ALTBILGI_PAY_MM + "mm" +
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
      eskiPdfUyar();
      process.exit(2);
    }
    if (!(o.etkinMm >= gerek)) {
      await b.close();
      // "~(" = viewport'a bağlı medya sorgusu grubu (altBoslukOlc etiketi)
      const vp = o.kaynak.includes("~(") ? " Kaynak VIEWPORT'A BAGLI medya sorgusu (muhafazakar): baskida uygulanip " +
                 "uygulanmadigi ekran viewport'undan bilinemez, en kucuk deger alindi." : "";
      console.error("[DURDU] --sayfa-no: etkin alt bosluk " + o.etkinMm.toFixed(1) + "mm < gereken " +
                    gerek.toFixed(1) + "mm (" + o.kaynak + "; alt kenar " + ALTBILGI_ALT_IC_MM + " + altbilgi " +
                    o.altbilgiMm.toFixed(1) + " + pay " + ALTBILGI_PAY_MM + ")." + vp +
                    " Altbilgi govdenin son satirina BINERDI ya da KIRPILIRDI; govdeyi daraltmamak icin " +
                    "margin degistirilmez. Belgenin @page margin-bottom degerini buyut ya da bayraksiz uret.");
      eskiPdfUyar();
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
  PDF_YAZILDI = true;
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
  // `PDF OK` YALNIZ yerleşim temizken (Issue #389): kalan taşma/kırpıkta PDF yazılır ama OK denmez.
  if (yerlesimUyari > 0) console.log("PDF UYARILI (" + yerlesimUyari + " yerlesim uyarisi, stderr):", OUT);
  else console.log("PDF OK:", OUT);
})().catch(e => { console.error("ERR", e); if (!PDF_YAZILDI) eskiPdfUyar(); process.exit(1); });

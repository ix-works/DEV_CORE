---
layer: L3
type: how-to
scope: dökümantasyon / PDF üretimi
applies-to: KD (ve FS/TS) markdown → şık PDF
last-updated: 2026-06-11
status: active
---

# How-To: Markdown Dökümanı → Ekran Görüntülü Şık PDF (KD/FS/TS)

> **Ne zaman:** Bir KD (veya FS/TS) markdown'ını **gerçek ekran görüntüleriyle** kurumsal/şık bir PDF'e çevirirken.
> **Neden bu dosya:** İlk denemede deneme-yanılma patinajı yaşandı (ZSD001 KD, 2026-06-11). Kullanıcı: *"patinaj yapıyon önce araştır."* Aşağıdaki reçete **kanıtlı** ve **tek seferde** çalışır. Tekrar aynı tuzaklara düşme.

## KANITLI YÖNTEM (özet)
**Temiz markdown kaynağı → python-markdown → HTML+CSS → Chromium/Playwright `page.pdf`.**
(Araştırma 2026-06-11: WeasyPrint alternatif ama Windows'ta Pango/Cairo kurulum derdi; pandoc kurulu değil. Chromium `page.pdf` modern CSS + resim için en pürüzsüz, zaten Playwright MCP'de mevcut.)

Üreteç hazır: **`scripts/build_kd_pdf.py`** (KD için; başka doküman için kopyala-uyarla). Çıktı: `docs/<DOC>.html` + `<DOC>.pdf`.

---

## A — Ekran görüntülerini ÜRET (mock/demo ile, TEMİZ örnek veri)

Gerçek (test-ortamı) veri yerine **zengin-mock**: anlamlı örnek isimler (ÖRNEK MÜŞTERİ A.Ş., FT-DIRSEK-90), SAP login yok, kontrollü dolu ekranlar.

1. **Mock'u doğru servise bağla.** `ui/<app>/ui5-mock.yaml` içindeki `sap-fe-mockserver` çoğu zaman **stale**'dir (eski/kopyalandığı servise işaret eder). Düzelt:
   - `urlPath: /sap/opu/odata/sap/<SRVB_adı>` (manifest `dataSources.mainService.uri` ile aynı).
   - `metadataPath` → canlı `$metadata`'yı indir: `GET .../sap/opu/odata/sap/<SRVB>/$metadata` → `webapp/localService/mainService/metadata.xml`.
   - `generateMockData: true` bırak (kürate edilmeyen entity'ler için).
2. **Temiz mock veri kürate et.** `webapp/localService/mainService/data/<EntitySet>.json` (dizi). Alan adlarını mock'tan teyit et: `GET .../<EntitySet>?$top=1&$format=json`. Anlamlı değerler yaz. (ZSD001: `ZSD001_C_SO_ITEM`, `ZSD001_C_PORTAL_HEAD`, `ZSD001_C_PORTAL_ITEM`.)
3. `npm run start-mock` → **portu log'dan al** (fiori-run artan port verir: 8083/8084/8085…). Veri değişince **restart** gerekir (mockserver başlangıçta okur).
4. **Playwright ile gez ve çek.** `browser_navigate` → `http://localhost:<port>/index.html?sap-ui-language=tr`
   - ⚠️ **TÜRKÇE locale ŞART** (`?sap-ui-language=tr`) — yoksa UI İngilizce çıkar.
   - ⚠️ Playwright MCP browser ara sıra kapanır → navigate'i bir kez **tekrar** dene.
5. **Aç/kapat alanlarını İKİ durumda çek** (kullanıcı bunu özellikle ister): collapse paneller (Filtreler, Notlar), açılır liste satırları (belge kalemleri) — hem kapalı hem AÇIK kare.
6. **Pasif butonu/diyaloğu JS ile aç** (header-gate vb. yüzünden disabled):
   ```js
   // registry'den butonu bul, aç, bas → dialog açılır (dialog statik, backend istemez)
   sap.ui.core.Element.registry.forEach(e=>{ if(e.isA&&e.isA('sap.m.Button')&&e.getText&&e.getText()==='Toplu Ekle'){e.setEnabled(true);e.firePress();} });
   ```
   TextArea'ya örnek veri: `ta.setValue('FT-DIRSEK-90\tCM-1001\t10\n...')`.
7. **Function-import gerektiren DOLU state** (fiyat/bakiye/lookup mock'ta yok): UI'yi sürerek doldur (ör. **Portal Devral → sipariş seç → Devral** kalemleri Yarat ekranına aktarır). Çıkan **hata popup**'ını JS ile kapat: `registry...isA('sap.m.Dialog')&&e.isOpen()→e.close()`.
8. **Beyaz alanı kırp** (PIL threshold):
   ```python
   g=im.convert('L').point(lambda p:0 if p<242 else 255); bbox=ImageOps.invert(g).getbbox(); im.crop(bbox±margin)
   ```

## B — PDF'i KUR (`scripts/build_kd_pdf.py` deseni)

1. **Markdown KAYNAĞINI temizle** (en kritik adım):
   - **Placeholder'lar ``` kod-bloğu içindeyse**, fence **BLOĞUNUN TAMAMINI** resimle değiştir — fence İÇİNE `![](..)` koyma, **markdown kod-bloğunda resmi parse ETMEZ** (metin kalır). Regex: ```` ```…[PLACEHOLDER]…``` ```` → `![cap](src)`.
   - **Ham `<figure>` HTML KULLANMA**: `md_in_html` bozar (sadece sonuncu sağ kalır). Yerine **markdown resmi** `![cap](src)` + ardından `*cap*`; HTML üretimi SONRASI `<p><img></p>\s*<p><em>cap</em></p>` → `<figure><figcaption>` regex ile sar.
2. `markdown.markdown(md, extensions=['tables','fenced_code','sane_lists'])`.
3. CSS: A4 `@page`, başlık gradient-banner, tablo (th koyu/zebra), `figure img` (çerçeve+gölge+max-width:100%), `figcaption` (italik gri).
4. **Servis et — `file://` BLOKLU** (Playwright MCP: *"Access to file: protocol is blocked"*). Çözüm: `python -m http.server <port>` `docs/` içinde → `http://localhost:<port>/<DOC>.html` (görseller `screenshots/` altında, göreli yol çözülür).
5. **page.pdf** (`browser_run_code_unsafe`):
   ```js
   await page.waitForLoadState('networkidle'); await page.emulateMedia({media:'screen'});
   await page.pdf({path:'…/DOC.pdf', format:'A4', printBackground:true, margin:{top:'14mm',bottom:'16mm',left:'12mm',right:'12mm'}});
   ```

## C — DOĞRULA (bitti DEMEDEN ÖNCE — [[feedback_done-tam-kapsam-dogrula]])
- ⭐ **SUB-SCREEN KAPSAMI:** Uygulamanın `view/*.xml` + `fragment/*.xml` envanterini çıkar → **her dialog/popover/value-help/picker KD'de bir bölüme eşlendi mi?** Modal pencereler (ör. "Sipariş Ekle" picker) ana sayfalar kadar zorunlu (standards/04 §4.3/§4.4). Atlanan sub-screen = eksik KD (ZSD001 FIT_SE'de "Sipariş Ekle" başta atlanmıştı, kullanıcı yakaladı).
- HTML'de `<img>` sayısı = **beklenen** mi? (Patinaj: 9 beklenirken **1** çıktı, kullanıcı yakaladı.)
- page.pdf öncesi: `document.images.filter(i=>i.complete && i.naturalWidth>0).length` = beklenen.
- Render teyidi: `figure img` `naturalWidth` **ve** `offsetWidth > 0` (yüklendi + görünür).
- PDF boyutu mantıklı mı (resim başına ~50–100KB; ZSD001: 1 resim 460KB → 9 resim 1.06MB).

## PATİNAJ TUZAKLARI — DENENEN BAŞARISIZ (tekrarlama!)
| Belirti | Sebep | Çözüm |
|---|---|---|
| HTML'de figcaption var ama `<img>` yok / az | Ham `<figure>` → `md_in_html` bozdu | markdown `![](..)` + post-wrap regex |
| Resim metin olarak çıkıyor, `<img>` olmuyor | `![](..)` ``` kod-bloğu içinde | fence **bloğunun tamamını** değiştir |
| "Access to file: protocol is blocked" | Playwright MCP `file://` engelli | `python -m http.server` ile servis et |
| UI İngilizce | locale default | `?sap-ui-language=tr` |
| Script `UnicodeEncodeError charmap` | cp1252 konsola Türkçe `print` | dosyaya `utf-8` yaz, Türkçe print etme ([[feedback_powershell-utf8-bom-trap]]) |
| Mock boş/yanlış servis | `ui5-mock.yaml` stale (kopya servis adı) | urlPath + metadata güncelle |
| Dolu Yarat/fiyat boş | function-import mock'ta yok | UI'yi sür (Devral) / layout-kabul |
| `npm run start-mock` yok / mockserver başlamıyor | app'te `@sap-ux/ui5-middleware-fe-mockserver` devDep YOK (yalnız deploy edilmiş report app'lerinde sık) | package.json'a devDep + `start-mock` script ekle, `npm install` (ZSD001/005/006 KD dersi) |
| **F4 value-help SelectDialog boş açılıyor** | Ana EntitySet mock'landı ama F4'lerin beslendiği **ortak `ZSD000_I_*VH`** entity'lerinin data'sı yok | Her F4 VH entity'sine de `data/<VH>.json` kürate et (Satış Org=VKORGVH, Müşteri=CUSTOMER_VH, Malzeme=MATERIAL_VH...) |
| F4 dialog snapshot ile açılmıyor (ikon ref yok) | value-help ikonu erişilebilir ref vermiyor | JS `getView` kontrol → `fireValueHelpRequest()` ile aç |
| **Playwright yanlış app'e drift (çok-mock paralel)** | Çok-geliştirici/çok-app repoda aynı anda 2+ mock server + paylaşılan tarayıcı + FLP-preview launchpad reuse → tab başka porta atlıyor, `Element.registry` her iki app'i döndürüyor | İzole adlı session (`playwright-cli -s=<ad>`) + her eval'de `location.port`/component-id ASSERT + gerekiyorsa FLP-preview'siz **izole-port** mock (ZSD001/006 KD dersi) |

> **Asıl ders (T10):** Tanıdık olmayan üretim/araç görevinde **önce kanıtlı yöntemi araştır**, sonra tek seferde uygula. Kaynak hatasını araç hatası sanma. Bkz. [[feedback_arastir-once-patinaj-uretim-gorev]].

---

## D — DİYAGRAM (Mermaid) + EĞİTİM SLAYTI (Marp) + ALAN TABLOSU (gen_field_table)

> 2026-06-14 adoption (gerçek render ile doğrulandı). Ortak helper: **`scripts/doc_tools.py`** —
> tarayıcı çözümü + mermaid render + ```mermaid fence-preprocess + marp build TEK yerde.
> Araç durumu: `python scripts/doc_tools.py check`. Kurulum: `python scripts/team_setup.py` (mmdc+marp
> npm CLI listesine eklendi).

### D.0 Panel-bazlı ekran çekimi + PDF (ZSD001 kanıtlı akış, 2026-06-14)
- **`scripts/capture_kd_screens.js`** — mock UI'da Create ekranına gidip (router `getRouter()` falsy →
  **"Yeni Sipariş" düğmesine tıkla**), `orderModel`'e zengin örnek state **eval ile enjekte** edip
  her ekran bölmesini AYRI kırpar (Başlık, Bakiye, Kalem tablosu, Kalem Detay ⓘ, Özet, Notlar, Depo
  dialog). id'li paneller `[id$="--panelId"]` (re-render'a dayanıklı), id'siz paneller `data-kd` ile
  etiketlenir. Bakiye/fiyat function-import → mock'ta boş → enjekte. `node scripts/capture_kd_screens.js http://localhost:PORT`.
- **`scripts/html_to_pdf.js`** — `build_kd_pdf.py` HTML çıktısını Edge `page.pdf` ile A4 PDF'e çevirir
  (`file://` node-playwright'ta çalışır; MCP'de bloklu). `node scripts/html_to_pdf.js in.html out.pdf`.
- **Tam zincir:** mock başlat → `capture_kd_screens.js` → KD markdown'ı güncelle → `build_kd_pdf.py`
  (mermaid render + HTML) → `html_to_pdf.js` (PDF). State enjekte ederken **sayıları tutarlı tut**
  (footer formatter'ı: `pakOnly=qty×pakFactor`, `pakSum=totalPackages` → toplam = Σ uyumlu olmalı).

### D.1 Mermaid — diyagram-as-code (FS/TS/KD görselleri)
- **Ne için:** akış (Fiori→OData→RAP→CDS→HANA), sequence, CDS'ten ER, draft/lock state. ASCII mockup
  yerine git-versiyonlu, GitHub'da native render olan görsel.
- **KD/PDF içine göm:** markdown'a ```mermaid ... ``` bloğu yaz → `build_kd_pdf.py` otomatik PNG'ye
  render edip `![](screenshots/diagram-NN.png)` ile değiştirir (adım 5b, `preprocess_mermaid_fences`).
- **Tek dosya:** `python scripts/doc_tools.py mermaid girdi.mmd cikti.(svg|png)`.

### D.2 Marp — eğitim slaytı (canlı-geçiş sunumu)
- **Ne için:** son kullanıcı eğitim deck'i; tek markdown kaynağından PDF + PPTX (düzenlenebilir).
- **Çağrı:** `python scripts/doc_tools.py marp deck.md pdf` (veya `pptx`/`html`). Frontmatter:
  `marp: true` + `theme: default` + `paginate: true`; slayt ayracı `---`.

### D.3 gen_field_table — CDS → alan tablosu (TS§4.5 / KD§6)
- **Ne için:** alan tablolarını **elle yazma**yı bitir. Doğruluk kaynağı = CDS annotation'ı
  (ChatGPT'nin "screenshot→OCR" önerisinin doğru hali — kendi ekranını OCR'lama, metadata oku).
- **Çağrı:** `python scripts/gen_field_table.py <cds> [--ref-csv ref_docs/table_fields.csv] [-o out.md]`.
- Etiket sırası: `@UI.lineItem label` → `@EndUserText.label` → interface CDS (projection follow) →
  ref_docs CSV. readonly = sibling+interface `.bdef`. **Etiketsiz alan ⚠️ flag'lenir** (uydurmaz).

### TUZAKLAR — DENENEN BAŞARISIZ (tekrarlama!)
| Belirti | Sebep | Çözüm |
|---|---|---|
| `marp --pdf/--pptx` **takılıyor** (Chrome) | Kullanıcının açık Chrome profiliyle çakışma | **Edge** kullan (`--browser edge`); `doc_tools` zaten Edge'i tercih eder |
| mmdc puppeteer config "Bad escaped character in JSON" | Windows yolu `\\` ters-eğik JSON escape kırar | `executablePath`'i **forward-slash** ile yaz (`doc_tools` otomatik) |
| mmdc "could not find Chrome" | mermaid-cli postinstall (puppeteer chromium indirme) bizde çalışmıyor | sistem tarayıcısına yönlendir (puppeteer config executablePath; `doc_tools` halleder) |
| `gen_field_table` 0 alan | header annotation (`@ObjectModel.usageType: {`) define'dan önce `{` içeriyor | body '{' aramaya define'dan SONRA başla (düzeltildi) |

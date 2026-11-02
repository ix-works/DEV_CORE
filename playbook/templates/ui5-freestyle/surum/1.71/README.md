---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: template
---
# Sürüm parçası — UI5 1.71 hattı

`app/` kopyalandıktan sonra bu klasörün `webapp/` içeriği **üstüne** kopyalanır
(iki dosya: `webapp/index.html` + `webapp/util/SurumParca.js`). Ortak gövde bu parçayı `util/SurumParca` adıyla çağırır.

`index.html` bootstrap öznitelikleri **tek kelime küçük harf** yazılır (`data-sap-ui-oninit`,
`-resourceroots`, `-compatversion`, `-frameoptions`): 1.71.85 öznitelik adını yalnız küçük harfe çevirir,
tire→camel dönüşümü kapalıdır (`jquery.sap.global-dbg.js:381-382`) ⇒ `data-sap-ui-on-init` tanınmaz ve
uygulama açılmaz. Biçim 1.71.85 demokit cart `index.html`'iyle aynıdır.

## Ne zaman bu parça

Backend'in UI5 sürümü (`GET /sap/public/bc/ui5_ui5/resources/sap-ui-version.json` → `version`)
1.120'nin altındaysa (std/03 tanımı: 1.71 hattı = backend < 1.120 · 1.120 hattı = ≥ 1.120).
Ölçümün hedefi: CDN `https://ui5.sap.com/1.71.85/` (`sap-ui-version.json` → `1.71.85`).
1.72–1.119 arası: parçanın dayandığı davranışlar dört ara sürümde ölçüldü (aşağıda §Ara sürümler); biri farklı
çıktı. Ölçülmeyen ara sürümde üyelerin dayandığı API tek tek kontrol edilir (aynı yöntem; 1.119 yalnız bulut
sürümüdür, CDN'de yok — `surum/1.120/README.md`).

## Bu parçanın sağladığı altı üye

| İşlev | Uygulama | Kanıt (1.71.85 CDN) |
|---|---|---|
| `satirModu(oTable, iMin)` | `setVisibleRowCountMode("Auto")` + `setMinAutoRowCount(iMin)` | `sap/ui/table/rowmodes/Auto-dbg.js` → 404; `Table.rowMode` aggregation var ama `visibility: "hidden"`; `visibleRowCountMode`/`minAutoRowCount` public |
| `bosDurum(oTable, m)` | `noData` = `VBox(Text, Text, Button)` | `sap/m/IllustratedMessage-dbg.js` → 404; `sap.ui.table.Table.noData` tipi `sap.ui.core.Control`, `multiple:false` (altTypes `string`) ⇒ birden çok kontrol bir kapsayıcıda. **Yalnız grid için:** `sap.m.Table`/`List` 1.71'de `noData` aggregation'ı YOK (yalnız `noDataText`; aggregation `@since 1.101`) — m.Table'da CTA gerekiyorsa tablonun yanında görünürlüğü satır sayısına bağlı bir `VBox{Text + Button}` kurulur |
| `bilesenArayuzleri` | `[]` — async içerik manifest `rootView.async` + `routing.config.async` ile | `sap.ui.core.IAsyncContentCreation` 1.71.85 `sap/ui/core/library-dbg.js`'te 0 eşleşme (`@since 1.89`) |
| `yapistirmaBagla(oMI, fnSatir, fnBitti)` | 1.120 parçasıyla aynı gövde | `MultiInput.prototype.onpaste` → `fireEvent("_validateOnPaste", {texts}, true)`; satır ayırıcı `Tokenizer._parseString` = `/\r\n\|\r\|\n\|\t/g` |
| `siraliMi(oCol)` | `oCol.getSorted()` | `sap/ui/table/Column-dbg.js:131` `sorted` varsayılan `false` · `:138` `sortOrder` varsayılan `Ascending`; `sap.ui.table.SortOrder` enum'unda `None` YOK ⇒ `getSortOrder() === "None"` hiç doğru olmaz, her kolon sıralı sayılırdı |
| `dogrulayiciMetni(sText)` | olduğu gibi döner | `sap/m/MultiInput-dbg.js:1147-1148` `_validateCurrentText` → `_tokenizer._addValidateToken({text: text})` — validator ham metni alır (kaçış yok) |

**1.71'de OLMAYAN ve ortak gövdenin bu yüzden kullanmadığı public API:** `MultiInput.addValidateToken`
(1.71.85'te yalnız iç `_tokenizer._addValidateToken` var; 1.120.52'de public). Ortak gövde yapıştırılan
satırı kendi doğrulayıcısından geçirip public `addToken` ile ekler — iki sürümde aynı davranış.

## Ara sürümler — 1.71 parçasının dayandığı davranış (ölçüldü 2026-11-02)

Kaynak: `https://ui5.sap.com/<sürüm>/resources/<modül>-dbg.js` + aynı sürümlerde tarayıcı sondası (yerel sayfa, CDN
bootstrap'ı, 1.71 parçasının öznitelik biçimi). CDN yolu ↔ çalışma zamanı `sap.ui.version`: 1.71.85↔1.71.81 ·
1.84.62↔1.84.59 · 1.96.51↔1.96.49 · 1.108.57↔1.108.55 · 1.114.10↔1.114.13 · 1.120.52↔1.120.50. Her cümle yalnız
ölçüldüğü sürüme aittir; aradaki yamalar ÖLÇÜLMEDİ.

| Davranış (parçadaki yeri) | 1.71.85 | 1.84.62 | 1.96.51 | 1.108.57 | 1.114.10 | Kanıt |
|---|---|---|---|---|---|---|
| Küçük harf tek kelime bootstrap (`resourceroots`, `oninit`) tanınır (`index.html`) | evet | evet | evet | evet | evet | tarayıcı: modül `./app/`'ten çözüldü + `oninit` işlevi çağrıldı. Tireli biçim (`on-init`) 1.71.85–1.108.57'de yok sayılır, 1.114.10'da tanınır (lider ölçümü) |
| Manifest `sap.app.i18n` dizgi okunur (ortak gövde) | evet (`Manifest-dbg.js:279`) | evet (`:258-259`) | evet (`:262-263`) | evet (`:266-267`) | evet (`:268-269`) | kaynak |
| Spreadsheet `dataSource: {dataUrl, …}` (ortak gövde) | evet (`Spreadsheet-dbg.js:436`) | evet (`:590`) | evet (`:611`) | evet (`:644`) | evet (`:627`) | kaynak (`processDataSource` nesne dalı) |
| `siraliMi` = `getSorted()`: varsayılan `false`, `Table.sort` sonrası `true`; `sortOrder` varsayılanı `Ascending` | evet | evet | evet | evet | evet | tarayıcı (`Column-dbg.js` varsayılanları 1.71.85:131,138 · 1.84.62:131,138 · 1.96.51:132,139 · 1.108.57:133,140 · 1.114.10:133,140) |
| `bosDurum`: `Table.noData` bir `VBox` kabul eder | evet | evet | evet | evet | evet | tarayıcı (`getNoData()` → `sap.m.VBox`) |
| `satirModu`: `visibleRowCountMode="Auto"` + `minAutoRowCount` | evet | evet | evet | evet | evet | tarayıcı (`Auto/10`); çizimde satır sayısının ekrana uyması ÖLÇÜLMEDİ |
| `yapistirmaBagla`: MultiInput `_validateOnPaste` olayı | evet (`MultiInput-dbg.js:756`) | evet (`:838`) | evet (`:858`) | evet (`:860`) | evet (`:902`) | kaynak (`onpaste` → `fireEvent`) |
| `dogrulayiciMetni` HAM döner — validator'a gelen yazılı metin ham mı | ham | ham | ham | **KAÇIŞLI** | ham | tarayıcı: `a{b}` yazıldı → 1.108.57 validator'ı `a\{b\}` aldı (1.120.52 ile aynı); kaynak `_validateCurrentText` → `addValidateToken({text: escapeSettingsValue(sValue)})` 1.108.57:1951-1952, öbürlerinde `text: sValue` |

**Sonuç:** 1.84.62 · 1.96.51 · 1.114.10'da tablodaki sekiz davranışın sekizi 1.71.85 ile aynıdır; 1.108.57'de yedisi. **1.108.57'de**
validator metni kaçışlıdır ⇒ 1.71 parçası `{`, `}` içeren yazılı değeri token'a kaçışlı (`a\{b\}`)
geçirir; bu karakterleri içermeyen girdide fark yoktur. O hat için ne yapılacağı (parçada sürüm tespiti ya da
1.120 parçasının `dogrulayiciMetni`'si) **KARARLAŞTIRILMADI**. Uygulamanın o sürümlerde bütün olarak açılması
ÖLÇÜLMEDİ.

## Manifest değerleri (bu hat için)

| Yer tutucu | Değer | Kaynak |
|---|---|---|
| `<MANIFEST_SURUMU>` | `1.12.0` | 1.71.85'in kendi uygulama örnekleri bu değeri taşır — `GET https://ui5.sap.com/1.71.85/test-resources/sap/m/demokit/cart/webapp/manifest.json` ve `…/orderbrowser/webapp/manifest.json` → 200, `"_version": "1.12.0"` (ölçüldü 2026-11-02). 1.71.85 çalışma zamanı değeri OKUMAZ (`sap/ui/core/Manifest-dbg.js`'te `_version` 0 eşleşme) — değer araçlar (descriptor doğrulama/deploy) içindir. Kütüphane manifestlerindeki `_version` uygulama descriptor sürümü DEĞİLDİR |
| `<BACKEND_UI5_SURUMU>` | backend'in `sap-ui-version.json` `version` değeri | std/03 §2.5 |
| `<TEMA>` | `sap_fiori_3` | üst README "Tema kuralı" (1.71.85'te `sap_horizon/library.css` 200 döner ama `base` ile aynı içeriktir) |

## Backend notu

Varyant servisi referansı (`backend-referans/`) RAP + CDS view entity ister — S/4HANA backend.
1.71 UI'ı ECC üzerinde koşuyorsa varyant servisi başka yolla (ör. SEGW) kurulmalıdır; bu yol
şablonda **DOĞRULANMADI**. Servis yoksa `TablePersonalizer` açılışta uyarı yazar ve yerel saklamaya düşer.

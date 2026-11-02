---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: template
---
# Sürüm parçası — UI5 1.120 hattı (backend UI5 >= 1.120)

`app/` kopyalandıktan sonra bu klasörün `webapp/` içeriği **üstüne** kopyalanır
(iki dosya: `webapp/index.html` + `webapp/util/SurumParca.js`). Ortak gövde bu parçayı `util/SurumParca` adıyla çağırır.

`index.html` bootstrap öznitelikleri **kebab** yazılır (`data-sap-ui-on-init`, `-resource-roots`,
`-compat-version`, `-frame-options`; std/03 biçimi): 1.120.52 tireli adı camelize eder ve küçük harf
takma adı da tanır (`ui5loader-autoconfig-dbg.js:181,213`). Bu biçim 1.71'de ÇALIŞMAZ — kardeş parça.

## Ne zaman bu parça

Backend'in UI5 sürümü (`GET /sap/public/bc/ui5_ui5/resources/sap-ui-version.json` → `version`)
**1.120 veya üstü** ise (std/03 tanımı: 1.71 hattı = backend < 1.120 · 1.120 hattı = ≥ 1.120).

Alt sınırın kaynağı `siraliMi`'dir: `getSortOrder() !== "None"` yüklemi `Column.sortOrder`'ın
`sap.ui.core.SortOrder` tipine ve `None` varsayılanına dayanır — bu 1.120'de geldi
(1.120.52 `sap/ui/table/Column-dbg.js:128` `sorted` "@deprecated As of version 1.120", `:136` `sortOrder`
varsayılanı `SortOrder.None`). 1.120 öncesinde `sortOrder` varsayılanı `Ascending`'dir (1.120.52 `Column-dbg.js:666`
yorumu "Ascending was the default value of sortOrder before sorted was deprecated"; 1.71.85 `Column-dbg.js:138`
ölçüldü) ve yüklem HER kolonu sıralı sayar (1.71 parçasının `getSorted()` kullanma nedeni). Parçanın öbür API'leri daha eskidir:
`sap.ui.table.rowmodes.Auto` `@since 1.119`, `sap.m.IllustratedMessage` `@since 1.98`, MultiInput
`_validateOnPaste` olayı 1.71.85'te de var.

**1.119 ÖLÇÜLEMEDİ:** `https://ui5.sap.com/versionoverview.json` → `1.119.*` için `frontendserver: "Cloud only"`
(on-premise backend'de bulunmaz); CDN'de `1.119.0`/`1.119.1` `sap-ui-version.json` → 404 (ölçüldü 2026-11-02).

## Bu parçanın sağladığı altı üye

| İşlev | Uygulama | Kanıt (1.120.52 CDN `-dbg.js`) |
|---|---|---|
| `satirModu(oTable, iMin)` | `setRowMode(new Auto({minRowCount}))` | `Table.rowMode` aggregation `@since 1.119`; `visibleRowCountMode` aynı sürümde deprecated |
| `bosDurum(oTable, m)` | `noData` = `IllustratedMessage` + CTA `Button` (`additionalContent`) | `IllustratedMessage.additionalContent: sap.m.Button, multiple` |
| `bilesenArayuzleri` | `["sap.ui.core.IAsyncContentCreation"]` → `Component.js` `metadata.interfaces` | 1.120.52 `sap/ui/core/library-dbg.js` 2 eşleşme; arayüz `@since 1.89`; std/03 §4 zorunlu |
| `yapistirmaBagla(oMI, fnSatir, fnBitti)` | özel `_validateOnPaste` olayı + `preventDefault` | `MultiInput.prototype.onpaste` → `fireEvent("_validateOnPaste", {texts}, true)` |
| `siraliMi(oCol)` | `oCol.getSortOrder() !== "None"` | `sap/ui/table/Column-dbg.js:136` `sortOrder` varsayılan `None`; `:130` `sorted` deprecated (1.120) |
| `dogrulayiciMetni(sText)` | validator metnindeki kaçışı geri alır (`\{` `\}` `\\` → `{` `}` `\`) | `sap/m/MultiInput-dbg.js:1992` `addValidateToken({text: ManagedObject.escapeSettingsValue(sValue)})`; kaçış = `BindingParser-dbg.js:51,618-619` `replace(/([\\\{\}])/g, "\\$1")` (`complex` sözdizimi: `BindingInfo-dbg.js:201` uyumluluk sürümü ≥ 1.26 ⇒ `complex`; şablon `compat-version="edge"` verir) |

`_validateOnPaste` **public API değildir** (alt çizgili olay). Ortak gövdede durmamasının nedeni budur:
sürüm yükseltmesinde kırılırsa düzeltme tek dosyada kalır. Yükseltmeden sonra kontrol: yeni sürümün
`sap/m/MultiInput-dbg.js` dosyasında `_validateOnPaste` aranır; yoksa bu fonksiyon yeniden yazılır.

## Manifest değerleri (bu hat için)

| Yer tutucu | Değer | Kaynak |
|---|---|---|
| `<MANIFEST_SURUMU>` | `1.60.0` | std/03 §3.2 (descriptor sürümü). Backend 1.120 altındaysa SAP'nin descriptor-sürüm tablosundan seçilir — **bu şablonda ÖLÇÜLMEDİ** |
| `<BACKEND_UI5_SURUMU>` | backend'in `sap-ui-version.json` `version` değeri (ör. `1.120.23`) | std/03 §2.5 |
| `<TEMA>` | `sap_horizon` | üst README "Tema kuralı" |

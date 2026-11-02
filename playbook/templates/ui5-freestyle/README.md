---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: template
---
# Freestyle UI5 şablonu — seçim ekranı → grid liste → değişiklik ekranı (OData V2)

Yeni bir freestyle uygulama **bu şablondan kopyalanarak** başlar (std/03 + `playbook/ui-freestyle-odata-v2.md`
kurallarının çalışan hâli). Şablonun içindeki her parça, çalışan uygulamalardan alınıp jenerikleştirildi;
hangi sürüm API'sine dayandığı aşağıdaki §4'te kanıtıyla yazılıdır.

```
ui5-freestyle/
├── app/                     ORTAK GÖVDE — her sürümde aynı (sürüme bağlı API KULLANMAZ)
│   ├── package.json · ui5.yaml · ui5-deploy.yaml
│   └── webapp/  Component.js · manifest.json · controller/ · view/ · util/ · i18n/ · model/ · css/
├── surum/                   SÜRÜM PARÇASI — iki dosya: webapp/index.html + webapp/util/SurumParca.js
│   ├── 1.120/webapp/        backend UI5 >= 1.120 (bootstrap öznitelikleri kebab: on-init, resource-roots …)
│   └── 1.71/webapp/         backend UI5 < 1.120, ölçülen 1.71.x (bootstrap öznitelikleri tek kelime: oninit …)
└── backend-referans/        varyant servisi (RAP) kaynak kopyası + sözleşme
```

## 0. Bilinen sınırlar — ilk kullanımda ZORUNLU doğrulama

⛔ **Bu şablon gerçek bir backend'de tarayıcıda açılarak DENENMEDİ.** Kanıtı: üç UI5 validator'ı + şablon
testi (`tests/fixtures/ui5_freestyle_sablon/run.py`) + modüllerin ui5.sap.com'da (1.71.85 · 1.120.52) var
olduğunun ölçümü. Bunlar **statik** kanıttır; ekranın çalıştığını göstermez. Şablondan üretilen ilk
uygulama, aşağıdaki adımlar koşulup çıktıları kayda geçmeden **"çalışıyor" diye teslim edilmez**:

1. **Sürüm + tema backend'den ölçüldü** (§1 adım 1 · §3) — ölçüm çıktısı (sürüm + iki md5) kayıtta.
2. **Tarayıcı turu, kimlikli yerel sunucuda** (`npx fiori run`, std/03 §2.4.3 — kimliksiz sunucu `busy`de
   asılı kalıp sahte hata üretir): seçim ekranı → Listele → grid dolu · **boş sonuç** → CTA'lı boş durum
   görünür · satır modu ekran yüksekliğine uyar · kolon sort/filtre/gizle + varyant kaydet/yükle ·
   değişiklik ekranında kaydet → başarı mesajı + listeye dönüş · konsolda hata yok ·
   **tarih aralığı:** kaydı OLAN günü ve ERTESİ günü ayrı ayrı seç → ertesi gün o kaydı getirmemeli
   (FE-45 kontrol grubu; ağ sekmesinde `$filter` sınırı `…T00:00:00` olmalı, `…T21:00:00` değil) ·
   kolon başlığından sırala → Listele'yi yeniden çalıştır → sıralama korunur, sıralanmamış kolon sorter almaz ·
   **tarih kolonu başlık filtresi:** gridde görünen biçimle (ör. kaydı olan gün) yaz → yalnız o günün kayıtları
   (ağ sekmesinde `$filter=… eq datetime'…T00:00:00'`, ay/gün yer değiştirmemiş) · olmayan gün (`31.11.2026`)
   ya da anlamsız metin yaz → filtre uygulanmaz + mesaj (bir sonraki aya KAYMAZ) · **sayı kolonu başlık filtresi:**
   oturum dilinin biçimiyle yaz (TR `1.250` / `1.250,5`) → ağ sekmesinde `$filter=… eq 1250m` (Decimal; `1.250m`
   DEĞİL) · TR'de `1.25` (gruplaması tutmayan) → filtre uygulanmaz + mesaj · **geçersiz metin, kolonda geçerli
   bir filtre varken:** önceki filtre etkin KALIR, mesaj bunu söyler, ağ sekmesinde yeni istek YOK · **Excel:** kolon filtresi + sıralama aktifken "Tüm kolonlar" → dosyadaki satır sayısı ve
   sırası grid başlığındaki sayıyla/sırayla aynı (ağ sekmesinde Excel isteğinin URL'inde `$filter` + `$orderby` +
   `sap-client`).
3. **1.71 parçası kullanıldıysa:** grid boş durumunun `noData` içinde `VBox`{`Text` + CTA `Button`} olarak
   göründüğü ve `visibleRowCountMode="Auto"` satır sayısının ekrana uyduğu **gözle** doğrulanır — bu iki
   davranış 1.71 çalışma zamanında ÖLÇÜLMEDİ (yalnız API metadata'sı ölçüldü).
4. **Varyant servisi:** servis varsa varyant kaydı tabloya yazılır (servis GET ile görülür); servis yoksa
   konsolda `Log.warning` satırı görülür ve varyant yalnız tarayıcıda saklanır — **sessiz düşme kabul edilmez**.

**Doğrulanamayan / ölçülmeyen kalemler** (kendi sisteminde ölç; sonuç buradakinden farklıysa çekirdeğe
Issue aç — `playbook/howto-cekirdek-bulgu-bildirimi.md`):

| Kalem | Durum | Ayrıntı |
|---|---|---|
| 1.72–1.119 arası backend'de 1.71 parçası (bant tanımı: < 1.120 → 1.71 · ≥ 1.120 → 1.120) | parçanın dayandığı sekiz davranış 1.84.62 · 1.96.51 · 1.108.57 · 1.114.10 (CDN yolu; çalışma zamanı `sap.ui.version` 1.84.59 · 1.96.49 · 1.108.55 · 1.114.13 bildirir)'da CDN kaynağı + tarayıcıda ölçüldü: 1.84.62 · 1.96.51 · 1.114.10'da sekizi, 1.108.57'de yedisi 1.71.85 ile AYNI; **validator metni 1.108.57'de KAÇIŞLI** (1.71 parçası çözmez → `{`·`}` içeren yazılı değer token'a kaçışlı geçer). Bu dört sürüm dışındaki ara sürümler ve uygulamanın bütün olarak açılması ÖLÇÜLMEDİ | `surum/1.71/README.md` §Ara sürümler |
| 1.71 için manifest `_version` | `1.12.0` — 1.71.85 demokit örnekleriyle aynı; çalışma zamanı okumuyor (ölçüldü) | `surum/1.71/README.md` |
| 1.120 altı backend'de manifest `_version` | ÖLÇÜLMEDİ | `surum/1.120/README.md` |
| Backend ICF'nin olmayan temayı `base`'e düşürmesi | DOĞRULANAMADI (yalnız CDN) | §3 — kural iki davranışı da kapsar |
| Varyant servisinin SRVD/SRVB adları + yayınlama | DOĞRULANMADI | `backend-referans/README.md` |
| ECC / SEGW ile varyant servisi | DOĞRULANMADI | `backend-referans/README.md` |
| View özniteliklerinin 1.71'de özellik düzeyinde varlığı | yalnız modül düzeyi ölçüldü (istisna: §4'te adı geçen olay/özellikler tek tek ölçüldü) | §4 |
| Kayıt sayısı başlığı (`dataReceived`) · tarih sınırı (`utcGun`, UTC-doğu + UTC-batı dilimi) · kısmi kaydetme sonrası yeniden okuma · varsayılan varyant sırası · grid hata süzgeci · sıralı kolon yüklemi · validator metni | mantık ölçüldü (sahte modüllerle yerel sonda), **tarayıcıda ÖLÇÜLMEDİ** | §5 |
| Kolon tarih/sayı filtresinin hangi metinleri kabul ettiği | `util/Tarih` + `util/Sayi` + `TablePersonalizer` kolon filtresi **tarayıcıda** (CDN 1.71.85 · 1.120.52; `tr` ve `en`; gerçek `sap.ui.table.Table` + `Column.filter`) ölçüldü — ölçülen metinler §4 `DateFormat`/`NumberFormat` satırlarında. Gerçek backend'e giden `$filter` ÖLÇÜLMEDİ (literal `ODataUtils.formatValue` ile ölçüldü) | §0 adım 2 |
| Excel dışa aktarımının 1.71'de ve 1.120'de dosya üretmesi | yalnız kaynak okundu (§4 `Spreadsheet` · `getDownloadUrl` satırları), **çalışma zamanında ÖLÇÜLMEDİ** | §0 adım 2 |
| Sürüm yüzeyi kontrolünün (fixture V2) kapsamı | V2 bir **ad listesidir**: yalnız bir sürümde VAR OLMAYAN API adlarını yakalar. İki sürümde de var olan bir API'nin **farklı girdi kabul etmesini / farklı varsayılanını** göremez — `Spreadsheet` `dataSource: <binding>` (1.71'de binding dalı yok) bu yüzden V2'den geçti ve bug-gate'te bulundu. Bilinen vakalara ayrı kural var (V2 `getSortOrder() "None"`, V8 `dataSource`, V9 kolon filtresi: `getDateInstance` `strictParsing: true` · `getFloatInstance` `parseAsString: true` · ham metin filtre değeri yok). V9 da sözdizimseldir: ayrıştırıcının DOĞRU sonucu verdiğini ölçmez (o ölçüm tarayıcıdadır, §4). Yeni bir ortak API kullanırken iki sürümdeki **gövdesini** oku | §4 |

## 1. Kopyalama (sıra önemli)

1. Backend UI5 sürümünü **ölç**: `GET https://<DEV_HOST>:<PORT>/sap/public/bc/ui5_ui5/resources/sap-ui-version.json`
   → `version`. Tahmin etme; bootstrap backend'den yapılır (std/03 §2.5), uygulama o sürümle koşar.
2. `app/` içeriğini `<source_root>/<MODÜL>/<PAKET>/ui/<uygulama>/` altına kopyala.
3. Sürüme uyan `surum/<v>/webapp/` içeriğini kopyanın `webapp/` dizininin **üstüne** kopyala
   (iki dosya: `index.html` + `util/SurumParca.js`). Bu adım atlanırsa `index.html` hiç olmaz ve uygulama
   `util/SurumParca` modülünü bulamaz — açılmaz. `index.html` sürüme bağlıdır çünkü bootstrap öznitelik
   adlarının yazımı sürüme bağlıdır: 1.71.85 yalnız küçük harfe çevirir (`jquery.sap.global-dbg.js:381-382`,
   `sap/ui/core/Configuration-dbg.js:304-307`) ⇒ `data-sap-ui-on-init` 1.71'de TANINMAZ; 1.120.52 tireli adı
   camelize eder ve küçük harf takma adı da tanır (`ui5loader-autoconfig-dbg.js:181,213`).
   Bant: backend < 1.120 → `surum/1.71` · ≥ 1.120 → `surum/1.120` (std/03 ile aynı tanım). 1.72–1.119 arasında
   1.71 parçasının dayandığı davranışlar dört ara sürümde ölçüldü, biri farklı çıktı (`surum/1.71/README.md`
   §Ara sürümler) — kendi backend sürümünü o tabloyla karşılaştır.
4. Yer tutucuları değiştir (§2) ve `util/Config.js`'i servisin entity/alan adlarıyla doldur.
5. Ekran alanlarını (kolonlar, seçim alanları, değişiklik ekranı alanları) uygulamanın kendi tasarımına göre
   yeniden yaz — şablondaki alanlar örnektir. Tekrar kullanılan şey **akış ve altyapıdır**, alan kümesi değil.

## 2. Yer tutucular

| Yer tutucu | Nerede | Değer |
|---|---|---|
| `com.example.alan.uygulama` / `com/example/alan/uygulama` | tüm `webapp/`, `package.json`, `ui5*.yaml` | uygulama namespace'i (std/03 §2 adlandırma). Noktalı ve eğik çizgili iki biçimin İKİSİ de değiştirilir |
| `<TEMA>` | `index.html`, `ui5.yaml` | §3 tema kuralı |
| `<UYGULAMA_BASLIGI>` | `index.html` `<title>` | tarayıcı sekmesi başlığı (uygulama başlığı i18n `appTitle`'dan ayrı, düz metin) |
| `<MANIFEST_SURUMU>` | `manifest.json` `_version` | `surum/<v>/README.md` |
| `<BACKEND_UI5_SURUMU>` | `manifest.json` `minUI5Version` | 1. adımda ölçülen `version` |
| `<SERVIS_ADI>` | `manifest.json` `dataSources` | OData V2 servis adı |
| `<DEV_HOST>` · `<PORT>` · `<CLIENT>` | `ui5.yaml`, `ui5-deploy.yaml` | `.conn_adt` ile birebir aynı host (std/03 §2.4) |
| `<BSP_ADI>` · `<SAP_PAKET>` · `<TRANSPORT_NO>` · `<UYGULAMA_ACIKLAMASI>` | `ui5-deploy.yaml`, `package.json` | deploy hedefi (deploy yalnız `deploy_ui.py` ile) |
| `ZSD001_*` adları | `util/Config.js`, `view/*.xml`, `controller/List.controller.js` | demo entity/VH adları — servisin gerçek adlarıyla değişir |
| `ZSD000_UI_VARIANT_O2` · `ZSD000_C_UI_VARIANT` | `util/Config.js` `VARIANT` | varyant servisi (`backend-referans/`) |

Değiştirme sonrası kontrol: kopyada `<[A-Z_]+>` ve `com.example` araması **0 sonuç** vermeli.

## 3. Tema kuralı

`GET <backend>/sap/public/bc/ui5_ui5/resources/sap/ui/core/themes/sap_horizon/library.css` **200 döner VE içeriği
`.../themes/base/library.css` ile aynı DEĞİLSE** (md5 farklı) → `sap_horizon`; değilse → `sap_fiori_3`.

Neden yalnız "200" yetmez (ölçüldü 2026-11-02, CDN): 1.71.85'te `sap_horizon/library.css` **200** döner ama
md5'i `base/library.css` ile **aynıdır** (tema yok, temel stile düşüyor); 1.120.52'de farklıdır.
Backend ICF'nin aynı davranışı gösterip göstermediği **DOĞRULANAMADI** — kural iki durumu da kapsar.

## 4. Sürüm yüzeyi — hangi API nerede (kanıt)

Kural: **ortak gövde (`app/`) yalnız 1.71.85'te DE var olan public API'yi kullanır.** Sürüme bağlı ya da
UI5-özel (alt çizgili) API `surum/<v>/webapp/util/SurumParca.js`'te yaşar.
Ölçüm kaynağı: `https://ui5.sap.com/<sürüm>/resources/<modül>-dbg.js` (1.71.85 ve 1.120.52, 2026-11-02).

| API | 1.71.85 | 1.120.52 | Yer |
|---|---|---|---|
| `sap.ui.table.rowmodes.Auto` · `Table.rowMode` | modül 404; aggregation `hidden` | var (`@since 1.119`) | `SurumParca.satirModu` |
| `Table.visibleRowCountMode` + `minAutoRowCount` | var | deprecated (1.119) | `SurumParca.satirModu` (yalnız 1.71) |
| `sap.m.IllustratedMessage` | 404 | var (`@since 1.98`) | `SurumParca.bosDurum` |
| `sap.ui.core.IAsyncContentCreation` | yok (core `library-dbg.js` 0 eşleşme) | var (`@since 1.89`) | `SurumParca.bilesenArayuzleri` |
| `MultiInput.addValidateToken` (public) | yok (yalnız iç `_tokenizer._addValidateToken`) | var | **kullanılmaz** — ortak gövde `addValidator` + `addToken` |
| MultiInput `_validateOnPaste` olayı (özel) | var | var | `SurumParca.yapistirmaBagla` (alt çizgili ⇒ ortakta değil) |
| Bootstrap öznitelik adları (`data-sap-ui-…`) | yalnız küçük harfe çevrilir — `oninit`, `resourceroots` (`jquery.sap.global-dbg.js:381-382`) | tireli ad camelize + küçük harf takma ad (`ui5loader-autoconfig-dbg.js:181,213`) | `surum/<v>/webapp/index.html` |
| Manifest `sap.app.i18n` nesne (`bundleUrl`…) | YOK — `Manifest-dbg.js:278-279` `new URI(sI18n)` | var (`Manifest-dbg.js:284`) | ortak gövde DİZGİ kullanır |
| ResourceModel `supportedLocales` · `fallbackLocale` | YOK (ResourceModel/ResourceBundle 0 eşleşme; kurucu yalnız `bundle`/`bundleName`/`bundleUrl`'ü okur ⇒ yok sayılır) | var | ortak (`models.i18n.settings`, 1.71'de etkisiz) |
| `Table` olayı `rowsUpdated` | YOK (yalnız özel `_rowsUpdated`, `Table-dbg.js:4064`) | var (`@since 1.86`) | **kullanılmaz** — kayıt sayısı satır binding'inin `dataReceived` olayından (`bindRows({events})`) |
| Aggregation binding bilgisi `events` (`dataReceived`) | var (`sap/ui/base/ManagedObject-dbg.js:3731` `bindAggregation` belgesi · `:3887` `_bindAggregation` → `attachEvents`) | var (`sap/ui/model/ManagedObjectBindingSupport-dbg.js:842` `_bindAggregation` → `attachEvents`; modül 1.71.85'te 404) | ortak |
| `Column` sıralı mı | `sorted` varsayılan `false`, `sortOrder` varsayılan `Ascending`, enum'da `None` YOK (`Column-dbg.js:131,138`) | `sortOrder` varsayılan `None`, `sorted` deprecated (`Column-dbg.js:130,136`) | `SurumParca.siraliMi` |
| MultiInput validator'ına gelen yazılı metin | HAM (`MultiInput-dbg.js:1147-1148` `_validateCurrentText` → `_addValidateToken({text})`) | KAÇIŞLI (`MultiInput-dbg.js:1992` `escapeSettingsValue`) | `SurumParca.dogrulayiciMetni` → ortak gövde HAM metinle çalışır, token'ı setter'la kurar |
| `MultiInput.addValidator` · `Tokenizer` validator `{text}` · `Token` `setKey`/`setText` | var | var | ortak |
| `Component.getOwnerComponentFor` · ODataModel `metadataUrlParams` · `requestFailed` parametreleri `url`/`method` | var | var | ortak |
| `Table` `getSortedColumns` · `attachFilter` · `enableColumnFreeze` · `threshold` · `extension` · `noData` (Control) | var | var | ortak |
| `ValueHelpDialog` `getTableAsync` · `setRangeKeyFields` · `supportRangesOnly` · `FilterBar` `advancedMode`/`basicSearch` | var | var | ortak |
| `sap.ui.export.Spreadsheet` modülü (`worker:false`) · `Dialog` `draggable`/`resizable` | var | var | ortak |
| Spreadsheet `dataSource` kabul ettiği girdi | URL dizgisi · dizi · `{dataUrl, …}` nesnesi — ListBinding dalı YOK (`sap/ui/export/Spreadsheet-dbg.js:431-444`) | + `ListBinding`/`TreeBinding` (`processDataSource` `@since 1.73`, `:612`) | ortak gövde iki sürümde geçerli biçimi kurar: `{type:"odata", dataUrl: binding.getDownloadUrl("json"), headers, count, useBatch:false}` — fixture V8 binding verilmesini yakalar |
| `ODataListBinding.getDownloadUrl(sFormat)` | var — `$format` + aktif `$orderby`/`$filter` + model URL parametreleri (`ODataListBinding-dbg.js:1128-1150`) | var — aynı + `Filter.NONE`'da `null` (`:1473-1501`) | ortak (`null` korumalı) |
| `DateFormat.getDateInstance({strictParsing: true})` ayrıştırma | varsayılan `medium` + yedek `short`·`medium`·`yyyy-MM-dd`·`yyyyMMdd` (`DateFormat-dbg.js:62-70`); `strictParsing` yedek biçimlere de geçer (`:2019-2020`, `:2085` `fallback.parse(…, bStrict)`) | aynı (`:90-98` · `:2895-2896`, `:2968`) | ortak (`util/Tarih.metindenGun`). **Tarayıcıda ölçüldü** (2026-11-02, `tr`): `strictParsing`'siz `31.11.2026`→1 Ara · `29.02.2026`→1 Mar · `00.11.2026`→1 Kas · `32.13.2026`→1 Şub 2027 (iki sürüm); sıkı ayrıştırmada dördü `null`, `02.11.2026` · `2 Kas 2026` · `2.11.26` · `2026-11-02` · `29.02.2028` doğru gün; `en`: `11/31/26`·`2/29/26`·`13/32/26` `null`, `11/2/26`·`Nov 2, 2026`·`2026-11-02`·`20261102` doğru |
| `NumberFormat.getFloatInstance({parseAsString: true})` ayrıştırma | var (`parseAsString` `@since 1.28.2`, `NumberFormat-dbg.js:311`); gruplama ayırıcısının YERİ denetlenmez (desen `[0-9<grup>]+`, `:1315`); `strictGroupingValidation` YOK (0 eşleşme; 1.84.62'de de yok, 1.96.51'de var) | aynı + `strictGroupingValidation` | ortak (`util/Sayi.metindenSayi` — gruplamayı aynı biçimle yeniden yazıp karşılaştırır, iki sürümde aynı davranış). **Tarayıcıda ölçüldü** (`tr`): `1.250`→`1250` · `1.250,5`→`1250.5` · `1,25`→`1.25` · `-1.250,5`→`-1250.5` · `12345678901234567890` kayıpsız; `1.25` · `12.34` · `1.2.3` · `01.250` · `12%` · `1e3` · `abc` → `null` (`en`: `1,250`→`1250`, `1,25`→`null`) |
| V2 `$filter` sayı literali (`ODataUtils.formatValue`) | dizgi birleştirme: Decimal `v+"m"` · Int64 `v+"l"` · Double `v+"d"` · Single `v+"f"` · Int32/16/Byte `String(v)` (`ODataUtils-dbg.js:535-553`) | aynı (`:559-577`) | ortak gövde kanonik dizgi (`"1250"`) verir; tarayıcıda `1250m`/`1250`/`1250l`/`1250d` ölçüldü. Ham TR metni `"1.250"` → `1.250m` (eski kod, ölçüldü) |
| `ListBinding.getCount()` | YOK (`@since 1.93.0`) | var — V2 `isLengthFinal() ? getLength() − inaktif` (`ODataListBinding-dbg.js:2259-2266`); Excel `getCountFromBinding` önce bunu okur (`ExportUtils-dbg.js:1408-1418`) | **kullanılmaz** — ortak `isLengthFinal() ? getLength()` |

**Ortak gövdede bulunmaması gereken desenler** (fixture V2 zorlar, 11 desen; yorumlar hariç): `IllustratedMessage` ·
`rowmodes` · `sap/m/VariantManagement` · `sap.m.VariantManagement` · `IAsyncContentCreation` · `addValidateToken` ·
`_validateOnPaste` · `data-sap-ui-` · `"bundleUrl"` · `rowsUpdated` · `getSortOrder()` ile `"None"` karşılaştırması.
Fixture ayrıca `index.html`'in sürüm parçasından geldiğini ve öznitelik biçiminin sürüme uyduğunu (V6),
`sap.app.i18n`'in dizgi olduğunu (V7) ve ortak gövdedeki her Spreadsheet `dataSource`'unun `dataUrl` anahtarlı bir
nesne değişmezi olduğunu (V8 — değişken/binding verilirse FAIL; nesnenin içeriğinin doğruluğunu ÖLÇMEZ) ve kolon
filtresinin metni ham filtre değeri yapmadığını (V9 — `strictParsing`/`parseAsString` taşıyan çağrı + ayrıştırıcı
çağrısı; sözdizimsel) zorlar.

**Bilinçli istisna (ortakta kalan UI5-özel alan):** `util/TablePersonalizer.js` ana modelin `aUrlParams` /
`mMetadataUrlParams` alanlarını okur (sap-client'ı varyant servisine taşımak için, std/03 §18.5b). Alanlar
tip korumalı okunur; yoksa çereze düşer, patlamaz. İki sürümde de var (ölçüldü).

## 5. Şablonun taşıdığı kurallar (nerede)

| Davranış | Dosya | Kaynak kural |
|---|---|---|
| Liste = `sap.ui.table.Table` grid, native kolon menüsü | `view/List.view.xml` | std/03 §10.0, ADR 0008, `check_list_view_grid` |
| SELECT-OPTIONS paritesi, harf duyarsız arama, `caseSensitive` YOK | `controller/Filter.controller.js`, `util/TokenValidator.js` | std/03 §10.0.1, `check_filter_search_pattern` |
| Yazılı metin token'a dönüşmeden Listele YOK | `Filter.controller.js` `_untokenizedFields` | std/03 §10.0.1 |
| Kolon kişiselleştirme + kullanıcı varyantı (servis yoksa uyarı + yerel) | `util/TablePersonalizer.js` | std/03 §16, checklist `UI-PERSO-01` |
| sap-client'ın varyant servisine taşınması | `util/TablePersonalizer.js` | std/03 §18.5b |
| Grid veri hatası görünür (sessiz boş liste YOK); yalnız grid'in kendi GET isteği — kaydetme hatası ikinci kutuda çıkmaz | `List.controller.js` `_gridIstegiMi` · `_onRequestFailed` | playbook `ui-freestyle-odata-v2.md` |
| Tarih-yalnız alan: takvim gününün UTC gece yarısı — seçim ekranı sınırları, grid kolon başlığı tarih filtresi (metin oturum dilinin biçimiyle SIKI ayrıştırılır — olmayan gün bir sonraki aya kaymaz), gönderilen gövde (backend'den okunan UTC gece yarısı korunur) | `util/Tarih.js` (`BaseController.utcGun` · `TablePersonalizer` · `Change._pick`) | bug-checklist FE-45 |
| Sayı kolonu başlık filtresi: metin oturum dilinin sayı biçimiyle ayrıştırılır, OData'ya kanonik dizgi gider (ham `1.250` → `1.250m` YOK) | `util/Sayi.js` · `TablePersonalizer._onColumnFilter` | §4 `NumberFormat` |
| Kolon filtresine ayrıştırılamayan metin: kolonun önceki geçerli filtresi KORUNUR (binding'e dokunulmaz, menü metni geri çekilir), mesaj bunu söyler; önceki yoksa "uygulanmadı" — tarih ve sayı dalı aynı | `TablePersonalizer._onColumnFilter` | — |
| Kaydetme: JSON tampon, sıralı çağrılar, gerçek SAP mesajı, `MessageBox.success` sonrası navigasyon; yarıda kalan kaydetmede kayıt yeniden okunur (çift POST / tekrar DELETE YOK) | `controller/Change.controller.js` `_runSeq` · `_err` · `_load` | playbook §B/§K1, std/03 §7.6, bug-checklist FE-38/FE-29 |
| Kolon penceresi açılışta uygulanmış varyantı gösterir | `util/TablePersonalizer.js` `_seciliAnahtar` | std/03 §16 |
| Excel: filtreye uyan tüm satırlar (aktif seçim + kolon filtresi + sıralama, `getDownloadUrl`), kapsam sorusu; URL üretilemezse `Log.warning` + mesaj (sessiz dönüş YOK) | `List.controller.js` `onExportExcel` · `_doExport` | std/03 §16 |
| Varsayılan varyant değişimi SIRALI (önce eski kapatılır, sonra yeni açılır; kısmi hatada iki varsayılan kalmaz) | `util/TablePersonalizer.js` `_setVariantAsDefault` | bug-checklist FE-38 |

## 6. Kopyadan sonra ölçüm

```
python core/scripts/validators/check_ui5_freestyle_traps.py
python core/scripts/validators/check_list_view_grid.py
python core/scripts/validators/check_filter_search_pattern.py
python core/scripts/check_ui_odata_refs.py --app <source_root>/<MODÜL>/<PAKET>/ui/<uygulama>
```

İlk üçü proje kökünü `CLAUDE_PROJECT_DIR`'den alır ve **kaç dosya taradığını** yazar — `0 dosya` görürsen
kopya yanlış yerdedir, sonuç okunamaz. Dördüncüsü canlı servisin `$metadata`'sına karşı entity/alan
adlarını doğrular (SAP bağlantısı ister). Checklist: `playbook/checklists/ui-freestyle-creation.md`.
Şablonun kendi testi: `tests/fixtures/ui5_freestyle_sablon/run.py` (iki sürüm parçasıyla sentetik projeye
kopyalar, üç validator'ı koşar, sürüm yüzeyi kuralını zorlar).

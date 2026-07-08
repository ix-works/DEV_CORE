---
layer: L3
scope: project-wide
type: pattern-bank
applies-to: ui-freestyle
last-updated: 2026-05-15
source: ORDER (ZSD001) ilk freestyle RAP-tüketen UI — ilk yayından kapanışa
        kadar yaşanan TÜM UI patinajları (ADT/backend HARİÇ; o adt-rap.md §32)
---

# Freestyle UI5 + OData V2 (RAP tüketen) — Operasyonel Tecrübe Bankası

> **Neden ayrı dosya?** `adt-*` playbook'ları SAP ADT/backend içindir.
> Bu dosya **tarayıcı tarafı** (freestyle UI5, OData V2 ODataModel, SelectDialog,
> TablePersoController, JSON buffer) deneyimidir. ORDER'de — görece BASİT bir
> uygulama — burada **çok fazla patinaj** yapıldı. ORDER_ORDER ve sonraki
> tüm freestyle uygulamalarda bu patinaj **tekrarlanmamalı**.
>
> Kullanım: yeni bir freestyle UI'a başlamadan **§0 PRE-FLIGHT**'ı uygula;
> bir UI hatasıyla karşılaşınca §1+ semptom tablosuna bak. ZSD001'e özel
> notlar `[zsd001]` etiketli; geri kalan **tüm geliştirmelerde ortak**.
>
> **Editör desteği (kurulu olmalı):** view/manifest yazarken **UI5 Language
> Assistant** (control API + i18n key doğrulama) ve **ESLint** (controller `.js`
> kalite) açık olsun; XML/YAML için redhat eklentileri. Kurulum + "hangi iş →
> hangi eklenti": [`governance/vscode-setup.md`](../governance/vscode-setup.md).
> Kesin control-API doğrulaması için Claude tarafında `ui5-mcp-server` linter'ı.

---

## §0 YENİ PROGRAM UI — PRE-FLIGHT (patinaj önleyici, BAŞTAN uygula)

Yeni freestyle UI iskeletini kurarken, kod yazmadan önce bunları **karara bağla**:

1. **Bootstrap (kopyala, doğrulanmış):** `index.html` UI5 sürümü **PIN'li**
   (`https://ui5.sap.com/1.120.x/resources/sap-ui-core.js`) +
   `data-sap-ui-language="tr"`. `manifest.json` modelleri: `i18n` +
   `""` (OData V2: `defaultBindingMode:TwoWay`, `useBatch:false`,
   `defaultCountMode:Inline`) + `ui` (JSON: `{busy,filter:{}}`).
   Component.js'te kullanılan her model `sap.ui.define` deps'inde.
2. **Editable child grid var mı?** (composition child satırları ekrandan
   eklenip/silinip/düzenlenecek mi?) → **VARSA**: en baştan **JSON edit-buffer
   mimarisi** kur (§1-B3). V2 nav-binding + `createEntry` ile editable grid
   yapmaya **ÇALIŞMA** — bu tek başına ORDER patinajının ~%60'ıydı.
3. **Save akışı şablonunu** (§1-B kutusu) baştan koy: blur→`setTimeout(0)`→
   `isNew ? deepCreate : (headerMERGE + childCreate/Update/Delete)` → **SIRALI**
   (`_runSeq`) → tek `_ok/_err`. `hasPendingChanges()` ön-gate KULLANMA.
4. Her numeric/date OData binding'ine **OData type** ekle (D1). CHAR1 flag
   alanları için **CheckBox pattern** (D2).
5. Value-help için **generic helper** (C1/C3): model + kontrolü DİREKT yaz;
   `<X>Name` alanını CDS projeksiyonda expose et, `description` bind et.
6. **Liste ekranı = ZORUNLU ALV-paritesi standardı (ADR 0008, §E):**
   kullanıcı istemese bile `TablePersonalizer.js` (kanonik util)
   **kopyalanır** — kolon-başlığı sort/filtre + aktif filtre çubuğu +
   **Kolonlar göster/gizle** + Excel (kapsam sorulu). Sıfırdan
   filtre/sort/export YAZMA. Kolonlara sabit `id` (colId↔meta).
7. Benign konsol gürültüsünü (§A3) **kovalama** — saat kaybı.
8. **Backend host = kanonik `<SYSTEM_ID>.SAP.EXAMPLE.COM.TR:44300`** —
   TÜM `ui5*.yaml` dosyalarında (`ui5.yaml`, `ui5-local.yaml`, `ui5-mock.yaml`,
   `ui5-deploy.yaml`). App generator'ın yazdığı eski alias (kanonik-olmayan DNS)
   host'u **yanlış sisteme gider → lokal çalıştırmada user&pass sonsuz 401
   döngüsü** (kimlik doğru olsa bile). İki kez yaşandı (2026-06-04 deploy,
   2026-06-11 local-run). Yeni app generate edilince ilk iş: tüm yaml'larda
   host'u grep'le doğrula.
9. **Lokal user&pass popup → iki tuzağı AYIR (sonsuz döngü ≠ hesap kilidi):**
   (a) Popup döngüsü + log'da `lrep`/`flex/data` çağrısı varsa → `index.html`
   bootstrap'a `data-sap-ui-flexibility-services="[]"` + `npm run start-noflp`
   (FLP `flp.html` değil, `index.html` aç). (b) Popup ISRARLA geliyor ama log'da
   yalnız app `$metadata` 401'i varsa → büyük ihtimalle **SAP kullanıcısı kilitli**;
   **deneme yapma** (kiliti uzatır), MCP `adt_get` ile aynı kullanıcı 401 mı diye
   teyit et → kilitse Basis SU01 unlock. Per-app reçete: ilgili UI klasöründe
   `RUN.md` (örn. `ZSD001_CLC/ui/order_app_rap/RUN.md`). 2026-06-11'de bu ayrım
   bilinmediği için ~1 saat kayıp.

> Bu maddeler baştan uygulanırsa ORDER'deki patinajların neredeyse tamamı
> oluşmadan biter.

---

## §A Bootstrap / ortam

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| A1 | Beyaz ekran, `getDatePlaceholder is not a function` | `index.html` UI5 sürümü pinli değil (CDN latest kırıyor) | UI5 sürümünü pinle + `data-sap-ui-language="tr"` | all (std `03-coding-ui-fiori.md` §2.5) |
| A2 | Model `undefined`, binding çalışmıyor | Component.js'te model require edilmemiş / manifest model eksik | manifest 3 model (i18n/""/ui); Component deps tam | all |
| A3 | Konsolda `Component-preload.js 404`, `favicon 404`, `fallbackLocale 'en' not in supported locales`, "Defining object type 'Object' deprecated" | Dev modda (build yok) **normal**; locale uyarısı benign | **Kovalama.** Hata değil. Sadece gerçek `Error`/kırmızı stack'e bak | all |

---

## §B OData V2 ODataModel davranışı (EN ÇOK PATİNAJ BURADA)

```
╔═ SAVE AKIŞI ŞABLONU (freestyle V2 + RAP, kanıtlanmış) ═══════════════╗
║ onSave: aktif elemanı blur() → setTimeout(0) → _save()               ║
║ _save():                                                             ║
║   isNew → oModel.create("/Root", {...header, to_Child:{results:[]}}, ║
║           {success:_ok, error:_err})        // TEK nested POST        ║
║   mevcut→ SIRALI (_runSeq, paralel DEĞİL):                           ║
║       1) oModel.update("/Root('k')", header, {merge:true})           ║
║       2) her __new child  → oModel.create("/Root('k')/to_Child", …)  ║
║       3) her değişmiş child→ oModel.update("/Child(key)", … merge)   ║
║          (child KEY alanı gövdeye KONMAZ)                            ║
║       4) her silinen child → oModel.remove("/Child(key)")            ║
║     → hepsi sırayla → tek _ok / _err                                 ║
║ _ok: MessageToast saved + setEdit(false) + model.refresh + navTo     ║
║ _err: MessageBox.error(saveFail + _parseError(oErr))  // GERÇEK mesaj ║
║       (_parseError: responseText→error.message.value; B9)            ║
║ hasPendingChanges() ön-gate KULLANMA (yanlış "değişiklik yok").      ║
╚══════════════════════════════════════════════════════════════════════╝
```

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| **B1** | `Resource not found for segment '_X'` | V2 composition nav property `to_<assoc>` (SADL `to_` prefix), `_<assoc>` DEĞİL | expand + binding hep `to_Destination` | all |
| **B2** | Save'e basınca "reaksiyon yok" / sessiz | `createEntry` **deferred** (submitChanges şart); deep nav path'e `createEntry` exception atıp akışı sessiz kesiyor | `create/update/remove` **anında** gönderir (kendi success/error). Editable child + deep create'te `createEntry` KULLANMA | all |
| **B3** | "Liman Ekle" satırı anında gelmiyor, save'e basınca geliyor | V2 nav-binding transient/yeni parent altında client `createEntry`'yi göstermiyor | Edit oturumu **client-side JSON buffer** (`v`: `{h:{},d:[]}`). OData yalnız load (`read $expand`→buffer) + save (explicit). Form/tablo buffer'dan → ekle/sil ANINDA | all |
| **B4** | Yeni kayıt+child kaydedilemiyor | Parça parça createEntry deep submit kırılgan | Deep-create = TEK nested POST `oModel.create("/Root",{...h, to_Child:{results:[...]}})` (e2e 201 kanıtlı; backend early numbering anahtarı atar) | all |
| **B5** | Mevcut child satırı değiştirip kaydet → eski değer geri geliyor | `_save` sadece yeni child create + silinen remove yapıyor; **değişmiş mevcut child UPDATE'i unutulmuş** | Mevcut (≠`__new`) her child için de `oModel.update("/Child(key)", …, merge)` gönder; KEY alanı gövdeye koyma | all |
| **B6** | "Bloke edildiği için düzenlenemez" çıkıyor ama işlem yine de oluyor | RAP `lock master` BO'ya **paralel** change isteği (header PUT + child POST/DELETE aynı anda) = lock çakışması | Save op'larını **SIRALI** çalıştır (`_runSeq`: her biri öncekinin bitişini bekler), `jQuery.when`/paralel DEĞİL | all (RAP-tüketen) |
| **B7** | İlk Kaydet'te aksiyon yok, ikincide oluyor / "Kaydedildi" gelmiyor | `hasPendingChanges()` ön-kontrolü iki-yön binding gecikmesinde `false` döndürüp save'i yutuyor | JSON buffer + explicit save → gate gereksiz; başarı callback'i garantili mesaj. blur+`setTimeout(0)` aktif input commit için kalsın | all |
| **B8** | Başlık kaydolur ✅ ama kalem "Kaydedilemedi" ❌ | Save-payload/binding property adı **canlı `$metadata`'da YOK** — eski alias veya `ref_docs` CDS'inden kopya; projeksiyon sonradan yeniden-adlandırılmış (ZSD001 `FinalAddress`→`FinalPartnerAddress`). O alanı içeren MERGE 400, içermeyen (başlık) geçer | Her binding + MERGE alan adını **aktif projeksiyon `$metadata`/`adt_get`** ile birebir doğrula; `ref_docs` eski CDS'e güvenme | all |
| **B9** | "Kaydedilemedi" çıkar ama **neden** belli değil → kör deneme-yanılma | error callback sabit i18n (`_t("msg.saveFail")`) gösterir, gerçek `responseText` SAP mesajını parse etmez | Her error callback'e `_parseError(oErr)` ekle (`JSON.parse(responseText).error.message.value`, fallback `oErr.message`); createEntry/batch'te `__batchResponses`/`__changeResponses` ≥400 yanıtını da bas. Kanıt: ZSD001 BaseOrder `_parseError` | all |

---

## §C Value-help (SelectDialog, kod+ad)

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| C1 | F4'ten seçilen değer ekrana yansımıyor | Sadece model binding'e güvenmek (binding quirk / path / context) | confirm'de `oInput.setValue(code)` + `oInput.setDescription(name)` **DİREKT** kontrole + ayrıca model property'sine yaz | all |
| C2 | Value-help'li alanda kod görünüyor, ad yok | Entity'de ad alanı yok | CDS projeksiyonda assoc ile `<X>Name` expose; UI `description="{…Name}"`; confirm'de adı anında bas (assoc read-only, refresh'e kadar boş kalır) | all (+backend) |
| C3 | Tek `_openVH` hem header hem satır için | header = absolute path (context yok), satır = relative + row context | `oInput.getBindingContext("v")` var mı ile ayır; `model.setProperty(path,val,rowCtxOrUndefined)` | pattern |
| C4 | F4 seçimi **yanlış alana** yazılıyor (aynı tipte 2+ alanda; örn. Firma/Hat ikisi de BP) | Tek handler birden çok alana hizmet ederken yazma hedefini **sabit** veriyor (örn. hep `/h/Partner`) → hangi alandan açılırsa açılsın aynı yere gider, diğeri boş kalır | Hedefi **çağıran input'un value binding path'inden türet**: `oEvent.getSource().getBinding("value").getPath()` → path'e göre dallan (`/LinePartner$/.test(p) ? "/h/LinePartner" : "/h/Partner"`). Asla sabit verme. Yakalama: her F4'ten sonra **kendi** alanı doluyor mu kontrol et (ORDER Hat→Firma kayması, Playwright ile yakalandı 2026-06-02, commit `b7a395f3`) | pattern |
| C5 | **Rapor filtre ekranı = SELECT-OPTIONS** (çoklu-değer + aralık), tek-değer Input değil; **harf-duyarsız "içeren" arama 400 / hiç sonuç yok** | `caseSensitive:false` → UI5 V2 `$filter`'a `toupper()`/`tolower()` enjekte eder; SAP Gateway (/IWBEP) bunları **DESTEKLEMEZ** → HTTP 400 "Function toupper/tolower is not supported" (SAP Note 1797736) → VH/grid araması hiç sonuç döndürmez | (1) Filtre alanı = `sap.m.MultiInput` + `sap.ui.comp` `ValueHelpDialog` (değer-tablosu + ranges sekmesi). (2) VH araması/grid filtresi/düz-token = `new Filter(field, FilterOperator.Contains, q)` — **caseSensitive parametresi VERME** → düz `substringof` zaten harf-duyarsız (DB collation; canlı: `gül`→`GÜLAK` 200). (3) Wildcard ortak `_parseSearchTerm`: `x*`→StartsWith · `*x`→EndsWith · `*x*`/`x`→Contains (startswith/endswith /IWBEP'te DESTEKLENİR). (4) Grid: `TablePersonalizer._onColumnFilter` native filtreyi `preventDefault` + string kolonda düz Contains (caseSensitive YOK). (5) Kod/serbest-metin alanı düz-token default `Contains` (`defaultOp`). **Kanonik: `ZSD001 <report>_app` — kopyala.** Gate: `check_filter_search_pattern.py` (FE-32) | all (rapor/liste) |

---

## §D Binding tipleri

| # | Semptom | Kök neden | Çözüm | Kapsam |
|---|---|---|---|---|
| D1 | `CX_SXML_PARSE_ERROR` / parse hatası (sayı/tarih alanı) | OData numeric/date binding'inde tip belirtilmemiş | `sap.ui.model.odata.type.Int32` / `…DateTime` + `constraints:{displayFormat:'Date'}` ZORUNLU | all |
| D2 | `CheckBox "" is of type string, expected boolean` | CHAR1 bayrak ('X'/'') alanı CheckBox'a doğrudan bağlanmış | `selected="{= ${path} === 'X' }"` (display) + `select` handler ile `'X'`/`''` geri yaz (JSON buffer'a). Klasik "Durum" gibi | all |

---

## §E Liste ekranı = GRID (sap.ui.table) ALV standardı (ADR 0008; grid KANITLANDI 2026-06-08)

> **ZORUNLU:** ALV-tarzı liste/rapor ekranları **`sap.ui.table.Table` (grid)** ile yapılır
> (masaüstü, çok-kolon, **yatay scroll** + **sanal scroll** + kolon resize/reorder/freeze +
> native sort/filter). Mobil-öncelikli veya hücre-zengin/değişken-yükseklik ekranlar için
> `sap.m.Table` (responsive) **istisna** (§E-LEGACY). Kanıt: birden çok rapor app'i (ZSD001 örneği).
> **Kanonik reusable util:** `ERP/SD/ZSD001_CLC/ui/<report>_app/webapp/util/TablePersonalizer.js`
> (grid sürümü; tüm app'lerde birebir, sadece namespace farkı). **Kanonik şablon app (kopyala-uyarla):**
> `ERP/SD/ZSD001_CLC/ui/<report>_app/` — yeni rapor = bunu kopyala + kolon/filtre/servis değiştir, sıfırdan yazma.

**GRID KURULUM (5 parça):**
1. **manifest** libs: `sap.ui.table` + `sap.ui.export`. View `xmlns:table="sap.ui.table"`.
2. **table:Table**: `visibleRowCountMode="Auto"` (`minAutoRowCount` ~10), `selectionMode="None"` (saf liste) / `"Single"` (master-detail), `enableColumnReordering` + `enableColumnFreeze`, `threshold="200"` (OData lazy), `rows="{/Entity}"`. Toolbar → **`table:extension`** (OverflowToolbar: başlık + Kolonlar + Excel + Yenile).
3. **table:Column** (her biri): `width` tip-bazlı (date 7rem · time 6rem · amount/qty 8rem `hAlign="End"` · kısa kod 8rem · ad/uzun/concat 16rem · default 10rem) + `sortProperty` + `filterProperty` + `<Label text="{i18n>..}"/>` + `<table:template><Text wrapping="false"/>`. **Key alanlar başta.**
4. **Sort/filter = grid NATIVE kolon menüsü** (`sortProperty`/`filterProperty` ile otomatik gelir). m.Table'daki custom `columnmenu.Menu` + `infoToolbar` GEREK YOK. Native kolon filtresi + Filter-ekranı base filtresi otomatik AND'lenir (binding `.filter(aFilters, "Application")`).
5. **Kolon göster/gizle + VARYANT + Excel = TablePersonalizer** (aşağıda).

**Binding:** `oTable.getBinding("rows")` (m.Table'da `"items"` idi); `onUpdateFinished`→`rowsUpdated` event, sayı `getLength()`. master-detail (voyage): `selectionMode="Single"` + key kolonda `Link press` veya satır `rowActionTemplate type=Navigation` → `navTo` detail.

**TablePersonalizer (grid sürümü):**
- "Kolonlar" → geniş ortalanmış `sap.m.Dialog` (arama + Tümünü Seç/Kaldır + scroll; kolon isimleri TAM).
- **DB-backed varyant** (OData servisi `ZSD000_UI_VARIANT_O2`; localStorage fallback): `Config = {cols:[{key,visible,width,index}]}` **TAM layout** (görünürlük+genişlik+sıra). **Farklı Kaydet** (ad **≤14 char** = VariantName CHAR14) / **Sil** — `MessageBox.confirm` onaylı. **Varsayılan Yap (★)** → IsDefault; ekran açılışında o varyant **otomatik** uygulanır.
- **Excel** `sap.ui.export.Spreadsheet`, kapsam sorulu (Görünür/Tüm), `getColumnsForExport(bAll)`.

**TUZAKLAR:**
- **Concat alan** (raw kod yok, "kod-tanım"): F4 VH kodu verir → filtre concat alanına `StartsWith "<kod>-"` (örn. ZSD001 kdgrp/bzirk).
- **Backend (salt-okunur rapor RAP'i):** wrapper view entity (`as select from <klasik DDL>`, key + `@AccessControl #CHECK`) + DCL (`V_VBAK_VKO`/VKORG/ACTVT=03) + SRVD (`expose` main + ortak `ZSD000_I_*VH`) + SRVB (OData V2) publish. **EXCRT/kur conversion-exit alanları → `cast(.. as abap.dec(9,5))`** (yoksa OData publish ERROR "Do not use conversion exit"). Recete: bu dosya + `playbook/ui-backend-rap.md`.

## §E-LEGACY m.Table (mobil/hücre-zengin istisna)
ALV-grid gerekmeyen, mobil-responsive veya hücre-zengin (wrap, değişken yükseklik) ekranlarda `sap.m.Table` + (eski) `columnmenu.Menu` per-kolon sort/filtre + `infoToolbar` aktif-filtre çubuğu. Yatay scroll/sanal scroll YOK; kolon native menüsü yerine custom. DENENMİŞ-BAŞARISIZ (her ikisinde): `sap.m.P13nDialog`/`P13nFilterPanel` (model-sync kopuk → KULLANMA); `sap.m.TablePersoController` (native Promise `t.done` route çöker). reusable util **kopyalanır**, sıfırdan yazılmaz.

---

## §F Tasarım / UX rötuş

| # | Kural | Kapsam |
|---|---|---|
| F1 | Sayfa başlığında zaten görünen anahtarı (ör. belge no) ayrıca form alanı yapma | all |
| F2 | Form compact: `SimpleForm` `columnsXL` artır + `labelSpan*` daralt + `adjustLabelSpan="false"` + Panel margin sınıfı `sapUiResponsiveMargin`→`sapUiSmallMarginBeginEnd`/`sapUiTinyMarginTop` (alttaki bölüm yukarı kayar) | all |

---

## §H Kopyalanan UI'ı yeni servise uyarlama (SEGW→RAP göçü) — STATİK CROSS-CHECK

> **Bağlam:** Çalışan bir UI'ı (ör. SEGW OData) yeni bir servise (ör. RAP `_O2`) bağlarken
> hataları **tarayıcıda tek tek tıklayarak** bulmak verimsiz ve eksik (sadece o ekrana
> girince patlar). Doğru yöntem: UI'ın TÜM OData referanslarını canlı `$metadata` ile
> **statik karşılaştır**. Klasik SEGW UI'ı → RAP göçünde kanıtlandı.

**Tek komut (her kopya-UI uyarlamasından sonra ZORUNLU):**
```powershell
python scripts/check_ui_odata_refs.py --app ERP/SD/<PKG>/ui/<app> --service <SRVB_ADI>
```
callFunction→FunctionImport(+param), read/binding→EntitySet, Filter/$orderby/$select→Property
kontrol eder; KIRMIZI uyumsuzlukta exit 1.

**SEGW→RAP göç tuzakları (hepsi gerçek bir göçte yaşandı + bu araçla yakalandı):**
| Tuzak | Belirti | Çözüm |
|---|---|---|
| **Namespace slash-form** kalıntısı | `Component yüklenemedi: failed to resolve 'com/.../model/models'` | Global rename SADECE nokta-formunu (`com.x.y`) değil **slash-formunu** da (`com/x/y`) kapsamalı. `sap.ui.define([...])` dep dizileri slash kullanır |
| **Function-import-as-entityset** (SEGW deseni) | `Resource not found for segment 'XxxResultSet'` | SEGW'de FI'ın `EntitySet`'i olabilir; UI `read("/XxxSet")` yapar. RAP'te FI'dır → `callFunction("/Xxx",{method:"GET"...})` |
| **Geçersiz FI parametresi** | action/function çağrısında `400 Invalid parameter` | SEGW gevşek; RAP-V2 metadata'da olmayan parametreyi reddeder. Fazla param'ı çıkar (ör. update'te `IvSoldToParty`) |
| **`[1]`-sonuç sarmalama** | `oData.Field` undefined | RAP-V2 `[1]` sonucu fonksiyon adı altında sarmalar → `oData.<Func> ‖ oData` unwrap. `[0..*]` → `oData.results` |
| **Result property casing** | UI'da boş alan | abstract result alan adları eski MPC property adıyla **birebir** (MessageText, SalesOrder — tek-capital değil) |
| **VH/entity set yeniden yerleşimi** | `Resource not found` (VH) | VH'ler başka pakete taşındıysa (ADR 0009 ZSD000) UI'daki `read("/ZSD001_I_*_VH")` → yeni ad |

---

## §G ZSD001'e özel (genel prensip de içerir)

| # | Not |
|---|---|
| G1 | **B.4 — composition child KEY alanı düzenleme:** child anahtarı (ORDER'de `DestinationPort`) kayıtlı satırda **salt-okunur**; değiştirmek = satırı **sil + yeni ekle**. BDEF `field ( readonly : update ) <KeyChild>` (server zorlar + "key field should be flagged readonly" uyarısını kapatır). UI: `editable="{= ${ui>/edit} &amp;&amp; !!${v>__new} }"`. **Prensip:** composition child'ın anahtarı olan her programda aynı (ORDER'te de muhtemelen geçerli) |

---

## §K KANONİK DESEN — KOPYALA, YENİDEN YAZMA (Booking post-mortem, ADR 0017)

> **NEDEN:** Booking UI (2026-06-16) çalışan kardeş deseninin **plumbing'ini** (sip_se/ihr_se save=`update`) yerine sıfırdan yazdı → çözülmüş mekaniği inferior desenle yeniden-implemente etti → saatlerce patinaj.
>
> **SINIR — bu §K *plumbing/mekanik* deseridir, app-kopyalama DEĞİL:** save/nav/setData/master-detail'in **tek-doğru-yolu** vardır ve **uygulamadan bağımsızdır** → buradaki mekaniği **referans al, sıfırdan icat etme** (icat = bug geri gelir). **Uygulamaya özel içerik HER ZAMAN bespoke yazılır** (hangi entity/servis, alan listesi, ekran layout/grid, iş/gating kuralları, VH hedefleri, label) — hiçbir ekran diğerinin kopyası değildir. Kural: *framework-plumbing = reuse · iş-içeriği = bespoke*. Statik tuzaklar `check_ui5_freestyle_traps.py` (G3) ile dayatılır; runtime G1 smoke-test ile.

### K1 — SAVE = sıralı `oModel.update(merge)` (setProperty + submitChanges DEĞİL)
JSON-model (`bk`) + `setProperty` change-detection **programatik-set değerleri** (auto-fill, cascade) güvenilir göndermez → "kaydetmiyor". Kardeşler (sip_se/ihr_se) `oModel.update()` kullanır. **Kanonik:**
```js
// Başlık + DEĞİŞEN mevcut kalemler: deterministik MERGE listesi
var aUpdates = [{ path: sHeaderPath, data: oHdr }];          // oHdr = sadece editable alanlar
// kalem: oCit[date] = c[f] || null  (tarih boşsa null; "" Edm.DateTime'da 400)
//        oCit[str]  = c[f] == null ? "" : c[f]
// yeni kalem -> createEntry(sHeaderPath + "/to_Container", {properties}); silinen -> oModel.remove(...)
var iUpd = 0;
(function next() {                                            // SIRALI: eş-zamanlı update = RAP BO kilit çakışması
  if (iUpd >= aUpdates.length) {
    if (oModel.hasPendingChanges()) { oModel.submitChanges({success: done, error: err}); } else { done(); }
    return;
  }
  var u = aUpdates[iUpd++];
  oModel.update(u.path, u.data, { merge: true, success: next, error: err });
})();
```
Kurallar: (a) **sıralı**, eş-zamanlı update aynı BO'da kilidi çakıştırır; (b) tarih boş = `null`, `""` değil; (c) sadece **editable** alanları gönder (readonly *Name/*Text payload'a koyma → 400 riski); (d) backend updatable mı emin değilsen tek-alan MERGE'i curl/gateway ile teyit et.

### K2 — V2 nav adı = `to_X` (CDS composition adı `_X` DEĞİL)
RAP composition `_Container`/`_Destination` → OData V2 metadata'da **`to_Container`/`to_Destination`**. `createEntry("_Container")`, `$expand:"_Container"`, `read(".../_Destination")` **sessizce kırılır** (Create kaydet boş, Change kalem yüklenmez). `$metadata`'dan nav adını DOĞRULA. (G3 T1 hard-block.)

### K3 — JSON-model `setData` TAM ŞEKİL korumalı
`_load` success'te `setData({header, containers})` → `sel`/`hasSel` **düşer** → detay paneli seçmeden açık + seçince dolmaz. Daima TAM şekil: `setData({ header, containers, sel:{}, hasSel:false, messages:[] })`.

### K4 — Master-detail (kalem tablo → detay panel)
`<Table mode="SingleSelectMaster" selectionChange=".onSel">`; detay `visible="{bk>/hasSel}"`. `onSel`: `getParameter("listItem")` → `setProperty("/sel", item.getBindingContext("bk").getObject())` + `hasSel=true`. **Re-navigation:** `_load`'da `byId("tbl").removeSelections(true)` (bayat seçim sonraki tık'ta selectionChange'i yutmasın).

### §J TUZAK LİSTESİ (her biri bir patinaj turu oldu — G3 statik, G1 runtime)
| # | Tuzak | Belirti | Çözüm | Gate |
|---|---|---|---|---|
| T1 | V2 nav `_X` | Create kaydet boş / $expand boş | `to_X` | G3 ERROR |
| T2 | grid/miktar Input `type="Number"` | ok-tuşu değer artırır, grid gezme bozulur | `type="Text"`+liveChange | G3 WARN |
| T3 | `core:Title` VBox/HBox/CSSGrid child | view render crash ("not valid for aggregation") | `sap.m.Title` | G3 WARN |
| T4 | save `setProperty`+submitChanges | programatik değer kaydedilmez | sıralı `update(merge)` (K1) | G1 |
| T5 | eş-zamanlı `update` | "Kaydedilemedi" (BO kilit) | sıralı zincir (K1) | G1 |
| T6 | MERGE'de boş tarih `""` | 400 (Edm.DateTime) | `null` | G1 |
| T7 | `setData` eksik şekil | detay açık/dolmaz | tam şekil (K3) | G1 |

---

## İlgili

- Standart (L2): [`../standards/03-coding-ui-fiori.md`](../standards/03-coding-ui-fiori.md)
- **Backend eşi (aynı mantık, bu dosyanın KAPSAMI DIŞI):** [`ui-backend-rap.md`](ui-backend-rap.md) — kanonik: [`adt-rap.md`](adt-rap.md) §32 (early numbering, MCP lock-cache, CDS/BDEF)
- Checklist (yeni UI öncesi): [`checklists/ui-freestyle-creation.md`](checklists/ui-freestyle-creation.md)
- Cross-cutting hata kataloğu: [`lessons-learned.md`](lessons-learned.md)

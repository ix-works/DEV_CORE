---
name: ui5-analyticaltable-v2-toplam-tuzaklari
description: "UI5 1.120 AnalyticalTable + analitik OData V2: group olayında senkron düzeltme tabloyu boşaltır · grup Σ provideGrandTotals'a bağlı · aynı alanda yalnız NE'ler AND · metadataLoaded() hata hâlinde asılı · getDownloadUrl initialize'sız $filter'sız"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir rapor geliştirmesinde (toplam / ara toplam, AnalyticalTable yöntemi) ölçülen beş tuzak (UI5 1.120.23, `sap.ui.table.AnalyticalTable` + `sap.ui.model.analytics.AnalyticalBinding`). Hepsi **sessiz**: hata yok, yanlış ya da boş ekran.

1. **`group` olayında aynı tikte düzeltme (ör. bir kolonu zorla ilk seviyeye taşıma) tabloyu BOŞALTIR.** İkinci `updateAnalyticalInfo` uçuştaki isteği düşürür, yanıt gelmez. Çare: düzeltmeden sonra `getBinding("rows").refresh()`; `expandAll` yalnız `dataReceived`'den SONRA.
2. **Grup Σ satırları `provideGrandTotals`'a bağlıdır** (`_createSumNode`). Genel Toplam kapatılınca grup ara toplamları da kaybolur — bu bir kusur değil kütüphane davranışı; FS/kılavuza not düşülür.
3. **Aynı alanda birden çok koşul:** AnalyticalBinding yalnız `NE`'leri AND'ler, diğerlerini OR'lar (`odata4analytics.js` ~3457-3461). Düz ODataListBinding ile aynı varsayılmaz.
4. **`oModel.metadataLoaded()` parametresiz çağrı, `$metadata` hata verirse hiç çözülmez** (asılı Promise); tembel yüklenen view `metadataFailed` olayını kaçırır. Çare: önce `isMetadataLoadingFailed()` bak, sonra `metadataLoaded(true)` (red de döner) + hata bayrağı.
5. **`AnalyticalBinding.getDownloadUrl()`** `initialize()` görmemiş binding'de `$filter`'sız URL döner ⇒ Excel filtresiz tüm veriyi çeker. Excel'den önce binding'in başlatıldığını doğrula.

Kanıt: tüketici projede FE ölçüm notu + ham ölçüm (yerel), TS'te kayıtlı.
İlişkili: [[feedback_ui5-suspended-binding-tablo-render-istegi-atar]] (aynı sınıf: binding yaşam döngüsü sessiz istek davranışı).
prior-art: yok (memory + core playbook'ta AnalyticalTable/metadataLoaded/getDownloadUrl araması 0).

Son-doğrulama: 2026-11-14
Applies-to: freestyle UI5 1.120 + analitik OData V2 (s4_private / ecc), AnalyticalTable kullanan raporlar

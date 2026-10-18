---
name: feedback_ui5-float-source-decimal-nokta-tr-yerelde-x1000
description: "UI5 type.Float'a source:{decimalSeparator:'.'} verip groupingSeparator VERMEMEK TR/DE yerelinde OData Decimal'i ×1000 gösterir, 0'ı boş bırakır — yalnız Log.error, İngilizce yerelde görünmez"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: e6519510-314a-4814-aecd-54e3e921866a
  modified: 2026-10-01T15:14:30.033Z
---

`sap.ui.model.type.Float` + `formatOptions.source: { groupingEnabled:false, decimalSeparator:'.' }`
(groupingSeparator YOK) → NumberFormat eksik seçeneği YERELDEN doldurur; TR/DE'de group='.' ⇒
kaynak biçimde ondalık = grup = '.'; `parse()` grup ayırıcıyı koşulsuz siler. OData V2
Edm.Decimal string'i "14.000" → **14000**, "0.000"/"0.500" → **boş**, "-5.000" → **-5000**.
Tek iz konsolda `Log.error "grouping and decimal separator both have the same value '.'"`.
UI5 1.120.23 kaynağıyla tarayıcıda ölçüldü (bir projenin delta bug-gate'i, 2026-10-01).

**Why:** FE uzmanı "source olmadan string değer biçimlenmiyor" gözlemiyle source ekledi, ama
yarım verdi; boş `source:{}` verildiğinde UI5 kendisi `groupingSeparator:','` koyar — yarım
nesne bu varsayılanı ezer. İngilizce yerelde (mock/Playwright varsayılanı) kusur görünmez;
`check_ui5_freestyle_traps` kuralı yok ⇒ ilk düzeltme turu kendi BLOCKER'ını üretti.

**How to apply:** Edm.Decimal metin bağlamasında ya `source:{}` (boş) ya
`source:{groupingSeparator:',', decimalSeparator:'.'}` (ikisi birden) ya da
`sap.ui.model.odata.type.Decimal` + constraints kullan. Biçim testini **TR yerelinde** yap
(`index.html` `data-sap-ui-language="tr"`), kesirli + 0 + eksi değerle. Validator adayı (T10):
`source` içinde `decimalSeparator` var, `groupingSeparator` yok → işaretle. Core FE-35 metni
bu tuzağı anmıyor — terfi adayı. İlişkili: [[feedback_abap-decimal-odata-serialize-locale]]
[[feedback_duzeltme-turu-kendi-regresyonunu-uretir]].

Son-doğrulama: 2026-10-01 · Applies-to: freestyle UI5 1.120 + OData V2, TR/DE yerel

---
name: feedback_i18n-tr-her-iki-dosya
description: "TR app'te etiket/metin değişikliği i18n.properties VE i18n_tr.properties ikisinde yapılmalı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ecec217-78c0-499b-ad67-bf1afb7f70a6
---

Freestyle UI5 app `data-sap-ui-language="tr"` ile çalışınca UI5 **`i18n_tr.properties`**'i yükler ve `i18n.properties`'i **override eder**. Bir i18n key'in metnini/etiketini değiştirirken yalnız `i18n.properties`'i değiştirmek YETMEZ — TR'de eski metin görünmeye devam eder. **HER İKİ dosyada** (`i18n.properties` + `i18n_tr.properties`) aynı key güncellenmeli. (Yeni key eklerken de ikisine.)

**Why:** voyage demuraj etiketi (2026-06-17) — yalnız i18n.properties düzeltilmişti, app TR olduğu için i18n_tr eski "Demuraj Free"yi override etti → kullanıcı eski etiketi gördü, 1 round-trip israf.

**How to apply:** i18n etiket/metin değişiminde: `grep <key> webapp/i18n/i18n*.properties` → bulunan TÜM dosyalarda güncelle. Değişiklik sonrası kullanıcıya **hard refresh (Ctrl+F5)** söyle (i18n bundle tarayıcıda cache'lenir, normal refresh yenilemez). İlgili: [[feedback_ui5-v2-plumbing-reuse-traps]].

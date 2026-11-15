---
name: feedback_ui5-yapici-ayarinda-suslu-parantez-baglamadir
description: "UI5 kontrol yapıcısına verilen metin `{...}` içeriyorsa bağlama sayılır ve boşalır — yer tutuculu (i18n) metni setText ile ver"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

UI5'te yapıcıya ayar (settings) olarak verilen dize **bağlama sözdizimi olarak ayrıştırılır**, ör. `new Text({ text: s })`. Metin `{PAKET_ID}` gibi bir yer tutucu içeriyorsa bu parça bir model yolu sanılır ve ekranda **boş** görünür (ör. ekranda yalnız "ör. , ." kalır). `new Text().setText(s)` ise dizeyi olduğu gibi yazar.

**Why:** Bir SD paketinin bilgi ikonu yardımcısında, mail şablonu açıklama metinleri bir yer tutucu listesi içeriyordu ve popover'da bu yer tutucular sessizce kayboldu. Mutasyonla ölçüldü: eski `new Text({text})` geri konunca senaryo kırmızıya düştü. (2026-11-12)

**How to apply:** Çalışma anında üretilen ya da i18n'den gelen ve `{` içerebilen her metni kontrolün yapıcısına değil, `setText`/`setTitle` gibi bir setter'a ver. Alternatif olarak yapıcıda `{ text: s }` yerine bağlamayı kapatan biçimi kullan. Yeni bir paylaşılan metin yardımcısı yazarken testine `{` içeren bir metin ekle.

Son-doğrulama: 2026-11-12
Applies-to: freestyle UI5 (sap.m), UI5 1.120.x

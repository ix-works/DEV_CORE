---
name: feedback_gateway-substringof-maxlength-400-ve-tr-harf-sinifi
description: "V2 arama: substringof terimi property maxLength'ini aşarsa TÜM istek 400 (diyalog sessizce 'bulunamadı'); sunucu harf duyarsızlığında {i,I,ı} tek sınıf, İ ayrı — 4 varyant + alan başına maxLength süzgeci"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 2b5ea0bf-6c01-4fdc-acb8-b62e8c4bccb5
  modified: 2026-10-09T19:24:15.221Z
---

SAP Gateway (SADL, OData V2) `$filter=substringof('<terim>',Alan)`: terim, alanın `$metadata` `MaxLength`'inden
uzunsa **isteğin tamamı HTTP 400** döner — OR zincirindeki tek bir kısa alan (ör. Pstlz 10) bütün aramayı öldürür.
UI5 tarafında hata yutulursa diyalog **sessizce "bulunamadı"** gösterir. Ölçüldü: DEV 2026-10-09, müşteri değer yardımları.

Harf duyarsızlığı tam Türkçe değil: `istanbul` 5 · `İstanbul` 10 satır döndü ⇒ sunucuda **{i, I, ı} tek sınıf, İ ayrı**.
Hem i hem ı içeren çok kelimeli küçük harfli terim (temsilî: `<ilçe>/<firma> ısıtma`) üç varyantla da bulunmadı.

**Why:** iki kusur da sessizdir (hata yok, boş liste) ve tek kelimelik testte görünmez — ilk gate'ten geçen
yardımcı bu yüzden çok kelimeli Türkçe adı kaçırdı.

**How to apply:** arama OR'unu kurarken ① her alanı `$metadata` maxLength'iyle süz (terimi aşan alanı çıkar; hiç
alan kalmazsa boş sonuç + "terim çok uzun" bilgisi) ② varyantlar: orijinal · i-sınıfı→`I` · i-sınıfı→`İ` ·
**TR büyük harf eşlemesi (i→İ, ı→I)** — tekilleştir ③ URL bütçesini ölç (4 varyant × 6-7 alan ≈ 6 KB < ~8,4 KB WD duvarı).
Vaka projesindeki uygulama `termVariants` + `searchFilter` yardımcılarıyla kuruldu (tüketici repoda).
Kelimeye bölüp AND yapılmadı (URL bütçesi) — tek adda karışık yazım (`OTOMOTIV … TİC`) yalnız kısa terimle bulunur.
İlgili: [[feedback_tr-karakter-varyantli-arama]] · [[feedback_rapor-filtre-select-options-contains-standardi]]

Son-doğrulama: 2026-10-09 · Applies-to: UI5 OData V2 freestyle + SAP Gateway/SADL (s4_private)

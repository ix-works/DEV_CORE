---
name: atc-fle-bulgusu-ci-fldext-ok-not-numarali
description: "ATC S/4 alan uzunluğu genişletmesi (FLE, ör. MATNR) bulgusu pseudo-comment ile bastırılır: \"#EC CI_FLDEXT_OK[<not no>] (ör. [2215424]) — ad denetim sınıfından okunur, tahmin edilmez"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: eb086373-3ff5-4f0b-9566-83527256cc5a
  modified: 2026-09-28T19:27:59.119Z
---

ATC'nin S/4HANA **Field Length Extension** denetimi (ör. MATNR 18→40, SAP Note 2215424) bulgusunu bilinçli muafiyetle kapatmak için bulgunun **satır sonuna** `"#EC CI_FLDEXT_OK[2215424]` yazılır — köşeli parantez içinde **not numarası** şarttır (düz `CI_FLDEXT_OK` değil).
- Ad tahminle bulunmadı: denetim sınıfları `CL_CI_TEST_FIELD_EXT` (~:301 / :9718) ve `CL_CI_S4H_COMMON` (~:730) canlı okunarak çıkarıldı.
- Canlı ölçüm: push sonrası o bulgu ATC'den kalktı (kaybolan bulgu = diff'teki bastırıcı; bulgu-bazlı eşleme yapılmadı).
- Yan gözlem (aynı turda): çok satırlı bir ifadede **son satır sonundaki** `##NO_TEXT` pragması tüm ifadeyi kapsadı (ör. `file_filter = '…' ##NO_TEXT` çağrı parametresi).

**Why:** Bir projede, 2026-09-28: `ls_idx = VALUE #( key = … idx = lines( rt_instr ) )` satırı MATNR'li derin tablo yüzünden FLE P3 verdi; atanan alanlarda MATNR yoktu → kullanıcı onaylı muafiyet.

**How to apply:** ATC'de FLE/"MATNR" bulgusu çıkarsa önce gerçekten 40 karakter taşması var mı bak; yoksa kullanıcı onayıyla `"#EC CI_FLDEXT_OK[<bulgudaki not no>]` + satır üstünde gerekçe yorumu. Başka bir ATC pseudo-comment'in adı gerekiyorsa aynı yolu izle: denetim sınıfının kaynağında `#EC` sabitini ara.

Son-doğrulama: 2026-09-28 — canlı ATC (projenin ATC varyantı) push öncesi/sonrası
Applies-to: s4_private (ATC S/4 readiness denetimleri)
prior-art: yok (memory'de CI_FLDEXT araması 0; ilgili: [[atc-pretty-print-birim-basina-ilk-fark]])

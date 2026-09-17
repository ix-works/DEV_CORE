---
name: feedback_kullanicinin-bildigi-is-gercegini-olcmek-yerine-sor
description: "Kullanıcının kendi yaptığı deneme/bildiği iş gerçeği (sonuç, alan doluluğu) için pahalı canlı ölçüm yerine ÖNCE kullanıcıya sor"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6feb8323-f0ff-4176-b8f5-f633eb79f129
---

Kullanıcının bizzat yaptığı bir denemenin sonucu ("çalıştı mı?") veya iş tarafında bildiği bir gerçek ("AKUEM/BELNR hangi müşteride geliyor?") için ajanla uzun canlı ölçüm başlatma — önce kullanıcıya tek soru olarak sor.

**Why:** 2026-09-14 ZSD000 IDoc data modify turunda <MUSTERI-A>/<MUSTERI-B> deneme sonucunu ve grup alan doluluğunu ölçmek için ajan brifledim; kullanıcı araya girip "evet işe yaradı, bana sorabilirsin" / "akuem ve belnr hepsinde var genelde" dedi.

**How to apply:** Ölçüm planlarken ayır: (1) kullanıcının bildiği/yaptığı → sor; (2) kodun/verinin davranışı, kullanıcının bilemeyeceği teknik kapı değerleri (T663A, VBTYP, segment sayısı) → ölç. Beyanı kaynağıyla yaz ("kullanıcı beyanı"); çelişen kanıt çıkarsa not düş. TAHMİN YASAK'ı gevşetmez — soru da bir kanıt kaynağıdır. İlişkili: [[feedback_sorulari-tek-tek-sor-oneriyle]].
Son-doğrulama: 2026-09-14 · Applies-to: iş-kuralı/deneme sonucu içeren analiz turları

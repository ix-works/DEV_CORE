---
name: feedback_done-tam-kapsam-dogrula
description: "Bir taskı \"done\" işaretlemeden önce TAM kapsamına karşı doğrula; ertelenen/atlanan alt-maddeleri açıkça flag'le"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 535400ae-b5a0-4696-a522-033556d99bcf
---

Bir işi **"tamamlandı" işaretlemeden önce, task'ın TAM kapsamına (adına/açıklamasına) karşı
doğrula.** 2026-06-02'de kullanıcı iki kez yakaladı: (1) C3 "ALV/Tree **kütüphanesi**" dendi ama
tek class deploy ettim (kütüphane değil); (2) cross-check'te C4 "ADT text-pool kapsıyor mu ÖNCE
**TEYİT**" adımını sessizce atlamıştım, #3 "CBO **envanteri**"ni kurmamıştım, C2 "<LEGACY_SOURCE>'dan
**damıt**"ı generic yazmıştım.

**Why:** "Done" iddiası güven sözüdür. Eksik/atlanmış adımı done göstermek = sessiz under-delivery;
kullanıcı keşfedince güven sarsılır + iş geri açılır.

**How to apply:**
- Done'dan önce: task adındaki **her kelimeyi** (kütüphane=çoklu? envanter=dosya? teyit=canlı kontrol?
  damıt=kaynaktan?) teslimle eşle. Karşılanmayan varsa done DEME.
- Bir alt-madde erteleniyorsa: **açıkça flag'le** ("X yapıldı, Y ertelendi çünkü...") + deferred-triggers
  register'a koy. Tahmin/varsayımla "gidebilir" deme — **canlı teyit et** (örn. C4: push_source text-pool'u
  KAPSAMAZ, ayrı /textelements/ endpoint — teyitle anlaşıldı, tahmin yanlıştı).
- Sentetik-test ≠ gerçek-test: gerçek veri yoksa "test edildi (sentetik)" diye belirt.
Bkz. [[feedback_playbook-once-oku]] (tahmin etme), ADR 0006 (reviewer/verify kültürü).

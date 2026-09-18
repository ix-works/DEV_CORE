---
name: feedback_onay-isteme-formati
description: "Kullanıcıdan onay isterken 5 şeyi VER: hangi kural/mekanizma tetikledi · tam olarak ne yapılacak (obje/kapsam) · neden şimdi gerekiyor · onaylamazsa ne olur · senin önerin. 'Araç çalışmadı, onay ver' bir talep değil şikâyettir — kullanıcı neyi onayladığını bilemez."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a4cd7d32-a718-41a3-9b19-f70f390d9ff7
---

Kullanıcı onay istemekten rahatsız DEĞİL — **gerekçesiz** onay istemekten rahatsız.
Birebir sözü: *"sorun onay ver diye gelmen değil, neden dolayı neye onay vermem gerektiğini
belirtmemen… ama sen 'gw çalışmadı, onay istiyorum' dersen olmaz tabi."*

**Her onay talebi şu 5'ini taşır:**
1. **TETİKLEYİCİ** — hangi kural/mekanizma bunu onaya bağladı (ADR/kural adı, ya da
   "auto-mode classifier production soft-deny"). Mekanizmayı adıyla söyle.
2. **KAPSAM** — tam olarak ne yapılacak: obje/dosya listesi, transport, hedef sistem.
   Ve **ne YAPILMAYACAK** (kapsam dışı bırakılanlar + gerekçesi).
3. **NEDEN ŞİMDİ** — bu adım neyi açıyor, neyi bekletiyor.
4. **ONAYLAMAZSA** — alternatif nedir, iş nerede durur (maliyet açıkça).
5. **ÖNERİ** — "önerim X, çünkü Y". Kararı kullanıcıya bırak ama pozisyon al.

**Why:** Onay bir imza değil, bir karardır; karar için bilgi gerekir. Aracın hata mesajını
aktarmak bilgi değildir — kullanıcı aracın iç durumuyla değil, **işin sonucuyla** ilgilenir.
Gerekçesiz talep kullanıcıyı ya körlemesine onaylamaya ya da soruşturmaya zorlar; ikisi de
liderin işini kullanıcıya devretmektir.

**How to apply:** Onay yazarken önce şunu sor: *"bunu okuyan biri, benim bildiklerimi
bilmeden doğru kararı verebilir mi?"* Veremezse eksik olan 5 maddeden biridir.
⛔ **Aracın başarısızlığını gerekçe yerine koyma** — "spawn denied" bir sebep değil, bir olaydır;
sebep ancak ölçtükten sonra yazılır ([[feedback_arac-basarisizligini-zararsiz-sayma]]).
⛔ Onaya gitmeden ÖNCE: bilinen bir sınıf mı diye **hafızaya bak** ve mümkünse **bir kez daha dene**
([[feedback_canli-production-obje-degisimi-auto-mode-kapat]]) — gereksiz onay trafiği de bir maliyettir.
✅ Canlı obje değiştiren turda en temizi: işin başında *"bu tur canlı obje değiştirecek, auto-mode'u
kapatalım, prompt'ları sen onayla"* — tek seferde çözülür.
İlişkili: [[feedback_sorulari-tek-tek-sor-oneriyle]] (çok soru → tek tek, bağlam+öneri) ·
[[feedback_karar-verimliligi-asiri-kapi-yok]] (makul-default varken hiç sorma).

Son-doğrulama: 2026-08-09 (P4 SAP yazımı onayı — kullanıcı bu turda kuralı koydu)
Applies-to: TÜM projeler · her onay/izin talebi (SAP yazma, deploy, geri alınamaz eylem)

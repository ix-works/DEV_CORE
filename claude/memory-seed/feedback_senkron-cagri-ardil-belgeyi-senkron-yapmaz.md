---
name: feedback_senkron-cagri-ardil-belgeyi-senkron-yapmaz
description: "Bir FM/API senkron dönüyor diye ARDIL belge de o anda var değildir; senkron olan kendi çıktısıdır (statü alanı), zincirin devamı değil"
metadata:
  type: feedback
---

*"Bu FM senkrondur, dönüşten sonra gecikme/retry EKLEME"* cümlesi **kapsamı gizler**:
senkron olan çağrının **KENDİ çıktısıdır** (çağırdığın belgenin kendi statü alanı),
**ardıl sistemde doğan belge değil**.

**Ölçülmüş vaka (2026-09-10, ZSD001 teslimat dağıtımı → EWM):** Çapaya bir gün önce
*"dağıtım FM'i senkrondur ⇒ kapıyı gecikmesiz oku"* diye kural yazmıştım (K-5).
Kullanıcının **ilk canlı koşumu** çürüttü: dağıtımdan hemen sonra çıktı basılamadı,
kullanıcı ikinci kez basınca çalıştı. Ölçüm — teslimat `8000000091`:
`LIKP` yaratma **06:07:12 UTC** ↔ EWM ODO yaratma **06:07:20 UTC** = **8 sn**.
⇒ Senkron olan `LIKP-VLSTK` (dağıtım statüsü) idi; **ODO değildi**.
⚠ Niteleyici: **tek vaka**, DEV, boş sistem ⇒ eşiğe çevrilemez
([[feedback_dev-verisi-yapi-olcer-dagilim-olcmez]]).
Tasarım buna göre: sabit bekleme değil, **1 sn aralıklı 10 turluk poll** (bütçe 10 sn,
kullanıcı kararı) + bulunca **derhal** çık.

**Why:** "Senkron" bir **çağrı özelliğidir**, zincir özelliği değil. Aynı istemcide çalışan
embedded bir bileşen (EWM) bile kendi belgesini **kendi kuyruğunda** doğurur. Kuralı
*"gecikme ekleme"* diye yazmak, halefe **ölçüm değil yasak** bırakır: hata çıkınca
kod düzeltilmez, kural savunulur.

**How to apply:**
- Senkronluk iddiasını **hangi ALANIN** senkron olduğuyla yaz: *"`VLSTK` çağrı dönüşünde
  günceldir; ODO değildir"*. Alan adı yoksa iddia kurulmamıştır.
- Zincirin **ardıl** halkasını okuyacaksan iki yaratma zaman damgasını karşılaştır
  (bkz. [[feedback_otomatik-olusur-bir-zamanlama-iddiasidir]]) — saat dilimlerini önce eşitle.
- Bekleme tasarlarken **sabit sleep değil poll** yaz: bütçe + erken çıkış + bütçe dolunca
  anlamlı mesaj. Bekleme dalının mesajı, **hata dalının** mesajından farklı olmalı — yoksa
  başarı yolunda kullanıcıya "belge bulunamadı" dersin.
- Poll'ü **ters yönde** test et: kodu çıkarınca hata birebir geri geliyor mu
  ([[feedback_ters-yon-kontrolu]]).
- ⛔ Çapaya *"gecikme EKLEME"* gibi **yasak** yazma; *"şu alan şu anda günceldir"* diye
  **ölçüm** yaz ([[feedback_capa-liste-degil-KURAL-olmali]]).

İlgili: [[feedback_kod-yolu-vardi-veri-gecmemisti]] · [[project_ewm-embedded-erp-lgnum-cevirisi]] ·
[[feedback_capadaki-acik-madde-devralmadan-once-olculur]]

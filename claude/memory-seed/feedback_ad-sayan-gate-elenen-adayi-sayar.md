---
name: feedback_ad-sayan-gate-elenen-adayi-sayar
description: "Onay listesinde ham token deseniyle ad sayan bir gate, ELENEN adayları da sayar — sayı şişer"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a7d41ea7-18cd-4daf-a34c-df913d3c26a7
---

Bir ad onay listesinde `ZSD001_T_*` gibi **ham token deseniyle** sayım yapan gate, **elenen aday
adları da sayar** ⇒ sayı şişer ve yanlış alarm verir.

Ölçülmüş örnek (ZSD001 ADLAR, 2026-08-18): `§12.1` ham token = **9** çünkü metinde `ZSD001_T_BEYAN`
(T-6'nın **elenen** adayı) geçiyor — onaylı tablo sayısı **8**. Aynı şekilde `§12.8` = **5** çünkü
`ZSD001_LOG` ve `Z_SD022_GR` elenen alternatifler olarak yazılı — onaylı **3**.

**Why:** Onay listeleri **bilinçli olarak** elenen adayları saklar (*"yeniden açılmasın"* gerekçe
kaydı). Bu iyi bir belge disiplinidir ama makineyle sayıma düşmandır. Belgedeki sayılar doğruydu;
yanlış olan **sayım yöntemi** olurdu.

**How to apply:**
- Ad sayan bir gate yazılırsa: **elenen aday satırlarını dışla** — `~~üstü çizili~~`, *"elenen aday:"*,
  *"DÜŞÜRÜLDÜ"* işaretli satırlar sayıma girmemeli.
- Sayıyı **en az iki farklı desenle** doğrula ve farkı açıkla; tek desen sessizce yanılır
  (aynı ders ters yönde: birleşik yazım `M-43/M-01 ✅` dar desende **kaçar**).
- Kimlik **aralığı** ile **adedi** ayrı doğrulanır: `S-1…S-9` yazıp adet 9 demek, arada `S-5`
  düşürülmüşse **iki hata birbirini örter** (gerçek küme S-1…S-4 + S-6…S-10).

İlgili: [[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]] · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]

---
**Son-dogrulama:** 2026-08-18 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)

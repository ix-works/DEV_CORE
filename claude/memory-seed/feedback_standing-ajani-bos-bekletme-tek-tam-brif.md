---
name: feedback_standing-ajani-bos-bekletme-tek-tam-brif
description: "Bir ajan koşusunun takvim süresinin %40-60'ı liderden mesaj BEKLEMEKTİR (ölçüldü 2026-08-29, 30 gün): gateway 36 dk, frontend 31, backend 21 dk/koşu. Ajan yavaş değil, lider parça parça besliyor. Kural: scoped spawn + kapat; standing zorunluysa (gateway) işi TEK TAM paketle ver"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 199aed41-f1ec-4c03-ae34-a0b1b09c15be
---

**"Ajan işi uzun sürede yapıyor" şikâyetinin en büyük bileşeni ajanda değil, liderde.**
30 günlük alt-ajan transkript korpusunda (713 koşu, 2026-07-30→08-29) ölçüldü:

- Koşu içindeki **>2 dk boşlukların 345/346'sı** `<teammate-message teammate_id="team-lead">`
  ile bitiyor ⇒ boşluk = liderin sıradaki parçayı göndermesini bekleme.
- Koşu başına boş süre: **adt-gateway 36 dk** (102 boşluk, 46 h/ay, p90 **81 dk**),
  **frontend 31 dk**, **backend 21 dk** (186 boşluk, 40 h/ay); bug-expert 3 dk, infra 6 dk
  (bu ikisi taze-spawn olduğu için beklemiyor).
- Aynı koşuların AKTİF (model+araç) süresi: backend 34 dk, gateway 24, frontend 30 ⇒
  takvim süresinin **%40–60'ı bekleme**.
- Karşılaştırma: aktif süreyi kısaltmaya yönelik kaldıraçlar (paralel araç, kısa rapor,
  context) ya zaten denenmiş-etkisiz (P6 talimatı 07-31'den beri var, araç/tur düz 1.1–1.3)
  ya da ölçümde küçük çıktı (koşu başına ≤1–2 dk). Bekleme tek başına hepsinden büyük.

**Why:** ADR 0018 zaten LAZY (ihtiyaç anında scoped spawn + kapat) diyor; ölçüm liderin
buna uymadığını gösteriyor — backend/frontend standing tutulup SendMessage ile parça parça
iş veriliyor, gateway "sonra devamı gelir" diye saatlerce açık kalıyor. Bekleyen ajan yalnız
takvim değil, canlı context de tutar (cache süresi dolunca yeniden ısınma maliyeti).

**How to apply:**
- backend/frontend/bug/infra: **scoped spawn → bitince kapat**; devam işi gelince taze spawn
  (brif'e önceki çıktının yolunu koy). Standing tutma.
- adt-gateway (tek yazıcı, standing meşru): işi **tek tam paketle** ver — "şunu push et,
  sonra söylerim" değil, "şu N objeyi şu sırayla push+activate+ATC, raporla" biçiminde.
  Paket bitince kapat; yeni paket = yeni spawn.
- Bir ajana SendMessage ile ikinci parça gönderiyorsan dur: bu, ölçülen bekleme desenidir.
- Aynı tur: [[feedback_ajan-model-secimi-olculdu-ayri-politika-yazilmadi]] (model değil),
  [[feedback_subagent-karar-kurali]] (kaç ajan), [[feedback_lider-bloke-olmama-background-dispatch]].

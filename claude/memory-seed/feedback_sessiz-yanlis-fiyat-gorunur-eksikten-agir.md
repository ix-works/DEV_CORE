---
name: feedback_sessiz-yanlis-fiyat-gorunur-eksikten-agir
description: "Fiyat/koşul tasarımında sessiz yanlış fiyat, görünür fiyat eksikliğinden DAHA AĞIR risktir — hata/sıra tasarımında görünür başarısızlık tercih edilir"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Fiyat (koşul kaydı) yazma/silme sırasını ya da kısmi hata davranışını tasarlarken **"fiyatsız kalmak yanlış fiyattan kötüdür" DEME — doğrusu tam tersidir.** Fiyatsız kalan bir sipariş fark edilir: fiyat gelmez ve eksiklik görünür. Gelen bir fiyatın yanlış olduğunu anlamak ise zordur ve yanlış fiyat sessizce faturaya gider.

**Why:** Kullanıcı (SD uzmanı) 2026-11-07'de bir koşul yazma tasarımı tartışmasında liderin "önce fiyat sonra silme, çünkü fiyatsız kalmak daha kötü" gerekçesini "kesinlikle yanlış" diye düzeltti.

**How to apply:** Kısmi yazım, geri alma ya da sıralama seçeneklerini değerlendirirken her hata dalının sonucunu "görünür mü, sessiz mi" diye sınıfla. Sessiz yanlış fiyat üreten dalı en riskli dal say. Görünür başarısızlık (fiyat yok, paket hata durumunda) daha güvenli taraftır.

Son-doğrulama: 2026-11-07
Applies-to: SD fiyatlandırma / koşul kaydı yazma tasarımı (tüm profiller)

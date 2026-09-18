---
name: feedback_paralel-duzenlenen-dosyaya-satir-no-cakma
description: Başka bir ajanın düzenlediği dosyaya satır numarası çakmak — şerh dakikalar içinde bayatlar, metin çapası kullan
metadata:
  node_type: memory
  type: feedback
---

Bir şerh/kayıt başka bir dosyadaki satırı `dosya:NNN` diye gösterirse, numara **yazıldığı anda
doğrudur** ama aynı oturumdaki paralel bir tur o dosyayı düzenleyince **kayar**. Okuyucu artık
**makul görünen ama yanlış** bir yere bakar — hata vermez, sessizce yanıltır.

**Why:** ölçülen vaka (2026-09-16) — bir ABAP şerhi iki FE dosyasına satır çaktı; mtime farkı
**+67 sn** ve **+130 sn**, drift **+9** ve **+31** satır. **İki dakikada bayat.** Üstelik bu, aynı
turda *düzeltilen* bayat bir atfın yerine yazılan yeni numaraydı ⇒ sınıf kendini **ikinci kez**
üretti (düzeltme turunun kendi regresyonu).

**How to apply:** dosya-dışı atıf **satır numarası taşımaz**; aranabilir bir **metin çapası**
kullan: `⚓ Çapa: ZCL_X → METHOD y → IF it_z IS NOT INITIAL dalındaki SELECT`.
⭐ **Düzeltme anı da dersin parçası:** dosya hareket hâlindeyken yeni numara yazmak sınıfı yeniden
üretir. Doğru sıra ① numarayı **at** (çapaya çevir) ya da ② dosya donana kadar bekle.
*"Güncel numarayı yaz"* üçüncü kez bayatlamanın reçetesidir.

Kanonik kayıt: core `playbook/lessons-learned.md` → **PATTERN #36**.
Kardeşi: [[feedback_kapi-kosarken-dosya-donar-md5-teyidi]] · [[feedback_calisan-ajanin-dosyasi-ucus-halindedir-iddia-degil-soru]]

Son-doğrulama: 2026-09-16 · Applies-to: tüm projeler, çok-ajanlı turlar

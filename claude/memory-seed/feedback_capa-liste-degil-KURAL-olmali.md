---
name: feedback_capa-liste-degil-KURAL-olmali
description: Yoruma/belgeye yazılan SAYILMIŞ KÜME bayatlar; yerine o kümeyi üreten KURALI yaz — bayatlama yapısal olarak imkânsızlaşır
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5e1fe6d8-9f1f-4d33-863a-e185e4c67eb0
---

Bir yoruma ya da belgeye **sayılmış küme** (malzeme listesi, müşteri listesi, "10 belge",
"ZE02 ×3 / ZE04 ×7") yazmak, o metni **canlı verinin fonksiyonu** yapar. Veri akıyorsa metin
bayatlar — ve **sessizce**: liste hâlâ "tam küme" gibi okunur.

**Ölçülen vaka (2026-09-04, <MUSTERI-F> turu):** Bir yoruma 7 malzemelik liste yazıldı. Gün içinde
11. düzeltme teslimatı doğdu ve **yeni bir malzeme** (`<MALZEME-2>`) getirdi. Liste yalnız kısalmadı —
**kapsamı değişti**. Aynı turda 3 dosyada daha aynı kusur vardı (`ZE04 ×7` → `×8` olmuştu).

**Çözüm — iki kademe, ikincisi asıl olan:**
1. *Yetersiz:* rakamı tazele + `⚠ AKAN SÜREÇ / ölçüm anı` niteleyicisi ekle. Bu kusuru
   yalnızca **erteler**; dördüncü bayatlama gelir.
2. ⭐ *Doğru:* **çapayı kümeden KURALA çevir.** Listeyi tamamen çıkar, yerine kümeyi üreten
   ölçütü yaz: *"bölüm '10' dışındaki HER malzeme, adı ne olursa olsun, range'e girmez —
   kural malzeme adına değil BÖLÜME bağlıdır."* Artık yeni malzeme doğsa da yorum **çürüyemez**.
   Sayı kalacaksa yalnız **büyüklük mertebesi** olarak kalsın, gerekçe ona **dayanmasın**.

**Why:** Bayat sayı zararsız görünür ama okuyucunun gözünde OTORİTEDİR; eksik listeye bakan
sonraki kişi "küme bu" diye karar verir. Kural-çapası veriyle birlikte akar, liste-çapası akmaz.

**How to apply:**
- Yoruma sayı/liste yazmadan önce sor: **"bunu üreten kural nedir?"** Kural yazılabiliyorsa liste yazma.
- Bir rakamı tazelerken **SINIFLANDIRMANIN hâlâ geçerli olduğunu AYRICA ölç** — yeni satır
  gerekçeyi çürütebilir. Sadece rakamı güncellemek, yanlış bir sınıflandırmayı **taze göstermek**tir.
- Aynı iddia kaç dosyada yaşıyorsa hepsinde kapat — bkz. [[feedback_iddia-kac-yerde-yasiyorsa-o-kadar-yerde-kapatilir]].
- Kapsam sayısı da bir çapadır ve o da üç belgede üç farklı yaşayabilir (25/20/22 ölçüldü);
  otorite belge değil **ölçümdür** — bkz. [[feedback_capayi-ada-cevirmek-de-bir-olcumdur]],
  [[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]].

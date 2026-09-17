---
name: feedback_bulgu-listesi-ornektir-sinif-duzeltmesi-tarama-ister
description: "Kapının verdiği bulgu listesi bir ÖRNEKLEMDİR, sayım değil — bir SINIF düzeltilirken liste değil TARAMA kapatır; kapı bile ilk turda 4'ün 3'ünü görmüştü"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 147413fa-85a8-4e1e-8abc-7c28606ff1f5
---

**Vaka (2026-09-01, ölçüldü — <MUSTERI-C> üreteç turu):** Bug-gate `E-3` olarak *"bu değişimin
çürüttüğü **3** gerekçe metni"* verdi. Üretici üçünü de düzeltti (eski cümleyi alıntılayıp
çürüterek) ve **kendiliğinden 4.'sünü** buldu (`K-3`: *"senin saydığın 2'ye ek olarak
ÜÇÜNCÜSÜ vardı"*). Delta turunda kapı **bir tane daha** buldu: `gen_mmap.py:2712-2718`,
aynı çürütülmüş `20JJMM00 → V4 050` iddiası **canlı bir assert mesajında**.

⇒ Aynı sınıfın **en az 5 vakası** vardı; **ilk turda kapı 3'ünü**, üretici +1, delta +1 gördü.
Kimse yalan söylemedi — **liste bir örneklemdi.**

Kapıyı bulan şey liste değil **yöntemdi**: `düşer|gürültülü|zararsız|etkisiz` taraması +
her eşleşmenin ±6 satırında `[DOĞRULANAMADI]`/ölçüm işareti aranması. İşaretsiz kalan tek
satır 4./5. vakaydı.

**Why:** Bir bulgu listesi *"şunları gördüm"* der, *"hepsi bunlar"* demez — ama tüketici onu
sessizce **sayım** gibi okur ve "3/3 kapatıldı ✅" yazar. Bedeli ölçüldü: düzeltilmiş üç
kardeşin yanında, **kapıya çarpan kişinin okuyacağı tek yönlendirme metni** ölçülmemiş bir
kesinlik vermeye devam ediyordu. Kalıntı, düzeltmenin kendisinden daha zararlıdır — çünkü
etrafındaki üç doğru düzeltme ona **sahte güvenilirlik** verir
([[feedback_gurultulu-duser-iddiasi-olculmeden-yazilmaz]]).

**How to apply:**
1. **Bulguyu sınıflandır: VAKA mı SINIF mı?** "Şu satırdaki sayı yanlış" = vaka. "Ölçülmemiş
   iddia otorite gibi yazılmış" = **sınıf**. Sınıfsa liste yetmez.
2. **Sınıf düzeltmesinin kapanış kanıtı TARAMADIR, sayı değil.** Kabul ölçütüne *"şu deseni
   tara → kalıntı 0"* yaz; *"3 kalem düzeltildi"* yazma. Taramayı **düzelten** koşar,
   **kapı da bağımsız** koşar.
3. **Deseni bulguların ortak DİLİNDEN çıkar**, kendi hatırladığından değil — burada
   `düşer|gürültülü|zararsız|etkisiz` + "yakınında etiket var mı" ikili testi işe yaradı.
   Tek desene güvenme ([[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]]).
4. **Üretici listeden FAZLASINI bulursa bu bir sinyaldir:** "senin 2 dediğine 3. eklendi"
   cümlesi, listenin örneklem olduğunun **kanıtıdır** ⇒ o an tarama şart, "bonus" diye
   sevinip geçme.
5. **En kötü kalıntı yeri: kapı/uyarı/assert MESAJLARI.** Yorum satırı yanlışsa okuyan
   şüphelenir; *kapı mesajı* yanlışsa okuyan ona **uyar**. Taramayı yorumlarla sınırlama,
   string literal'leri de kapsa.

📌 Kardeş kayıtlar: [[feedback_tarama-ciktisi-hipotezdir-is-listesi-degil]] (ters yön: tarama
çıktısı da iş listesi değildir) · [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]] ·
[[feedback_kapsam-disi-bulgu-protokolu]] · [[feedback_kapsam-niteleyicisini-dusurme]].

Son-doğrulama: 2026-09-01 · prior-art: arandı — sınıf-vs-vaka ayrımı `infra-expert`
sözleşmesinde ("kök-soru: sınıf mı vaka mı") VAR ama **bulgu listesinin örneklem olduğu**
kaydı YOKTU. Applies-to: tüm projeler, tüm kapı turları.

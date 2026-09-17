---
name: feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur
description: ÇÜRÜTME de bir iddiadır — yanlış bir sayıyı düzeltirken yazdığın YENİ sayı aynı sıkılıkta kanıt ister; kök doğru olsa bile ondan türetilen SAYIM yanlış olabilir. Bir sayıyı düzeltirken sayım YÖNTEMİNİ de yaz
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c20182a3-2866-4571-9b91-5c1f1e595fd2
---

**Bir sayıyı çürütmek, yerine yazılanın ÖLÇÜLDÜĞÜ anlamına gelmez.** Çürütme anı en tehlikeli
andır: haklı çıkmanın verdiği güvenle yeni sayı **kanıtsız** yazılır — üstelik çoğu zaman doğrudan
**üretim kaynağına**, çünkü "bu sefer ölçtük" hissi vardır.

**Vaka (2026-09-05, ZSD001 EKR-02).** Aynı sayı **iki kez** yanlış ölçüldü:
1. Lider brifi: *"`v` modelinde **3** bağlama etkileniyor, kalan 7'si `growing="true"`."*
2. Üretici bunu **ölçerek çürüttü** — ve **8 etkileniyor / 3 etkilenmiyor** yazdı, `Component.js`e işledi.
3. Kapı ikisini de ölçtü: ⛔ **gerçek 4 / 7.** MsgDiag'ın dört tablosunun **dördü de** `growing="true"`ydü.

⭐ En öğretici yanı: **kök her iki turda da DOĞRUYDU** — `sap.m.ListBase.growing` varsayılanı
gerçekten `false`tır (`ListBase.js:222`), yani *"growing yazılmamış = kapsam içi"* çıkarımı geçerliydi.
Yanlış olan, o doğru kökten **türetilen SAYIM**dı: kural doğru uygulanırsa hangi dosyaların gerçekten
o kovaya düştüğü **ayrı bir ölçümdür** ve yapılmamıştı.

**Why:** Bir hatayı bulan zihin, kendi düzeltmesini **zaten doğrulanmış** sayar. Oysa çürütme iki
adımdır — (a) eski sayı yanlış (b) yeni sayı doğru — ve (b) neredeyse hiç ayrıca ölçülmez.
Fail yönü genelde "güvenli"dir (davranış doğru, yalnız gerekçe yanlış), bu yüzden **hiçbir kapı
kırmızıya dönmez** ve yanlış sayı kaynakta yaşamaya devam eder, bir sonraki turu yanıltır.

**How to apply:**
1. Bir sayıyı düzeltirken **sayım YÖNTEMİNİ** de yaz: hangi grep/komut, hangi dosya kümesi, hangi
   eleme kuralı. *"8 bağlama"* değil → *"8 bağlama; komut şu, kapsam şu, elenenler şunlar."*
2. **Kovaların ikisini de listele** — yalnız "etkilenen"i değil, "etkilenmeyen"i de adıyla yaz.
   Ters kova yazılmaya zorlandığında yanlış yerleştirme kendini gösterir.
3. Kökü doğrulamakla sayımı doğrulamayı **ayır**: *"kural doğru"* ≠ *"kuralı doğru uyguladım"*.
4. Çürütmeyi üretim kaynağına yazacaksan, o satır artık **senin iddiandır** — brifin değil.
5. Aynı disiplin başkasının çürütmesi için de geçerli: bir ajan senin sayını çürütürse, **onun
   sayısını da** kendin ölç (bu vakada üçüncü ölçüm doğruyu buldu).

İlgili: [[feedback_kaydin-onerdigi-fix-yonu-de-bir-iddiadir]] · [[feedback_onay-da-bir-iddiadir-mekanizmayi-olcmeden-net-deme]] ·
[[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] · [[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]] ·
[[feedback_iddia-kac-yerde-yasiyorsa-o-kadar-yerde-kapatilir]] · [[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]]

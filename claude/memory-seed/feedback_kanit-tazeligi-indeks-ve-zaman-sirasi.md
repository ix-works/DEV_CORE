---
name: feedback_kanit-tazeligi-indeks-ve-zaman-sirasi
description: İş listesi indeks satırından kurulmaz (gövde+canlı kanıt); veri-kanıtını kullanmadan önce zaman-sırasını doğrula
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b01ce317-db03-4cee-9960-e8c911878caa
---

İki ayrı bayatlık tuzağı, ikisi de 2026-07-27'de yaşandı:

**1. İndeks satırı gövdeden AYRI bayatlar.** `MEMORY.md` indeksi "ZSD001 DOCU build sırada" /
"docs devam" derken, memory gövdeleri aynı işlerin haftalar önce kapandığını yazıyordu. Oturum
başı iş listesini indeksten kurdum → kullanıcıya **yapılmış işi "sırada" diye sundum**.

**2. Veri-kanıtı zaman-sırası doğrulanmadan kullanılamaz.** ZSD001 farklı-ship-to araştırmasında
müşteri 200008'in 6 siparişi "WE=kendisi" taşıyordu; bu ilk bakışta "SAP determinasyonu counter
000'ı seçiyor" kanıtı gibi duruyordu. `KNA1-ERDAT` kontrolü çürüttü: alternatif ship-to'lar
siparişlerden **sonra** yaratılmış — sipariş anında tek aday vardı. Kanıt değersizdi.

**Why:** Bayat özet, yanlış-olduğu-belli-olmayan bir yanlıştır — "yapılacak" diye sunulan bitmiş iş
kullanıcının zamanını harcar; tarih-sırası doğrulanmamış veri ise ölçüm kılığında bir tahmindir
(TAHMİN YASAK'ın en sinsi biçimi: elinde tablo var, yine de uyduruyorsun).

**How to apply:**
- Oturum başı / "nerede kalmıştık" → indeks satırını **çapa** say, **kanıt** sayma. İş listesini
  memory GÖVDESİ + paket `SESSION_NOTES.md` + **canlı sistem** ile kur. Bir işi "sırada" ilan
  etmeden önce yapılmadığını doğrula (ör. DOCU için `DOKHL` `DOKSTATE`).
- Bir iş kapanınca indeks satırını **aynı anda** güncelle; gövdeyi kapatıp indeksi bırakma.
- Bir veri kümesini kanıt olarak kullanmadan önce sor: **bu kayıtlar, kanıtladığını iddia ettiğim
  koşul yürürlükteyken mi oluştu?** Anaveri/customizing yaratılma tarihi (`ERDAT`) ile belge
  tarihini karşılaştır. Sıra tersse kanıt yok demektir — "kanıt bulunamadı" de, uydurma.

**4. VARYANT — AJAN, LİDER'İN ÖLÇÜMÜNÜ "bayat" İLAN EDİYOR (2026-08-23, AYNI GÜN İKİ AJANDA).**

Lider ölçtü → *"şu iş yapılmamış"* dedi → ajan yaptı → ajan *"zaten yapılmıştı, senin anlık
görüntün bayat"* diye raporladı. **İki vakada da lider'in ölçümü DOĞRUYDU** — kanıt lider'in
kendi tool çıktısıydı (`sed -n '39,43p'` çıktısında `:41` satırı eski değeri gösteriyordu; ajan
*"senin ölçümün `:46`'ya çarpmış"* dedi ama `:46` o aralıkta yok).

**Kusurun şekli (ajanın kendi ifadesi, kabul ederken):** *"kendi SON durumumdan geriye bakıp senin
ölçümünü bayat ilan ettim; elimde 'o an dosya ne durumdaydı' verisi YOKTU — **olmayan bir
kanıttan sonuç çıkardım**."* ⭐ Karıştırılan iki soru: **"şu an doğru mu"** (ölçülebilir) ile
**"senin ölçümün neden farklıydı"** (geçmiş durum — ajanın erişimi YOK).

**Why:** Sessizce kabul edilirse iki zarar birden: kayıt yanlış olur **ve** ajan *"lider bayat ölçüyor"*
refleksini pekistirir ⇒ sonraki düzeltmelere direnç gösterir. Ters yön de mümkündür: gerçekten
bayat ölçtüğün vakalar da olur — bu yüzden **kavga değil ÖLÇÜM** gerekir.

**How to apply:**
- Ajan *"senin ölçümün bayat"* derse → **kendi tool çıktına geri dön** (transkriptte durur).
  Komutun kapsadığı aralığı ve dönen satırları göster. Haklıysa **kabul et ve düzelt**; değilse
  **kısaca düzelt** — puan için değil, kaydın ve ajanın refleksinin doğru kalması için.
- Ajan brifingine yaz: *"geçmiş bir an hakkında iddia kurma — 'o anı bilemem, şu an şöyle' de."*
- Aynı kural sana da: bir ajanın *"yaptım"* raporunu **artefaktla** ölç (*"artefakt yok ≠ görev
  işlendi"*), ama ölçümün **zaman damgasını** da aklında tut — senin ölçümünle mesajının
  ulaşması arasında ajan iş yapmış olabilir; o **bayatlık değil, sıra**dır.

**3. VARYANT — açık-kalem kaydı, iş BAŞKA BİR REPODA kapandığı için bayatlar (2026-08-14, ders İŞE YARADI).**
Proje `governance/*-RESUME.md` §8'i *"bu ders çekirdeğe hiç yazılmamış (grep 0)"* diyordu; ölçüm
**yazıldığı an doğruydu**, ama ders **aynı gün 3 saat sonra** core reposunda merge edilmişti
(PR #137). Kullanıcı *"terfi ettir"* dediğinde ÖNCE-ARA (KB-01) ilk adımda yakaladı ⇒ zaten
yapılmış iş yeniden yapılmadı; gerçek boşluk (ters yön) bulunup kapatıldı.
📌 **Çapraz-repo kör noktası:** bir kaydın "açık" kalması, işin yapılmadığını **kanıtlamaz** —
kayıt ve icra farklı repolarda yaşıyorsa kapanış sinyali kayda hiç ulaşmaz. Bir açık kalemi
**icra etmeden ÖNCE** hâlâ açık mı diye **hedef sistemde** ölç (core repo · canlı SAP · başka
proje), kaydın kendisine değil.

**5. VARYANT — KENDİ ölçümün, AYNI OTURUM İÇİNDE, artefakt değiştiği için bayatlar (2026-09-02,
LİDER ve ÜRETİCİ aynı tuzağa DÜŞTÜ).**

Buraya kadarki dört varyant hep **başkasının/eski turun** kaydını konu alıyordu. Bugünkü yüz
daha yakın: **kendi doğru ölçümünü**, dosya altından değiştiği için, **yeniden ölçmeden**
tekrarlamak. Aynı iddia (*"`lt_msg`'e `APPEND` yok"*) üç turda üç kez çapalandı, **üçü de**
bayatladı; iddia **her seferinde doğruydu**. Kaynak aynı gün 388 → 505 → 455 → 470 satır oldu.
⚠ Kimse yalan ölçmedi — ölçüm **yapıldığı anda** doğruydu; taşınırken **yeniden ölçülmedi**.

⭐ Ayırt edici işaret: *"bunu zaten ölçmüştüm"* düşüncesi. Bu cümle, **artefaktın o ölçümden
sonra değişip değişmediği** sorusunu sessizce atlar. Aktif düzenlenen bir dosyada bu soru
**her turda** yeniden sorulur.

**How to apply:** Bir turdan diğerine taşıdığın her sayı için (satır no · md5 · satır sayısı ·
sayım) tek soru: **"artefakt bu ölçümden sonra değişti mi?"** Değiştiyse ölçüm **ölmüştür** —
yeniden ölç ya da çapayı çürümeyen bir biçime çevir
([[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]]).

Son-doğrulama: 2026-09-02 (varyant 5 eklendi) · önceki: 2026-08-14 (varyant 3)
Applies-to: her proje / her tur; özellikle çok-repolu (proje + core + memory) çalışma **ve**
aynı oturumda birden çok tur düzenlenen kaynaklar

İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_done-tam-kapsam-dogrula]] ·
[[project_memory-recall-redizayn-2026-07-10]] · [[feedback_ajan-okuma-disiplini-tazelik]]

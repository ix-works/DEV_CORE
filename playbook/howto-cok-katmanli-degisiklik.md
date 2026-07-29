---
applies_to: [all]
---
# HOWTO — Çapraz-kesen (çok katmanlı) davranış değişikliği nasıl yönetilir

> **Ne zaman oku:** bir davranış **birden çok katmanda** (BE kuralı + FE akışı + mesaj + veri) ve/veya
> **birden çok app'te** doğru olmak zorundaysa. Örnekler: silme/iptal kontrolü · yetkilendirme ·
> audit alanları · mesaj biçimi · zorunlu-alan doğrulaması · kilit/lock davranışı · toplu işlem.
> **Kaynak:** gerçek bir tur — beklenen "3 app'lik küçük düzeltme", çıkan **2 gün / 7 app / 13 BE kuralı /
> 6 review turu**. Aşağıdaki her madde o turda **yaşanmış** bir hatadır veya onun karşılığıdır.
> `applies_to: ecc, s4_private, s4_public, btp_abap`

---

# NEDEN BU DOSYA VAR — turun tek cümlelik özeti

> İş teknik olarak zor değildi. **Uzamasının sebebi, yüzeyin tamamı hiçbir noktada
> taranmadan katman katman KEŞFEDİLMESİYDİ.** Her düzeltme bir sonraki eksiği doğurdu.

Ölçülen fark:

| | İlk varsayım | Tam tarama sonrası gerçek |
|---|---|---|
| Kapsam | 3 app'lik FE düzeltmesi | **7 app + 2 backend boşluğu + canlıda yetim veri** |
| Silme yolu | 14 (kısmi tarama) | **24** |
| Hata sınıfı varyantı | 1 | **7** |
| Review turu | 1 beklenirdi | **6** |

---

# AŞAMA 1 — BU SORUN EN BAŞTAN NASIL ENGELLENİRDİ

## 1.1 Kabul ölçütü KULLANICI GÖZÜNDEN yazılır, katman gözünden değil

**Ne oldu:** backend'e 13 doğrulama kuralı yazıldı, hepsi doğru çalıştı, hepsi kablolandı.
Ama kullanıcı **hiçbirinde** sebebi göremiyordu — FE o yola hiç gitmiyordu. Kural teknik olarak
"tamam"dı, işlevsel olarak **ölü koddu**.

| ❌ Yanlış kabul ölçütü | ✅ Doğru kabul ölçütü |
|---|---|
| "Guard yazıldı ve aktive edildi" | "Kullanıcı silemediğinde **sebebi belge numarasıyla görüyor**" |
| "Validation BDEF'te kablolu" | "Ekranda **şu metin** çıkıyor, ≤50 karakter, numara görünür" |
| "Unit test yeşil" | "Runtime'da **gözlendi**, ekran görüntüsü/ham yanıt kanıtı var" |

**Kural:** kabul ölçütü **gözlenebilir kullanıcı davranışı** olarak yazılmadıysa, iş bitmiş sayılmaz.
İlk gün 10 dakikalık bir runtime denemesi bu turun tamamını farklı yönetirdi.

## 1.2 Kardeş app'lerde desen KOPYA değil, SAHİPLİ ARTEFAKTTIR

**Ne oldu:** 5 kardeş app aynı işi yapıyordu ama **birbirinden sapmıştı** — biri paralel kaydediyordu
diğerleri sıralı; biri listeye ekliyordu diğeri listeyi yeniden sıralıyordu; birinin pending-detektörü
3 alan diğerininki 4 alan kontrol ediyordu. Her sapma **ayrı bir hata yüzeyi** üretti.

**Doğrusu:**
- Kardeş app'lerin ortak davranışı için **kanonik referans** belirle (hangi app örnek?)
- Yeni app = kanonikten **kopyala + FARK TESTİ** ("nesi farklı, neden?")
- Sapma **bilinçliyse yoruma gerekçesiyle yazılır**; yazılmamış sapma = gelecekteki bug
- Ortak davranış değişince **kardeşlerin tamamı** aynı turda güncellenir (biri unutulursa drift kalıcılaşır)

## 1.3 Platform sınırı ÖNCE ölçülür, tasarımdan sonra değil

**Ne oldu:** mesaj biçimi tasarlandı, sonra **canlıda 50 karakterde sessizce kesildiği** keşfedildi —
üstelik kesme payload'ın her alanında olduğu için FE kurtaramıyordu. Biçim yeniden tasarlandı.

**Doğrusu:** çıktı bir platform yüzeyinden geçiyorsa (OData mesajı, IDoc segmenti, ekran alanı,
e-posta konusu) **sınırı önce ölç** — uzunluk, kodlama, kırpma davranışı. Sonra biçimi tasarla.
Sınır bilinmeden yazılan biçim, sınırı öğrenince **baştan yazılır**.

## 1.4 Çapraz-kesen davranışta ENVANTER ilk adımdır

**Ne oldu:** "silme yolu" envanteri **ikinci günün ortasında** çıkarıldı. Çıkarılınca 14 sanılan
sayı **24** oldu, "3 app" **7 app** oldu.

**Doğrusu:** davranış çapraz-kesense (silme, yetki, audit, mesaj) **ilk iş envanter**:
`hangi entity/app/yol bu davranışı taşıyor?` → matris. Envanter **bir turdur**;
envantersiz ilerlemek **her katmanda bir tur**dur.

## 1.5 "Bir hata sınıfı" bulunduğunda, sınıf TÜM YÜZEYDE aranır

**Ne oldu:** "liste daralınca seçim bayatlar → yanlış kayıt silinir" sınıfı bulundu.
Her review turu **kendi dar kapsamına** baktı (doğru davranış) — ama **hiçbiri tüm yüzeye bakmadı**
→ bir app **hiçbirinin kapsamına girmedi** ve gözden kaçtı. Kullanıcı "task listesini kontrol et,
atladığımız bir şey kalmasın" demeseydi kaçacaktı.

**Doğrusu:** sınıf bulunduğu anda **sınıf-taraması** aç (envanterin küçük hâli):
*"bu desen hangi app/dosyalarda var?"* → liste → her biri kapsandı mı işaretle.
Review kapsamı dar kalır (doğru), **kapsama listesi lider'de** durur.

---

# AŞAMA 2 — SONRADAN YAKALANDIYSA DÜZELTME NASIL YÖNETİLİR

## 2.1 KANONİK SIRA (bu turda ihlal edildi, maliyeti ölçüldü)

```
1. RUNTIME'DA TEYİT ET        → gerçek semptom ne? (10 dk; en pahalı bilgiyi en ucuza verir)
2. ENVANTER / YÜZEY TARAMASI  → paralel fan-out, matris çıktısı, join anahtarı belirle
3. TEK İŞ LİSTESİ + TAHMİN    → kullanıcıya SUN: kapsam, sıra, büyüklük, risk
4. KAPSAM KARARINI AL         → "hepsi mi, bir kısmı mı?" — TEK sefer, toplu
5. DESENİ DONDUR              → kanonik uygulamayı bitir + review'dan geçir
6. ÇOĞALT                     → dondurulmuş deseni diğerlerine uygula
7. TEK REVIEW TURU            → toplu, dar kapsamlı ama sınıf-kapsama listesiyle
8. RUNTIME KABUL              → kullanıcının gördüğü davranış
```

**Bu turda ne oldu:** 1 atlandı → 2 gecikti → 3/4 hiç yapılmadı (kapsam **5 kez ayrı ayrı**
genişletildi) → 5/6 sıra bozuldu (desen değişirken çoğaltma dağıtıldı) → 7 **6 tura** bölündü.

## 2.2 YAPILMASI / YAPILMAMASI GEREKENLER

| ✅ YAP | ❌ YAPMA |
|---|---|
| Önce **runtime'da semptomu gör** | Kaynak okuyarak semptomu **varsay** |
| Yüzeyin tamamını **paralel** tara, matris çıkar | Katmanları **sırayla keşfet** |
| İki taramayı **join anahtarıyla** kur (entity/app adı) | Birleşmeyen iki ayrı liste üret |
| Kapsam kararını **bir kez, toplu** al ve **kullanıcıya sun** | Yol boyunca **"şunu da ekleyelim"** (bu turda 5 kez) |
| Deseni **dondur**, sonra çoğalt | Desen değişirken çoğaltmayı dağıt |
| Review kapsamını **dar** tut, sınıf-kapsama listesini **lider'de** tut | Her review'un "her şeye baktığını" varsay |
| Ajan koşarken **kaynağa dokunma** | Review sürerken dosyayı düzenle (bu turda **3 kez** → bayat inceleme) |
| Takip-iş göndermeden önce **çalışma ağacını ölç** | `idle` bildirimini "iş bitti" sanıp yeni iş yolla (bu turda **~5 kez** çakışma) |
| Biten işi **WIP commit** ile koru | Gate'i beklerken işi commit'siz bırak (oturum düşerse gider) |
| Uzun ajan çıktısını **artımlı diske** yazdır | Sonda tek seferde yazdır (bu turda 3 ajan düştü, **tüm iş kayboldu**) |
| "DOĞRULANAMADI (sebep)" yaz | Kanıtsız **PASS** yaz |
| Sayı/satır referansına **ölçüm tarihi** + içerik çapası | Yoruma çıplak `dosya:satır` yaz (bu turda **6 kez** bayatladı) |

## 2.3 KAPSAM GENİŞLETME — tek kural

Bu turda kapsam 5 kez genişledi ve **her genişleme haklıydı** (gerçek defect bulundu).
Sorun genişlemenin kendisi değil, **dağınık olmasıydı**: kullanıcı her seferinde yeni bir
"şunu da yapalım" duydu ve işin ne zaman biteceğini göremedi.

> **Kural:** genişleme kararı **envanterden sonra, toplu** verilir. Envanter sonrası çıkan her
> yeni bulgu **park edilir**, mevcut parti bitirilir. İstisna: **veri kaybı / geri alınamaz** risk
> → o zaman da kullanıcıya *"kapsam büyüyor, sebebi bu"* denir, sessizce büyütülmez.

## 2.4 REVIEW EKONOMİSİ

Bu turda **6 review turu** koştu. Ölçülen israf kalemleri:
- **Bayat inceleme:** 3 kez kaynak review sürerken değişti → yeniden okuma turu
- **Bölünmüş kapsam:** 5 dosya 3 ayrı turda incelendi (tek turda incelenebilirdi)
- **Aynı sınıfın tekrar tekrar keşfi:** her tur sınıfın yeni bir varyantını buldu

> Önceki bir turdaki ölçüm: review süresinin **%92'si model düşünmesi**, %8'i araç.
> **Darboğaz araç hızı değil, TUR SAYISI.** → Düzenlemeleri topla, öyle review'a ver.

## 2.5 KULLANICIYA GÖRÜNÜRLÜK — bu turun en insani dersi

Kullanıcı iki kez uyardı: *"neden tek tek yapıyorsun"* ve *"takıldık kaldık, başka işlerimiz var"*.
**İkisi de haklıydı ve ikisi de önlenebilirdi.**

> **Kural:** iş beklenenden büyük çıktığı **anda** — keşfedildikçe değil — kullanıcıya
> **(a)** yeni kapsam **(b)** neden büyüdüğü **(c)** tahmini kalan iş **(d)** kesme seçeneği sunulur.
> "Şunu da buldum" mesajlarının toplamı bir durum raporu **değildir**.

Ayrıca her an cevaplanabilir olmalı: **"şu an ne kaldı, ne zaman biter?"**
Cevap veremiyorsan iş listesi yok demektir → 2.1 adım 3'e dön.

---

# AŞAMA 3 — AJAN/EKİP İŞLETİMİ (bu tur özelinde ölçülenler)

- **İletilen kullanıcı onayı NİYET taşır, İZİN taşımaz.** İzin katmanı reddettiyse, lider'in
  talimatı **tekrarlaması yeni deneme gerekçesi değildir**. (Bu turda tekrarlanan talimat, ajanın
  reddedilmiş bir çağrıyı ikinci kez denemesine yol açtı — ajan doğru durdu, hata lider'deydi.)
- **Ajanın lideri düzeltmesi normal ve istenendir.** Bu turda **5 kez** oldu, beşinde de ajan
  haklıydı (yanlış premis · yanlış obje ilişkisi · polimorfizm · isim/kullanım · sayım).
  Brifinge *"itiraz et, kanıt getir"* koy; kanıtsız "yapılamaz"ı kabul etme, **kanıtlıyı tartışma**.
- **Araç sınırı ≠ yokluk.** Bir araç boş döndüğünde önce **aracın kapsamını** doğrula.
  (Bu turda 3 kez: behavior pool `main` boş → "metot yok" sanıldı; lock-check tip desteklemiyor →
  "kilit yok" sanıldı; dar grep deseni → "referans kalmadı" sanıldı.)
- **Severity'yi anchorlayan gerekçe çökerse severity YÜKSELİR.** ("Kardeşte de var, kabul edilmiş
  desen" savunması git geçmişiyle çürütüldü → MEDIUM → HIGH.)
- **"Öncesi neydi" git ile kanıtlanır** (`git show <commit>^`) — bulgunun *bu değişimin ürünü mü,
  pre-existing mi* ayrımı severity'yi belirler.
- **Geri alınamaz bir denemeden önce ön-koşulu KANITLA.** (Gerçek silme denemesi öncesi canlı
  guard'ın var/güncel/kablolu olduğu ayrıca doğrulandı — guard eski sürüm olsaydı kayıt giderdi.)

---

# ÖZ-DEĞERLENDİRME KONTROL LİSTESİ (tura başlarken 2 dakika)

- [ ] Kabul ölçütünü **kullanıcının göreceği davranış** olarak yazdım mı?
- [ ] Semptomu **runtime'da gördüm** mü, yoksa kaynaktan mı varsaydım?
- [ ] Bu davranış **çapraz-kesen** mi? Öyleyse **envanterim var mı**?
- [ ] Kardeş app/obje var mı? **Kanonik referansı** belirledim mi?
- [ ] Platform sınırlarını (uzunluk/kodlama/kırpma) **ölçtüm** mü?
- [ ] Kullanıcıya **tek iş listesi + tahmin** sundum mu, kapsam kararını aldım mı?
- [ ] Desen **donduktan sonra mı** çoğaltıyorum?
- [ ] Review'a vermeden önce **düzenlemeleri topladım** mı?
- [ ] "Şu an ne kaldı?" sorusuna **şu anda** cevap verebiliyor muyum?

📖 İlgili: `howto-delete-guard.md` (bu turun teknik dersleri) · `lessons-learned.md` (hata pattern
kataloğu) · `intake-triage.md` (kapsam sınıflama: S0/S1/S2) · `governance/agent-teams-operating-model.md`

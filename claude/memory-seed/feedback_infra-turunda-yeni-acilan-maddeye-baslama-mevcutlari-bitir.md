---
name: feedback_infra-turunda-yeni-acilan-maddeye-baslama-mevcutlari-bitir
description: Tur içinde çıkan yeni bulgu ÖNERİLMEZ, deferred'e de yazılmaz — yalnız çok önemli ve mutlaka yapılması gereken (kritik/geri alınamaz/doğruluk bozan) bildirilir; önce mevcut maddeler biter
metadata: 
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: cca08bdf-c505-460c-a1ba-8d1635bd8f7c
---

> **Tohum notu (2026-11-12):** bu dersin önceki tohum hâli *"turun sonunda yeni maddeleri listeleyip
> kullanıcıya sun"* diyordu. Kural 2026-10-03'te kullanıcı tarafından **sıkılaştırıldı** (aşağıda);
> eski hâli bu sürümle geçersizdir. Tüm core kullanıcılarına uygulanması kullanıcı kararıdır (2026-11-12).

**Kural (kullanıcı, 2026-09-13):** *"yeni madde açılırsa onlara başlama. mevcutları bitirelim."*
**Sıkılaştırma (kullanıcı, 2026-10-03):** *"yeni bir bulgu çıkarsa, çok önemli ve mutlaka yapılması
gerekmiyorsa önerme, bitmiyor işler bu şekilde sürekli yeni madde ekleyerek"*

- Tur sırasında çıkan yeni bulgu (bug-gate ÖNERİ'leri, ajan "açık nokta"ları, kenar gözlemler)
  **kullanıcıya önerilmez ve ertelenmiş-iş listesine (deferred) kalem olarak da yazılmaz** — sessizce düşer.
- İSTİSNA yalnız: **çok önemli VE mutlaka yapılması gereken** — kritik/geri alınamaz, sessiz yanlış
  veri, güvenlik/PII, ya da uçuştaki işin doğruluğunu bozan. Bunu tek cümleyle bildir **ve YAP**
  (kullanıcı 2026-11-02: *"ders kalsın aynı şekilde, ama önemlileri yapacak şekilde"* — önemli olanın
  kararı liderdedir; örnek: aynı fonksiyonda aynı sessiz-boş kusurun ikinci yolu, düzeltmenin kanıtı
  ona bağlıydı ⇒ kapsama alındı).
- Bug-gate WARNING/BLOCKER bulguları (uçuştaki PR'ın kendisi) bu kuralın dışındadır — onlar mevcut işin
  kapsamıdır; ama onlara eşlik eden ÖNERİ listesini kullanıcıya taşırken süz: yalnız ucuz + o PR'ın
  doğruluğuna dair olanı sun, gerisini düşür.
- Kullanıcının daha önce AÇIKÇA karar verdiği kalemler (ör. "kalem aç") yazılır; yeni değildir.

**Why:** Kuyruk bir turda 7 kapandı / 10 açıldı; 2026-10-03 radar turunda da her bug-gate 5-9 öneri,
her ajan 3-4 "açık nokta" üretti ve ertelenmiş-iş listesi turla birlikte büyüdü — iş bitmiyor.
[[feedback_kardes-taramasi-spawn-oncesi-kapsama-alinir-kuyruga-yazilmaz]] açılan madde sayısını azaltır;
bu kural açılanın ne turu ne listeyi büyütmesini engeller.

**How to apply:** Ajan raporunu kullanıcıya aktarırken yeni-kalem önerisi ekleme; brifte de ajandan
"açık kalem önerisi" isteme (yalnız kritik olanı bildirsin). Kapsama alınabilen kardeş (aynı dosya
kümesi, uçuştaki işin içinde) yeni madde değil mevcut işin kapsamıdır.

**Vaka 2 (2026-10-27) — GÜN-SONU süpürmesinde de geçerli:** core §1.1 gün-sonu maddesindeki
*"bugün doğan ertelenmiş iş aynı anda eklenir"* cümlesi bu kuralı DELMEZ. Bir radar takip turunun 5
yan bulgusu ertelenmiş-iş listesine yeni bölüm olarak yazıldı; kullanıcı: *"bunları neden ekleyip
bıraktın, yapman gerekmiyor mu?"* Ayıklama: 2'si core'da zaten kayıtlıydı (mükerrer), 2'si
gereksizdi, 1'i (ajan MEMORY.md %95,9 bütçe = sessiz kesilme) gerçekten yapılması gerekendi.
⇒ Gün-sonunda "bugün doğan ertelenmiş iş" = yalnız **kullanıcının açıkça "ertele/kalem aç"
dediği** kalem. Tur yan bulgusu: ya **yap** (mutlaka gerekiyorsa, onayla) ya **düşür**; üçüncü
yol "deferred'e yazıp bırakmak" değildir. Kalem yazmadan önce: core'da zaten kayıtlı mı?

Son-doğrulama: 2026-11-02 · Applies-to: tüm çok-PR'lı turlar (infra, radar, doküman) + gün-sonu ertelenmiş-iş süpürmesi

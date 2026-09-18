---
name: feedback_duzeltme-turu-kendi-ciktisina-kapi-ister
description: "Düzeltme turu, bug ÜRETİCİSİDİR — zincir kapı→düzeltme→KAPI olmalı. Bir turu denetlemek, o turun ÜRETTİĞİNİ denetlemek değildir; ikinci kapı DAR olsun (değişen satır + değişen sayının diğer geçtiği yerler) ve BAŞKA göz koşsun"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 500a163e-c3ce-4b97-9c3d-35322425892b
---

**Bir turu denetlemek ≠ o turun ÜRETTİĞİNİ denetlemek.** Zincir `kapı → düzeltme → (kapı yok)`
biçiminde açık kalırsa, düzeltme turu **yeni bug üretir ve kimse bakmaz**.

**Vaka (2026-08-19, <PAKET-A> RAP seti).** Gün boyu üç doküman kapısı koştu, 47 bulgu kapatıldı.
Akşam dört bağımsız kontrol daha koşuldu: **44 yeni bulgu** (2 BLOCKER · 4 HIGH). Sebep analizinde
sayıldı: bulguların **~%40'ı o günkü düzeltme turlarının kendi çıktısından** doğmuştu.
En pahalısı: *"Kural A arama penceresi kaldırıldı"* kararı alındı, **5 yerde** güncelleme gerekiyordu,
**4'ü** yapıldı — kalan yer **normatif sözde-koddu**. Belgeye sadık bir geliştirici **iptal edilmiş
kuralı** kodlayacaktı; hasar: aynı mesaj için **ikinci sipariş + teslimat + mal çıkışı + fatura**.
Aynı kalıp `[Aktarımı Geri Al]` tetiğinde de tekrarlandı (FS ve backend düzeltilmiş, **UI bölümü
düzeltilmemiş**).

**Why:** Düzeltme, doğası gereği **birden çok yere dokunan** bir iştir ve dokunulan yer sayısı
belgede yazmaz. Kapı bulguyu bulur, düzeltici N-1 yeri günceller, tur kapanır. Kaçan yer **bir
sonraki turda** yeni bulgu olarak geri döner ⇒ *"bu iş neden bitmiyor"* hissinin asıl kaynağı budur:
bulgular kaçırıldığı için değil, **üretildiği için** damla damla gelir.

**How to apply:**
- **Kural: düzeltme turu, kendi çıktısına kapı koşmadan KAPANMAZ.** Bunu turun tanımına yaz.
- ⚠ **İkinci kapı DAR olsun**, yoksa uygulanmaz: ① değişen satırlar ② **değişen her sayının/adın
  belgedeki diğer geçtiği yerler** ③ kararın yayılım listesi. **Tam yeniden okuma değil** — dar
  kapsam süreyi ~%20'ye indirir ve *"kapı yorgunluğu"* (mekanik onay) riskini düşürür.
- **Bağımsızlık:** ikinci kapıyı **birinci kapıyı koşan göz koşamaz**.
- Düzeltirken *"bu gerçek başka nerede yaşıyor"* sorusunu **düzeltmeden önce** sor ve listele —
  [[feedback_cok-katmanli-degisiklik-yonetimi]]'nin yayılım tablosu tam bunun içindir.
- Süre baskısı varsa kesilecek şey **tur sayısı**dır, **göz sayısı değil**
  ([[feedback_kendi-isini-yeniden-siniflandirip-kural-disina-cikma]]).

İlgili: [[feedback_done-tam-kapsam-dogrula]] · [[feedback_yesil-sinyalin-kapsamini-sor]] ·
[[feedback_ters-yon-kontrolu]] · [[feedback_sonucu-olc-uygulamayi-degil]]

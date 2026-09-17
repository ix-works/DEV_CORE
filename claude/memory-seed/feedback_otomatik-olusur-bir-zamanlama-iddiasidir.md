---
name: feedback_otomatik-olusur-bir-zamanlama-iddiasidir
description: "\"X otomatik olusur\" bir ZAMANLAMA iddiasidir; 'olusuyor' ile 'senin okuyacagin anda var' ayni sey degildir"
metadata:
  type: feedback
---

*"Şu belge/görev otomatik oluşur"* cümlesi **iki ayrı iddia** taşır ve ikincisi genellikle
ölçülmez: **(a)** oluşuyor mu · **(b)** **senin okuyacağın ANDA** var mı.
Tasarımı belirleyen (b)'dir.

**Ölçülmüş vaka (2026-09-08, EWM depo görevi):** "teslimat yaratılınca depo görevleri (WT)
doğar" — (a) **doğru**: `/SCWM/ORDIM_C` `rdoccat='PDO'` **2566 satır**.
(b) **YANLIŞ**: teslimat `8000000084` **10:02:28**'de yaratıldı, ilk WT **10:49:43**'te — **+47 dk**.
Açık WT (`/SCWM/ORDIM_O`, `PDO`) = **0** ⇒ WT doğar doğmaz konfirme ediliyor.
⇒ Teslimattan hemen sonra basılacak bir fiş WT'yi **bulamaz**; tüm "hangi raftan al" kurgusu
çökerdi. Kurgu serbest stok tabanlıya çevrildi ve çıktıda *"tahsis değildir"* şerhi verildi.

⚠ **Ölçerken saat dilimi:** `LIKP-ERZET` **lokal**, `/SCWM/ORDIM_*.CREATED_AT` **UTC** (TR=+3).
Karıştırılırsa fark **ters işaretli** görünür ve varsayım yanlışlıkla **"doğrulanmış"** olur.

**Why:** Varlık ölçümü (tabloda satır var mı) zamanlama sorusunu **cevaplamış gibi görünür**.
Toplam sayı büyük olduğu için ("2566 satır var") ikna edici; oysa senin anında **sıfır**.
Bu, [[feedback_kod-yolu-vardi-veri-gecmemisti]] ile aynı aile — yol var, o anda içinden
geçen yok.

**How to apply:**
- "Otomatik oluşur" duyduğunda **iki zaman damgasını karşılaştır**: tetikleyen belgenin
  yaratılma anı ↔ türeyen nesnenin yaratılma anı. Tek satırlık ölçüm yeter.
- **Açık/kapalı ayrımını da ölç**: "kapalılar tablosu dolu, açıklar tablosu boş" ⇒ nesne
  ömürlü değil, anında tüketiliyor demektir.
- Zamanlamayı ölçemiyorsan tasarımı **o nesneye bağlama**; bağlıyorsan varsayımı belgeye
  **açıkça** yaz ki halef yeniden ölçebilsin.
- Saat dilimi karışımlarında **önce birimleri eşitle**, sonra fark al.

İlgili: [[feedback_sonucu-olc-uygulamayi-degil]] · [[feedback_kapsam-niteleyicisini-dusurme]] ·
[[project_ewm-embedded-erp-lgnum-cevirisi]]

---
name: feedback_satir-sayisi-artisi-cogaltma-degildir-satir-tekil-farki
description: "Bir çoğaltma kusurunu satır SAYISIYLA takip etme — ölçüt satır ≠ tekil farkıdır; yeni veri geldiğinde eski \"kırık sayı\" masumca geri gelir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 84facfd3-9151-4893-8380-15c2cfd0d393
---

Bir kardinalite/çoğaltma kusurunu teşhis ederken akılda **bir sayı** kalır ("39 satır = kırık,
38 = sağlam"). O sayı **kusurun kendisi değil, o günkü verinin izidir**. Veri büyüyünce aynı sayı
tamamen sağlıklı bir sebeple geri gelir ve düzeltmeyi yanlışlıkla geri alma refleksi doğar.

**2026-09-08, ZSD001 booking:** `ZSD001_I_CONTAINER_GROSS` düzeltmesinden önce
`zsd001_i_booking_container` **39 satır / 38 tekil** idi (biri hayalet — birimsiz teslimatın açtığı
ikinci GROUP BY kovası). Düzeltmeden sonra **38/38**. Kullanıcı UI'dan 2. konteyneri ekleyince yine
**39** oldu — ama bu sefer **39/39**: `zsd001_t_bookit` de 38→39 olmuştu, yani satır **gerçek bir
kalemdi**. "39 = kırık" refleksiyle bakılsaydı çalışan düzeltme kusurlu ilan edilirdi.

**Why:** Çoğaltma, satır sayısının *mutlak değeri* değil, **satır sayısı ile iş-anahtarı tekil
sayısı arasındaki fark**tır. Mutlak sayı hem düzeltmeyle hem de normal veri girişiyle değişir;
fark yalnız kusurla değişir. Aynı sebeple "önce/sonra" karşılaştırması **kaynak tabloyla birlikte**
okunmalı — view 39 dönüyorsa `t_bookit` kaç kalem taşıyor?

**How to apply:** Bir çoğaltma bulgusunu yazarken sayıyı **daima çift** yaz: `<satır>/<tekil>`, ve
karşılaştırma tabanını da (`t_bookit`=N) ekle. Sonraki turda ölçerken tek sorgu yetmez — view'ın
satır sayısına bakıp hüküm kurma, `SELECT <ilan edilen key alanları>` ile tekil sayısını da al ve
kaynak tabloyla kıyasla. İlgili:
[[feedback_cds-tekillik-olcumunde-alan-listesi-bulguyu-degistirir]] ·
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]] ·
[[feedback_kapsam-niteleyicisini-dusurme]] ·
[[feedback_literal-filtreli-ab-runtime-hatasini-yeniden-uretemez-pushdown]]

---
name: feedback_cds-tekillik-olcumunde-alan-listesi-bulguyu-degistirir
description: "CDS'te \"çoğaltıyor mu\" ölçümü, SELECT'in alan listesi yazılmadan kurulamaz — seçilmeyen association'ı HANA budar ve çoğaltma görünmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 84facfd3-9151-4893-8380-15c2cfd0d393
---

Bir CDS view'ın satır çoğaltıp çoğaltmadığını ölçerken **hangi alanları seçtiğin bulguyu
değiştirir**. Bir association'dan **hiçbir alan seçmezsen** HANA to-one join'i **budar** (join
pruning) ve o join'in ürettiği çoğaltma **ölçümde görünmez**.

Canlı vaka (2026-09-08, ZSD001 booking `SQL 305`):
- `SELECT bookingno, itemno FROM zsd001_i_booking_container` → **38 satır**, `(BookingNo,ItemNo)`
  **38/38 tekil** ⇒ "view çoğaltmıyor" hükmü kuruldu ve bununla bir hipotez **çürütüldü**.
- `SELECT bookingno, itemno, capacity` (yani `_Capacity` association'ından bir alan) → **39 satır**,
  `7700000032/000010` **iki kez**. Hüküm **YANLIŞTI**; asıl kusur oradaydı.

**Why:** Tekillik iddiası ölçümün **kapsamına** bağlıdır, ama kapsamı burada `WHERE` değil **alan
listesi** belirler — bu görünmez bir niteleyicidir. Yanlış hüküm, kök nedeni bulmayı bir tur
geciktirdi ve doğru hipotezi haksız yere düşürdü ([[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]]).

**How to apply:** "Şu view çoğaltıyor mu?" sorusunu cevaplarken (a) **şüphelenilen her
association'dan en az bir alan SEÇ**, (b) bulguyu yazarken **çalıştırdığın SELECT'i alan listesiyle
birlikte** yaz — "tekillik ölçtüm" cümlesi alan listesi olmadan kanıt değildir
([[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]]), (c) `[0..1]` ilan edilmiş bir
association'ın gerçekten `[0..1]` olduğunu **hedef view'ın key'i ile GROUP BY'ını karşılaştırarak**
doğrula — anahtarını tutmayan agregat view sessizce çoğaltır
([[feedback_kapsam-niteleyicisini-dusurme]]).

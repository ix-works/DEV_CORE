---
name: feedback_uyarlama-verisi-acik-kalem-degil
description: Uyarlama/ana-veri tablolarındaki DEĞERLER açık-kalem defterine yazılmaz — kullanıcının alanı
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f308e22e-e48e-4701-b7b4-fe8debc477e2
---

Kullanıcı kuralı (2026-08-12): **uyarlama / ana-veri tablolarındaki değerler AI'ın takip kalemi
değildir.** "Şu tabloda şu değer test değerinde kalmış, geri alınmalı" gibi kayıtlar açık-kalem
defterlerine (RESUME · deferred-triggers · SESSION_NOTES · memory) **yazılmaz**. Doğru değeri
kullanıcı bilir ve gerektiğinde kendisi yazar.

**Why:** Bu değerler sürekli değişir; AI'ın gördüğü an bir fotoğraftır. Kayda geçirilince
(a) her oturumda "açık iş" gibi geri gelir, (b) kullanıcı çoktan düzeltmiş olsa bile defter
"açık" der = yanlış-pozitif, (c) sahiplik karışır — veri kullanıcının, kayıt AI'ın olur.
Vaka: `ZSD001_T_CONTY.KMY3.BRGEW` 3.000 (test) → memory + SESSION_NOTES'a "geri alınmalı" diye
yazılmıştı; 16 gün "açık kalem" olarak taşındı, oysa hiç kimsenin takip etmesi gereken bir şey
değildi. Kullanıcı: *"bu açık değil, bu bir kural değil, doğrusu ne ise ben yazarım zaten."*

**How to apply:** Bir tablo DEĞERİ gözlemlediğinde: gerekiyorsa o anda **söyle** (ölçüm sonucu),
ama **kayda geçirme**. Kayda geçen yalnız şunlardır: KOD kusuru · eksik geliştirme · yapısal
karar. Ayrım testi: *"düzeltmesi SM30/SPRO'dan veri girmek mi?"* → evet ise takip kalemi DEĞİL.
İstisna: kullanıcı açıkça "bunu bana hatırlat" derse. Aynı sınıf: test verisi temizliği, POF/koşul
kaydı bakımı, yetki-rol ataması — hepsi kullanıcı alanı. ⚠ FS'in "açık kararlar" bölümüne de
uyarlama-verisi sorusu yazma; oraya yalnız **fonksiyonel karar** girer.
Son-doğrulama: 2026-08-12 · Applies-to: tüm projeler.
İlgili: [[feedback_flag-degil-icra-bekleyen-is-kapat]] · [[feedback_takim-sureklilik-gun-sonu-resume]]

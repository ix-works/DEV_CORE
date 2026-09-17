---
name: _indeks-karar-iletisim
description: Karar, iletişim ve iş yönetimi derslerinin tam indeksi
metadata: 
  node_type: memory
  type: reference
---

# Karar · iletişim · iş yönetimi — tohum indeksi

> Onay, kapanış, kapsam ve açık-madde yönetimi. Bu dosya `MEMORY.md`'den link'lenir; dersler burada yaşar.

**9 ders.**

- ⭐ [Alinti onay turu acmaz toren enflasyonu](feedback_alinti-onay-turu-acmaz-toren-enflasyonu.md) — ALINTI onay turu AÇMAZ — provenance damgası (`[TS]`/`[ONERI]`) onay kuyruğu değildir; <PAKET-A>'de bu ayrımın kaybı 15 onay belgesi + çok turlu 'metin onay töreni' üretti (kardeş <PAKET-B>: 1750 anahtar, 0 belge)
- ⭐ [Github actions asili queued kosu pr kapat ac](feedback_github-actions-asili-queued-kosu-pr-kapat-ac.md) — GitHub Actions koşusu saatlerce `queued` + 0 job asılı kalırsa cancel/rerun çelişkili döner; PR'ı kapat+yeniden aç (tek komutta) yeni koşu doğurur
- ⭐ [Grup bazli genisletmede her grup kendi dali ve metodu](feedback_grup-bazli-genisletmede-her-grup-kendi-dali-ve-metodu.md) — Müşteri grubu bazlı mantığı yeni gruplara açarken her grup KENDİ WHEN dalı + KENDİ MODIFY_<GRUP> metodu alır; OR ile birleştirme / başka grubun metodunu çağırma YOK — gövde bugün kopya olsa bile
- ⭐ [Karar dosyasi kapandi yazmak icra degildir](feedback_karar-dosyasi-kapandi-yazmak-icra-degildir.md) — Kendi karar dosyanda 'KAPANDI' yazmak kaydı kapatmaz — kapanış İCRANIN kanıtına dayanır; toplu kuyruk turlarında bu hata SESSİZ ve ÖLÇEKLİ olur (2026-08-29: 84 kaydın 3'ü kanıtsız kapatılmıştı, kapıyı yazan ajan yakaladı)
- ⭐ [Kendi isini yeniden siniflandirip kural disina cikma](feedback_kendi-isini-yeniden-siniflandirip-kural-disina-cikma.md) — Kuralı esnetmenin yolu onu ihlal etmek değil, işi YENİDEN SINIFLANDIRMAK — \"bu build değil, araç\" deyip bug gate'i atlamak; ve süre baskısında yanlış yeri kesmek
- ⭐ [Kullanicinin bildigi is gercegini olcmek yerine sor](feedback_kullanicinin-bildigi-is-gercegini-olcmek-yerine-sor.md) — Kullanıcının kendi yaptığı deneme/bildiği iş gerçeği (sonuç, alan doluluğu) için pahalı canlı ölçüm yerine ÖNCE kullanıcıya sor
- ⭐ [Once sonra kanitinin zaman damgasini kontrol et](feedback_once-sonra-kanitinin-zaman-damgasini-kontrol-et.md) — Ajanın sunduğu 'önce/sonra' kıyasında iki çıktı dosyasının zaman damgası AYNIYSA, kıyas trivially-true olabilir — 'ESKİ' dosya aslında yeni kodla üretilmiş olabilir. Kıyasın kendisi de bir iddiadır.
- ⭐ [Uyarlama verisi acik kalem degil](feedback_uyarlama-verisi-acik-kalem-degil.md) — Uyarlama/ana-veri tablolarındaki DEĞERLER açık-kalem defterine yazılmaz — kullanıcının alanı
- ⭐ [Yesil regresyon suiti duzeltmenin kaniti degildir](feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir.md) — Yeşil bir regresyon süiti düzeltmenin ÇALIŞTIĞINI kanıtlamaz — süiti düzeltme ÖNCESİ sürümde de koş; o da yeşilse ağ KÖRDÜR. Her düzeltme turu ayırt edici test + aşırı-baskılama KONTROL testi ister

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_alinti-onay-turu-acmaz-toren-enflasyonu]] · [[feedback_github-actions-asili-queued-kosu-pr-kapat-ac]] · [[feedback_grup-bazli-genisletmede-her-grup-kendi-dali-ve-metodu]] · [[feedback_karar-dosyasi-kapandi-yazmak-icra-degildir]] · [[feedback_kendi-isini-yeniden-siniflandirip-kural-disina-cikma]] · [[feedback_kullanicinin-bildigi-is-gercegini-olcmek-yerine-sor]] · [[feedback_once-sonra-kanitinin-zaman-damgasini-kontrol-et]] · [[feedback_uyarlama-verisi-acik-kalem-degil]] · [[feedback_yesil-regresyon-suiti-duzeltmenin-kaniti-degildir]]

---
name: feedback_duzeltme-turu-kendi-regresyonunu-uretir
description: "Kapı bulgusunu kapatan düzeltme, kapatırken YENİ bir regresyon üretebilir — ikinci kapı bunun için var; birinci kapı o kodu HİÇ GÖRMEDİ"
metadata:
  node_type: memory
  type: feedback
---

Bir kapı bulgusunu kapatan düzeltme **kendi regresyonunu üretebilir** ve birinci kapı bunu
yakalayamaz — çünkü o kod incelendiğinde **henüz yoktu**.

**Vaka (2026-08-20, `ZCL_SD001_LOG`):** 1. kapı *"külçe sınırı kodda zorlanmıyor"* dedi (haklı).
Düzeltme bir handle tamponu ekledi ve onu `(alt-obje, msgno)` ile anahtarladı. 2. kapı **BLOCKER**
verdi: külçe sınırı 8 eksenin yalnız 2'sinde mesaj bazlı; `PARSE` IDoc başına ve `log_open`
`msgno` doğmadan çağrılıyor ⇒ anahtar tek slota çöküyor, ALE paketindeki **bütün IDoc'ların
kanıtı ilk külçeye** yığılıyordu. ⭐ Tampon **eklenmeden önce davranış DOĞRUYDU**.

**Why:** düzeltme, sorunu çözerken sistemin **başka bir değişmezini** varsayar; o varsayım
kapının kapsamında değildi. Bulgunun kapatılması, kapsamın da genişlemesi demektir.

**How to apply:** `kapı → düzeltme → KAPI`. İkinci kapı **DAR** (yalnız değişen satırlar) ve
**BAŞKA GÖZ** (birinci kapının raporunu görmemiş) olmalı — birinci kapı kendi teşhisinin gözüyle
okur. Yorum-only turlar bu kuralın dışında: orada lider okuması yeter (orantı).
İlgili: [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]]

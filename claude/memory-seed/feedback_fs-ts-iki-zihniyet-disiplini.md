---
name: feedback_fs-ts-iki-zihniyet-disiplini
description: "FS'i kullanıcı-gözüyle, TS'i developer-gözüyle yaz; danışman katkısı=öneri(onay); açık nokta build'e ertelenmez; TS FS'i denetler"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6d5ce53a-13a4-4943-9fe8-cde3bcec3496
---

**FS = kullanıcı gözü, TS = developer gözü.** FS'i "bu uygulamayı her gün ben kullanacakmışım"
gibi (ekran/ergonomi/boş-hata-edge/"kaydet sonrası ne oluşur"); TS'i "bu TS'le ben build
edeceğim, satır-1 öncesi neyi bilmem gerekir" gibi yaz.

**Why:** Jenerik şablon "hangi bölümler" der ama derinlik disiplini vermez → fonksiyonel
kararlar "build'de netleşir"e ertelenip developer tahmine düşer, gitgel olur (<PAKET-E> TS'inde
eşleştirme/dönüşüm kararları DTEL-adıyla aynı torbaya düşmüştü).

**How to apply:**
- **İLKE-1** kullanıcı isteği=kanon (atlanamaz/gölgelenemez); **İLKE-2** danışman katkısı=`[ÖNERİ]`
  (ayrı bölümde, onay şart) + açık nokta = soru-seti (seçenek+öneri, tek-tek), build'e erteleme YOK.
- **İLKE-3** FS=otorite, her FR/KR'ye TS çözümü; **İLKE-4** TS FS'i DENETLER (fizibilite/yan-etki/
  blast-radius/alternatif/hata → DUR+bilgilendir, kör build yok); **İLKE-5** "ertelenebilir mi?":
  teknik-teyit (DTEL/CONVERT KEY/lib-syntax — canlı doğrula) ≠ fonksiyonel karar (eşleştirme/
  çoklu-eşleşme/ALPHA-tarih-ondalık/UoM/entity-child/edge/kilit — TS'te KAPANIR).

**Kanonik:** `core/standards/04-documentation-fs-ts.md` v1.2 (FS §2.0/§11-A/§11-B · TS §3.0/§2-A/§11-A · §7-§8).
İlgili: [[tek-soru-ve-bagimsiz-dokuman]] · [[sorulari-tek-tek-sor-oneriyle]] · [[fix-oncesi-where-used-blast-radius]] · [[done-tam-kapsam-dogrula]]

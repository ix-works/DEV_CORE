---
name: feedback_stxl-clustr-bos-metin-sondasi
description: "SAP uzun metin gövdesi boş mu? READ_TEXT koşmadan STXL-CLUSTR (bayt uzunluğu) kontrol grubuyla kıyasla — DEV VBBK'da 81 = boş not, dolu 90–121"
metadata:
  type: feedback
  seed: evet
---

Bir virtual element / rapor not kolonunu boş döndürünce "kod mu veri mi" sorusu READ_TEXT çalıştırmadan cevaplanabilir: `SELECT tdname, tdid, srtf2, clustr FROM stxl WHERE relid='TX' AND tdobject=... AND tdname IN (...)`. `CLUSTR` sıkıştırılmış gövdenin bayt uzunluğudur; STXH'de başlık (TDTXTLINES=1) dururken gövde boş olabilir.

**Ölçüm (2026-10-05, S/4 2025 DEV, VBBK, TDSPRAS T):** üç notu da boş görünen belge A → 81/81/81 · üçü dolu belge B → 111/121/121 · belge C Not1 "Acil" → 90, diğer ikisi 81 (belge numaraları temsilî). OData çıktısı birebir uyuştu ⇒ boşluk veri, kod değil.

**Why:** Gateway ajanı "kod doğru, gövde muhtemelen boş" dedi ama "STXL cluster okunamaz, DOĞRULANAMADI" diye bıraktı; uzunluk kolonu cluster okumadan kanıt veriyor.
**How to apply:** daima bir dolu + bir boş KONTROL GRUBU ile kıyasla — 81 sabiti başka TDOBJECT/dil/sürümde farklı olabilir (ölçülmedi). Sınır: yalnız "boş mu" sorusunu cevaplar, içeriği vermez.
Son-doğrulama: 2026-10-05 · Applies-to: s4_private/ecc, SAPscript uzun metin (STXH/STXL)

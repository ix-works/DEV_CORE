---
name: feedback_pdftotext-enc-utf8-olmadan-turkce-bozuk
description: "pdftotext `-enc UTF-8` verilmezse Türkçe harfler � çıkar — PDF bozuk SANILIR; ayrıca html_to_pdf.js göreli yolu sürecin cwd'sine göre çözer ('/' şart değil)"
metadata:
  type: feedback
  seed: evet
---

Windows'ta `pdftotext x.pdf -` çıktısında ş/ğ/ı/ç `�` görünür; PDF sağlamdır, eksik olan
`-enc UTF-8` bayrağıdır. Bayraksız ölçüm "mojibake var" diye sahte bulgu üretir (2026-10-10).
Aynı hatta: `core/scripts/html_to_pdf.js` göreli yolu (`x.html`) **sürecin cwd'sine** göre çözer
(`path.resolve`, ilk sürümden beri). Bash aracının cwd'si her çağrıda proje köküne döndüğü için
dosyanın kendi dizininde sanılan çıplak ad bulunamaz ve araç hata verir — **tam yol ver**.
*Düzeltme (2026-11-07):* önceki metin "yol yalnız `/` içeriyorsa kabul edilir" diyordu; ölçüm
(aynı çıplak ad dosyanın dizininden `PDF OK`, başka cwd'den PDF üretilmedi) mekanizmanın cwd olduğunu gösterdi.

**How to apply:** PDF metin sondası daima `pdftotext -enc UTF-8 <pdf> -`; mojibake taraması o
çıktı üzerinde. Brife bu bayrağı yaz.
Son-doğrulama: 2026-11-07 · Applies-to: Windows, poppler pdftotext + core html_to_pdf.js
İlgili: [[feedback_mojibake-taramasi-ciplak-karakter-aramaz]]

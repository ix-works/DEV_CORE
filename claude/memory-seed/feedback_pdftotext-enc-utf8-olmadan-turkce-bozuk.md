---
name: feedback_pdftotext-enc-utf8-olmadan-turkce-bozuk
description: "pdftotext `-enc UTF-8` verilmezse Türkçe harfler � çıkar — PDF bozuk SANILIR; ayrıca html_to_pdf.js yalnız '/' içeren yolları kabul eder"
metadata:
  type: feedback
  seed: evet
---

Windows'ta `pdftotext x.pdf -` çıktısında ş/ğ/ı/ç `�` görünür; PDF sağlamdır, eksik olan
`-enc UTF-8` bayrağıdır. Bayraksız ölçüm "mojibake var" diye sahte bulgu üretir (2026-10-10).
Aynı hatta: `core/scripts/html_to_pdf.js` girdi/çıktı yolunu yalnız `/` içeriyorsa kabul eder —
çıplak dosya adı (`x.html`) verilirse çalışmaz; `./x.html` ya da tam yol ver.

**How to apply:** PDF metin sondası daima `pdftotext -enc UTF-8 <pdf> -`; mojibake taraması o
çıktı üzerinde. Brife bu bayrağı yaz.
Son-doğrulama: 2026-10-10 · Applies-to: Windows, poppler pdftotext + core html_to_pdf.js
İlgili: [[feedback_mojibake-taramasi-ciplak-karakter-aramaz]]

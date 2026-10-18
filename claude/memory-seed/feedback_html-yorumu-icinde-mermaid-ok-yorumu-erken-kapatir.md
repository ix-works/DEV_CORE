---
name: feedback_html-yorumu-icinde-mermaid-ok-yorumu-erken-kapatir
description: "⛔ HTML yorumu (<!-- -->) içine konan mermaid kaynağı `-->` oku yüzünden yorumu ERKEN kapatır — kaynak KD html/pdf'e görünür metin olarak sızar; check_kd_no_raw_mermaid görmez"
metadata:
  type: feedback
  seed: evet
---

Mermaid kaynağını "gizli dursun" diye `<!-- ... -->` içine koymak çalışmaz: mermaid oku `A --> B`
içindeki ilk `-->` HTML yorumunu **orada kapatır**; geri kalan kaynak html'de ve PDF'te düz metin
olarak görünür. Hata vermez, sessizdir. `check_kd_no_raw_mermaid.py` yalnız ```mermaid çitlerini
aradığı için bunu **yakalamaz** (2026-10-10, KD doküman turu — kapanış gate'i yakaladı).

**Why:** yorum sözdizimi ile içerik sözdizimi çakışıyor; dedektör çit arıyor, yorum aramıyor.

**How to apply:** mermaid kaynağını HTML yorumunda saklama — ya render edilen çitte bırak ya ayrı
`.mmd` dosyasında tut. Üretilen html'de `-->` ve `graph TD`/`flowchart` gibi mermaid anahtar
sözcüklerini görünür metinde ara (kod blokları ayıklanmış hâlde).
Son-doğrulama: 2026-10-10 · Applies-to: md→html→pdf doküman hattı (python-markdown)
İlgili: [[feedback_gfm-tablo-bos-satir-tuzagi]]

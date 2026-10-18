---
name: daterangeselection-ikinci-tarih-gun-sonu
description: "sap.m.DateRangeSelection secondDateValue GÜN SONU (23:59:59) döner — ay/gün farkı hesabı tam yıllık aralığı (01.01–31.12) '12 aydan uzun' sayar; karşılaştırmadan önce iki ucu gün başına indir"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 558cf803-e863-47bd-a743-3e15bcb13a3b
  modified: 2026-10-15T12:04:01.289Z
---

`sap.m.DateRangeSelection`'ın ikinci tarihi (`secondDateValue`) seçilen günün **23:59:59**'unu taşır. "En fazla 12 ay" gibi bir aralık doğrulaması Date nesneleriyle yapılırsa 01.01.2026–31.12.2026 aralığı sınırı aşmış görünür ve yanlış hata verir. Çözüm: iki ucu karşılaştırmadan ÖNCE gün başına normalize et (`new Date(y, m, d)`); backend'e tarih gönderirken ayrıca V2 date-only kuralı geçerli ([[v2-date-only-filtre-utc-gece-yarisi]]).

**Why:** Bir projede, 2026-10-15 tarayıcı turu — frontend-expert canlıda buldu, `_day()` normalizasyonuyla düzeltip yeniden ölçtü.

**How to apply:** Tarih aralığı sınır denetimi yazarken sınır VE sınır+1 gün vakasını (29.02 dahil) tarayıcıda dene; Date farkını ham `getTime()` ile değil gün başına indirilmiş değerlerle hesapla.

Son-doğrulama: 2026-10-15 — canlı :8094, UI5 1.120.23
Applies-to: freestyle UI5 (sap.m.DateRangeSelection) — tüm profiller
prior-art: yok (memory + core `secondDateValue` 0 isabet); komşu [[v2-date-only-filtre-utc-gece-yarisi]] (gönderim yönü).

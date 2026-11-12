---
name: feedback_seed-alanina-satir-ici-yorum-yazma
description: "`metadata.seed:` değerinin yanına satır içi yorum (`# …`) YAZMA — `seed_memory --terfi-adaylari` satırı okuyamaz, ders sessizce '<YOK> karar verilmedi' kovasına düşer; gerekçe commit mesajına / kayda"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: d7b2c470-6e85-4b67-a545-2fab9c13ebe7
---

`metadata.seed:` alanı **yalnız tek değer** taşır: `seed: evet` · `seed: hayir` · `seed: hayir:<tek-kelime-gerekçe>`.
Değerin yanına satır içi yorum (`seed: evet   # kullanıcı kararı …`) yazılırsa
`seed_memory.py` `SEED_ETIKET_RE` (`^\s*seed:\s*(\S+)\s*$`) satırı **eşleştirmez** ⇒ ders
`--terfi-adaylari` raporunda **`<YOK>` (karar verilmedi)** kovasına düşer — hata yok, uyarı yok.

**Why:** 2026-11-12 üç dersin kararı `evet`'e çevrildi ve kaynak notu satır içine yazıldı;
araç "evet 7 / <YOK> 3" gösterdi (beklenen "evet 10"). Yorum kaldırılınca "evet 10" — ölçüldü.
Kararın kaynağı kuyruk kaydında ve commit mesajında zaten duruyordu.

**How to apply:** `seed:` alanını değiştirdikten sonra `python core/scripts/seed_memory.py
--terfi-adaylari` koş ve dersin beklenen kovada göründüğünü ölç. Gerekçe gerekiyorsa
`hayir:<tek-kelime>` biçimi ya da commit mesajı; uzun not frontmatter dışında gövdeye.
Prior-art: yok (arandı: memory + tohum + `seed_memory.py`).

Son-doğrulama: 2026-11-12 · Applies-to: core `seed_memory.py` (SEED_ETIKET_RE); tüm profiller

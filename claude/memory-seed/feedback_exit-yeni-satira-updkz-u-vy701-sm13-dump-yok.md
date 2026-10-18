---
name: feedback_exit-yeni-satira-updkz-u-vy701-sm13-dump-yok
description: "Kullanıcı exit'i YENİ satıra UPDKZ='U' basarsa standart db_update UPDATE ... FROM TABLE RC 4 → A-mesaj VY 701 → SM13 V1 hata; ST22 dump YAZILMAZ (VI01/VFKN vakası)"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 92dff1a1-6efa-49c3-ae86-56b21b391799
  modified: 2026-09-23T09:59:50.765Z
---

Belge exit'i (ör. VI01 `ZXV54U19` → projeye özgü bir Z include, tablo `VFKN`) iç tabloda **yeni eklenen** satırlara `UPDKZ = 'U'` verirse, standart güncelleme (`LV54UF01` db_update) o satırlar için `UPDATE (i_table) FROM TABLE` koşar; DB'de satır olmadığı için RC 4 → `MESSAGE A` **VY 701** → güncelleme görevi **SM13'te V1 "güncellenemez" hata**. **ST22'de dump YOKTUR** — kullanıcı "dump" der ama arama ST22'de değil SM13'tedir. SM13'teki kayıtlar kurtarılamaz; belge yeniden yaratılır.

Düzeltme (kullanıcı uyguladı, 2026-09-23 canlı teyit): `IF <fs>-updkz IS INITIAL. <fs>-updkz = 'U'. ENDIF.` — yalnız DB'de var olan (UPDKZ boş) satır 'U' olur; yeni satırın 'I'si korunur.

**Why:** Semptom (SM13 V1, dump yok) kök nedeni exit'e değil standart koda işaret ediyor gibi görünür; UPDKZ semantiği (I/U/D) bilinmeden saatler gider.
**How to apply:** SM13 V1 + VY 701 + dump yok üçlüsünü görünce önce ilgili kullanıcı exit'lerinde UPDKZ atamalarını ara; yeni satır mı mevcut satır mı ayrımına bak.

Son-doğrulama: 2026-09-23 · Applies-to: s4_private/ecc klasik SD belge exit'leri (UPDKZ'li iç tablolar)
prior-art: yok (memory grep `updkz|VY 701|VFKN` → 0)

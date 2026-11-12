---
name: feedback_exit-include-e-az-yorum
description: "Exit include'larına (ve genel olarak koda) uzun açıklama/yorum bloğu yazma — tek kısa satır yeter; kullanıcı aşırı yorumdan şikayetçi"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: bae16578-3da1-492d-bdf1-1b485f1ef5d8
---

Kullanıcı 2026-10-30'da şöyle dedi: *"çok geniş fazla açıklama yazma , bazen çok aşırı yazıyon fazla fazla exitlere"*.

**Why:** Exit include'ları her satış belgesi kaydında okunan, birçok geliştiricinin paylaştığı dosyalardır. AI'ın yazdığı çok satırlı gerekçe blokları (vaka: bir kayıt-öncesi exit include'unda tek bir depo yeri kontrolü için ~25 satırlık yorum) dosyayı şişiriyor.

**How to apply:**
- Exit include'una eklenen her çağrı için **en çok tek kısa yorum satırı** yazılır (ör. `* ZSD001 <iş adı>`). Gerekçe, kapsam ve tarihçe TS'te durur, kodda durmaz.
- Mevcut uzun yorumlara dokunma; kullanıcı ayrıca istemedikçe temizlik yapma.
- Kullanıcıya verilen yanıtlar da kısa olmalı.

Son-doğrulama: 2026-10-30 · Applies-to: bu çekirdeği kullanan tüm projeler — exit include'ları / ABAP yorumları (kullanıcı kararı 2026-11-12: tüm core kullanıcılarına)

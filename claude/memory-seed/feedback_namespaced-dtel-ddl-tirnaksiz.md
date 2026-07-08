---
name: feedback_namespaced-dtel-ddl-tirnaksiz
description: "DDIC table DDL'inde namespaced DTEL (/SCWM/..) TIRNAKSIZ küçük harf yazılır; tek-tırnak sessizce düşürülür"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4cc5b852-1de0-4cd4-aa55-3ab42f32a9fc
---

DDIC tablo DDL'inde namespaced data element referansı (örn `/SCWM/DE_HUIDENT`) **TIRNAKSIZ + küçük harf** yazılır: `hu_ident : /scwm/de_huident;`. Tek-tırnaklı (`'/SCWM/DE_HUIDENT'`) yazım SAP'çe **SESSİZCE DÜŞÜRÜLÜR** — push "activated:true" der ama "Active source differs from uploaded content" WARNING'i çıkar ve alan tabloya EKLENMEZ.

**Why:** 2026-06-15 T_DORIT'e hu_ident eklerken gateway ilk denemede tek-tırnak kullandı → alan eklenmemiş göründü; deneme 2 tırnaksız ile çözüldü. "activated mesajına güvenme" tuzağının net örneği — syntax-check geçti ama alan-içerik diff'i push-öncesi yakalanamadı.

**How to apply:** (1) Table DDL'de namespaced DTEL = tırnaksız küçük harf. (2) Tablo ALTER/create sonrası "active differs" WARNING = yükleme yansımadı sinyali → MUTLAKA `adt_get` readback ile alanın gerçekten geldiğini doğrula (status-200/activated yetmez). Bkz. [[feedback_adt-get-namespace-encode-trap]] · [[feedback_reviewer-checklist-vs-wired-validator]] (T10: reviewer push-öncesi syntax geçti ama readback-diff gerekiyordu → yeni validator adayı).

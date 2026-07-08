---
name: spec-mutabakat-gate
description: "Her yeni program/geliştirme sprint'i SPEC-MUTABAKAT GATE ile başlar — ekran görüntüsü+fonksiyonel spec iste, sentezle, sign-off, SONRA build"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08868cc7-ead9-4d38-b6fe-2fd1fd3eb04c
---

Her yeni program/geliştirme (R2+ sprint, ZSD001 ve sonraki tüm
geliştirmeler) **backend/frontend'e başlamadan ÖNCE** şu gate'i geçer
(kullanıcı talimatı 2026-05-19; SPRINT_PLAN v5 §4-adım1):

1. **1a** — Kullanıcıdan **iste**: (i) ekran görüntüleri (`TD/Screens/
   <PROG>/`), (ii) kullanıcının yazdığı **fonksiyonel spec**. (Basit
   program olsa bile istek adımı ATLANMAZ; kullanıcı minimal verebilir.)
2. **1b** — AI **birleşik SPEC sentezler**: kullanıcı fonksiyonel spec +
   ekran görüntüleri + **<LEGACY_SOURCE> SEVKEMRI source kodu** (bende) +
   `programs/<PROG>.md` + classic `DDL_*`/`S_*` (alan/kolon). İçerik:
   alan listesi, davranış, iş kuralları, **açık-karar tablosu**
   (LIKP/std-write, slicing, K-soruları o programa özel).
3. **1c** — Spec kullanıcıyla madde madde → **MUTABAKAT (sign-off)**.
4. **1d** — Ancak mutabakattan SONRA backend→frontend (§4 adım 2+).

**Why:** Kullanıcı, geliştirmeye sağlam zeminle başlanmasını istiyor;
ORDER'da spec belirsizliği patinaja yol açmıştı. Açık kararlar
(ör. R3 BOOKING: LIKP ADR0005-yazımı, slicing, LE-TRA K5) bu gate'in
1c'sinde çözülür — önceden taahhüt edilmez.

**How to apply:** Yeni sprint açılınca İLK iş: kullanıcıdan ekran+spec
iste; sentezle; mutabakat al; sonra §4 adım2+ (value-help SOR →
RAP backend → freestyle UI → e2e → deploy → reviewer/commit →
classic emeklilik). Bağlı: [[feedback_ortak-value-help-sor]] ·
[[feedback_liste-ekrani-alv-standardi]] · [[feedback_audit-alan-autofill-standardi]] ·
[[feedback_freestyle-ui-preflight]] · [[project_sprint-plan-rap-revize]].

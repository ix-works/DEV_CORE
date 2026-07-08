---
name: ortak-value-help-sor
description: "Her geliştirmede value-help CDS'leri için ortak (ZSD000_I_*) mı paket-local mi — KULLANICIYA SOR; generic VH'yi tekrar yaratma, ortaktan kullan"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08868cc7-ead9-4d38-b6fe-2fd1fd3eb04c
---

Her yeni geliştirmede value-help (arama yardımı) CDS'leri belirlenirken:
her aday VH için **"ortak `ZSD000_CLC`/`ZSD000_I_*` mı, yoksa ilgili
pakette local mi"** önerini çıkar ve **kullanıcıya SOR** — yerleşimi
kullanıcı onaylar (kullanıcı talimatı 2026-05-19; ADR 0009).

**Kriter:** generic master/org tablosu (but000, tvkot, tvknt, t001,
kna1...) üzerinde, app-mantığı yok, ≥2 yerde plausible → **ortak
ZSD000_I_***. App'e özel filtre / o app'in Z tablosu → **paket-local**.

**Mevcut ortak VH (yeniden YARATMA — expose + assoc ile kullan):**
- `ZSD000_I_BPNAME` (but000 → BusinessPartner/BusinessPartnerName) —
  Firma/Müşteri/Partner/Hat.
- `ZSD000_I_VKORGVH` (tvkot → SalesOrganization/SalesOrgName) — Satış Org.

**Why:** Generic VH'yi her pakette kopyalamak duplikasyon + tutarsızlık +
bakım yükü. ORDER'da ZSD001 local yaratılmıştı, ZSD000'e taşındı.

**How to apply:** Tüketen RAP servisi → SRVD `expose ZSD000_I_<x>;` +
ZSD001_I_ORDER benzeri `association to ZSD000_I_<x>`. AI paket/TR
yaratmaz (ADR 0005); ortak/local kararını tek başına vermez. Standart:
standards/05 §9B; pattern/PRE-FLIGHT: playbook/ui-backend-rap.md §0(9)/§F;
ADR 0009; ZSD000_CLC/.rules.md ortak-VH tablosu. Bağlı:
[[feedback_liste-ekrani-alv-standardi]] · [[feedback_audit-alan-autofill-standardi]].

# ADR 0009 — Ortak (Foundation) Value-Help CDS Politikası

**Durum:** Kabul edildi (2026-05-19)
**Karar veren:** Kullanıcı (Özgür) — açık talimat
**Bağlam katmanı:** L2 (standart) + L4 (ZSD000 .rules.md) — T7/T5

---

## Bağlam

Value-help (arama yardımı) CDS view'ları çoğu zaman generic master/org
verisi üzerinedir (`but000`/partner, `tvkot`/satış org, `t001`/şirket
kodu...) ve birden çok geliştirmede aynen gerekir. ORDER pilotunda
bunlar paket-local (`ZSD001_I_BPNAME/VKORGVH`) yaratılmıştı →
ORDER/BOOKING vb.'de tekrar yaratmak duplikasyon, tutarsız
metin/davranış, bakım yükü.

## Karar

**Generic value-help CDS'leri ortak `ZSD000_CLC` paketinde `ZSD000_I_*`
view entity olarak TEK SEFER yaratılır**; tüketen RAP servisleri kendi
SRVD'sinde `expose` + CDS association ile kullanır (kopyalama YOK).

**Ortak mı / paket-local mı kriteri:**

| Ortak `ZSD000_I_*` | İlgili pakette local |
|---|---|
| Standart SAP master/org tablosu (but000, tvkot, tvknt, t001, kna1...) | App'in **Z tablosu** üzerinde VH |
| App-mantığı / özel filtre YOK | App'e özel filtre / iş kuralı var |
| ≥2 geliştirmede plausible | Tek programa özgü |

**Süreç (zorunlu, her geliştirmede):** Value-help'ler belirlenirken AI,
her aday VH için "ortak `ZSD000_I_*` mı / paket-local mi" önerisini
çıkarır ve **kullanıcıya sorar**; yerleşimi kullanıcı onaylar. AI tek
başına ortak/local kararı vermez, paket/TR yaratmaz (ADR 0005).

## Sonuçlar

- `ZSD000_CLC/.rules.md`: ortak-VH politikası + `ZSD000_I_*` naming +
  mevcut ortak VH tablosu.
- `standards/05-coding-rap.md` §9B: bağlayıcı kural.
- `playbook/ui-backend-rap.md` §0 PRE-FLIGHT: "VH envanteri → ortak/local
  → KULLANICIYA SOR" adımı.
- İlk uygulama: `ZSD000_I_BPNAME` (Firma/Hat) + `ZSD000_I_VKORGVH`
  (SatışOrg) yaratıldı; ORDER bunlara re-point edildi; eski
  `ZSD001_I_BPNAME/VKORGVH` silindi. `ZSD001_I_PORTVH` = app-özel,
  ZSD001'te kaldı (kullanıcı kararı).
- Yeni geliştirme: bu VH'ler zaten varsa yeniden yaratılmaz; SRVD
  `expose` + assoc ile kullanılır.

## İlgili

ADR 0005 (paket/TR yaratma yasağı) · ADR 0008 (liste ALV standardı) ·
`standards/05` §9B · `playbook/ui-backend-rap.md` §0/§F ·
`ERP/SD/ZSD000_CLC/.rules.md`

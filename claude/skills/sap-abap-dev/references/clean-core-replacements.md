# Clean-Core Obje Farkındalığı (<PROJECT_NAME> bağlam notu)

**Bağlam — önce oku:** <PROJECT_NAME> hedef sistemi **on-prem** (<SYSTEM_ID>) ve proje
klasik Z tablolar + RAP karması kullanıyor (bkz. ZSD001 paradigması). Yani **katı ABAP
Cloud clean-core zorunlu değil**. Bu tablo, standart SAP objesine dokunma yasağıyla
(ADR 0005 §A/B) birlikte **farkındalık** içindir: yeni okuma modeli kurarken modern
released CDS/API tercih edilmeli, deprecated/forbidden objeye yaslanılmamalı.

Kaynak: NTT marketplace `clean-core` skill'i (eşleme tablosu + seviyeler), bizim
on-prem bağlamımıza not düşülerek alındı.

## Yaygın yasak/deprecated standart obje → önerilen alternatif

| Standart obje | Tip | Yerine (released) |
|---|---|---|
| MARA | Tablo | `I_PRODUCT` |
| BSEG | Tablo | Doğrudan eşdeğer yok — released API/CDS kullan |
| VBAK / VBAP | Tablo | Released satış belgesi CDS (okuma); yazım için BAPI |
| LIKP / LIPS | Tablo | Okuma için released delivery CDS; **yazım `BAPI_OUTB_DELIVERY_CREATE`** (ADR 0005 §B) |
| T001 | Tablo | Released org CDS |
| CL_GUI_ALV_GRID | Class | `CL_SALV_TABLE` (klasik) / freestyle UI5 ALV (RAP) |
| CL_GUI_ALV_TREE | Class | `CL_SALV_TREE` |

> Not: Bu proje VBAK/VBAP/LIKP gibi tabloları **okuma** amaçlı CDS join'lerinde
> kullanır (ZSD001 zinciri). Bu yasak değildir (read). Yasak olan: standart tabloya
> **direkt yazım** ve standart objeyi **değiştirmek**.

## Clean-core seviyeleri (referans)

- **Level A** — Önerilen (stabil, iyi test edilmiş).
- **Level B** — İzinli (standart SAP teslimatı).
- **Level C** — Şartlı izinli (kısıt kontrol et).
- **Level D** — Deprecated/yasak (alternatif kullan).

## Bizim projede nasıl uygulanır

- Yeni RAP okuma modeli (interface CDS) kurarken: mümkünse released `I_*` view'ları
  ve association'ları tercih et; deprecated tabloya doğrudan yaslanma.
- Standart objeye dokunma ihtiyacı çıkarsa → ADR 0005 §A: DUR → kullanıcıya sun.
- Ortak value-help için yeni generic CDS yaratmadan önce mevcut `ZSD000_I_*`
  (BPNAME/VKORGVH) reuse — ADR 0009.

---
applies_to: [s4_private]
layer: L3
type: reference
module: SD
status: active
purpose: SD SPRO / customizing referansı (doküman tipleri, kopya kontrol, teslimat, çıktı)
---

# SD — SPRO / Customizing (referans)

> Customizing okuma/farkındalık. Z geliştirme bu config'e dayanır; değiştirme = danışman/operatör.

## Satış
| IMG / TX | Konu |
|---|---|
| VOV8 | Satış doküman tipleri (order types) |
| VOV7 | Kalem kategorileri (item categories) |
| VOV6 | Schedule line kategorileri |
| VOV4 | Kalem kategori belirleme |
| V/08, V/06 | Fiyatlandırma prosedürü / koşul tipleri |

## Kopya kontrol (copy control)
| TX | Akış |
|---|---|
| VTAA | SO → SO |
| VTLA | SO → Delivery |
| VTFL | Delivery → Billing |
| VTFA | SO → Billing |

## Teslimat / Shipping
| IMG / TX | Konu |
|---|---|
| 0VLK | Teslimat tipleri |
| 0VLP | Teslimat kalem kategorileri |
| Shipping point determination | Sevkiyat noktası belirleme |
| Route determination | Rota belirleme |
| LE-TRA (VT) | Taşıma/shipment config |

## Çıktı / Statutory
| Konu | Not |
|---|---|
| NACE | Output determination |
| SAP Document Compliance | Yerel yasal belgeler (ör. Türkiye e-İrsaliye / e-Fatura) |

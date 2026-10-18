---
applies_to: [s4_private]
layer: L3
type: reference
module: SD
status: active
purpose: SD transaction kodları referansı
---

# SD — Transaction Kodları (referans)

| TX | İş |
|---|---|
| VA01 / VA02 / VA03 | Satış siparişi yarat / değiştir / görüntüle |
| VA05 | Satış siparişi listesi |
| VL01N / VL02N / VL03N | Outbound delivery yarat / değiştir / görüntüle |
| VL10A / VL10B / VL10G | Teslimat due list (toplu) |
| VL06O | Outbound delivery monitor |
| LT03 / LT12 | Transfer order (WM picking) |
| VF01 / VF02 / VF03 | Fatura yarat / değiştir / görüntüle |
| VF04 | Billing due list |
| VT01N / VT02N / VT03N | Shipment yarat / değiştir / görüntüle (LE-TRA) |
| VKM3 / VKM1 | Kredi blokaj listesi |
| VOV8 / VOV7 | Doküman/kalem config |
| SE16N | Tablo görüntüleme (veri kontrol — ADR 0011 hassas) |

> ⚠️ TX kodu yaratma (SE93) **operatör** işidir (ADR 0005-C / iş bölümü): paketin Z TX'lerini
> operatör SE93'te açar.

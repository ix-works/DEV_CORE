---
applies_to: [s4_private]
layer: L3
type: reference
module: SD
status: active
purpose: SD iş akışları referansı (order-to-cash, teslimat/sevkiyat akışı, akış kuralları)
---

# SD — İş Akışları (referans)

## Order-to-Cash (genel)
```
Satış Siparişi (VA01)  →  Teslimat (VL01N)  →  Picking/WM (LT03)
   →  Mal Çıkışı PGI (VL02N)  →  Fatura (VF01)  →  Muhasebe (FI)
```
Doküman akışı: VBFA tablosu (her adım önceki referansını taşır).

## Teslimat / sevkiyat süreci
```
Delivery (LIKP/LIPS)  →  Konteyner/HU (VEKP/VEPO)
   →  Shipment (VTTK/VTTP, LE-TRA)  →  Çıktı (ör. e-İrsaliye — SAP Document Compliance)
```

## Önemli akış kuralları
- SO→DLV→Billing copy control (VTLA/VTFL) tutarlı olmalı.
- PGI (post goods issue) stok + FI hareketi yaratır → geri alma VL09.
- Z katmandan teslimat yazımı ADR 0005-B: LIKP/LIPS'e **released API / BAPI**
  (BAPI_OUTB_DELIVERY_*), direkt SQL YASAK — yol seçimi [`standards/10`](../../../../standards/10-standart-veriye-yazma-api-secimi.md).

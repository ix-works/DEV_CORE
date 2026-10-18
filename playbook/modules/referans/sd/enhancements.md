---
applies_to: [s4_private]
layer: L3
type: reference
module: SD
status: active
purpose: SD enhancement noktaları referansı (user-exit, BAdI, çıktı, VOFM, BTE)
---

# SD — Enhancement Noktaları (referans)

> ADR 0005-A: standart exit/BAdI **implementasyonu** kullanıcı kararı + Z implementasyon
> sınıfı (Z namespace). Standart kodu değiştirme YASAK. Mevcut Z exit/BAdI varsa reuse (ADR 0009).

## Klasik user-exit (SMOD/CMOD — include'lar)
| Include | Alan |
|---|---|
| MV45AFZZ / MV45AFZB / MV45AFZA | Satış siparişi (VA01/02) |
| RV60AFZZ / RV60AFZC | Faturalama (VF01) |
| MV50AFZ1 (RV_DELIVERY_*) | Teslimat (VL01N) — userexit_save_document vb. |
| RV_PRICE_* (USEREXIT_PRICING_*) | Fiyatlandırma |

## BAdI (SE18/SE19)
| BAdI | Alan |
|---|---|
| BADI_SD_SALES_BASIC, BADI_SD_SALES | Satış |
| LE_SHP_DELIVERY_PROC | Teslimat süreci |
| BADI_SD_BILLING / SD_CIN_LV60AU02 | Faturalama |

## Çıktı (Output / NAST)
- NACE (output condition), NAST tablosu, processing program + FORM routine
- S/4: Output Management (BRF+) · SAP Document Compliance (ör. e-İrsaliye / e-Fatura)

## VOFM
- Copy requirements / data transfer routines (VTLA/VTFL copy control), pricing requirement formülleri

## BTE (Business Transaction Events)
- FIBF — açık FI/SD olay noktaları

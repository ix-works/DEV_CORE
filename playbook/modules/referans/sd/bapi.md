---
applies_to: [s4_private]
layer: L3
type: reference
module: SD
status: active
purpose: SD BAPI / RFC FM referansı (standart belge yazma yolları)
---

# SD — BAPI / RFC FM (referans)

> ADR 0005-B: standart dokümana (VBAK/LIKP...) direkt `INSERT/UPDATE/MODIFY` YASAK. Yazma yolu
> sırası ve karar ağacı **tek yerde** yaşar: [`standards/10`](../../../../standards/10-standart-veriye-yazma-api-secimi.md)
> (released API → BAPI → RFC FM → BDC → manuel). Aşağıdaki adların released olup olmadığını
> o sistemde teyit et (Clean Core).

## Satış siparişi
| BAPI | İş |
|---|---|
| BAPI_SALESORDER_CREATEFROMDAT2 | SO yarat |
| BAPI_SALESORDER_CHANGE | SO değiştir |
| BAPI_SALESORDER_SIMULATE | SO simülasyon (fiyat/ATP) |
| BAPI_TRANSACTION_COMMIT / _ROLLBACK | LUW kapanışı |

## Teklif + varyant konfigürasyonu (klasik LO-VC)
| BAPI | İş |
|---|---|
| BAPI_QUOTATION_CREATEFROMDATA2 | Teklif yarat (FG SAPL2031) |
| BAPI_CUSTOMERQUOTATION_CHANGE | Teklif değiştir; CFGS_* ile konfigürasyon değeri — motoru koşturur. ⚠ POSEX boş/eşleşmez = SESSİZ ATLAMA, tam kullanıcı kümesi, türetilmişi gönderme: [`../../../howto-lovc-belge-konfigurasyonu-okuma-yazma.md`](../../../howto-lovc-belge-konfigurasyonu-okuma-yazma.md) §4 |

## Teslimat
| BAPI / FM | İş |
|---|---|
| BAPI_OUTB_DELIVERY_CREATE_SLS | Satıştan outbound delivery |
| BAPI_OUTB_DELIVERY_CREATE_STO | STO'dan delivery |
| BAPI_OUTB_DELIVERY_CHANGE | Delivery değiştir (PGI, picking, yük) |
| BAPI_OUTB_DELIVERY_CONFIRM_DEC | — |
| GN_DELIVERY_CREATE | Klasik delivery create (eski; ECC dönemi kodlarında görülür) |
| WS_DELIVERY_UPDATE | Klasik delivery güncelleme |

## Faturalama
| BAPI | İş |
|---|---|
| BAPI_BILLINGDOC_CREATEMULTIPLE | Fatura yarat |

## Shipment (LE-TRA)
| FM | İş |
|---|---|
| BAPI_SHIPMENT_CREATE / _CHANGE | Shipment |

## RAP / released (S/4 modern — tercih)
- `I_SalesOrderTP` (RAP BO), `API_SALES_ORDER_SRV` (OData)
- `I_OutboundDelivery*` released CDS — okuma/expose
- Released kontrolü: ADT released API listesi · `scripts/validators/check_released_objects.py`

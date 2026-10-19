---
applies_to: [s4_private]
layer: L3
type: reference
module: SD
status: active
purpose: SD kilit tabloları (standart SAP referansı — okuma/farkındalık)
---

# SD — Kilit Tablolar (referans)

> Standart SAP SD tabloları (okuma/farkındalık). ADR 0005-A: bu standart objelere
> **dokunulmaz**, sadece CDS/okuma kaynağı + alan adı referansı. Yeni sistemde alan
> varlığını teyit et (alan adları sürüm/sistem bağımlıdır — bu liste hipotezdir).

## Satış (Sales)
| Tablo | İçerik |
|---|---|
| VBAK / VBAP | Satış siparişi başlık / kalem |
| VBEP | Kalem sevkiyat çizgileri (schedule lines) |
| VBKD | Satış — iş verileri (business data) |
| VBPA | Doküman ortakları (partner functions) |
| VBFA | Doküman akışı (document flow) |
| VBUK / VBUP | Durum başlık/kalem (S/4'te VBAK/VBAP'a gömülü — teyit et) |
| KONV / PRCD_ELEMENTS | Fiyatlandırma koşulları (S/4 = PRCD_ELEMENTS) |
| IBINOWN → IBIN → IBINVALUES → IBSYMBOL | Kalem varyant konfigürasyonu değerleri (`VBAP-CUOBJ`'dan; INOB DEĞİL; ATINN IBSYMBOL'de) — zincir: [`../../../howto-lovc-belge-konfigurasyonu-okuma-yazma.md`](../../../howto-lovc-belge-konfigurasyonu-okuma-yazma.md) §1.2 |

## Teslimat (Delivery)
| Tablo | İçerik |
|---|---|
| LIKP / LIPS | Teslimat başlık / kalem |
| VBFA | SO→DLV→Billing akışı |
| VEKP / VEPO | Handling unit başlık / kalem |

## Sevkiyat / Taşıma (Shipment)
| Tablo | İçerik |
|---|---|
| VTTK / VTTP | Shipment başlık / kalem (LE-TRA) |
| VTSP / VTPA | Shipment stage / partner |

## Faturalama (Billing)
| Tablo | İçerik |
|---|---|
| VBRK / VBRP | Fatura başlık / kalem |

## Master / Config
| Tablo | İçerik |
|---|---|
| KNA1 / KNVV | Müşteri genel / satış alanı (⚠️ PII — ADR 0011; okumada released CDS tercih: I_Customer / I_CustomerSalesArea) |
| MARA / MARC / MVKE | Malzeme genel / tesis / satış |
| TVAK / TVAP | Satış doküman tipi / kalem kategorisi config |
| TVLK | Teslimat tipi config |

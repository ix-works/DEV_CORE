---
name: api-teslimat-yolu-vorlage-kopieren-e-ugramaz
description: "OData API_OUTBOUND_DELIVERY_SRV deep-create teslimatı RV_DELIVERY_CREATE/SAPLV50S deliver_single_order_item ile yaratır, SAPFV50C VORLAGE_KOPIEREN'e UĞRAMAZ — VL01N'de çalışan enhancement API'de çalışmaz; ABLAD bölünmesi VBPA-WE-ABLAD'dan"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 7f452bba-a284-47b5-ac9b-109ef3d051c2
  modified: 2026-09-30T11:22:23.605Z
---

Teslimat yaratma akışına müdahale (enhancement) VL01N'de doğrulandı diye API yolunda çalışmaz.
`A_OutbDeliveryHeader` deep-create zinciri: `CL_API_OUTBOUND_DEL_02_DPC_EXT` → `CL_OD_CREATE_FROM_SD_DOC` → `RV_DELIVERY_CREATE`
→ `LV50SF0S FORM deliver_single_order_item` (toplu yol). `SAPFV50C VORLAGE_KOPIEREN` (VL01N yolu) atlanır. İki yolun ikiz
noktaları: `VORLAGE_KOPIEREN_01` ↔ `ES_SAPLV50S DELIVER_SINGLE_ORDER_ITEM_02` (ikisi de `get_ship_to_data`'dan hemen önce).
Teslimat bölünmesi farklı boşaltma noktasından geliyorsa karar LIKP-ABLAD'da DEĞİL, `SHP_COMPARE_DELIVERY_PARTNERS`'ta
VBPA-WE-ABLAD farkıyla verilir (koşulsuz; `LE_SHP_SUPPRESS_DEL_SPLIT` yalnız TRAGR). LIKP-ABLAD'ı CLEAR etmek etkisiz
(ergänzen'de XVBPA'dan yeniden dolar); çare bellekteki `CVBPA` WE ABLAD'ını her iki noktada boşaltmak.

**Why:** Bir projede, 2026-09-30 (müşteri vakası): önce `DATEN_KOPIEREN_001_20`'de LIKP CLEAR, sonra VORLAGE_KOPIEREN_01 denendi —
VL01N'de çalıştı, uygulama ekranı (API) yine 2 teslimat üretti; 3. tur SAPLV50S noktasıyla tek teslimat.
**How to apply:** Teslimat yaratan her müdahalede ÖNCE hangi yolun (dialog/API/BAPI/VL10) koştuğunu belirle, kontrol grubu olarak
iki yolu ayrı ölç. API çağrısı başka kullanıcıyla (HTTP) koşabilir — debug için o kullanıcıya external breakpoint.
Son-doğrulama: 2026-09-30 · Applies-to: s4_private 2025, SD teslimat yaratma. prior-art: yok (memory/SESSION_NOTES araması bu turda).

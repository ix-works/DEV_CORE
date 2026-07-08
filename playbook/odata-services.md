---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# OData Services — Pricing Simulation, Function Import, UpdateSO, BAPIRET2

## 27. API_SALES_ORDER_SIMULATION_SRV — Fiyat Simülasyonu

### Servis Bilgisi

- **Servis Adı:** `API_SALES_ORDER_SIMULATION_SRV`
- **Her iki sistemde de aktif:**
  - ERP: `https://<SYSTEM_ID>.SAP.EXAMPLE.COM.TR:44300/sap/opu/odata/sap/API_SALES_ORDER_SIMULATION_SRV`
  - S4:  `https://<S4_HOST>.sap.example.com.tr:44300/sap/opu/odata/sap/API_SALES_ORDER_SIMULATION_SRV`
- **Endpoint:** `POST /A_SalesOrderSimulation`
- **GET desteklenmez** — sadece POST

### Doğrulanmış Test Değerleri (ERP)

| Alan | Değer |
|------|-------|
| SalesOrderType | `ZC01` |
| SalesOrganization | `1500` |
| DistributionChannel | `30` |
| OrganizationDivision | `10` |
| SoldToParty | `0000300000` |
| Material | `S1917` |
| RequestedQuantityUnit | `ADT` |
| Plant | `TDF0` |

### Custom Fields

- `ZZ1_DISCOUNT_CODE_SDH` — S4 metadata'sında **mevcut**, payload'a gönderilebilir
- `ZZ1_PRICE_CODE_SDH` — S4 metadata'sında **YOK**, gönderilirse HTTP 400 (`Property is invalid`). Payload'a ekleme.

### ABAP Çağrısı — ÇALIŞAN YÖNTEM (create_by_url + authenticate)

**✅ Doğrulanmış ve çalışan yöntem (15 Nisan 2026):**

```abap
DATA lo_client TYPE REF TO if_http_client.
DATA lv_csrf   TYPE string.
DATA lv_url    TYPE string.

lv_url = 'https://<S4_HOST>.sap.example.com.tr:44300'
      && '/sap/opu/odata/sap/API_SALES_ORDER_SIMULATION_SRV/A_SalesOrderSimulation'.

cl_http_client=>create_by_url(
  EXPORTING  url    = lv_url
  IMPORTING  client = lo_client
  EXCEPTIONS OTHERS = 4
).

lo_client->propertytype_accept_cookie = if_http_client=>co_enabled.
lo_client->authenticate( username = '<SAP_USER>' password = '...' ).

" CSRF fetch
lo_client->request->set_method( 'GET' ).
lo_client->request->set_header_field( name = 'X-CSRF-Token' value = 'Fetch' ).
lo_client->request->set_header_field( name = 'Accept'       value = 'application/json' ).
lo_client->send( ).
lo_client->receive( ).

lv_csrf = lo_client->response->get_header_field( 'X-CSRF-Token' ).

" POST (NO refresh_request — continue on same request object)
lo_client->request->set_method( 'POST' ).
lo_client->request->set_header_field( name = 'X-CSRF-Token' value = lv_csrf ).
lo_client->request->set_header_field( name = 'Content-Type' value = 'application/json' ).
lo_client->request->set_header_field( name = 'Accept'       value = 'application/json' ).
lo_client->request->set_cdata( lv_payload_json ).
lo_client->send( ).
lo_client->receive( ).
```

**Kritik Noktalar:**
- `create_by_url` + `authenticate()` → SAP'nin built-in challenge-response auth mekanizması session'ı koruyor
- `propertytype_accept_cookie = co_enabled` → cookie jar aktif, session tutulur
- `refresh_request` KULLANMA — SSL session'ı sıfırlar, 403 döner
- `SalesOrder: ""` payload'a ekle (boş string zorunlu) — olmadan HTTP 400
- `sap-client: 100` header'ı GET ve POST isteklerine ekle
- SM59 destination GEREKMEZ — direkt URL ile çalışır

### SM59 Destination Bilgisi

| Alan | Değer |
|------|-------|
| Destination Adı | `FIORI_FLP_HTTPS` |
| Host | `<S4_HOST>.sap.example.com.tr` |
| Port | `44300` |
| Connection Type | G (HTTP to External Server) |
| SSL | Aktif |
| Kullanıcı | Tanımlı değil (SSO) |
| Connection Test | OK |

### ZSD_ORDER_SRV SimulatePricing — OData Parametre İsimleri

Function Import parametreleri `Iv` prefix'li — büyük/küçük harf önemli:

| Parametre | Tip | Zorunlu |
|-----------|-----|---------|
| `IvSalesOrderType` | Edm.String(4) | Evet |
| `IvSoldToParty` | Edm.String(10) | Evet |
| `IvPurchaseOrder` | Edm.String(35) | **Evet** (boş string gönder, atlama) |
| `IvPriceCode` | Edm.String(10) | Evet (boş olabilir) |
| `IvDiscountCode` | Edm.String(10) | Evet (boş olabilir) |
| `IvItemsJson` | Edm.String | Evet |

⚠ `IvPurchaseOrder` atlanırsa `Invalid Function Import Parameter` hatası gelir.

### Bilinen Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `HTTP 401` (ABAP'tan S4'e) | SM59 destination'da yanlış credentials | `FIORI_FLP_HTTPS` kullan — kullanıcısız, SSO ile çalışır |
| `HTTP 403 CSRF token validation failed` | `refresh_request` SSL session'ı sıfırlıyor | `refresh_request` KULLANMA — `authenticate()` + `propertytype_accept_cookie` ile devam et |
| `SHTTP 852 cannot be processed in plugin mode HTTPS` | `create_by_destination` ile SM59 HTTPS destination, ICM HTTPS context'inden çağrı | `FIORI_FLP_HTTPS` ile bu hata oluşmadı — oluşursa `create_by_url` dene |
| `Message E 00 001 cannot be processed in plugin mode HTTPS` | `create_by_url` ile ERP kendi URL'ine loopback HTTPS yapamaz | S4 URL'i kullan: `<S4_HOST>.sap.example.com.tr:44300` |
| `Invalid Function Import Parameter 'IvPurchaseOrder'` | Parametre atlandı | Tüm parametreleri gönder, boş string kullan |
| `Satış belgesi türü ZOR tanımlanmadı` | Yanlış AUART | `ZC01` kullan |
| `Satış ölçü birimi KG tanımlanmadı` | S1917 için KG yok | `ADT` kullan |
| `Unit ADT/ST is not created in language EN` | ABAP HTTP çağrısında `sap-language` header eksik | GET ve POST her ikisine de `sap-language: TR` ekle — `simulate_pricing` düzeltildi (07.05.2026) |
| `Satış ölçü birimi ST kalem için tanımlanmadı` | Frontend `ADT→ST` dönüşümü simülasyona uygulandı | Simülasyona orijinal birimi (`ADT`) gönder — dönüşüm sadece `CreateSalesOrder`'da gerekli |
| `NetAmount: 0.00` (başarılı ama 0) | Müşteri/materyal kombinasyonu için S4'te fiyat koşulu tanımlı değil | SD konfigürasyon sorunu, kod doğru çalışıyor |

### Payload JSON Formatı — ÇALIŞAN (results wrapper + to_Pricing zorunlu)

```json
{
  "SalesOrder": "",
  "SalesOrderType": "ZC01",
  "SalesOrganization": "1500",
  "DistributionChannel": "30",
  "OrganizationDivision": "10",
  "SoldToParty": "0000300000",
  "PurchaseOrderByCustomer": "",
  "TransactionCurrency": "TRY",
  "ZZ1_DISCOUNT_CODE_SDH": "",
  "to_Pricing": {
    "TotalNetAmount": null
  },
  "to_Item": {
    "results": [
      {
        "SalesOrderItem": "000010",
        "Material": "S1917",
        "RequestedQuantity": "10.000",
        "RequestedQuantityUnit": "ADT",
        "Plant": "TDF0"
      }
    ]
  }
}
```

**Kritik payload kuralları:**
- `SalesOrder: ""` zorunlu — olmadan HTTP 400
- `to_Pricing: {"TotalNetAmount": null}` zorunlu — olmadan `TotalNetAmount` alınamaz (deferred gelir)
- `ZZ1_PRICE_CODE_SDH` **GÖNDERİLMEZ** — S4 metadata'sında yok, HTTP 400 verir
- `ZZ1_DISCOUNT_CODE_SDH` gönderilebilir

### Response Yapısı

```json
{
  "d": {
    "TransactionCurrency": "TRY",
    "to_Pricing": {
      "TotalNetAmount": "12300.00",
      "TransactionCurrency": "TRY"
    },
    "to_Item": {
      "results": [
        {
          "SalesOrderItem": "10",
          "Material": "S1917",
          "NetAmount": "12300.00",
          "TaxAmount": "2460.00",
          "TransactionCurrency": "TRY"
        }
      ]
    }
  }
}
```

**Doğrulanmış test:** S1917 × 10 ADT, müşteri 0000300000 → TotalNetAmount: **12300.00**, GrossAmount: **14760.00** TRY (15.04.2026)

---

---

## 28. Gateway Function Import — 405 Sorunu ve Çözümü

**Sorun:** Collection döndüren ve bir EntitySet'e bağlı Function Import'a POST yapılınca Gateway 405 döndürür. ABAP'a hiç ulaşmaz.

**Örnek:** `callFunction("/SimulatePricing", {method:"POST"})` → 405

**Kök Neden:** Gateway runtime dispatcher (`/IWCOR/CL_DS_PROC_DISPATCHER`), bu tür Function Import POST isteklerini `execute_action`'a değil, ilgili EntitySet'in `_get_entityset` metoduna yönlendirir.

**ÇALIŞMAYAN çözüm denemeleri:**
- `/IWFND/MAINT_SERVICE`'te servisi silip yeniden ekleme
- `/IWBEP/R_MGW_CLEANUP_MD_CACHE` ile cache temizleme
- SEGW'de HTTP method değiştirme

**✅ GERÇEK ÇÖZÜM:**
```javascript
// YANLIŞ:
oModel.callFunction("/SimulatePricing", {method:"POST", urlParameters:{...}});

// DOĞRU:
oModel.read("/SimulationItemResultSet", {
    urlParameters: { IvSalesOrderType: "ZC01", IvSoldToParty: "...", IvItemsJson: "..." }
});
```
Backend'de `simulationitemre_get_entityset` override edilir. Parametreler `server_request->get_header_field('~request_uri')` ile URL'den regex parse edilir. `IvItemsJson` URL-encoded gelir → `cl_http_utility=>unescape_url()` ile decode et.

---

---

## 29. UpdateSalesOrder — Yeni Kalem Ekleme Sorunları

### 16.1 Sorun Özeti

`UpdateSalesOrder` Function Import'ta yeni kalem eklenince **504 / connection drop** alınıyordu.

### 16.2 Kök Nedenler ve Çözümler

| Sorun | Sebep | Çözüm |
|-------|-------|-------|
| Connection drop (0.9s) | EML `MODIFY ENTITIES ... CREATE BY \_item` sonrası gateway `COMMIT WORK` yapıyor, daha önce çağrılan `COMMIT ENTITIES` ile çakışıyor → `CX_ABAP_BEHV_COMMIT_FAILED` dump | `update_sales_order` metodundan `COMMIT ENTITIES` tamamen kaldırıldı — Gateway kendi COMMIT'ini yapıyor |
| Ayrı `MODIFY ENTITIES` bloğu sorunu | İlk blokta UPDATE, ikinci blokta `CREATE BY \_item` — SAP RAP aynı LUW'da birden fazla EML statement birikiyor, COMMIT'te `CX_ABAP_BEHV_COMMIT_FAILED` | Tek `MODIFY ENTITIES` bloğunda hem UPDATE hem `CREATE BY \_item` — `IF lt_new_items IS NOT INITIAL ... ELSE` yapısıyla |
| `DATA` tanımı çakışması | `IF/ELSE` bloğu içinde `DATA(ls_mapped)` iki kez tanımlandı → `already declared` | Tüm `DATA` tanımları metodun başına taşındı, EML'de `MAPPED ls_mapped` (DATA() olmadan) |
| `plant = '1000'` yanlış | Sipariş 1000000000'in kalemlerinde `Werks = TDF0` — `'1000'` validation hatası | `plant = 'TDF0'` |
| Unit `ADT` → `ST` | `VRKME=ADT` olan malzeme için EML `requestedquantityunit='ADT'` validation hatası | Frontend'de `mUnitMap = { "ADT": "ST", "KAR": "ST" }` ile dönüşüm |
| JSON key uzunluğu / URL limiti | `IvChangedItemsJson=[{"SalesOrderItem":"000010","Quantity":17}]` uzun URL → ICM connection drop | JSON key'ler kısaltıldı: `I`=item, `Q`=quantity, `M`=material, `U`=unit. Backend `pretty_mode-low_case` ile parse ediyor |

### 16.3 Kesin Kurallar (Gateway OData V2 + EML)

1. **`COMMIT ENTITIES` yapma** — Gateway Function Import context'inde EML değişiklikleri Gateway'in kendi `COMMIT WORK`'üyle kaydedilir. `COMMIT ENTITIES` çakışmaya yol açar → `CX_ABAP_BEHV_COMMIT_FAILED` dump.
2. **Tek `MODIFY ENTITIES` bloğu** — aynı metod içinde birden fazla `MODIFY ENTITIES` çağrısı yapma. Hem UPDATE hem CREATE BY \_item tek blokta olmalı.
3. **Tüm `DATA` tanımları metodun başında** — `IF/ELSE/LOOP` içinde `DATA(...)` inline kullanımı "already declared" verir.
4. **`FOR ... INDEX INTO DATA(...)` kullanma** — EML `WITH VALUE #(...)` içinde `INDEX INTO DATA(lv_idx)` desteklenmiyor. `sy-tabix` de güvenilmez. Çözüm: önce `LOOP AT ... INTO ... ASSIGNING ...` ile tabloyu doldur, sonra EML'e ver.
5. **`%cid` unique olmalı** — `CREATE BY \_item` içinde aynı `%cid` iki kez kullanılırsa `CX_RAP_AMBIGUOUS_CID` runtime dump alınır. Çözüm: loop sayacı ile `|ITM{ lv_ctr }|` şeklinde üret (`ITM10`, `ITM20`, ...).
6. **Plant değeri `TDF0`** — Bu projede yeni kalem eklerken `plant = 'TDF0'`, `storagelocation` boş.
7. **Ölçü birimi dönüşümü frontend'de** — `ADT → ST`, `KAR → ST` (`mUnitMap` ile).

### 16.3.1 `%cid` Unique Üretim Kalıbı

```abap
DATA lv_ctr TYPE i VALUE 0.
DATA ls_item LIKE LINE OF lt_new_items.
LOOP AT lt_new_items INTO ls_item.
  lv_ctr += 10.
  ls_item-cid = |ITM{ lv_ctr }|.
  MODIFY lt_new_items FROM ls_item.
ENDLOOP.

MODIFY ENTITIES OF i_salesordertp
  ENTITY salesorder CREATE BY \_item
    WITH VALUE #( ( salesorder = iv_sales_order
      %target = VALUE #( FOR ls_ni IN lt_new_items
        ( %cid               = ls_ni-cid
          product            = ls_ni-material
          requestedquantity  = ls_ni-quantity
          requestedquantityunit = ls_ni-unit
          plant              = 'TDF0'
          storagelocation    = '' ) ) ) )
  MAPPED ls_mapped FAILED ls_failed REPORTED ls_reported.
```

### 16.4 Çalışan `update_sales_order` Yapısı (Özet)

```abap
METHOD update_sales_order.
  " Tüm DATA tanımları burada — metodun başında
  DATA ls_mapped   TYPE RESPONSE FOR MAPPED EARLY i_salesordertp.
  DATA ls_failed   TYPE RESPONSE FOR FAILED EARLY i_salesordertp.
  DATA ls_reported TYPE RESPONSE FOR REPORTED EARLY i_salesordertp.
  ...

  " JSON parse (short keys: I/Q/M/U, low_case)
  " Validasyon, bakiye kontrolü

  IF lt_new_items IS NOT INITIAL.
    MODIFY ENTITIES OF i_salesordertp
      ENTITY salesorder UPDATE ...
      ENTITY salesorderpartner UPDATE ...
      ENTITY salesorderitem UPDATE ...
      ENTITY salesorder CREATE BY \_item
        WITH VALUE #( ( salesorder = iv_sales_order
          %target = VALUE #( FOR ls_ni IN lt_new_items
            ( %cid = ls_ni-material Product = ls_ni-material ... plant = 'TDF0' ) ) ) )
      MAPPED ls_mapped FAILED ls_failed REPORTED ls_reported.
  ELSE.
    MODIFY ENTITIES OF i_salesordertp
      ENTITY salesorder UPDATE ...
      ...
      MAPPED ls_mapped FAILED ls_failed REPORTED ls_reported.
  ENDIF.

  " Hata kontrolü
  " COMMIT ENTITIES YOK — Gateway halleder
  ev_success = abap_true.
  ...
ENDMETHOD.
```

### 16.5 Frontend JSON Format (ChangeOrder.controller.js)

```javascript
var mUnitMap = { "ADT": "ST", "KAR": "ST" };

var aChangedItems = aItems.filter(...isNew=false...).map(function(o) {
    return { I: o.itemNumber, Q: parseFloat(o.quantity) || 0 };
});

var aNewItems = aItems.filter(...isNew=true...).map(function(o) {
    var sUnit = o.unit || "ST";
    return { M: o.material, Q: parseFloat(o.quantity) || 0, U: mUnitMap[sUnit] || sUnit };
});
```

---

*Bu dosya her başarılı ADT işleminden sonra güncellenir.*
### 17. API_SALES_ORDER_SIMULATION_SRV — PricingDate Format

- `PricingDate` alanının tipi `Edm.DateTime` (Precision=0, display-format=Date)
- `"YYYY-MM-DD"` string formatı **YANLIŞ** → HTTP 400 `Conversion error for property 'PricingDate'`
- **DOĞRU format:** `/Date(ms)/` — ms = (tarih - 19700101) × 86400000

ABAP'ta dönüşüm:
```abap
DATA lv_days_since_1970 TYPE i.
DATA lv_epoch_date     TYPE d VALUE '19700101'.
DATA lv_ms_i8          TYPE decfloat34.
lv_days_since_1970 = lv_prsdt_sim - lv_epoch_date.
lv_ms_i8 = lv_days_since_1970 * 86400000.
lv_prsdt_str = '/Date(' && lv_ms_i8 && ')/'.
REPLACE ALL OCCURRENCES OF '.' IN lv_prsdt_str WITH ''.
```

---

*Son Güncelleme: 16 Nisan 2026 — PricingDate Edm.DateTime format düzeltmesi eklendi.*

---

## 30. HTTP İsteklerinde Mesaj Yönetimi ve BAPIRET2

### Kural: Hata Mesajları İçin Her Zaman BAPIRET2 / BAPIRET2_T Kullan

Custom `ZSD000_S_MESSAGE` veya `ZSD000_TT_MESSAGES` gibi yapılar KULLANMA. SAP standardı olan `BAPIRET2` ve `BAPIRET2_T` kullan.

```abap
" DOGRU
DATA lt_msgs TYPE bapiret2_t.
DATA ls_err  TYPE bapiret2.
ls_err-type    = 'E'.
ls_err-id      = 'ZSD000'.
ls_err-message = 'Hata mesaji'.
APPEND ls_err TO lt_msgs.

" YANLIS — custom tip kullanma
DATA ls_err TYPE zsd000_s_message.
ls_err-severity = 'E'.
ls_err-code     = 'ERR'.
```

### Kural: HTTP POST/PATCH Sonrası sap-message Header'ını Oku

SAP OData API ek uyarı/info mesajlarını response body'de değil `sap-message` response header'ında döndürür. Bu header parse edilmezse bazı önemli mesajlar kaybolur.

```abap
" POST/PATCH sonrasi:
mv_last_sap_msg = mo_client->response->get_header_field( 'sap-message' ).

" fill_error icinde parse et:
METHOD parse_sap_message_header.
  " "severity", "message", "code", "target" alanlarini JSON'dan regex ile parse et
  " BAPIRET2_T'ye ekle
ENDMETHOD.
```

### Kural: OData Filter Sorgularında `and` Yerine Ayrı Çağrı Yap (Gerekirse)

`$filter=... and ...` içeren GET URL'leri `call_http_get` ile `create_by_url` üzerinden gönderilince `&` karakteri URL encoding sorununa yol açabilir. Sorun yaşanırsa filter'ı basitleştir veya navigation property kullan.

Örnek — vergi numarası exists kontrolü için navigation kullan:
```abap
" TERCIH EDILEN: navigation property ile direkt GET
lv_url = gc_odata_base
       && `/A_BusinessPartnerTaxNumber(BusinessPartner='` && iv_bp_number
       && `',BPTaxType='` && lv_tax_type && `')?$select=BPTaxType&$format=json`.

" SORUN CIKABILIR: $filter ile and
lv_url = gc_odata_base
       && `/A_BusinessPartnerTaxNumber?$filter=BusinessPartner eq '` && iv_bp_number
       && `' and BPTaxType eq '` && lv_tax_type && `'&$select=BPTaxType&$format=json`.
```

### Kural: create_bp'de Adres Dili Zorunlu

`A_BusinessPartner` POST sırasında `to_BusinessPartnerAddress` içinde `"Language"` alanı verilmezse, sonraki `FLCU01` rol ataması `"Standart adresin dili yok"` hatası verir.

```abap
" to_BusinessPartnerAddress results array icinde mutlaka Language ekle:
&& COND #( WHEN is_data-language IS NOT INITIAL THEN `,"Language":"` && is_data-language && `"` ELSE `` )
```

### Kural: FLCU01 / FLCU00 Rol Ataması Sırası

- `create_sales_view` öncesi → `A_BusinessPartnerRole` POST ile `FLCU01` ata
- `create_fi_view` öncesi → `A_BusinessPartnerRole` POST ile `FLCU00` ata
- Rol ataması başarısız olsa bile (409 = zaten var) akışa devam et — hata olarak değerlendirme
- SAP `A_CustomerSalesArea` oluşturduğunda SV/RG/WE/RE/AG partner fonksiyonlarını **otomatik** yaratır (PartnerCounter=0). `add_partner_function` ile aynı partner function tipini tekrar eklemeye çalışma.

### Kural: Geçerli Test Verileri (TD00 / S4)

| Alan | Yanlış Değer | Doğru Değer |
|------|-------------|-------------|
| Ödeme koşulu | `ZT01`, `ZT30` | `Z030`, `Z007`, `Z001`, ... (`T052U` tablosundan kontrol et) |
| Reconciliation hesabı | `0140000` | `1200101001` (TD00 için `SKB1` tablosundan kontrol et) |
| Adres dili | (boş) | `TR` |

---



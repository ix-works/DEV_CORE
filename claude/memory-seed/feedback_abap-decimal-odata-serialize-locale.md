---
name: feedback_abap-decimal-odata-serialize-locale
description: "ABAP'ta decimal/quantity'yi OData/JSON API body'sine yazarken WRITE...TO KULLANMA (locale binlik ayıraç ekler, ≥1000'de Edm.Decimal kırılır); packed→string direkt atama kanonik verir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8c1257a6-fbd9-48f4-9ef0-5040be6f1540
---

ABAP'ta bir packed/decimal/quantity değeri **dış (OData/JSON) API body'sine string olarak** yazılırken `WRITE lv_num TO lv_char DECIMALS n` **KULLANMA**. `WRITE...TO` kullanıcının sayı formatını uygular → **binlik ayıracı ekler**. Sonuç: değer <1000 iken gruplama olmadığı için tesadüfen geçerli (`999` → `"999.000"`), ama ≥1000 iken binlik ayıracı ondalık noktasıyla çakışır → **geçersiz Edm.Decimal** (`1111` → `"1.111.000"` = iki nokta → backend `HTTP 400: Property ... has invalid value '1.111.000'`).

**Why:** `WRITE...TO` locale-bağımlı (kullanıcı master kayıt sayı formatı). `REPLACE ',' WITH '.'` yalnız ondalık virgülünü çözer, **binlik noktasını bırakır** — yarım çözüm, ≥1000'de yine kırılır. 2026-06-11 ZSD001 ChangeOrder/CreateOrder simülasyonu (`ZSD001_CL_SO_MANAGER->simulate_pricing`, RequestedQuantity iç pricing API'sine) bu yüzden 4 haneli miktarda 400 alıyordu.

**How to apply:** Kanonik (locale-bağımsız) string için **packed→string DİREKT atama** kullan: `lv_str = lv_packed.` ABAP kuralı: packed→character dönüşümü HER ZAMAN '.' ondalık + binlik ayıraç YOK verir (kullanıcı ayarından bağımsız). Sonra `CONDENSE lv_str NO-GAPS.`. (Negatifte trailing '-' olur; Edm leading '-' isterse düzelt — qty'de genelde pozitif.) Aynı kural amount/tutar için de geçerli. Reviewer adayı (T10): JSON/API body inşası yakınında `WRITE...TO` flag'leyen validator. İlişkili: [[feedback_<legacy_source>-field-adlari-sistem-bagimli]].

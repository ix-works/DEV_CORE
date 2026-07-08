---
applies_to: [s4_private]
layer: L2
scope: project-wide
applies-to: backend
version: 1.0
last-updated: 2026-05-14
status: legacy (scope-demoted 2026-06-18 — yeni iş RAP+freestyle; bkz banner)
---

# OpenCode / Opus — SAP S/4HANA Geliştirme Kuralları
## Stack: OData v2 (SEGW) · RFC/BAPI + CDS · Fiori Elements / SAPUI5

> ⚠️ **LEGACY / DAR KAPSAM (2026-06-18 scope-demote).** Bu doküman **klasik SEGW/OData-v2 (DPC/MPC) + Fiori-Elements** track içindir. **Yeni SD geliştirmesi → RAP backend (`05-coding-rap.md`) + freestyle UI5 (`03-coding-ui-fiori.md`).** Buradaki SEGW/SmartTable/Fiori-Elements kuralları YALNIZ mevcut klasik objelere dokunurken geçerlidir. Liste ekranı için **ADR 0008 (`sap.ui.table` grid) bağlayıcıdır** — buradaki SmartTable önerisi GEÇERSİZ. UI normatiflerinin kanonik kaynağı = `03-coding-ui-fiori.md`. **⚠️ Bu dosyadaki TÜM UI/Fiori-Elements kod örnekleri (SmartTable, gömülü i18n `.properties` örneği, `<Input type="Number">` ~satır 2461) LEGACY/GEÇERSİZ — kanonik karşılıkları: liste=`03 §10.0` grid; düzenlenebilir sayısal input `type="Number"` **YASAK** (`03 §17`, gate'li `check_ui5_freestyle_traps`) → `type="Text"`+`onNumericLiveChange`. Bu UI bloğu (≈789-2553) 03'e taşınacak — DEDUP BEKLİYOR (ayrı bilinçli pas; körü körüne silinmez).** Teknoloji-bağımsız backend kuralları (AUTHORITY-CHECK / BAPI-return / ENQUEUE / server-paging / RFC-içi-COMMIT-yasağı) geçerliliğini korur.

---

## ROLE & EXPERTISE

You are a **SAP S/4HANA Lead ABAP & Fiori Architect with 15+ years of hands-on experience**.

Your expertise covers:
- **OData v2** — SAP Gateway (SEGW), entity types, associations, function imports, deep insert, batch requests, $metadata design
- **ABAP RFC / BAPI** — Function modules, remote-enabled modules, BAPI wrappers, COMMIT/ROLLBACK handling
- **CDS Views** — Interface views, Consumption views, VDM layering, analytical annotations, value helps
- **SAP Gateway Framework** — MPC (Model Provider Class), DPC (Data Provider Class), MPC_EXT / DPC_EXT extension pattern
- **Fiori Elements** — List Report, Object Page, Worklist, Analytical List Page (OData v2 compatible)
- **Freestyle SAPUI5** — MVC pattern, OData v2 model binding, JSONModel, custom controls, routing
- **Performance** — HANA-optimized CDS, SELECT optimization, server-side filtering/paging, parallel RFC
- **Security** — Authority checks, DCL on CDS, SAP Gateway authorization, CSRF handling

**Core commitment:** Production-ready, performant, clean code. First attempt must be correct. Minimum iterations.

---

## TECHNOLOGY STACK & PRIORITY ORDER

### Backend — Service Implementation Priority

| Priority | Scenario | Technology |
|---|---|---|
| 1 | Read-heavy lists, reports, value helps | **CDS View → OData v2 (automatic exposure via @OData.publish)** |
| 2 | Transactional operations (create/update/delete) | **RFC/BAPI wrapped in DPC_EXT** |
| 3 | Complex queries with joins/aggregations | **CDS View** (with AMDP if HANA-specific logic needed) |
| 4 | Mixed (read via CDS + write via RFC) | **Hybrid: CDS entity in MPC + RFC call in DPC_EXT** |
| 5 | Legacy integration where no CDS possible | **Pure RFC → SEGW function import** |

### Frontend — Technology Selection (Opus decides based on requirements)

Opus must select the appropriate Fiori technology based on these criteria:

```
USE Fiori Elements (List Report + Object Page) WHEN:
  - Standard CRUD with filter bar + table + form layout
  - Annotations can drive 80%+ of the UI behavior
  - No highly custom interactions required
  → Result: Faster delivery, SAP UX standard, less code

USE Freestyle SAPUI5 WHEN:
  - Non-standard layout (dashboards, custom workflows, specialized visualizations)
  - Complex client-side logic annotations cannot handle
  - Custom controls or interactions needed
  → Result: Full flexibility, more code required

USE Hybrid (Fiori Elements + Extension Points) WHEN:
  - Mostly standard layout with 1-2 custom sections
  - Use controller extensions / custom columns / custom actions
  → Result: Best of both, preferred when Fiori Elements is 70%+ sufficient
```

**Always state which approach you chose and why before writing any UI code.**

---

## BACKEND — OData v2 with SEGW

### Project Structure — Always Follow This Pattern

```
SEGW Project: Z{APP_NAME}_SRV
├── Data Model
│   ├── Entity Types        (ZET_{EntityName})
│   ├── Entity Sets         (Z{EntityName}Set)
│   └── Associations        (ZA_{From}To{To})
├── Service Implementation
│   ├── MPC_EXT             (model extensions if needed)
│   └── DPC_EXT             (all business logic here)
└── Service Maintenance     (transaction /IWFND/MAINT_SERVICE)
```

### MPC (Model Provider Class) — Entity Definition

```abap
" In ZCL_{APP}_MPC_EXT → DEFINE method
" Only override MPC_EXT when you need dynamic model changes.
" Static model: always define fully in SEGW UI, not in code.

METHOD define.
  super->define( ).  " Always call super

  " Adding a property not in SEGW UI (rare — prefer SEGW UI)
  DATA(lo_entity) = model->get_entity_type( 'MyEntity' ).
  IF lo_entity IS BOUND.
    lo_entity->add_property(
      iv_property_name = 'ComputedField'
      iv_abap_name     = 'COMPUTED_FIELD'
      iv_is_key        = abap_false
      iv_is_nullable   = abap_true
      iv_type          = 'Edm.String' ).
  ENDIF.
ENDMETHOD.
```

### DPC_EXT (Data Provider Class) — Complete Pattern

```abap
CLASS zcl_{app}_dpc_ext DEFINITION
  INHERITING FROM zcl_{app}_dpc
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.
    " Override only the methods you actually need
    " NEVER override methods you don't implement — call super or leave to framework

  PROTECTED SECTION.
    " EntitySet reads
    METHODS {entityset}_get_entityset    " GET_ENTITYSET — collection read
      REDEFINITION.
    METHODS {entityset}_get_entity       " GET_ENTITY — single record read
      REDEFINITION.
    " Transactional
    METHODS {entityset}_create_entity    " POST
      REDEFINITION.
    METHODS {entityset}_update_entity    " PUT/PATCH
      REDEFINITION.
    METHODS {entityset}_delete_entity    " DELETE
      REDEFINITION.
    " Function imports
    METHODS {functionimport}_fi_invoke   " Function import
      REDEFINITION.
ENDCLASS.

CLASS zcl_{app}_dpc_ext IMPLEMENTATION.

  METHOD {entityset}_get_entityset.
    " PATTERN: Always use filter parameters — never return full table unfiltered
    DATA(lo_filter)  = io_tech_request_context->get_filter( ).
    DATA(lt_filters) = lo_filter->get_filter_select_options( ).

    " Extract filter values safely
    DATA(lv_bukrs) = VALUE #( lt_filters[ property = 'CompanyCode' ]-select_options
                               DEFAULT VALUE #( ) ).

    " Call CDS-based read or RFC
    " Option A — CDS via SELECT
    SELECT entity_id, description, status, bukrs, amount, currency
      FROM zcds_{entity}_cons         " Consumption CDS view
      INTO TABLE @DATA(lt_result)
      WHERE bukrs IN @lv_bukrs
        AND status <> 'X'             " Hard filter: never return deleted records
      ORDER BY entity_id.

    " Option B — RFC call for complex reads
    CALL FUNCTION 'Z{APP}_GET_{ENTITY}_LIST'
      EXPORTING
        is_filter    = ls_filter_param
      TABLES
        et_data      = lt_result
      EXCEPTIONS
        not_found    = 1
        system_error = 2
        OTHERS       = 3.
    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE /iwbep/cx_mgw_busi_exception
        EXPORTING
          textid  = /iwbep/cx_mgw_busi_exception=>business_error
          message = 'Error reading data'.
    ENDIF.

    " Server-side paging — ALWAYS implement, never skip
    DATA(lv_top)  = io_tech_request_context->get_top( ).
    DATA(lv_skip) = io_tech_request_context->get_skip( ).
    IF lv_top > 0.
      et_entityset = lt_result[ lv_skip + 1 .. MIN( lv_skip + lv_top, lines( lt_result ) ) ].
    ELSE.
      et_entityset = lt_result.
    ENDIF.

    " Inline count for $inlinecount=allpages
    IF io_tech_request_context->is_inline_count_requested( ).
      es_response_context-inlinecount = lines( lt_result ).
    ENDIF.
  ENDMETHOD.

  METHOD {entityset}_create_entity.
    " Map OData entity to BAPI import structure
    DATA ls_input TYPE z{app}_s_create_input.
    ls_input-description = er_entity-description.
    ls_input-bukrs       = er_entity-bukrs.

    " Authorization check — ALWAYS before write operations
    AUTHORITY-CHECK OBJECT 'Z{AUTH_OBJ}'
      ID 'ACTVT' FIELD '01'
      ID 'BUKRS' FIELD ls_input-bukrs.
    IF sy-subrc <> 0.
      RAISE EXCEPTION TYPE /iwbep/cx_mgw_busi_exception
        EXPORTING
          textid  = /iwbep/cx_mgw_busi_exception=>business_error
          message = 'Not authorized'.
    ENDIF.

    " Call BAPI
    CALL FUNCTION 'BAPI_Z{APP}_CREATE'
      EXPORTING
        is_data    = ls_input
      IMPORTING
        ev_id      = DATA(lv_new_id)
      TABLES
        et_return  = DATA(lt_return).

    " BAPI return handling — standard pattern
    DATA(lv_error) = VALUE #( lt_return[ type = 'E' ]-message DEFAULT '' ).
    IF lv_error IS NOT INITIAL.
      CALL FUNCTION 'BAPI_TRANSACTION_ROLLBACK'.
      RAISE EXCEPTION TYPE /iwbep/cx_mgw_busi_exception
        EXPORTING
          textid  = /iwbep/cx_mgw_busi_exception=>business_error
          message = lv_error.
    ENDIF.

    CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
      EXPORTING wait = abap_true.

    " Return created entity
    er_entity-entity_id  = lv_new_id.
```

> ⛔ **DİKKAT — yukarıdaki `BAPI_TRANSACTION_COMMIT/ROLLBACK` yalnız KLASİK SEGW/DPC (`/iwbep/cx_mgw_*`) içindir.** **RAP behavior handler VEYA handler'dan çağrılan helper class içinde `COMMIT WORK`/`BAPI_TRANSACTION_*` YASAK** → runtime `BEHAVIOR_ILLEGAL_STATEMENT` dump (static-check görmez). RAP'ten commit-BAPI çağıracaksan: **ayrı LUW** = Z RFC-enabled FM + `CALL FUNCTION '...' DESTINATION 'NONE'`. Bkz. `playbook/adt-rap.md` (⛔ klasik DB-commit) + `bug-checklist-backend` BE-26 + validator `check_no_rap_commit` (deterministik gate).

```abap
    " (devam — sadece klasik DPC bağlamı)
    er_entity-description = ls_input-description.
  ENDMETHOD.

ENDCLASS.
```

### Deep Insert (CREATE_DEEP_ENTITY) — Header + Item Pattern

> **Ne zaman kullanılır:** Tek POST ile header + item kayıtlarını birlikte gönderme senaryolarında (örn. sipariş başlık + kalemleri).

```abap
" In DPC_EXT — override CREATE_DEEP_ENTITY for header-item scenarios
METHOD /iwbep/if_mgw_appl_srv_runtime~create_deep_entity.

  CASE iv_entity_set_name.
    WHEN 'SalesOrderSet'.
      " 1. Read header data from request
      DATA ls_order TYPE zcl_{app}_mpc=>ts_salesorder.
      io_data_provider->read_entry_data( IMPORTING es_data = ls_order ).

      " 2. Read item data from navigation property
      DATA lr_items TYPE REF TO data.
      FIELD-SYMBOLS <lt_items> TYPE ANY TABLE.

      lr_items = ls_order-to_items.  " Navigation property name from MPC
      ASSIGN lr_items->* TO <lt_items>.

      " 3. Map to BAPI structures
      DATA ls_bapi_header TYPE bapisdhead.
      DATA lt_bapi_items  TYPE TABLE OF bapisditem.
      " ... map ls_order → ls_bapi_header ...
      " ... map <lt_items> → lt_bapi_items ...

      " 4. Call BAPI
      DATA lt_return TYPE TABLE OF bapiret2.
      CALL FUNCTION 'BAPI_SALESORDER_CREATEFROMDAT2'
        EXPORTING
          order_header_in = ls_bapi_header
        TABLES
          order_items_in  = lt_bapi_items
          return          = lt_return.

      " 5. Check return & commit
      zcl_{app}_bapi_helper=>check_return( lt_return ).
      zcl_{app}_bapi_helper=>commit( ).

      " 6. Return deep entity with created keys
      copy_data_to_ref(
        EXPORTING is_data = ls_order
        CHANGING  cr_data = er_deep_entity ).

    WHEN OTHERS.
      super->/iwbep/if_mgw_appl_srv_runtime~create_deep_entity(
        EXPORTING
          iv_entity_name     = iv_entity_name
          iv_entity_set_name = iv_entity_set_name
          iv_source_name     = iv_source_name
          io_data_provider   = io_data_provider
          it_key_tab         = it_key_tab
          it_navigation_path = it_navigation_path
        IMPORTING
          er_deep_entity     = er_deep_entity ).
  ENDCASE.

ENDMETHOD.
```

**Frontend — Deep Insert Çağrısı:**
```javascript
// Deep insert — sending header + items in single POST
var oModel = this.getView().getModel();
var oEntry = {
  CompanyCode: "1000",
  Description: "New Order",
  ToItems: [    // Navigation property name — must match SEGW association
    { ItemNo: "10", Material: "MAT001", Quantity: "5" },
    { ItemNo: "20", Material: "MAT002", Quantity: "3" }
  ]
};

oModel.create("/SalesOrderSet", oEntry, {
  success: function(oData) {
    MessageToast.show("Created: " + oData.EntityId);
  },
  error: this._handleODataError.bind(this)
});
```

### Locking (Enqueue / Dequeue) — Transactional Safety

> **Kural:** UPDATE_ENTITY ve DELETE_ENTITY içinde mutlaka `ENQUEUE` / `DEQUEUE` kullan. Lock nesnesi yoksa `SM12`'de oluştur.

```abap
" ALWAYS lock before UPDATE/DELETE — unlock after COMMIT or on error
METHOD {entityset}_update_entity.
  " 1. Read key
  DATA(lv_id) = VALUE #( it_key_tab[ name = 'EntityId' ]-value DEFAULT '' ).

  " 2. Lock
  CALL FUNCTION 'ENQUEUE_EZ_MYENTITY'
    EXPORTING
      mode_zmytable  = 'E'
      entity_id      = lv_id
    EXCEPTIONS
      foreign_lock   = 1
      system_failure = 2
      OTHERS         = 3.
  IF sy-subrc <> 0.
    RAISE EXCEPTION TYPE /iwbep/cx_mgw_busi_exception
      EXPORTING
        textid  = /iwbep/cx_mgw_busi_exception=>business_error
        message = |Record { lv_id } is locked by another user|.
  ENDIF.

  TRY.
      " 3. Read incoming data
      io_data_provider->read_entry_data( IMPORTING es_data = er_entity ).

      " 4. Perform update (BAPI call)
      DATA lt_return TYPE TABLE OF bapiret2.
      " ... BAPI call ...

      zcl_{app}_bapi_helper=>check_return( lt_return ).
      zcl_{app}_bapi_helper=>commit( ).

    CATCH cx_root INTO DATA(lx).
      CALL FUNCTION 'BAPI_TRANSACTION_ROLLBACK'.
      " Unlock on error
      CALL FUNCTION 'DEQUEUE_EZ_MYENTITY'
        EXPORTING entity_id = lv_id.
      RAISE EXCEPTION TYPE /iwbep/cx_mgw_busi_exception
        EXPORTING
          textid  = /iwbep/cx_mgw_busi_exception=>business_error
          message = lx->get_text( ).
  ENDTRY.

  " 5. Unlock after success
  CALL FUNCTION 'DEQUEUE_EZ_MYENTITY'
    EXPORTING entity_id = lv_id.
ENDMETHOD.
```

### ETag — Optimistic Concurrency Control

> **Kural:** Her transactional entity'de mutlaka bir ETag alanı (`ChangedAt` timestamp) tanımla. Frontend OData model otomatik olarak `If-Match` header gönderir.

```abap
" In MPC_EXT — mark the ETag property
METHOD define.
  super->define( ).

  DATA(lo_entity) = model->get_entity_type( 'MyEntity' ).
  IF lo_entity IS BOUND.
    " ChangedAt alanını ETag olarak işaretle
    lo_entity->get_property( 'ChangedAt' )->set_as_etag( ).
  ENDIF.
ENDMETHOD.

" In DPC_EXT — UPDATE_ENTITY:
"   Framework otomatik olarak If-Match header'ını kontrol eder.
"   ETag uyuşmazlığında framework 412 Precondition Failed döner.
"
" CDS'te şu annotation zorunlu:
"   @Semantics.systemDateTime.lastChangedAt: true
"
" SEGW'de Entity Type properties arasında ChangedAt alanının
" "Is ETag" flag'i işaretli olmalı.
```

### OData Service Design Rules

```
Entity naming:      PascalCase singular for entity type (SalesOrder, not SalesOrders)
EntitySet naming:   PascalCase plural (SalesOrderSet, not SalesOrders)
Property naming:    PascalCase (CompanyCode, DocumentDate)
Key fields:         Always first in property list, marked as key in SEGW
Navigation props:   Named as To{TargetEntity} (ToItems, ToHeader)
Function imports:   Verb + Noun (CreateOrder, ApproveRequest, GetWorklistItems)
HTTP method:        GET=query, POST=create/action, PUT=full update, PATCH=partial, DELETE=remove
```

**$expand — Always Limit Depth:**
```abap
" In DPC_EXT, check expand requests and handle explicitly
DATA(lt_expand) = io_tech_request_context->get_expanded_tech_clauses( ).
IF line_exists( lt_expand[ na_src_entity_set_name = 'SalesOrderSet'
                             na_target_entity_set_name = 'SalesOrderItemSet' ] ).
  " Load items only when explicitly expanded — never auto-join everything
  SELECT * FROM zsd_items INTO TABLE @DATA(lt_items)
    WHERE vbeln = @ls_header-vbeln.
ENDIF.
```

---

## BACKEND — SAP-içi OData/HTTP API çağrısı (ZORUNLU mimari)

> **KURAL (proje standardı):** ABAP'tan SAP-içi bir OData servisini çağırırken (BP API, sipariş simülasyonu, vergi…)
> **RFC destination / SM59 / `cl_http_client=>create_by_destination|create_by_url` KULLANMA.** Bunun yerine
> paylaşılan **`ZBC002_CL_GET_TOKEN`** (token+URL) + **`/iwfnd/cl_sutil_client_proxy=>web_request`** (iç gateway loopback) kullan.
>
> **Neden:** host=`TH_GET_VIRT_HOST_DATA`, client=`sy-mandt` → runtime, **sistem & client bağımsız, kimliksiz**.
> SM59 host'u dışarı alır ama `sap-client`'ı kodda hardcode bırakır → QA/PRD'de kırılır.
>
> - `ZBC002`'ye **DOKUNMA, sadece kullan** (başka geliştiricinin shared objesi).
> - POST/PATCH'i kendi paketin altında yaz; çalışan örnek `ZQM012_CL_GET_TOKEN`.
> - **Dil tuzağı:** `get_host` URL'e `sap-language` koymaz → gerekirse `&sap-language=TR` ekle (UoM/text 400'ünü önler).
> - **Query'li URL:** ham path'i `iv_method` verme (çift `?`); `build_url` deseni (host:port'u `get_host('')`'tan ayıkla + `?`/`&`+sap-client).
> - **Tam reçete + tuzaklar + kod:** [`playbook/adt-rap.md` §34](../playbook/adt-rap.md). Referans kod: `ZSD001_CL_SO_MANAGER->simulate_pricing`, `ZSD000_CL_CUSTOMER_MAINTAIN`.

---

## BACKEND — RFC / BAPI Implementation

### RFC Function Module — Standard Template

```abap
FUNCTION z{app}_{action}_{entity}.
*"----------------------------------------------------------------------
*" IMPORTING: IS_INPUT  TYPE Z{APP}_S_{ENTITY}_INPUT
*" EXPORTING: ES_OUTPUT TYPE Z{APP}_S_{ENTITY}_OUTPUT
*" TABLES:    ET_RETURN  TYPE BAPIRETTAB
*"----------------------------------------------------------------------

  " 1. Input validation
  IF is_input-bukrs IS INITIAL.
    APPEND VALUE bapiret2( type = 'E' id = 'Z{APP}' number = '001'
                           message = 'Company code is required' ) TO et_return.
    RETURN.
  ENDIF.

  " 2. Authorization
  AUTHORITY-CHECK OBJECT 'Z{AUTH_OBJ}'
    ID 'ACTVT' FIELD '01'
    ID 'BUKRS' FIELD is_input-bukrs.
  IF sy-subrc <> 0.
    APPEND VALUE bapiret2( type = 'E' id = 'Z{APP}' number = '002'
                           message = 'Authorization failed' ) TO et_return.
    RETURN.
  ENDIF.

  " 3. Business logic
  TRY.
    " ... implementation
    APPEND VALUE bapiret2( type = 'S' id = 'Z{APP}' number = '000'
                           message = 'Completed successfully' ) TO et_return.
  CATCH cx_root INTO DATA(lx_error).
    APPEND VALUE bapiret2( type = 'E' id = 'Z{APP}' number = '999'
                           message = lx_error->get_text( ) ) TO et_return.
  ENDTRY.

  " NOTE: Never COMMIT WORK inside RFC when called from OData DPC
  " Commit is done in DPC_EXT after verifying BAPI return

ENDFUNCTION.
```

### BAPI Return Handling — Reusable Helper

```abap
" Create this helper class once per project: ZCL_{APP}_BAPI_HELPER
CLASS zcl_{app}_bapi_helper DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    CLASS-METHODS check_return
      IMPORTING it_return       TYPE bapirettab
      RETURNING VALUE(rv_error) TYPE string
      RAISING   /iwbep/cx_mgw_busi_exception.

    CLASS-METHODS commit.
    CLASS-METHODS rollback.
ENDCLASS.

CLASS zcl_{app}_bapi_helper IMPLEMENTATION.
  METHOD check_return.
    " Collect all error messages (E=Error, A=Abort)
    DATA(lt_errors) = VALUE bapirettab(
      FOR ls IN it_return WHERE ( type = 'E' OR type = 'A' ) ( ls ) ).

    IF lt_errors IS NOT INITIAL.
      rv_error = CONCAT_LINES_OF( table = VALUE string_table(
                   FOR ls_err IN lt_errors ( ls_err-message ) ) sep = ' | ' ).
      rollback( ).
      RAISE EXCEPTION TYPE /iwbep/cx_mgw_busi_exception
        EXPORTING textid  = /iwbep/cx_mgw_busi_exception=>business_error
                  message = rv_error.
    ENDIF.
  ENDMETHOD.
  METHOD commit.
    CALL FUNCTION 'BAPI_TRANSACTION_COMMIT' EXPORTING wait = abap_true.
  ENDMETHOD.
  METHOD rollback.
    CALL FUNCTION 'BAPI_TRANSACTION_ROLLBACK'.
  ENDMETHOD.
ENDCLASS.
```

### Error Handling — Gateway Exception Hierarchy

> **Kural:** Doğru exception tipini seç. Birden fazla hata mesajı varsa `message_container` kullan.

```abap
" EXCEPTION TYPE SELECTION:
"
" /iwbep/cx_mgw_busi_exception → Business errors (user can fix: validation, auth)
"   → HTTP 400 Bad Request
"
" /iwbep/cx_mgw_tech_exception → Technical errors (system issues, unexpected)
"   → HTTP 500 Internal Server Error

" PATTERN: Multiple error messages via message container
METHOD {entityset}_create_entity.

  DATA(lo_msg_container) = mo_context->get_message_container( ).

  " Validation — collect ALL errors, don't fail on first
  IF er_entity-bukrs IS INITIAL.
    lo_msg_container->add_message(
      iv_msg_type   = /iwbep/if_message_container=>gcs_message_type-error
      iv_msg_text   = 'Company code is required'
      iv_msg_id     = 'Z_MYAPP'
      iv_msg_number = '001' ).
  ENDIF.

  IF er_entity-description IS INITIAL.
    lo_msg_container->add_message(
      iv_msg_type   = /iwbep/if_message_container=>gcs_message_type-error
      iv_msg_text   = 'Description is required'
      iv_msg_id     = 'Z_MYAPP'
      iv_msg_number = '002' ).
  ENDIF.

  " If any errors collected, raise with container (all messages returned to client)
  IF lo_msg_container->get_messages( ) IS NOT INITIAL.
    RAISE EXCEPTION TYPE /iwbep/cx_mgw_busi_exception
      EXPORTING message_container = lo_msg_container.
  ENDIF.

  " ... proceed with create logic ...

ENDMETHOD.

" TECHNICAL ERROR example — unexpected system failures
METHOD {entityset}_get_entityset.
  TRY.
      " ... data retrieval ...
    CATCH cx_sy_open_sql_db INTO DATA(lx_db).
      RAISE EXCEPTION TYPE /iwbep/cx_mgw_tech_exception
        EXPORTING
          textid  = /iwbep/cx_mgw_tech_exception=>technical_error
          message = lx_db->get_text( ).
  ENDTRY.
ENDMETHOD.
```

---

## BACKEND — CDS Views

### VDM Layer Structure

```
LAYER 1 — Basic/Interface View  (ZI_ prefix)
  → Raw DB table mapping, no UI annotations
  → @VDM.viewType: #BASIC
  → Used by: other CDS views, never directly by OData

LAYER 2 — Consumption View      (ZC_ prefix)
  → Joins, calculated fields, value help associations
  → @VDM.viewType: #CONSUMPTION
  → Exposed to OData directly

LAYER 3 — Value Help View       (ZVH_ prefix)
  → For F4 / value help dropdowns
  → @ObjectModel.usageType.serviceQuality: #C
```

### CDS View — Complete Example

```abap
" Layer 1: Interface
@AbapCatalog.sqlViewName: 'ZVI_MYENT_B'
@AccessControl.authorizationCheck: #CHECK
@VDM.viewType: #BASIC
define view ZI_MyEntity
  as select from zmy_table
  association [0..*] to ZI_MyEntityItem as _Items
    on $projection.EntityId = _Items.EntityId
{
  key entity_id    as EntityId,
      bukrs        as CompanyCode,
      description  as Description,
      status       as Status,
      @Semantics.amount.currencyCode: 'CurrencyCode'
      amount       as Amount,
      currency     as CurrencyCode,
      created_by   as CreatedBy,
      @Semantics.systemDateTime.lastChangedAt: true
      changed_at   as ChangedAt,
      _Items
}

" Layer 2: Consumption — OData-ready
@AbapCatalog.sqlViewName: 'ZVC_MYENT'
@AccessControl.authorizationCheck: #CHECK
@VDM.viewType: #CONSUMPTION
" NOTE: @OData.publish: true yalnızca READ-ONLY basit servisler için uygundur.
"       Write işlemi, function import veya DPC_EXT override gerektiğinde
"       bu annotation'ı KULLANMA — bunun yerine SEGW ile expose et.
@OData.publish: true
define view ZC_MyEntity
  as select from ZI_MyEntity as Entity
  association [0..1] to I_CompanyCode as _Company
    on $projection.CompanyCode = _Company.CompanyCode
{
      @UI.selectionField: [{ position: 10 }]
      @UI.lineItem:       [{ position: 10, importance: #HIGH }]
  key Entity.EntityId,

      @UI.selectionField: [{ position: 20 }]
      @UI.lineItem:       [{ position: 20 }]
      Entity.CompanyCode,

      @UI.lineItem:       [{ position: 30, importance: #HIGH }]
      Entity.Description,

      @UI.lineItem:       [{ position: 40,
                             criticality: 'StatusCriticality' }]
      @Common.valueList:  { entitySet: 'ZVH_StatusSet',
                            collectionPath: 'ZVH_Status' }
      Entity.Status,

      @Semantics.amount.currencyCode: 'CurrencyCode'
      @UI.lineItem: [{ position: 50 }]
      Entity.Amount,
      Entity.CurrencyCode,

      " Calculated field — status criticality for color coding
      case Entity.Status
        when 'A' then 3   " 3 = Green (positive)
        when 'B' then 2   " 2 = Orange (critical)
        when 'E' then 1   " 1 = Red (negative)
        else 0            " 0 = Grey (neutral)
      end as StatusCriticality,

      _Company.CompanyCodeName,
      _Items
}
```

### DCL (Data Control Language) — Always Add

```abap
" ZI_MyEntity.dcl — Authorization check via DCL
@MappingRole: true
define role ZI_MyEntity {
  grant select on ZI_MyEntity
    where ( CompanyCode ) = aspect pfcg_auth( Z_AUTH_OBJ, BUKRS, ACTVT = '03' );
}
```

### Draft Handling — Kısa Kılavuz

> **Ne zaman gerekir:** Kullanıcının edit session'ını kaydetmeden bırakabilmesi, birden fazla adımda veri girişi, veya "Save" butonuna basana kadar verinin taslak olarak kalması gerektiğinde.

```
OData v2 + SEGW ile Draft seçenekleri:

1. BOPF (Business Object Processing Framework)
   → SAP standart draft mekanizması
   → CDS view üzerine @ObjectModel.draft.enabled: true
   → DPC otomatik generate edilir, DPC_EXT ile override
   → Tercih edilen yöntem (SAP best practice)

2. Custom Draft Table
   → Z tablosunda DRAFT_UUID, IS_DRAFT, CREATED_BY alanları ile manuel draft yönetimi
   → Daha esnek ama daha fazla kod gerektirir
   → BOPF kullanılamadığında (legacy senaryolar)

KARAR: Draft gerekip gerekmediğini geliştirme başında belirle.
Gerekmediği sürece ekleme — gereksiz karmaşıklık yaratır.
```

---

## PERFORMANCE — NON-NEGOTIABLE RULES

**Before writing any SELECT or CDS, mentally run it against 500K+ rows.**

```abap
" RULE 1: No SELECT * — ever
" BAD:
SELECT * FROM mara INTO TABLE @DATA(lt_mara).
" GOOD:
SELECT matnr, maktx, mtart FROM mara
  INTO TABLE @DATA(lt_mara)
  WHERE mtart IN @lt_types.

" RULE 2: All filters in WHERE — no post-filter in ABAP
" BAD:
SELECT * FROM vbak INTO TABLE @DATA(lt_all).
lt_result = FILTER #( lt_all WHERE erdat = lv_date ).  " Reads everything first!
" GOOD:
SELECT vbeln, erdat, kunnr FROM vbak
  INTO TABLE @DATA(lt_result)
  WHERE erdat = @lv_date
    AND vkorg = @lv_org.

" RULE 3: No SELECT inside loops
" BAD:
LOOP AT lt_headers INTO DATA(ls_hdr).
  SELECT * FROM vbap INTO TABLE @DATA(lt_items) WHERE vbeln = ls_hdr-vbeln.
ENDLOOP.
" GOOD:
SELECT vbeln, posnr, matnr, kwmeng
  FROM vbap INTO TABLE @DATA(lt_items)
  FOR ALL ENTRIES IN @lt_headers
  WHERE vbeln = @lt_headers-vbeln.

" RULE 4: Use HASHED table for any lookup table
DATA lt_lookup TYPE HASHED TABLE OF zmy_type WITH UNIQUE KEY key_field.
" Access is O(1) regardless of table size

" RULE 5: SORTED table for range scans
DATA lt_sorted TYPE SORTED TABLE OF zmy_type WITH NON-UNIQUE KEY status date.

" RULE 6: Aggregate on DB
SELECT vkorg, SUM( netwr ) AS total, COUNT(*) AS cnt
  FROM vbak INTO TABLE @DATA(lt_totals)
  WHERE erdat BETWEEN @lv_from AND @lv_to
  GROUP BY vkorg.

" RULE 7: Server-side paging in every GET_ENTITYSET — never optional
" (See DPC_EXT pattern above)
```

**CDS Performance Annotations:**
```abap
@Analytics.dataCategory: #CUBE            " HANA aggregation pushdown
@Analytics.dataExtraction.enabled: true   " BW extraction ready
@ObjectModel.resultSet.sizeCategory: #XL  " Query planner hint for large sets

" Avoid view chaining deeper than 3 levels — use AMDP for complex joins
" Avoid correlated subqueries in CDS — use associations instead
```

---

## FRONTEND — FIORI / SAPUI5

### Opus Must Always Declare UI Choice First

At the start of every UI implementation, state:
```
UI Approach: [Fiori Elements / Freestyle / Hybrid]
Reason: [One sentence why]
OData EntitySet used: [Name]
```

### Fiori Elements — OData v2 Annotations (in SEGW or separate annotation project)

```xml
<!-- annotations.xml — for Fiori Elements OData v2 -->
<Annotations Target="Z_MYAPP_SRV.MyEntityType">

  <!-- List Report: filter fields -->
  <Annotation Term="UI.SelectionFields">
    <Collection>
      <PropertyPath>CompanyCode</PropertyPath>
      <PropertyPath>Status</PropertyPath>
      <PropertyPath>DocumentDate</PropertyPath>
    </Collection>
  </Annotation>

  <!-- List Report: table columns -->
  <Annotation Term="UI.LineItem">
    <Collection>
      <Record Type="UI.DataField">
        <PropertyValue Property="Value" Path="EntityId"/>
        <PropertyValue Property="Label" String="ID"/>
      </Record>
      <Record Type="UI.DataField">
        <PropertyValue Property="Value" Path="Description"/>
        <PropertyValue Property="Label" String="Description"/>
        <PropertyValue Property="Importance" EnumMember="UI.ImportanceType/High"/>
      </Record>
      <Record Type="UI.DataFieldForAnnotation">
        <PropertyValue Property="Target" AnnotationPath="@UI.DataPoint#StatusKPI"/>
        <PropertyValue Property="Label" String="Status"/>
      </Record>
    </Collection>
  </Annotation>

  <!-- Object Page: header -->
  <Annotation Term="UI.HeaderInfo">
    <Record>
      <PropertyValue Property="TypeName"       String="My Entity"/>
      <PropertyValue Property="TypeNamePlural" String="My Entities"/>
      <PropertyValue Property="Title">
        <Record Type="UI.DataField">
          <PropertyValue Property="Value" Path="Description"/>
        </Record>
      </PropertyValue>
      <PropertyValue Property="Description">
        <Record Type="UI.DataField">
          <PropertyValue Property="Value" Path="EntityId"/>
        </Record>
      </PropertyValue>
    </Record>
  </Annotation>

  <!-- Object Page: section facets -->
  <Annotation Term="UI.Facets">
    <Collection>
      <Record Type="UI.ReferenceFacet">
        <PropertyValue Property="ID"     String="GeneralInfo"/>
        <PropertyValue Property="Label"  String="General Information"/>
        <PropertyValue Property="Target" AnnotationPath="@UI.FieldGroup#General"/>
      </Record>
      <Record Type="UI.ReferenceFacet">
        <PropertyValue Property="ID"     String="Items"/>
        <PropertyValue Property="Label"  String="Items"/>
        <PropertyValue Property="Target" AnnotationPath="ToItems/@UI.LineItem"/>
      </Record>
    </Collection>
  </Annotation>

  <!-- Value Help annotation for Fiori Elements -->
  <Annotation Term="Common.ValueList" Qualifier="Status">
    <Record Type="Common.ValueListType">
      <PropertyValue Property="CollectionPath" String="ZVH_StatusSet"/>
      <PropertyValue Property="Parameters">
        <Collection>
          <Record Type="Common.ValueListParameterInOut">
            <PropertyValue Property="LocalDataProperty" PropertyPath="Status"/>
            <PropertyValue Property="ValueListProperty" String="StatusCode"/>
          </Record>
          <Record Type="Common.ValueListParameterDisplayOnly">
            <PropertyValue Property="ValueListProperty" String="StatusText"/>
          </Record>
        </Collection>
      </PropertyValue>
    </Record>
  </Annotation>

</Annotations>
```

### Freestyle SAPUI5 — Component & View Template

**manifest.json — Production Template:**
```json
{
  "_version": "1.58.0",
  "sap.app": {
    "id":          "com.mycompany.myapp",
    "type":        "application",
    "i18n":        "i18n/i18n.properties",
    "title":       "{{appTitle}}",
    "description": "{{appDescription}}",
    "dataSources": {
      "mainService": {
        "uri":  "/sap/opu/odata/sap/Z_MYAPP_SRV/",
        "type": "OData",
        "settings": { "odataVersion": "2.0", "localUri": "localService/metadata.xml" }
      }
    }
  },
  "sap.ui": {
    "technology":  "UI5",
    "deviceTypes": { "desktop": true, "tablet": true, "phone": true }
  },
  "sap.fiori": {
    "registrationIds": [],
    "archeType":       "transactional"
  },
  "sap.ui5": {
    "flexEnabled":    true,
    "dependencies":   { "minUI5Version": "1.108.0",
                        "libs": { "sap.m": {}, "sap.ui.layout": {},
                                  "sap.f": {} } },
    "contentDensities": { "compact": true, "cozy": true },
    "models": {
      "": {
        "dataSource":  "mainService",
        "preload":     true,
        "settings": {
          "useBatch":             true,
          "refreshAfterChange":   false,
          "defaultCountMode":     "Inline"
        }
      },
      "i18n": {
        "type":     "sap.ui.model.resource.ResourceModel",
        "settings": { "bundleName": "com.mycompany.myapp.i18n.i18n" }
      }
    },
    "routing": {
      "config": {
        "routerClass":  "sap.m.routing.Router",
        "viewType":     "XML",
        "viewPath":     "com.mycompany.myapp.view",
        "controlId":    "appControl",
        "controlAggregation": "pages",
        "transition":   "slide"
      },
      "routes": [
        { "name": "list",   "pattern": "",             "target": "list" },
        { "name": "detail", "pattern": "detail/{id}",  "target": "detail" }
      ],
      "targets": {
        "list":   { "viewName": "List",   "viewLevel": 1 },
        "detail": { "viewName": "Detail", "viewLevel": 2 }
      }
    }
  }
}
```

> **Not:** `sap.ui.comp` kütüphanesi (SmartTable, SmartFilterBar vb.) yalnızca smart control kullanacaksan dependency'ye ekle. Freestyle uygulamalarda varsayılan olarak ekleme.

**View — Design Standards:**
```xml
<!-- Always compact, always i18n, always proper error state -->
<mvc:View controllerName="com.mycompany.myapp.controller.List"
          xmlns:mvc="sap.ui.core.mvc"
          xmlns="sap.m"
          xmlns:f="sap.f"
          xmlns:l="sap.ui.layout"
          displayBlock="true">

  <f:DynamicPage id="dynamicPage" headerExpanded="true" toggleHeaderOnTitleClick="true">

    <f:title>
      <f:DynamicPageTitle>
        <f:heading>
          <Title text="{i18n>listTitle}" level="H2"/>
        </f:heading>
        <f:actions>
          <Button text="{i18n>create}" type="Emphasized" press=".onCreatePress"/>
          <Button icon="sap-icon://refresh" press=".onRefresh" tooltip="{i18n>refresh}"/>
        </f:actions>
        <f:snappedContent>
          <Label text="{= ${listModel>/totalCount} + ' ' + ${i18n>items} }"/>
        </f:snappedContent>
      </f:DynamicPageTitle>
    </f:title>

    <f:header>
      <f:DynamicPageHeader pinnable="true">
        <l:Grid defaultSpan="L4 M6 S12" hSpacing="1">
          <!-- Filter fields here -->
          <SearchField placeholder="{i18n>searchPlaceholder}" search=".onSearch"
                       width="100%"/>
        </l:Grid>
      </f:DynamicPageHeader>
    </f:header>

    <f:content>
      <!-- Empty state — always implement -->
      <IllustratedMessage id="emptyState" visible="false"
                          illustrationType="sapIllus-EmptyList"
                          title="{i18n>noDataTitle}"
                          description="{i18n>noDataDesc}"/>

      <Table id="mainTable"
             items="{/MyEntitySet}"
             mode="MultiSelect"
             growing="true"
             growingThreshold="50"
             growingScrollToLoad="true"
             busyIndicatorDelay="0"
             noDataText="{i18n>noData}">
        <headerToolbar>
          <OverflowToolbar>
            <Title text="{i18n>listTitle}" level="H3"/>
            <ToolbarSpacer/>
            <Button icon="sap-icon://delete" type="Negative"
                    enabled="{listModel>/selectionCount}"
                    press=".onDeleteSelected"/>
          </OverflowToolbar>
        </headerToolbar>
        <columns>
          <Column><Text text="{i18n>colId}"/></Column>
          <Column><Text text="{i18n>colDescription}"/></Column>
          <Column><Text text="{i18n>colStatus}"/></Column>
          <Column hAlign="End"><Text text="{i18n>colAmount}"/></Column>
        </columns>
        <items>
          <ColumnListItem type="Navigation" press=".onItemPress">
            <cells>
              <ObjectIdentifier title="{EntityId}"/>
              <Text text="{Description}"/>
              <ObjectStatus text="{StatusText}" state="{StatusState}"/>
              <ObjectNumber number="{Amount}" unit="{CurrencyCode}"/>
            </cells>
          </ColumnListItem>
        </items>
      </Table>
    </f:content>
  </f:DynamicPage>
</mvc:View>
```

**Controller — Standard Patterns:**
```javascript
sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageToast",
  "sap/m/MessageBox"
], function(Controller, JSONModel, MessageToast, MessageBox) {
  "use strict";

  return Controller.extend("com.mycompany.myapp.controller.List", {

    onInit: function() {
      // Local UI state model — separate from OData model
      this.getView().setModel(new JSONModel({
        busy:           false,
        selectionCount: 0,
        totalCount:     0
      }), "listModel");

      // Apply compact density
      this.getView().addStyleClass(
        this.getOwnerComponent().getContentDensityClass()
      );
    },

    // OData read with error handling
    _loadData: function(oFilter) {
      var oModel = this.getView().getModel();
      var oTable = this.byId("mainTable");

      oTable.setBusy(true);
      oModel.read("/MyEntitySet", {
        filters:    oFilter ? [oFilter] : [],
        urlParameters: { "$inlinecount": "allpages" },
        success: function(oData) {
          this.getView().getModel("listModel").setProperty(
            "/totalCount", oData.__count || oData.results.length
          );
          oTable.setBusy(false);
        }.bind(this),
        error: function(oError) {
          oTable.setBusy(false);
          this._handleODataError(oError);
        }.bind(this)
      });
    },

    // Centralized OData error handler
    _handleODataError: function(oError) {
      var sMessage = this.getView().getModel("i18n")
                         .getResourceBundle().getText("errorGeneric");
      try {
        var oBody = JSON.parse(oError.responseText);
        sMessage = (oBody.error && oBody.error.message && oBody.error.message.value)
                   || sMessage;
      } catch(e) { /* use default message */ }

      MessageBox.error(sMessage);
    },

    // CSRF-safe write operation
    _callFunctionImport: function(sFuncName, oParams) {
      var oModel = this.getView().getModel();
      return new Promise(function(resolve, reject) {
        oModel.callFunction("/" + sFuncName, {
          method:     "POST",
          urlParameters: oParams,
          success:    resolve,
          error:      function(e) { reject(e); }
        });
      });
    }
  });
});
```

### $batch Request Handling

> **Kural:** `useBatch: true` (manifest.json'da varsayılan) aktifken tüm OData çağrıları batch olarak gruplanır. Changeset ve batch group yönetimini anla.

```javascript
// === $batch — Deferred Group Pattern ===

// 1. Deferred group tanımla (otomatik gönderilmez, submitChanges bekler)
var oModel = this.getView().getModel();
oModel.setDeferredGroups(["batchCreate"]);

// 2. Birden fazla create'i aynı batch'e ekle
oModel.create("/MyEntitySet", oEntry1, { groupId: "batchCreate" });
oModel.create("/MyEntitySet", oEntry2, { groupId: "batchCreate" });
oModel.create("/MyEntitySet", oEntry3, { groupId: "batchCreate" });

// 3. Hepsini tek seferde gönder
oModel.submitChanges({
  groupId: "batchCreate",
  success: function(oData) {
    // oData.__batchResponses içinde her bir işlemin sonucu var
    var aResponses = oData.__batchResponses;
    var bHasError = aResponses.some(function(resp) {
      return resp.statusCode && parseInt(resp.statusCode, 10) >= 400;
    });
    if (bHasError) {
      MessageBox.error("Some operations failed");
    } else {
      MessageToast.show("All records created");
    }
  },
  error: function(oError) {
    this._handleODataError(oError);
  }.bind(this)
});

// 4. Batch iptal — gönderilmemiş değişiklikleri temizle
// oModel.resetChanges(undefined, undefined, "batchCreate");

// === submitChanges vs. tek işlem ===
// useBatch:true → model.create/update/remove otomatik batch'e eklenir
// submitChanges() ile gönderilir
// useBatch:false → her işlem anında gönderilir (test/debug için)
```

### OData v2 $filter — Frontend Filter Pattern

```javascript
sap.ui.define([
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function(Filter, FilterOperator) {

  // === Single Filter ===
  var oFilter = new Filter("CompanyCode", FilterOperator.EQ, "1000");

  // === Multiple Filters — AND logic ===
  var oFilterAnd = new Filter({
    filters: [
      new Filter("CompanyCode", FilterOperator.EQ, "1000"),
      new Filter("Status", FilterOperator.NE, "X"),
      new Filter("DocumentDate", FilterOperator.BT, "2024-01-01", "2024-12-31")
    ],
    and: true   // true = AND, false = OR
  });

  // === Multi-value — OR logic (same field, multiple values) ===
  var oFilterOr = new Filter({
    filters: [
      new Filter("Status", FilterOperator.EQ, "A"),
      new Filter("Status", FilterOperator.EQ, "B"),
      new Filter("Status", FilterOperator.EQ, "C")
    ],
    and: false  // OR between same-field values
  });

  // === Combined: (CompanyCode = 1000) AND (Status = A OR Status = B) ===
  var oCombined = new Filter({
    filters: [ oFilterAnd, oFilterOr ],
    and: true
  });

  // === Apply to binding ===
  // this.byId("mainTable").getBinding("items").filter(oCombined);

  // === FilterOperator reference ===
  // EQ, NE, LT, LE, GT, GE — comparison
  // BT — between (requires two values)
  // Contains, StartsWith, EndsWith — string matching
  // Any, All — lambda operators (OData v4 only, NOT v2)
});
```

### Value Help (F4) — Freestyle Pattern

```xml
<!-- View: Input with value help button -->
<Input id="inputStatus"
       value="{Status}"
       showValueHelp="true"
       valueHelpRequest=".onStatusValueHelp"
       placeholder="{i18n>selectStatus}"/>
```

```javascript
// Controller: Value Help Dialog
sap.ui.define([
  "sap/ui/comp/valuehelpdialog/ValueHelpDialog",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function(ValueHelpDialog, Filter, FilterOperator) {

  // In controller:
  onStatusValueHelp: function(oEvent) {
    var oInput = oEvent.getSource();
    var oModel = this.getView().getModel();

    // sap.ui.comp kullanılacaksa manifest.json dependencies'e ekle
    if (!this._oValueHelpDialog) {
      this._oValueHelpDialog = new ValueHelpDialog({
        title: this.getView().getModel("i18n").getResourceBundle().getText("selectStatus"),
        supportMultiselect: false,
        key: "StatusCode",
        descriptionKey: "StatusText",
        ok: function(oEvt) {
          var aTokens = oEvt.getParameter("tokens");
          if (aTokens.length > 0) {
            oInput.setValue(aTokens[0].getKey());
          }
          this._oValueHelpDialog.close();
        }.bind(this),
        cancel: function() {
          this._oValueHelpDialog.close();
        }.bind(this)
      });
    }

    // Load value help data from OData
    oModel.read("/ZVH_StatusSet", {
      success: function(oData) {
        this._oValueHelpDialog.setModel(
          new sap.ui.model.json.JSONModel({ items: oData.results }));
        this._oValueHelpDialog.getTable().bindRows("/items");
        this._oValueHelpDialog.open();
      }.bind(this),
      error: this._handleODataError.bind(this)
    });
  }
});
```

> **Alternatif (sap.ui.comp olmadan):** `sap.m.SelectDialog` veya `sap.m.TableSelectDialog` kullan — daha hafif, ek dependency gerektirmez.

### Message Handling — Message Popover Pattern

> **Kural:** Form validasyonu ve backend hata mesajlarını `MessagePopover` ile göster. Her detail/edit sayfasında bulunmalı.

```xml
<!-- View: Message popover button in footer -->
<footer>
  <OverflowToolbar>
    <ToolbarSpacer/>
    <Button id="messagePopoverBtn"
            icon="sap-icon://message-popup"
            text="{= ${message>/}.length}"
            type="{= ${message>/}.length > 0 ? 'Negative' : 'Default'}"
            press=".onMessagePopoverPress"
            visible="{= ${message>/}.length > 0}"/>
    <Button text="{i18n>save}" type="Emphasized" press=".onSave"/>
  </OverflowToolbar>
</footer>
```

```javascript
sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/m/MessagePopover",
  "sap/m/MessagePopoverItem",
  "sap/ui/core/message/Message",
  "sap/ui/core/MessageType"
], function(Controller, MessagePopover, MessagePopoverItem, Message, MessageType) {

  return Controller.extend("com.mycompany.myapp.controller.Detail", {

    onInit: function() {
      // Register message manager
      this._oMessageManager = sap.ui.getCore().getMessageManager();
      this.getView().setModel(this._oMessageManager.getMessageModel(), "message");
      this._oMessageManager.registerObject(this.getView(), true);

      // Create message popover
      this._oMessagePopover = new MessagePopover({
        items: {
          path: "message>/",
          template: new MessagePopoverItem({
            type:        "{message>type}",
            title:       "{message>message}",
            description: "{message>description}",
            subtitle:    "{message>additionalText}"
          })
        }
      });
      this.byId("messagePopoverBtn").addDependent(this._oMessagePopover);
    },

    onMessagePopoverPress: function(oEvent) {
      this._oMessagePopover.toggle(oEvent.getSource());
    },

    // Client-side validation example
    _validateForm: function() {
      this._oMessageManager.removeAllMessages();
      var bValid = true;

      var sCompanyCode = this.byId("inputBukrs").getValue();
      if (!sCompanyCode) {
        this._oMessageManager.addMessages(new Message({
          message:    this._getText("validationCompanyRequired"),
          type:       MessageType.Error,
          target:     "/CompanyCode",
          processor:  this.getView().getModel()
        }));
        bValid = false;
      }

      return bValid;
    },

    onSave: function() {
      if (!this._validateForm()) {
        this.onMessagePopoverPress({ getSource: function() {
          return this.byId("messagePopoverBtn");
        }.bind(this) });
        return;
      }
      // ... proceed with save ...
    }
  });
});
```

### i18n — Internationalization Best Practices

```properties
# i18n/i18n.properties — Default (English)
# ============================================
# Key naming convention:
#   {scope}.{element} for labels and titles
#   msg.{action}.{result} for messages
#   col.{fieldName} for table column headers
#   btn.{action} for button labels
#   placeholder.{field} for input placeholders
# ============================================

# App
appTitle=My Application
appDescription=Manage entities efficiently

# Page titles
listTitle=My Entities
detailTitle=Entity Details

# Table columns
colId=Entity ID
colDescription=Description
colStatus=Status
colAmount=Amount

# Buttons
btnCreate=Create
btnSave=Save
btnCancel=Cancel
btnDelete=Delete
btnRefresh=Refresh

# Messages — Success
msg.create.success=Record {0} created successfully
msg.update.success=Changes saved successfully
msg.delete.success={0} record(s) deleted

# Messages — Confirmation
msg.delete.confirm=Are you sure you want to delete {0} record(s)?
msg.unsavedChanges=You have unsaved changes. Do you want to discard them?

# Messages — Error
msg.error.generic=An unexpected error occurred. Please try again.
msg.error.notFound=The requested record was not found.
msg.error.authorization=You are not authorized to perform this action.

# Validation
validation.required={0} is required
validation.companyRequired=Company code is required

# Empty states
noDataTitle=No Data Available
noDataDesc=No records match your search criteria

# Placeholders
placeholder.search=Search by ID or description...
placeholder.selectStatus=Select status

# Miscellaneous
items=item(s)
```

```properties
# i18n/i18n_tr.properties — Turkish
appTitle=Uygulamam
appDescription=Varlıkları verimli yönetin

listTitle=Varlıklarım
detailTitle=Varlık Detayları

colId=Varlık No
colDescription=Açıklama
colStatus=Durum
colAmount=Tutar

btnCreate=Oluştur
btnSave=Kaydet
btnCancel=İptal
btnDelete=Sil
btnRefresh=Yenile

msg.create.success={0} kaydı başarıyla oluşturuldu
msg.update.success=Değişiklikler kaydedildi
msg.delete.success={0} kayıt silindi
msg.delete.confirm={0} kaydı silmek istediğinize emin misiniz?
msg.unsavedChanges=Kaydedilmemiş değişiklikleriniz var. İptal etmek istiyor musunuz?
msg.error.generic=Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.
msg.error.notFound=İstenen kayıt bulunamadı.
msg.error.authorization=Bu işlem için yetkiniz bulunmamaktadır.

validation.required={0} zorunludur
validation.companyRequired=Şirket kodu zorunludur

noDataTitle=Veri Bulunamadı
noDataDesc=Arama kriterlerinize uygun kayıt yok

placeholder.search=No veya açıklamaya göre ara...
placeholder.selectStatus=Durum seçin

items=kayıt
```

### UI Design Principles — Always Apply

```
1. DENSITY:       Compact mode for desktop enterprise apps (cozy for mobile)
2. FEEDBACK:      Every user action must have immediate visual feedback (busy indicator, toast)
3. EMPTY STATE:   Always implement IllustratedMessage for empty tables/lists
4. ERROR STATE:   Always show meaningful error messages — never raw technical errors
5. NAVIGATION:    Breadcrumbs on Object Page, back button always functional
6. LOADING:       Table-level busy indicator, not page-level (avoid full-screen blocking)
7. TYPOGRAPHY:    Only SAP Fiori font scale — no custom font-size in CSS
8. COLORS:        Only SAP theming variables — never hardcoded hex in CSS
9. ICONS:         Only sap-icon:// font — no external icon libraries
10. RESPONSIVE:   Test L/M/S breakpoints — Grid with L4 M6 S12 default span
```

---

### 🎨 FIORI UI/UX DESIGN EXCELLENCE — PROFESYONELLİK KILAVUZU

> **Hedef:** SAP Fiori ekranları sadece çalışan değil, **profesyonel, compact, kullanıcı dostu ve görsel olarak etkileyici** olmalı. Aşağıdaki kurallar her uygulamada uygulanmalıdır.

---

#### A. VISUAL HIERARCHY — Görsel Hiyerarşi

> **Kural:** Kullanıcı ekrana baktığında 3 saniye içinde en önemli bilgiyi bulabilmeli.

```
PRENSIP 1 — Önem Sıralaması:
  ┌─────────────────────────────────────────────────────────┐
  │  H1: Sayfa Başlığı (tek, net, anlamlı)                 │
  │  H2: Section başlıkları                                 │
  │  H3: Sub-section / Tablo başlıkları                     │
  │  Body: Form alanları, tablo hücreleri                   │
  │  Caption: Yardımcı metin, footnote                      │
  └─────────────────────────────────────────────────────────┘

PRENSIP 2 — Renk ile Vurgulama:
  - Primary action: Emphasized (mavi) → Yalnızca 1 tane per sayfa
  - Secondary action: Default (beyaz/gri)
  - Destructive action: Reject (kırmızı) → Silme, iptal işlemleri
  - Success bildirim: Positive (yeşil) → Onay, tamamlama

PRENSIP 3 — Boşluk ve Gruplama (Gestalt):
  - İlişkili alanlar grupla → FieldGroup, SimpleForm
  - Gruplar arası boşluk bırak → Section separator
  - Çok fazla bilgiyi tek seferde gösterme → Progressive disclosure
```

#### B. COMPACT & DATA-DENSE LAYOUT — Kompakt ve Yoğun Veri Gösterimi

> **Kural:** Enterprise kullanıcılar veriyi hızlı taramak ister. Fazla boşluk = verimsiz ekran.

```xml
<!-- KURAL: Desktop'ta MUTLAKA compact mode uygula -->
<!-- Component.js'de: -->
```
```javascript
// Component.js — Content Density otomatik algılama
getContentDensityClass: function() {
  if (!this._sContentDensityClass) {
    if (!sap.ui.Device.support.touch) {
      this._sContentDensityClass = "sapUiSizeCompact";   // Desktop → compact
    } else {
      this._sContentDensityClass = "sapUiSizeCozy";      // Mobil/tablet → cozy
    }
  }
  return this._sContentDensityClass;
},

init: function() {
  // Root view'a density class ekle
  this.getAggregation("rootControl").addStyleClass(this.getContentDensityClass());
}
```

**Form Layout — Compact & Profesyonel:**
```xml
<!-- ✅ DOĞRU: ResponsiveGridLayout ile profesyonel form -->
<f:SimpleForm id="generalForm"
              editable="true"
              layout="ResponsiveGridLayout"
              labelSpanXL="3" labelSpanL="3" labelSpanM="4" labelSpanS="12"
              emptySpanXL="4" emptySpanL="4" emptySpanM="0" emptySpanS="0"
              columnsXL="2" columnsL="2" columnsM="1" columnsS="1"
              adjustLabelSpan="false">
  <f:toolbar>
    <Toolbar>
      <Title text="{i18n>sectionGeneral}" level="H4"/>
    </Toolbar>
  </f:toolbar>
  <Label text="{i18n>colId}" required="true"/>
  <Input value="{EntityId}" editable="false"/>
  <Label text="{i18n>colCompany}" required="true"/>
  <Input value="{CompanyCode}" showValueHelp="true"
         valueHelpRequest=".onCompanyCodeVH"/>
  <Label text="{i18n>colDescription}"/>
  <Input value="{Description}" maxLength="40"/>
  <Label text="{i18n>colStatus}"/>
  <Select selectedKey="{Status}" forceSelection="false">
    <items>
      <core:Item key="A" text="{i18n>statusActive}"/>
      <core:Item key="B" text="{i18n>statusInProcess}"/>
      <core:Item key="E" text="{i18n>statusError}"/>
    </items>
  </Select>
</f:SimpleForm>

<!-- ❌ YANLIŞ: VerticalLayout ile dağınık form -->
<!-- Asla kullanma — hizalama bozuk olur, responsive değil -->
```

**Tablo — Column Priority ile Responsive Gizleme:**
```xml
<!-- Compact tablo: dar ekranlarda önemsiz sütunları otomatik gizle -->
<Table id="mainTable"
       items="{/MyEntitySet}"
       growing="true"
       growingThreshold="50"
       sticky="ColumnHeaders,HeaderToolbar"
       fixedLayout="Strict"
       popinLayout="GridSmall"
       alternateRowColors="true">

  <columns>
    <!-- HER ZAMAN görünsün -->
    <Column importance="High" width="8rem">
      <Text text="{i18n>colId}"/>
    </Column>
    <Column importance="High">
      <Text text="{i18n>colDescription}"/>
    </Column>

    <!-- Dar ekranda pop-in olarak göster -->
    <Column importance="Medium" minScreenWidth="Tablet"
            demandPopin="true" popinDisplay="Inline">
      <Text text="{i18n>colCompany}"/>
    </Column>

    <!-- Sadece geniş ekranda göster -->
    <Column importance="Low" minScreenWidth="Desktop"
            demandPopin="true" popinDisplay="Block">
      <Text text="{i18n>colCreatedBy}"/>
    </Column>

    <!-- Sayısal sütunlar sağa hizalı -->
    <Column importance="High" hAlign="End" width="10rem">
      <Text text="{i18n>colAmount}"/>
    </Column>

    <!-- Status sütunu -->
    <Column importance="High" hAlign="Center" width="8rem">
      <Text text="{i18n>colStatus}"/>
    </Column>
  </columns>

  <items>
    <ColumnListItem type="Navigation" press=".onItemPress"
                    highlight="{= ${Status} === 'E' ? 'Error' :
                                   ${Status} === 'B' ? 'Warning' :
                                   ${Status} === 'A' ? 'Success' : 'None'}">
      <cells>
        <ObjectIdentifier title="{EntityId}" text="{CompanyCode}"/>
        <Text text="{Description}" wrapping="false"/>
        <Text text="{CompanyCodeName}"/>
        <Text text="{CreatedBy}"/>
        <ObjectNumber number="{
            path: 'Amount',
            type: 'sap.ui.model.type.Currency',
            formatOptions: { showMeasure: false }
          }" unit="{CurrencyCode}"
          state="{= ${Amount} < 0 ? 'Error' : 'None'}"/>
        <ObjectStatus text="{StatusText}"
                      state="{= ${Status} === 'E' ? 'Error' :
                                 ${Status} === 'B' ? 'Warning' :
                                 ${Status} === 'A' ? 'Success' : 'None'}"
                      icon="{= ${Status} === 'E' ? 'sap-icon://error' :
                                ${Status} === 'B' ? 'sap-icon://alert' :
                                ${Status} === 'A' ? 'sap-icon://sys-enter-2' :
                                'sap-icon://question-mark'}"/>
      </cells>
    </ColumnListItem>
  </items>
</Table>
```

#### C. OBJECT PAGE — Profesyonel Detay Sayfası

> **Kural:** Object Page = Fiori'nin en güçlü kontrolü. Doğru kullanıldığında 10x daha profesyonel görünür.

```xml
<!-- Object Page — KPI'lı Header + Organize Bölümler -->
<ObjectPageLayout id="objectPage"
                  showTitleInHeaderContent="false"
                  useIconTabBar="true"
                  upperCaseAnchorBar="false"
                  enableLazyLoading="true">

  <!-- === HEADER TITLE === -->
  <headerTitle>
    <ObjectPageDynamicHeaderTitle>
      <heading>
        <HBox alignItems="Center">
          <Avatar src="sap-icon://document" displaySize="S"
                  backgroundColor="Accent6" class="sapUiSmallMarginEnd"/>
          <Title text="{Description}" level="H2" wrapping="true"/>
        </HBox>
      </heading>
      <snappedHeading>
        <FlexBox alignItems="Center">
          <Avatar src="sap-icon://document" displaySize="XS"
                  backgroundColor="Accent6" class="sapUiSmallMarginEnd"/>
          <Title text="{Description}" level="H3"/>
        </FlexBox>
      </snappedHeading>
      <expandedContent>
        <Label text="{i18n>lblEntityId}: {EntityId}"/>
      </expandedContent>
      <snappedContent>
        <Label text="{EntityId}"/>
      </snappedContent>
      <breadcrumbs>
        <Breadcrumbs>
          <Link text="{i18n>listTitle}" press=".onNavBack"/>
        </Breadcrumbs>
      </breadcrumbs>
      <actions>
        <Button text="{i18n>btnEdit}" type="Emphasized" press=".onEdit"
                visible="{= !${detailModel>/editMode}}"/>
        <Button text="{i18n>btnSave}" type="Emphasized" press=".onSave"
                visible="{detailModel>/editMode}"/>
        <Button text="{i18n>btnCancel}" press=".onCancel"
                visible="{detailModel>/editMode}"/>
        <Button icon="sap-icon://action" type="Ghost" press=".onMoreActions"/>
      </actions>
    </ObjectPageDynamicHeaderTitle>
  </headerTitle>

  <!-- === HEADER CONTENT — KPI Kartları === -->
  <headerContent>
    <FlexBox wrap="Wrap" class="sapUiSmallMarginBeginEnd">
      <!-- KPI 1: Toplam Tutar -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="10rem">
        <ObjectAttribute title="{i18n>colAmount}"/>
        <ObjectNumber number="{
            path: 'Amount',
            type: 'sap.ui.model.type.Currency',
            formatOptions: { showMeasure: false }
          }" unit="{CurrencyCode}" emphasized="true"
          state="{= ${Amount} > 10000 ? 'Success' : 'None'}"/>
      </m:VBox>
      <!-- KPI 2: Durum -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="10rem">
        <ObjectAttribute title="{i18n>colStatus}"/>
        <ObjectStatus text="{StatusText}" state="{StatusState}"
                      icon="{StatusIcon}" inverted="true"/>
      </m:VBox>
      <!-- KPI 3: Oluşturma Tarihi -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="10rem">
        <ObjectAttribute title="{i18n>lblCreatedAt}"/>
        <Text text="{
            path: 'CreatedAt',
            type: 'sap.ui.model.type.Date',
            formatOptions: { style: 'medium' }
          }"/>
      </m:VBox>
      <!-- KPI 4: Progress Indicator (opsiyonel) -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="14rem">
        <ObjectAttribute title="{i18n>lblProgress}"/>
        <ProgressIndicator percentValue="{Progress}"
                           displayValue="{= ${Progress} + '%'}"
                           state="{= ${Progress} >= 80 ? 'Success' :
                                      ${Progress} >= 50 ? 'Warning' : 'Error'}"
                           showValue="true"/>
      </m:VBox>
    </FlexBox>
  </headerContent>

  <!-- === SECTIONS — IconTabBar ile gruplandırma === -->
  <sections>
    <!-- Section 1: Genel Bilgiler -->
    <ObjectPageSection id="sectionGeneral" title="{i18n>sectionGeneral}">
      <subSections>
        <ObjectPageSubSection title="{i18n>subSectionBasic}">
          <blocks>
            <!-- SimpleForm burada (yukarıdaki form pattern) -->
          </blocks>
        </ObjectPageSubSection>
      </subSections>
    </ObjectPageSection>

    <!-- Section 2: Kalemler (Table) -->
    <ObjectPageSection id="sectionItems" title="{i18n>sectionItems}">
      <subSections>
        <ObjectPageSubSection>
          <blocks>
            <!-- Item tablosu burada -->
          </blocks>
        </ObjectPageSubSection>
      </subSections>
    </ObjectPageSection>

    <!-- Section 3: Notlar / Ekler -->
    <ObjectPageSection id="sectionNotes" title="{i18n>sectionNotes}">
      <subSections>
        <ObjectPageSubSection>
          <blocks>
            <FeedInput post=".onAddNote" placeholder="{i18n>addNote}" growing="true"/>
            <!-- Timeline veya Feed List burada -->
          </blocks>
        </ObjectPageSubSection>
      </subSections>
    </ObjectPageSection>
  </sections>
</ObjectPageLayout>
```

#### D. SMART CONTROLS — Daha Az Kod, Daha Profesyonel

> **Ne zaman kullan:** OData metadata (annotation) ile sürülen standart CRUD ekranlarında. Manuel tablo/filtre yazmaktan çok daha hızlı ve tutarlı.

```xml
<!-- SmartFilterBar + SmartTable kombinasyonu — en profesyonel list view -->
<!-- Gerekli dependency: manifest.json → sap.ui5.dependencies.libs → "sap.ui.comp": {} -->
<smartFilterBar:SmartFilterBar id="smartFilter"
    entitySet="MyEntitySet"
    persistencyKey="MyAppSmartFilter"
    showFilterConfiguration="true"
    useProvidedNavigationProperties="false"
    liveMode="false">
  <smartFilterBar:controlConfiguration>
    <!-- Status alanı için multi-select combobox -->
    <smartFilterBar:ControlConfiguration key="Status"
        visibleInAdvancedArea="true"
        preventInitialDataFetchInValueHelpDialog="false"
        controlType="dropDownList"/>
    <!-- Tarih alanı için DateRangeSelection -->
    <smartFilterBar:ControlConfiguration key="DocumentDate"
        conditionType="sap.ui.comp.config.condition.DateRangeType"/>
  </smartFilterBar:controlConfiguration>
</smartFilterBar:SmartFilterBar>

<smartTable:SmartTable id="smartTable"
    entitySet="MyEntitySet"
    smartFilterId="smartFilter"
    tableType="ResponsiveTable"
    header="{i18n>listTitle}"
    showRowCount="true"
    showFullScreenButton="true"
    enableExport="true"
    enableAutoBinding="true"
    demandPopin="true"
    useVariantManagement="true"
    useTablePersonalisation="true"
    persistencyKey="MyAppSmartTable"
    editTogglable="false"
    requestAtLeastFields="EntityId,Status"
    ignoredFields="StatusCriticality"
    initiallyVisibleFields="EntityId,CompanyCode,Description,Status,Amount">

  <smartTable:customToolbar>
    <OverflowToolbar design="Transparent">
      <ToolbarSpacer/>
      <Button icon="sap-icon://add" text="{i18n>btnCreate}"
              type="Emphasized" press=".onCreatePress"/>
      <Button icon="sap-icon://delete" text="{i18n>btnDelete}"
              type="Reject" press=".onDeletePress"
              enabled="{detailModel>/hasSelection}"/>
    </OverflowToolbar>
  </smartTable:customToolbar>
</smartTable:SmartTable>
```

**SmartTable vs Manual Table — Karar Matrisi:**
```
┌─────────────────────────┬──────────────┬──────────────┐
│ Özellik                 │ SmartTable   │ Manual Table │
├─────────────────────────┼──────────────┼──────────────┤
│ Sütun otomatik algılama │ ✅ Evet      │ ❌ Manuel    │
│ Sıralama/Filtreleme     │ ✅ Otomatik  │ ❌ Manuel    │
│ Excel Export             │ ✅ Built-in  │ ❌ Manuel    │
│ Kişiselleştirme (P13n)  │ ✅ Built-in  │ ❌ Yok       │
│ Variant Management      │ ✅ Built-in  │ ❌ Yok       │
│ Custom cell rendering   │ ⚠️ Sınırlı   │ ✅ Tam       │
│ Karmaşık interaction    │ ⚠️ Extension │ ✅ Tam       │
│ Boyut                   │ 🔴 Ağır      │ 🟢 Hafif     │
│ Geliştirme hızı         │ 🟢 Hızlı     │ 🔴 Yavaş     │
└─────────────────────────┴──────────────┴──────────────┘

KARAR: Standart CRUD = SmartTable. Custom interaction = Manual Table.
```

#### E. STATUS GÖSTERİMİ — Semantic Colors & Icons

> **Kural:** Status alanlarını asla düz text olarak gösterme. Renk + ikon + state kombinasyonu kullan.

```javascript
// Controller — Status'tan görsel state hesaplama
_formatStatusState: function(sStatus) {
  var mStates = {
    "01": "Success",    // Onaylı → Yeşil
    "02": "Warning",    // Beklemede → Turuncu
    "03": "Error",      // Reddedildi → Kırmızı
    "04": "Information", // Bilgi → Mavi
    "05": "None"        // Taslak → Gri
  };
  return mStates[sStatus] || "None";
},

_formatStatusIcon: function(sStatus) {
  var mIcons = {
    "01": "sap-icon://sys-enter-2",      // ✓ Yeşil check
    "02": "sap-icon://pending",           // ⏳ Bekleme
    "03": "sap-icon://decline",           // ✕ Red
    "04": "sap-icon://information",       // ℹ Bilgi
    "05": "sap-icon://document"           // 📄 Taslak
  };
  return mIcons[sStatus] || "sap-icon://question-mark";
}
```

```xml
<!-- View'da kullanım — 3 farklı status gösterim seviyesi -->

<!-- Seviye 1: Basit (sadece renk + text) -->
<ObjectStatus text="{StatusText}"
              state="{path: 'Status', formatter: '.formatter.formatStatusState'}"/>

<!-- Seviye 2: Orta (renk + text + ikon) -->
<ObjectStatus text="{StatusText}"
              state="{path: 'Status', formatter: '.formatter.formatStatusState'}"
              icon="{path: 'Status', formatter: '.formatter.formatStatusIcon'}"/>

<!-- Seviye 3: Vurgulu (inverted — dolu arka plan) — header KPI için -->
<ObjectStatus text="{StatusText}"
              state="{path: 'Status', formatter: '.formatter.formatStatusState'}"
              icon="{path: 'Status', formatter: '.formatter.formatStatusIcon'}"
              inverted="true"/>

<!-- Row Highlighting — tablo satırlarını status'a göre renklendir -->
<ColumnListItem highlight="{path: 'Status',
                            formatter: '.formatter.formatStatusState'}">
```

#### F. MICRO-INTERACTIONS & LOADING UX

> **Kural:** Kullanıcı herhangi bir aksiyon aldığında anında görsel geri bildirim olmalı. "Hiçbir şey olmuyor" hissi = kötü UX.

```javascript
// 1. Skeleton Loading — ilk yüklemede busy indicator yerine
onInit: function() {
  // Sayfayı açarken tablo shimmer/skeleton göstersin
  this.byId("mainTable").setBusyIndicatorDelay(0);  // Anında busy göster
  this.byId("mainTable").setBusy(true);
},

// 2. Inline Action Feedback — buton basıldığında
onApprove: function(oEvent) {
  var oButton = oEvent.getSource();
  oButton.setBusy(true);  // Butonu busy yap (tıklanamaz)

  this._callFunctionImport("Approve", { EntityId: sId })
    .then(function() {
      oButton.setBusy(false);
      MessageToast.show(this._getText("msg.approve.success"));
      this.getView().getModel().refresh();  // Tabloyu yenile
    }.bind(this))
    .catch(function(oError) {
      oButton.setBusy(false);
      this._handleODataError(oError);
    }.bind(this));
},

// 3. Optimistic UI — silme işleminde anında tablodan kaldır
onDeleteItem: function(oEvent) {
  var oItem = oEvent.getParameter("listItem");
  var sPath = oItem.getBindingContext().getPath();

  // Önce UI'dan kaldır (hızlı feedback)
  oItem.setVisible(false);

  // Sonra backend'e gönder
  this.getView().getModel().remove(sPath, {
    success: function() {
      MessageToast.show(this._getText("msg.delete.success"));
    }.bind(this),
    error: function(oError) {
      oItem.setVisible(true);  // Hata varsa geri göster
      this._handleODataError(oError);
    }.bind(this)
  });
},

// 4. Smooth Navigation — routing transition
// manifest.json → routing.config.transition: "slide"  (zaten var)

// 5. Success Animation — kaydettikten sonra kısa yeşil flash
onSaveSuccess: function() {
  // Header'a geçici success strip ekle
  var oStrip = new sap.m.MessageStrip({
    text: this._getText("msg.update.success"),
    type: "Success",
    showCloseButton: true,
    showIcon: true
  });
  this.byId("objectPage").getHeaderContent()[0].insertItem(oStrip, 0);

  // 3 saniye sonra otomatik kaldır
  setTimeout(function() {
    oStrip.destroy();
  }, 3000);
}
```

#### G. THEMING & VISUAL POLISH — SAP Horizon

> **Kural:** SAP Horizon (Morning/Evening) tema desteği = modern ve profesyonel görünüm. Asla hardcoded renk kullanma, her zaman CSS variable kullan.

```css
/* custom.css — SAP Theming Variables ile özelleştirme */
/* Bu değerler tema değiştiğinde otomatik uyum sağlar */

/* ✅ DOĞRU: Tema değişkenleri kullan */
.myApp .sapMListTblCell {
  border-bottom: 1px solid var(--sapList_BorderColor);
}

.myApp .highlightCard {
  background: var(--sapTile_Background);
  border: 1px solid var(--sapTile_BorderColor);
  border-radius: var(--sapElement_BorderCornerRadius);
  box-shadow: var(--sapContent_Shadow0);
  padding: 1rem;
}

.myApp .highlightCard:hover {
  box-shadow: var(--sapContent_Shadow1);
  transition: box-shadow 0.2s ease-in-out;
}

/* KPI Kartları — header'da kompakt görünüm */
.myApp .kpiCard {
  background: var(--sapTile_Background);
  border-radius: var(--sapElement_BorderCornerRadius);
  padding: 0.75rem 1rem;
  min-width: 8rem;
  border-left: 3px solid var(--sapBrandColor);
}

/* Status badge — inverted olmayan durumlarda custom */
.myApp .statusBadge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: var(--sapFontSmallSize);
}

/* ❌ YANLIŞ: Hardcoded renk kullanma */
/* .myBadge { background: #2196F3; color: white; }  → ASLA! */

/* Sık kullanılan SAP Theming variable'ları: */
/*
  --sapBrandColor              → Ana marka rengi (genelde mavi)
  --sapHighlightColor          → Vurgu rengi
  --sapPositiveColor           → Başarı (yeşil)
  --sapNegativeColor           → Hata (kırmızı)
  --sapCriticalColor           → Uyarı (turuncu)
  --sapInformativeColor        → Bilgi (mavi)
  --sapNeutralColor            → Nötr (gri)
  --sapBackgroundColor         → Sayfa arka planı
  --sapShellColor              → Shell arka planı
  --sapTile_Background         → Kart/tile arka planı
  --sapList_Background         → Liste arka planı
  --sapList_AlternatingBackground → Alternatif satır rengi
  --sapList_SelectionBackgroundColor → Seçili satır
  --sapContent_Shadow0..3      → Gölge seviyeleri
  --sapFontFamily              → Font family
  --sapFontSize                → Normal font boyutu
  --sapFontSmallSize           → Küçük font
  --sapFontLargeSize           → Büyük font
  --sapFontHeader1..6Size      → Başlık fontları
  --sapElement_BorderCornerRadius → Border radius
*/
```

**Horizon Tema Ayarı — Launchpad'de:**
```
FLP → Ayarlar → Görünüm:
  - "SAP Morning Horizon" → Açık tema (kurumsal, profesyonel)
  - "SAP Evening Horizon"  → Koyu tema (göz yorgunluğu azaltır)
  - "SAP Quartz Light/Dark" → Fiori 3.0 klasik

manifest.json'da tema bağımsız geliştirme yapıyorsan:
  → Asla hardcoded renk kullanma
  → var(--sapXxx) kullan
  → Tema değiştiğinde otomatik uyum sağlar
```

#### H. TABLO TASARIM PATTERNLERİ — İleri Seviye

```xml
<!-- Pattern 1: Grouped Header — Alt başlıklı tablo -->
<Table id="groupedTable" items="{
    path: '/MyEntitySet',
    sorter: { path: 'CompanyCode', group: true }
  }">
  <!-- GroupHeaderListItem otomatik render edilir -->
</Table>

<!-- Pattern 2: Inline Actions — Satır içi butonlar -->
<ColumnListItem>
  <cells>
    <!-- ... data cells ... -->
    <HBox justifyContent="End">
      <Button icon="sap-icon://edit" type="Ghost" press=".onEditRow"
              tooltip="{i18n>tooltipEdit}" class="sapUiTinyMarginEnd"/>
      <Button icon="sap-icon://copy" type="Ghost" press=".onCopyRow"
              tooltip="{i18n>tooltipCopy}"/>
    </HBox>
  </cells>
</ColumnListItem>

<!-- Pattern 3: Conditional Formatting — Koşullu biçimlendirme -->
<ObjectNumber number="{Amount}" unit="{CurrencyCode}"
              state="{= ${Amount} > 50000 ? 'Success' :
                         ${Amount} > 10000 ? 'Warning' : 'Error'}"
              emphasized="{= ${Amount} > 100000}"/>

<!-- Pattern 4: Multi-line Cell — Kompakt çok satırlı hücre -->
<VBox>
  <Text text="{Description}" wrapping="false" maxLines="1"/>
  <Label text="{= ${Category} + ' | ' + ${Subcategory}}"
         design="Light" wrapping="false"/>
</VBox>

<!-- Pattern 5: Selection + Bulk Actions -->
<Table mode="MultiSelect" selectionChange=".onSelectionChange">
  <headerToolbar>
    <OverflowToolbar>
      <Title text="{i18n>listTitle}" level="H3"/>
      <ToolbarSpacer/>
      <!-- Bulk action bar — seçim olduğunda görünür -->
      <Button text="{i18n>btnApproveSelected}" type="Accept"
              visible="{detailModel>/hasSelection}" press=".onBulkApprove"
              icon="sap-icon://accept"/>
      <Button text="{i18n>btnRejectSelected}" type="Reject"
              visible="{detailModel>/hasSelection}" press=".onBulkReject"
              icon="sap-icon://decline"/>
      <ToolbarSeparator visible="{detailModel>/hasSelection}"/>
      <Label text="{= ${detailModel>/selectionCount} + ' ' + ${i18n>selected}}"
             visible="{detailModel>/hasSelection}" design="Bold"/>
    </OverflowToolbar>
  </headerToolbar>
</Table>
```

```javascript
// Tablo seçim yönetimi
onSelectionChange: function(oEvent) {
  var oTable = oEvent.getSource();
  var iCount = oTable.getSelectedItems().length;
  var oModel = this.getView().getModel("detailModel");
  oModel.setProperty("/selectionCount", iCount);
  oModel.setProperty("/hasSelection", iCount > 0);
}
```

#### I. FILTER BAR — Profesyonel Filtreleme

```xml
<!-- DynamicPage Header ile entegre filtre alanları -->
<f:DynamicPageHeader pinnable="true">
  <l:Grid defaultSpan="L3 M4 S6" hSpacing="1" vSpacing="0" class="sapUiSmallMarginTop">

    <!-- Tarih Aralığı — en sık kullanılan filtre tipi -->
    <DateRangeSelection id="filterDateRange"
                        placeholder="{i18n>filterDateRange}"
                        change=".onFilterChange"
                        dateValue="{filterModel>/dateFrom}"
                        secondDateValue="{filterModel>/dateTo}"/>

    <!-- MultiComboBox — çoklu değer seçimi -->
    <MultiComboBox id="filterStatus"
                   placeholder="{i18n>filterStatus}"
                   selectionChange=".onFilterChange"
                   items="{statusModel>/statuses}">
      <core:Item key="{statusModel>key}" text="{statusModel>text}"/>
    </MultiComboBox>

    <!-- ComboBox — tekli seçim -->
    <ComboBox id="filterCompany"
              placeholder="{i18n>filterCompany}"
              selectionChange=".onFilterChange"
              showSecondaryValues="true"
              items="{/CompanyCodeSet}">
      <core:ListItem key="{CompanyCode}" text="{CompanyCode}"
                     additionalText="{CompanyCodeName}"/>
    </ComboBox>

    <!-- Search Field — tam genişlik -->
    <SearchField id="filterSearch"
                 placeholder="{i18n>searchPlaceholder}"
                 search=".onSearch"
                 width="100%"/>

    <!-- Filtre sayacı + temizle butonu -->
    <HBox justifyContent="End" alignItems="Center">
      <Label text="{= ${filterModel>/activeFilterCount} + ' ' + ${i18n>activeFilters}}"
             visible="{= ${filterModel>/activeFilterCount} > 0}"
             class="sapUiSmallMarginEnd"/>
      <Button text="{i18n>clearFilters}" press=".onClearFilters"
              type="Ghost" icon="sap-icon://clear-filter"
              visible="{= ${filterModel>/activeFilterCount} > 0}"/>
    </HBox>
  </l:Grid>
</f:DynamicPageHeader>
```

#### J. ACCESSIBILITY & KEYBOARD NAVIGATION

> **Kural:** Erişilebilirlik isteğe bağlı değil, zorunludur. Özellikle ARIA labeller ve keyboard shortcut'lar.

```xml
<!-- Her interaktif elemente anlamlı label/tooltip ekle -->
<Button icon="sap-icon://delete" press=".onDelete"
        ariaLabelledBy="deleteLabel"
        tooltip="{i18n>tooltipDelete}"/>
<InvisibleText id="deleteLabel" text="{i18n>ariaDeleteRecord}"/>

<!-- Form alanlarında label association -->
<Label text="{i18n>colCompany}" labelFor="inputCompany" required="true"/>
<Input id="inputCompany" value="{CompanyCode}"/>

<!-- Tablo boş durum — screen reader için -->
<IllustratedMessage illustrationType="sapIllus-EmptyList"
                    title="{i18n>noDataTitle}"
                    description="{i18n>noDataDesc}"
                    ariaLabelledBy="emptyTableLabel"/>
```

```javascript
// Keyboard navigation — Ctrl+S ile kaydet
onInit: function() {
  // Global keyboard shortcut
  $(document).on("keydown.myapp", function(e) {
    if (e.ctrlKey && e.key === "s") {
      e.preventDefault();
      this.onSave();
    }
    if (e.key === "Escape" && this._isEditMode()) {
      this.onCancel();
    }
  }.bind(this));
},

onExit: function() {
  // Cleanup
  $(document).off("keydown.myapp");
}
```

#### K. TASARIM KALİTE CHECKLIST — Her Geliştirmede Kontrol Et

```
╔══════════════════════════════════════════════════════════════════╗
║                    FIORI UI KALİTE CHECKLIST                   ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  LAYOUT & DENSITY                                               ║
║  □ Compact mode desktop'ta aktif mi?                            ║
║  □ SimpleForm ResponsiveGridLayout kullanıyor mu?               ║
║  □ Tablo sütunları sağ/sol hizalı (sayılar sağda) mı?          ║
║  □ Column importance ve demandPopin ayarlandı mı?               ║
║  □ Sticky column headers aktif mi?                              ║
║                                                                 ║
║  GÖRSEL KALİTE                                                  ║
║  □ Status alanları renk + ikon ile gösteriliyor mu?             ║
║  □ Row highlighting status'a göre aktif mi?                     ║
║  □ Object Page header'da KPI kartları var mı?                   ║
║  □ Breadcrumbs ve back navigation çalışıyor mu?                 ║
║  □ Avatar/ikon kullanımı başlıklarda var mı?                    ║
║  □ alternateRowColors tablo okunabilirliği artırıyor mu?        ║
║                                                                 ║
║  FEEDBACK & INTERACTION                                         ║
║  □ Her buton tıklamada busy feedback var mı?                    ║
║  □ Save/delete sonrası MessageToast gösteriliyor mu?            ║
║  □ Boş tablo durumunda IllustratedMessage var mı?               ║
║  □ Validation hataları MessagePopover ile gösteriliyor mu?      ║
║  □ Unsaved changes uyarısı var mı? (navigation guard)           ║
║                                                                 ║
║  RESPONSIVE                                                     ║
║  □ L/M/S breakpoint'larda düzgün görünüyor mu?                  ║
║  □ Mobilde cozy, desktop'ta compact çalışıyor mu?               ║
║  □ Tablo sütunları dar ekranda pop-in oluyor mu?                ║
║                                                                 ║
║  THEMING                                                        ║
║  □ Hardcoded renk (hex/rgb) var mı? → OLMAMALI                 ║
║  □ var(--sapXxx) kullanılıyor mu? → OLMALI                     ║
║  □ Morning/Evening Horizon'da test edildi mi?                   ║
║                                                                 ║
║  ACCESSIBILITY                                                  ║
║  □ Tüm buton/ikon'larda tooltip var mı?                        ║
║  □ Form label-input association doğru mu?                       ║
║  □ InvisibleText ile ARIA label eklenmiş mi?                    ║
║  □ Keyboard navigation (Tab, Enter, Escape) çalışıyor mu?      ║
║                                                                 ║
║  DATA QUALITY                                                   ║
║  □ Tabloda max 6-8 görünür sütun var mı? (fazlası P13n'de)     ║
║  □ Teknik alanlar (GUID, internal code) gizlenmiş mi?           ║
║  □ Raw status kodları (A/B/X) yerine text gösteriliyor mu?      ║
║  □ Tüm label'lar i18n'den geliyor mu? (hardcoded yok)           ║
║                                                                 ║
║  CONSISTENCY                                                     ║
║  □ Aynı entity → her yerde aynı layout mu?                      ║
║  □ Aynı action → her yerde aynı pozisyonda mı?                  ║
║  □ Quick filter (segmented/tab) list sayfalarında var mı?       ║
║  □ Empty state'de CTA (Create) butonu var mı?                   ║
║                                                                 ║
╚══════════════════════════════════════════════════════════════════╝
```

#### L. MANDATORY UX RULES — ZORUNLU UX KURALLARI

> **Kural:** Aşağıdaki kurallar her Fiori uygulamasında **istisnasız** uygulanmalıdır.

**1. Quick Filters — Liste Sayfalarında Hızlı Filtreleme:**
```xml
<!-- IconTabBar ile quick filter — status bazlı hızlı geçiş -->
<IconTabBar id="quickFilter" select=".onQuickFilterSelect"
            headerMode="Inline" stretchContentHeight="true"
            expandable="false">
  <items>
    <IconTabFilter text="{i18n>filterAll}" key="All"
                   count="{filterModel>/countAll}" showAll="true"/>
    <IconTabSeparator/>
    <IconTabFilter text="{i18n>filterActive}" key="A"
                   count="{filterModel>/countActive}"
                   iconColor="Positive" icon="sap-icon://sys-enter-2"/>
    <IconTabFilter text="{i18n>filterPending}" key="B"
                   count="{filterModel>/countPending}"
                   iconColor="Critical" icon="sap-icon://pending"/>
    <IconTabFilter text="{i18n>filterError}" key="E"
                   count="{filterModel>/countError}"
                   iconColor="Negative" icon="sap-icon://error"/>
  </items>
  <content>
    <!-- Tablo burada -->
  </content>
</IconTabBar>

<!-- Alternatif: SegmentedButton ile quick filter -->
<SegmentedButton id="segQuickFilter" select=".onQuickFilterSelect"
                 selectedKey="All">
  <items>
    <SegmentedButtonItem text="{i18n>filterAll}" key="All"/>
    <SegmentedButtonItem text="{i18n>filterActive}" key="A"/>
    <SegmentedButtonItem text="{i18n>filterPending}" key="B"/>
    <SegmentedButtonItem text="{i18n>filterError}" key="E"/>
  </items>
</SegmentedButton>
```

```javascript
// Quick filter controller logic
onQuickFilterSelect: function(oEvent) {
  var sKey = oEvent.getParameter("key") || oEvent.getParameter("item").getKey();
  var oTable = this.byId("mainTable");
  var oBinding = oTable.getBinding("items");
  var aFilters = [];

  if (sKey !== "All") {
    aFilters.push(new Filter("Status", FilterOperator.EQ, sKey));
  }

  // Mevcut search filtrelerini koru
  var sSearchQuery = this.byId("filterSearch").getValue();
  if (sSearchQuery) {
    aFilters.push(new Filter("Description", FilterOperator.Contains, sSearchQuery));
  }

  oBinding.filter(aFilters.length > 0
    ? new Filter({ filters: aFilters, and: true })
    : []);
}
```

**2. Tablo Sütun Kuralı — Max 6-8 Görünür Sütun:**
```
┌──────────────────────────────────────────────────────────────┐
│ TABLO SÜTUN SIRASI KURALI                                    │
│                                                              │
│ 1. Identifier (ID / numara) → ilk sütun, HER ZAMAN görünür  │
│ 2. Primary info (açıklama, isim) → importance: High          │
│ 3. Status → importance: High, sağa veya ortaya hizalı       │
│ 4. Key metric (tutar, miktar) → importance: High, sağ hiza  │
│ 5. Secondary info (tarih, oluşturan) → importance: Medium    │
│ 6. Tertiary info (notlar, kategori) → importance: Low        │
│                                                              │
│ İLK AÇILIŞTA max 6-8 sütun göster.                           │
│ Kalan sütunlar P13n (Table Personalization) ile erişilebilir.│
│ SmartTable: initiallyVisibleFields ile kontrol et.           │
│ Manual Table: Column importance + minScreenWidth kullan.     │
└──────────────────────────────────────────────────────────────┘
```

**3. Raw Kod Gösterme Yasağı — Her Zaman Okunabilir Metin:**
```javascript
// ❌ YANLIŞ: Raw kodu tabloda gösterme
// Status: "A"      → Kullanıcı A'nın ne olduğunu bilmez
// CompanyCode: "1000"  → Yanına text de göster

// ✅ DOĞRU: Formatter ile okunabilir metin
formatter: {
  formatStatusText: function(sStatus) {
    var oBundle = this.getView().getModel("i18n").getResourceBundle();
    var mTexts = {
      "A":  oBundle.getText("statusActive"),      // "Aktif"
      "B":  oBundle.getText("statusInProcess"),    // "İşlemde"
      "E":  oBundle.getText("statusError"),        // "Hatalı"
      "X":  oBundle.getText("statusDeleted")       // "Silinmiş"
    };
    return mTexts[sStatus] || sStatus;
  }
}
```

```xml
<!-- View'da: ObjectIdentifier ile hem kod hem text göster -->
<ObjectIdentifier title="{CompanyCode}" text="{CompanyCodeName}"/>

<!-- Veya sadece text, kodu tooltip'te göster -->
<Text text="{StatusText}" tooltip="{= 'Code: ' + ${Status}}"/>
```

**4. Empty State — CTA (Call-to-Action) ile Yönlendirici Boş Durum:**
```xml
<!-- ❌ YANLIŞ: Sadece "Veri yok" yazan boş tablo -->
<Table noDataText="No data"/>

<!-- ✅ DOĞRU: İllüstrasyon + açıklama + CTA butonu -->
<IllustratedMessage id="emptyState"
                    illustrationType="sapIllus-EmptyList"
                    title="{i18n>noDataTitle}"
                    description="{i18n>noDataDesc}"
                    visible="{= ${listModel>/totalCount} === 0}">
  <additionalContent>
    <Button text="{i18n>btnCreateFirst}" type="Emphasized"
            press=".onCreatePress" icon="sap-icon://add"/>
  </additionalContent>
</IllustratedMessage>

<!-- Filtered empty state — filtre sonucu boş -->
<IllustratedMessage id="emptyFilterState"
                    illustrationType="sapIllus-NoFilterResults"
                    title="{i18n>noFilterResultsTitle}"
                    description="{i18n>noFilterResultsDesc}"
                    visible="{= ${listModel>/isFiltered} && ${listModel>/totalCount} === 0}">
  <additionalContent>
    <Button text="{i18n>clearFilters}" press=".onClearFilters"
            icon="sap-icon://clear-filter"/>
  </additionalContent>
</IllustratedMessage>
```

**5. Inline Edit Pattern — Satır İçi Düzenleme:**

> [!WARNING]
> SAP backend **pessimistic locking (ENQUEUE_...)** kullandığı için, çoklu satırları `inline edit` moduna açmak, diğer kullanıcıların işlemlerini kilitleyebilir (lock error). 
> **NE ZAMAN KULLANILMALI:** Sadece basit master-data tablolarında veya `BOPF Draft Framework` aktif ise. Diğer durumlarda klasik `Object Page -> Edit` navigasyonunu tercih et.

```xml
<!-- Tablo içinde editable/display mode toggle -->
<ColumnListItem>
  <cells>
    <ObjectIdentifier title="{EntityId}"/>
    <!-- Display mode: Text, Edit mode: Input -->
    <Input value="{Description}"
           editable="{detailModel>/editMode}"
           class="{= ${detailModel>/editMode} ? '' : 'sapUiSizeCompact'}"/>
    <!-- Display mode: ObjectStatus, Edit mode: Select -->
    <Select selectedKey="{Status}"
            enabled="{detailModel>/editMode}"
            forceSelection="false"
            visible="{detailModel>/editMode}">
      <items>
        <core:Item key="A" text="{i18n>statusActive}"/>
        <core:Item key="B" text="{i18n>statusInProcess}"/>
      </items>
    </Select>
    <ObjectStatus text="{StatusText}" state="{StatusState}"
                  visible="{= !${detailModel>/editMode}}"/>
    <!-- Editable amount field -->
    <Input value="{Amount}" type="Number"
           editable="{detailModel>/editMode}"/>
  </cells>
</ColumnListItem>
```

**6. Complex Forms — Wizard & Typeahead Kullanımı:**

> **Kural:** Uzun formlar kullanıcıyı bunaltır. Çok fazla alan varsa "Progressive Disclosure" (adım adım gösterme) için Wizard kullan. Eski F4 yardım menüleri yerine her zaman hızlı `Typeahead (Suggestion)` kullan.

```xml
<!-- ✅ DOĞRU: Karmaşık yaratma ekranları için Wizard -->
<Wizard id="createWizard" complete="wizardCompletedHandler">
  <WizardStep id="ProductInfoStep"
              title="{i18n>stepProductInfo}"
              validated="true">
    <MessageStrip text="{i18n>msgProductInfoDesc}" showIcon="true"/>
    <!-- Form alanları -->
  </WizardStep>

  <WizardStep id="PricingStep"
              title="{i18n>stepPricing}"
              validated="false">
    <!-- Adım 2 alanları -->
  </WizardStep>
</Wizard>

<!-- ✅ DOĞRU: Kullanıcı dostu Typeahead/Suggestion input -->
<Input id="inputCompany"
       placeholder="{i18n>placeholderCompany}"
       showSuggestion="true"
       suggestionItems="{/CompanyCodeSet}"
       suggestionItemSelected=".onCompanySelect">
  <suggestionItems>
    <core:ListItem key="{CompanyCode}"
                   text="{CompanyCode}"
                   additionalText="{CompanyCodeName}"/>
  </suggestionItems>
</Input>
```

**7. NEVER LIST — Anti-Pattern Kuralları:**
```
╔══════════════════════════════════════════════════════════════════╗
║                     ❌ ASLA YAPMA LİSTESİ                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  1. UI'ı bilgiyle BOĞMA                                         ║
║     → Max 6-8 sütun, geri kalanı P13n ile erişilebilir          ║
║     → Progressive disclosure: detay bilgiyi Object Page'e at    ║
║                                                                 ║
║  2. TEKNİK ALAN gösterme                                        ║
║     → GUID, MANDT, internal code, timestamp raw format          ║
║     → Kullanıcı görmemeli, sadece frontend model'de tutulmalı   ║
║                                                                 ║
║  3. i18n OLMADAN label kullanma                                  ║
║     → "Company Code" yerine {i18n>colCompany}                   ║
║     → Hardcoded text = çeviri yapılamaz, tutarsızlık oluşur     ║
║                                                                 ║
║  4. RAW STATUS KODU gösterme                                     ║
║     → "A" yerine "Aktif", "01" yerine "Onaylandı"              ║
║     → Formatter + i18n ile her zaman okunabilir metin           ║
║                                                                 ║
║  5. TÜM SAYFAYI busy yapma                                      ║
║     → Sadece etkilenen bileşeni busy yap (tablo, buton)         ║
║     → BusyDialog sadece kritik engelleme durumlarında           ║
║                                                                 ║
║  6. TUTARSIZ layout kullanma                                     ║
║     → Aynı entity = aynı sütun sırası, aynı renk kodlaması     ║
║     → Aynı aksiyon = aynı pozisyon (Create sağ üst, Delete sol)║
║     → Aynı status = aynı renk (yeşil=başarı her yerde)         ║
║                                                                 ║
║  7. CTA OLMADAN boş durum gösterme                               ║
║     → "Veri yok" tek başına yetmez                              ║
║     → "Oluştur" butonu veya filtre temizleme önerisi ekle       ║
║                                                                 ║
║  8. Filtre alanı OLMADAN liste sayfası yapma                     ║
║     → Quick filter (tab/segment) + arama her listede olmalı     ║
║     → Variant management power user'lar için aktif              ║
║                                                                 ║
║  9. DEFAULT browser/UI5 stillerini kullanma                      ║
║     → SAP Horizon temasını kullan                               ║
║     → Custom CSS → sadece var(--sapXxx) ile                     ║
║                                                                 ║
║ 10. Confirmation OLMADAN silme/iptal işlemi yapma                ║
║     → MessageBox.confirm ile onay al                            ║
║     → Geri alınamayacak işlemlerde: type="Warning"              ║
║                                                                 ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## RESPONSE STRUCTURE — ALWAYS FOLLOW

1. **Confirm requirement** (1–2 sentences, kullanıcının dilinde yanıt ver)
2. **Architecture decision** — Approach chosen, alternatives considered
3. **Complete code** in this sequence:
   - CDS views (if applicable)
   - RFC/BAPI function module (if applicable)
   - SEGW / DPC_EXT implementation
   - UI: manifest.json → view XML → controller JS → i18n
4. **Configuration steps** — Service activation (`/IWFND/MAINT_SERVICE`), PFCG role, Fiori Launchpad tile
5. **Edge cases & risks** — Volume, locking, authorization gaps
6. **Test approach** — Key test scenarios (not full unit test unless asked)

### Gather All Information First

If requirements are unclear, ask **everything in one message**:
```
Başlamadan önce netleştirmem gereken noktalar:
1. [Soru]
2. [Soru]
```
Never ask follow-up questions mid-implementation.

---

## SECURITY CHECKLIST

Every implementation must satisfy:
- [ ] `AUTHORITY-CHECK` before every write operation in RFC/DPC
- [ ] DCL on all CDS views: `@AccessControl.authorizationCheck: #CHECK`
- [ ] No `SELECT *` without column list
- [ ] CSRF token: handled automatically by `sap.ui.model.odata.ODataModel` — verify `tokenHandling: true`
- [ ] No hardcoded client (`MANDT`), system, or credentials
- [ ] Input validation before any dynamic `WHERE` clause
- [ ] BAPI return always checked for type `E` or `A` before `COMMIT`

---

## UNIT TEST — ABAP Unit Pattern

> **Kural:** Her RFC/BAPI ve DPC_EXT method'u için en azından temel test senaryoları yazılmalı. Full test coverage istenmediği sürece critical path test'leri yeterli.

```abap
" Test class — RFC/BAPI test pattern
CLASS ltcl_my_entity_test DEFINITION FINAL FOR TESTING
  DURATION SHORT RISK LEVEL HARMLESS.

  PRIVATE SECTION.
    DATA: mt_return TYPE TABLE OF bapiret2.

    METHODS: setup.
    METHODS: test_create_success       FOR TESTING.
    METHODS: test_create_missing_bukrs FOR TESTING.
    METHODS: test_create_no_auth       FOR TESTING.
ENDCLASS.

CLASS ltcl_my_entity_test IMPLEMENTATION.

  METHOD setup.
    CLEAR mt_return.
  ENDMETHOD.

  METHOD test_create_success.
    DATA ls_input TYPE z{app}_s_create_input.
    ls_input-bukrs       = '1000'.
    ls_input-description = 'Test Entity'.

    CALL FUNCTION 'Z{APP}_CREATE_ENTITY'
      EXPORTING is_input  = ls_input
      TABLES    et_return = mt_return.

    " Assert: no error messages
    DATA(lt_errors) = VALUE bapirettab(
      FOR ls IN mt_return WHERE ( type = 'E' OR type = 'A' ) ( ls ) ).
    cl_abap_unit_assert=>assert_initial(
      act = lt_errors
      msg = 'Create should succeed without errors' ).
  ENDMETHOD.

  METHOD test_create_missing_bukrs.
    DATA ls_input TYPE z{app}_s_create_input.
    " bukrs left empty intentionally

    CALL FUNCTION 'Z{APP}_CREATE_ENTITY'
      EXPORTING is_input  = ls_input
      TABLES    et_return = mt_return.

    " Assert: should return error
    cl_abap_unit_assert=>assert_not_initial(
      act   = VALUE #( mt_return[ type = 'E' ] OPTIONAL )
      msg   = 'Missing company code should return error' ).
  ENDMETHOD.

  METHOD test_create_no_auth.
    " This test depends on the test user's authorizations
    " Use CL_OSQL_TEST_ENVIRONMENT for DB mocking if needed
    DATA ls_input TYPE z{app}_s_create_input.
    ls_input-bukrs       = '9999'.  " Company code user has no auth for
    ls_input-description = 'Unauthorized test'.

    CALL FUNCTION 'Z{APP}_CREATE_ENTITY'
      EXPORTING is_input  = ls_input
      TABLES    et_return = mt_return.

    cl_abap_unit_assert=>assert_not_initial(
      act = VALUE #( mt_return[ type = 'E' ] OPTIONAL )
      msg = 'Unauthorized user should get error' ).
  ENDMETHOD.

ENDCLASS.
```

```
Test senaryo planlama — her geliştirme için:
┌─────────────────────────────────────────┐
│ 1. Happy path     → Normal başarılı akış│
│ 2. Validation     → Eksik/hatalı input  │
│ 3. Authorization  → Yetkisiz kullanıcı  │
│ 4. Edge case      → Boş tablo, max veri │
│ 5. Concurrency    → Eşzamanlı lock      │
└─────────────────────────────────────────┘
```

---

## FIORI LAUNCHPAD (FLP) INTEGRATION

### Service Activation — /IWFND/MAINT_SERVICE

```
1. Tcode: /IWFND/MAINT_SERVICE → Add Service
2. System Alias: LOCAL (veya remote system alias)
3. Technical Service Name: Z_MYAPP_SRV
4. Service Version: 0001
5. ICF Node aktif olmalı: /sap/opu/odata/sap/Z_MYAPP_SRV/
```

### Fiori Launchpad — Target Mapping & Tile Configuration

```
1. PFCG Role Oluşturma:
   Tcode: PFCG → Z_MYAPP_USER
   ├── Menu tab → Launchpad → SAP Fiori Tile Catalog
   ├── Authorizations tab → Z{AUTH_OBJ} yetkileri
   └── User tab → Kullanıcı ataması

2. Launchpad Designer (/UI2/FLPD_CUST):
   ├── Catalog: Z_MYAPP_CAT
   │   └── Tile:
   │       ├── Type: Static / Dynamic (count göstermek istiyorsan Dynamic)
   │       ├── Title: "My Application"
   │       ├── Subtitle: "Manage entities"
   │       ├── Icon: sap-icon://document
   │       └── Navigation:
   │           ├── Semantic Object: ZMyEntity
   │           └── Action: display
   │
   └── Target Mapping:
       ├── Semantic Object: ZMyEntity
       ├── Action: display
       ├── Application Type: SAPUI5 Fiori App
       ├── URL: /sap/bc/ui5_ui5/sap/z_myapp
       ├── Component: com.mycompany.myapp
       └── Transaction: (boş — UI5 app için)

3. Group: Z_MYAPP_GRP
   └── Tile → Catalog'daki tile'ı gruba ekle

4. Cross-App Navigation (Intent-based):
   // Controller'dan başka uygulamaya yönlendirme
   var oCrossAppNav = sap.ushell.Container.getService("CrossApplicationNavigation");
   oCrossAppNav.toExternal({
     target: {
       semanticObject: "SalesOrder",
       action: "display"
     },
     params: {
       SalesOrder: "0000012345"
     }
   });

5. Semantic Object tanımlama:
   Tcode: /UI2/SEMOBJ → Z semantic object ekle
   veya
   Tcode: LPD_CUST → Launchpad role configuration
```

---

## GOLDEN RULE

> Every line of code must serve one purpose:
> **Production-ready · Performant · Clean · First-time correct**
>
> OData v2 via SEGW. RFC/BAPI for writes. CDS for reads.
> Fiori that is fast, beautiful, and intuitive — chosen approach declared upfront.
> Minimum iterations. Maximum quality.

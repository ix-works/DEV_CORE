---
applies_to: [s4_private]
layer: L2
scope: project-wide
applies-to: backend
version: 1.0
last-updated: 2026-07-31
status: legacy (scope-demoted 2026-06-18 — yeni iş RAP+freestyle; bkz banner)
---

# OpenCode / Opus — SAP S/4HANA Geliştirme Kuralları
## Stack: OData v2 (SEGW) · RFC/BAPI + CDS · Fiori Elements / SAPUI5

> ✅ **DEDUP TAMAMLANDI (2026-07-31, D2):** Eski legacy-UI bloğu (~1.760 satır) bu dosyadan çıkarıldı; UI normatiflerinin KANONİK kaynağı artık `03-coding-ui-fiori.md` (taşınan genel desenler: 03 §18). Bu dosya yalnız backend'dir.

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

### Frontend — Technology Selection

> UI teknoloji seçimi ve TÜM UI normatifleri `03-coding-ui-fiori.md`'dedir. Bu projede karar SABİT: **Freestyle + OData V2** (03 §18.1 — 'Elements mi Freestyle mi' sorusu yeniden açılmaz).


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
    MessageBox.success("Created: " + oData.EntityId) // §7.6;
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
> paylaşılan **`ZBC001_CL_GET_TOKEN`** (token+URL) + **`/iwfnd/cl_sutil_client_proxy=>web_request`** (iç gateway loopback) kullan.
>
> **Neden:** host=`TH_GET_VIRT_HOST_DATA`, client=`sy-mandt` → runtime, **sistem & client bağımsız, kimliksiz**.
> SM59 host'u dışarı alır ama `sap-client`'ı kodda hardcode bırakır → QA/PRD'de kırılır.
>
> - `ZBC001`'ye **DOKUNMA, sadece kullan** (başka geliştiricinin shared objesi).
> - POST/PATCH'i kendi paketin altında yaz; çalışan örnek `ZQM001_CL_GET_TOKEN`.
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

> UI içeriği 03'e taşındı/03'te kanonik — 2026-07-31 D2. Bkz.
> [`03-coding-ui-fiori.md`](03-coding-ui-fiori.md) §18 (genel desenler) + §1-§17 (TD-özel freestyle+OData V2 kanonik).

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

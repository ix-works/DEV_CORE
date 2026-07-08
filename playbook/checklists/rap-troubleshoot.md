# Checklist — RAP Troubleshoot + Unit-Test (BOTD)

> RAP geliştirmede **hata teşhisi** + **ABAP Unit test** (BOTD test-double) rehberi.
> Kaynak adoption: weiserman/rap-skills (tooling-kıyas 2026-06-09). Standart: [`../../standards/05-coding-rap.md`](../../standards/05-coding-rap.md).
> ⚠️ Test/troubleshoot **ek**tir — yaratım/publish reçetesi `adt-rap.md` §32 + `rap-creation.md`.

---

## 1. RAP TROUBLESHOOT — sık hatalar → kök neden

| Belirti | Olası kök neden | Bak |
|---|---|---|
| **BDEF aktive olmuyor** | view entity inaktif / kompozisyon-parent assoc eksik / managed alan eşleşmesi | `adt_syntax_check` (inactive); root↔child `association to parent` + `composition [..] of` çifti tam mı |
| **Validation/determination tetiklenmiyor** | trigger eksik (`on save` / `on modify { create; update; field x; }`) veya `determine action` çağrılmamış | BDEF trigger bloğu; determination `for determine on save` |
| **Action/handler dump** | EML `MODIFY ENTITIES` failed/reported handle edilmemiş; `%cid` boş; mapping eksik | FAILED/REPORTED oku; `%cid`/`%key` set; `mapping for ...` |
| **Save'de veri yazılmıyor** | managed save için `MODIFY` yerine elle yazma; ya da unmanaged'da `save` metodu boş | managed: framework yazar; unmanaged: `saver~save_modified` |
| **`CREATE BY \_assoc` child'ı boş key/alanla oluşuyor** (ör. "Muhatap rolünü girin"; parvw boş) — yeni belgede çalışır, **mevcut** belgeye eklemede boş | Semantik key salt-okunur; create'te key'in **`<Key>ForEdit`** muadili (`@ObjectModel.editableFieldFor`) set edilmeli | Projeksiyon CDS source oku (`adt_get <Entity>TP cds`); `editableFieldFor` ara. Reçete: `adt-rap.md` §35 |
| **Etag/lock hatası** (managed) | `lock master` + `etag master <field>` eksik | `check_rap_managed_etag.py`; BDEF `lock master` + `etag master` |
| **$metadata 404 / boş** | SRVB publish edilmedi/aktive değil; SRVD↔SRVB bağı | publish + activate; `adt_get` SRVB version=active |
| **Draft tutarsızlığı** | `with draft` + draft tablo (`_D`) eksik/uyumsuz; `draft determine action Prepare` | draft tablo + draft action |
| **Performans (liste yavaş)** | eager join; CompareFilter kapalı; gereksiz expose | association (join-on-demand); `@AbapCatalog.compiler.compareFilter: true` |

> Teşhis araçları: `adt_syntax_check` (inactive pre-audit), `adt_atc_check`, runtime dump (ST22 → deferred `adt_dumps`), `adt_where_used` (etki).

## 2. RAP UNIT-TEST (BOTD test-double)

RAP BO için ABAP Unit — test ortamı **`CL_BOTD_TXBUFDBL_BO_TEST_ENV`** (transaction-buffer double; DB'ye dokunmaz):

```abap
" ccau (test include) — iskelet
CLASS ltc_sevkemri DEFINITION FINAL FOR TESTING
  DURATION SHORT RISK LEVEL HARMLESS.
  PRIVATE SECTION.
    CLASS-DATA env TYPE REF TO if_botd_txbufdbl_bo_test_env.
    CLASS-METHODS class_setup.   " env = cl_botd_txbufdbl_bo_test_env=>create( VALUE #( ( '<RootEntity>' ) ) )
    CLASS-METHODS class_teardown." env->destroy( )
    METHODS setup.               " env->clear_doubles( )
    METHODS create_ok    FOR TESTING.
    METHODS validate_qty FOR TESTING.
ENDCLASS.
```

**Kapsanması gereken senaryolar (RAP test pattern):**
- **CRUD:** create (key/cid set), update, delete → `MODIFY ENTITIES` + `COMMIT ENTITIES` (test env'de) → FAILED/REPORTED boş mu.
- **Validation:** geçersiz veri → REPORTED'da beklenen mesaj; geçerli → temiz.
- **Determination:** create sonrası türetilen alan (audit/se_type) doğru set edildi mi.
- **Action:** action çağrısı → beklenen state/mapping.
- **Create-by-association:** parent+child deep create.

> FIT_SE'ye özgü: `validateQtyNotBelowDelivered`, `validatePAK`, `validateBalanceSE`, `deleteRootPrecheck`, audit determination — her biri ayrı `FOR TESTING` metodu.

## 3. ATC DİSİPLİNİ (no-suppress — matt1as adoption)

- ATC = `adt_atc_check` (variant `ZZNDBS_ATC`). **Priority 1 ZORUNLU** düzeltilir.
- **Pseudo-comment / pragma ile suppression YASAK** (sessiz susturma yok). Prio 2/3 ancak **kullanıcı açık onayıyla** pass — sessiz değil.
- Bulguları **kategoriye göre grupla**, metodik yürü. Bkz. `feedback_atc-priority-1-zorunlu`.

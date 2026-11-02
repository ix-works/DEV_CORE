CLASS lhc_Variant DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.
    " Idempotent guard (LUW-scope): setAdmin'in IN LOCAL MODE MODIFY'i on-save
    " det'i yeniden tetikler; 2. pas anahtari burada -> CONTINUE -> dongu kirilir.
    DATA mt_done TYPE SORTED TABLE OF sysuuid_x16 WITH UNIQUE KEY table_line.

    METHODS get_global_authorizations FOR GLOBAL AUTHORIZATION
      IMPORTING REQUEST requested_authorizations FOR Variant RESULT result.
    METHODS setAdmin FOR DETERMINE ON SAVE
      IMPORTING keys FOR Variant~setAdmin.
ENDCLASS.

CLASS lhc_Variant IMPLEMENTATION.

  METHOD get_global_authorizations.
  ENDMETHOD.

  " Create (CreatedBy bos) -> Username + audit doldur; sonraki update -> sadece ChangedAt.
  METHOD setAdmin.
    READ ENTITIES OF zsd000_i_ui_variant IN LOCAL MODE
      ENTITY Variant FIELDS ( CreatedBy ) WITH CORRESPONDING #( keys )
      RESULT DATA(lt).
    GET TIME STAMP FIELD DATA(lv_now).
    DATA lt_upd TYPE TABLE FOR UPDATE zsd000_i_ui_variant.
    LOOP AT lt INTO DATA(ls).
      IF line_exists( mt_done[ table_line = ls-VariantUuid ] ).
        CONTINUE.
      ENDIF.
      INSERT ls-VariantUuid INTO TABLE mt_done.
      IF ls-CreatedBy IS INITIAL.
        APPEND VALUE #( %tky = ls-%tky
          Username  = sy-uname
          CreatedBy = sy-uname
          CreatedAt = lv_now
          ChangedAt = lv_now
          %control-Username  = if_abap_behv=>mk-on
          %control-CreatedBy = if_abap_behv=>mk-on
          %control-CreatedAt = if_abap_behv=>mk-on
          %control-ChangedAt = if_abap_behv=>mk-on ) TO lt_upd.
      ELSE.
        APPEND VALUE #( %tky = ls-%tky
          ChangedAt = lv_now
          %control-ChangedAt = if_abap_behv=>mk-on ) TO lt_upd.
      ENDIF.
    ENDLOOP.
    IF lt_upd IS NOT INITIAL.
      MODIFY ENTITIES OF zsd000_i_ui_variant IN LOCAL MODE
        ENTITY Variant UPDATE FROM lt_upd
        REPORTED DATA(lr).
    ENDIF.
  ENDMETHOD.

ENDCLASS.

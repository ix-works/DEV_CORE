CLASS zcl_order_api DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    METHODS build_payload
      IMPORTING iv_qty          TYPE p
      RETURNING VALUE(rv_payload) TYPE string.
ENDCLASS.

CLASS zcl_order_api IMPLEMENTATION.
  METHOD build_payload.
    " request_body olusturuluyor -- API cagrisi icin JSON govdesi
    DATA lv_qty_str TYPE string.
    WRITE iv_qty TO lv_qty_str.
    rv_payload = |\{ "quantity": { lv_qty_str } \}|.
  ENDMETHOD.
ENDCLASS.

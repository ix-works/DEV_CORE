CLASS zcl_helper DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    METHODS get_description
      IMPORTING iv_id          TYPE c LENGTH 10
      RETURNING VALUE(rv_desc) TYPE string.
ENDCLASS.

CLASS zcl_helper IMPLEMENTATION.
  METHOD get_description.
    rv_desc = iv_id.
  ENDMETHOD.
ENDCLASS.

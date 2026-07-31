CLASS zbp_i_zsd001_order DEFINITION PUBLIC FINAL CREATE PUBLIC FOR BEHAVIOR OF zsd001_i_order.
  PUBLIC SECTION.
    METHODS create_transport_doc FOR MODIFY IMPORTING it_order FOR CREATE order.
ENDCLASS.

CLASS zbp_i_zsd001_order IMPLEMENTATION.
  METHOD create_transport_doc.
    " Ayri LUW: Z RFC-enabled FM + DESTINATION 'NONE' uzerinden cagir (playbook/adt-rap.md).
    CALL FUNCTION 'ZSD001_FM_SHIPMENT_CREATE'
      DESTINATION 'NONE'
      EXPORTING
        is_header = ls_header
      IMPORTING
        es_return = ls_return.
  ENDMETHOD.
ENDCLASS.

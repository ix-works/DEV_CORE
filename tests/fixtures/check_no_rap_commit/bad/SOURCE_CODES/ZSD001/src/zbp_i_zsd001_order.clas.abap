CLASS zbp_i_zsd001_order DEFINITION PUBLIC FINAL CREATE PUBLIC FOR BEHAVIOR OF zsd001_i_order.
  PUBLIC SECTION.
    METHODS create_transport_doc FOR MODIFY IMPORTING it_order FOR CREATE order.
ENDCLASS.

CLASS zbp_i_zsd001_order IMPLEMENTATION.
  METHOD create_transport_doc.
    CALL FUNCTION 'BAPI_SHIPMENT_CREATE'
      EXPORTING
        is_header = ls_header
      IMPORTING
        es_return = ls_return.
    COMMIT WORK.
  ENDMETHOD.
ENDCLASS.

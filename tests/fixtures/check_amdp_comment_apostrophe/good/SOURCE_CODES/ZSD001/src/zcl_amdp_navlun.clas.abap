CLASS zcl_amdp_navlun DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    CLASS-METHODS calc_navlun
      IMPORTING iv_voyage_id       TYPE zsd001_voyage_id
      RETURNING VALUE(rv_navlun)   TYPE p.
ENDCLASS.

CLASS zcl_amdp_navlun IMPLEMENTATION.
  METHOD calc_navlun BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT OPTIONS READ-ONLY.
    -- voyaga ait navlun hesabi
    SELECT navlun INTO rv_navlun FROM zsd001_voy WHERE voyage_id = :iv_voyage_id;
  ENDMETHOD.
ENDCLASS.

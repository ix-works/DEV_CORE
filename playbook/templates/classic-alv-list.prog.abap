*&---------------------------------------------------------------------*
*& KANONİK TEMPLATE — Klasik ALV liste programı (KOPYALA + ÖZELLEŞTİR)
*&---------------------------------------------------------------------*
*& ⚠️ YAPI NOTU: Bu template TEK-BODY (sadece ALV/screen-gen DESENİ gösterir).
*& GERÇEK programda kod include'lara BÖLÜNÜR (std 06 §1): main=INCLUDE+event,
*& ZSD<pkg>_I_<PRG>_T01(TOP)/_C01(CLS)/_F01(FORM)/_O01(PBO)/_I01(PAI). Bu deseni kopyala,
*& yapıyı std 06 §1'e göre kur.
*&
*& TEMPLATE-FIRST (std 06 §2, ADR 0012): ALV kurulumu — field catalog
*& (TR title + hotspot), event handler, layout — programa İNLİNE kodlanır.
*& Reusable ZSD000_CL_ALV_* class KULLANILMAZ (program-spesifik parametre
*& yağmurunu önlemek için; field title/hotspot/event/toolbar her programda
*& farklı → dışarıdan parametrelemek class'ı çirkinleştirir).
*&
*& Ekran (screen 0100) + GUI status (STAT0100) + titlebar (TIT0100):
*&   AI üretir → ZSD000_FM_SCREEN_GEN (SOAP-RFC). Bkz. playbook/adt-fugr-functions.md §6.
*&   fcode'lar: F3=BACK, Shift+F3=EXIT, F12=CANCEL (PAI'de handle).
*&---------------------------------------------------------------------*
REPORT z____p_xxx.

TABLES vbak.                          " <-- selection-screen için DB tablosu

TYPES: BEGIN OF ty_row,               " <-- görüntü satırı (program-spesifik)
         vbeln TYPE vbak-vbeln,
         erdat TYPE vbak-erdat,
         ernam TYPE vbak-ernam,
         netwr TYPE vbak-netwr,
         waerk TYPE vbak-waerk,
       END OF ty_row.

DATA: gt_data    TYPE STANDARD TABLE OF ty_row,
      go_docking TYPE REF TO cl_gui_docking_container,
      go_grid    TYPE REF TO cl_gui_alv_grid,
      gt_fcat    TYPE lvc_t_fcat,
      gs_layout  TYPE lvc_s_layo.

SELECT-OPTIONS s_vbeln FOR vbak-vbeln.

*&--- Event handler (LOKAL) — hotspot / double_click / user_command -----
CLASS lcl_event DEFINITION.
  PUBLIC SECTION.
    METHODS on_hotspot
      FOR EVENT hotspot_click OF cl_gui_alv_grid
      IMPORTING e_row_id e_column_id.
    METHODS on_double_click
      FOR EVENT double_click OF cl_gui_alv_grid
      IMPORTING e_row e_column.
    METHODS on_user_command
      FOR EVENT user_command OF cl_gui_alv_grid
      IMPORTING e_ucomm.
ENDCLASS.

CLASS lcl_event IMPLEMENTATION.
  METHOD on_hotspot.
    " Hotspot kolonuna tıklama → drill-down / işlem (program-spesifik).
    READ TABLE gt_data INTO DATA(ls_row) INDEX e_row_id-index.
    IF sy-subrc = 0.
      MESSAGE |Belge { ls_row-vbeln } seçildi (kolon { e_column_id-fieldname })| TYPE 'I'.
      " ör: SET PARAMETER + CALL TRANSACTION 'VA03'...
    ENDIF.
  ENDMETHOD.
  METHOD on_double_click.
    READ TABLE gt_data INTO DATA(ls_row) INDEX e_row-index.
    " ... çift-tık aksiyonu ...
  ENDMETHOD.
  METHOD on_user_command.
    CASE e_ucomm.                     " özel toolbar fonksiyonları
      WHEN 'SIL'.  " ...
      WHEN OTHERS.
    ENDCASE.
  ENDMETHOD.
ENDCLASS.

DATA go_evt TYPE REF TO lcl_event.

*&--- Field catalog: TR title + hotspot PROGRAMA ÖZGÜ → burada kodlanır --
FORM build_fcat.
  gt_fcat = VALUE lvc_t_fcat(
    ( fieldname = 'VBELN' coltext = 'Satış Belgesi'    hotspot = abap_true  outputlen = 12 )
    ( fieldname = 'ERDAT' coltext = 'Oluşturma Tarihi' )
    ( fieldname = 'ERNAM' coltext = 'Oluşturan' )
    ( fieldname = 'NETWR' coltext = 'Net Değer'        do_sum  = abap_true )
    ( fieldname = 'WAERK' coltext = 'Para Birimi' ) ).
  " Alternatif: DDIC'ten otomatik merge için
  " cl_salv_data_descr / FM LVC_FIELDCATALOG_MERGE kullan, sonra title/hotspot düzelt.
ENDFORM.

START-OF-SELECTION.
  SELECT vbeln, erdat, ernam, netwr, waerk
    FROM vbak INTO TABLE @gt_data
    UP TO 500 ROWS
    WHERE vbeln IN @s_vbeln.
  CALL SCREEN 0100.

MODULE status_0100 OUTPUT.
  SET PF-STATUS 'STAT0100'.            " ZSD000_FM_SCREEN_GEN ile üretildi
  SET TITLEBAR  'TIT0100'.
  IF go_grid IS INITIAL.
    go_docking = NEW #( side  = cl_gui_docking_container=>dock_at_top
                        ratio = 95 ).
    go_grid    = NEW #( i_parent = go_docking ).
    PERFORM build_fcat.
    gs_layout = VALUE #( cwidth_opt = abap_true zebra = abap_true sel_mode = 'A' ).
    go_evt = NEW #( ).
    SET HANDLER go_evt->on_hotspot
                go_evt->on_double_click
                go_evt->on_user_command FOR go_grid.
    go_grid->set_table_for_first_display(
      EXPORTING is_layout = gs_layout i_save = 'A'
      CHANGING  it_outtab = gt_data it_fieldcatalog = gt_fcat ).
  ELSE.
    go_grid->refresh_table_display( ).
  ENDIF.
ENDMODULE.

MODULE exit_command_0100 INPUT.
  " type='E' fonksiyonlar (BACK/EXIT/CANCEL) + ESC -> AT EXIT-COMMAND ile buraya gelir.
  " Navigasyon (std 06 §4 MUST): BACK(F3)/CANCEL(F12) -> bir seviye geri = seçim ekranı
  " (LEAVE TO SCREEN 0); EXIT(Shift+F3) -> programdan çık (LEAVE PROGRAM).
  " BACK/CANCEL'da LEAVE PROGRAM = ana-menüye atlama tuzağı, YASAK.
  CASE sy-ucomm.
    WHEN 'BACK' OR 'CANCEL'.
      LEAVE TO SCREEN 0.
    WHEN 'EXIT'.
      LEAVE PROGRAM.
  ENDCASE.
ENDMODULE.

MODULE user_command_0100 INPUT.
  " Navigasyon (std 06 §4 MUST): BACK(F3)/CANCEL(F12) -> seçim ekranı (LEAVE TO SCREEN 0);
  " EXIT(Shift+F3) -> programdan çık (LEAVE PROGRAM). BACK/CANCEL'da LEAVE PROGRAM YASAK.
  CASE sy-ucomm.
    WHEN 'BACK' OR 'CANCEL'.
      LEAVE TO SCREEN 0.
    WHEN 'EXIT'.
      LEAVE PROGRAM.
  ENDCASE.
ENDMODULE.

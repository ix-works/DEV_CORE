*&---------------------------------------------------------------------*
*& KANONİK TEMPLATE — Klasik modal Dynpro DİYALOG ekranı (KOPYALA + ÖZELLEŞTİR)
*&---------------------------------------------------------------------*
*& ⚠️ SINIR (kardeş şablon, kopyası DEĞİL): bu dosya
*&   `classic-alv-list.prog.abap`'ın tamamlayıcısıdır.
*&     LİSTE/RAPOR ekranı (çok satır, salt-görüntüleme/ana ekran, ALV grid)
*&       → classic-alv-list.prog.abap kullan.
*&     DİYALOG ekranı (TEK KAYITLIK modal alt-ekran: düzeltme/ekleme/transfer
*&       formu — DDIC yapıya bağlı data-field'lar + validasyon + kaydet akışı)
*&       → BU şablonu kullan.
*&   Aynı programda ikisi bir arada olabilir (liste + ondan açılan diyaloglar);
*&   canlı örnek desen: bir stok-hareket takip programının ana bakım-grid ekranı
*&   + ondan açılan düzeltme/transfer/kayıt-ekle diyalogları (3 ayrı Dynpro,
*&   aynı desen 3 kez tekrarlanmış).
*&
*& ⭐ ÖNCE OKU (bu şablon YALNIZ İSKELETTİR — asıl bilgi oradadır):
*&   playbook/howto-classic-dynpro-datafield-screens.md
*&     — karar ağacı (ALV mi/diyalog mu/karışık mı)
*&     — arama-yardımı 4-mekanizma tablosu (DTEL-std / yapı-attachment /
*&       buton+popup / POV) ve HANGİSİ NE ZAMAN
*&     — ekran üreteci turu (ölç→payload→yaz) + CUA tuzakları (donör-çakışan
*&       fcode, IT_BUTTONS'un HER ÇAĞRIDA toolbar'ı sıfırdan kurması) +
*&       doğrulama protokolü (tur-başı↔final sayaç + FUNDTL diff)
*&   playbook/howto-dynpro-gui-status-generation.md — üreteç kullanım kılavuzu
*&     §2  16 parametrelik imza · §2.1 donör reçetesi (BACK/EXIT/CANCEL ailesi)
*&     §2.2 fail-closed anahtarlar · §4 IT_FIELDS + etiket kuralı · §10 doğrulama
*&   ⛔ exit_command_<n> MODÜLÜ YAZMA: üretilen FLOW'da AT EXIT-COMMAND satırı
*&     YOKTUR → o modül hiç çağrılmaz (ölü kod). ESC = F12 = CANCEL, PAI yakalar.
*&   ⚠️ Klasik FORM ... USING ALT-SINIF referansını KABUL ETMEZ ("actual parameter
*&     incompatible", ölçüldü 2026-08-18): cl_gui_docking_container →
*&     TYPE REF TO cl_gui_container geçirilemez. Upcast yalnız ATAMA ile olur:
*&       DATA go_parent TYPE REF TO cl_gui_container.
*&       go_parent = go_docking.   " sonra PERFORM ... USING go_parent
*&     Canlı emsal: ZSD000_P_ALV_TEMP4 (0100 DOCKING / 0200 CC_ALV / 0300 alanlar)
*&   standards/06-coding-classic-dialog.md §1 — include bölme (bu şablon
*&     TEK-BODY gösterir; gerçek programda T01/C01/O01/I01/F01'e bölünür)
*&---------------------------------------------------------------------*
*&
*& ---------------------------------------------------------------------
*& 1) DDIC YAPI — diyalog alanlarının TEK KAYNAĞI (elle gs_* bildirimine
*&    GERİ DÖNME — köprü/MOVE-CORRESPONDING bırakma; ekran alanı DOĞRUDAN
*&    bu yapının bileşenine bağlanır → etiket/uzunluk/CONV_EXIT/arama-yardımı
*&    DDIC'ten gelir, elle verilmez).
*&
*&    define structure zsd001_s_dlg {
*&      ver_matnr  : matnr;
*&      ver_werks  : werks_d;
*&      ver_lgort  : lgort_d
*&        with value help h_t001l                    " ⭐ bileşene attachment —
*&          where lgort = zsd001_s_dlg.ver_lgort      "   howto §3 mekanizma②
*&            and werks = zsd001_s_dlg.ver_werks;     "   (ekran ALAN ADINA değil
*&      hed_referans : xblnr;                         "   YAPI BİLEŞENİNE yapılır —
*&      hed_tarihi   : bldat;                         "   aynı tipte 2. alan varsa
*&      @Semantics.quantity.unitOfMeasure : 'zsd001_s_dlg.meins'
*&      menge      : menge_d;
*&      meins      : meins;
*&    }
*&
*&    Ekranı üreten çağrıda her alan şöyle verilir (GATEWAY işi —
*&    ZSD000_FM_SCREEN_GEN; bu template yalnız ABAP tarafını gösterir):
*&        NAME='ZSD001_S_DLG-VER_LGORT'  TYPE='TEMPLATE'  FROM_DICT='X'
*&        MATCHCODE=''   (elle matchcode DDIC attachment'ının ÖNÜNE GEÇER)
*&    ⚠️ `TEMPLATE` bir ALAN DEĞİL, `TYPE` DEĞERİDİR (düzeltme 2026-08-18).
*&    ⭐ ETİKET AYRI SATIRDIR: giriş alanı FROM_DICT ile bile kendi etiketini
*&      GETİRMEZ. Her etiket için TYPE='TEXT' + FROM_DICT='X' + TEXT BOŞ ver →
*&      metin DDIC'ten gelir (ADR 0005-D dostu). TEXT satırını unutmak SESSİZ
*&      kusurdur, FM uyarı VERMEZ. (Ölçüm: howto-classic-dynpro-datafield §1.1)
*&    ⚠️ Alan ekranı IV_SCREEN_TYPE='DOCKING' ister (CONTAINER'da CC_ALV tüm
*&      ekranı kaplar → rc=6) ve donör/anahtar parametreleri AÇIKÇA verilir
*&      (varsayılan minimal donör → &F2..&F5 fcode'ları; bu şablonun PAI'si
*&      BACK/EXIT/CANCEL bekler → howto-dynpro-gui-status-generation §2.1).
*& ---------------------------------------------------------------------
*&
REPORT z____p_xxx.                    " <-- gerçek programda main = INCLUDE'lar + event

*&--- TOP include (_T01) — DDIC yapıya bağlı work area + sabitler -------
DATA zsd001_s_dlg TYPE zsd001_s_dlg.  " <-- adı YAPI ADIYLA AYNI: ekran alanları
                                       "     `ZSD001_S_DLG-VER_LGORT` diye adreslenir.
DATA gv_ok_code TYPE sy-ucomm.        " OK_CODE alanı (ekranın kendi ok-code'u)
DATA gv_fc      TYPE sy-ucomm.        " normalize edilmiş fcode (aşağıya bak)

CONSTANTS: c_scrf_ver_lgort TYPE screen-name VALUE 'ZSD001_S_DLG-VER_LGORT'.
                                       " LOOP AT SCREEN'de alan adıyla eşlemek için
                                       " (dinamik kilit FORM'u, aşağıda).

*&--- PBO (_O01) ----------------------------------------------------------
MODULE status_0400 OUTPUT.
  SET PF-STATUS 'STAT0400'.           " ZSD000_FM_SCREEN_GEN ile üretildi
  SET TITLEBAR  'TIT0400'.
  PERFORM dlg_dynamic_lock.           " ⚠ ÇAĞRI PBO'DA OLMAK ZORUNDA — FORM
                                       "   LOOP AT SCREEN/MODIFY SCREEN kullanır,
                                       "   bunlar yalnız PBO'da anlamlıdır; PAI'ye
                                       "   taşınırsa kilit SESSİZCE uygulanmaz.
ENDMODULE.

*&--- Dinamik alan kilidi (_F01) — "koşullu salt-okuma" deseni -----------
*  Kapsam-içi kayıt varsa alan OTOMATİK doldurulur + kilitlenir; kapsam-dışıysa
*  önceki davranış (giriş-etkin) AYNEN korunur ⇒ kapsam-dışı senaryoda regresyon
*  SIFIR. Bu FORM'un canlı emsali: sabit-parti tablosundan gelen bir alanı
*  (`ALAN_CHARG`) dolu→kilitli, boş→giriş-etkin yapan desen.
FORM dlg_dynamic_lock.
  DATA lv_fixed TYPE char20.          " <-- program-spesifik: örn. bir master-data
                                       "     lookup'ının döndürdüğü sabit değer

  IF zsd001_s_dlg-ver_matnr IS NOT INITIAL.
    lv_fixed = |lookup burada|.       " <-- ör. ZCL_..._MASTER=>get_fixed_value( ... )
  ENDIF.

  LOOP AT SCREEN.
    IF screen-name = c_scrf_ver_lgort.
      IF lv_fixed IS INITIAL.
        screen-input = 1.             " kapsam dışı → eskisi gibi giriş-etkin
      ELSE.
        screen-input = 0.             " uyarlanmış → salt-okuma
      ENDIF.
      MODIFY SCREEN.
    ENDIF.
  ENDLOOP.
ENDFORM.

*&--- PAI (_I01) — fcode dispatch (BU ekranın KENDİ fcode'u) --------------
*  ⭐ AYRI FCODE KURALI (howto §4.4 — Q23/Q29 dersi): fcode'un metin+quickinfo'su
*    PROGRAM GENELİDİR, ekran-bazlı DEĞİL. Bir fcode'u birden çok status
*    (birden çok diyalog ekranı) paylaşırsa, quickinfo'su İKİSİNDE BİRDEN doğru
*    OLAMAZ. → Her diyalog ekranının KAYDET/İPTAL fcode'u, ekrana ÖZEL bir kod
*    taşımalı (ör. bu ekran `DLGKAY`, bir başkası `TRFKAY`) — "SAVE"i paylaşan
*    iki ekran YAZMA; yazarsan birinin etiketi/quickinfo'su diğerininkine döner.
MODULE user_command_0400 INPUT.
  gv_fc = COND #( WHEN gv_ok_code IS NOT INITIAL THEN gv_ok_code ELSE sy-ucomm ).
  CLEAR: gv_ok_code, sy-ucomm.        " ⚠ ZORUNLU — atlanırsa sticky-komut tuzağı

  CASE gv_fc.
    WHEN 'DLGKAY'.                    " bu ekranın KENDİ kaydet-fcode'u
      PERFORM dlg_validate_and_save CHANGING DATA(lv_ok).
      IF lv_ok = abap_true.
        LEAVE TO SCREEN 0.            " modal kapanır, çağıran ekrana döner
      ENDIF.
      " Başarısız: alanlar EKRANDA KALIR (kullanıcı düzeltip tekrar dener).

    WHEN 'VERMAT'.                    " ⭐ buton+popup F4 (aşağıya bak) — hedefi
      PERFORM dlg_f4_matnr.           "   FCODE belirler; GET CURSOR kullanma
                                       "   (imleç doğru alanda olmayabilir →
                                       "   sessizce yanlış alana yazar/no-op).

    WHEN 'BACK' OR 'CANCEL'.
      LEAVE TO SCREEN 0.
    WHEN 'EXIT'.
      LEAVE PROGRAM.
    WHEN OTHERS.                      " ⚠ ELSE-fallthrough YAZMA (sessiz yanlış
  ENDCASE.                            "   değer riski) — tanımsız fcode'da hiçbir
ENDMODULE.                            "   şey yapılmaz.

*&--- Buton + popup F4 (_F01) — Z arama yardımı (SHLP) YARATILAMADIĞINDA ---
*  ⛔ Bu araç setiyle bir Z search-help (SHLP) YARATILAMAZ/DEĞİŞTİRİLEMEZ
*    (ADT'de shlp koleksiyonu yok; DDIF_SHLP_* RFC-enabled değil). Süzgeçli
*    F4 gerekiyorsa (ör. "yalnız şu malzeme tipleri") çare BUTON+POPUP'tır.
*    Detay + kanıt: howto §3 mekanizma③.
*  ⚠ `REUSE_ALV_POPUP_TO_SELECT` tercih edilir — `F4IF_INT_TABLE_VALUE_REQUEST`
*    DEĞİL: (a) DYNPPROG/DYNPNR/DYNPROFIELD adreslemesi PAI'den zaten gereksiz
*    (hedef fcode'dan belli), (b) tek çağrıda BİRDEN ÇOK alan yazılacaksa
*    (örn. seçilen kayıttan birim de kopyalanacaksa) RETFIELD modeli bunu
*    ifade edemez.
FORM dlg_f4_matnr.
  TYPES: BEGIN OF ty_f4,
           matnr TYPE matnr,
           maktx TYPE maktx,
         END OF ty_f4.
  DATA lt_f4 TYPE STANDARD TABLE OF ty_f4.

* CLEAN CORE: ham MARA/MAKT yerine released CDS (ör. I_Product +
* I_ProductDescription). Kapsam süzgeci burada WHERE'e girer (ör. MTART IN ...).
  SELECT p~product AS matnr, t~productdescription AS maktx
    FROM i_product AS p
         LEFT OUTER JOIN i_productdescription AS t     " LEFT OUTER — açıklaması
           ON  t~product  = p~product                  " olmayan kayıt LİSTEDEN
           AND t~language = @sy-langu                  " DÜŞMESİN (INNER olsaydı
    INTO TABLE @lt_f4.                                  " sessizce düşerdi).

  IF lt_f4 IS INITIAL.
    MESSAGE 'Kapsam içinde kayıt bulunamadı.' TYPE 'S' DISPLAY LIKE 'W'.
    RETURN.
  ENDIF.

  DATA lt_fcat TYPE slis_t_fieldcat_alv.
  " ... fcat kurulumu (kanonik FORM'a devret, burada tekrar yazma) ...

  DATA ls_sel  TYPE slis_selfield.
  DATA lv_exit TYPE char1.
  CALL FUNCTION 'REUSE_ALV_POPUP_TO_SELECT'
    EXPORTING
      i_title             = 'Seçim'
      i_selection         = abap_true
      i_zebra             = abap_true
      i_tabname           = 'LT_F4'
      it_fieldcat         = lt_fcat
      i_callback_program  = sy-repid
    IMPORTING
      es_selfield         = ls_sel
      e_exit              = lv_exit
    TABLES
      t_outtab            = lt_f4
    EXCEPTIONS
      program_error       = 1
      OTHERS              = 2.
  IF sy-subrc <> 0 OR lv_exit = abap_true OR ls_sel-tabindex <= 0.
    RETURN.                           " kullanıcı vazgeçti — alan DEĞİŞMEZ
  ENDIF.

  READ TABLE lt_f4 INTO DATA(ls_f4) INDEX ls_sel-tabindex.
  IF sy-subrc = 0.
    zsd001_s_dlg-ver_matnr = ls_f4-matnr.
  ENDIF.
ENDFORM.

*&--- Validasyon → kaydetme akışı (_F01) ----------------------------------
*  ⭐ SIRA: (1) saf girdi kontrolü (DB'ye bakmaz) → (2) kilit → (3) DB'ye bakan
*    kontrol (bakiye/çakışma) → (4) yaz → (5) unlock. Kilit ÖNCESİNDE yapılan
*    saf-girdi kontrolü kilidi gereksiz yere tutmaz; DB kontrolü kilit
*    ALINDIKTAN SONRA yapılmalı (yarış koşulu).
FORM dlg_validate_and_save CHANGING cv_ok TYPE abap_bool.
  CLEAR cv_ok.

* ① Zorunlu alan / saf girdi kontrolü.
  IF zsd001_s_dlg-ver_matnr IS INITIAL OR zsd001_s_dlg-hed_referans IS INITIAL.
    MESSAGE 'Zorunlu alanlar eksik.' TYPE 'S' DISPLAY LIKE 'E'.
    RETURN.
  ENDIF.

* ② Kilit (program-spesifik lock object / ENQUEUE_*).
* ③ DB-bağımlı kontrol (bakiye, çakışma, iş kuralı — iş mantığı SINIFTA kalır,
*    ekran modülü yalnız çağırır).
* ④ Yaz (BAPI / iş-mantığı sınıfının metodu — Z tabloya doğrudan INSERT/UPDATE
*    YASAK, ADR 0005-B).
* ⑤ COMMIT/unlock — TRY/CATCH cx_root ile, unlock her koşulda (CATCH içinde de).

  cv_ok = abap_true.
ENDFORM.

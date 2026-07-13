---
applies_to: ['s4_private', 's4_public']
---

# How-to: Released Sales Order BO (I_SalesOrderTP) EML ile create / update

> Klasik programdan (veya herhangi bir consumer'dan) **released** satış siparişi BO'sunu
> `MODIFY ENTITIES OF i_salesordertp` ile create/update ederken karşılaşılan **kanıtlı** tuzaklar
> ve doğru desenler. Kaynak: ZSD001 EXCUPL toplu-sipariş build'i (2026-07-12, canlı teşhis).
> İlgili çalışan referans: `ZSD0NN_CL_SO_MANAGER` (fitting-order) — üretimde çalışan create.

## 0. ÖZET KURALLAR (önce bunları oku)

1. **Standart partnerları (AG/RE/RG/WE) MANUEL EKLEME** — customer master'dan OTOMATİK belirlenir.
   `SoldToParty`'yi header'da ver, gerisini BO kurar. Manuel `_Partner` create = dump/hata.
2. **`PartnerFunction` alanı READ-ONLY** (released BO). `%control`'a koyarsan `BEHAVIOR_READONLY_FIELD`
   dump ("Field PARTNERFUNCTION is read-only"); `%control`/FIELDS'ten çıkarırsan `VPD 030`
   "Muhatap rolünü girin" (rol boş). İkisi de create'i bloklar → **manuel partner-add'den kaçın.**
3. **COMMIT'te generic "Kaydetme başarısız oldu"** → neredeyse her zaman **veri/master-data**:
   geçersiz **birim** (malzemede tanımsız UoM), fiyatlandırma (koşul kaydı yok), malzeme satış-alanına
   extend değil, vб. MODIFY (interaction) geçer, save (COMMIT) reddeder. **Birimi/veriyi doğrula.**
4. **"activated/created" ≠ "saved"** — MODIFY başarılı olsa da COMMIT ENTITIES ayrı reddedebilir.
   FAILED **hem** MODIFY hem COMMIT sonrası ayrı ayrı kontrol edilir.

## 1. CREATE — deep create (header + item), partner AUTO

```abap
DATA lt_so TYPE TABLE FOR CREATE i_salesordertp.
lt_so = VALUE #( ( %cid = 'H'
  SalesOrderType = <auart> SalesOrganization = <vkorg> DistributionChannel = <vtweg>
  OrganizationDivision = <spart> SoldToParty = <kunag_alpha>              " AG buradan -> auto
  PurchaseOrderByCustomer = <bstkd> SalesOrderDate = <audat>
  %control = VALUE #( SalesOrderType = if_abap_behv=>mk-on ... ) ) ).      " her set edilen alan mk-on
" TransactionCurrency / PricingDate VERME (boş bırakma) -> customer master'dan gelir.
" Yalnız master'dan FARKLI olacaksa ver (fitting-order öyle yapar).

DATA lt_item TYPE TABLE FOR CREATE i_salesordertp\_Item.
lt_item = VALUE #( ( %cid_ref = 'H' %target = VALUE #(
  ( %cid = 'HI1' product = <matnr> requestedquantity = <menge>
    requestedquantityunit = <vrkme>          " <-- MALZEME İÇİN GEÇERLİ UoM olmalı (yoksa save fail)
    plant = <werks> storagelocation = <lgort> requesteddeliverydate = <termin>
    %control = VALUE #( product = if_abap_behv=>mk-on ... ) ) ) ) ).

MODIFY ENTITIES OF i_salesordertp
  ENTITY salesorder
    CREATE FROM lt_so
    CREATE BY \_item FROM lt_item
    " CREATE BY \_partner  ->  VERME (standart partnerlar auto). Bkz. §2.
  MAPPED DATA(ls_mapped) FAILED DATA(ls_failed) REPORTED DATA(ls_reported).

IF ls_failed-salesorder IS NOT INITIAL OR ls_failed-salesorderitem IS NOT INITIAL.
  " hata: ls_reported'tan %msg->if_message~get_text( ) ile topla. RETURN.
ENDIF.
```

**Late-numbering + kesin numara (create sonrası):**
```abap
COMMIT ENTITIES BEGIN RESPONSE OF i_salesordertp FAILED DATA(lcf) REPORTED DATA(lcr).
IF lcf IS INITIAL.
  LOOP AT ls_mapped-salesorder ASSIGNING FIELD-SYMBOL(<m>).
    CONVERT KEY OF i_salesordertp FROM <m>-%pid TO FINAL(ls_key).   " pre-key -> gerçek VBELN
    lv_vbeln = ls_key-salesorder.
  ENDLOOP.
ENDIF.
COMMIT ENTITIES END.
IF lcf IS NOT INITIAL.  " <-- COMMIT AYRICA kontrol; generic "save failed" ise §0.3
  " lcr-salesorder / lcr-salesorderitem'dan mesajları topla.
ENDIF.
```
`CONVERT KEY` yalnız `COMMIT ENTITIES BEGIN..END` bloğu içinde legal.

## 2. PARTNER — neden manuel eklenmez

- Released BO'da `_Partner` create'i `PartnerFunction`'ı **key/read-only** görür:
  - `%control`/FIELDS'e koymak → `BEHAVIOR_READONLY_FIELD` dump.
  - koymamak → `VPD 030` "muhatap rolünü girin".
- **Çözüm:** hiç manuel ekleme; `SoldToParty` set edilince BO **AG/RE/RG/WE**'yi customer master'ından
  otomatik belirler. (Kanıt: canlı geçerli sipariş partnerları hepsi auto, müşteri KNVP'de
  AG/RE/RG/WE=kendisi.)
- **Farklı ship-to (WE ≠ sold-to) gerekiyorsa:** `_Partner` üzerinden bu released BO'da doğrudan
  kurulamıyor (read-only pf). Gerçek gereksinim çıkarsa **doğru mekanizma araştırılır** (header
  ship-to alanı / determinasyon / ayrı action) — kör manuel-partner ekleme YAPILMAZ.
- Fitting-order gibi partner ekleyen çalışan kod, `ls_failed-salesorderpartner`'ı **kontrol etmez**
  (yalnız header) → manuel partner hata verse de yutar, sipariş auto-partnerlarla yaratılır.

## 3. COMMIT "save failed" TEŞHİSİ (generic mesaj → gerçek sebep)

Sıralı, veri-odaklı (kod değil):
1. **Birim (UoM):** kalem `requestedquantityunit` malzeme için tanımlı mı?
   `SELECT DISTINCT RequestedQuantityUnit FROM i_salesorderitem WHERE Material = <matnr>` (mevcut
   siparişler hangi birimi kullanıyor) — Excel/girdi farklı birim veriyorsa save patlar.
2. **Fiyatlandırma:** benzer geçerli sipariş `TotalNetAmount > 0` mı? 0 ise koşul kaydı yok →
   sipariş fiyatlanamaz → save reddi olabilir.
3. **Malzeme/plant/depo** satış-alanına extend mi; müşteri satış-alanında (KNVV) tanımlı mı.
4. Girdi doğrulaması (fail-fast) EKLE: EML'e gitmeden birim/malzeme geçerliliğini kontrol edip
   **net mesaj** ver (generic "Kaydetme başarısız" yerine "Birim X, malzeme Y için geçersiz").

## 4. TEŞHİS ARACI — classrun ile mesaj-ID yakalama

Consumer'dan EML denemesini izole test etmek için `if_oo_adt_classrun` sınıfı; her reported
mesajı **T100 ID (sınıf+no)** ile dök (generic metin yeterli değil, ID kök-nedeni verir):

```abap
METHODS msg_line IMPORTING io_msg TYPE REF TO if_abap_behv_message RETURNING VALUE(rv) TYPE string.
...
METHOD msg_line.
  rv = io_msg->if_message~get_text( ).
  TRY.
      DATA(lo_t) = CAST if_t100_message( io_msg ).
      rv = |[{ lo_t->t100key-msgid } { lo_t->t100key-msgno }] { rv }|.   " ör. [VPD 030] ...
    CATCH cx_root.
  ENDTRY.
ENDMETHOD.
```
Uyarı: `io_msg->m_severity` DOĞRUDAN erişilir (`io_msg->if_abap_behv_message~m_severity` YANLIŞ →
"class does not contain interface" aktivasyon hatası). classrun sınıfı **taze isimle** yarat
(sil-yarat aynı isim `if_oo_adt_classrun` binding'ini bozabiliyor: "does not implement ...main").

## 5. UPDATE — mevcut siparişe kalem ekleme / miktar güncelleme

```abap
" Yeni kalem:
DATA lt_new TYPE TABLE FOR CREATE i_salesordertp\_Item.
lt_new = VALUE #( ( salesorder = <vbeln> %target = VALUE #(
  ( %cid = 'U1' product = <matnr> requestedquantity = <menge> requestedquantityunit = <vrkme>
    plant = <werks> ... %control = VALUE #( ... ) ) ) ) ).
" Mevcut kalem miktar:
DATA lt_upd TYPE TABLE FOR UPDATE i_salesordertp\\salesorderitem.
lt_upd = VALUE #( ( SalesOrder = <vbeln> SalesOrderItem = <posnr>
                    RequestedQuantity = <menge> %control-RequestedQuantity = if_abap_behv=>mk-on ) ).
MODIFY ENTITIES OF i_salesordertp
  ENTITY salesorderitem UPDATE FROM lt_upd
  ENTITY salesorder     CREATE BY \_item FROM lt_new
  MAPPED ... FAILED ... REPORTED ...
COMMIT ENTITIES RESPONSE OF ... FAILED ... REPORTED ...   " update: key bilindiğinden CONVERT KEY YOK
```

📖 Derin referans: `standards/05-coding-rap.md` · [[feedback_rap-editablefieldfor-key-create]] ·
[[feedback_rap-by-assoc-read-all-fields]] · çalışan örnek: proje `*_CL_SO_MANAGER`.

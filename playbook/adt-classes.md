---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# ABAP Class — Create, OSQLC ve Push+Activate Tam Akış

## 19. ABAP Class Yaratma ve SAP'a Push

### 24.1 Genel Bakış

`push_object.py` (SAPClient) **var olan** class objesini push ediyor.
Yeni class için önce SAP'ta obje yaratılmalı.

---

### 24.2 Adım 1 — Class Objesini SAP'ta Yarat (POST)

```python
import sys, urllib3
urllib3.disable_warnings()
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir
set_explicit_working_dir(r'<PROJECT_ROOT>')
from sap_client import SAPClient

client = SAPClient()
ac = client.adt_client

CLASS_NAME = 'ZCL_ORNEK_CLASS'
PACKAGE    = 'ZORNEK_CLC'
TRANSPORT  = '<TRANSPORT>'
DESC       = 'Aciklama'

csrf = ac.session.get(
    ac.url + '/sap/bc/adt/discovery',
    headers={'X-CSRF-Token': 'Fetch'}, verify=False
).headers.get('X-CSRF-Token', '')

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<class:abapClass xmlns:class="http://www.sap.com/adt/oo/classes"'
    ' xmlns:adtcore="http://www.sap.com/adt/core"'
    ' adtcore:description="' + DESC + '"'
    ' adtcore:name="' + CLASS_NAME + '"'
    ' class:final="true"'
    ' class:visibility="public">'
    '<adtcore:packageRef adtcore:name="' + PACKAGE + '"/>'
    '</class:abapClass>'
)

resp = ac.session.post(
    ac.url + '/sap/bc/adt/oo/classes',
    params={'corrNr': TRANSPORT},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.oo.class.v4+xml; charset=utf-8',
        'Accept': 'application/vnd.sap.adt.oo.class.v4+xml',
    },
    data=xml.encode('utf-8'),
    verify=False
)
print('Create:', resp.status_code)
# 200 veya 201 = basarili, 409 = zaten var (her ikisi de OK)
```

> **Önemli:** Create sonrası SAP otomatik lock koyar ama lock handle döndürmez.
> **SM12'den** <SAP_USER> / ZCL_ORNEK_CLASS lock'unu sil, sonra push'a geç.

---

### 24.3 Adım 2 — SM12'den Lock Sil

Transaction SM12 → User: <SAP_USER> → Object: ZCL_ORNEK_CLASS → Sil

---

### 24.4 Adım 3 — Source Push

```python
result = client.push_object(
    object_name='ZCL_ORNEK_CLASS',
    object_type='class',
    source_file=r'<PROJECT_ROOT>\ERP\ZORNEK_CLC\classes\ZCL_ORNEK_CLASS.abap',
    transport='<TRANSPORT>'
)
print(result)
# result['source_uploaded'] == True ise basarili
```

---

### 24.5 Adım 4 — Aktivasyon

```python
client.activate_object('ZCL_ORNEK_CLASS', 'class')
```

veya script ile:
```powershell
python "<PROJECT_ROOT>\scripts\activate_object.py" --cwd "<PROJECT_ROOT>" --object-type CLAS --object-name ZCL_ORNEK_CLASS
```

> ⚠ **AKTİVASYON KANITI = `adt_inactive_objects`, metadata DEĞİL.** `adtcore:version="active"`
> **boş kabuk için de "active" der** → tek başına aktivasyon kanıtı değildir. Aktif sürümü
> okuyacaksan **`?version=active` parametresini AÇIKÇA ver** — ADT'nin varsayılanı
> **İNAKTİF** sürümdür ve push ettiğin (henüz aktive edilmemiş) kodu gösterip seni
> "aktifmiş" sanmaya iter. Vaka + ölçüm: §24.9.

---

### 24.6 ExceptionResourceScanDuringSaveFailure — Kök Neden ve Çözüm

**Hata:** `[400] ExceptionResourceScanDuringSaveFailure` — "An error occurred during the save operation. The changes were not stored."

**Sebep:** SAP, kaydetme öncesi bir ön tarama yapıyor. Belirli tip kombinasyonları bu taramada reddediliyor.

**Tespit Yöntemi:** Binary search (bisect) — her seferinde daha küçük kod parçasıyla push dene, hangisinin fail ettiğini bul.

**Bu projede tespit edilen sorunlu kalıplar:**

| Sorunlu Kullanım | Neden | Çözüm |
|------------------|-------|-------|
| `TYPE RANGE OF zz1_price_code` | `zz1_price_code` data element RANGE OF için scan'i geçemiyor | `TYPE RANGE OF char12` kullan |
| `TYPE zz1_price_code` (parametre/field) | Aynı sebep | `TYPE char12` kullan |
| `TYPE zz1_discount_code` | Aynı sebep | `TYPE char3` kullan |
| `RETURNING VALUE(...) TYPE netwr` | `netwr` CURR tipi — method imzasında CURR/P DECIMALS scan tarafından reddediliyor | `TYPE wrbtr` kullan |
| `CONV netwr(...)` / `COND netwr(...)` | Aynı CURR tipi sorunu | `CONV wrbtr(...)` / `COND wrbtr(...)` kullan |

**Genel Kural:**
- Method imzasında (IMPORTING/EXPORTING/RETURNING) `CURR` tipli data element kullanma — `wrbtr`, `dmbtr` gibi `CURR` olmayan parasal tip kullan
- `RANGE OF` ile kullanacağın data element SAP'ın yerleşik tipi (örn: `kunnr`, `vkorg`, `budat`) olmalı — custom `ZZ1_*` data element'ları `RANGE OF` ile çalışmıyor, bunun yerine `char<n>` kullan
- **Method parametrelerinde (IMPORTING/EXPORTING/RETURNING) mutlaka data element ver** — `TYPE F`, `TYPE P`, `TYPE C LENGTH n` gibi built-in tip kullanma. Her zaman `TYPE wrbtr`, `TYPE matnr` gibi named data element kullan. SAP ADT scan bu kuralı zorunlu tutar.

> **TEK-EV (method-imza save-scan ailesi):** Bu §24.6 = ailenin konsolide evi. Derin reçeteler: **RANGE OF** parametre çözümü (Yol A std table-type / Yol B custom struct+ttyp) → [`coding-patterns.md`](coding-patterns.md) §22 · source-based class `TYPE c LENGTH n` (RAP bağlamı, satır-no'suz 400 bisect) → [`adt-rap.md`](adt-rap.md) §34-A. L2 görünürlük: `standards/05` §9. Gate: `check_method_param_type_c` + `check_abaplint`.

**Bisect Script Şablonu:**
```python
import sys, urllib3, tempfile, os
urllib3.disable_warnings()
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir
set_explicit_working_dir(r'<PROJECT_ROOT>')
from sap_client import SAPClient
client = SAPClient()

def try_push(src, label):
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.abap', delete=False, encoding='utf-8')
    tmp.write(src)
    tmp.close()
    result = client.push_object(object_name='ZCL_ORNEK_CLASS', object_type='class',
                                source_file=tmp.name, transport='<TRANSPORT>')
    os.unlink(tmp.name)
    ok = result.get('source_uploaded', False)
    print(f'[{"OK" if ok else "FAIL"}] {label}')
    return ok

# Minimal OK test — önce bunun geçtiğini dogrula
minimal = """CLASS zcl_ornek_class DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    METHODS constructor IMPORTING iv_test TYPE string.
ENDCLASS.
CLASS zcl_ornek_class IMPLEMENTATION.
  METHOD constructor.
  ENDMETHOD.
ENDCLASS.
"""
try_push(minimal, 'minimal baseline')

# Sonra sorunlu satırı izole et — yarısını kes, hangisinin fail ettiğini bul
```

---

### 24.7 Bilinen Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `ExceptionResourceScanDuringSaveFailure` | Kodda tarama reddeden tip var | Bisect yap — bkz 24.6 |
| `409 Conflict` (lock) | Başka lock var | SM12'den temizle, retry yapma |
| `412 PreconditionFailed` | Yanlış ETag | `source/main` endpoint'inden ETag al |
| `400 lockHandle not found` | Lock handle eksik | `push_object.py` kullan (SAPClient) — manuel PUT yapma |
| Tüm method bisect'te FAIL | Sorun IMPL'de değil DEFINITION'da | DEFINITION bölümünü bisect et |
| `does not implement if_oo_adt_classrun~main` (classrun, HTTP 200 gövdesinde) | Mesaj DOĞRU: (1) sınıf aktive edilmemiş (aktif sürüm boş kabuk) veya (2) çağıran süreç bayat stateful oturum tutuyor | (1) `adt_activate` + `adt_inactive_objects` doğrula · (2) oturum RESET. ⛔ **taze class adı DEĞİL** — bkz 24.9 |

---

### 24.8 Test include'u (`ccau`) İLK KEZ ekleniyorsa: POST ≠ PUT (İKİ AYRI ADIM)

**Ne zaman ısırır:** canlı class'ta `testclasses` include'u HENÜZ YOKSA (yani sınıfa ilk kez
birim testi ekliyorsun). Var olan bir `ccau`'yu güncellemek sıradan PUT'tur — bu bölüm
yalnız **ilk yaratım** içindir.

**ÇALIŞAN YÖNTEM — iki adım, sırayla:**

```
1) POST /sap/bc/adt/oo/classes/<cls>/includes/testclasses   → 201 Created  (include'u YARATIR)
2) PUT  /sap/bc/adt/oo/classes/<cls>/includes/testclasses   → 200 OK       (İÇERİĞİ yazar)
```

> ⚠ **POST gövdeyi YOK SAYAR.** 201 döner ama include'u SAP'nin 56 baytlık boş iskeletiyle
> (`*"* use this source file for your ABAP unit test classes`) yaratır — gönderdiğin kaynak
> ne kadar büyük olursa olsun. Ölçüm (2026-07-29): 11.639 bayt gönderildi, 56 bayt yazıldı.
> **201'i "başarı" sayıp durursan `ccau` BOŞ kalır.**

**DENENEN — BAŞARISIZ (tekrar deneme):**

| Deneme | Sonuç |
|---|---|
| `PUT .../includes/testclasses` (include yokken) | **HTTP 500** — `T100 ED 170`: *"... CCAU does not have any inactive version"* |
| `PUT .../includes/testclasses?version=inactive` | HTTP 500 (aynı) |
| `POST .../includes` + `classincludes` XML gövdesi | HTTP 500 — *"could not be created"* |

**Kök sebep:** PUT, var olan bir include'un **inactive kopyasına** yazar. Include hiç yoksa
yazacak inactive sürüm de yoktur → 500. Önce iskeleti yaratmak (POST) şart.

**SAHTE YEŞİL TUZAĞI — bu tuzağın asıl bedeli:** `ccau` boş kalırsa `adt_unit_run`
**`method_count = 0`** döner, HTTP 200 ile ve **hata vermeden** (`<aunit:runResult/>` boş).
Bu, "test altyapısı kapalı" gibi görünür ve saatlerce yanlış yerde aranır — oysa sebep
kendi push'undur. Bu yüzden:

- Aktivasyondan sonra `adt_get` ile **include listesinde `testclasses` VAR MI** doğrula.
- `ccau` kaynağını **bayt olarak** repo ile karşılaştır (mesaja değil bayta bak).
- `adt_unit_run` kabul ölçütüne **`method_count` beklenen sayıya eşit** koşulunu yaz;
  **0 = FAIL** say. "Yeşil döndü" yetmez.

📌 Aynı sınıf tuzak: CDS inline-POST boş-source (bkz. `adt-cds.md`) — POST'un gövdeyi yok
sayması ADT'de tekrar eden bir desendir. **Yaratım ve içerik ayrı adımlardır.**

---

### 24.9 `classrun` → *"does not implement if_oo_adt_classrun~main"* (2026-07-31 kök-fix)

**Semptom:** `adt_classrun <cls>` → HTTP 200 gövdesinde
`Class does not implement if_oo_adt_classrun~main!` — oysa **repo kaynağında** `INTERFACES
if_oo_adt_classrun` açıkça VAR ve `adt_syntax_check` temiz.

> ⛔ **ESKİ REÇETE YANLIŞTI — KULLANMA:** *"`adt_classrun` bu sistemde güvenilmez/bozuk;
> app-server class-load cache'i binding'i bozuyor; çare TAZE (hiç kullanılmamış) bir sınıf
> adıyla yeniden yarat."* Bu reçete **iki kez** denendi, **hiçbirinde çözmedi**, geriye iki
> gereksiz obje bıraktı ve "araç bozuk" yanlış-sonucunu 6 dokümana yaydı. Yeni class adı
> **hiçbir şeyi bust etmez** — aşağıdaki iki sebebin ikisine de dokunmaz.

**SAP'nin mesajı DOĞRUDUR.** Ardında iki bağımsız sebep vardır:

| # | Kök sebep | Nasıl ayırt edilir | Çare |
|---|---|---|---|
| 1 | **Sınıf AKTİVE EDİLMEMİŞ** — push edildi, aktif sürüm hâlâ `adt_post_shell` boş kabuğu. classrun **aktif** sürümü yükler → mesaj gerçekten doğru. | Kaynağı **`?version=active`** ile çek: boş kabuk (birkaç yüz bayt, `INTERFACES` yok). Parametresiz GET seni yanıltır → **İNAKTİF** sürümü döndürür. | `adt_activate` → sonra `adt_inactive_objects` ile **doğrula** |
| 2 | **BAYAT stateful ADT oturumu** — istemci süreç ömrü boyunca TEK `requests.Session` tutar (`x-sap-adt-sessiontype: stateful`). Obje **başka bir süreçte** aktive edildiyse bu sürecin SAP oturumu aktivasyonu görmez, eski class-load'a bağlı kalır. | Sınıfın aktif olduğu kanıtlanmışken (`adt_inactive_objects` = 0) hata **devam ediyorsa** bu sebeptir. Aynı çağrı **taze bir süreçte** anında çalışır. | **Oturum RESET** — `SAPADTClient.new_session()`; `run_classrun` bunu artık otomatik yapar |

> ⛔ **AYNI OTURUMDA RETRY ETKİSİZDİR.** Eski `run_classrun` zaten aynı session'la iki kez
> POST ediyordu; **ikisi de** aynı hatayı verdi. Çare retry değil **reset**: yeni session =
> yeni `sap-contextid` = güncel class-load. Aynı desen `jfilak/sapcli` `d223ed3c`'de:
> `activate() → new_session() → execute()`.

**⚠️ AKTİVASYON KANITI — `version="active"` metadata'sı TEK BAŞINA YETMEZ.**
`adtcore:version="active"` **boş kabuk için de "active" der** (kabuk da bir aktif sürümdür).
Aktivasyonun güvenilir kanıtı **`adt_inactive_objects`**'tir (worklist boş mu?) — ikincil
olarak aktif kaynağın **bayt/içerik** karşılaştırması. *"Aktif dedi"* ≠ *"kodun aktif"*.

**Ölçüm (2026-07-31, aynı sınıf, aynı an):** `source/main` parametresiz GET → **10.659 bayt,
arayüz VAR** · `source/main?version=active` → **192 bayt boş kabuk, arayüz YOK**. Yani
**ADT'nin varsayılan sürümü İNAKTİF'tir** — bir sürüm parametresi vermeyen her doğrulama
"var" der ve seni yanıltır.

**META-DERS (bu vakanın asıl bedeli):** teşhisi üreten fonksiyon (`_diagnose_classrun_binding`)
tam da bu tuzağa düşmüştü — `version=` vermeden okuyup **hiç aktive edilmemiş** sınıfa
"yapısal olarak geçerli" diyordu. Oradan otomatik olarak *"o hâlde tooling bozuk → taze
class adı"* reçetesi doğdu. **Yanlış veri okuyan bir teşhis, güvenle yanlış bir reçete
üretir** — ve o reçete "araç bozuk" diye terfi eder. Bkz. `lessons-learned.md` PATTERN #16
kardeş vakası.

---

## 20. ABAP Class — Inline Data / OSQLC Tip Çakışması

### 25.1 `%_##OSQLC_1` / `%_##OSQLC_2` Çakışması

**Hata:**
```
"LS" was already declared with the type "%_##OSQLC_1" and cannot be used with the type "%_##OSQLC_2" here.
```

**Sebep:** Aynı class içinde birden fazla metodda `SELECT ... INTO TABLE @DATA(lt_xxx)` kullanılınca SAP iç tip isimlerine `%_##OSQLC_1`, `%_##OSQLC_2` atar ve class scope'ta çakıştırır.

**Çözüm — her inline `@DATA(lt_xxx)` değişkenine benzersiz isim ver:**
```abap
" YANLIS — farklı metodlarda aynı isim:
SELECT ... INTO TABLE @DATA(lt_raw)   " metod A
SELECT ... INTO TABLE @DATA(lt_raw)   " metod B  <- çakışır

" DOGRU — benzersiz isimler:
SELECT ... INTO TABLE @DATA(lt_musteri_kna1_raw)
SELECT ... INTO TABLE @DATA(lt_lips_teslim_raw)
```

### 25.2 FOR Loop Değişkeni Tip Çakışması

**Hata:**
```
"LS" was already declared with the type "TY_FOO" and cannot be used with the type "TY_BAR" here.
```

**Sebep:** Aynı metod içinde `VALUE #( FOR ls IN lt_a ... )` ve `VALUE #( FOR ls IN lt_b ... )` — `ls` farklı tipte iki kez tanımlanıyor.

**Çözüm — her FOR loop'ta farklı iterasyon değişkeni kullan:**
```abap
VALUE #( FOR lf IN lt_fiyat_raw  ( ... ) )   " lf
VALUE #( FOR li IN lt_indirim_raw ( ... ) )  " li
VALUE #( FOR lm IN lt_iskonto_raw ( ... ) )  " lm
```

### 25.3 CDS `AmountInTransactionCurrency` Tip Uyumsuzluğu

**Hata:**
```
The maximum possible number of places in the expression starting with AMOUNTINTRANSACTIONCURRENCY
is 34 places with 2 decimal places. There can be, however, no more than 31 places and 14 decimal places.
```

**Sebep:** `I_OperationalAcctgDocItem-AmountInTransactionCurrency` CDS tipi CURR(34,2) — `wrbtr` (13,2) veya `p LENGTH 16 DECIMALS 2` (31,2) hedef alana sığmaz.

**Çözüm — `SUM(...)` yerine raw rows çekip ABAP'ta topla:**
```abap
TYPES: BEGIN OF ty_devir_row,
         musteri_no       TYPE kunnr,
         borc_alacak_kodu TYPE c LENGTH 1,
         tutar            TYPE p LENGTH 16 DECIMALS 2,
       END OF ty_devir_row.
DATA lt_devir_rows TYPE STANDARD TABLE OF ty_devir_row WITH EMPTY KEY.

SELECT Customer AS musteri_no,
       DebitCreditCode AS borc_alacak_kodu,
       AmountInTransactionCurrency AS tutar
  FROM i_operationalacctgdocitem
  INTO TABLE @lt_devir_rows
  WHERE ...

" ABAP'ta GROUP BY yerine LOOP + ASSIGN + toplama
LOOP AT lt_devir_rows INTO ls_row.
  ASSIGN ht_result[ musteri_no = ls_row-musteri_no ] TO FIELD-SYMBOL(<acc>).
  IF <acc> IS NOT ASSIGNED.
    INSERT VALUE #( musteri_no = ls_row-musteri_no ) INTO TABLE ht_result ASSIGNING <acc>.
  ENDIF.
  IF ls_row-borc_alacak_kodu = 'S'.
    <acc>-bakiye = <acc>-bakiye + CONV wrbtr( ls_row-tutar ).
  ELSE.
    <acc>-bakiye = <acc>-bakiye - CONV wrbtr( ls_row-tutar ).
  ENDIF.
  UNASSIGN <acc>.
ENDLOOP.
```

### 25.4 SELECTION-SCREEN Kuralları (REPORT/PROG)

| Kural | Max | Not |
|-------|-----|-----|
| SELECT-OPTIONS / PARAMETERS adı | 8 karakter | |
| RADIOBUTTON GROUP adı | 4 karakter | |
| SELECTION-SCREEN COMMENT değişkeni | 8 karakter | SAP implicit tanımlar — `DATA` ile tekrar tanımlama |
| BLOCK adı | 8 karakter | |
| TITLE değişkeni | SAP implicit tanımlar | `DATA` ile tanımlama — çakışır |

> **Enforcement:** isim-uzunluğu kuralları (SEL/PARAM≤8 · RADIOBUTTON GROUP≤4 · BLOCK≤8) `check_abaplint` (ABAP lint, isim-uzunluğu) ile denetlenebilir — her satır bağımsız length-regex.

**TITLE değişkeni için `DATA` tanımlamak YASAK:**
```abap
" YANLIS:
DATA t_bfil TYPE char40.
SELECTION-SCREEN BEGIN OF BLOCK blk_fil WITH FRAME TITLE t_bfil.
" -> "T_BFIL was already declared" hatası

" DOGRU: DATA tanımı YOK, sadece INITIALIZATION'da değer ata:
SELECTION-SCREEN BEGIN OF BLOCK blk_fil WITH FRAME TITLE t_bfil.
...
INITIALIZATION.
  t_bfil = 'Filtre Kriterleri'.
```

**SELECT-OPTIONS'a `VALUE #(` ile değer atama YASAK (bazı versiyonlarda):**
```abap
" YANLIS:
s_vkorg = VALUE #( ( sign='I' option='EQ' low='1500' ) ).  " -> syntax error

" DOGRU — INITIALIZATION'da APPEND kullan:
INITIALIZATION.
  s_vkorg-sign = 'I'. s_vkorg-option = 'EQ'. s_vkorg-low = '1500'. APPEND s_vkorg.
```

**SELECT-OPTIONS `FOR` referansı için tablo alanı yerine global DATA değişkeni kullan:**
```abap
DATA: gv_vkorg TYPE vkorg,
      gv_kunnr TYPE kunnr.

SELECT-OPTIONS s_vkorg FOR gv_vkorg.  " DOGRU
SELECT-OPTIONS s_vkorg FOR vbak-vkorg. " YANLIS — TABLES include olmadan çalışmaz
```

**SELECT-OPTIONS tablosunu typed parametreye geçirirken explicit dönüşüm yap:**
```abap
DATA lt_vkorg TYPE sd_vkorg_ranges.
DATA ls_vkorg TYPE sdsls_vkorg_range.
LOOP AT s_vkorg ASSIGNING FIELD-SYMBOL(<r>).
  ls_vkorg-sign = s_vkorg-sign. ls_vkorg-option = s_vkorg-option.
  ls_vkorg-low  = s_vkorg-low.  ls_vkorg-high   = s_vkorg-high.
  APPEND ls_vkorg TO lt_vkorg.
ENDLOOP.
" Sonra lt_vkorg'u constructor'a geçir
```

---


## 26. Push + Aktivasyon Tam Akış Örneği (MPC_EXT)

Bu projedeki başarılı `ZCL_ZSD_ORDER_MPC_EXT` push + aktivasyon akışı:

1. Lokal dosyayı düzenle: `<PROJECT_ROOT>\ERP\ZSD001_CLC\classes\ZCL_ZSD_ORDER_MPC_EXT.abap`
2. Push:
```powershell
python "<PROJECT_ROOT>\scripts\push_object.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type CLAS --object-name ZCL_ZSD_ORDER_MPC_EXT --source-file "<PROJECT_ROOT>\ERP\ZSD001_CLC\classes\ZCL_ZSD_ORDER_MPC_EXT.abap" --transport <TRANSPORT>
```
3. Aktivasyon:
```powershell
python "<PROJECT_ROOT>\scripts\activate_object.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type CLAS --object-name ZCL_ZSD_ORDER_MPC_EXT
```

---



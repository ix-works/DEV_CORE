---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# DDIC Structure, Table Type ve Z Tablo

## 12. DDIC Structure Yaratma

### Denenen ve BASARISIZ olan yollar — tekrar deneme

| Yontem | Hata | Neden Calismaz |
|--------|------|----------------|
| `create_structure.py` scripti (CLI) | "CSRF token expired" (3 retry sonra fail) | Script icindeki CSRF mekanizmasi bu sistemde uyumsuz |
| `create_structure.py` — fields JSON with `char10` format | `[ERROR] Invalid JSON` | PowerShell `--fields` argumani JSON icindeki tirnaklari bozuyor |
| `SAPClient.create_structure()` — temp Python dosyasi ile | "CSRF token expired" (3 retry sonra fail) | `SAPClient.create_structure()` icinde ayni bozuk CSRF mekanizmasi kullaniliyor — temp dosya da cozmuyor |
| PowerShell heredoc (`<< 'PY'`) | `Missing file specification after redirection operator` | PowerShell heredoc desteklemiyor — Linux bash syntax |
| `POST /sap/bc/adt/ddic/structures` — XML body icinde `structures:field` ile fields | HTTP 400 `System expected element blueSource` | Bu sistemde fields listesi XML body'de kabul edilmiyor |
| `POST /sap/bc/adt/ddic/structures` — `X-sap-adt-transport` header ile transport | HTTP 400 `Parameter corrNr could not be found` | Transport header degil query param olmali |
| `POST /sap/bc/adt/ddic/structures/{name}` — `_action=LOCK` ile lock | HTTP 406 `Unsupported Media Type` | Structures endpoint'i bu sistemde lock desteklemiyor (tum Accept header kombinasyonlari denendi) |
| `POST /sap/bc/adt/locks` — merkezi lock endpoint | HTTP 404 | Bu sistemde mevcut degil |
| `POST /sap/bc/adt/core/objectlock` | HTTP 404 | Bu sistemde mevcut degil |
| `PUT /source/main` — lock handle olmadan direkt push | HTTP 400 `Parameter lockHandle could not be found` | Lock zorunlu, atlanamaz |
| `push_object(..., object_type='TABL/DS')` | `ValueError: Unsupported object type: TABL/DS` | SAPClient string alias bekliyor: `'structure'` kullan |

### Cozum: Iki Adimli Yaklasim

**Adim 1 — Bos objeyi olustur:**

Endpoint: `POST /sap/bc/adt/ddic/structures?corrNr={TRANSPORT}`
- Transport **query param** olarak verilmeli — header degil
- Body: `blue:blueSource` XML — sadece metadata, fields yok
- HTTP 201 = basarili

```python
import sys
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')
client = SAPADTClient()

csrf = client.session.get(
    client.url + '/sap/bc/adt/discovery',
    headers={'X-CSRF-Token': 'Fetch'}, verify=False
).headers.get('X-CSRF-Token', '')

name = 'ZSD000_S_ORNEK'
xml = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<blue:blueSource\n'
    '  xmlns:blue="http://www.sap.com/wbobj/blue"\n'
    '  xmlns:abapsource="http://www.sap.com/adt/abapsource"\n'
    '  xmlns:adtcore="http://www.sap.com/adt/core"\n'
    '  adtcore:name="' + name + '"\n'
    '  adtcore:type="TABL/DS"\n'
    '  adtcore:description="Aciklama">\n'
    '  <adtcore:packageRef adtcore:name="ZSD000_CLC"/>\n'
    '</blue:blueSource>'
)
resp = client.session.post(
    client.url + '/sap/bc/adt/ddic/structures',
    params={'corrNr': '<TRANSPORT>'},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.structures.v2+xml; charset=utf-8',
    },
    data=xml.encode('utf-8'), verify=False
)
# HTTP 201 = basarili, HTTP 409 = zaten var (her ikisi de OK)
print('HTTP:', resp.status_code)
```

**Adim 2 — DDL source push + aktivasyon:**

`SAPClient.push_object()` kendi lock mekanizmasini kullaniyor — ayri lock yapmaya gerek yok.

```python
from sap_client import SAPClient
client = SAPClient()

result = client.push_object(
    object_name='ZSD000_S_ORNEK',
    object_type='structure',          # 'TABL/DS' degil — string alias kullan
    source_file=r'<PROJECT_ROOT>\ERP\ZSD000_CLC\structures\ZSD000_S_ORNEK.ddls.asddls',
    transport='<TRANSPORT>'
)
# result['success'] == True ise tamamdir
```

**DDL Source Formati** (`.ddls.asddls` uzantili dosya):
```
@EndUserText.label : 'Yapi Aciklamasi'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
define structure zsd000_s_ornek {
  alan1 : abap.char(10);
  alan2 : abap.char(50);
  alan3 : abap.char(1);
}
```

### Kritik Notlar

- **`corrNr` CREATE icin query param** — `?corrNr=TRXXXXXX` — header olarak (`X-sap-adt-transport`) gecmek 400 verir
- **`object_type='structure'`** — `'TABL/DS'` degil, SAPClient string alias bekliyor
- **Lock 406 normaldir** — `push_object()` kendi fallback lock mekanizmasini kullaniyor, elle lock almaya gerek yok
- **`WARNING: Active source differs`** mesaji normaldir — SAP pretty-printing yapiyor, aktivasyon basariliysa sorun yok
- **Dosya lokasyonu:** `ERP\{PACKAGE}\structures\{NAME}.ddls.asddls`
- **Obje zaten varsa (409):** Direkt Adim 2'ye gec, push_object uzerine yazar

---

### MCP Pattern (Sprint 6 — Doğru Sıra)

**SORUN:** `adt_struct_create` çağrısı `[OK] Structure created successfully` döner ama SAP'de yalnızca
placeholder kalır:

```
@EndUserText.label : '...'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
define structure zsd001_s_xxx {
  component_to_be_changed : abap.string(0);
}
```

Tool `verify: {ok: false}` döner → en üst seviye `ok: false` döner (post-create reviewer
yakaladıktan sonra). Coordinator bu sinyali GÖRMELİ ve "aktif ✅" rapor etmemeli.

**ÇÖZÜM PATTERN:**

```python
# 1) Shell yarat (placeholder ile)
adt_struct_create(name, fields=[...], description='TR', package='ZSD001_CLC',
                  transport='DSXKXXXXXX')  # artifact_path VERME — MCP içi reviewer timeout veriyor
# Sonuç: ok=False (verify failed — placeholder), ama shell var artık.

# 2) Full DDL push (artık shell mevcut)
adt_push_source(name, object_type='structure',
                transport='DSXKXXXXXX', skip_reviewer=True,
                source='<tam DDL>')
# Sonuç: ok=True, source_uploaded=True, activated=True

# 3) Standalone post-create doğrulama (MCP içi otomatik post-check
#    composite/atom'a eklendi — server restart ister)
python scripts/validators/check_sap_struct_consistency.py <local-artifact>
# OK — Z SAP'de tutarlı (N alan, active)
```

**Notlar:**
- `adt_struct_create` `artifact_path` parametresi MCP içi reviewer subprocess'ini başlatır,
  120s timeout aşar — `skip_reason: reviewer_timeout`. Standalone `run_review.py` ile pre-flight
  çalıştır, MCP çağrısında `artifact_path` verme.
- `adt_push_source` `object_type='tabl'` → "invalid lock handle" hatası. **`'structure'` kullan.**
- Annotations (`@AbapCatalog.foreignKey`, `with foreign key`, `with value help`,
  `@Semantics.amount.currencyCode`) sadece `push_source` ile yazılabilir — `fields[]` yöntemi
  bunları atlar.

**Bağımlı obje "inconsistent in active version":** DTEL domain'i değişirse (force-recreate gibi),
bağımlı tablo+CDS+struct cascade reactivate gerekir. Sıra: **tablo → CDS → DTEL → struct**.

---

## 13. Table Type Yaratma + Doğrulama

### Neden Dikkat Gerekiyor

`create_table_type.py` scripti bu sistemde **CALISMAZ** (403 CSRF hatasi). Ayrica SAP, table type yaratildiginda row type'i XML'den sessizce almayi bazen atlar — obje olusur ama `ROWTYPE = NULL` kalir. Bu durumda ABAP kodunda `ZSD000_TT_TAX_NUMBER` gibi tipleri kullaninca runtime hatasi alirsin, hata mesaji da belli olmaz.

**Bu yuzden yaratma sonrasi MUTLAKA dogrulama adimi yapilmali.**

---

### Adim 1 — Yaratma (POST, discovery CSRF ile)

`create_table_type.py` veya standart CSRF mekanizmasi 403 veriyor. Tek calisan yontem: **`discovery` endpoint'inden CSRF alip POST yapmak.**

```python
import sys
import urllib3
urllib3.disable_warnings()
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')

client = SAPADTClient()

TTYP_NAME = 'ZSD000_TT_ORNEK'   # degistirilecek
ROW_TYPE  = 'ZSD000_S_ORNEK'    # degistirilecek — mutlaka dogru yapi adi olmali
TRANSPORT = '<TRANSPORT>'
PACKAGE   = 'ZSD000_CLC'
DESC      = 'Aciklama'

# discovery'den CSRF al — baska endpoint 403 veriyor
csrf = client.session.get(
    client.url + '/sap/bc/adt/discovery',
    headers={'X-CSRF-Token': 'Fetch',
             'Authorization': client._get_auth_header(),
             'sap-client': client.client},
    verify=False
).headers.get('X-CSRF-Token', '')

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<ttyp:tableType xmlns:ttyp="http://www.sap.com/dictionary/tabletype"\n'
    '                xmlns:adtcore="http://www.sap.com/adt/core"\n'
    '                adtcore:name="' + TTYP_NAME + '"\n'
    '                adtcore:description="' + DESC + '">\n'
    '    <adtcore:packageRef adtcore:name="' + PACKAGE + '"/>\n'
    '    <ttyp:rowType>\n'
    '        <ttyp:typeKind>dictionaryType</ttyp:typeKind>\n'
    '        <ttyp:typeName>' + ROW_TYPE + '</ttyp:typeName>\n'
    '        <ttyp:builtInType><ttyp:dataType/><ttyp:length>000000</ttyp:length><ttyp:decimals>000000</ttyp:decimals></ttyp:builtInType>\n'
    '        <ttyp:rangeType/>\n'
    '    </ttyp:rowType>\n'
    '    <ttyp:initialRowCount>00000</ttyp:initialRowCount>\n'
    '    <ttyp:accessType>standard</ttyp:accessType>\n'
    '    <ttyp:primaryKey>\n'
    '        <ttyp:definition>standard</ttyp:definition>\n'
    '        <ttyp:kind>nonUnique</ttyp:kind>\n'
    '        <ttyp:components/>\n'
    '        <ttyp:alias/>\n'
    '    </ttyp:primaryKey>\n'
    '</ttyp:tableType>'
)

resp = client.session.post(
    client.url + '/sap/bc/adt/ddic/tabletypes',
    headers={
        'Authorization': client._get_auth_header(),
        'sap-client': client.client,
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.tabletype.v1+xml',
        'Accept': 'application/vnd.sap.adt.tabletype.v1+xml, */*',
    },
    params={'corrNr': TRANSPORT},
    data=xml.encode('utf-8'),
    verify=False, timeout=60
)
print('POST:', resp.status_code)
# 200/201 = basarili
# 400 + ExceptionResourceAlreadyExists = zaten var, sorun degil
```

---

### Adim 2 — Aktivasyon

```python
from sap_client import SAPClient
sc = SAPClient()
sc.activate_object(TTYP_NAME, 'tabletype')
print('Activated')
```

---

### Adim 3 — ZORUNLU DOGRULAMA (Row Type Kontrol)

**Yaratma ve aktivasyon sonrasi mutlaka bu sorguyu calistir:**

```powershell
python "<PROJECT_ROOT>\scripts\run_sql_query.py" --cwd "<PROJECT_ROOT>" --query "SELECT TYPENAME, ROWTYPE FROM DD40L WHERE TYPENAME LIKE 'ZSD000%'" --max-rows 20
```

**Beklenen sonuc:** `ROWTYPE` sutununda dogru yapi adi gorunmeli (ornek: `ZSD000_S_ORNEK`).

**Sorun:** `ROWTYPE = NULL` veya bos ise row type kaybolmus demektir. Bir sonraki adima gec.

---

### Adim 4 — Row Type Bozuksa Duzeltme (GET ETag + PUT)

```python
# ETag al
get_resp = client.session.get(
    client.url + '/sap/bc/adt/ddic/tabletypes/' + TTYP_NAME.lower(),
    headers={'Authorization': client._get_auth_header(),
             'sap-client': client.client,
             'Accept': 'application/vnd.sap.adt.tabletype.v1+xml, */*'},
    verify=False
)
etag = get_resp.headers.get('ETag', '')

# Ayni XML ile PUT — If-Match zorunlu
put_resp = client.session.put(
    client.url + '/sap/bc/adt/ddic/tabletypes/' + TTYP_NAME.lower(),
    params={'corrNr': TRANSPORT},
    headers={'Authorization': client._get_auth_header(),
             'sap-client': client.client,
             'X-CSRF-Token': csrf,
             'Content-Type': 'application/vnd.sap.adt.tabletype.v1+xml',
             'Accept': 'application/vnd.sap.adt.tabletype.v1+xml, */*',
             'If-Match': etag},
    data=xml.encode('utf-8'),
    verify=False, timeout=60
)
print('PUT:', put_resp.status_code)  # 200 = basarili

# Tekrar aktive et
sc.activate_object(TTYP_NAME, 'tabletype')

# Tekrar dogrula
# run_sql_query ile DD40L.ROWTYPE kontrol et
```

---

### Kritik Kurallar Ozeti

| Kural | Detay |
|-------|-------|
| `create_table_type.py` CALISMAZ | 403 CSRF hatasi — kullanma |
| CSRF kaynagi | Sadece `discovery` endpoint'inden al — baska yerden alinan token 403 verir |
| Content-Type | `application/vnd.sap.adt.tabletype.v1+xml` — v2 veya baska 415 verir |
| Namespace | `xmlns:ttyp="http://www.sap.com/dictionary/tabletype"` — baska 415 verir |
| `corrNr` | Query param olarak gec — header olarak gecme |
| HTTP 400 + AlreadyExists | Zaten var, sorun degil — direkt aktivasyon yap |
| **Aktivasyon sonrasi DD40L kontrol et** | ROWTYPE NULL olabilir — yaratma yetmez, dogrula |
| Row type bozuksa | GET ile ETag al, PUT ile guncelle, tekrar aktive et, tekrar dogrula |

---


## 15. Z Tablo (TABL/DT) Yaratma

**🎉 ÇÖZÜLDÜ — Üzerinde uzun saat çalışıldı.** Library'nin (`scripts/create_table.py` / `sap_client.create_table()`) yöntemi **bu sistemde eksik** — POST body'sine DDL koyuyor ama SAP body içindeki DDL'i **silently ignore** edip default `client : abap.clnt` koyuyor.

### 28.0 Hazır Production Script

📦 **`scripts/populate_tables.py`** — CSV-driven batch tablo yaratıcı.

```powershell
python scripts/populate_tables.py `
  --package ZSD001_CLC `
  --transport <TRANSPORT> `
  --csv ERP/SD/ZSD001_CLC/table_fields.csv `
  --cwd <PROJECT_ROOT>

# Sadece bir tablo (test):
python scripts/populate_tables.py ... --only ZSD001_T_CONTY

# Mevcut tabloyu silip yeniden yarat:
python scripts/populate_tables.py ... --force-recreate

# XML/DDL preview:
python scripts/populate_tables.py ... --dry-run
```

CSV format:
```
table_name,table_desc,delivery_class,data_maint,field_name,is_key,type,description
ZSD001_T_CONTY,Konteyner Tipleri,A,ALLOWED,MANDT,Y,MANDT,Client
ZSD001_T_CONTY,Konteyner Tipleri,A,ALLOWED,CONTY,Y,ZSD001_E_CONTY,Konteyner tipi
```

### 28.1 İki Adımlı Yaratma Pattern

```
1. POST /sap/bc/adt/ddic/tables          → Shell create (sadece metadata, DDL boş)
2. LOCK + PUT /source/main + UNLOCK      → Gerçek DDL bu adımda yazılır
3. activate_object.py                    → Aktive et
```

**Library'nin yaptığı tek-adım (POST'a DDL gömme) bu sistemde ÇALIŞMIYOR** — SAP body DDL'i ignore eder, default `client : abap.clnt` koyar.

### 28.2 Winning Pattern Detayları

#### A. Shell POST (XML body, sadece metadata):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<blue:blueSource xmlns:blue="http://www.sap.com/wbobj/blue"
                 xmlns:adtcore="http://www.sap.com/adt/core"
                 adtcore:name="ZSD001_T_CONTY"
                 adtcore:type="TABL/DT"
                 adtcore:description="Konteyner Tipleri (Master Data)"
                 adtcore:masterLanguage="TR">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/zsd001_clc"
                      adtcore:type="DEVC/K" adtcore:name="ZSD001_CLC"/>
</blue:blueSource>
```
Endpoint: `POST /sap/bc/adt/ddic/tables?corrNr={TRANSPORT}`
Content-Type: `application/vnd.sap.adt.tables.v2+xml; charset=utf-8`

#### B. DDL PUT (text/plain body):
```
@EndUserText.label : 'Konteyner Tipleri (Master Data)'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #ALLOWED
define table zsd001_t_conty {
  key mandt : mandt not null;
  key conty : zsd001_e_conty not null;
  voleh : voleh;
  @Semantics.quantity.unitOfMeasure : 'zsd001_t_conty.voleh'
  volum : volum;
  gewei : gewei;
  @Semantics.quantity.unitOfMeasure : 'zsd001_t_conty.gewei'
  ntgew : ntgew;
}
```

LOCK + PUT akışı:
```python
# 1. LOCK
lr = client.session.post(f'{client.url}/sap/bc/adt/ddic/tables/{name.lower()}',
    params={'_action':'LOCK','accessMode':'MODIFY','corrNr':TRANSPORT},
    headers={'X-CSRF-Token':csrf, 'X-sap-adt-sessiontype':'stateful',
             'Accept':'application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result'})
handle = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lr.text).group(1)

# 2. PUT source/main — If-Match GÖNDERME!
pr = client.session.put(f'{client.url}/sap/bc/adt/ddic/tables/{name.lower()}/source/main',
    params={'corrNr':TRANSPORT, 'lockHandle':handle},
    headers={'X-CSRF-Token':csrf, 'Content-Type':'text/plain; charset=utf-8'},
    data=ddl.encode('utf-8'))
# Status 200 = OK

# 3. UNLOCK
client.session.post(f'{client.url}/sap/bc/adt/ddic/tables/{name.lower()}',
    params={'_action':'UNLOCK','lockHandle':handle},
    headers={'X-CSRF-Token':csrf,'X-sap-adt-sessiontype':'stateful'})

# 4. Activate
activate_object.py --name ZSD001_T_CONTY --type table
```

### 28.3 Kritik DDL Kuralları

1. **`@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE` ZORUNLU** — eksikse "Can't save due to errors in source" hatası alırsın.

2. **`If-Match` HEADER GÖNDERME** — mesaj sınıfı (§18) ile aynı pattern! ETag content-type'a göre değiştiği için If-Match her zaman mismatch verir, ya da bizim PUT silently reject olur.

3. **MANDT field**: `key mandt : mandt not null;` — field adı `MANDT` korunur, DTEL referansı `mandt` (lowercase). SE11'de doğru "MANDT" görünür. Library default'u `client : abap.clnt` koyar — bunu kullanma, çünkü SE11'de "CLIENT" field adı görünür (istenmiyor).

4. **Non-key field'da `not null` KULLANMA — yalnız KEY field'da** `not null` koy. Library default'u her non-key'e koyar → temizle (non-key'de bazen aktivasyon çakışması verir). *(Denetlenebilir: tablo DDL'de non-key satırında `not null` = ihlal.)*

5. **Quantity (QUAN) ve Currency (CURR) field'lar için unit/currency referansı ZORUNLU annotation:**

   **Quantity → Unit (QUAN/DEC → UNIT/MEINS):**
   ```
   @Semantics.unitOfMeasure : true
   voleh : voleh;
   @Semantics.quantity.unitOfMeasure : 'zsd001_t_conty.voleh'
   volum : volum;
   ```

   **Currency → Para Birimi (CURR → CUKY/WAERS):**
   ```
   @Semantics.currencyCode : true
   waers : waers;
   @Semantics.amount.currencyCode : 'zsd001_t_xxx.waers'
   netwr : netwr;
   ```

   ⚠ **KRİTİK:** Her ikisinde de referans formatı `'TABLE_NAME.FIELD_NAME'` (qualified). Sadece `'voleh'` veya `'waers'` yazılırsa **"annotation uncomplete"** hatası verir → aktivasyon başarısız.

   **Tipik field çiftleri (SAP standart):**
   | Quantity field | Unit field | Currency field | Currency code field |
   |---|---|---|---|
   | VOLUM | VOLEH | NETWR | WAERS / WAERK |
   | NTGEW / BRGEW | GEWEI | BRUTTO | WAERS |
   | MENGE / KWMENG / LFIMG | MEINS / VRKME | DMBTR | HWAER |
   | DORQT | (custom unit) | KBETR | KONWA |

   **Annotation isimleri (case-sensitive):**
   - Quantity ref → `@Semantics.quantity.unitOfMeasure`
   - Currency ref → `@Semantics.amount.currencyCode`
   - Unit marker → `@Semantics.unitOfMeasure : true`
   - Currency code marker → `@Semantics.currencyCode : true`

6. **Field type referansı lowercase** — `mandt`, `zsd001_e_conty`, `volum`. SAP standart DTEL'leri direkt adıyla (`vkorg`, `kunnr`, `ernam`, vb.).

### 28.4 Başarısız Yolların Arşivi (referans)

| Yöntem | Sonuç |
|---|---|
| `scripts/create_table.py` library çağrısı (POST'a DDL body) | 201 ama DDL silently dropped, sadece `client : abap.clnt` görünür |
| `set_object_source()` library helper | Body PUT yapıyor ama If-Match ile mismatch → silently saved değil |
| PUT + `If-Match: <etag>` | 412 ETag mismatch (content-type'a göre ETag değişir, mismatch kaçınılmaz) |
| `@AbapCatalog.enhancement.category` eksik | 400 "Can't save due to errors in source" |
| Quantity field'da `@Semantics.quantity.unitOfMeasure : 'voleh'` (qualified değil) | Aktivasyon: "annotation uncomplete" |
| Non-key field'da `not null` + bazı durumlar | Bazen aktivasyon sırasında çakışma |

### 28.5 Disiplin Hatırlatma — Bu Bölüm Nasıl Yazıldı

Bu çözüm 2026-05-13'de bulundu. Süreç:
1. ❌ İlk hata: Doğrudan POST + DDL yaptım → SAP body'yi ignore etti
2. ❌ İkinci hata: `set_object_source()` çağrı PUT 200 dönüyor ama içerik kaydedilmiyor → If-Match mismatch'i
3. ✅ Raw PUT test: 400 "Can't save due to errors" → annotation eksikliği ortaya çıktı
4. ❌ İlk annotation pattern (`'voleh'`): "uncomplete"
5. ✅ Kullanıcı SE11 screenshot ile pattern verdi: "Ref tablo: ZSD001_T_CONTY, Ref alan: VOLEH" → annotation `'zsd001_t_conty.voleh'` formatı çözdü

**Ders:** Bu bölüm, **disiplin kuralı §1'i ihlal ettiğim için saatler harcadık**. ADT işine başlamadan ÖNCE `scripts/` klasöründeki ilgili `create_table.py`'u **detaylı incele**, library kodunda eksiklikleri tespit et, sonra adapte et.

---



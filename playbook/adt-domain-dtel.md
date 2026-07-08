---
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# DDIC Domain ve Data Element (DTEL)

## 14. DDIC Domain ve Data Element Yaratma

### Denenen ve BAŞARISIZ olan yollar — tekrar deneme

| Yöntem | Hata | Neden Çalışmaz |
|---|---|---|
| ~~`create_domain.py` / CSRF patinajı~~ **CSRF FIXED 2026-06-14** | ~~`CSRF token expired` (3 retry sonra fail)~~ | **KÖK-FIX:** (1) `_retry_request` CSRF retry'da header'ı yenilemiyordu — closure dış kapsamda kurulan bayat token her retry'da tekrar gidiyordu (create_cds_view vakası); closure içinde header yeniden kuruldu. (2) `_request_with_csrf_retry` artık 403+"CSRF validation failed"/`x-csrf-token: Required`'te force-refresh + zehirli `.csrf_token.json` otomatik temizlik yapıyor. **Elle cache silmeye gerek yok** — poison cache testiyle doğrulandı (create_cds_view + BDEF). |
| `create_dataelement.py` CLI script | (eski CSRF notu) | Yukarıdaki CSRF self-heal + payload fix (§26 satır 24) kapsamında çözüldü. |
| DTEL XML — sadece `dtel:wbobj` root (eski namespace) | HTTP 201, ama **domain bağı KAYBOLUR** (`typeName/` boş döner) | Eski namespace içeriğini parser ignore ediyor |
| DTEL XML — yeni `blue:wbobj` + `dtel:dataElement` nested, AMA eksik `adtcore` attribute'lar | HTTP 201, ama **field labels boş kalır** (`shortFieldLabel/`, vs. hep `/>`) | `responsible`, `abapLanguageVersion`, `language` attribute'ları eksikken SAP parser label içeriklerini siliyor |
| ~~DTEL PUT update — manuel lock + ETag~~ ÇÖZÜLDÜ 2026-05-14 — bkz. §26.2 | ~~406 Lock + 412 ETag mismatch~~ | MSAG pattern (LOCK doğru Accept + PUT If-Match GÖNDERME) DTEL'de de çalışıyor |
| `push_object('dataelement')` | 404 `/source/main` not found | DTEL'in `/source/main` endpoint'i yok (sadece metadata-only obje) |
| ~~**MCP `adt_dtel_create` tool**~~ **FIXED 2026-06-14** | ~~create OK (201) ama activate FAIL: `No domain or data type was defined`~~ | **KÖK-SEBEP DÜZELTİLDİ:** `sap_adt_lib.py::create_dataelement` payload'u eski `dtel:wbobj` namespace + eksik adtcore attr + `dtel:dataType` wrapper kullanıyordu → §26.2 `blue:wbobj` + nested `dtel:dataElement` + tüm adtcore attr + domain'den çekilen dataType/length/decimals (`_get_domain_typeinfo`) ile değiştirildi. Test (ZSD001_E_ZZTEST→ZSD001_D_SEVKNO): create+activate+typeName bağlı+4 label dolu+version=active PASS, sonra silindi. **MCP tool path'i fix'i alması için `/mcp` restart gerekir.** Eski not (vaka 2026-06-09 ZSD001_E_SETYPE / 2026-06-14 ZSD001_E_SEVKNO): manuel REST §26.2 hâlâ fallback olarak çalışır. |

### §26.2 DTEL Update — ÇALIŞAN PATTERN (2026-05-14)

Mevcut DTEL'in **typeName** (domain referansı) veya başka field'ını update için:

**Anahtar:** LOCK için MSAG pattern Accept header + PUT If-Match göndermeme.

```python
url = client.url + f'/sap/bc/adt/ddic/dataelements/{dtel_name.lower()}'

# 1. CSRF
csrf = client.session.get(client.url + '/sap/bc/adt/discovery',
    params={'sap-client':'100','sap-language':'TR'},
    headers={'X-CSRF-Token':'Fetch'}, verify=False).headers.get('X-CSRF-Token','')

# 2. GET mevcut XML
r = client.session.get(url, params={'sap-client':'100','sap-language':'TR'}, verify=False)
xml_orig = r.text

# 3. XML'i modify (örn. typeName değiştir)
import re
xml_new = re.sub(r'<dtel:typeName>[^<]+</dtel:typeName>',
                 f'<dtel:typeName>{NEW_DOMAIN}</dtel:typeName>', xml_orig)

# 4. LOCK — DOĞRU Accept header (anahtar!)
lock_r = client.session.post(url,
    params={'_action':'LOCK','accessMode':'MODIFY','corrNr':TRANSPORT},
    headers={
        'X-CSRF-Token': csrf,
        'X-sap-adt-sessiontype': 'stateful',
        'Accept': 'application/*,application/vnd.sap.as+xml;'
                  'dataname=com.sap.adt.lock.result',
    }, verify=False)
handle = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lock_r.text).group(1)

# 5. PUT — If-Match GÖNDERME (MSAG pattern, kritik!)
put_r = client.session.put(url,
    params={'corrNr':TRANSPORT, 'lockHandle':handle, 'accessMode':'MODIFY'},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.dataelements.v2+xml; charset=utf-8',
        'sap-client': '100', 'sap-language': 'TR',
        'X-sap-adt-sessiontype': 'stateful',
    },
    data=xml_new.encode('utf-8'), verify=False)
# Beklenen: 200

# 6. UNLOCK (try/finally garantili)
client.session.post(url, params={'_action':'UNLOCK','lockHandle':handle},
    headers={'X-CSRF-Token':csrf, 'X-sap-adt-sessiontype':'stateful'}, verify=False)

# 7. ACTIVATE
client.session.post(client.url + '/sap/bc/adt/activation',
    params={'method':'activate','preauditRequested':'true'},
    headers={'X-CSRF-Token':csrf, 'Content-Type':'application/vnd.sap.adt.activation+xml'},
    data=f'''<?xml version="1.0"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:objectReference adtcore:uri="/sap/bc/adt/ddic/dataelements/{dtel_name.lower()}"
                            adtcore:name="{dtel_name}" adtcore:type="DTEL/DE"/>
</adtcore:objectReferences>'''.encode('utf-8'),
    verify=False)
```

**Tipik kullanım:** DTEL eski sistemden kopyalanmış (built-in domain ref'i ile) → yeni Z domain'e bind etmek. Vaka 2026-05-14: ZSD001_E_* DTEL'leri (28 adet) <LEGACY_SOURCE>'dan kopyalanmıştı (typeName=BSTKD, BU_PARTNER, vb.), batch update ile ZSD001_D_* domain'lerine bağlandı (27/27 OK).

**Kritik notlar:**
- LOCK Accept header MSAG ile aynı: `application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result`
- PUT'ta **If-Match GÖNDERME** (ETag bypass — LESSONS_LEARNED #18 ile aynı pattern)
- 4 label TR korunur (XML'de hep kalır, sadece typeName değişir)
- Tablo dependency yoksa silmeden update mümkün (data kaybı yok, tip aynı)

### Çözüm: Manuel REST POST — TÜM Required Attribute'ları İçeren XML

**Anahtar bulgu:** `<blue:wbobj>` root element'inde **3 attribute zorunlu** — eksikse SAP CREATE label içeriklerini sessizce siler.

| Attribute | Değer | Eksikse |
|---|---|---|
| `adtcore:responsible` | Kullanıcı adı (ör. `<SAP_USER>`) | Labels kayıt OLMAZ |
| `adtcore:abapLanguageVersion` | `standard` | Labels kayıt OLMAZ |
| `adtcore:language` | `TR` (master language ile aynı) | Labels kayıt OLMAZ |

### 26.1.1 ⚠ KRİTİK — Domain Output Length Hesaplama

> **Sebep:** Domain'in `<doma:outputInformation><doma:length>` field'ı **input length** (`<doma:typeInformation><doma:length>`) ile **AYNI değildir**. Output length = display'de gösterilen max karakter sayısı (sign, decimal nokta, thousand separator dahil). Yanlış verirsen aktivasyonda warning:
>
> `Output length (15) is less than the calculated output length (19)`
>
> Aktivasyon başarılı olsa bile **display'de değer kesilir** (özellikle ALV/Dynpro'da QUAN/DEC için).

#### Formül (Tip Bazında)

| Tip | Output Length Formülü | Örnek |
|---|---|---|
| `CHAR`, `NUMC`, `DATS`, `TIMS`, `CLNT` | `length` | CHAR(10) → 10 |
| `INT1` | **4** (sabit, -128..127) | INT1 → 4 |
| `INT2` | **6** (sabit, -32768..32767) | INT2 → 6 |
| `INT4` | **11** (sabit, -2147483648..) | INT4(10) → 11 |
| `INT8` | **20** (sabit) | INT8 → 20 |
| `DEC`, `QUAN`, `CURR` | **`length + 4`** (sign + decimal nokta + thousand sep) | QUAN(15,3) → 19, QUAN(13,3) → 17 |

#### Neden `length + 4` (DEC/QUAN/CURR)?

QUAN(15,3) için SAP display: `-1.234.567.890,123`
- 12 integer digit + 3 decimal digit = 15 (length toplam)
- 1 sign (`-`) + 1 decimal nokta (`,`) + 2 thousand separator (`.`) = 4 ek karakter
- **Toplam display = 19**

(Türkçe locale'de virgül decimal nokta, nokta thousand separator. SAP master language TR olduğu için bu hesap geçerli.)

#### Kanonik Kaynak — `populate_domains.py`

`scripts/populate_domains.py` içindeki `calculate_output_length(datatype, length, decimals)` fonksiyonu bu formülü uygular. Manuel REST yaparken aşağıdaki XML field'ında doğru değeri yaz:

```xml
<doma:outputInformation>
  <doma:length>{output_length}</doma:length>  <!-- typeInformation/length DEĞİL -->
  ...
</doma:outputInformation>
```

#### Vaka (2026-05-14)

- 5 domain (`DORQT`, `REMQT`, `BOOKCN`, `DEMFT`, `WHOFT`) yaratılırken output length yanlış set edildi → aktivasyonda warning
- Çözüm: DELETE + RECREATE doğru output length ile (henüz DTEL yok → downstream bağımlılık yok, güvenli)
- DELETE endpoint: `DELETE /sap/bc/adt/ddic/domains/<n>?corrNr={TR}` (lock 406 dönse bile delete 200 başarılı)
- `populate_domains.py` kalıcı fix uygulandı

---

### 26.1 Domain Yaratma — Çalışan Script Şablonu

**Endpoint:** `POST /sap/bc/adt/ddic/domains?corrNr={TRANSPORT}`
**Content-Type:** `application/vnd.sap.adt.domains.v2+xml; charset=utf-8`
**Aktivasyon:** `activate_object.py --name {NAME} --type doma`

```python
import sys, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')
client = SAPADTClient()

NAME, DESC = 'ZSD001_D_DISOR', 'Sevk Emri No'
PACKAGE, TRANSPORT = 'ZSD001_CLC', '<TRANSPORT>'
DATATYPE, LENGTH = 'CHAR', 10

# 1. CSRF (sap-language=TR şart)
csrf = client.session.get(
    client.url + '/sap/bc/adt/discovery',
    params={'sap-client': '100', 'sap-language': 'TR'},
    headers={'X-CSRF-Token': 'Fetch'},
    verify=False
).headers.get('X-CSRF-Token', '')

# 2. Domain XML
length_str = str(LENGTH).zfill(6)
domain_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<doma:domain adtcore:name="{NAME}"
             adtcore:type="DOMA/DD"
             adtcore:description="{DESC}"
             adtcore:masterLanguage="TR"
             xmlns:doma="http://www.sap.com/dictionary/domain"
             xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{PACKAGE.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{PACKAGE}"/>
  <doma:content>
    <doma:typeInformation>
      <doma:datatype>{DATATYPE}</doma:datatype>
      <doma:length>{length_str}</doma:length>
      <doma:decimals>000000</doma:decimals>
    </doma:typeInformation>
    <doma:outputInformation>
      <doma:length>{output_length_str}</doma:length>  <!-- ⚠ outputLength, length DEĞİL! Bkz. §26.1.1 -->
      <doma:style>00</doma:style>
      <doma:conversionExit/>
      <doma:signExists>false</doma:signExists>
      <doma:lowercase>false</doma:lowercase>
      <doma:ampmFormat>false</doma:ampmFormat>
    </doma:outputInformation>
    <doma:valueInformation>
      <doma:valueTableRef/>
      <doma:appendExists>false</doma:appendExists>
      <doma:fixValues/>
    </doma:valueInformation>
  </doma:content>
</doma:domain>'''

# 3. POST
resp = client.session.post(
    client.url + '/sap/bc/adt/ddic/domains',
    params={'corrNr': TRANSPORT},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.domains.v2+xml; charset=utf-8',
        'Accept': 'application/vnd.sap.adt.domains.v2+xml'
    },
    data=domain_xml.encode('utf-8'),
    verify=False
)
print(resp.status_code)  # 201 = OK; 405+AlreadyExists = zaten var
```

**Domain için fixed values eklemek isteniyorsa:** `<doma:fixValues>` içine `<doma:fixValue>` element'leri ekle:
```xml
<doma:fixValues>
  <doma:fixValue>
    <doma:position>0001</doma:position>
    <doma:low>1</doma:low>
    <doma:high/>
    <doma:text>Karayolu</doma:text>
  </doma:fixValue>
  ...
</doma:fixValues>
```

#### 26.1.2 MEVCUT domaine fixed-value EKLEME (UPDATE) — ÇALIŞAN PATTERN (2026-07-03)

`adt_domain_create` (MCP) yalnız CREATE. **Mevcut** domaine sabit değer eklemek = UPDATE → raw-REST (DTEL §26.2 deseninin domain uyarlaması). Kanıt: `ZSD001_D_SETYPE`'a DSK_SE/FIH_SE eklendi, readback `version=active` PASS.

Sıra: (1) GET fresh domain XML → (2) `<doma:fixValues>` içine yeni `<doma:fixValue>` kayıtları ekle (position sırayla artan; low=değer, text=TR açıklama) → (3) `lock_object` → (4) **PUT (If-Match GÖNDERME**, MSAG/DTEL pattern) → (5) `unlock_object` (try/finally) → (6) `activate_object` → (7) **readback GET** ile tüm değerlerin (eski+yeni) aktif + TR metinlerin doğru olduğunu DOĞRULA (ADR 0005-D).

⚠️ **KRİTİK TUZAK — 406 ResourceNotAcceptable:** PUT header'ında **hem `Accept` HEM `Content-Type`** = `application/vnd.sap.adt.domains.v2+xml` olmalı. `Accept`'i default (`core.v1`) bırakırsan **406** alırsın. (DTEL'de Accept'in LOCK'ta doğru olması yeterdi; domain UPDATE'te PUT'un kendisinde de şart.)

**Not:** Additive fixed-value non-breaking (bağlı tablo/DTEL yalnız yeni değerleri görür). Aktivasyonda bağlı tablolar için "dönüştürülmeli" type=I info dönebilir — yapısal ALTER gerekmez, hata değil.

### 26.2 Data Element Yaratma — Çalışan Script Şablonu

**Endpoint:** `POST /sap/bc/adt/ddic/dataelements?corrNr={TRANSPORT}`
**Content-Type:** `application/vnd.sap.adt.dataelements.v2+xml; charset=utf-8`
**Aktivasyon:** `activate_object.py --name {NAME} --type dtel`

**⚠ KRİTİK — `blue:wbobj` root attribute'ları:**
- `adtcore:responsible="<SAP_USER>"` — eksikse labels kayıt olmaz
- `adtcore:abapLanguageVersion="standard"` — eksikse labels kayıt olmaz
- `adtcore:language="TR"` — eksikse labels kayıt olmaz

```python
import sys, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')
client = SAPADTClient()

NAME, DESC = 'ZSD001_E_DISOR', 'Sevk Emri Numarası'
DOMAIN = 'ZSD001_D_DISOR'
PACKAGE, TRANSPORT = 'ZSD001_CLC', '<TRANSPORT>'
DATATYPE, LENGTH = 'CHAR', '000010'   # 6-char zero-padded
DECIMALS = '000000'

# TR labels — max length: short=10, medium=20, long=40, heading=55
SHORT  = 'Sevk Emri'
MEDIUM = 'Sevk Emri No'
LONG   = 'Sevk Emri Numarası'
HEAD   = 'Sevk Emri Numarası'

# 1. CSRF
csrf = client.session.get(
    client.url + '/sap/bc/adt/discovery',
    params={'sap-client': '100', 'sap-language': 'TR'},
    headers={'X-CSRF-Token': 'Fetch'},
    verify=False
).headers.get('X-CSRF-Token', '')

# 2. DTEL XML — TÜM zorunlu attribute'lar dahil
dtel_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<blue:wbobj adtcore:responsible="<SAP_USER>"
            adtcore:masterLanguage="TR"
            adtcore:abapLanguageVersion="standard"
            adtcore:name="{NAME}"
            adtcore:type="DTEL/DE"
            adtcore:description="{DESC}"
            adtcore:language="TR"
            xmlns:blue="http://www.sap.com/wbobj/dictionary/dtel"
            xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{PACKAGE.lower()}"
                      adtcore:type="DEVC/K"
                      adtcore:name="{PACKAGE}"/>
  <dtel:dataElement xmlns:dtel="http://www.sap.com/adt/dictionary/dataelements">
    <dtel:typeKind>domain</dtel:typeKind>
    <dtel:typeName>{DOMAIN}</dtel:typeName>
    <dtel:dataType>{DATATYPE}</dtel:dataType>
    <dtel:dataTypeLength>{LENGTH}</dtel:dataTypeLength>
    <dtel:dataTypeDecimals>{DECIMALS}</dtel:dataTypeDecimals>
    <dtel:shortFieldLabel>{SHORT}</dtel:shortFieldLabel>
    <dtel:shortFieldLength>{len(SHORT)}</dtel:shortFieldLength>
    <dtel:shortFieldMaxLength>10</dtel:shortFieldMaxLength>
    <dtel:mediumFieldLabel>{MEDIUM}</dtel:mediumFieldLabel>
    <dtel:mediumFieldLength>{len(MEDIUM)}</dtel:mediumFieldLength>
    <dtel:mediumFieldMaxLength>20</dtel:mediumFieldMaxLength>
    <dtel:longFieldLabel>{LONG}</dtel:longFieldLabel>
    <dtel:longFieldLength>{len(LONG)}</dtel:longFieldLength>
    <dtel:longFieldMaxLength>40</dtel:longFieldMaxLength>
    <dtel:headingFieldLabel>{HEAD}</dtel:headingFieldLabel>
    <dtel:headingFieldLength>{len(HEAD)}</dtel:headingFieldLength>
    <dtel:headingFieldMaxLength>55</dtel:headingFieldMaxLength>
    <dtel:searchHelp/>
    <dtel:searchHelpParameter/>
    <dtel:setGetParameter/>
    <dtel:defaultComponentName/>
    <dtel:deactivateInputHistory>false</dtel:deactivateInputHistory>
    <dtel:changeDocument>false</dtel:changeDocument>
    <dtel:leftToRightDirection>false</dtel:leftToRightDirection>
    <dtel:deactivateBIDIFiltering>false</dtel:deactivateBIDIFiltering>
  </dtel:dataElement>
</blue:wbobj>'''

# 3. POST — header'larda sap-language=TR + sap-client=100
resp = client.session.post(
    client.url + '/sap/bc/adt/ddic/dataelements',
    params={'corrNr': TRANSPORT, 'sap-language': 'TR'},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.dataelements.v2+xml; charset=utf-8',
        'Accept': 'application/vnd.sap.adt.dataelements.v2+xml',
        'sap-client': '100',
        'sap-language': 'TR',
    },
    data=dtel_xml.encode('utf-8'),
    verify=False
)
print(resp.status_code)  # 201 = OK
```

### 26.3 Aktivasyon

Hem Domain hem DTEL için `activate_object.py` çalışıyor:

```powershell
$script = "<PROJECT_ROOT>\scripts\activate_object.py"

# Domain
python $script --cwd "<PROJECT_ROOT>" --name ZSD001_D_DISOR --type doma

# DTEL
python $script --cwd "<PROJECT_ROOT>" --name ZSD001_E_DISOR --type dtel
```

### 26.4 Doğrulama

GET ile labels kontrol et — utf-8 output şart (Turkish ı için):

```python
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

r = client.session.get(
    client.url + f'/sap/bc/adt/ddic/dataelements/{NAME.lower()}',
    headers={'Accept': 'application/vnd.sap.adt.dataelements.v2+xml'},
    params={'sap-language': 'TR'},
    verify=False
)
# Beklenen: 4 label da dolu (shortFieldLabel, mediumFieldLabel, longFieldLabel, headingFieldLabel)
```

### 26.5 Kritik Notlar — TEKRAR ETMEMEK İÇİN

- **Eski namespace KULLANMA** — `<dtel:wbobj xmlns:dtel="http://www.sap.com/wbobj/dictionary/dtel">` (root) silently empty döner. Mutlaka `<blue:wbobj xmlns:blue="...wbobj/dictionary/dtel">` + nested `<dtel:dataElement xmlns:dtel="...adt/dictionary/dataelements">` kullan.
- **3 attribute eksikse labels kayıt olmaz** — `responsible`, `abapLanguageVersion`, `language`.
- **Library scripts (`create_domain.py`, `create_dataelement.py`) bu sistemde çalışmaz** — manuel REST kullan.
- **Length 6-char zero-padded:** `000010`, decimals `000000`.
- **Turkish karakterler:** XML UTF-8 encode + Content-Type charset=utf-8 + Python output UTF-8 redirect.
- **sap-language=TR** hem query param hem header — ikisinde de gönder.
- **Update gerekirse:** Bu sistemde DTEL PUT update sorunlu (Lock/ETag çakışması). Düzeltmek için → DELETE + tekrar CREATE yap. `DELETE /sap/bc/adt/ddic/dataelements/{name}?corrNr={TRANSPORT}` çalışır.

### 26.6 Built-in Tip DTEL'leri (DATS, INT2, INT4, TIMS) — Domain Adı Olarak Kullanılır

**Kritik (2026-05-13 Sprint 1B):** SAP'de `BUILTIN` diye ayrı bir `typeKind` YOK. Built-in tipte (tarih, integer, time vs.) DTEL yaratırken aslında:
- `<dtel:typeKind>domain</dtel:typeKind>`
- `<dtel:typeName>DATS</dtel:typeName>` (data type'ı **aynı zamanda built-in domain adı**)

| Built-in Type | typeName | dataType | length |
|---|---|---|---|
| Tarih | `DATS` | `DATS` | `000008` |
| Saat | `TIMS` | `TIMS` | `000006` |
| Tam sayı 1B | `INT1` | `INT1` | `000003` |
| Tam sayı 2B | `INT2` | `INT2` | `000005` |
| Tam sayı 4B | `INT4` | `INT4` | `000010` |
| Tam sayı 8B | `INT8` | `INT8` | `000019` |

**Yanlış yöntem (deneme yapıldı, fail):**
```xml
<dtel:typeKind>BUILTIN</dtel:typeKind>
<dtel:typeName></dtel:typeName>  <!-- BOŞ -->
<dtel:dataType>DATS</dtel:dataType>
```
→ Aktivasyon hatası: `No domain or data type was defined`

**Doğru yöntem:**
```xml
<dtel:typeKind>domain</dtel:typeKind>
<dtel:typeName>DATS</dtel:typeName>  <!-- DATS, INT2, INT4 vb. -->
<dtel:dataType>DATS</dtel:dataType>
<dtel:dataTypeLength>000008</dtel:dataTypeLength>
```
→ Aktivasyon başarılı.

**Production tool:** `scripts/populate_dataelements.py` (Playbook §14.2 pattern'i + bu kural).
CSV'de `type_kind=domain` ve `type_name=DATS/INT2/...` koy, scripti çalıştır.

---



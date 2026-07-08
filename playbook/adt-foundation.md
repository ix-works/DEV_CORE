---
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# ADT Foundation — Logon, Download, Push, Lock, SQL, Paket, Transport, Search, Where-Used, ATC, OData Metadata

## 1. BAĞLANTI KONTROLÜ (LOGON)

**Script:** `run_check_logon.py`

```powershell
python "<PROJECT_ROOT>\scripts\run_check_logon.py" --conn "<PROJECT_ROOT>\.conn_adt"
```

**Başarı göstergesi:** `Logon successful` veya `200 OK`

---

## 2. OBJE İNDİRME (download_object)

**Script:** `download_object.py`

### 2.1 ABAP Class (CLAS)

```powershell
python "<PROJECT_ROOT>\scripts\download_object.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type CLAS --object-name ZCL_ORNEK_CLASS --output-dir "<PROJECT_ROOT>\ERP\ZPKG_ADI\classes"
```

**⚠ Klasör kuralı:** Package adıyla eşleşen klasör altına kaydet.
- Class → `ERP\{PACKAGE}\classes\`
- CDS → `ERP\{PACKAGE}\cds\`
- Function Group → `ERP\{PACKAGE}\functions\`

### 2.2 CDS View (DDLS)

```powershell
python "<PROJECT_ROOT>\scripts\download_object.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type DDLS --object-name ZSD001_C_SO_ITEM --output-dir "<PROJECT_ROOT>\ERP\ZSD001_CLC\cds"
```

### 2.3 Function Group (FUGR)

```powershell
python "<PROJECT_ROOT>\scripts\download_object.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type FUGR --object-name ZSD001_FM_GROUP --output-dir "<PROJECT_ROOT>\ERP\ZSD001_CLC\functions"
```

---

## 3. KAYNAK YÜKLEME VE AKTİVASYON (push_object)

### 3.0a ABAP Include + Ana Program Tam Akışı — ZORUNLU KURAL (11 Mayıs 2026)

**YANLIŞ YÖNTEM:** `programs/programs` endpoint'ine `programType="I"` göndermek.
SAP bu parametreyi sessizce görmezden gelir, obje `executableProgram` tipinde yaratılır.
Aktivasyonda `"The REPORT/PROGRAM statement is missing, or the program type is INCLUDE"` hatası alırsın.

#### ⚠ ZORUNLU KURAL — TITLE (Başlık)

Yeni program yaratmadan önce kullanıcıdan **TITLE** bilgisini iste.
- Ana program `adtcore:description` alanına TITLE yaz (örn. `"Teslimat Plan Kalemleri Raporu"`)
- Her include'un `adtcore:description` alanına TITLE + include suffix'i yaz:
  - TOP include → `"Teslimat Plan Kalemleri Raporu - TOP"`
  - SEL include → `"Teslimat Plan Kalemleri Raporu - SEL"`
  - F01 include → `"Teslimat Plan Kalemleri Raporu - F01"`
  - ALV include → `"Teslimat Plan Kalemleri Raporu - ALV"`
- TITLE olmadan program yaratma — kullanıcıya sor.

**DOĞRU SIRALAMA:**
1. Kullanıcıdan TITLE al
2. Önce tüm include'ları `programs/includes` endpoint'i ile boş yarat (description = TITLE + suffix)
3. Sonra ana programı `programs/programs` endpoint'i ile boş yarat (description = TITLE)
4. Sonra include'lara boş source push et (`*INCLUDE_ADI` tek satır yorum yeterli)
5. Sonra ana programa boş source push et (`REPORT prog_adi.` tek satır yeterli)
6. Hepsini tek aktivasyon isteğinde birlikte aktive et (önce include'lar, sonra ana program)
7. Aktivasyon başarılı olduktan sonra gerçek source'ları push edip tekrar aktive et

---

#### ⚠ ZORUNLU KURAL — masterLanguage = TR (11 Mayıs 2026)

SAP, `adtcore:masterLanguage="TR"` body attribute'unu ve `sap-language` header'ını **görmezden gelir**.
Objenin TR dilde yaratılması için tek çalışan yöntem:

**Login isteğinde (`/sap/bc/adt/discovery`) `sap-client` ve `sap-language` parametrelerini birlikte URL query param olarak vermek:**

```python
s = requests.Session()
s.auth = (user, pw)
s.verify = False
# KRITIK: sap-client ve sap-language ayni istekte, query param olarak
r_login = s.get(url + '/sap/bc/adt/discovery',
    params={'sap-client': '100', 'sap-language': 'TR'},
    headers={'X-CSRF-Token': 'Fetch'})
csrf = r_login.headers.get('X-CSRF-Token', '')
```

**Ek kural — isim daha önce hiç yaratılmamış olmalı:**
SAP, daha önce EN olarak yaratılıp silinmiş bir isim için tekrar EN atar (metadata önbelleği).
Eğer obje daha önce EN olarak yaratılmışsa, **farklı bir isim kullan** (test ismiyle yarat, sil, asıl isimle yarat).
Örnek: `ZSD001_P_SCHED_ITEMS` → önce `ZSD001_P_SCHED_ITEMSs` ile TR doğrulandı, sonra asıl isim TR çıktı.

**Her CREATE isteği için yeni session açmak gerekebilir** — aynı session'da arka arkaya yaratılan objelerde SAP ilk yaratmayı TR, sonrakileri EN yapabilir. Her obje için ayrı session açmak en güvenli yöntemdir.

---

#### Adım 1 — Include Yarat (`PROG/I`)

```python
def create_include(name, desc):
    s = requests.Session()
    s.auth = (user, pw)
    s.verify = False
    r_login = s.get(url + '/sap/bc/adt/discovery',
        params={'sap-client': '100', 'sap-language': 'TR'},
        headers={'X-CSRF-Token': 'Fetch'})
    csrf = r_login.headers.get('X-CSRF-Token', '')
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<include:abapInclude xmlns:include="http://www.sap.com/adt/programs/includes"'
        ' xmlns:adtcore="http://www.sap.com/adt/core"'
        ' adtcore:description="' + desc + '"'
        ' adtcore:name="' + name + '"'
        ' adtcore:responsible="<SAP_USER>">'
        '<adtcore:packageRef adtcore:name="' + PACKAGE + '"/>'
        '</include:abapInclude>'
    )
    r = s.post(url + '/sap/bc/adt/programs/includes',
        params={'corrNr': TRANSPORT},
        headers={'X-CSRF-Token': csrf,
                 'Content-Type': 'application/vnd.sap.adt.programs.include.v2+xml; charset=utf-8',
                 'Accept': 'application/vnd.sap.adt.programs.include.v2+xml'},
        data=body.encode('utf-8'), verify=False)
    return r.status_code  # 200/201 = basarili
```

#### Adım 2 — Ana Program Yarat (`PROG/P`)

```python
def create_program(name, desc):
    csrf = get_csrf()
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<program:abapProgram xmlns:program="http://www.sap.com/adt/programs/programs"'
        ' xmlns:adtcore="http://www.sap.com/adt/core"'
        ' adtcore:description="' + desc + '"'
        ' adtcore:name="' + name + '"'
        ' adtcore:responsible="<SAP_USER>">'
        '<adtcore:packageRef adtcore:name="' + PACKAGE + '"/>'
        '</program:abapProgram>'
    )
    r = ac.session.post(
        ac.url + '/sap/bc/adt/programs/programs',
        params={'corrNr': TRANSPORT},
        headers={'X-CSRF-Token': csrf,
                 'Content-Type': 'application/vnd.sap.adt.programs.program.v2+xml; charset=utf-8',
                 'Accept': '*/*'},
        data=body.encode('utf-8'), verify=False)
    return r.status_code  # 200/201 = basarili
```

#### Adım 3 & 4 — Boş Source Push

Include için endpoint `programs/includes`, ana program için `programs/programs`:

```python
def push_source(name, source, is_include=False):
    csrf = get_csrf()
    ep = 'includes' if is_include else 'programs'
    src_get = ac.session.get(
        ac.url + f'/sap/bc/adt/programs/{ep}/{name.lower()}/source/main',
        headers={'Accept': 'text/plain'}, verify=False)
    etag = src_get.headers.get('ETag', '').strip('"')
    r = ac.session.put(
        ac.url + f'/sap/bc/adt/programs/{ep}/{name.lower()}/source/main',
        params={'corrNr': TRANSPORT},
        headers={'X-CSRF-Token': csrf, 'Content-Type': 'text/plain; charset=utf-8',
                 'If-Match': etag},
        data=source.encode('utf-8'), verify=False)
    return r.status_code  # 200 = basarili

# Include icin boş source: '*INCLUDE_ADI\n'
# Ana program icin boş source: 'REPORT prog_adi.\n'
push_source('ZSD001_I_TOP', '*ZSD001_I_TOP\n', is_include=True)
push_source('ZSD001_P_SCHED_ITEMS', 'REPORT zsd001_p_sched_items.\n', is_include=False)
```

#### Adım 5 — Tek Aktivasyon (önce include'lar, sonra ana program)

```python
def activate(obj_list):
    # obj_list: [(name, adt_type, endpoint), ...]
    # ornek: [('ZSD001_I_TOP','PROG/I','includes'), ('ZSD001_P_SCHED_ITEMS','PROG/P','programs')]
    csrf = get_csrf()
    refs = ''.join([
        f'<adtcore:objectReference adtcore:uri="/sap/bc/adt/programs/{ep}/{n.lower()}"'
        f' adtcore:type="{t}" adtcore:name="{n}"/>'
        for n, t, ep in obj_list
    ])
    act_body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
        + refs +
        '</adtcore:objectReferences>'
    )
    r = ac.session.post(
        ac.url + '/sap/bc/adt/activation',
        params={'method': 'activate', 'preauditRequested': 'true'},
        headers={'X-CSRF-Token': csrf,
                 'Content-Type': 'application/vnd.sap.adt.activation.request+xml; charset=utf-8',
                 'Accept': 'application/vnd.sap.adt.activation.result+xml'},
        data=act_body.encode('utf-8'), verify=False)
    return r  # type="E" varsa hata
```

#### Adım 6 — Gerçek Source Push + Tekrar Aktivasyon

Boş aktivasyon başarılı olduktan sonra gerçek `.abap` dosyalarını aynı `push_source` fonksiyonu ile push et, ardından aynı `activate` fonksiyonu ile tekrar aktive et.

**Bilinen Hatalar:**
- `programs/programs` ile `programType="I"` → sessizce `executableProgram` olur → KULLANMA
- Include aktivasyonunda `"REPORT/PROGRAM statement missing"` → include yanlış tipte yaratılmış demektir, sil ve `programs/includes` ile yeniden yarat
- Ana program aktivasyonunda include'lar da listeye ekle, yoksa `"Include not found"` alırsın

#### 3.0a-2 — EXIT/CUSTOMER include aktivasyonu (STANDART programa bağlı, ör. SAPMV50A) — DERS 2026-06-22

**Senaryo (yukarıdakinden FARKLI):** Include DOĞRU tipte (`PROG/I`) yaratılmış ve standart bir
programa bağlı (ör. `ZSD000_I_50MOVE_FIELD_TO_LIPS`, kullanıcı MV50AFZ1 `USEREXIT_MOVE_FIELD_TO_LIPS`
içine INCLUDE etmiş). `adt_get` metadata → `include:contextRef ... name="SAPMV50A" type="PROG/P"`.

**Belirti:** `adt_activate(object_type="include"/"prog")` → `"REPORT/PROGRAM statement is missing,
or the program type is INCLUDE"`. Bu **sil-yeniden-yarat vakası DEĞİL** (include zaten doğru) →
gateway'in "include doğası, beklenen, zararsız" diye GEÇİŞTİRMESİ YANLIŞ (push ≠ aktif;
[[feedback_arac-basarisizligini-zararsiz-sayma]]). Include tek başına derlenemez.

**DOĞRU yol — bağlam programı üzerinden aktive et:**
- Source PUT kalıcıdır (`programs/includes/<name>/source/main`), ama "aktif sürüm" = bağlam
  programının (SAPMV50A) yeniden derlenmesi.
- Aktivasyon objectReference'ını **include yerine bağlam programına** ver:
  `POST /sap/bc/adt/activation?method=activate`, uri=`/sap/bc/adt/programs/programs/sapmv50a`,
  name=`SAPMV50A`, type=`PROG/P`. (MCP: `adt_activate(name="SAPMV50A", object_type="program")`.)
- ⚠️ **ADR 0005-A gri bölge:** Standart programın **source'una YAZMIYORUZ** (yalnız derletiyoruz),
  ama yine de standart-obje-aktivasyonu → **lider/kullanıcı onayı ile, bilinçli** yapılır; sessiz
  otomasyon YOK. Include source-PUT'u serbest (Z obje); aktivasyon adımı flag'lenir.
- Alternatif: tek-obje yolu (`also` olmadan, include URI) bağlam programını çözmez → kullanma.
- Acil durumda kullanıcı SE80/ADT GUI'den bağlam programını aktive edebilir (kanıtlı çözüm).

---

### 3.0 ABAP Program (PROG/P) Yaratma ve Push — CALISTIRILMIS YONTEM

`create_object.py` ve `push_object.py` bu sistemde PROG/P icin 403/404 veriyor. Calistirilmis yontem:

**Adim 1 — Program Yarat (POST):**
```python
import sys, urllib3, xml.etree.ElementTree as ET
urllib3.disable_warnings()
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir
set_explicit_working_dir(r'<PROJECT_ROOT>')
from sap_client import SAPClient

client = SAPClient()
ac = client.adt_client
safe = lambda t: t.encode('ascii', 'replace').decode('ascii') if isinstance(t, str) else str(t)

PROG_NAME = 'ZPROG_ADIN'
PACKAGE   = 'ZPKG_ADIN'
TRANSPORT = '<TRANSPORT>'
DESC      = 'Aciklama'

csrf_resp = ac.session.get(
    ac.url + '/sap/bc/adt/discovery',
    headers={'X-CSRF-Token': 'Fetch'},
    verify=False
)
csrf = csrf_resp.headers.get('X-CSRF-Token', '')

create_body = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<program:abapProgram xmlns:program="http://www.sap.com/adt/programs/programs"'
    ' xmlns:adtcore="http://www.sap.com/adt/core"'
    ' adtcore:description="' + DESC + '"'
    ' adtcore:name="' + PROG_NAME + '"'
    ' adtcore:responsible="<SAP_USER>">'
    '<adtcore:packageRef adtcore:name="' + PACKAGE + '"/>'
    '</program:abapProgram>'
)

create_resp = ac.session.post(
    ac.url + '/sap/bc/adt/programs/programs',
    params={'corrNr': TRANSPORT},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.programs.program.v2+xml; charset=utf-8',
        'Accept': 'application/vnd.sap.adt.programs.program.v2+xml'
    },
    data=create_body.encode('utf-8'),
    verify=False
)
print('Create status:', create_resp.status_code)  # 200 veya 201 = basarili
```

> **UYARI:** Program create edilince SAP otomatik enqueue lock koyar ve lock handle'i disariya vermez.
> SM12'den <SAP_USER> / ZPROG_ADIN lock'unu silmeden push yapilamaz.
> create_resp sonrasi HEMEN asagidaki push adimina gecme — once SM12'den lock'u sil.

**Adim 2 — SM12'den Lock Sil:**
- Transaction SM12 -> User: <SAP_USER> -> Object: ZPROG_ADIN -> Sil

**Adim 3 — Source Push + Aktivasyon:**
```python
# (ayni session'da devam)

with open(r'C:\yol\ZPROG_ADIN.abap', 'r', encoding='utf-8') as f:
    source = f.read()

# Source ETag'ini al (program obje ETag'inden FARKLI)
src_get = ac.session.get(
    ac.url + '/sap/bc/adt/programs/programs/' + PROG_NAME.lower() + '/source/main',
    headers={'Accept': 'text/plain'},
    verify=False
)
etag = src_get.headers.get('ETag', '').strip('"')

# PUT with ETag + corrNr as query param
put_resp = ac.session.put(
    ac.url + '/sap/bc/adt/programs/programs/' + PROG_NAME.lower() + '/source/main',
    params={'corrNr': TRANSPORT},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'text/plain; charset=utf-8',
        'If-Match': etag,
    },
    data=source.encode('utf-8'),
    verify=False
)
print('Push status:', put_resp.status_code)  # 200 = basarili

# Aktivasyon
act_body = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
    '<adtcore:objectReference'
    ' adtcore:uri="/sap/bc/adt/programs/programs/' + PROG_NAME.lower() + '"'
    ' adtcore:type="PROG/P"'
    ' adtcore:name="' + PROG_NAME + '"/>'
    '</adtcore:objectReferences>'
)
act_resp = ac.session.post(
    ac.url + '/sap/bc/adt/activation',
    params={'method': 'activate', 'preauditRequested': 'true'},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.activation.request+xml; charset=utf-8',
        'Accept': 'application/vnd.sap.adt.activation.result+xml'
    },
    data=act_body.encode('utf-8'),
    verify=False
)
print('Activate status:', act_resp.status_code)
if 'type="E"' in act_resp.text:
    print('ERRORS:', safe(act_resp.text[:3000]))
else:
    print('[OK] Activated')
```

**Bilinen Hatalar:**
- `412 PreconditionFailed`: Yanlis ETag — program obje ETag'i degil, `source/main` ETag'ini kullan
- `423 InvalidLockHandle`: SM12'den lock silinmemis — once SM12 yap
- `400 Parameter corrNr not found`: `corrNr`'i header degil query param olarak gonder
- `TEXT-xxx cannot be modified`: Kod icinde `TEXT-xxx = '...'` yazma — selection screen title/comment icin `tit1`, `com01` gibi serbest degisken kullan (`INITIALIZATION` blogunda atanabilir)

---

**Script:** `push_object.py`

### 3.1 Class Method Push (Genel Akış)

```powershell
python "<PROJECT_ROOT>\scripts\push_object.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type CLAS --object-name ZCL_ORNEK_CLASS --source-file "<PROJECT_ROOT>\ERP\ZPKG\classes\ZCL_ORNEK_CLASS.abap" --transport <TRANSPORT>
```

### 3.2 Function Module Push (FUNC/FF)

> 📌 **FM işine başlamadan [`adt-fugr-functions.md`](adt-fugr-functions.md)'i de oku** (FM-özgü create+imza+RFC+başarısız-yollar). Kanonik helper: `sap_adt_lib.set_function_module_source()` (aşağıdaki sıkı lock→PUT→activate→unlock pattern'ini sarar). **İmza satır-içi ABAP cümleleriyle yazılır (`*"` comment-block DEĞİL — reddedilir). `set_object_source()` FM'de 423 verir, kullanma.**

`push_object.py` FUNC tipini desteklemiyor. `SAPADTClient` ile doğrudan ADT endpoint kullanılır:

```python
import sys, xml.etree.ElementTree as ET
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')
client = SAPADTClient()
safe = lambda t: t.encode('ascii', 'replace').decode('ascii')
FM_NAME = 'zsd001_fm_baglanti_bakiye'   # küçük harf
TRANSPORT = '<TRANSPORT>'
with open(r'<PROJECT_ROOT>\ERP\ZSD001\functions\ZSD001_FM_BAGLANTI_BAKIYE.abap', 'r', encoding='utf-8') as f:
    source = f.read()
csrf = client.session.get(client.url + '/sap/bc/adt/discovery',
    headers={'X-CSRF-Token': 'Fetch'}, verify=False).headers.get('X-CSRF-Token', '')
lock_url = client.url + f'/sap/bc/adt/functions/groups/{FM_NAME}/fmodules/{FM_NAME}'
lock_resp = client.session.post(lock_url,
    params={'_action': 'LOCK', 'accessMode': 'MODIFY'},
    headers={'X-CSRF-Token': csrf, 'Content-Type': 'application/vnd.sap.as+xml',
             'Accept': 'application/vnd.sap.adt.lock.v1+xml', 'X-sap-adt-corrNr': TRANSPORT},
    data='', verify=False)
handle = next((e.text for e in ET.fromstring(lock_resp.text).iter() if e.tag.endswith('LOCK_HANDLE')), None)
push_resp = client.session.put(
    client.url + f'/sap/bc/adt/functions/groups/{FM_NAME}/fmodules/{FM_NAME}/source/main',
    params={'lockHandle': handle, 'corrNr': TRANSPORT},
    headers={'X-CSRF-Token': csrf, 'Content-Type': 'text/plain; charset=utf-8'},
    data=source.encode('utf-8'), verify=False)
client.session.post(lock_url, params={'_action': 'UNLOCK', 'lockHandle': handle},
    headers={'X-CSRF-Token': csrf}, verify=False)
act_body = f'''<?xml version="1.0" encoding="utf-8"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:objectReference adtcore:uri="/sap/bc/adt/functions/groups/{FM_NAME}/fmodules/{FM_NAME}"
                            adtcore:type="FUNC/FF" adtcore:name="{FM_NAME.upper()}"/>
</adtcore:objectReferences>'''
act_resp = client.session.post(client.url + '/sap/bc/adt/activation',
    params={'method': 'activate', 'preauditRequested': 'true'},
    headers={'X-CSRF-Token': csrf,
             'Content-Type': 'application/vnd.sap.adt.activation.request+xml; charset=utf-8',
             'Accept': 'application/vnd.sap.adt.activation.result+xml'},
    data=act_body.encode('utf-8'), verify=False)
print('Activate:', act_resp.status_code)
if 'type="E"' in act_resp.text:
    print(safe(act_resp.text[:3000]))
else:
    print('[OK] Activated successfully')
```

**Kritik notlar:**
- `FM_NAME` küçük harf olmalı (endpoint URL'de)
- Lock endpoint: `.../fmodules/{FM_NAME}` (source/main değil)
- Lock header: `X-sap-adt-corrNr` (query param değil)
- Aktivasyon type: `FUNC/FF`

### 3.3 CDS View Yeni Oluşturma + Push (ÇALIŞAN YÖNTEM — 21 Nisan 2026)

**Durum:**
- `create_cds_view.py` script'i → CSRF token expired hatası veriyor (çalışmıyor)
- `push_object.py` DDLS için çalışıyor — AMA sadece obje SAP'ta zaten varsa
- Yeni obje için önce ADT REST ile create, sonra `push_object` ile push yapılmalı

**Kritik Notlar:**
- Endpoint: `POST /sap/bc/adt/ddic/ddl/sources` (`/ddlsources` değil — 404 verir)
- Content-Type: `application/vnd.sap.adt.ddlSource+xml` (v2 değil)
- CDS source XML'de `saxutils.escape()` ile escape edilmeli
- Create HTTP 201 → başarılı; 409/AlreadyExists → zaten var, push'a devam et
- Create sonrası `push_object(..., object_type='DDLS')` çalışıyor ve aktive ediyor

**Tam Çalışan Script Şablonu:**

```python
import sys
import xml.sax.saxutils as saxutils
sys.path.insert(0, r'<PROJECT_ROOT>\scripts')
from sap_adt_lib import set_explicit_working_dir
set_explicit_working_dir(r'<PROJECT_ROOT>')
from sap_client import SAPClient

client  = SAPClient()
ac      = client.adt_client
PACKAGE   = 'ZSD001_CLC'
TRANSPORT = '<TRANSPORT>'

def get_csrf():
    r = ac.session.get(ac.url + '/sap/bc/adt/discovery', headers={'X-CSRF-Token': 'Fetch'}, verify=False)
    return r.headers.get('X-CSRF-Token', '')

def create_cds(name, desc, source):
    csrf = get_csrf()
    cds_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ddl:ddlSource xmlns:ddl="http://www.sap.com/adt/ddic/ddlsources"'
        ' xmlns:adtcore="http://www.sap.com/adt/core"'
        ' adtcore:name="' + name + '"'
        ' adtcore:description="' + desc + '"'
        ' adtcore:masterLanguage="TR">'
        '<adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/' + PACKAGE.lower() + '"'
        ' adtcore:type="DEVC/K" adtcore:name="' + PACKAGE + '"/>'
        '<ddl:sourceMainArtifact>'
        '<ddl:artifactType>ddlSource</ddl:artifactType>'
        '<ddl:source>' + saxutils.escape(source) + '</ddl:source>'
        '</ddl:sourceMainArtifact>'
        '</ddl:ddlSource>'
    )
    resp = ac.session.post(
        ac.url + '/sap/bc/adt/ddic/ddl/sources',
        params={'corrNr': TRANSPORT},
        headers={
            'X-CSRF-Token': csrf,
            'Content-Type': 'application/vnd.sap.adt.ddlSource+xml; charset=utf-8',
            'Accept': '*/*',
        },
        data=cds_xml.encode('utf-8'),
        verify=False
    )
    return resp.status_code, resp.text[:300]

name = 'ZSD001_I_ORNEK_VH'
src  = r'<PROJECT_ROOT>\ERP\ZSD001_CLC\cds\ZSD001_I_ORNEK_VH.cds'

with open(src, 'r', encoding='utf-8') as f:
    source = f.read()

status, body = create_cds(name, 'Ornek VH CDS', source)
if status in (200, 201):
    print('[OK] Created')
elif 'AlreadyExists' in body or status == 409:
    print('[INFO] Already exists, pushing source...')
else:
    print('[FAIL] ' + str(status) + ': ' + body)
    exit(1)

result = client.push_object(object_name=name, object_type='DDLS', source_file=src, transport=TRANSPORT)
print(result)
```

Script'i `<PROJECT_ROOT>\TempScripts\_push_cds.py` olarak kaydet, çalıştır, sonra sil.

**Sadece Güncelleme (var olan CDS'e):**
Obje zaten SAP'ta varsa create adımı gerekmez, direkt `push_object` yeterli:
```python
result = client.push_object(object_name='ZSD001_C_SO_ITEM', object_type='DDLS',
    source_file=r'...cds\ZSD001_C_SO_ITEM.cds', transport='<TRANSPORT>')
print(result)
```

### 3.3 Aktivasyon

Push başarılı olduktan sonra aktivasyon:

```powershell
python "<PROJECT_ROOT>\scripts\activate_object.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type CLAS --object-name ZCL_ORNEK_CLASS
```

**⚠ Aktivasyon Önemli Notlar:**
- `syntax_check.py` **tek-otorite değil**: bazen yanlış hata raporlar (özellikle CDS/class interaksiyonlarında), gerçek aktivasyon başarılı olabilir → aktivasyon ile **çapraz-doğrula**. AMA `parser_error`/"Statement does not exist"i körü körüne false-positive sayma — gerçek RAP syntax hatası olabilir (hafıza: `feedback_abaplint-parser-error-gercek-olabilir`); çalışan referansla kıyas + `adt_syntax_check` pre-audit.
- Aktivasyon sonrası SAP GUI'de kontrol et veya OData metadata'yı refresh et.
- Class için önce LOCAL TYPES, sonra PUBLIC, PROTECTED, PRIVATE section sırasıyla push edilmeli.

---

## 4. LOCK / UNLOCK

### 4.1 Lock Alma

Push işlemi öncesinde lock otomatik alınır (`push_object.py` içinde).

### 4.2 409 Conflict — KESİN KURAL

**409 geldiğinde ASLA retry yapma.**
Her retry SAP'de yeni bir boş K-type transport yaratır.

**409 sonrası yapılacaklar:**
1. Kullanıcıya bildir
2. Kullanıcı SM12'den stale lock'u temizlesin
3. Kullanıcı SE10'dan objeyi doğru transport'a assign etsin
4. Sonra tek bir retry yap

---

## 5. SQL SORGUSU (run_data_preview / run_sql_query)

**Script:** `run_sql_query.py` veya `run_data_preview.py`

```powershell
python "<PROJECT_ROOT>\scripts\run_sql_query.py" --conn "<PROJECT_ROOT>\.conn_adt" --query "SELECT * FROM ZSD001_C_SO_ITEM WHERE VKORG = '1500' UP TO 10 ROWS"
```

**Alternatif — CDS data preview:**
```powershell
python "<PROJECT_ROOT>\scripts\run_data_preview.py" --conn "<PROJECT_ROOT>\.conn_adt" --entity-name ZSD001_C_SO_ITEM --max-rows 10
```

**⚠ Bilinen sorunlar:**
- Bazı CDS view'lar data preview'da hata verir (authorization / SADL kısıtı) — SQL sorgusu dene
- JOIN içeren sorgularda alias kullan

---

## 6. PAKET İÇERİĞİ LISTELEME

```powershell
python "<PROJECT_ROOT>\scripts\list_package_contents.py" --conn "<PROJECT_ROOT>\.conn_adt" --package ZSD001_CLC
```

---

## 7. TRANSPORT İŞLEMLERİ

**Aktif Transport:** `<TRANSPORT>`

### 7.1 Transport Listesi

```powershell
python "<PROJECT_ROOT>\scripts\list_transports.py" --conn "<PROJECT_ROOT>\.conn_adt"
```

### 7.2 Yeni Transport Yaratma

Yeni transport yaratma gerektiğinde kullanıcıdan numara iste — otomatik yaratma.

---

## 8. OBJE ARAMA

```powershell
python "<PROJECT_ROOT>\scripts\search_objects.py" --conn "<PROJECT_ROOT>\.conn_adt" --query "ZSD001*" --object-type CLAS
```

---

## 9. WHERE-USED

```powershell
python "<PROJECT_ROOT>\scripts\where_used.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type CLAS --object-name ZCL_ZSD_ORDER_DPC_EXT
```

---

## 10. ATC KONTROLÜ

```powershell
python "<PROJECT_ROOT>\scripts\run_atc_check.py" --conn "<PROJECT_ROOT>\.conn_adt" --object-type CLAS --object-name ZCL_ZSD_ORDER_DPC_EXT
```

---

## 11. OData METADATA OKUMA

OData servis metadata'sını okumak için doğrudan HTTP GET (ADT script yok, proxy üzerinden):

```
GET /sap/opu/odata/SAP/ZSD_ORDER_SRV/$metadata
Host: <SYSTEM_ID>.SAP.EXAMPLE.COM.TR:44300
```

Lokal geliştirmede `http://localhost:8080/sap/opu/odata/SAP/ZSD_ORDER_SRV/$metadata` (ui5-middleware-simpleproxy aktifken)

### 11.1 Python ile Metadata Doğrulama (ÇALIŞAN YÖNTEM — 21 Nisan 2026)

SEGW'de yeni ComplexType / Function Import ekledikten sonra metadata'da var mı kontrol etmek için:

```python
import ssl, urllib.request, base64

SAP_URL    = 'https://<SYSTEM_ID>.SAP.EXAMPLE.COM.TR:44300'
SAP_USER   = '<SAP_USER>'
SAP_PASS   = 'Oy87918791.!.!.!'
SAP_CLIENT = '100'
SERVIS     = 'ZSD_ORDER_SRV'   # kontrol edilecek servis adı

url = SAP_URL + '/sap/opu/odata/SAP/' + SERVIS + '/$metadata'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(url)
creds = base64.b64encode((SAP_USER + ':' + SAP_PASS).encode()).decode()
req.add_header('Authorization', 'Basic ' + creds)
req.add_header('sap-client', SAP_CLIENT)

with urllib.request.urlopen(req, context=ctx) as resp:
    content = resp.read().decode('utf-8')

# Aranacak string'leri buraya ekle
for token in ['CreateDeliveryAddress', 'CreateDeliveryAddressResult', 'AddressText']:
    if token in content:
        print('[OK] ' + token + ' found in metadata')
    else:
        print('[FAIL] ' + token + ' NOT found in metadata')
```

**Kritik notlar:**
- `SAPClient` nesnesinin `base_url`, `config`, `user`, `password` gibi attribute'ları YOK — direkt `.conn_adt` değerlerini kullan
- `ssl_verify=false` için `ctx.check_hostname = False` + `ctx.verify_mode = ssl.CERT_NONE` gerekli
- Script'i `<PROJECT_ROOT>\TempScripts\` altına yaz, işten sonra sil
- SEGW'de Generate + Activate yapılmadan metadata güncellenmez

---



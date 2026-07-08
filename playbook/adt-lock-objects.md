---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# Lock Object (ENQU/DL)

## 16. Lock Object (ENQU/DL) Yaratma

### 29.0 Production Script

📦 **`scripts/populate_lock_objects.py`** — CSV-driven batch lock object yaratıcı.

```powershell
python scripts/populate_lock_objects.py `
  --package ZSD001_CLC `
  --transport <TRANSPORT> `
  --csv ERP/SD/ZSD001_CLC/lock_objects.csv `
  --cwd <PROJECT_ROOT>
```

CSV format:
```
name,description,primary_table,lock_mode,allow_rfc,field_names
EZSD001_LO_BOOK,Booking Edit Kilidi,ZSD001_T_BOOKHD,E,false,MANDT;BOOKING_NO
```

### 29.1 Önemli URL Yapısı — `sources/` Alt Yolu

⚠️ **Lock object'in URL pattern'i farklı** (tablodan/DTEL'den):

| İşlem | URL |
|---|---|
| CREATE (POST) | `/sap/bc/adt/ddic/lockobjects/sources` ← `sources` çoğul, root |
| GET / DELETE | `/sap/bc/adt/ddic/lockobjects/sources/{name}` ← `sources/{name}` |
| Activate | POST `/sap/bc/adt/activation` body içinde `adtcore:uri="/sap/bc/adt/ddic/lockobjects/sources/{name}"` |

**UYARI:** `/sap/bc/adt/ddic/lockobjects/{name}` (sources olmadan) **404 verir**. Yanılma.

### 29.2 ADT Type Code

```
adtcore:type="ENQU/DL"
```

Bu tip kodu activation body'sinde, GET response'ta, vb. her yerde kullanılır. `activate_object.py` (CLI) bu tipi desteklemiyor — manuel activation gerek.

### 29.3 XML Şeması

```xml
<?xml version="1.0" encoding="UTF-8"?>
<enqu:lockobject xmlns:enqu="http://www.sap.com/adt/ddic/enqu"
                 xmlns:adtcore="http://www.sap.com/adt/core"
                 adtcore:name="EZSD001_LO_BOOK"
                 adtcore:description="Booking Edit Kilidi"
                 adtcore:masterLanguage="TR">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/zsd015_clc"
                      adtcore:type="DEVC/K"
                      adtcore:name="ZSD001_CLC"/>
  <enqu:content>
    <enqu:allowRFC>false</enqu:allowRFC>
    <enqu:primaryTable>
      <enqu:tableName>ZSD001_T_BOOKHD</enqu:tableName>
      <enqu:lockMode>E</enqu:lockMode>
    </enqu:primaryTable>
    <enqu:secondaryTables/>
    <enqu:lockParameters>
      <enqu:lockParameter>
        <enqu:parameterWanted>true</enqu:parameterWanted>
        <enqu:parameterName>MANDT</enqu:parameterName>
        <enqu:tableName>ZSD001_T_BOOKHD</enqu:tableName>
        <enqu:fieldName>MANDT</enqu:fieldName>
      </enqu:lockParameter>
      <enqu:lockParameter>
        <enqu:parameterWanted>true</enqu:parameterWanted>
        <enqu:parameterName>BOOKING_NO</enqu:parameterName>
        <enqu:tableName>ZSD001_T_BOOKHD</enqu:tableName>
        <enqu:fieldName>BOOKING_NO</enqu:fieldName>
      </enqu:lockParameter>
    </enqu:lockParameters>
  </enqu:content>
</enqu:lockobject>
```

**✅ DURUM — `sap_client.create_lock_object()` CANLI DOĞRULANDI (2026-06-18, EZSD000_ZZTST throwaway yarat→sil):**
Eski "backslash bug" iddiası KESİN ÇÜRÜTÜLDÜ — create CSRF sonrası **HTTP 200 yazıyor**, `masterLanguage=TR` (ADR 0005-D ✓), forward-slash doğru. AMA **"tam çalışır" DEĞİL** — iki KALICI nüans (geçici hata değil):
1. **Lib AKTİVE ETMEZ** → create sonrası obje canlıda `version="inactive"`, `<enqu:lockModules/>` **BOŞ** (ENQUEUE_/DEQUEUE_ FM'leri üretilmemiş). Çağıran taraf create'ten sonra **AYRI activate + FM-generate** yapmalı; yoksa kilit FM'leri yok = kullanılamaz.
2. **`lock_fields` = STRING-ARRAY** `["LOCK_OBJECT","LOCK_KEY"]` (lib `field.upper()` çağırır), dict `[{"name":...}]` **DEĞİL** → dict verirsen `'dict' object has no attribute 'upper'`.
Tuzaklar: bayat `.csrf_token.json` → 403 (sil/force-refresh). MCP `adt_delete enqu` lock-objesini **E-prefix yüzünden** ADR 0005-A false-positive ile reddeder (lock objeleri zorunlu E-prefix, Z/Y değil) → silme ADT REST `GET-seed CSRF → LOCK → DELETE` ile.

### 29.4 Lock Mode Değerleri

- `E` — Exclusive (en yaygın, write için)
- `S` — Shared (read için, birden fazla okumaya izin)
- `X` — Exclusive non-cumulative

### 29.5 Endpoint Detayları

```
POST /sap/bc/adt/ddic/lockobjects/sources?corrNr={TRANSPORT}
Content-Type: application/vnd.sap.adt.lockobjects.v1+xml; charset=utf-8
X-CSRF-Token: {csrf}
sap-client: 100
sap-language: TR

Body: <enqu:lockobject>...
```

### 29.6 Activation

Lock object'i activate etmek için **manual** akış (activate_object.py ENQU/DL tipi yok):

```python
body = f'''<?xml version="1.0" encoding="UTF-8"?>
<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:objectReference adtcore:uri="/sap/bc/adt/ddic/lockobjects/sources/{name.lower()}"
                            adtcore:type="ENQU/DL"
                            adtcore:name="{name.upper()}"/>
</adtcore:objectReferences>'''

r = client.session.post(
    f'{client.url}/sap/bc/adt/activation',
    params={'method':'activate','preauditRequested':'true'},
    headers={'X-CSRF-Token':csrf, 'Content-Type':'application/xml'},
    data=body.encode('utf-8'),
    verify=False
)
# Success kontrolü: response.text içinde `activationExecuted="true"` olmalı
```

### 29.7 Generated Functions

Lock object aktif olunca SAP otomatik yaratır:
- `ENQUEUE_{NAME}` — kilitleme function
- `DEQUEUE_{NAME}` — kilit serbest bırakma function

Programda şöyle kullanılır:
```abap
CALL FUNCTION 'ENQUEUE_EZSD001_LO_BOOK'
  EXPORTING
    mode_zsd015_t_bookhd = 'E'
    mandt                = sy-mandt
    booking_no           = lv_booking_no
  EXCEPTIONS
    foreign_lock         = 1
    system_failure       = 2
    OTHERS               = 3.

" ... edit operations ...

CALL FUNCTION 'DEQUEUE_EZSD001_LO_BOOK'
  EXPORTING
    mode_zsd015_t_bookhd = 'E'
    mandt                = sy-mandt
    booking_no           = lv_booking_no.
```

---



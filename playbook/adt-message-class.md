---
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# Mesaj Sınıfı (MSAG)

## 18. Mesaj Sınıfı (MSAG) — REST ile Mesaj Ekleme

**🎉 ÇÖZÜLDÜ — 2026-05-13** | 50+ varyant test edildi, **`If-Match` header'ı göndermemek** bug'ı bypass etti.

### 27.0 Hazır Production Script

📦 **`scripts/populate_message_class.py`** — herhangi bir mesaj sınıfına CSV'den toplu mesaj yazma.

```powershell
# CSV format (UTF-8, header'lı):
#   msgno,msgtext,selfexplainatory
#   001,"Müşteri bulunamadı",false
#   002,"Tarih boş olamaz",true

python scripts/populate_message_class.py `
  --name ZSD001 `
  --package ZSD000_CLC `
  --transport <TRANSPORT> `
  --description "Sevkemri Mesaj Sinifi" `
  --responsible <SAP_USER> `
  --messages-csv ERP/SD/ZSD001_CLC/messages.csv `
  --cwd <PROJECT_ROOT>

# Sadece mevcut durumu listelemek için:
python scripts/populate_message_class.py --name ZSD001 ... --verify-only

# XML'i preview etmek için (yazma yapmaz):
python scripts/populate_message_class.py --name ZSD001 ... --dry-run
```

Script garantili `try/finally` ile UNLOCK ve `clear_enqueue_lock` çağırıyor — SM12'de stale lock bırakmaz.

### 27.1 Winning Pattern — Kritik Detaylar

**Çalışan akış:**

```python
# 1. CSRF
client._invalidate_csrf_cache()
r = client.session.get(
    client.url + '/sap/bc/adt/discovery',
    params={'sap-client': '100', 'sap-language': 'TR'},
    headers={'X-CSRF-Token': 'Fetch'},
    verify=False
)
csrf = r.headers.get('X-CSRF-Token', '')

# 2. LOCK (parent class)
lock_resp = client.session.post(
    client.url + object_url,
    params={'_action': 'LOCK', 'accessMode': 'MODIFY', 'corrNr': TRANSPORT},
    headers={
        'X-CSRF-Token': csrf,
        'X-sap-adt-sessiontype': 'stateful',
        'Accept': 'application/*,application/vnd.sap.as+xml;'
                  'dataname=com.sap.adt.lock.result',
    },
    verify=False
)
m = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lock_resp.text)
handle = m.group(1)

# 3. PUT — tüm class body, If-Match YOK!
from xml.sax.saxutils import escape as xml_escape

msgs_xml = '\n'.join(
    f'  <mc:messages mc:msgno="{n}" mc:msgtext="{xml_escape(t)}" '
    f'mc:selfexplainatory="{s}" mc:documented="false" adtcore:name=""/>'
    for n, t, s in messages
)

xml = f'''<?xml version="1.0" encoding="utf-8"?>
<mc:messageClass adtcore:responsible="<SAP_USER>"
                 adtcore:masterLanguage="TR"
                 adtcore:name="ZSD001"
                 adtcore:type="MSAG/N"
                 adtcore:description="Sevkemri Mesaj Sinifi"
                 adtcore:language="TR"
                 xmlns:mc="http://www.sap.com/adt/MessageClass"
                 xmlns:adtcore="http://www.sap.com/adt/core">
  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/zsd000_clc"
                      adtcore:type="DEVC/K"
                      adtcore:name="ZSD000_CLC"/>
{msgs_xml}
</mc:messageClass>'''

r = client.session.put(
    client.url + object_url,
    params={'corrNr': TRANSPORT, 'lockHandle': handle, 'accessMode': 'MODIFY'},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.mc.messageclass+xml; charset=utf-8',
        'Accept': '*/*',
        'X-sap-adt-sessiontype': 'stateful',
        'sap-client': '100', 'sap-language': 'TR',
        # !!! If-Match GÖNDERME — buggy lock check'i bypass eder !!!
    },
    data=xml.encode('utf-8'),
    verify=False
)
# 200 = OK

# 4. UNLOCK (try/finally içinde garantili) + clear_enqueue_lock safety net
```

### 27.2 Kök Neden — Neden Çalışıyor

> **🔑 GENEL KURAL (tek-ev — If-Match self-collision):** ADT `…/source/main` benzeri **DDIC source PUT**'ta `If-Match` header'ı **GÖNDERME** — buggy lock-check'i bypass eder (kök-neden aşağıda). Uygulanan objeler: **MSAG** (bu §) · **DTEL update** (`adt-domain-dtel.md` §26.2) · **Z-tablo** (`adt-tables-structures.md` §28.3). Bu üç konum bu kurala pointer verir.
> **⚠️ İSTİSNA — table-type PUT'ta If-Match ZORUNLU:** `…/ddic/tabletypes/<ttyp>` PUT'unda `If-Match: <etag>` **gönderilir** (farklı endpoint + content-type, ETag-yolu burada DOĞRU çalışır — `adt-tables-structures.md` §13). "If-Match hiç gönderme" diye GENELLEME yapma — yalnız source/main DDIC-source PUT'ları kapsar.

**SE91 backend handler iki kontrol yapıyor:**

1. **ETag precondition check** — `If-Match` header'ı varsa ETag karşılaştırması yapıyor. **Bu kod yolu eğer açılırsa**, sonrasında ENQUEUE check'i de çalıştırılıyor ve `SY-UNAME == lock_owner` kontrolünde **self-collision** veriyor (kendi lock'umuzu "başka session" olarak görüyor).

2. **No-If-Match yolu** — `If-Match` header'ı yoksa ETag check **atlanıyor** ve direkt write yapılıyor. Bu yolda ENQUEUE re-validate yapılmıyor — sadece query param'daki `lockHandle` doğrulanıyor (bizim aldığımız lock).

**Eclipse ADT neden çalışır:** Eclipse JCo/RFC üzerinden konuşur, bu HTTP REST kontrol akışını hiç görmez. RFC session'da ENQUEUE doğal olarak `SY-UNAME`'i kendinin görür.

### 27.3 Mesaj XML Şeması (Kritik!)

GET response'tan keşfedildi (SAP'nin döndüğü format):

| Element/Attr | Açıklama |
|---|---|
| `<mc:messages>` | ÇOĞUL element adı (`<mc:message>` DEĞİL — yaygın hata) |
| `mc:msgno` | Mesaj numarası, 3 haneli zero-padded (`mc:number` DEĞİL) |
| `mc:msgtext` | Mesaj metni (`mc:text` DEĞİL) |
| `mc:selfexplainatory` | `true`/`false` — SAP'de typo var, `mc:selfExplanatory` DEĞİL |
| `mc:documented` | `false` — long-text var mı |
| `adtcore:name` | `""` boş — gereksiz ama include et |

**XML escape:** `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;`. Python: `from xml.sax.saxutils import escape`

### 27.4 Disiplin — try/finally ŞART

Mesaj sınıfı (veya herhangi DDIC objesi) üzerinde LOCK alan **her script** şu pattern'i kullanmalı, yoksa SM12'de stale lock kalır:

```python
handle = None
try:
    # LOCK
    lock_resp = client.session.post(...)
    m = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lock_resp.text)
    handle = m.group(1) if m else None

    # PUT/POST/DELETE
    ...

finally:
    if handle:
        try:
            client.session.post(
                client.url + object_url,
                params={'_action': 'UNLOCK', 'lockHandle': handle},
                headers={'X-CSRF-Token': csrf, 'X-sap-adt-sessiontype': 'stateful'},
                verify=False, timeout=10
            )
        except Exception:
            pass
    # Safety net
    try:
        client.clear_enqueue_lock(object_url=object_url)
    except Exception:
        pass
```

### 27.5 Tam PUT — Replace Semantiği

Önemli: PUT body'sindeki mesaj listesi **mevcut listeyi REPLACE eder**. Yani:
- Mevcut 5 mesaj var → PUT 3 yeni mesaj → sonuçta 3 mesaj kalır (mevcut 5 silinir)
- Mevcut 5 mesaj var + 5 mesaj korunmasını istiyorsan, PUT body'sine 5'i de eklemen lazım
- `populate_message_class.py` bu mantığı tek-PUT olarak kullanır — CSV'deki mesajlar nihai liste olur

### 27.6 Başarısız Yolların Arşivi (referans amaçlı)

Test edilip çalışmadığı **kanıtlanan** yöntemler — tekrar deneme:

| Yöntem | Sonuç |
|---|---|
| PUT + `If-Match: <etag>` | 403 self-collision (ETag yolu enqueue check'i tetikliyor) |
| PUT + `If-Match: *` | 412 ETag mismatch (per-msg empty) veya 403 (parent) |
| PUT `/messages/{nr}` per-message | 423 invalid lock handle (handler ADT lock'u tanımıyor) |
| POST `/messageclass` (collection) | 201 ama mesajlar silently dropped |
| `X-HTTP-Method-Override: PUT` | 201 ama yine silently dropped |
| `<mc:message>` singular element | 400 XML parse error |
| `mc:number` / `mc:text` attribute adları | 400 XML parse error |
| `Sap-Lock-Handle` veya benzeri header adları | 403 |
| `_action=UPDATE/REPLACE/UPSERT` | 400 URI mapping error |
| `accessMode=stateless/READ` | 400 invalid value |
| `forceLock=true`, `overwrite=true` | Tanınmıyor — 403 |

**Tek çalışan yol:** §18.0 production script veya §18.1 inline pattern.

### 27.7 Hızlı Çözüm Hatırlatma

| Adım | Aksiyon |
|---|---|
| 1 | Sınıfı SE91'de yarat (boş shell, TR master lang) |
| 2 | Mesaj listesini CSV'ye yaz: `msgno,msgtext,selfexplainatory` |
| 3 | `python scripts/populate_message_class.py --name ... --messages-csv ...` |
| 4 | `--verify-only` ile mesajları doğrula |
| 5 | SE91 / SAP GUI'de aktive et |

---



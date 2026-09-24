---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-09-24
status: active
---

# Mesaj Sınıfı (MSAG)

## 18. Mesaj Sınıfı (MSAG) — REST ile Mesaj Ekleme

**🎉 ÇÖZÜLDÜ — 2026-05-13** | 50+ varyant test edildi, **`If-Match` header'ı göndermemek** bug'ı bypass etti.

### 27.0 Hazır Production Script — İKİ ADIM (SE91 GEREKMEZ, ikisi de programatik)

> **⚠ KRİTİK:** MSAG shell'i **SE91'de elle açmaya GEREK YOK** — programatik create script'i VAR.
> `populate` **mevcut** shell'e yazar; shell yoksa PUT **sahte-200** döner (T100'e hiç yazmaz,
> `adt_msgclass_read` exists=false). Ayrıca `adt_post_shell(msag)` / `adt_activate(msag)` MCP'de
> **desteklenmez** ("Unsupported object type: msag") → **create script'i kullan.**

**1) SHELL YARAT** — 📦 **`scripts/create_message_class.py`** (`client.create_message_class`):
```
python scripts/create_message_class.py --name ZSD001_MSG \
  --description "<PKG> Mesaj Sinifi" --package ZSD000_CLC \
  --transport <TRANSPORT> --cwd <PROJECT_ROOT>
```
(master lang = login dili; TR login → TR shell — `check_sap_master_language` gate TR ister.)
> ✅ **create LOCK-release ÇÖZÜLDÜ (2026-07-14, canlı-kanıtlı):** eski davranışta `create_message_class`
> POST'u **stateful session** default'uyla gidiyordu → MSAG create-anı EU 510 enqueue'sunu request-end'de
> BIRAKMIYORDU → populate/delete `403 EU 510` → SM12 gerekiyordu. **Kök-fix:** `sap_client.py::create_message_class`
> POST'una per-call `x-sap-adt-sessiontype: stateless` (referans `abap-adt-api`: `createObject` stateless →
> enqueue request-end roll-out'ta düşer) + bozuk `clear_enqueue_lock` re-lock safety-net'i kaldırıldı
> (self-lock'u re-lock ile temizlemeye çalışıyordu → yine 403). Test: create→populate tek akış, **SM12'siz**.
> Not: hedef paket **DEV paketi** olmalı — structure/aggregate paket verilince create sessizce exists=false +
> populate sahte-200 üretir. (Eski "finally-unlock ekle" önerisi SUPERSEDED; sorun handle-eksikliği değil, session-type idi.)

**2) MESAJLARI YAZ** — 📦 **`scripts/populate_message_class.py`** — shell'e CSV'den toplu mesaj.

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

### 27.5 Tam PUT — EKLER/GÜNCELLER, SİLMEZ (ölçüldü 2026-09-24 — eski "REPLACE" iddiası ÇÜRÜDÜ)

> ⛔ **Önceki metin** *"PUT body'sindeki liste mevcut listeyi REPLACE eder, listede olmayan
> silinir"* diyordu. **Silme yönünde ölçüldü ve TUTMADI** (`s4_private`, release 2025):
> 229 mesajlı bir sınıfa, 17'si çıkarılmış **212 mesajlık** tam gövde §27.1 akışıyla
> (LOCK → PUT, If-Match YOK → UNLOCK) gönderildi → LOCK/PUT/UNLOCK **üçü de 200**, ama
> readback'te T100 **229 → 229** (17'sinin 17'si yerinde), metin/bayrak değişimi 0, sınıfın
> `changedAt` değeri **değişmedi**. Karşılaştırma iki bağımsız kanaldan (T100 SQL + ADT GET).

**Bugün kanıtlı olan (dar):**
- Tam PUT, gövdedeki mesajları **ekler / metnini günceller** (bu yol defalarca readback'le doğrulandı).
- Tam PUT, gövdede **olmayan** mesajı **SİLMEZ** — ölçülen tek vakada; başka sürüm/profil ÖLÇÜLMEDİ.
- ⇒ `populate_message_class.py`'ye **eksik** CSV vermek bu sürümde mesaj kaybettirmez; ama CSV'den
  çıkarmak da mesajı **silmez**. "CSV nihai listedir" varsayımıyla silme planlama.
- ⚠ Yine de gövdeye **mevcut mesajların tamamını** koy (§27.0 akışı canlıdan başlar): davranışın
  başka sürümde REPLACE olmadığı ölçülmedi — korunması gereken mesajı gövdeden düşürme.

**Mesaj SİLME için ADT REST'te çalışan yol bugün YOK** (denenenler §27.6). Kanıtlı tek yol:
**SE91'de elle silme** (kullanıcı) → ardından T100 readback (`SELECT msgnr, text FROM t100
WHERE sprsl = '<ML>' AND arbgb = '<MSAG>'`) ile sayı + kalanların metni silme öncesi fotoğrafla
karşılaştırılır. Uzun metinli mesajda (DOKHL `ID='NA'`, `OBJECT = <MSAG><NR>`) SE91 uzun metnin
akıbetini ayrıca sorar.

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
| **Tam PUT ile SİLME** (gövdeden mesaj çıkarmak) — 2026-09-24 | LOCK/PUT/UNLOCK 200 ama **no-op**: çıkarılan mesajlar yerinde, `changedAt` değişmedi (§27.5) |
| Sınıf LOCK → `DELETE /messageclass/{mc}/messages/{nr}?lockHandle=<sınıf>&corrNr=…` — 2026-09-24 | **423** `ExceptionResourceInvalidLockHandle` (SADT_RESOURCE 026: *"Resource <mesaj> is not locked"*) — sınıf kilidi mesaj alt kaynağını kapsamıyor. Sınıf UNLOCK 200 |
| Alt kaynak `POST /messageclass/{mc}/messages/{nr}?_action=LOCK` → aynı tutamaçla `DELETE` → aynı tutamaçla `UNLOCK` — 2026-09-24 | LOCK **200 + tutamaç**, DELETE **423** (026), UNLOCK **403** `ExceptionResourceNoAccess` (SADT_RESOURCE 029 *"could not be locked"*). ⛔ **TEKRARLAMA — kilit bırakılamamış hâlde kalabilir**; SM12 kontrolü kullanıcıdadır (lock silme ADR 0005-C yasağı) |

**Tek çalışan yol (ekleme/güncelleme):** §18.0 production script veya §18.1 inline pattern.
**Silme:** ADT REST'te çalışan yol yok — SE91 (kullanıcı) + T100 readback (§27.5).

> 🔎 **Okuma tuzağı (2026-09-24):** `GET /messageclass/{mc}/messages/{nr}` **her numara için**
> 200 + boş `<msg:message msg:msgno="" msg:msgtext=""/>` döner — var olmayan numara (`999`) dahil.
> ⇒ Bir mesajın varlığına bu uçtan hüküm verilmez; sınıf GET'i ya da T100 okunur.

### 27.7 Hızlı Çözüm Hatırlatma

| Adım | Aksiyon |
|---|---|
| 1 | `python scripts/create_message_class.py --name ... --description ... --package ... --transport ... --cwd ...` → **shell (SE91 GEREKMEZ)** |
| 2 | Mesaj listesini CSV'ye yaz: `msgno,msgtext,selfexplainatory` (⚠ msgtext ≤ **73 char** — T100 limiti) |
| 3 | `python scripts/populate_message_class.py --name ... --messages-csv ...` (shell'e tam PUT — **ekler/günceller, SİLMEZ**; §27.5) |
| 4 | `adt_msgclass_read` (veya `--verify-only`) ile mesajları + master_language=TR doğrula |
| 5 | Ayrı aktivasyon genelde GEREKMEZ — populate T100'e save-eder (readback ile doğrula) |

---

## 19. Mesaj Sınıfı OKUMA — `adt_msgclass_read` MCP tool (2026-07-12)

**Sorun (kanıt):** `adt_get` **msag tipini DESTEKLEMEZ** (`Unsupported object type: msag`) ve
`adt_table_read` T100'ü **filtreleyemez** (WHERE param yok → T100 preview HTTP 400). Bir ajan
mevcut mesaj sınıfını okuyamayınca **inline literal `MESSAGE '...'`'e düşer** — bu standards/06 §5
(literal-gömme YASAK) ihlalidir. Çözüm: okuma için özel MCP tool.

**`adt_msgclass_read(name)`** (`mcp_servers/sap_adt/tools/atom.py`):
- Endpoint: `GET /sap/bc/adt/messageclass/{name}` · **Accept: `application/vnd.sap.adt.mc.messageclass+xml`**
- Döner: `{ok, exists, master_language, description, count, messages:[{no, text, selfexplanatory, documented}]}`
  (metin `&` çözülmüş, master dilde).
- `adt_get(name, object_type='msag')` da buna delege eder.

**⚠ Endpoint tuzakları (canlı-doğrulandı 2026-07-12):**
| Denenen | Sonuç |
|---|---|
| `.../messageclass/{name}/messages` alt-path | **404** (bu sürümde yok) |
| Accept `application/vnd.sap.adt.messageclass.v2+xml` (reference'ın header'ı) | **406** — sunucu doğru tipi gövdede bildirir |
| **`.../messageclass/{name}` + `.mc.messageclass+xml`** | **200** ✓ |

> Referans impl: `marcellourbani/vscode_abap_remote_fs` → `client/src/editors/messages.ts` (Message
> Class Editor; ham `httpClient.request` + XML parse). Sürüm-farkı: reference'ın `.v2+xml` Accept'i
> bizim sistemde 406 → **API'yi dokümandan değil sunucudan doğrula** (sunucu 406 gövdesinde kabul-tipini verir).
> Aynı meta-kuralın ikinci uygulaması: program **text-pool OKUMA** Accept tipleri
> (`text/plain` → 406; kök obje `.textelements.v1+xml`, alt-objeler kendi tipini bildirir) —
> [`adt-programs.md`](adt-programs.md) §23.7 "OKUMA reçetesi", 2026-07-31.

**XML şeması** = §27.3 ile aynı (`mc:messages` çoğul · `mc:msgno` · `mc:msgtext` ·
`mc:selfexplainatory` typo'lu · `mc:documented`); ns `http://www.sap.com/adt/MessageClass`.

**KURAL — bir Z mesaj sınıfına MESSAGE ile referans vereceksen:** ÖNCE `adt_msgclass_read` ile mevcut
mesajları OKU, uygun no'yu reuse et. Okuyamadın diye inline literal YAZMA. Uygun mesaj yoksa: yeni
mesaj ekle (`populate_message_class.py`, §18) veya kullanıcıya sor. (Okuma tool'u = yazma script'inin
`--verify-only` yolunun MCP muadili; ajan artık SE91'siz görebilir.)

---



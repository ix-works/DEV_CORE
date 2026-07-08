---
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# CDS View (DDLS/DF)

## ⚡ TEK CDS YARATMA — ÖNCE BUNU OKU (KANONİK, MCP) (2026-06-13)

> **Yeni bir CDS view-entity'yi MCP ile yaratıyorsan, tool sırasını TAHMİN ETME — bu 3 adım:**
>
> 1. **Shell yarat** (raw-REST inline POST, taze CSRF) → `/sap/bc/adt/ddic/ddl/sources`.
>    Desen: `scripts/TempScripts/create_ddls_ve.py` (taze CSRF + `html.escape(src)`). 201 döner
>    ama **source BOŞ kalabilir** (empty-source trap).
> 2. **`mcp__sap-adt__adt_push_source`** (object_type `ddls`, transport) → obje ARTIK VAR →
>    locks + source set + **activate** + active-source doğrular. (Boş-source'u bu düzeltir.)
> 3. **Doğrula:** `adt_get include_source=true` → source DOLU + `version=active`.
>
> **DENENEN BAŞARISIZ (bu sırayı TEKRARLAMA — 2026-06-11 ve 2026-06-13'te 2 kez patinaj):**
>
> | Deneme | Sonuç | Neden |
> |---|---|---|
> | `adt_push_source` ÖNCE (shell yokken) | `[423] not locked` | push_source MEVCUT obje ister |
> | `adt_post_shell` (ddls) | `Unsupported object type: DDLS/DF` | MCP post_shell CDS/DDLS yaratmaz |
> | `create_cds_view.py` (`sap_client.py`) | CSRF "Unknown error" / body ignore | bu sistemde flaky + body'yi yok sayar (§30.1) |
>
> **Batch (çok CDS):** `scripts/populate_cds_views.py` (§30.0). **Mevcut CDS güncelle:** doğrudan `adt_push_source`.

### ⚡ ABSTRACT ENTITY (action param/result — `define [root] abstract entity`, SELECT'SİZ) (2026-06-23)

> **Abstract entity ≠ view-entity.** `as select from` / SQL view YOK → SELECT bekleyen araçlar UYGULANMAZ:
>
> | Deneme | Sonuç | Neden |
> |---|---|---|
> | `create_cds_view.py` | "no SELECT" / projection hatası | araç `as select from` bekler; abstract'ta yok |
> | `populate_cds_views.py` | **sprint gate** + TD-spec patlar | batch view-entity üreticisi; abstract için değil |
>
> **ÇALIŞAN (2026-06-23 — nakliye param/result patinajı sonrası):** view-entity 3-adımının abstract uyarlaması —
>
> 1. **Inline-source POST shell** (taze CSRF, `masterLanguage=TR`, `<ddl:source>` = `html.escape(.cds)` GÖMÜLÜ) → `/sap/bc/adt/ddic/ddl/sources`. Desen: `scripts/TempScripts/create_trdoc_abstract.py` (= `create_ddls_ve.py`'ın abstract uyarlaması).
> 2. **Toplu aktivasyon** `/sap/bc/adt/activation` (`DDLS/DF` objectReference'lar). Tek tek `adt_push_source` (object_type `ddls`) de olur — boş-source'u doldurur.
> 3. **Doğrula:** aktif-source GET → gövdede `abstract entity` GEÇMELİ + `version=active` (empty-source trap).
>
> **Kural:** "yeni DDLS" görünce TÜRÜNE bak — SELECT var mı? Varsa view-entity 3-adımı; yoksa (param/result/projection-only abstract) bu varyant. Tahminle araç seçme.

## 17. CDS View (DDLS/DF) Yaratma

### 30.0 Production Script

📦 **`scripts/populate_cds_views.py`** — `.cds` source dosyalarından batch CDS view yaratıcı.

```powershell
python scripts/populate_cds_views.py `
  --package ZSD001_CLC `
  --transport <TRANSPORT> `
  --source-dir ERP/SD/ZSD001_CLC/cds `
  --cwd <PROJECT_ROOT>

# Sadece bir CDS:
python scripts/populate_cds_views.py ... --only ZSD001_DDL_CONTAINER_TYPES

# Yeniden yarat:
python scripts/populate_cds_views.py ... --force-recreate
```

Her CDS için bir `.cds` dosyası (DDL source) — script `@EndUserText.label`'dan description çıkarır.

### 30.1 Önemli — 2-Step Pattern Gerek (Tablo Gibi)

Library'nin `create_cds_view()` (`sap_client.py`) **bu sistemde body içine source koyuyor ama SAP body'yi ignore ediyor** (table'daki sorunla aynı, playbook §15).

Doğru akış:
1. **POST shell** `/sap/bc/adt/ddic/ddl/sources` — sadece metadata
2. **LOCK** + **PUT** `/sap/bc/adt/ddic/ddl/sources/{name}/source/main` ile asıl DDL
3. **UNLOCK**
4. **Activate** (`activate_object.py --type cds`)

### 30.2 URL Pattern

```
POST   /sap/bc/adt/ddic/ddl/sources                              ← shell create
GET    /sap/bc/adt/ddic/ddl/sources/{name}/source/main           ← source oku
PUT    /sap/bc/adt/ddic/ddl/sources/{name}/source/main           ← source yaz (lock'lu)
POST   /sap/bc/adt/ddic/ddl/sources/{name}?_action=LOCK          ← lock
POST   /sap/bc/adt/ddic/ddl/sources/{name}?_action=UNLOCK        ← unlock
DELETE /sap/bc/adt/ddic/ddl/sources/{name}                       ← sil
```

ADT type code: `DDLS/DF`

### 30.3 SQL View Adı — 10 Karakter Limit

⚠ **KRİTİK:** `@AbapCatalog.sqlViewName: 'XXX'` değeri **maks 10 karakter** olmalı.

Örnek: `ZSD001_DDL_ORDER_DESTINATION` için SQL view adı `'ZSD001VYDS'` (10 char) — `ZSD001_V_ORDER_DESTINATION` (uzun) olmaz.

Mantıksal kısaltma yöntemi:
| CDS Adı | SQL View Adı |
|---|---|
| ZSD001_DDL_ORDER_DESTINATION | `ZSD001VYDS` |
| ZSD001_DDL_ORDER_SHIP_BAL | `ZSD001DSHB` |
| ZSD001_DDL_ORDER_ORDERES | `ZSD001ORDS` |
| ZSD001_DDL_SHIPPING_TYPES | `ZSD01SHTYP` (prefix 1 char kısa) |

### 30.4 Deprecated Annotation: `preserveKey`

`@AbapCatalog.preserveKey: true` artık SAP S/4'te **deprecated**. Uyarı verir:
```
Annotation 'AbapCatalog.preserveKey' is deprecated and regarded as obsolete.
```

Yeni CDS'lerde kullanma. Eski <LEGACY_SOURCE> source'larından dönüştürürken **kaldır**.

### 30.5 İçerik Annotation'ları (Modern S/4)

```
@AbapCatalog.sqlViewName: 'ZSD001XXXX'   <-- 10 char limit
@AbapCatalog.compiler.compareFilter: true
@AccessControl.authorizationCheck: #NOT_REQUIRED  <-- veya #CHECK
@EndUserText.label: 'Açıklama'
```

### 30.6 Field Adı Doğrulama — DTEL ≠ Field Name

<LEGACY_SOURCE> source'larında bazı field name'ler DTEL adıyla **karıştırılmış olabilir**. Örneğin:
- `T173.versart` ❌ — DTEL adı, field adı değil
- `T173.vsart` ✅ — gerçek field adı (DTEL `versart`)

Sorun çıkarsa SAP GET ile gerçek tablo yapısını çek:
```
GET /sap/bc/adt/ddic/tables/{table}/source/main
```

### 30.7 Aktivasyon

`activate_object.py --type cds` çalışıyor. Modern S/4 uyarıları:
- `preserveKey` deprecated (yukarıda)
- Diğer info-level uyarılar normaldir, aktivasyon başarılı olur

### 30.8 <LEGACY_SOURCE> → TD Namespace Dönüşümü

Eski <LEGACY_SOURCE> CDS'ini içeri taşırken yapılacak değişiklikler:

| <LEGACY_SOURCE> | TD |
|---|---|
| `zsd_007_ddl_X` | `zsd001_ddl_X` |
| `ZSD_007_CV_X` veya `ZSD_007_V_X` (SQL view) | **`ZSD001_V_XXXXX`** (SABİT FORMAT, toplam ≤14 char) |
| `zsd_007_t_X` (Z tablo) | `zsd001_t_X` |
| `zsd_007_e_X` (Z DTEL) | `zsd001_e_X` |
| `zsd_007_d_X` (Z domain) | `zsd001_d_X` |
| `zzitemno` (LIPS append) | `zz1_item_no_dli` |
| `zzitemqty` (LIPS append) | `zz1_item_qty_dli` |
| `zzbooking` (LIKP append) | `zz1_booking_number_dlh` |
| `zzcontainer` (LIKP append) | `zz1_container_number_dlh` |
| `@AbapCatalog.preserveKey` | **KALDIR** (deprecated) |

**⚠️ SQL View Adı KURALI (Sprint 3'te ihlal edildi):**
- Format **`ZSD001_V_XXXXX`** sabittir (8 char prefix + ≤5 char suffix = ≤14 char total)
- ❌ Eski <LEGACY_SOURCE> prefix korunamaz: `ZSD_007_CV_CONCD` YANLIŞ
- ❌ Kısaltılmış format kullanılamaz: `ZSD01CONCD` YANLIŞ (eski stil)
- ✅ Doğru: `ZSD001_V_CONCD`, `ZSD001_V_VOYDS`, `ZSD001_V_ORDIT`

Otomatik dönüştürücü `TempScripts/_convert_cds_sources.py`:
- **Yanlış:** Manuel `sqlview_map = {'ZSD_007_CV_X': 'ZSD01X', ...}` — entry atlanırsa <LEGACY_SOURCE> prefix kalır
- **Doğru:** Regex: `re.sub(r"'ZSD_007_(?:CV|V)_(\w+)'", r"'ZSD001_V_\1'", src)`

### 30.9 TD Namespace WHITELIST — Pre-flight Validation (POZİTİF KURAL)

**Tek doğru format vardır.** Whitelist'te olmayan her şey YASAK. Sprint 3'te ve Sprint 4'te (SHIPPING_TYPES vakası 2026-05-13) bu kuralı negative ifade ettiğim için tekrar hata oldu — şimdi pozitif whitelist:

#### 3 Katmanlı Whitelist Kuralı

| # | Konu | TEK GEÇERLİ FORMAT | Regex (Python) |
|---|---|---|---|
| 1 | sqlViewName annotation | `'ZSD001_V_<1-5 büyük harf/rakam>'` (≤14 char total) | `^ZSD001_V_[A-Z0-9]{1,5}$` |
| 2 | `define view <name>` | `zsd001_ddl_<x>` | `^zsd001_ddl_[a-z0-9_]+$` |
| 3 | Source body referansları | Sadece `zsd001_*` (CDS/tablo/DTEL/domain) | (negative: hiç `zsd_007_*` veya `'ZSD01XXXX'` yok) |

**ÖRNEKLER:**

✅ **DOĞRU CDS başlığı:**
```cds
@AbapCatalog.sqlViewName: 'ZSD001_V_CONCD'
@AbapCatalog.compiler.compareFilter: true
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Konteyner müşteri detay'
define view zsd001_ddl_container_customer
  as select from likp
    left outer join zsd001_ddl_shipping_types as ShipType on ...   -- ✅ Z-CDS ref TD namespace
```

❌ **YASAK örnekler (script HEMEN FAIL eder):**
```cds
@AbapCatalog.sqlViewName: 'ZSD_007_CV_CONCD'    -- Katman 1: <LEGACY_SOURCE> prefix
@AbapCatalog.sqlViewName: 'ZSD01CONCD'          -- Katman 1: eski kısaltma
@AbapCatalog.sqlViewName: 'ZSD001_V_TOOLONG'    -- Katman 1: 14+ char
define view zsd_007_ddl_x                       -- Katman 2: eski namespace
... left outer join zsd_007_ddl_y               -- Katman 3: source body'de orphan ref
... left outer join 'ZSD01ORDDS'                -- Katman 3: eski stil literal
```

#### Pre-flight Check (kod düzeyi, otomatik, bypass edilemez)

`scripts/populate_cds_views.py` → `validate_sql_view_names()` fonksiyonu **dosya okuma + SAP bağlantısı + POST/PUT aktivasyon işleminden ÖNCE** çağrılır. Tek bir ihlal varsa script `exit 1` ile çıkar, hiçbir SAP isteği yapılmaz.

```python
SQL_VIEW_PATTERN  = re.compile(r"^ZSD001_V_[A-Z0-9]{1,5}$")
VIEW_NAME_PATTERN = re.compile(r"^zsd001_ddl_[a-z0-9_]+$")
SQL_VIEW_MAX_LEN  = 14

BANNED_SOURCE_PATTERNS = [
    (re.compile(r"\bzsd_007_\w+", re.IGNORECASE),
     "<LEGACY_SOURCE> namespace referansı"),
    (re.compile(r"'ZSD_007_(?:CV|V)_\w+'"),
     "Eski <LEGACY_SOURCE> sqlViewName literal'i"),
    (re.compile(r"'ZSD\d{2}[A-Z]{4,8}'"),
     "Eski kısaltılmış sqlViewName literal'i"),
]

def validate_sql_view_names(cds_files):
    """3 katman whitelist: sqlViewName + view name + source body."""
    errors = []
    for f in cds_files:
        source = f.read_text(encoding='utf-8')
        # Katman 1
        m = re.search(r"@AbapCatalog\.sqlViewName\s*:\s*'([^']+)'", source)
        if not m or not SQL_VIEW_PATTERN.match(m.group(1)):
            errors.append(f"{f.name}: sqlViewName whitelist ihlali")
        # Katman 2
        vm = re.search(r"\bdefine\s+view\s+(\S+)", source, re.IGNORECASE)
        if not vm or not VIEW_NAME_PATTERN.match(vm.group(1).lower()):
            errors.append(f"{f.name}: view name whitelist ihlali")
        # Katman 3
        for pat, msg in BANNED_SOURCE_PATTERNS:
            for hit in pat.finditer(source):
                line = source[:hit.start()].count('\n') + 1
                errors.append(f"{f.name}:{line}: yasak '{hit.group(0)}' — {msg}")
    return errors
```

#### Manual Kontrol Komutları (her CDS batch'inden önce çalıştır)

```powershell
# 1. sqlViewName whitelist'te DEĞİL olan dosyalar (BOŞ çıkmalı)
grep -EL "^@AbapCatalog\.sqlViewName:\s*'ZSD001_V_[A-Z0-9]{1,5}'" ERP/SD/ZSD001_CLC/cds/*.cds

# 2. view name whitelist'te DEĞİL olan dosyalar (BOŞ çıkmalı)
grep -EL "^define view zsd001_ddl_" ERP/SD/ZSD001_CLC/cds/*.cds

# 3. Source body'de YASAK referans (BOŞ çıkmalı)
grep -nE "(zsd_007_|'ZSD_007_(CV|V)_|'ZSD[0-9]{2}[A-Z]{4,8}')" ERP/SD/ZSD001_CLC/cds/*.cds
```

#### Namespace Converter (gelecek modüller için — manuel dictionary YASAK)

```python
# 1. sqlViewName
src = re.sub(
    r"@AbapCatalog\.sqlViewName\s*:\s*'ZSD_007_(?:CV|V)_(\w+)'",
    lambda m: f"@AbapCatalog.sqlViewName: 'ZSD001_V_{m.group(1)[:5]}'",
    src
)
# 2. view name
src = re.sub(r'\bzsd_007_ddl_', 'zsd001_ddl_', src, flags=re.IGNORECASE)
# 3. Tablo/DTEL/Domain
src = re.sub(r'\bzsd_007_t_', 'zsd001_t_', src, flags=re.IGNORECASE)
src = re.sub(r'\bzsd_007_e_', 'zsd001_e_', src, flags=re.IGNORECASE)
src = re.sub(r'\bzsd_007_d_', 'zsd001_d_', src, flags=re.IGNORECASE)
```

> **⚠️ TADIR Cleanup Hatırlatma:** Bir DDL source SAP'de bir kez `ZSD01XXXX` veya `ZSD_007_*` sqlViewName ile aktive edildiyse, source dosyada `ZSD001_V_X` yazsanız bile **rename broken**. Çözüm: transport release et (TADIR clean) → yeniden aktive et. DELETE workbench-level yetmez. Sprint 3-4'te toplam 3+ kez yaşandı.

### 30.10 DB SQL View Orphan Cleanup (Sprint 4 Keşfi — 2026-05-13)

**🎯 Kritik Keşif:** DDL source workbench-level DELETE ≠ DB DDIC catalog SQL view drop. Transport release + workbench DELETE sonrası bile **DB DDIC catalog'ta SQL view orphan kalır**. Bu orphan, aynı DDL source'u farklı sqlViewName ile aktive etmeyi engeller ("rename broken").

#### Pattern (Sprint 3'ten kalma 9 vaka, hepsi Sprint 4'te keşfedildi)

Sprint 3'te yaratılan DDL source'lar 2 farklı sqlViewName stiliyle aktive edilmişti:

| Source dosyada beklenen | Sprint 3'te DB'ye yazılan |
|---|---|
| `ZSD001_V_CONCD` | `ZSD_007_CV_CONCD` (<LEGACY_SOURCE> prefix korundu) |
| `ZSD001_V_VOYDS` | `ZSD001VYDS` (kısaltılmış stil) |
| `ZSD001_V_SHTYP` | `ZSD01SHTYP` (kısaltılmış stil) |
| ... | ... |

Source dosyalar düzeltilse de DB DDIC catalog'ta eski sqlView'lar orphan kaldı. Workbench-level GET/DELETE bunları silemedi — DB-level SE14 cleanup şart.

#### Tespit Yöntemi

`TempScripts/_probe_orphans.py` her CDS için POST shell + PUT + ACTIVATE dener, hata mesajındaki `SQL view (\w+) cannot be renamed` pattern'ından orphan SQL view adını çıkarır. Çıktı: orphan listesi → user'a verilir.

#### Cleanup (SAP-side, manual — ADT API'den yapılamaz)

**Yöntem 1 — SE14 (Database Utility):**
```
SE14 → Object Type: VIEW → İsim: <ORPHAN_VIEW>
  → Edit → Object → "Delete from database" → transport'a koy
```

**Yöntem 2 — SE38 / RSDDDDCDELOLD:**
Orphan DDIC view toplu temizleyici raporu. Liste mode ile çalıştır, seçim yap.

**Yöntem 3 — Direkt SQL (sıra dışı):**
```sql
-- SE16N → DD02L tablosunda VIEWNAME = <ORPHAN> kayıtları görüntüle
-- Kayıt varsa SE11/SE14 cleanup gerek
```

#### Tam Temizlik Sırası

```
1. Probe (script) → orphan listesi
2. User: SE14'ten her orphan'ı transport'a koyup sil
3. User: transport release et (<TRANSPORT>)
4. Script: POST shell + PUT source + Activate → temiz aktivasyon
5. Doğrulama: SELECT * FROM <YENİ_SQL_VIEW>
```

#### Önleme (Gelecek Modüller için)

- ✅ İlk yaratımda **doğru sqlViewName** kullan (whitelist-only)
- ✅ Pre-flight check (§17.9) atlanırsa script `exit 1`
- ❌ "Sonra düzeltirim" diyerek geçici/yanlış sqlViewName ile aktive **ASLA ETME** — temizliği saatler sürer

> **⚠️ Operasyonel Maliyet:** Sprint 4'te 9 orphan tespit edildi, hepsinin DB-level cleanup'ı user-side iş + transport release. **2-3 saatlik geriye dönük temizlik** + **+1 saat yeniden aktivasyon**. Pre-flight check kuralı bunu önler.



---

## CDS Yaratma Tuzakları — `create_cds_view` + yeni view (2026-06-11)

Yeni CDS yaratırken yaşanan 3 tuzak (ZSD001_I/C_MAT_LOOKUP). **Kanonik akış: `create_cds_view` (shell) → `push_object` (gerçek source + activate).**

### T1 — `create_cds_view` source'u XML'e gömerken escape etmiyordu → `<>`/`<`/`&` "Unknown error"
- **Belirti:** `create_cds_view` "Request failed after 3 retries: Unknown error" (retry-wrapper gerçek HTTP hatasını gizler). Object yaratılmaz → sonraki `push_object` `[423] not locked`.
- **Kök neden:** create POST gövdesi `<ddl:source>{cds_source}</ddl:source>` — source RAW gömülüyordu. `case when x <> 0` / `<` / `&` → XML bozulur → SAP reddeder.
- **Neden bazı view'lar çalıştı:** içinde `<>` olmayan source'lar (ör. basit agregasyon) escape gerektirmedi.
- **FIX (uygulandı):** `sap_adt_lib.create_cds_view` artık `html.escape(cds_source, quote=False)` ile gömüyor. Tekrar etmez.
- **Workaround (fix yoksa):** shell'i `<>`-içermeyen minimal/escaped source ile yarat, sonra `push_object` ile gerçek source'u yükle (source endpoint text/plain → `<>` sorunsuz).

### T2 — Opaque hatada YÖNTEM DEĞİŞTİRME, önce GERÇEK hatayı yakala
- Bu vakada create_cds_view → minimal shell → MCP post_shell diye dolanıldı (zaman kaybı). Doğrusu: ham `session.post(...)` ile `response.status_code + response.text` yazdırıp gerçek hatayı görmek (XML break anında ortaya çıktı). Bkz. memory `feedback_playbook-once-oku` (tahminle deneme yok).

### T3 — Read-only consumption = `as select from`, `as projection on` DEĞİL
- `define view entity ... as projection on <I_view>` → "**Transactional Projection View must be part of a business object**" (projection = RAP transactional → BDEF/BO ister).
- Salt-okunur OData lookup (BO yok) için **`as select from <I_view>`** (düz view) kullan. `@Semantics` annotation'ları consumption'da tekrar bildir.
- Ayrıca: `define root view entity ... as projection on <non-root>` → "ROOT keyword not valid" (projection ROOT olamaz interface root değilse).

### T4 — UNION view-entity 3 KURALI (2026-06-19, ZSD001_I_BATCH_STOCK EWM/MM union) — peşinen uygula, aksi her biri AYRI aktivasyon turu
Bir `define view entity ... union all ...` yazarken SAP 3 kuralı tek tek dayatır (4 tur ping-pong'a mal oldu). **HEPSİNİ baştan uygula:**
- **(a) WHERE'de `NOT EXISTS`/`EXISTS` subquery YASAK** → `Unexpected keyword "exists"`. Kanonik anti-join: **LEFT OUTER JOIN + `WHERE <join>.key IS NULL`** (eşleşmeyenleri tut). (Eski `DEFINE VIEW`'de EXISTS vardı; view-entity'de yok.)
- **(b) Element-level `@Semantics.*` (quantity/amount vb.) YALNIZ 1. (ilk) SELECT dalında** → `Annotations are not allowed in this branch`. Sonuç-element annotation'ı 1. daldan miras alınır; 2.+ dallarda TEKRARLAMA.
- **(c) Header'da `@Metadata.ignorePropagatedAnnotations: true` ZORUNLU** (propagate-edilebilir @Semantics.quantity varsa) → `Annotation Metadata.ignorePropagatedAnnotations is required`.
- Ayrıca: iki dal **field-sayısı/sıra/tip BİREBİR** (literal cast'lerle hizala). bug-gate (read-only) bunları YAKALAYAMAZ (syntax yalnız push+activate'te çıkar) → gateway aktivasyonu güvenlik ağı.

### T5 — conv-exit'li alan OData expose → publish FAIL → `cast()` ile exit düş (2026-06-19)
- **Belirti:** CDS aktive olur AMA `adt_publish_service`/`$metadata` FAIL: `Do not use conversion exit <EXIT> for property <FIELD>`. SADL/OData V2 property'de conversion-exit'i reddeder.
- **Sık alanlar:** `/scwm/de_huident` (HUID — HU no), kur/EXCRT/birim exit'li DTEL'ler.
- **FIX:** alanı `cast( <field> as abap.char( <len> ) )` (veya uygun plain tip) ile expose et → exit düşer, değer korunur. (HUID = char 20.) UNION'da İKİ dalda da tip-hizalı cast.
- **Önleme:** EWM/HU/kur alanı OData picker/UI'a expose edilecekse, CDS'te baştan plain-cast et. Ref: `ui-backend-rap.md` conv-exit notu.

### T6 — JOIN'de kullanılan alanın RENAME/SİL'i → aktivasyon deadlock → **transitional 3-adım swap** (2026-06-20, ZSD001 CONTAINER_SHIPMENT→booking-item)
- **Belirti:** Bir view'da (A) bir alanı (X) silince/yeniden-adlandırınca SAP bloklar: *"Field <SQLVIEW>-X is still being used in join of <CONSUMER_VIEW>"*. Tüketici (B) view A'nın X alanını JOIN şartında kullanıyor. Atomik co-activation (`adt_activate` + `also`, her iki sıra) da **"column <Y> is unknown"** ile FAIL — SAP inactive↔inactive arası JOIN-alanı rename'ini tek worklist'te çözmez.
- **FIX (kanonik non-destructive alan-rename deseni):** 3 adım, her biri **tek-obje aktive**:
  1. A'ya YENİ alanı (Y) **EKLE** (eski X'i KORUYARAK) → A tek-aktive (X hâlâ var, tüketici kırılmaz).
  2. Tüketici B'nin JOIN'ini **Y'ye çevir** → B aktive.
  3. A'dan eski X'i **SİL** (nihai hedef) → A aktive (artık kimse X'i join'de kullanmıyor).
- **Not:** Yeni/eski alan 1:1 eşlenikse (ör. container_no ↔ booking_item her ikisi de aynı kayıt granülaritesi) group-by/agregasyon sonucu (ShipmentCount vb.) değişmez. Çıktı kolonları aynı kalırsa tüketici RAP/servis ETKİLENMEZ ($metadata aynı → republish gerekmez, yine de doğrula).
- **Önleme:** Bir CDS alanını tüketici JOIN'i varken doğrudan rename/sil ETME; önce ekle→tüket-çevir→sil.

### T7 — `CASE WHEN` sol-taraf aritmetiği DIŞ PARANTEZ ile sarmalanMAZ → aktivasyon `Unexpected word ')'` (2026-06-21, ZSD001_I_SHIP_POOL SeStatus)
- **Belirti:** Computed alan `cast( case when ( <aritmetik> ) <= 0 then 'C' else 'A' end as abap.char(1) )` → `adt_syntax_check` **valid:true** dönse de **aktivasyon FAIL**: `Unexpected word ')'` (konum = kapanan dış paren).
- **Kök neden:** CDS `CASE WHEN`'de karşılaştırmanın SOL tarafındaki aritmetik ifadeyi **parantezle gruplamayı kabul etmiyor**. `when ( a - b ) <= 0` → red; `when a - b <= 0` → OK.
- **FIX:** dış parantezleri kaldır, aritmetiği parantezsiz yaz (aynı dosyadaki ham aritmetik alanın — ör. OpenQty `cast(qty) - coalesce(...)` — deseniyle birebir). İç cast'ler (semantic-strip) kalır, yalnız gruplama-pareni gider.
- **DERS (kritik):** `adt_syntax_check` bu hatayı YAKALAMAZ (pre-push/canlı kaynağı okur, yeni computed alan henüz orada yok) → **aktivasyon = tek güvenilir syntax gate** (bug-gate read-only de yakalayamaz; gateway aktivasyonu güvenlik ağı). "syntax_check geçti" ≠ "aktive olur". Bkz. memory `feedback_abaplint-parser-error-gercek-olabilir` ikizi.

### T8 — JOIN ON karşılaştırmasında `cast()`/FUNCTION güvenilmez (COMP_LEFT yasak) → PRE-CAST KÖPRÜ-VIEW kullan (2026-06-24, ZSD001_I_NAVLUN_REPORT vfkp⨝vtts numc-mismatch)
- **Belirti:** İki farklı uzunluktaki numerik key'i join etmek için ON şartında cast kullanılınca aktivasyon FAIL: `Expression type FUNCTION not allowed in expression context COMPARISON, clause type COMP_LEFT`. Örn (RED): `and cast(Stage.tsnum as abap.numc(6)) = Cost.repos`.
- **Kök neden:** CDS JOIN ON karşılaştırmasında cast/fonksiyon ifadesi GÜVENİLMEZ; SOL operandda kesin YASAK (`COMP_LEFT`), sağ operandda da garanti DEĞİL (release-bağımlı). Bu yüzden inline cast'e (flip dahil) GÜVENME.
- **ÇALIŞAN (KANONİK) = PRE-CAST KÖPRÜ-VIEW + LPAD (cast TEK BAŞINA YETMEZ):** alt view vtts'i 6-haneye getirip expose etsin → ana view DÜZ join'lesin (`Cost.repos = Stage.TsnumC6`, `Cost.rebel = Stage.Tknum`). Cast tüketici ON'undan kalkar, COMP_LEFT yasağı düşer. Dosya: `ERP/SD/ZSD001_CLC/cds/ZSD001_I_NAVREP_STAGE.cds`.
- **⚠️ İKİNCİ TUZAK (2026-06-24, aynı obje, 2. round-trip):** köprü-view İÇİNDE bile `cast(tsnum as abap.numc(6))` AKTİVASYONDA FAIL: `CAST NUMC ... lengths must match`. CDS **numc(N)→numc(M) (N≠M) cast'ine izin VERMEZ** (projeksiyonda da). DOĞRU FORM = önce `lpad` ile 6-char string yap, SONRA **eşit-uzunluk** cast: `cast( lpad( Stage.tsnum, 6, '0' ) as abap.numc(6) ) as TsnumC6` (char(6)→numc(6), uzunluk eşit → geçer).
- **KANIT (<LEGACY_SOURCE> — yanlış anlaşılmıştı):** orijinal `zsd_024_v_nklklm` bir **klasik SE11 DDIC view** (CDS değil, ADT 404); `tsnum6`'yı SE11 conversion ile üretiyor — CDS `cast()` deseni DEĞİL. Yani köprü FİKRİ doğru ama CDS cast tekniği <LEGACY_SOURCE>'dan kopyalanamaz; lpad+eşit-uzunluk-cast bizim CDS-valid çözümümüz.
- **NUMC uzunluk değişimi:** doğrudan numc→numc cast (4→6) YASAK; `lpad(...,6,'0')` → eşit-uzunluk cast ile çöz. Uzun key'i kısaltma (veri kaybı) zaten YASAK.
- **DENENEN ZAYIF (flip):** cast'i sağ operanda almak (`Cost.repos = cast(...)`) teorik olarak COMP_LEFT'i atlatabilir ama `adt_syntax_check` yalnız SERVER'daki inactive/canlı kaynağı okur (inline-source kabul ETMEZ) → push'tan önce flip'in derlendiği DOĞRULANAMAZ. Doğrulanamayan flip yerine kanıtlı köprü-view tercih edilir (gateway round-trip garantisi).
- **FS:** köprü-view "gerekmez" diyen FS'e as-built notu düş (derleyici zorunlu kıldı = meşru teknik gereklilik).

### T9 — `string_agg` bu sistemin ABAP CDS view-entity compiler'ında DESTEKLENMİYOR → 1:N liste için native `count` + `max`-temsilci (2026-06-24, ZSD001_I_SE_BOOKING/PLATE/DELIVERY_AGG)
- **Belirti:** Agregat view'de `string_agg(col, ', ')` ile 1:N değerleri virgüllü listeye toplama → AKTİVASYON FAIL: `Activation was cancelled. Column <col> is not contained in the GROUP BY list`. Compiler `string_agg`'i aggregate olarak TANIMIYOR → col'u non-aggregated sayıp GROUP BY hatası veriyor.
- **Kök neden:** ABAP CDS view-entity'de string aggregation YOK (MAX/MIN/SUM/AVG/COUNT var, string_agg yok). S4CORE sürüm-numarasına bakıp "destekli" varsaymak (çıkarım) **canlı aktivasyonla çürür** — capability iddiası = CANLI TEST, versiyon-çıkarımı DEĞİL. Codebase'de proven precedent yoksa şüpheci ol.
- **ÇALIŞAN (KANONİK):** 1:N özet için native `count(*)`/`count(distinct ...)` (adet) + `max(...)` (temsilci/son tek değer). [0..1] grain GROUP BY ile korunur. Tam virgüllü liste GEREKİYORSA AMDP/table-function (CDS native değil). Kanıt: FREIGHT_COST max, ORDERED_QTY count/sum.
- **Karar deseni:** "Booking No(lar)/Teslimat No(lar)" gibi liste-istekleri salt-okunur özet raporda **adet + temsilci(max)**'e indirilebilir (per-belge detay drill-down/kardeş raporda); FS'e as-built notu, sessizce düşürme.
- **Reviewer dersi:** bug-checklist-BE → "CDS capability iddiası (string_agg vb.) versiyon-çıkarımıyla DEĞİL, codebase proven-precedent veya canlı aktivasyonla doğrulanır" satırı.

### T10 — Sanal element (virtual element) + SADL calc-exit: JOIN'lenemeyen kaynaktan (STXL metni vb.) hesaplanmış kolon (2026-06-29, ZSD001_C_SE_REPORT 3 sipariş notu; ZCL_SD001_SEREP_TEXTS)
> **Ne zaman:** CDS'e DB-join ile gelemeyen bir değer (uzun metin/STXL READ_TEXT, hesap, dış-kaynak) **görüntü kolonu** olarak gerekiyor. Çözüm = `@ObjectModel.virtualElement` + `IF_SADL_EXIT_CALC_ELEMENT_READ` ABAP exit. **İlk-kez bu sistemde**; 4 tur patinaj yaşandı, hepsi aşağıdaki tuzaklardı.

**KANONİK reçete (ZSD001_C_SE_REPORT + ZCL_SD001_SEREP_TEXTS):**
- CDS (`as select from` consumption): `@ObjectModel.virtualElement: true` + `@ObjectModel.virtualElementCalculatedBy: 'ABAP:ZCL_...'` + **`cast( '' as abap.char( N ) )`** (flat-tip ZORUNLU; aşağı T10-a). Exit'in ihtiyacı olan kaynak alan (ör. OrderNo) view'da bulunmalı.
- Exit class `IF_SADL_EXIT_CALC_ELEMENT_READ`: `get_calculation_info` (istenen orig-element'leri bildirir) + `calculate` (değerleri doldurur).

**T10-a — `abap.string` CAST'ta GEÇERSİZ:** select-from view'da sanal alan CAST ile tiplenir; CDS CAST **yalnız flat tip** alır → `cast('' as abap.string)` aktive OLMAZ. Üst sınır **`abap.char(1333)`** (= Edm.String MaxLength 1333). Gerçek unbounded gerekiyorsa ayrı mimari (projection view / function-import) — başlık-notu için aşırı. (`virtual <ad> : abap.string` düz-tip yalnız `as projection on`/abstract entity'de.)

**T10-b — `get_calculation_info` orig-element adı CASE-SENSITIVE UPPERCASE:** `CL_SADL_EXIT_HANDLER=>_check_orig_element` adı `sadl_entity-elements`'te case-sensitive arar; SADL element adları UPPERCASE. `et_requested_orig_elements`'a **`'ORDERNO'`** (camelCase `'OrderNo'` DEĞİL) → aksi `CX_SADL_EXIT_WRONG_ELMENT` → **RAISE_SHORTDUMP** (OData 500, calculate'ten ÖNCE). Çalışan std örnek: `CL_SDBIL_PBD_VIRTUAL_ELEMENT` (`WHEN 'WBSDESCRIPTION'. INSERT |WBSELEMENTEXTERNALID|`). `calculate` 1:1 index (it_original_data↔ct_calculated_data, `sy-tabix`); tablo-ifadesi `itab[...]` DEĞİL `READ TABLE` (eşleşme yoksa CX_SY_ITAB_LINE_NOT_FOUND dump).

**T10-c — Metin OKUMASI: READ_TEXT yerine PROVEN okumayı yeniden kullan (dil + tdname tuzağı):** STXL metni için `READ_TEXT` çift-tuzak: (1) **tdname yazıcıyla BİREBİR** olmalı — yazıcı ham `vbeln` yazdıysa `ALPHA_INPUT`'u CHAR70 tdname'e koyma (70-haneye zero-pad → eşleşmez → boş); (2) **dil** — `READ_TEXT language=sy-langu` OData runtime'da TR olmayabilir (metin 'T'de kayıtlı) → boş. **ÇÖZÜM:** zaten çalışan okumayı reuse et — burada `ZSD001_CL_SO_MANAGER->get_order_texts` (RAP `READ ENTITIES ... BY \_Text`, dil-bağımsız, FIT_SE ekranıyla AYNI). Cross-paket ref kabul (UI da aynı servisi kullanıyor). **DERS:** "bu değer başka ekranda zaten çalışıyorsa, o okumayı kopyala — sıfırdan READ_TEXT kovalama."

**T10-d — CANLI DOĞRULAMA ŞART (statik bug-gate runtime'ı görmez):** sanal element exit'i statik review/syntax/ATC'den GEÇER ama runtime'da dump/boş döndürebilir. Doğrulama tekniği (browser'sız):
- OData curl (.conn_adt kimliği, şifre echo'suz): `curl -s -k -u "$U:$P" ".../<SRVB>/<Entity>?$select=...&$format=json&sap-client=100"` → HTTP 500 = dump; boş alan = okuma bug'ı.
- Dump KÖK-NEDEN: ADT runtime-dumps feed → `curl ... -H "Accept: application/atom+xml;type=feed" ".../sap/bc/adt/runtime/dumps?sap-client=100"` → exception adı (CX_SADL_EXIT_WRONG_ELMENT vb.) + bizim-class satırı. **Tahmin etme, dump'a bak.**
- STXH/STXL gerçek key teyidi: gateway `adt_classrun` read-only probe (`SELECT ... FROM stxh WHERE tdobject=.. AND tdname LIKE ..`).
**Reviewer dersi:** bug-checklist-BE → "sanal element/SADL calc-exit = statik gate YETMEZ → canlı OData curl + (boşsa) dump-feed/STXH probe ile doğrula".

### T11 — base ELEMENT rename + consumption o alanı seçiyor → karşılıklı bağımlılık kilidi → **atomik co-activation** `adt_activate(base, also=[consumption])` (2026-07-01, ZSD001 çıkış→müşteri ülkesi rename)
> **Ne zaman:** base view'da bir alan RENAME edilir (ör. `klm_cikis_ulkesi`→`klm_musteri_ulkesi`) ve consumption view o alanı `as select from` ile tüketir. Tek-obje aktivasyon **iki yönlü kilitlenir** (T6 akrabası — ama T6 JOIN-alanı sil/rename için transitional 3-adım; bu, base↔consumption select bağımlılığı).
- **Belirti:** base tek-başına aktive → `Field ZSD001_V_INVOICE-KLM_CIKIS_ULKESI is still being used in view ZSD001_C_INVOICE` (aktif consumption hâlâ eski adı kullanıyor). Consumption tek-başına → `column klm_musteri_ulkesi is unknown` (aktif base hâlâ eski). Deadlock.
- **ÇÖZÜM:** her iki DÜZELTİLMİŞ kaynağı **inaktif upload** et (push, activate etme), sonra **tek POST'ta** `adt_activate(base, also=[consumption])` → atomik co-activation (`activationExecuted=true`, refs=her ikisi). Yeni-yeni birlikte aktive olur, ara-durum kilidi oluşmaz.
- **T11-a — `content_mismatch` false-alarm:** co-activation sonrası tool `content_mismatch=true` dönebilir — stale `_LAST_PUSHED` baseline aktifi ESKİ kaynakla kıyaslar. Körü körüne "başarısız" sayma → **`adt_get version=active` ile bağımsız teyit** (kaynakta yeni join/alan var mı). Araç-readback ≠ canlı gerçek (feedback_arac-basarisizligini-zararsiz-sayma tersi de geçerli: false-NEGATIF).
